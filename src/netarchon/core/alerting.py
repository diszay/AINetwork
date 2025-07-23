"""
NetArchon Alerting System

Alert management, processing, and notification system for network monitoring.
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from collections import defaultdict

from ..models.alerts import Alert, AlertRule, AlertSeverity, AlertType, AlertStatus, NotificationChannel, AlertSummary
from ..models.connection import ConnectionInfo
from ..utils.exceptions import MonitoringError
from ..utils.logger import get_logger
from .monitoring import MetricData, MetricType


class AlertManager:
    """Main alert management and processing system."""
    
    def __init__(self, storage_backend: Optional[str] = None):
        """Initialize alert manager.
        
        Args:
            storage_backend: Storage backend for alerts and rules (file, database, etc.)
        """
        self.storage_backend = storage_backend or "memory"
        self.logger = get_logger(f"{__name__}.AlertManager")
        
        # In-memory storage for alerts and rules
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._alert_rules: Dict[str, AlertRule] = {}
        self._notification_channels: Dict[str, NotificationChannel] = {}
        self._alert_cooldowns: Dict[str, datetime] = {}
        
        # Notification handlers
        self._notification_handlers: Dict[str, Callable] = {}
        
        # Setup default notification handlers
        self._setup_default_handlers()
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add or update an alert rule.
        
        Args:
            rule: AlertRule configuration
            
        Returns:
            True if rule was added successfully
        """
        try:
            self._alert_rules[rule.rule_id] = rule
            self.logger.info(f"Added alert rule: {rule.rule_id}",
                           rule_id=rule.rule_id, device_id=rule.device_id, 
                           metric=rule.metric_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add alert rule: {str(e)}", rule_id=rule.rule_id)
            return False
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            True if rule was removed successfully
        """
        try:
            if rule_id in self._alert_rules:
                del self._alert_rules[rule_id]
                self.logger.info(f"Removed alert rule: {rule_id}", rule_id=rule_id)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to remove alert rule: {str(e)}", rule_id=rule_id)
            return False
    
    def process_metrics(self, metrics: List[MetricData]) -> List[Alert]:
        """Process metrics and generate alerts based on configured rules.
        
        Args:
            metrics: List of metrics to process
            
        Returns:
            List of alerts generated from the metrics
        """
        generated_alerts = []
        
        try:
            for metric in metrics:
                # Check threshold violations
                alerts = self._check_threshold_violations(metric)
                generated_alerts.extend(alerts)
                
                # Check for status changes
                status_alerts = self._check_status_changes(metric)
                generated_alerts.extend(status_alerts)
            
            # Process and store generated alerts
            for alert in generated_alerts:
                self._process_alert(alert)
            
            self.logger.debug(f"Processed {len(metrics)} metrics, generated {len(generated_alerts)} alerts",
                            metric_count=len(metrics), alert_count=len(generated_alerts))
            
        except Exception as e:
            self.logger.error(f"Error processing metrics: {str(e)}")
            raise MonitoringError(f"Alert processing failed: {str(e)}") from e
        
        return generated_alerts
    
    def detect_status_changes(self, current_metrics: List[MetricData], 
                            historical_metrics: List[MetricData]) -> List[Alert]:
        """Detect device status changes between current and historical metrics.
        
        Args:
            current_metrics: Current metric values
            historical_metrics: Historical metric values for comparison
            
        Returns:
            List of alerts for detected status changes
        """
        alerts = []
        
        try:
            # Group metrics by device
            current_by_device = defaultdict(list)
            historical_by_device = defaultdict(list)
            
            for metric in current_metrics:
                current_by_device[metric.device_id].append(metric)
            
            for metric in historical_metrics:
                historical_by_device[metric.device_id].append(metric)
            
            # Check for device status changes
            for device_id in current_by_device:
                current_device_metrics = current_by_device[device_id]
                historical_device_metrics = historical_by_device.get(device_id, [])
                
                # Detect interface status changes
                interface_alerts = self._detect_interface_changes(
                    device_id, current_device_metrics, historical_device_metrics
                )
                alerts.extend(interface_alerts)
                
                # Detect connectivity changes
                connectivity_alerts = self._detect_connectivity_changes(
                    device_id, current_device_metrics, historical_device_metrics
                )
                alerts.extend(connectivity_alerts)
            
            self.logger.debug(f"Detected {len(alerts)} status change alerts")
            
        except Exception as e:
            self.logger.error(f"Error detecting status changes: {str(e)}")
            raise MonitoringError(f"Status change detection failed: {str(e)}") from e
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an active alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            acknowledged_by: User or system acknowledging the alert
            
        Returns:
            True if alert was acknowledged successfully
        """
        try:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                
                self.logger.info(f"Alert acknowledged: {alert_id}",
                               alert_id=alert_id, acknowledged_by=acknowledged_by)
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert: {str(e)}", alert_id=alert_id)
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert.
        
        Args:
            alert_id: ID of the alert to resolve
            
        Returns:
            True if alert was resolved successfully
        """
        try:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                
                # Move to history
                self._alert_history.append(alert)
                del self._active_alerts[alert_id]
                
                self.logger.info(f"Alert resolved: {alert_id}", alert_id=alert_id)
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to resolve alert: {str(e)}", alert_id=alert_id)
            return False
    
    def get_active_alerts(self, device_id: Optional[str] = None, 
                         severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts with optional filtering.
        
        Args:
            device_id: Optional filter by device ID
            severity: Optional filter by severity
            
        Returns:
            List of active alerts matching the criteria
        """
        alerts = list(self._active_alerts.values())
        
        if device_id:
            alerts = [alert for alert in alerts if alert.device_id == device_id]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts
    
    def get_alert_summary(self) -> AlertSummary:
        """Get summary statistics for all alerts.
        
        Returns:
            AlertSummary with current statistics
        """
        active_alerts = list(self._active_alerts.values())
        
        # Count by severity
        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1
        
        # Count by device
        device_counts = defaultdict(int)
        for alert in active_alerts:
            device_counts[alert.device_id] += 1
        
        # Count by type
        type_counts = defaultdict(int)
        for alert in active_alerts:
            type_counts[alert.alert_type.value] += 1
        
        return AlertSummary(
            total_alerts=len(active_alerts) + len(self._alert_history),
            active_alerts=len(active_alerts),
            critical_alerts=severity_counts[AlertSeverity.CRITICAL.value],
            high_alerts=severity_counts[AlertSeverity.HIGH.value],
            medium_alerts=severity_counts[AlertSeverity.MEDIUM.value],
            low_alerts=severity_counts[AlertSeverity.LOW.value],
            info_alerts=severity_counts[AlertSeverity.INFO.value],
            device_alerts=dict(device_counts),
            alert_types=dict(type_counts),
            last_updated=datetime.now()
        )
    
    def _check_threshold_violations(self, metric: MetricData) -> List[Alert]:
        """Check if metric violates any configured thresholds."""
        alerts = []
        
        for rule in self._alert_rules.values():
            if (rule.device_id == metric.device_id and 
                rule.metric_name == metric.metric_name and 
                rule.enabled):
                
                # Check cooldown
                cooldown_key = f"{rule.rule_id}_{metric.device_id}"
                if self._is_in_cooldown(cooldown_key, rule.cooldown_minutes):
                    continue
                
                # Check threshold violation
                if self._evaluate_threshold(metric.value, rule.threshold_value, rule.comparison_operator):
                    alert = self._create_threshold_alert(metric, rule)
                    alerts.append(alert)
                    self._set_cooldown(cooldown_key)
        
        return alerts
    
    def _check_status_changes(self, metric: MetricData) -> List[Alert]:
        """Check for status changes in interface metrics."""
        alerts = []
        
        # Check for interface status changes (simplified)
        if metric.metric_type == MetricType.INTERFACE and "status" in metric.metric_name:
            if isinstance(metric.value, str):
                if metric.value.lower() in ["down", "admin-down"]:
                    alert = Alert(
                        alert_id=str(uuid.uuid4()),
                        device_id=metric.device_id,
                        alert_type=AlertType.INTERFACE_DOWN,
                        severity=AlertSeverity.HIGH,
                        message=f"Interface {metric.metric_name} is down",
                        description=f"Interface status changed to {metric.value}",
                        timestamp=metric.timestamp,
                        metadata={"interface": metric.metric_name, "status": metric.value}
                    )
                    alerts.append(alert)
        
        return alerts
    
    def _detect_interface_changes(self, device_id: str, current: List[MetricData], 
                                historical: List[MetricData]) -> List[Alert]:
        """Detect interface status changes."""
        alerts = []
        
        # Simplified interface change detection
        # In production, this would compare interface states
        for metric in current:
            if metric.metric_type == MetricType.INTERFACE:
                # Check for significant changes (placeholder logic)
                pass
        
        return alerts
    
    def _detect_connectivity_changes(self, device_id: str, current: List[MetricData], 
                                   historical: List[MetricData]) -> List[Alert]:
        """Detect device connectivity changes."""
        alerts = []
        
        # Simplified connectivity detection
        # In production, this would check for device reachability changes
        if not current and historical:
            # Device appears to be unreachable
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                device_id=device_id,
                alert_type=AlertType.CONNECTIVITY_LOST,
                severity=AlertSeverity.CRITICAL,
                message=f"Device {device_id} connectivity lost",
                description="No metrics received from device",
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        return alerts
    
    def _create_threshold_alert(self, metric: MetricData, rule: AlertRule) -> Alert:
        """Create alert for threshold violation."""
        return Alert(
            alert_id=str(uuid.uuid4()),
            device_id=metric.device_id,
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=rule.severity,
            message=f"{metric.metric_name} threshold violation",
            description=f"{metric.metric_name} value {metric.value} {rule.comparison_operator} {rule.threshold_value}",
            timestamp=metric.timestamp,
            metric_value=float(metric.value) if isinstance(metric.value, (int, float)) else None,
            threshold_value=rule.threshold_value,
            source_rule_id=rule.rule_id,
            metadata={"metric_type": metric.metric_type.value, "unit": metric.unit}
        )
    
    def _process_alert(self, alert: Alert) -> None:
        """Process and store a generated alert."""
        # Store active alert
        self._active_alerts[alert.alert_id] = alert
        
        # Send notifications
        self._send_notifications(alert)
        
        self.logger.info(f"Alert generated: {alert.alert_type.value}",
                        alert_id=alert.alert_id, device_id=alert.device_id,
                        severity=alert.severity.value)
    
    def _send_notifications(self, alert: Alert) -> None:
        """Send alert notifications through configured channels."""
        try:
            # Get rule-specific notification channels if available
            channels = []
            if alert.source_rule_id and alert.source_rule_id in self._alert_rules:
                rule = self._alert_rules[alert.source_rule_id]
                if rule.notification_channels:
                    channels = rule.notification_channels
            
            # Default to all enabled channels if none specified
            if not channels:
                channels = [ch.channel_id for ch in self._notification_channels.values() if ch.enabled]
            
            # Send notifications
            for channel_id in channels:
                if channel_id in self._notification_channels:
                    self._send_notification(alert, self._notification_channels[channel_id])
        
        except Exception as e:
            self.logger.error(f"Failed to send notifications for alert {alert.alert_id}: {str(e)}")
    
    def _send_notification(self, alert: Alert, channel: NotificationChannel) -> None:
        """Send notification through specific channel."""
        try:
            if channel.channel_type in self._notification_handlers:
                handler = self._notification_handlers[channel.channel_type]
                handler(alert, channel)
            else:
                self.logger.warning(f"No handler for notification channel type: {channel.channel_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to send notification via {channel.channel_id}: {str(e)}")
    
    def _setup_default_handlers(self) -> None:
        """Setup default notification handlers."""
        self._notification_handlers["log"] = self._log_notification_handler
    
    def _log_notification_handler(self, alert: Alert, channel: NotificationChannel) -> None:
        """Default log-based notification handler."""
        self.logger.info(f"ALERT NOTIFICATION: {alert.message}",
                        alert_id=alert.alert_id,
                        device_id=alert.device_id,
                        severity=alert.severity.value,
                        alert_type=alert.alert_type.value)
    
    def _evaluate_threshold(self, value: any, threshold: float, operator: str) -> bool:
        """Evaluate threshold condition."""
        try:
            numeric_value = float(value)
            
            if operator == ">":
                return numeric_value > threshold
            elif operator == "<":
                return numeric_value < threshold
            elif operator == ">=":
                return numeric_value >= threshold
            elif operator == "<=":
                return numeric_value <= threshold
            elif operator == "==":
                return numeric_value == threshold
            elif operator == "!=":
                return numeric_value != threshold
            
            return False
        except (ValueError, TypeError):
            return False
    
    def _is_in_cooldown(self, cooldown_key: str, cooldown_minutes: int) -> bool:
        """Check if alert is in cooldown period."""
        if cooldown_key in self._alert_cooldowns:
            last_alert = self._alert_cooldowns[cooldown_key]
            cooldown_period = timedelta(minutes=cooldown_minutes)
            return datetime.now() - last_alert < cooldown_period
        return False
    
    def _set_cooldown(self, cooldown_key: str) -> None:
        """Set cooldown timestamp for alert type."""
        self._alert_cooldowns[cooldown_key] = datetime.now()