"""
Unit tests for NetArchon connection models.
"""

import pytest
from datetime import datetime

from src.netarchon.models.connection import (
    ConnectionType,
    ConnectionStatus,
    ConnectionInfo,
    CommandResult,
    AuthenticationCredentials
)


class TestConnectionType:
    """Test ConnectionType enumeration."""
    
    def test_connection_types(self):
        """Test all connection types are defined."""
        assert ConnectionType.SSH.value == "ssh"
        assert ConnectionType.TELNET.value == "telnet"
        assert ConnectionType.API.value == "api"


class TestConnectionStatus:
    """Test ConnectionStatus enumeration."""
    
    def test_connection_statuses(self):
        """Test all connection statuses are defined."""
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.FAILED.value == "failed"
        assert ConnectionStatus.TIMEOUT.value == "timeout"


class TestConnectionInfo:
    """Test ConnectionInfo dataclass."""
    
    def test_valid_connection_info(self):
        """Test creating valid connection info."""
        now = datetime.utcnow()
        conn = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=now,
            last_activity=now,
            status=ConnectionStatus.CONNECTED
        )
        
        assert conn.device_id == "router1"
        assert conn.host == "192.168.1.1"
        assert conn.port == 22
        assert conn.username == "admin"
        assert conn.connection_type == ConnectionType.SSH
        assert conn.established_at == now
        assert conn.last_activity == now
        assert conn.status == ConnectionStatus.CONNECTED
    
    def test_empty_device_id_validation(self):
        """Test validation for empty device ID."""
        with pytest.raises(ValueError, match="Device ID cannot be empty"):
            ConnectionInfo(
                device_id="",
                host="192.168.1.1",
                port=22,
                username="admin",
                connection_type=ConnectionType.SSH,
                established_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                status=ConnectionStatus.CONNECTED
            )
    
    def test_empty_host_validation(self):
        """Test validation for empty host."""
        with pytest.raises(ValueError, match="Host cannot be empty"):
            ConnectionInfo(
                device_id="router1",
                host="",
                port=22,
                username="admin",
                connection_type=ConnectionType.SSH,
                established_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                status=ConnectionStatus.CONNECTED
            )
    
    def test_invalid_port_validation(self):
        """Test validation for invalid port."""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            ConnectionInfo(
                device_id="router1",
                host="192.168.1.1",
                port=0,
                username="admin",
                connection_type=ConnectionType.SSH,
                established_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                status=ConnectionStatus.CONNECTED
            )
        
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            ConnectionInfo(
                device_id="router1",
                host="192.168.1.1",
                port=65536,
                username="admin",
                connection_type=ConnectionType.SSH,
                established_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                status=ConnectionStatus.CONNECTED
            )
    
    def test_empty_username_validation(self):
        """Test validation for empty username."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            ConnectionInfo(
                device_id="router1",
                host="192.168.1.1",
                port=22,
                username="",
                connection_type=ConnectionType.SSH,
                established_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                status=ConnectionStatus.CONNECTED
            )
    
    def test_is_connected(self):
        """Test is_connected method."""
        conn = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        assert conn.is_connected() is True
        
        conn.status = ConnectionStatus.DISCONNECTED
        assert conn.is_connected() is False
    
    def test_update_activity(self):
        """Test update_activity method."""
        conn = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
        
        old_time = conn.last_activity
        conn.update_activity()
        
        assert conn.last_activity > old_time
    
    def test_set_status(self):
        """Test set_status method."""
        conn = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTING
        )
        
        old_time = conn.last_activity
        conn.set_status(ConnectionStatus.CONNECTED)
        
        assert conn.status == ConnectionStatus.CONNECTED
        assert conn.last_activity > old_time


class TestCommandResult:
    """Test CommandResult dataclass."""
    
    def test_valid_command_result(self):
        """Test creating valid command result."""
        now = datetime.utcnow()
        result = CommandResult(
            success=True,
            output="Version 16.09.04",
            error="",
            execution_time=1.5,
            timestamp=now,
            command="show version",
            device_id="router1"
        )
        
        assert result.success is True
        assert result.output == "Version 16.09.04"
        assert result.error == ""
        assert result.execution_time == 1.5
        assert result.timestamp == now
        assert result.command == "show version"
        assert result.device_id == "router1"
    
    def test_none_values_initialization(self):
        """Test initialization with None values."""
        result = CommandResult(
            success=False,
            output=None,
            error=None,
            execution_time=0.5,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        assert result.output == ""
        assert result.error == ""
    
    def test_has_error(self):
        """Test has_error method."""
        # Success with no error
        result = CommandResult(
            success=True,
            output="OK",
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        assert result.has_error() is False
        
        # Failure
        result.success = False
        assert result.has_error() is True
        
        # Success but with error message
        result.success = True
        result.error = "Warning: something"
        assert result.has_error() is True
    
    def test_get_summary(self):
        """Test get_summary method."""
        result = CommandResult(
            success=True,
            output="OK",
            error="",
            execution_time=1.23,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        summary = result.get_summary()
        assert "SUCCESS" in summary
        assert "show version" in summary
        assert "1.23s" in summary
        
        result.success = False
        summary = result.get_summary()
        assert "FAILED" in summary


class TestAuthenticationCredentials:
    """Test AuthenticationCredentials dataclass."""
    
    def test_valid_password_auth(self):
        """Test creating valid password authentication."""
        creds = AuthenticationCredentials(
            username="admin",
            password="secret123"
        )
        
        assert creds.username == "admin"
        assert creds.password == "secret123"
        assert creds.enable_password is None
        assert creds.private_key_path is None
    
    def test_valid_key_auth(self):
        """Test creating valid key authentication."""
        creds = AuthenticationCredentials(
            username="admin",
            password="",
            private_key_path="/path/to/key"
        )
        
        assert creds.username == "admin"
        assert creds.password == ""
        assert creds.private_key_path == "/path/to/key"
    
    def test_empty_username_validation(self):
        """Test validation for empty username."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            AuthenticationCredentials(
                username="",
                password="secret123"
            )
    
    def test_no_auth_method_validation(self):
        """Test validation when no auth method provided."""
        with pytest.raises(ValueError, match="Either password or private key path must be provided"):
            AuthenticationCredentials(
                username="admin",
                password="",
                private_key_path=""
            )
    
    def test_has_enable_password(self):
        """Test has_enable_password method."""
        creds = AuthenticationCredentials(
            username="admin",
            password="secret123"
        )
        assert creds.has_enable_password() is False
        
        creds.enable_password = "enable123"
        assert creds.has_enable_password() is True
    
    def test_uses_key_auth(self):
        """Test uses_key_auth method."""
        creds = AuthenticationCredentials(
            username="admin",
            password="secret123"
        )
        assert creds.uses_key_auth() is False
        
        creds.private_key_path = "/path/to/key"
        assert creds.uses_key_auth() is True