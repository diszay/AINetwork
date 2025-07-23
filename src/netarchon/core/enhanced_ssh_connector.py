"""
Enhanced SSH Connector with BitWarden Integration

Extended SSH connectivity that automatically retrieves credentials from BitWarden
for seamless network device authentication.
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
    AuthenticationCredentials,
    AuthenticationType
)
from ..utils.exceptions import (
    ConnectionError,
    AuthenticationError,
    TimeoutError
)
from ..utils.logger import get_logger
from ..utils.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig
from ..utils.retry_manager import retry_manager_registry, create_network_retry_config
from ..integrations.bitwarden import BitWardenManager, BitWardenError

# Import the original connector for fallback
from .ssh_connector import SSHConnector as BaseSSHConnector, ConnectionPool


class EnhancedSSHConnector(BaseSSHConnector):
    """
    Enhanced SSH connector with BitWarden credential management.
    
    Automatically retrieves credentials from BitWarden vault for network devices,
    falling back to manual credentials when needed.
    """
    
    def __init__(self, timeout: int = 30, retry_attempts: int = 3, 
                 enable_bitwarden: bool = True):
        """Initialize enhanced SSH connector.
        
        Args:
            timeout: Connection timeout in seconds
            retry_attempts: Number of retry attempts for failed connections
            enable_bitwarden: Enable BitWarden integration
        """
        super().__init__(timeout, retry_attempts)
        self.logger = get_logger(f"{__name__}.EnhancedSSHConnector")
        
        # BitWarden integration
        self.enable_bitwarden = enable_bitwarden
        self.bitwarden_manager: Optional[BitWardenManager] = None
        
        if enable_bitwarden:
            try:
                self.bitwarden_manager = BitWardenManager()
                self.logger.info("BitWarden integration enabled")
            except Exception as e:
                self.logger.warning(f"BitWarden initialization failed: {e}")
                self.enable_bitwarden = False
    
    def connect_with_bitwarden(self, 
                              host: str,
                              device_type: Optional[str] = None,
                              port: int = 22,
                              device_id: Optional[str] = None,
                              fallback_credentials: Optional[AuthenticationCredentials] = None) -> ConnectionInfo:
        """
        Connect to device using BitWarden credentials.
        
        Args:
            host: Target host IP address or hostname
            device_type: Type of device (router, switch, etc.)
            port: SSH port (default 22)
            device_id: Optional device identifier
            fallback_credentials: Credentials to use if BitWarden fails
            
        Returns:
            ConnectionInfo object with connection details
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            TimeoutError: If connection times out
        """
        if not device_id:
            device_id = f"{host}:{port}"
        
        self.logger.info(f"Attempting BitWarden-enabled SSH connection to {host}:{port}",
                        device_id=device_id)
        
        credentials = None
        
        # Try to get credentials from BitWarden
        if self.enable_bitwarden and self.bitwarden_manager:
            try:
                bw_credential = self.bitwarden_manager.get_device_credentials(host, device_type)
                
                if bw_credential:
                    credentials = AuthenticationCredentials(
                        username=bw_credential.username,
                        password=bw_credential.password,
                        enable_password=bw_credential.enable_password,
                        auth_type=AuthenticationType.PASSWORD
                    )
                    
                    self.logger.info(f"Using BitWarden credentials for {host}",
                                   device_id=device_id,
                                   bitwarden_item=bw_credential.source_item_name)
                else:
                    self.logger.warning(f"No BitWarden credentials found for {host}",
                                      device_id=device_id)
                    
            except BitWardenError as e:
                self.logger.warning(f"BitWarden credential retrieval failed: {e}",
                                  device_id=device_id)
        
        # Use fallback credentials if BitWarden failed
        if not credentials and fallback_credentials:
            credentials = fallback_credentials
            self.logger.info(f"Using fallback credentials for {host}",
                           device_id=device_id)
        
        if not credentials:
            raise AuthenticationError(f"No credentials available for {host}")
        
        # Use the original connection method
        return self.connect(host, credentials, port, device_id)
    
    def connect_with_auto_discovery(self,
                                   host: str,
                                   port: int = 22,
                                   device_id: Optional[str] = None) -> ConnectionInfo:
        """
        Connect to device with automatic credential discovery.
        
        Attempts to automatically determine device type and find appropriate credentials.
        
        Args:
            host: Target host IP address or hostname
            port: SSH port (default 22)
            device_id: Optional device identifier
            
        Returns:
            ConnectionInfo object with connection details
        """
        if not device_id:
            device_id = f"{host}:{port}"
        
        self.logger.info(f"Attempting auto-discovery connection to {host}:{port}",
                        device_id=device_id)
        
        # Try to determine device type from common patterns
        device_type = self._guess_device_type(host)
        
        # Try connection with discovered type
        try:
            return self.connect_with_bitwarden(
                host=host,
                device_type=device_type,
                port=port,
                device_id=device_id
            )
        except AuthenticationError:
            # Try with generic search terms
            return self.connect_with_bitwarden(
                host=host,
                device_type=None,
                port=port,
                device_id=device_id
            )
    
    def _guess_device_type(self, host: str) -> Optional[str]:
        """
        Guess device type based on IP address patterns and common conventions.
        
        Args:
            host: Target host IP address or hostname
            
        Returns:
            Guessed device type or None
        """
        # Common router IP addresses
        router_ips = ['192.168.1.1', '192.168.0.1', '10.0.0.1', '172.16.0.1']
        if host in router_ips:
            return 'router'
        
        # Check for common naming patterns
        hostname_lower = host.lower()
        
        if any(term in hostname_lower for term in ['router', 'gateway', 'rt']):
            return 'router'
        elif any(term in hostname_lower for term in ['switch', 'sw']):
            return 'switch'
        elif any(term in hostname_lower for term in ['firewall', 'fw']):
            return 'firewall'
        elif any(term in hostname_lower for term in ['ap', 'access-point', 'wifi']):
            return 'access_point'
        
        # IP address pattern analysis
        ip_parts = host.split('.')
        if len(ip_parts) == 4:
            try:
                last_octet = int(ip_parts[3])
                
                # Common patterns
                if last_octet == 1:
                    return 'router'  # Usually gateway
                elif 10 <= last_octet <= 50:
                    return 'infrastructure'  # Network infrastructure range
                elif 100 <= last_octet <= 200:
                    return 'server'  # Server range
                    
            except ValueError:
                pass
        
        return None
    
    def test_bitwarden_connection(self) -> Dict[str, Any]:
        """
        Test BitWarden connectivity and return status.
        
        Returns:
            Dictionary with connection status and details
        """
        if not self.enable_bitwarden or not self.bitwarden_manager:
            return {
                'enabled': False,
                'status': 'disabled',
                'message': 'BitWarden integration not enabled'
            }
        
        try:
            vault_status = self.bitwarden_manager.get_vault_status()
            
            result = {
                'enabled': True,
                'authenticated': vault_status.is_authenticated,
                'unlocked': vault_status.is_unlocked,
                'server_url': vault_status.server_url,
                'user_email': vault_status.user_email,
                'last_sync': vault_status.last_sync.isoformat() if vault_status.last_sync else None,
                'total_items': vault_status.total_items
            }
            
            if vault_status.is_authenticated and vault_status.is_unlocked:
                result['status'] = 'ready'
                result['message'] = 'BitWarden vault is ready'
            elif vault_status.is_authenticated:
                result['status'] = 'locked'
                result['message'] = 'BitWarden vault is locked'
            else:
                result['status'] = 'unauthenticated'
                result['message'] = 'BitWarden not authenticated'
            
            return result
            
        except Exception as e:
            return {
                'enabled': True,
                'status': 'error',
                'message': f'BitWarden test failed: {str(e)}'
            }
    
    def get_available_credentials(self, host_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available credentials from BitWarden.
        
        Args:
            host_pattern: Optional pattern to filter credentials
            
        Returns:
            List of available credentials
        """
        if not self.enable_bitwarden or not self.bitwarden_manager:
            return []
        
        try:
            mappings = self.bitwarden_manager.get_all_device_mappings()
            credentials = []
            
            for device_ip, mapping in mappings.items():
                if not host_pattern or host_pattern in device_ip:
                    credentials.append({
                        'device_ip': device_ip,
                        'device_hostname': mapping.device_hostname,
                        'device_type': mapping.device_type,
                        'bitwarden_item_name': mapping.bitwarden_item_name,
                        'credential_type': mapping.credential_type.value,
                        'auto_discovered': mapping.auto_discovered,
                        'last_verified': mapping.last_verified.isoformat() if mapping.last_verified else None
                    })
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to get available credentials: {e}")
            return []
    
    def sync_bitwarden_vault(self) -> bool:
        """
        Synchronize BitWarden vault.
        
        Returns:
            True if sync successful, False otherwise
        """
        if not self.enable_bitwarden or not self.bitwarden_manager:
            return False
        
        try:
            return self.bitwarden_manager.sync_vault()
        except Exception as e:
            self.logger.error(f"BitWarden vault sync failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources including BitWarden manager."""
        super().cleanup() if hasattr(super(), 'cleanup') else None
        
        if self.bitwarden_manager:
            self.bitwarden_manager.cleanup()


class EnhancedConnectionPool(ConnectionPool):
    """Enhanced connection pool with BitWarden integration."""
    
    def __init__(self, max_connections: int = 50, idle_timeout: int = 300,
                 enable_bitwarden: bool = True):
        """Initialize enhanced connection pool.
        
        Args:
            max_connections: Maximum number of concurrent connections
            idle_timeout: Timeout for idle connections in seconds
            enable_bitwarden: Enable BitWarden integration
        """
        super().__init__(max_connections, idle_timeout)
        self.enable_bitwarden = enable_bitwarden
        self.enhanced_connector = None
    
    def _get_connector(self) -> EnhancedSSHConnector:
        """Get enhanced SSH connector instance (lazy initialization)."""
        if self.enhanced_connector is None:
            self.enhanced_connector = EnhancedSSHConnector(
                enable_bitwarden=self.enable_bitwarden
            )
        return self.enhanced_connector
    
    def connect_with_bitwarden(self, host: str, device_type: Optional[str] = None,
                              port: int = 22, device_id: Optional[str] = None) -> ConnectionInfo:
        """Connect using BitWarden credentials with connection pooling."""
        connection_key = f"{host}:{port}"
        
        # Check for existing connection
        if connection_key in self.connections:
            connection = self.connections[connection_key]
            if connection.status == ConnectionStatus.CONNECTED:
                self.logger.debug(f"Reusing existing connection to {host}:{port}")
                return connection
        
        # Create new connection
        connector = self._get_connector()
        connection = connector.connect_with_bitwarden(
            host=host,
            device_type=device_type,
            port=port,
            device_id=device_id
        )
        
        # Store in pool
        if len(self.connections) < self.max_connections:
            self.connections[connection_key] = connection
        
        return connection