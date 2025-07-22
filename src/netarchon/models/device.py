"""
NetArchon Device Models

Data structures for network devices, types, and status information.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional


class DeviceType(Enum):
    """Network device types."""
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    JUNIPER_JUNOS = "juniper_junos"
    ARISTA_EOS = "arista_eos"
    GENERIC = "generic"


class DeviceStatus(Enum):
    """Device operational status."""
    ONLINE = "online"
    OFFLINE = "offline"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """Network device information."""
    hostname: str
    ip_address: str
    device_type: DeviceType
    vendor: str
    model: str
    os_version: str
    last_seen: datetime
    status: DeviceStatus
    
    def __post_init__(self):
        """Validate device info after initialization."""
        if not self.hostname:
            raise ValueError("Hostname cannot be empty")
        if not self.ip_address:
            raise ValueError("IP address cannot be empty")
    
    def is_online(self) -> bool:
        """Check if device is online."""
        return self.status == DeviceStatus.ONLINE
    
    def update_status(self, status: DeviceStatus) -> None:
        """Update device status and last seen time."""
        self.status = status
        self.last_seen = datetime.utcnow()


@dataclass
class DeviceProfile:
    """Device-specific profile with capabilities and command syntax."""
    device_type: DeviceType
    vendor: str
    model: str
    os_version: str
    capabilities: List[str]
    command_syntax: Dict[str, str]
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.capabilities:
            self.capabilities = []
        if not self.command_syntax:
            self.command_syntax = {}
    
    def has_capability(self, capability: str) -> bool:
        """Check if device has specific capability."""
        return capability in self.capabilities
    
    def get_command(self, command_type: str) -> Optional[str]:
        """Get device-specific command syntax."""
        return self.command_syntax.get(command_type)
    
    def add_capability(self, capability: str) -> None:
        """Add capability to device profile."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    def set_command_syntax(self, command_type: str, syntax: str) -> None:
        """Set command syntax for specific command type."""
        self.command_syntax[command_type] = syntax