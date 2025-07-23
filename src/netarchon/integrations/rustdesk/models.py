"""
RustDesk Integration Data Models

Data structures for RustDesk sessions, devices, connections, and server status.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class ConnectionType(Enum):
    """Types of RustDesk connections."""
    DIRECT = "direct"
    RELAY = "relay"
    P2P = "p2p"
    UNKNOWN = "unknown"


class SessionStatus(Enum):
    """RustDesk session status."""
    ACTIVE = "active"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    PENDING = "pending"


class DeviceStatus(Enum):
    """RustDesk device status."""
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    UNKNOWN = "unknown"


class ServerComponentType(Enum):
    """RustDesk server component types."""
    SIGNAL_SERVER = "hbbs"  # Signal/ID server
    RELAY_SERVER = "hbbr"   # Relay server
    API_SERVER = "api"      # API server (Pro version)


@dataclass
class RustDeskDevice:
    """Represents a RustDesk client device."""
    device_id: str
    device_name: str
    platform: str  # windows, macos, linux, android, ios
    version: str
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    is_online: bool = False
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'RustDeskDevice':
        """Create device from database row."""
        return cls(
            device_id=row.get('id', ''),
            device_name=row.get('name', 'Unknown'),
            platform=row.get('platform', 'unknown'),
            version=row.get('version', ''),
            ip_address=row.get('ip'),
            mac_address=row.get('mac'),
            status=DeviceStatus(row.get('status', 'unknown')),
            last_seen=datetime.fromisoformat(row['last_seen']) if row.get('last_seen') else None,
            is_online=bool(row.get('online', False))
        )


@dataclass
class RustDeskConnection:
    """Represents a RustDesk remote desktop connection."""
    connection_id: str
    from_device_id: str
    to_device_id: str
    from_device_name: str
    to_device_name: str
    connection_type: ConnectionType
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    bytes_transferred: Optional[int] = None
    status: SessionStatus = SessionStatus.PENDING
    remote_ip: Optional[str] = None
    local_ip: Optional[str] = None
    relay_server: Optional[str] = None
    session_quality: Optional[str] = None  # good, fair, poor
    
    @property
    def is_active(self) -> bool:
        """Check if connection is currently active."""
        return self.status in [SessionStatus.ACTIVE, SessionStatus.CONNECTED]
    
    @property
    def duration(self) -> Optional[int]:
        """Get connection duration in seconds."""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        elif self.is_active:
            return int((datetime.now() - self.start_time).total_seconds())
        return self.duration_seconds
    
    @classmethod
    def from_log_entry(cls, log_data: Dict[str, Any]) -> 'RustDeskConnection':
        """Create connection from log entry."""
        return cls(
            connection_id=log_data.get('id', ''),
            from_device_id=log_data.get('from_id', ''),
            to_device_id=log_data.get('to_id', ''),
            from_device_name=log_data.get('from_name', 'Unknown'),
            to_device_name=log_data.get('to_name', 'Unknown'),
            connection_type=ConnectionType(log_data.get('type', 'unknown')),
            start_time=datetime.fromisoformat(log_data['start_time']) if log_data.get('start_time') else datetime.now(),
            end_time=datetime.fromisoformat(log_data['end_time']) if log_data.get('end_time') else None,
            status=SessionStatus(log_data.get('status', 'pending')),
            remote_ip=log_data.get('remote_ip'),
            local_ip=log_data.get('local_ip'),
            relay_server=log_data.get('relay_server')
        )


@dataclass
class RustDeskSession:
    """Represents a complete RustDesk session with multiple connections."""
    session_id: str
    user_id: Optional[str]
    device_id: str
    device_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    connections: List[RustDeskConnection] = field(default_factory=list)
    total_duration: Optional[int] = None
    total_bytes: Optional[int] = None
    session_type: str = "remote_desktop"  # remote_desktop, file_transfer, chat
    
    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return any(conn.is_active for conn in self.connections)
    
    @property
    def duration(self) -> Optional[int]:
        """Get total session duration in seconds."""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        elif self.is_active:
            return int((datetime.now() - self.start_time).total_seconds())
        return self.total_duration
    
    def add_connection(self, connection: RustDeskConnection) -> None:
        """Add a connection to this session."""
        self.connections.append(connection)
    
    def get_active_connections(self) -> List[RustDeskConnection]:
        """Get all active connections in this session."""
        return [conn for conn in self.connections if conn.is_active]


@dataclass
class RustDeskServerComponent:
    """Represents a RustDesk server component."""
    name: str
    component_type: ServerComponentType
    status: str  # running, stopped, error
    pid: Optional[int] = None
    port: Optional[int] = None
    start_time: Optional[datetime] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    connection_count: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class RustDeskServerStatus:
    """Complete RustDesk server status."""
    components: List[RustDeskServerComponent] = field(default_factory=list)
    total_devices: int = 0
    active_connections: int = 0
    total_sessions_today: int = 0
    server_uptime: Optional[int] = None  # seconds
    database_size: Optional[int] = None  # bytes
    log_size: Optional[int] = None  # bytes
    last_updated: Optional[datetime] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if all server components are healthy."""
        return all(
            comp.status == "running" 
            for comp in self.components 
            if comp.component_type in [ServerComponentType.SIGNAL_SERVER, ServerComponentType.RELAY_SERVER]
        )
    
    def get_component(self, component_type: ServerComponentType) -> Optional[RustDeskServerComponent]:
        """Get specific server component."""
        for comp in self.components:
            if comp.component_type == component_type:
                return comp
        return None


@dataclass
class RustDeskNetworkMetrics:
    """Network metrics for RustDesk traffic."""
    timestamp: datetime
    total_connections: int
    active_connections: int
    bytes_per_second: float
    packets_per_second: float
    relay_usage_percent: float
    direct_connection_percent: float
    average_latency_ms: Optional[float] = None
    connection_success_rate: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_connections': self.total_connections,
            'active_connections': self.active_connections,
            'bytes_per_second': self.bytes_per_second,
            'packets_per_second': self.packets_per_second,
            'relay_usage_percent': self.relay_usage_percent,
            'direct_connection_percent': self.direct_connection_percent,
            'average_latency_ms': self.average_latency_ms,
            'connection_success_rate': self.connection_success_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RustDeskNetworkMetrics':
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            total_connections=data['total_connections'],
            active_connections=data['active_connections'],
            bytes_per_second=data['bytes_per_second'],
            packets_per_second=data['packets_per_second'],
            relay_usage_percent=data['relay_usage_percent'],
            direct_connection_percent=data['direct_connection_percent'],
            average_latency_ms=data.get('average_latency_ms'),
            connection_success_rate=data.get('connection_success_rate')
        )


@dataclass
class RustDeskSecurityEvent:
    """Security event detected in RustDesk monitoring."""
    event_id: str
    event_type: str  # failed_auth, unauthorized_access, suspicious_activity
    timestamp: datetime
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    remote_ip: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'device_id': self.device_id,
            'device_name': self.device_name,
            'remote_ip': self.remote_ip,
            'severity': self.severity,
            'description': self.description,
            'details': self.details,
            'resolved': self.resolved
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RustDeskSecurityEvent':
        """Create from dictionary."""
        return cls(
            event_id=data['event_id'],
            event_type=data['event_type'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            device_id=data.get('device_id'),
            device_name=data.get('device_name'),
            remote_ip=data.get('remote_ip'),
            severity=data.get('severity', 'medium'),
            description=data.get('description', ''),
            details=data.get('details', {}),
            resolved=data.get('resolved', False)
        )


@dataclass
class RustDeskDeploymentConfig:
    """Configuration for RustDesk client deployment."""
    server_host: str
    server_port: int = 21116
    key: Optional[str] = None
    relay_servers: List[str] = field(default_factory=list)
    custom_client_name: Optional[str] = None
    auto_login: bool = False
    allow_lan_discovery: bool = True
    enable_file_transfer: bool = True
    enable_audio: bool = True
    enable_tunnel: bool = False
    quality_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_config_json(self) -> str:
        """Convert to RustDesk configuration JSON."""
        config = {
            'host': self.server_host,
            'port': self.server_port,
            'key': self.key,
            'relay-servers': self.relay_servers,
            'custom-rendezvous-server': f"{self.server_host}:{self.server_port}",
            'auto-login': self.auto_login,
            'lan-discovery': self.allow_lan_discovery,
            'file-transfer': self.enable_file_transfer,
            'audio': self.enable_audio,
            'tunnel': self.enable_tunnel
        }
        
        if self.quality_settings:
            config.update(self.quality_settings)
        
        return json.dumps(config, indent=2)