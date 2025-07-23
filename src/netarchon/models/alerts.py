"""
NetArchon Alert Models

Data models for alert management and notification system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(Enum):
    """Types of alerts."""
    DEVICE_DOWN = "device_down"
    DEVICE_UP = "device_up"
    INTERFACE_DOWN = "interface_down"
    INTERFACE_UP = "interface_up"
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    TEMPERATURE_HIGH = "temperature_high"
    THRESHOLD_VIOLATION = "threshold_violation"
    CONNECTIVITY_LOST = "connectivity_lost"
    CONNECTIVITY_RESTORED = "connectivity_restored"
    CONFIGURATION_CHANGED = "configuration_changed"


class AlertStatus(Enum):
    """Alert status values."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Configuration for alert generation rules."""
    rule_id: str
    device_id: str
    metric_name: str
    threshold_value: float
    comparison_operator: str  # >, <, >=, <=, ==, !=
    severity: AlertSeverity
    enabled: bool = True
    description: Optional[str] = None
    notification_channels: Optional[List[str]] = None
    cooldown_minutes: int = 15  # Minimum time between alerts of same type


@dataclass
class Alert:
    """Alert instance data structure."""
    alert_id: str
    device_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    description: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    source_rule_id: Optional[str] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary representation."""
        return {
            'alert_id': self.alert_id,
            'device_id': self.device_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'metric_value': self.metric_value,
            'threshold_value': self.threshold_value,
            'source_rule_id': self.source_rule_id,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create alert from dictionary representation."""
        return cls(
            alert_id=data['alert_id'],
            device_id=data['device_id'],
            alert_type=AlertType(data['alert_type']),
            severity=AlertSeverity(data['severity']),
            message=data['message'],
            description=data['description'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            status=AlertStatus(data['status']),
            metric_value=data.get('metric_value'),
            threshold_value=data.get('threshold_value'),
            source_rule_id=data.get('source_rule_id'),
            acknowledged_by=data.get('acknowledged_by'),
            acknowledged_at=datetime.fromisoformat(data['acknowledged_at']) if data.get('acknowledged_at') else None,
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None,
            metadata=data.get('metadata', {})
        )


@dataclass
class NotificationChannel:
    """Configuration for alert notification channels."""
    channel_id: str
    channel_type: str  # email, webhook, slack, etc.
    name: str
    configuration: Dict[str, Any]
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification channel to dictionary."""
        return {
            'channel_id': self.channel_id,
            'channel_type': self.channel_type,
            'name': self.name,
            'configuration': self.configuration,
            'enabled': self.enabled
        }


@dataclass
class AlertSummary:
    """Summary statistics for alerts."""
    total_alerts: int
    active_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    info_alerts: int
    device_alerts: Dict[str, int]
    alert_types: Dict[str, int]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert summary to dictionary."""
        return {
            'total_alerts': self.total_alerts,
            'active_alerts': self.active_alerts,
            'critical_alerts': self.critical_alerts,
            'high_alerts': self.high_alerts,
            'medium_alerts': self.medium_alerts,
            'low_alerts': self.low_alerts,
            'info_alerts': self.info_alerts,
            'device_alerts': self.device_alerts,
            'alert_types': self.alert_types,
            'last_updated': self.last_updated.isoformat()
        }