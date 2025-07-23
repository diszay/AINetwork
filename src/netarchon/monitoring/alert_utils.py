"""
Alert Management Utilities

Utility functions and helper classes for the intelligent alerting system.
"""

from typing import Dict, List, Any
from netarchon.monitoring.alert_manager import (
    EnhancedAlertManager, NotificationConfig, NotificationChannel,
    EmailNotificationHandler, WebhookNotificationHandler, 
    StreamlitNotificationHandler, SlackNotificationHandler
)
from netarchon.monitoring.storage_manager import MetricStorageManager


def create_alert_manager(storage_manager: MetricStorageManager,
                        notification_configs: List[NotificationConfig] = None) -> EnhancedAlertManager:
    """Create a configured alert manager instance."""
    alert_manager = EnhancedAlertManager(storage_manager)
    
    if notification_configs:
        for config in notification_configs:
            if config.channel == NotificationChannel.EMAIL:
                handler = EmailNotificationHandler(config)
            elif config.channel == NotificationChannel.WEBHOOK:
                handler = WebhookNotificationHandler(config)
            elif config.channel == NotificationChannel.STREAMLIT:
                handler = StreamlitNotificationHandler(config)
            elif config.channel == NotificationChannel.SLACK:
                handler = SlackNotificationHandler(config)
            else:
                continue
            
            alert_manager.add_notification_handler(handler)
    
    return alert_manager


def create_default_notification_configs() -> List[NotificationConfig]:
    """Create default notification configurations for home network."""
    return [
        NotificationConfig(
            channel=NotificationChannel.STREAMLIT,
            enabled=True,
            streamlit_session_state_key="netarchon_alerts"
        ),
        NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=False,  # Disabled by default, user needs to configure
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            rate_limit_minutes=10,
            max_notifications_per_period=5
        )
    ]


def create_home_network_alert_rules() -> Dict[str, Dict[str, Any]]:
    """Create default alert rule configurations for home network devices."""
    return {
        "connectivity_rules": {
            "device_offline": {
                "name": "Device Offline",
                "description": "Alert when a device becomes unreachable",
                "metric_type": "connectivity",
                "metric_name": "reachable",
                "operator": "equals",
                "threshold": False,
                "severity": "warning",
                "evaluation_window_minutes": 5,
                "consecutive_breaches_required": 2,
                "cooldown_minutes": 15
            },
            "high_latency": {
                "name": "High Network Latency",
                "description": "Alert when network latency is high",
                "metric_type": "latency",
                "metric_name": "ping_latency",
                "operator": "greater_than",
                "threshold": 100.0,
                "severity": "warning",
                "evaluation_window_minutes": 3,
                "consecutive_breaches_required": 3
            }
        },
        "docsis_rules": {
            "low_snr": {
                "name": "DOCSIS Low SNR",
                "description": "Alert when DOCSIS SNR is too low",
                "device_filter": ["arris_s33"],
                "metric_type": "docsis",
                "metric_name": "snr",
                "operator": "less_than",
                "threshold": 30.0,
                "severity": "critical"
            },
            "power_anomaly": {
                "name": "DOCSIS Power Anomaly",
                "description": "Alert when DOCSIS power levels are anomalous",
                "device_filter": ["arris_s33"],
                "metric_type": "docsis",
                "operator": "anomaly_detection",
                "severity": "warning"
            }
        },
        "system_rules": {
            "high_cpu": {
                "name": "High CPU Usage",
                "description": "Alert when CPU usage is consistently high",
                "device_filter": ["mini_pc_server"],
                "metric_type": "system_resources",
                "metric_name": "cpu_usage",
                "operator": "greater_than",
                "threshold": 85.0,
                "severity": "warning"
            },
            "high_memory": {
                "name": "High Memory Usage",
                "description": "Alert when memory usage is critically high",
                "device_filter": ["mini_pc_server"],
                "metric_type": "system_resources",
                "metric_name": "memory_usage",
                "operator": "greater_than",
                "threshold": 90.0,
                "severity": "critical"
            },
            "low_disk_space": {
                "name": "Low Disk Space",
                "description": "Alert when disk space is running low",
                "device_filter": ["mini_pc_server"],
                "metric_type": "system_resources",
                "metric_name": "disk_usage",
                "operator": "greater_than",
                "threshold": 85.0,
                "severity": "warning"
            }
        },
        "wifi_rules": {
            "weak_backhaul": {
                "name": "Weak Mesh Backhaul",
                "description": "Alert when mesh backhaul signal is weak",
                "device_filter": ["netgear_orbi_satellite_1", "netgear_orbi_satellite_2"],
                "metric_type": "wifi_mesh",
                "metric_name": "backhaul_signal",
                "operator": "less_than",
                "threshold": -70.0,
                "severity": "warning"
            }
        },
        "security_rules": {
            "security_event": {
                "name": "Security Event Detected",
                "description": "Alert on security-related events",
                "metric_type": "security",
                "operator": "not_equals",
                "threshold": "normal",
                "severity": "critical",
                "auto_resolve": False
            }
        },
        "bandwidth_rules": {
            "high_usage": {
                "name": "High Bandwidth Usage",
                "description": "Alert when bandwidth usage is unusually high",
                "device_filter": ["xfinity_gateway"],
                "metric_type": "bandwidth",
                "operator": "anomaly_detection",
                "severity": "info"
            }
        }
    }


def get_alert_severity_color(severity: str) -> str:
    """Get color code for alert severity."""
    colors = {
        'info': '#17a2b8',
        'warning': '#ffc107', 
        'critical': '#dc3545',
        'emergency': '#6f42c1'
    }
    return colors.get(severity.lower(), '#6c757d')


def format_alert_message(alert_data: Dict[str, Any]) -> str:
    """Format alert data into a readable message."""
    return (f"{alert_data.get('severity', 'UNKNOWN').upper()} Alert: "
            f"{alert_data.get('rule_name', 'Unknown Rule')} - "
            f"{alert_data.get('device_name', 'Unknown Device')} - "
            f"{alert_data.get('message', 'No message')}")


def calculate_alert_priority_score(alert_data: Dict[str, Any]) -> int:
    """Calculate priority score for alert sorting."""
    severity_scores = {
        'emergency': 100,
        'critical': 75,
        'warning': 50,
        'info': 25
    }
    
    base_score = severity_scores.get(alert_data.get('severity', 'info'), 25)
    
    # Adjust based on device importance
    device_multipliers = {
        'mini_pc_server': 1.5,
        'arris_s33': 1.3,
        'xfinity_gateway': 1.2,
        'netgear_orbi_router': 1.1
    }
    
    device_id = alert_data.get('device_id', '')
    multiplier = device_multipliers.get(device_id, 1.0)
    
    return int(base_score * multiplier)


def group_related_alerts(alerts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group related alerts by correlation group or device."""
    groups = {}
    
    for alert in alerts:
        # Group by correlation group if available
        correlation_group = alert.get('correlation_group')
        if correlation_group:
            if correlation_group not in groups:
                groups[correlation_group] = []
            groups[correlation_group].append(alert)
        else:
            # Group by device
            device_id = alert.get('device_id', 'unknown')
            if device_id not in groups:
                groups[device_id] = []
            groups[device_id].append(alert)
    
    return groups


def generate_alert_summary(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics for a list of alerts."""
    if not alerts:
        return {
            'total_alerts': 0,
            'by_severity': {},
            'by_device': {},
            'active_count': 0,
            'resolved_count': 0
        }
    
    # Count by severity
    severity_counts = {}
    for alert in alerts:
        severity = alert.get('severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Count by device
    device_counts = {}
    for alert in alerts:
        device = alert.get('device_name', 'Unknown')
        device_counts[device] = device_counts.get(device, 0) + 1
    
    # Count by status
    active_count = len([a for a in alerts if a.get('status') == 'active'])
    resolved_count = len([a for a in alerts if a.get('status') == 'resolved'])
    
    return {
        'total_alerts': len(alerts),
        'by_severity': severity_counts,
        'by_device': device_counts,
        'active_count': active_count,
        'resolved_count': resolved_count,
        'most_common_severity': max(severity_counts.items(), key=lambda x: x[1])[0] if severity_counts else None,
        'most_affected_device': max(device_counts.items(), key=lambda x: x[1])[0] if device_counts else None
    }