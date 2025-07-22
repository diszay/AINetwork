"""
NetArchon Connection Models

Data structures for SSH connections and related information.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ConnectionType(Enum):
    """Connection type enumeration."""
    SSH = "ssh"
    TELNET = "telnet"
    API = "api"


class ConnectionStatus(Enum):
    """Connection status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ConnectionInfo:
    """SSH connection information."""
    device_id: str
    host: str
    port: int
    username: str
    connection_type: ConnectionType
    established_at: datetime
    last_activity: datetime
    status: ConnectionStatus
    
    def __post_init__(self):
        """Validate connection info after initialization."""
        if not self.device_id:
            raise ValueError("Device ID cannot be empty")
        if not self.host:
            raise ValueError("Host cannot be empty")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        if not self.username:
            raise ValueError("Username cannot be empty")
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.status == ConnectionStatus.CONNECTED
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def set_status(self, status: ConnectionStatus) -> None:
        """Update connection status."""
        self.status = status
        self.update_activity()


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    output: str
    error: str
    execution_time: float
    timestamp: datetime
    command: str
    device_id: str
    
    def __post_init__(self):
        """Initialize default values."""
        if self.output is None:
            self.output = ""
        if self.error is None:
            self.error = ""
    
    def has_error(self) -> bool:
        """Check if command execution had errors."""
        return not self.success or bool(self.error)
    
    def get_summary(self) -> str:
        """Get summary of command execution."""
        status = "SUCCESS" if self.success else "FAILED"
        return f"{status}: {self.command} ({self.execution_time:.2f}s)"


@dataclass
class AuthenticationCredentials:
    """Authentication credentials for device connections."""
    username: str
    password: str
    enable_password: Optional[str] = None
    private_key_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        if not self.username:
            raise ValueError("Username cannot be empty")
        if not self.password and not self.private_key_path:
            raise ValueError("Either password or private key path must be provided")
    
    def has_enable_password(self) -> bool:
        """Check if enable password is available."""
        return bool(self.enable_password)
    
    def uses_key_auth(self) -> bool:
        """Check if using key-based authentication."""
        return bool(self.private_key_path)