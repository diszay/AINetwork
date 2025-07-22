"""
Unit tests for NetArchon SSH connector.
"""

import socket
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest
import paramiko

from src.netarchon.core.ssh_connector import SSHConnector, ConnectionPool
from src.netarchon.models.connection import (
    ConnectionInfo,
    ConnectionType,
    ConnectionStatus,
    AuthenticationCredentials
)
from src.netarchon.utils.exceptions import (
    ConnectionError,
    AuthenticationError,
    TimeoutError
)


class TestSSHConnector:
    """Test SSHConnector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.connector = SSHConnector(timeout=10, retry_attempts=2)
        self.credentials = AuthenticationCredentials(
            username="admin",
            password="secret123"
        )
        self.key_credentials = AuthenticationCredentials(
            username="admin",
            password="",
            private_key_path="/path/to/key"
        )
    
    def test_connector_initialization(self):
        """Test SSH connector initialization."""
        connector = SSHConnector(timeout=30, retry_attempts=5)
        assert connector.timeout == 30
        assert connector.retry_attempts == 5
        assert connector.logger is not None
    
    def test_default_initialization(self):
        """Test SSH connector with default parameters."""
        connector = SSHConnector()
        assert connector.timeout == 30
        assert connector.retry_attempts == 3
    
    @patch('paramiko.SSHClient')
    def test_successful_connection(self, mock_ssh_client_class):
        """Test successful SSH connection."""
        # Setup mock
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        
        # Execute
        connection = self.connector.connect("192.168.1.1", self.credentials)
        
        # Verify
        assert isinstance(connection, ConnectionInfo)
        assert connection.host == "192.168.1.1"
        assert connection.port == 22
        assert connection.username == "admin"
        assert connection.connection_type == ConnectionType.SSH
        assert connection.status == ConnectionStatus.CONNECTED
        assert connection.device_id == "192.168.1.1:22"
        
        # Verify SSH client calls
        mock_ssh_client.set_missing_host_key_policy.assert_called_once()
        mock_ssh_client.connect.assert_called_once_with(
            hostname="192.168.1.1",
            port=22,
            username="admin",
            password="secret123",
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
    
    @patch('paramiko.SSHClient')
    def test_connection_with_custom_port_and_device_id(self, mock_ssh_client_class):
        """Test connection with custom port and device ID."""
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        
        connection = self.connector.connect(
            "192.168.1.1", 
            self.credentials, 
            port=2222, 
            device_id="router1"
        )
        
        assert connection.port == 2222
        assert connection.device_id == "router1"
        
        mock_ssh_client.connect.assert_called_once_with(
            hostname="192.168.1.1",
            port=2222,
            username="admin",
            password="secret123",
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
    
    @patch('paramiko.SSHClient')
    def test_key_based_authentication(self, mock_ssh_client_class):
        """Test SSH connection with key-based authentication."""
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        
        connection = self.connector.connect("192.168.1.1", self.key_credentials)
        
        mock_ssh_client.connect.assert_called_once_with(
            hostname="192.168.1.1",
            port=22,
            username="admin",
            key_filename="/path/to/key",
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
    
    @patch('paramiko.SSHClient')
    def test_authentication_failure(self, mock_ssh_client_class):
        """Test authentication failure handling."""
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        
        with pytest.raises(AuthenticationError) as exc_info:
            self.connector.connect("192.168.1.1", self.credentials)
        
        assert "Authentication failed for 192.168.1.1:22" in str(exc_info.value)
        assert exc_info.value.details["host"] == "192.168.1.1"
        assert exc_info.value.details["port"] == 22
        assert exc_info.value.details["username"] == "admin"
        
        mock_ssh_client.close.assert_called_once()
    
    @patch('paramiko.SSHClient')
    @patch('time.sleep')
    def test_connection_timeout_with_retry(self, mock_sleep, mock_ssh_client_class):
        """Test connection timeout with retry logic."""
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.side_effect = socket.timeout("Connection timed out")
        
        with pytest.raises(TimeoutError) as exc_info:
            self.connector.connect("192.168.1.1", self.credentials)
        
        assert "Connection to 192.168.1.1:22 timed out after 2 attempts" in str(exc_info.value)
        assert exc_info.value.details["timeout"] == 10
        
        # Verify retry attempts
        assert mock_ssh_client.connect.call_count == 2
        assert mock_ssh_client.close.call_count == 2
        mock_sleep.assert_called_once_with(2)  # First retry delay
    
    @patch('paramiko.SSHClient')
    @patch('time.sleep')
    def test_connection_error_with_retry(self, mock_sleep, mock_ssh_client_class):
        """Test connection error with retry logic."""
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.side_effect = socket.error("Connection refused")
        
        with pytest.raises(ConnectionError) as exc_info:
            self.connector.connect("192.168.1.1", self.credentials)
        
        assert "Failed to connect to 192.168.1.1:22 after 2 attempts" in str(exc_info.value)
        assert exc_info.value.details["attempts"] == 2
        
        # Verify retry attempts
        assert mock_ssh_client.connect.call_count == 2
        mock_sleep.assert_called_once_with(2)
    
    @patch('paramiko.SSHClient')
    def test_successful_connection_after_retry(self, mock_ssh_client_class):
        """Test successful connection after initial failure."""
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        
        # First attempt fails, second succeeds
        mock_ssh_client.connect.side_effect = [
            socket.error("Connection refused"),
            None  # Success
        ]
        
        with patch('time.sleep'):
            connection = self.connector.connect("192.168.1.1", self.credentials)
        
        assert connection.status == ConnectionStatus.CONNECTED
        assert mock_ssh_client.connect.call_count == 2
    
    def test_disconnect_success(self):
        """Test successful disconnection."""
        # Create connection with mock SSH client
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        mock_ssh_client = Mock()
        connection._ssh_client = mock_ssh_client
        
        self.connector.disconnect(connection)
        
        mock_ssh_client.close.assert_called_once()
        assert connection.status == ConnectionStatus.DISCONNECTED
        assert connection._ssh_client is None
    
    def test_disconnect_no_client(self):
        """Test disconnection when no SSH client exists."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        # No exception should be raised
        self.connector.disconnect(connection)
    
    def test_disconnect_with_error(self):
        """Test disconnection with error handling."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        mock_ssh_client = Mock()
        mock_ssh_client.close.side_effect = Exception("Close error")
        connection._ssh_client = mock_ssh_client
        
        # Should not raise exception
        self.connector.disconnect(connection)
        assert connection._ssh_client is None
    
    def test_is_connected_true(self):
        """Test is_connected returns True for active connection."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        mock_transport = Mock()
        mock_transport.is_active.return_value = True
        
        mock_ssh_client = Mock()
        mock_ssh_client.get_transport.return_value = mock_transport
        connection._ssh_client = mock_ssh_client
        
        assert self.connector.is_connected(connection) is True
    
    def test_is_connected_false_status(self):
        """Test is_connected returns False for disconnected status."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.DISCONNECTED
        )
        
        assert self.connector.is_connected(connection) is False
    
    def test_is_connected_no_client(self):
        """Test is_connected returns False when no SSH client."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        result = self.connector.is_connected(connection)
        
        assert result is False
        assert connection.status == ConnectionStatus.DISCONNECTED
    
    def test_is_connected_inactive_transport(self):
        """Test is_connected returns False for inactive transport."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        mock_transport = Mock()
        mock_transport.is_active.return_value = False
        
        mock_ssh_client = Mock()
        mock_ssh_client.get_transport.return_value = mock_transport
        connection._ssh_client = mock_ssh_client
        
        result = self.connector.is_connected(connection)
        
        assert result is False
        assert connection.status == ConnectionStatus.DISCONNECTED
    
    def test_test_connection_success(self):
        """Test successful connection test."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        # Mock SSH client and command execution
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"test"
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, None)
        mock_ssh_client.get_transport.return_value.is_active.return_value = True
        
        connection._ssh_client = mock_ssh_client
        
        result = self.connector.test_connection(connection)
        
        assert result is True
        mock_ssh_client.exec_command.assert_called_once_with('echo "test"', timeout=10)
    
    def test_test_connection_not_connected(self):
        """Test connection test when not connected."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.DISCONNECTED
        )
        
        result = self.connector.test_connection(connection)
        assert result is False
    
    def test_test_connection_unexpected_output(self):
        """Test connection test with unexpected output."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"unexpected"
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, None)
        mock_ssh_client.get_transport.return_value.is_active.return_value = True
        
        connection._ssh_client = mock_ssh_client
        
        result = self.connector.test_connection(connection)
        assert result is False
    
    def test_test_connection_exception(self):
        """Test connection test with exception."""
        connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.side_effect = Exception("Command failed")
        mock_ssh_client.get_transport.return_value.is_active.return_value = True
        
        connection._ssh_client = mock_ssh_client
        
        result = self.connector.test_connection(connection)
        
        assert result is False
        assert connection.status == ConnectionStatus.FAILED


class TestConnectionPool:
    """Test ConnectionPool class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pool = ConnectionPool(max_connections=3, idle_timeout=60)
        self.credentials = AuthenticationCredentials(
            username="admin",
            password="secret123"
        )
    
    def test_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(max_connections=10, idle_timeout=120)
        assert pool.max_connections == 10
        assert pool.idle_timeout == 120
        assert len(pool.connections) == 0
        assert pool.connector is None
        assert pool.logger is not None
    
    def test_default_pool_initialization(self):
        """Test connection pool with default parameters."""
        pool = ConnectionPool()
        assert pool.max_connections == 50
        assert pool.idle_timeout == 300
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_get_connection_new(self, mock_ssh_connector_class):
        """Test getting a new connection."""
        # Setup mock
        mock_connector = Mock()
        mock_connection = Mock(spec=ConnectionInfo)
        mock_connection.device_id = "router1"
        mock_connector.connect.return_value = mock_connection
        mock_ssh_connector_class.return_value = mock_connector
        
        # Execute
        connection = self.pool.get_connection(
            "router1", "192.168.1.1", self.credentials
        )
        
        # Verify
        assert connection == mock_connection
        assert "router1" in self.pool.connections
        assert len(self.pool.connections) == 1
        
        mock_connector.connect.assert_called_once_with(
            "192.168.1.1", self.credentials, 22, "router1"
        )
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_get_connection_reuse_existing(self, mock_ssh_connector_class):
        """Test reusing an existing connection."""
        # Setup mock
        mock_connector = Mock()
        mock_connection = Mock(spec=ConnectionInfo)
        mock_connection.device_id = "router1"
        mock_connector.connect.return_value = mock_connection
        mock_connector.is_connected.return_value = True
        mock_ssh_connector_class.return_value = mock_connector
        
        # Add connection to pool
        self.pool.connections["router1"] = mock_connection
        
        # Execute
        connection = self.pool.get_connection(
            "router1", "192.168.1.1", self.credentials
        )
        
        # Verify
        assert connection == mock_connection
        mock_connector.is_connected.assert_called_once_with(mock_connection)
        mock_connection.update_activity.assert_called_once()
        # Should not create new connection
        mock_connector.connect.assert_not_called()
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_get_connection_replace_stale(self, mock_ssh_connector_class):
        """Test replacing a stale connection."""
        # Setup mock
        mock_connector = Mock()
        old_connection = Mock(spec=ConnectionInfo)
        old_connection.device_id = "router1"
        new_connection = Mock(spec=ConnectionInfo)
        new_connection.device_id = "router1"
        
        mock_connector.is_connected.return_value = False
        mock_connector.connect.return_value = new_connection
        mock_ssh_connector_class.return_value = mock_connector
        
        # Add stale connection to pool
        self.pool.connections["router1"] = old_connection
        
        # Execute
        connection = self.pool.get_connection(
            "router1", "192.168.1.1", self.credentials
        )
        
        # Verify
        assert connection == new_connection
        assert self.pool.connections["router1"] == new_connection
        mock_connector.is_connected.assert_called_once_with(old_connection)
        mock_connector.connect.assert_called_once()
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_get_connection_max_limit_reached(self, mock_ssh_connector_class):
        """Test connection limit enforcement."""
        # Setup mock
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        
        # Fill pool to maximum
        for i in range(3):
            mock_conn = Mock(spec=ConnectionInfo)
            mock_conn.device_id = f"router{i}"
            self.pool.connections[f"router{i}"] = mock_conn
        
        # Mock cleanup to not remove any connections
        with patch.object(self.pool, 'cleanup_idle_connections'):
            with pytest.raises(ConnectionError) as exc_info:
                self.pool.get_connection(
                    "router3", "192.168.1.4", self.credentials
                )
        
        assert "Maximum connections (3) reached" in str(exc_info.value)
        assert exc_info.value.details["current_connections"] == 3
    
    def test_release_connection_existing(self):
        """Test releasing an existing connection."""
        mock_connection = Mock(spec=ConnectionInfo)
        mock_connection.device_id = "router1"
        self.pool.connections["router1"] = mock_connection
        
        self.pool.release_connection("router1")
        
        mock_connection.update_activity.assert_called_once()
        assert "router1" in self.pool.connections  # Should still be in pool
    
    def test_release_connection_nonexistent(self):
        """Test releasing a non-existent connection."""
        # Should not raise exception
        self.pool.release_connection("nonexistent")
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_close_connection(self, mock_ssh_connector_class):
        """Test closing a specific connection."""
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        
        mock_connection = Mock(spec=ConnectionInfo)
        mock_connection.device_id = "router1"
        self.pool.connections["router1"] = mock_connection
        
        self.pool.close_connection("router1")
        
        mock_connector.disconnect.assert_called_once_with(mock_connection)
        assert "router1" not in self.pool.connections
    
    def test_close_connection_nonexistent(self):
        """Test closing a non-existent connection."""
        # Should not raise exception
        self.pool.close_connection("nonexistent")
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_cleanup_idle_connections(self, mock_ssh_connector_class):
        """Test cleanup of idle connections."""
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        
        # Create connections with different activity times
        old_time = datetime.utcnow() - timedelta(seconds=120)  # 2 minutes ago
        recent_time = datetime.utcnow() - timedelta(seconds=30)  # 30 seconds ago
        
        old_connection = Mock(spec=ConnectionInfo)
        old_connection.device_id = "old_router"
        old_connection.last_activity = old_time
        
        recent_connection = Mock(spec=ConnectionInfo)
        recent_connection.device_id = "recent_router"
        recent_connection.last_activity = recent_time
        
        self.pool.connections["old_router"] = old_connection
        self.pool.connections["recent_router"] = recent_connection
        
        self.pool.cleanup_idle_connections()
        
        # Old connection should be removed, recent should remain
        assert "old_router" not in self.pool.connections
        assert "recent_router" in self.pool.connections
        mock_connector.disconnect.assert_called_once_with(old_connection)
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_close_all_connections(self, mock_ssh_connector_class):
        """Test closing all connections."""
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        
        # Add multiple connections
        for i in range(3):
            mock_conn = Mock(spec=ConnectionInfo)
            mock_conn.device_id = f"router{i}"
            self.pool.connections[f"router{i}"] = mock_conn
        
        self.pool.close_all_connections()
        
        assert len(self.pool.connections) == 0
        assert mock_connector.disconnect.call_count == 3
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_get_pool_status(self, mock_ssh_connector_class):
        """Test getting pool status."""
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        
        # Add connections with different states
        active_conn = Mock(spec=ConnectionInfo)
        inactive_conn = Mock(spec=ConnectionInfo)
        
        mock_connector.is_connected.side_effect = lambda conn: conn == active_conn
        
        self.pool.connections["active"] = active_conn
        self.pool.connections["inactive"] = inactive_conn
        
        status = self.pool.get_pool_status()
        
        assert status["total_connections"] == 2
        assert status["active_connections"] == 1
        assert status["max_connections"] == 3
        assert status["idle_timeout"] == 60
        assert set(status["connection_ids"]) == {"active", "inactive"}
    
    def test_remove_connection(self):
        """Test internal _remove_connection method."""
        mock_connection = Mock(spec=ConnectionInfo)
        self.pool.connections["router1"] = mock_connection
        
        self.pool._remove_connection("router1")
        
        assert "router1" not in self.pool.connections
    
    def test_remove_connection_nonexistent(self):
        """Test removing non-existent connection."""
        # Should not raise exception
        self.pool._remove_connection("nonexistent")