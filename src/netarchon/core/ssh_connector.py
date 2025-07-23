"""
NetArchon SSH Connection Module

Core SSH connectivity functionality for network device connections.
"""

import socket
import time
from datetime import datetime
from typing import Optional, Dict, Any

import paramiko

from ..models.connection import (
    ConnectionInfo,
    ConnectionType,
    ConnectionStatus,
    AuthenticationCredentials
)
from ..utils.exceptions import (
    ConnectionError,
    AuthenticationError,
    TimeoutError
)
from ..utils.logger import get_logger
from ..utils.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig
from ..utils.retry_manager import retry_manager_registry, create_network_retry_config


class ConnectionPool:
    """Manages multiple SSH connections with pooling and reuse."""
    
    def __init__(self, max_connections: int = 50, idle_timeout: int = 300):
        """Initialize connection pool.
        
        Args:
            max_connections: Maximum number of concurrent connections
            idle_timeout: Timeout for idle connections in seconds
        """
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connector = None  # Will be initialized lazily
        self.logger = get_logger(f"{__name__}.ConnectionPool")
    
    def _get_connector(self) -> 'SSHConnector':
        """Get SSH connector instance (lazy initialization)."""
        if self.connector is None:
            self.connector = SSHConnector()
        return self.connector
        
    def get_connection(self, 
                      device_id: str,
                      host: str,
                      credentials: AuthenticationCredentials,
                      port: int = 22) -> ConnectionInfo:
        """Get or create a connection for the specified device.
        
        Args:
            device_id: Unique device identifier
            host: Target host IP address or hostname
            credentials: Authentication credentials
            port: SSH port (default 22)
            
        Returns:
            ConnectionInfo object
            
        Raises:
            ConnectionError: If unable to establish connection
        """
        # Check if we already have a connection for this device
        if device_id in self.connections:
            connection = self.connections[device_id]
            
            # Test if existing connection is still valid
            if self._get_connector().is_connected(connection):
                connection.update_activity()
                self.logger.debug("Reusing existing connection", device_id=device_id)
                return connection
            else:
                # Remove stale connection
                self.logger.info("Removing stale connection", device_id=device_id)
                self._remove_connection(device_id)
        
        # Check connection limit
        if len(self.connections) >= self.max_connections:
            self.cleanup_idle_connections()
            
            if len(self.connections) >= self.max_connections:
                raise ConnectionError(f"Maximum connections ({self.max_connections}) reached",
                                    {"current_connections": len(self.connections)})
        
        # Create new connection
        try:
            connection = self._get_connector().connect(host, credentials, port, device_id)
            self.connections[device_id] = connection
            
            self.logger.info("New connection added to pool", 
                           device_id=device_id, 
                           pool_size=len(self.connections))
            
            return connection
            
        except Exception as e:
            self.logger.error("Failed to create connection", 
                            device_id=device_id, error=str(e))
            raise
    
    def release_connection(self, device_id: str) -> None:
        """Release a connection back to the pool.
        
        Args:
            device_id: Device identifier to release
        """
        if device_id in self.connections:
            connection = self.connections[device_id]
            connection.update_activity()
            self.logger.debug("Connection released back to pool", device_id=device_id)
        else:
            self.logger.warning("Attempted to release non-existent connection", 
                              device_id=device_id)
    
    def close_connection(self, device_id: str) -> None:
        """Close and remove a specific connection.
        
        Args:
            device_id: Device identifier to close
        """
        if device_id in self.connections:
            connection = self.connections[device_id]
            self._get_connector().disconnect(connection)
            self._remove_connection(device_id)
            
            self.logger.info("Connection closed and removed from pool", 
                           device_id=device_id, 
                           pool_size=len(self.connections))
    
    def cleanup_idle_connections(self) -> None:
        """Remove idle connections that exceed the timeout."""
        current_time = datetime.utcnow()
        idle_connections = []
        
        for device_id, connection in self.connections.items():
            idle_time = (current_time - connection.last_activity).total_seconds()
            
            if idle_time > self.idle_timeout:
                idle_connections.append(device_id)
        
        for device_id in idle_connections:
            self.logger.info("Removing idle connection", 
                           device_id=device_id, 
                           idle_time=idle_time)
            self.close_connection(device_id)
        
        if idle_connections:
            self.logger.info(f"Cleaned up {len(idle_connections)} idle connections",
                           remaining_connections=len(self.connections))
    
    def close_all_connections(self) -> None:
        """Close all connections in the pool."""
        device_ids = list(self.connections.keys())
        
        for device_id in device_ids:
            self.close_connection(device_id)
        
        self.logger.info("All connections closed", closed_count=len(device_ids))
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status information.
        
        Returns:
            Dictionary with pool status details
        """
        active_connections = sum(1 for conn in self.connections.values() 
                               if self._get_connector().is_connected(conn))
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "max_connections": self.max_connections,
            "idle_timeout": self.idle_timeout,
            "connection_ids": list(self.connections.keys())
        }
    
    def _remove_connection(self, device_id: str) -> None:
        """Internal method to remove connection from pool."""
        if device_id in self.connections:
            del self.connections[device_id]


class SSHConnector:
    """Core SSH connection functionality with circuit breaker protection."""
    
    def __init__(self, timeout: int = 30, retry_attempts: int = 3):
        """Initialize SSH connector.
        
        Args:
            timeout: Connection timeout in seconds
            retry_attempts: Number of retry attempts for failed connections
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.logger = get_logger(f"{__name__}.SSHConnector")
        
        # Initialize circuit breaker for SSH connections
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3
        )
        self.circuit_breaker = circuit_breaker_manager.get_circuit_breaker("ssh_connections", cb_config)
        
    def connect(self, 
                host: str, 
                credentials: AuthenticationCredentials,
                port: int = 22,
                device_id: Optional[str] = None) -> ConnectionInfo:
        """Establish SSH connection to a network device.
        
        Args:
            host: Target host IP address or hostname
            credentials: Authentication credentials
            port: SSH port (default 22)
            device_id: Optional device identifier
            
        Returns:
            ConnectionInfo object with connection details
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            TimeoutError: If connection times out
        """
        if not device_id:
            device_id = f"{host}:{port}"
            
        self.logger.info(f"Attempting SSH connection to {host}:{port}", 
                        device_id=device_id)
        
        # Use circuit breaker protection for connection attempts
        return self.circuit_breaker.call(self._connect_internal, host, credentials, port, device_id)
    
    def _connect_internal(self, host: str, credentials: AuthenticationCredentials, 
                         port: int, device_id: str) -> ConnectionInfo:
        """Internal connection method with retry logic.
        
        Args:
            host: Target host IP address or hostname
            credentials: Authentication credentials
            port: SSH port
            device_id: Device identifier
            
        Returns:
            ConnectionInfo object with connection details
        """
        
        connection_info = ConnectionInfo(
            device_id=device_id,
            host=host,
            port=port,
            username=credentials.username,
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTING
        )
        
        ssh_client = None
        last_error = None
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                self.logger.debug(f"Connection attempt {attempt}/{self.retry_attempts}",
                                device_id=device_id, attempt=attempt)
                
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Prepare connection parameters
                connect_params = {
                    'hostname': host,
                    'port': port,
                    'username': credentials.username,
                    'timeout': self.timeout,
                    'allow_agent': False,
                    'look_for_keys': False
                }
                
                # Add authentication method
                if credentials.uses_key_auth():
                    connect_params['key_filename'] = credentials.private_key_path
                else:
                    connect_params['password'] = credentials.password
                
                # Attempt connection
                ssh_client.connect(**connect_params)
                
                # Store SSH client in connection info for later use
                connection_info._ssh_client = ssh_client
                connection_info.status = ConnectionStatus.CONNECTED
                connection_info.established_at = datetime.utcnow()
                connection_info.update_activity()
                
                self.logger.info(f"SSH connection established successfully",
                               device_id=device_id, attempt=attempt)
                
                return connection_info
                
            except paramiko.AuthenticationException as e:
                last_error = e
                self.logger.error(f"Authentication failed on attempt {attempt}",
                                device_id=device_id, error=str(e))
                if ssh_client:
                    ssh_client.close()
                raise AuthenticationError(f"Authentication failed for {host}:{port}", 
                                        {"host": host, "port": port, "username": credentials.username})
                
            except socket.timeout as e:
                last_error = e
                self.logger.warning(f"Connection timeout on attempt {attempt}",
                                  device_id=device_id, timeout=self.timeout)
                if ssh_client:
                    ssh_client.close()
                    
            except (socket.error, paramiko.SSHException) as e:
                last_error = e
                self.logger.warning(f"Connection failed on attempt {attempt}",
                                  device_id=device_id, error=str(e))
                if ssh_client:
                    ssh_client.close()
                    
            # Wait before retry (except on last attempt)
            if attempt < self.retry_attempts:
                retry_delay = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                self.logger.debug(f"Retrying in {retry_delay} seconds",
                                device_id=device_id)
                time.sleep(retry_delay)
        
        # All attempts failed
        connection_info.status = ConnectionStatus.FAILED
        
        if isinstance(last_error, socket.timeout):
            raise TimeoutError(f"Connection to {host}:{port} timed out after {self.retry_attempts} attempts",
                             {"host": host, "port": port, "timeout": self.timeout})
        else:
            raise ConnectionError(f"Failed to connect to {host}:{port} after {self.retry_attempts} attempts: {last_error}",
                                {"host": host, "port": port, "attempts": self.retry_attempts, "last_error": str(last_error)})
    
    def disconnect(self, connection: ConnectionInfo) -> None:
        """Disconnect SSH connection.
        
        Args:
            connection: ConnectionInfo object to disconnect
        """
        if not hasattr(connection, '_ssh_client') or not connection._ssh_client:
            self.logger.warning("No active SSH client to disconnect",
                              device_id=connection.device_id)
            return
            
        try:
            connection._ssh_client.close()
            connection.status = ConnectionStatus.DISCONNECTED
            connection.update_activity()
            
            self.logger.info("SSH connection closed successfully",
                           device_id=connection.device_id)
            
        except Exception as e:
            self.logger.error("Error closing SSH connection",
                            device_id=connection.device_id, error=str(e))
        finally:
            connection._ssh_client = None
    
    def is_connected(self, connection: ConnectionInfo) -> bool:
        """Check if SSH connection is active.
        
        Args:
            connection: ConnectionInfo object to check
            
        Returns:
            True if connection is active, False otherwise
        """
        if not connection.is_connected():
            return False
            
        if not hasattr(connection, '_ssh_client') or not connection._ssh_client:
            connection.status = ConnectionStatus.DISCONNECTED
            return False
            
        try:
            # Try to get transport to check if connection is alive
            transport = connection._ssh_client.get_transport()
            if transport and transport.is_active():
                return True
            else:
                connection.status = ConnectionStatus.DISCONNECTED
                return False
                
        except Exception as e:
            self.logger.debug("Connection check failed",
                            device_id=connection.device_id, error=str(e))
            connection.status = ConnectionStatus.DISCONNECTED
            return False
    
    def test_connection(self, connection: ConnectionInfo) -> bool:
        """Test SSH connection by executing a simple command.
        
        Args:
            connection: ConnectionInfo object to test
            
        Returns:
            True if connection test passes, False otherwise
        """
        if not self.is_connected(connection):
            return False
            
        try:
            # Execute a simple command to test the connection
            stdin, stdout, stderr = connection._ssh_client.exec_command('echo "test"', timeout=10)
            output = stdout.read().decode().strip()
            
            if output == "test":
                connection.update_activity()
                self.logger.debug("Connection test passed",
                                device_id=connection.device_id)
                return True
            else:
                self.logger.warning("Connection test failed - unexpected output",
                                  device_id=connection.device_id, output=output)
                return False
                
        except Exception as e:
            self.logger.warning("Connection test failed with exception",
                              device_id=connection.device_id, error=str(e))
            connection.status = ConnectionStatus.FAILED
            return False