"""
Unit tests for NetArchon exception classes.
"""

import pytest
from src.netarchon.utils.exceptions import (
    NetArchonError,
    ConnectionError,
    AuthenticationError,
    TimeoutError,
    CommandExecutionError,
    PrivilegeError,
    ConfigurationError,
    ValidationError,
    RollbackError,
    DeviceError,
    UnsupportedDeviceError,
    MonitoringError,
    DataCollectionError
)


class TestNetArchonError:
    """Test base NetArchonError class."""
    
    def test_basic_exception(self):
        """Test basic exception creation."""
        error = NetArchonError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}
    
    def test_exception_with_details(self):
        """Test exception with details."""
        details = {"device": "router1", "port": 22}
        error = NetArchonError("Connection failed", details)
        assert error.message == "Connection failed"
        assert error.details == details
        assert "Connection failed - Details:" in str(error)
    
    def test_exception_inheritance(self):
        """Test exception inheritance."""
        error = NetArchonError("Test")
        assert isinstance(error, Exception)


class TestConnectionErrors:
    """Test connection-related exceptions."""
    
    def test_connection_error(self):
        """Test ConnectionError."""
        error = ConnectionError("SSH connection failed")
        assert isinstance(error, NetArchonError)
        assert str(error) == "SSH connection failed"
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        assert isinstance(error, ConnectionError)
        assert isinstance(error, NetArchonError)
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Connection timeout")
        assert isinstance(error, ConnectionError)


class TestCommandErrors:
    """Test command execution exceptions."""
    
    def test_command_execution_error(self):
        """Test CommandExecutionError."""
        error = CommandExecutionError("Command failed")
        assert isinstance(error, NetArchonError)
    
    def test_privilege_error(self):
        """Test PrivilegeError."""
        error = PrivilegeError("Insufficient privileges")
        assert isinstance(error, CommandExecutionError)


class TestConfigurationErrors:
    """Test configuration-related exceptions."""
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config error")
        assert isinstance(error, NetArchonError)
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid config syntax")
        assert isinstance(error, ConfigurationError)
    
    def test_rollback_error(self):
        """Test RollbackError."""
        error = RollbackError("Rollback failed")
        assert isinstance(error, ConfigurationError)


class TestDeviceErrors:
    """Test device-related exceptions."""
    
    def test_device_error(self):
        """Test DeviceError."""
        error = DeviceError("Device detection failed")
        assert isinstance(error, NetArchonError)
    
    def test_unsupported_device_error(self):
        """Test UnsupportedDeviceError."""
        error = UnsupportedDeviceError("Unknown device type")
        assert isinstance(error, DeviceError)


class TestMonitoringErrors:
    """Test monitoring-related exceptions."""
    
    def test_monitoring_error(self):
        """Test MonitoringError."""
        error = MonitoringError("Monitoring failed")
        assert isinstance(error, NetArchonError)
    
    def test_data_collection_error(self):
        """Test DataCollectionError."""
        error = DataCollectionError("Failed to collect metrics")
        assert isinstance(error, MonitoringError)