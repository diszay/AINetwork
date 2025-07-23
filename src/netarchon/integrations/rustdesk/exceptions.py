"""
RustDesk Integration Exceptions

Custom exception classes for RustDesk integration error handling.
"""

from netarchon.utils.exceptions import NetArchonError


class RustDeskError(NetArchonError):
    """Base exception for RustDesk integration errors."""
    pass


class RustDeskConnectionError(RustDeskError):
    """Raised when RustDesk connection operations fail."""
    
    def __init__(self, message: str = "RustDesk connection failed"):
        super().__init__(message)
        self.error_type = "connection_error"


class RustDeskServerError(RustDeskError):
    """Raised when RustDesk server operations fail."""
    
    def __init__(self, service_name: str, message: str = None):
        if message is None:
            message = f"RustDesk server '{service_name}' operation failed"
        super().__init__(message)
        self.error_type = "server_error"
        self.service_name = service_name


class RustDeskDatabaseError(RustDeskError):
    """Raised when RustDesk database operations fail."""
    
    def __init__(self, operation: str, message: str = None):
        if message is None:
            message = f"RustDesk database operation '{operation}' failed"
        super().__init__(message)
        self.error_type = "database_error"
        self.operation = operation


class RustDeskDeploymentError(RustDeskError):
    """Raised when RustDesk client deployment fails."""
    
    def __init__(self, target_device: str, message: str = None):
        if message is None:
            message = f"RustDesk deployment to '{target_device}' failed"
        super().__init__(message)
        self.error_type = "deployment_error"
        self.target_device = target_device


class RustDeskConfigurationError(RustDeskError):
    """Raised when RustDesk configuration is invalid."""
    
    def __init__(self, config_item: str, message: str = None):
        if message is None:
            message = f"RustDesk configuration '{config_item}' is invalid"
        super().__init__(message)
        self.error_type = "configuration_error"
        self.config_item = config_item


class RustDeskMonitoringError(RustDeskError):
    """Raised when RustDesk monitoring operations fail."""
    
    def __init__(self, monitor_type: str, message: str = None):
        if message is None:
            message = f"RustDesk monitoring '{monitor_type}' failed"
        super().__init__(message)
        self.error_type = "monitoring_error"
        self.monitor_type = monitor_type


class RustDeskSecurityError(RustDeskError):
    """Raised when RustDesk security violations are detected."""
    
    def __init__(self, security_event: str, message: str = None):
        if message is None:
            message = f"RustDesk security event detected: {security_event}"
        super().__init__(message)
        self.error_type = "security_error"
        self.security_event = security_event