"""
NetArchon Exception Classes

Comprehensive exception hierarchy for NetArchon operations.
"""


class NetArchonError(Exception):
    """Base exception for all NetArchon errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ConnectionError(NetArchonError):
    """SSH connection related errors."""
    pass


class AuthenticationError(ConnectionError):
    """Authentication failures."""
    pass


class TimeoutError(ConnectionError):
    """Connection or operation timeout errors."""
    pass


class CommandExecutionError(NetArchonError):
    """Command execution related errors."""
    pass


class PrivilegeError(CommandExecutionError):
    """Privilege escalation errors."""
    pass


class ConfigurationError(NetArchonError):
    """Configuration management related errors."""
    pass


class ValidationError(ConfigurationError):
    """Configuration validation errors."""
    pass


class RollbackError(ConfigurationError):
    """Configuration rollback errors."""
    pass


class DeviceError(NetArchonError):
    """Device detection and management related errors."""
    pass


class UnsupportedDeviceError(DeviceError):
    """Unsupported device type errors."""
    pass


class MonitoringError(NetArchonError):
    """Monitoring and metrics collection errors."""
    pass


class DataCollectionError(MonitoringError):
    """Data collection failures."""
    pass