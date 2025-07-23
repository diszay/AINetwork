"""
Intelligent Alerting System

Advanced alerting system with complex rule support, alert correlation for home network topology,
notification channels (email, webhook, Streamlit), and predictive alerting based on usage patterns.
"""

import asyncio
import smtplib
import threading
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import re
import statistics
from pathlib import Path

from netarchon.utils.logger import get_logger
from netarchon.monitoring.concurrent_collector import MetricData, DeviceType, MetricType
from netarchon.monitoring.storage_manager import MetricStorageManager, QueryFilter
from netarchon.integrations.rustdesk.home_network_integration import RustDeskHomeNetworkMonitor


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    STREAMLIT = "streamlit"
    SLACK = "slack"
    DISCORD = "discord"


class RuleOperator(Enum):
    """Rule comparison operators."""
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    REGEX_MATCH = "regex"
    THRESHOLD_BREACH = "threshold"
    ANOMALY_DETECTION = "anomaly"


@dataclass
class AlertRule:
    """Individual alert rule configuration."""
    rule_id: str
    name: str
    description: str
    device_filter: Optional[List[str]] = None  # Device IDs
    metric_type_filter: Optional[List[MetricType]] = None
    metric_name_filter: Optional[List[str]] = None
    operator: RuleOperator = RuleOperator.GREATER_THAN
    threshold_value: Optional[Union[float, str]] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    
    # Advanced rule options
    evaluation_window_minutes: int = 5
    consecutive_breaches_required: int = 1
    cooldown_minutes: int = 30
    auto_resolve: bool = True
    auto_resolve_minutes: int = 60
    
    # Correlation settings
    correlation_group: Optional[str] = None
    dependency_rules: List[str] = field(default_factory=list)
    
    # Notification settings
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    custom_message_template: Optional[str] = None
@da
taclass
class Alert:
    """Individual alert instance."""
    alert_id: str
    rule_id: str
    rule_name: str
    device_id: str
    device_name: str
    metric_type: MetricType
    metric_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    
    # Alert timing
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    # Alert context
    current_value: Any = None
    threshold_value: Any = None
    breach_count: int = 1
    correlation_group: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    notification_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for storage/transmission."""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'metric_type': self.metric_type.value,
            'metric_name': self.metric_name,
            'severity': self.severity.value,
            'status': self.status.value,
            'message': self.message,
            'triggered_at': self.triggered_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'breach_count': self.breach_count,
            'correlation_group': self.correlation_group,
            'metadata': self.metadata,
            'notification_history': self.notification_history
        }


@dataclass
class NotificationConfig:
    """Notification channel configuration."""
    channel: NotificationChannel
    enabled: bool = True
    
    # Email configuration
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    
    # Webhook configuration
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = field(default_factory=dict)
    webhook_auth_token: Optional[str] = None
    
    # Streamlit configuration
    streamlit_session_state_key: str = "alerts"
    
    # Rate limiting
    rate_limit_minutes: int = 5
    max_notifications_per_period: int = 10


@dataclass
class BaselineData:
    """Baseline data for anomaly detection."""
    device_id: str
    metric_type: MetricType
    metric_name: str
    
    # Statistical baselines
    mean_value: float
    std_deviation: float
    min_value: float
    max_value: float
    percentile_95: float
    percentile_99: float
    
    # Time-based patterns
    hourly_patterns: Dict[int, float] = field(default_factory=dict)  # Hour -> average value
    daily_patterns: Dict[int, float] = field(default_factory=dict)   # Day of week -> average
    
    # Metadata
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0  # 0-1 confidence in baseline accuracy


class PredictiveModel:
    """Simple predictive model for anomaly detection."""
    
    def __init__(self, sensitivity: float = 2.0):
        self.sensitivity = sensitivity  # Standard deviations for anomaly threshold
        self.logger = get_logger("PredictiveModel")
    
    def is_anomaly(self, current_value: float, baseline: BaselineData, 
                   current_time: datetime = None) -> Tuple[bool, float]:
        """Detect if current value is anomalous based on baseline."""
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Basic statistical anomaly detection
            if baseline.std_deviation == 0:
                return False, 0.0
            
            z_score = abs(current_value - baseline.mean_value) / baseline.std_deviation
            is_anomaly = z_score > self.sensitivity
            
            # Time-based pattern analysis
            hour = current_time.hour
            day_of_week = current_time.weekday()
            
            # Check hourly pattern deviation
            if hour in baseline.hourly_patterns:
                expected_hourly = baseline.hourly_patterns[hour]
                hourly_deviation = abs(current_value - expected_hourly) / (baseline.std_deviation + 0.001)
                
                if hourly_deviation > self.sensitivity:
                    is_anomaly = True
                    z_score = max(z_score, hourly_deviation)
            
            # Check daily pattern deviation
            if day_of_week in baseline.daily_patterns:
                expected_daily = baseline.daily_patterns[day_of_week]
                daily_deviation = abs(current_value - expected_daily) / (baseline.std_deviation + 0.001)
                
                if daily_deviation > self.sensitivity:
                    is_anomaly = True
                    z_score = max(z_score, daily_deviation)
            
            return is_anomaly, z_score
            
        except Exception as e:
            self.logger.error(f"Error in anomaly detection: {e}")
            return False, 0.0
    
    def predict_next_value(self, baseline: BaselineData, 
                          future_time: datetime) -> Tuple[float, float]:
        """Predict next value and confidence interval."""
        try:
            # Simple prediction based on time patterns
            hour = future_time.hour
            day_of_week = future_time.weekday()
            
            predicted_value = baseline.mean_value
            
            # Adjust based on hourly pattern
            if hour in baseline.hourly_patterns:
                predicted_value = baseline.hourly_patterns[hour]
            
            # Adjust based on daily pattern
            if day_of_week in baseline.daily_patterns:
                daily_factor = baseline.daily_patterns[day_of_week] / baseline.mean_value
                predicted_value *= daily_factor
            
            # Confidence interval (2 standard deviations)
            confidence_interval = 2 * baseline.std_deviation
            
            return predicted_value, confidence_interval
            
        except Exception as e:
            self.logger.error(f"Error in prediction: {e}")
            return baseline.mean_value, baseline.std_deviation * 2class Noti
ficationHandler:
    """Base class for notification handlers."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = get_logger(f"NotificationHandler-{config.channel.value}")
        self._rate_limiter = {}
    
    async def send_notification(self, alert: Alert) -> Dict[str, Any]:
        """Send notification for alert."""
        # Check rate limiting
        if not self._check_rate_limit(alert):
            return {
                'success': False,
                'error': 'Rate limit exceeded',
                'channel': self.config.channel.value
            }
        
        try:
            result = await self._send_notification_impl(alert)
            self._update_rate_limiter(alert)
            return result
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel': self.config.channel.value
            }
    
    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if notification is within rate limits."""
        key = f"{alert.device_id}_{alert.rule_id}"
        current_time = datetime.now()
        
        if key not in self._rate_limiter:
            self._rate_limiter[key] = []
        
        # Clean old entries
        cutoff_time = current_time - timedelta(minutes=self.config.rate_limit_minutes)
        self._rate_limiter[key] = [
            timestamp for timestamp in self._rate_limiter[key]
            if timestamp > cutoff_time
        ]
        
        # Check if under limit
        return len(self._rate_limiter[key]) < self.config.max_notifications_per_period
    
    def _update_rate_limiter(self, alert: Alert):
        """Update rate limiter after successful notification."""
        key = f"{alert.device_id}_{alert.rule_id}"
        if key not in self._rate_limiter:
            self._rate_limiter[key] = []
        self._rate_limiter[key].append(datetime.now())
    
    async def _send_notification_impl(self, alert: Alert) -> Dict[str, Any]:
        """Implementation-specific notification sending."""
        raise NotImplementedError


class EmailNotificationHandler(NotificationHandler):
    """Email notification handler."""
    
    async def _send_notification_impl(self, alert: Alert) -> Dict[str, Any]:
        """Send email notification."""
        if not self.config.email_to:
            return {'success': False, 'error': 'No email recipients configured'}
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from or self.config.smtp_username
            msg['To'] = ', '.join(self.config.email_to)
            msg['Subject'] = f"NetArchon Alert: {alert.severity.value.upper()} - {alert.rule_name}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                
                server.send_message(msg)
            
            return {
                'success': True,
                'channel': 'email',
                'recipients': self.config.email_to,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'channel': 'email'}
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body."""
        severity_colors = {
            AlertSeverity.INFO: '#17a2b8',
            AlertSeverity.WARNING: '#ffc107',
            AlertSeverity.CRITICAL: '#dc3545',
            AlertSeverity.EMERGENCY: '#6f42c1'
        }
        
        color = severity_colors.get(alert.severity, '#6c757d')
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color}; margin-top: 0;">
                    {alert.severity.value.upper()} Alert: {alert.rule_name}
                </h2>
                
                <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa; font-weight: bold;">Device</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{alert.device_name} ({alert.device_id})</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa; font-weight: bold;">Metric</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{alert.metric_type.value} - {alert.metric_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa; font-weight: bold;">Current Value</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{alert.current_value}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa; font-weight: bold;">Threshold</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{alert.threshold_value}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa; font-weight: bold;">Triggered At</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Message:</strong><br>
                    {alert.message}
                </div>
                
                <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                    This alert was generated by NetArchon monitoring system.<br>
                    Alert ID: {alert.alert_id}
                </p>
            </div>
        </body>
        </html>
        """


class WebhookNotificationHandler(NotificationHandler):
    """Webhook notification handler."""
    
    async def _send_notification_impl(self, alert: Alert) -> Dict[str, Any]:
        """Send webhook notification."""
        if not self.config.webhook_url:
            return {'success': False, 'error': 'No webhook URL configured'}
        
        try:
            # Prepare webhook payload
            payload = {
                'alert': alert.to_dict(),
                'timestamp': datetime.now().isoformat(),
                'source': 'netarchon-alert-manager'
            }
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                **self.config.webhook_headers
            }
            
            if self.config.webhook_auth_token:
                headers['Authorization'] = f'Bearer {self.config.webhook_auth_token}'
            
            # Send webhook
            response = requests.post(
                self.config.webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            
            return {
                'success': True,
                'channel': 'webhook',
                'status_code': response.status_code,
                'response': response.text[:500],  # Limit response size
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'channel': 'webhook'}


class StreamlitNotificationHandler(NotificationHandler):
    """Streamlit notification handler."""
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self._streamlit_alerts = []
    
    async def _send_notification_impl(self, alert: Alert) -> Dict[str, Any]:
        """Add alert to Streamlit session state."""
        try:
            # Add to internal buffer
            self._streamlit_alerts.append(alert)
            
            # Keep only recent alerts (last 100)
            if len(self._streamlit_alerts) > 100:
                self._streamlit_alerts = self._streamlit_alerts[-100:]
            
            # Try to update Streamlit session state if available
            try:
                import streamlit as st
                if hasattr(st, 'session_state'):
                    if self.config.streamlit_session_state_key not in st.session_state:
                        st.session_state[self.config.streamlit_session_state_key] = []
                    
                    st.session_state[self.config.streamlit_session_state_key].append(alert.to_dict())
                    
                    # Keep only recent alerts in session state
                    if len(st.session_state[self.config.streamlit_session_state_key]) > 50:
                        st.session_state[self.config.streamlit_session_state_key] = \
                            st.session_state[self.config.streamlit_session_state_key][-50:]
            except ImportError:
                pass  # Streamlit not available
            
            return {
                'success': True,
                'channel': 'streamlit',
                'alert_count': len(self._streamlit_alerts),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'channel': 'streamlit'}
    
    def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts for Streamlit display."""
        return self._streamlit_alerts[-limit:] if self._streamlit_alerts else []


class SlackNotificationHandler(NotificationHandler):
    """Slack notification handler."""
    
    async def _send_notification_impl(self, alert: Alert) -> Dict[str, Any]:
        """Send Slack notification."""
        if not self.config.webhook_url:
            return {'success': False, 'error': 'No Slack webhook URL configured'}
        
        try:
            # Create Slack message
            severity_colors = {
                AlertSeverity.INFO: '#36a64f',
                AlertSeverity.WARNING: '#ff9500',
                AlertSeverity.CRITICAL: '#ff0000',
                AlertSeverity.EMERGENCY: '#800080'
            }
            
            color = severity_colors.get(alert.severity, '#808080')
            
            payload = {
                'attachments': [{
                    'color': color,
                    'title': f'{alert.severity.value.upper()} Alert: {alert.rule_name}',
                    'fields': [
                        {'title': 'Device', 'value': f'{alert.device_name} ({alert.device_id})', 'short': True},
                        {'title': 'Metric', 'value': f'{alert.metric_type.value} - {alert.metric_name}', 'short': True},
                        {'title': 'Current Value', 'value': str(alert.current_value), 'short': True},
                        {'title': 'Threshold', 'value': str(alert.threshold_value), 'short': True},
                        {'title': 'Time', 'value': alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S'), 'short': True}
                    ],
                    'text': alert.message,
                    'footer': 'NetArchon Alert Manager',
                    'ts': int(alert.triggered_at.timestamp())
                }]
            }
            
            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            
            return {
                'success': True,
                'channel': 'slack',
                'status_code': response.status_code,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'channel': 'slack'}class E
nhancedAlertManager:
    """
    Advanced alert management system with complex rule support, correlation,
    predictive alerting, and multiple notification channels.
    """
    
    def __init__(self, storage_manager: MetricStorageManager, 
                 rustdesk_monitor: RustDeskHomeNetworkMonitor = None):
        self.storage_manager = storage_manager
        self.rustdesk_monitor = rustdesk_monitor or RustDeskHomeNetworkMonitor()
        self.logger = get_logger("EnhancedAlertManager")
        
        # Alert management
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Notification system
        self.notification_handlers: Dict[NotificationChannel, NotificationHandler] = {}
        
        # Predictive system
        self.predictive_model = PredictiveModel()
        self.baselines: Dict[str, BaselineData] = {}
        
        # Correlation system
        self.correlation_groups: Dict[str, List[str]] = {}  # group -> alert_ids
        
        # Background processing
        self._running = False
        self._evaluation_thread = None
        self._baseline_thread = None
        
        # Rule breach tracking
        self._breach_counters: Dict[str, Dict[str, int]] = {}  # rule_id -> device_id -> count
        self._last_evaluations: Dict[str, datetime] = {}
        
        # Initialize default rules for home network
        self._initialize_default_rules()
    
    def add_notification_handler(self, handler: NotificationHandler):
        """Add a notification handler."""
        self.notification_handlers[handler.config.channel] = handler
        self.logger.info(f"Added notification handler: {handler.config.channel.value}")
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.rule_id] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
        
        # Initialize breach counter
        if rule.rule_id not in self._breach_counters:
            self._breach_counters[rule.rule_id] = {}
    
    def remove_rule(self, rule_id: str):
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            if rule_id in self._breach_counters:
                del self._breach_counters[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")
    
    def start_monitoring(self):
        """Start alert monitoring and evaluation."""
        if self._running:
            return
        
        self._running = True
        
        # Start rule evaluation thread
        self._evaluation_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
        self._evaluation_thread.start()
        
        # Start baseline update thread
        self._baseline_thread = threading.Thread(target=self._baseline_loop, daemon=True)
        self._baseline_thread.start()
        
        self.logger.info("Alert monitoring started")
    
    def stop_monitoring(self):
        """Stop alert monitoring."""
        self._running = False
        
        if self._evaluation_thread:
            self._evaluation_thread.join(timeout=10)
        
        if self._baseline_thread:
            self._baseline_thread.join(timeout=10)
        
        self.logger.info("Alert monitoring stopped")
    
    def _evaluation_loop(self):
        """Main alert evaluation loop."""
        while self._running:
            try:
                current_time = datetime.now()
                
                # Evaluate each rule
                for rule_id, rule in self.rules.items():
                    if not rule.enabled:
                        continue
                    
                    # Check if it's time to evaluate this rule
                    last_eval = self._last_evaluations.get(rule_id, datetime.min)
                    if (current_time - last_eval).total_seconds() < (rule.evaluation_window_minutes * 60):
                        continue
                    
                    try:
                        self._evaluate_rule(rule, current_time)
                        self._last_evaluations[rule_id] = current_time
                    except Exception as e:
                        self.logger.error(f"Failed to evaluate rule {rule_id}: {e}")
                
                # Check for auto-resolution
                self._check_auto_resolution(current_time)
                
                # Sleep for 30 seconds before next evaluation cycle
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in evaluation loop: {e}")
                time.sleep(60)
    
    def _evaluate_rule(self, rule: AlertRule, current_time: datetime):
        """Evaluate a single alert rule."""
        try:
            # Query recent metrics for this rule
            filter_criteria = QueryFilter(
                device_ids=rule.device_filter,
                metric_types=rule.metric_type_filter,
                metric_names=rule.metric_name_filter,
                start_time=current_time - timedelta(minutes=rule.evaluation_window_minutes),
                end_time=current_time,
                limit=1000
            )
            
            metrics = self.storage_manager.query_metrics(filter_criteria)
            
            # Group metrics by device
            device_metrics = {}
            for metric in metrics:
                if metric.device_id not in device_metrics:
                    device_metrics[metric.device_id] = []
                device_metrics[metric.device_id].append(metric)
            
            # Evaluate rule for each device
            for device_id, device_metric_list in device_metrics.items():
                if not device_metric_list:
                    continue
                
                # Get latest metric for evaluation
                latest_metric = max(device_metric_list, key=lambda m: m.timestamp)
                
                # Evaluate rule condition
                is_breach = self._evaluate_rule_condition(rule, latest_metric)
                
                if is_breach:
                    self._handle_rule_breach(rule, latest_metric, current_time)
                else:
                    self._handle_rule_normal(rule, device_id, current_time)
                    
        except Exception as e:
            self.logger.error(f"Failed to evaluate rule {rule.rule_id}: {e}")
    
    def _evaluate_rule_condition(self, rule: AlertRule, metric: MetricData) -> bool:
        """Evaluate if a metric breaches the rule condition."""
        try:
            current_value = metric.value
            threshold = rule.threshold_value
            
            if rule.operator == RuleOperator.GREATER_THAN:
                return float(current_value) > float(threshold)
            
            elif rule.operator == RuleOperator.LESS_THAN:
                return float(current_value) < float(threshold)
            
            elif rule.operator == RuleOperator.EQUALS:
                return str(current_value) == str(threshold)
            
            elif rule.operator == RuleOperator.NOT_EQUALS:
                return str(current_value) != str(threshold)
            
            elif rule.operator == RuleOperator.CONTAINS:
                return str(threshold) in str(current_value)
            
            elif rule.operator == RuleOperator.REGEX_MATCH:
                return bool(re.search(str(threshold), str(current_value)))
            
            elif rule.operator == RuleOperator.ANOMALY_DETECTION:
                return self._evaluate_anomaly_condition(rule, metric)
            
            else:
                self.logger.warning(f"Unknown operator: {rule.operator}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to evaluate rule condition: {e}")
            return False
    
    def _evaluate_anomaly_condition(self, rule: AlertRule, metric: MetricData) -> bool:
        """Evaluate anomaly detection condition."""
        try:
            baseline_key = f"{metric.device_id}_{metric.metric_type.value}_{metric.metric_name}"
            
            if baseline_key not in self.baselines:
                return False  # No baseline available
            
            baseline = self.baselines[baseline_key]
            
            # Check if current value is anomalous
            is_anomaly, z_score = self.predictive_model.is_anomaly(
                float(metric.value), baseline, metric.timestamp
            )
            
            return is_anomaly
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate anomaly condition: {e}")
            return False
    
    def _handle_rule_breach(self, rule: AlertRule, metric: MetricData, current_time: datetime):
        """Handle a rule breach."""
        device_id = metric.device_id
        
        # Update breach counter
        if device_id not in self._breach_counters[rule.rule_id]:
            self._breach_counters[rule.rule_id][device_id] = 0
        
        self._breach_counters[rule.rule_id][device_id] += 1
        breach_count = self._breach_counters[rule.rule_id][device_id]
        
        # Check if we have enough consecutive breaches
        if breach_count >= rule.consecutive_breaches_required:
            # Check if alert already exists and is in cooldown
            alert_key = f"{rule.rule_id}_{device_id}"
            
            if alert_key in self.active_alerts:
                existing_alert = self.active_alerts[alert_key]
                
                # Check cooldown period
                time_since_trigger = (current_time - existing_alert.triggered_at).total_seconds() / 60
                if time_since_trigger < rule.cooldown_minutes:
                    return  # Still in cooldown
                
                # Update existing alert
                existing_alert.breach_count = breach_count
                existing_alert.current_value = metric.value
                existing_alert.last_updated = current_time
                
            else:
                # Create new alert
                alert = self._create_alert(rule, metric, breach_count, current_time)
                self.active_alerts[alert_key] = alert
                self.alert_history.append(alert)
                
                # Send notifications
                asyncio.create_task(self._send_alert_notifications(alert))
                
                self.logger.info(f"Alert triggered: {alert.rule_name} for {alert.device_name}")
    
    def _handle_rule_normal(self, rule: AlertRule, device_id: str, current_time: datetime):
        """Handle when rule condition is normal (not breached)."""
        # Reset breach counter
        if device_id in self._breach_counters.get(rule.rule_id, {}):
            self._breach_counters[rule.rule_id][device_id] = 0
        
        # Check for auto-resolution
        alert_key = f"{rule.rule_id}_{device_id}"
        if alert_key in self.active_alerts and rule.auto_resolve:
            alert = self.active_alerts[alert_key]
            
            # Check if enough time has passed for auto-resolution
            time_since_trigger = (current_time - alert.triggered_at).total_seconds() / 60
            if time_since_trigger >= rule.auto_resolve_minutes:
                self._resolve_alert(alert_key, current_time, "Auto-resolved: condition returned to normal")
    
    def _create_alert(self, rule: AlertRule, metric: MetricData, 
                     breach_count: int, current_time: datetime) -> Alert:
        """Create a new alert."""
        alert_id = f"{rule.rule_id}_{metric.device_id}_{int(current_time.timestamp())}"
        
        # Create custom message if template provided
        if rule.custom_message_template:
            message = rule.custom_message_template.format(
                device_name=metric.device_name,
                metric_name=metric.metric_name,
                current_value=metric.value,
                threshold_value=rule.threshold_value,
                breach_count=breach_count
            )
        else:
            message = (f"{metric.metric_name} on {metric.device_name} is {metric.value} "
                      f"(threshold: {rule.threshold_value})")
        
        return Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            device_id=metric.device_id,
            device_name=metric.device_name,
            metric_type=metric.metric_type,
            metric_name=metric.metric_name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=message,
            triggered_at=current_time,
            current_value=metric.value,
            threshold_value=rule.threshold_value,
            breach_count=breach_count,
            correlation_group=rule.correlation_group,
            metadata=metric.metadata
        )
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        rule = self.rules.get(alert.rule_id)
        if not rule:
            return
        
        notification_results = []
        
        for channel in rule.notification_channels:
            if channel in self.notification_handlers:
                handler = self.notification_handlers[channel]
                try:
                    result = await handler.send_notification(alert)
                    notification_results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to send {channel.value} notification: {e}")
                    notification_results.append({
                        'success': False,
                        'error': str(e),
                        'channel': channel.value
                    })
        
        # Update alert with notification history
        alert.notification_history.extend(notification_results)
        
        self.logger.info(f"Sent {len(notification_results)} notifications for alert {alert.alert_id}")
    
    def _check_auto_resolution(self, current_time: datetime):
        """Check for alerts that should be auto-resolved."""
        alerts_to_resolve = []
        
        for alert_key, alert in self.active_alerts.items():
            rule = self.rules.get(alert.rule_id)
            if not rule or not rule.auto_resolve:
                continue
            
            # Check if alert has been active long enough for auto-resolution
            time_since_trigger = (current_time - alert.triggered_at).total_seconds() / 60
            if time_since_trigger >= rule.auto_resolve_minutes:
                alerts_to_resolve.append((alert_key, "Auto-resolved: timeout reached"))
        
        # Resolve alerts
        for alert_key, reason in alerts_to_resolve:
            self._resolve_alert(alert_key, current_time, reason)
    
    def _resolve_alert(self, alert_key: str, resolved_time: datetime, reason: str):
        """Resolve an active alert."""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = resolved_time
            alert.last_updated = resolved_time
            alert.metadata['resolution_reason'] = reason
            
            del self.active_alerts[alert_key]
            
            self.logger.info(f"Alert resolved: {alert.rule_name} for {alert.device_name} - {reason}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an active alert."""
        for alert_key, alert in self.active_alerts.items():
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                alert.last_updated = datetime.now()
                alert.metadata['acknowledged_by'] = acknowledged_by
                
                self.logger.info(f"Alert acknowledged: {alert.rule_name} by {acknowledged_by}")
                return True
        
        return False
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get all active alerts."""
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [alert for alert in alerts if alert.severity == severity_filter]
        
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)
    
    def get_alert_history(self, hours_back: int = 24, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        filtered_alerts = [
            alert for alert in self.alert_history
            if alert.triggered_at >= cutoff_time
        ]
        
        return sorted(filtered_alerts, key=lambda a: a.triggered_at, reverse=True)[:limit] 
   def _baseline_loop(self):
        """Background loop to update baselines for anomaly detection."""
        while self._running:
            try:
                self._update_baselines()
                
                # Update baselines every hour
                time.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in baseline loop: {e}")
                time.sleep(600)  # Wait 10 minutes before retry
    
    def _update_baselines(self):
        """Update statistical baselines for anomaly detection."""
        try:
            # Get metrics from last 7 days for baseline calculation
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            filter_criteria = QueryFilter(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            metrics = self.storage_manager.query_metrics(filter_criteria)
            
            # Group metrics by device, type, and name
            metric_groups = {}
            for metric in metrics:
                key = f"{metric.device_id}_{metric.metric_type.value}_{metric.metric_name}"
                if key not in metric_groups:
                    metric_groups[key] = []
                metric_groups[key].append(metric)
            
            # Calculate baselines for each group
            for key, metric_list in metric_groups.items():
                if len(metric_list) < 10:  # Need minimum data points
                    continue
                
                try:
                    baseline = self._calculate_baseline(metric_list)
                    self.baselines[key] = baseline
                except Exception as e:
                    self.logger.error(f"Failed to calculate baseline for {key}: {e}")
            
            self.logger.info(f"Updated {len(self.baselines)} baselines")
            
        except Exception as e:
            self.logger.error(f"Failed to update baselines: {e}")
    
    def _calculate_baseline(self, metrics: List[MetricData]) -> BaselineData:
        """Calculate baseline statistics for a metric series."""
        if not metrics:
            raise ValueError("No metrics provided for baseline calculation")
        
        # Extract numeric values
        numeric_values = []
        for metric in metrics:
            try:
                numeric_values.append(float(metric.value))
            except (ValueError, TypeError):
                continue
        
        if len(numeric_values) < 5:
            raise ValueError("Insufficient numeric data for baseline")
        
        # Calculate basic statistics
        mean_value = statistics.mean(numeric_values)
        std_deviation = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
        min_value = min(numeric_values)
        max_value = max(numeric_values)
        
        # Calculate percentiles
        sorted_values = sorted(numeric_values)
        percentile_95 = so  ]      )
  
  r_period=5_peonsnotificati  max_       s=10,
   minuteate_limit_   r       7,
  port=58tp_         sm",
   l.com"smtp.gmair=mtp_serve      sgure
      o confir needs tlt, useauef by dsabled Di=False,  #ed  enabl
          EMAIL,l.annecationChifihannel=Not      c
      nfig(icationCo       Notif    ),
 
    "chon_alerts"netare_key=taton_sssilit_se   stream         rue,
led=T      enab     MLIT,
 nnel.STREAhaificationCannel=Not ch           nfig(
ficationCo Noti       n [
tur re
   ""etwork."or home n ftionsn configura notificatioeate default """Cr]:
   nConfigtioficat[Noti) -> Lisnfigs(ion_cootificatefault_ne_def creatager


dalert_man
    return 
    dler)hanion_handler(ificat_notager.add  alert_man                   
nue
     conti        lse:
          e
        dler(config)onHanificatiNotdler = Slack   han         SLACK:
    el.onChannificatil == Notonfig.channe      elif c      g)
fir(conionHandleatotific= StreamlitNdler         hanT:
        AMLIREonChannel.STcatifi == Notinnelconfig.cha   elif          fig)
onandler(cionHficatbhookNotidler = Wehan             
   .WEBHOOK:eltionChannfical == Notiig.channeelif conf           fig)
 nHandler(conificatioailNotndler = Em       ha      IL:
   hannel.EMAficationC == Notiig.channel if conf   
        n_configs:atiog in notificfor confi
        ion_configs:notificat  if )
    
  nagerrage_maager(stoManlerthancedAger = Ent_mana aler."""
   tance manager insred alertte a configu""Crea   "er:
 dAlertManaghance) -> EnNoneonfig] = nCtificatiost[Noconfigs: Lification_    noti                   
 geManager,ricStoraager: Mettorage_man(sgeralert_manaate_def crenagement
t ma alerions fory funct Utilit)


#ng(orinitp_mosto    self."
    xit.""anager eontext m""C "       exc_tb):
xc_val, xc_type, e, eelft__(s   def __exi
    
 eturn self     ring()
   t_monitorstar   self."
     "er entry."ntext manag  """Co     lf):
 se__enter__(def   
    
            })
  rror': str(e       'e        se,
 ': Fal    'success        rn {
    tu         re")
   erts: {e}export aliled to Fa.error(f" self.logger
            as e:tionxcept Excep    e
                 
    }              }'
 mat_typermat: {ford forte': f'Unsuppoor'err                    ': False,
ccess      'su        {
           return            
se:         el   
         }
                 (alerts)
  ennt': l'cou               
     (),valueutput.get   'data': o          
        'csv',mat':'for                    e,
uccess': Tru          's         turn {
           re     
               dict())
  alert.to_erow(iter.writwr                    :
    rtslet in a for aler                         
            ader()
  iter.writehe wr            
       s)mednaes=fielldnamput, fietWriter(outic csv.D    writer =             .keys()
   o_dict()alerts[0].t = dnames       fiel           ts:
  if aler               )
 tringIO(put = io.S   out              
            
     import io             csv
      import            sv':
= 'c.lower() =typermat_   elif fo
            
              }    
       (alerts): lencount'          '       erts],
   ert in alict() for al_d [alert.to 'data':                ',
    'jsonat':orm  'f                  s': True,
    'succes                n {
urret         ':
       == 'jsone.lower() _typ format       if    
         =1000)
    imitack, lrs_bk=houurs_bacry(hoalert_histo self.get_s =lert          atry:
        s."""
  mat fora in various datlert""Export a
        ", Any]:[str 24) -> Dictnt = is_back:'json', hour: str = ypeormat_ts(self, frt export_ale
    defn {}
    ur         ret)
   e}"stics: { alert statito getf"Failed or(logger.errself.         
   tion as e:t Excep       excep    
           }
       at()
   oform.isrrent_timemestamp': cu    'ti         ',
   stoppedng else 'f._runnig' if selnin 'runng_status':itori        'mon     ),
   s()ndlers.key_haication.notift(selflislers': ation_hand'notific          
       },         0
       selines elseelf.ba) if snesself.baseli/ len()) nes.values(selif.bafor b in selce_score enfid: sum(b.conidence'g_conf    'av               s),
 .baselinelen(selfselines': ba 'total_          {
         ines': sel      'ba         le_stats,
 istics': rule_stat        'rus,
        devicetop_': ng_devicesop_alerti          't
      },          
      by_severityry_istoerity': hby_sev        '           istory),
 t_h(recenl_24h': lenta         'to        {
   story': nt_hi     'rece          },
              everity
   ve_by_s actiy_severity':      'b       
       ve_alerts),en(self.acti  'total': l              ts': {
    tive_aler         'ac        return {
                
  
             }        rity.value
': rule.seve  'severity              led,
     rule.enabbled':       'ena          ts),
   aleren(rule_d': ls_triggereertal      '              e] = {
le.nams[rurule_stat              id]
  = rule_le_id =lert.rustory if aent_hiecin r for alert ts = [alertle_aler      ru         
 s():temself.rules.irule in or rule_id,        f {}
     tats =    rule_s
        nessle effective # Ru  
                   ue)[:5]
  erse=Trx: x[1], revey=lambda .items(), kountsrt_cdevice_aleted(ces = sor  top_devi          
          0) + 1
   vice_name,(alert.degetlert_counts. device_avice_name] =t.de[alerntsrt_couale   device_           ory:
  nt_histrt in receor ale         f
   counts = {}ert_evice_al           ds
 icealerting devp # To              
              ])
 
            severityity ==lert.sever    if a       y
         cent_histor reor alert in alert f                n([
    levalue] =verity.ity[seory_by_sever    hist         :
   lertSeverityeverity in A     for s
       = {}_severity byistory_          h       
     )
  urs_back=24ho_history(get_alertself.history = cent_     re
       s) hourst 24atistics (laory st# Alert hist                 
         ])
            
  verity= severity =t.seerf al  i               
   ts.values()e_alerivn self.actr alert i  alert fo                 
 en([= lity.value] severerity[_sev  active_by        
      verity:tSeity in Alerever      for s  y = {}
    e_by_severit    activ      severity
  s by ert # Active al            
 
          ow().netimee = dat_tim current          try:
   ""
      tics."ert statishensive alompre"""Get c     y]:
   r, An -> Dict[stics(self)_statist get_alert  
    def")
  rt rulesault aleles)} def{len(self.ruialized Init.info(f"self.logger  
         ))
      "
       value} GBd: {current_ge detecteusandwidth Unusual baate="emplom_message_tust      c     
 EAMLIT],el.STRtionChannfica[Notinnels=fication_cha       noti80,
     e_minutes=1lvuto_reso  a        ue,
  Tro_resolve=    aut
        =120,wn_minutescooldo          2,
  uired=eqs_rtive_breache   consecu      tes=15,
   ow_minuluation_wind      eva     .INFO,
 erityy=AlertSev    severit
        ON,ECTIDETor.ANOMALY_ateOperultor=R     opera       e"],
"data_usagme_filter=[ metric_na        
   H],ype.BANDWIDTricTetilter=[Mpe_f_tytric          me"],
  tewayfinity_ga=["xce_filter  devi         ,
 ally high"unusu usage is n bandwidthlert whe="Aion  descript      
    sage",width Uigh Bandme="H          nae",
  sagth_ugh_bandwid_id="hi    rule        le(
rtRuadd_rule(Aleself.       age rules
 dth usandwi   # B
     
        ))        t_value}"
me}: {curren{device_nated on event detecrity plate="Secuge_temstom_messacu      
      .STREAMLIT],onChannelcatiIL, Notifiannel.EMAficationChs=[Notinelcation_chan     notifi    alse,
   =Folveauto_res     5,
       n_minutes=     cooldow       ed=1,
ireaches_requive_brsecut        con  tes=1,
  _minundowvaluation_wi  e        ICAL,
  y.CRITlertSeveritrity=A    seve,
        e="normal"shold_valuhre     t,
       EQUALSor.NOT_=RuleOperatoroperat           
 URITY],e.SECTypetric_filter=[Mpetymetric_       
     nts",ved erelatey-n securiton="Alert o descripti          tected",
 y Event Deurite="Secnam     
       ted",t_detecevenrity_e_id="secu rul        le(
   lertRud_rule(Af.ad      sel
  srule # Security   
       ))
           "
   value} dBm: {current_name}on {device_signal  backhaul  meshlate="Weakge_tempm_messa      custo      LIT],
el.STREAMtionChannotificas=[Nannelification_ch  not      0,
    ve_minutes=6 auto_resol       =True,
    lve auto_reso    ,
       tes=30ooldown_minu         ced=3,
   ches_requirtive_breacu   conse      utes=5,
   ow_minndvaluation_wi     e  ING,
     verity.WARNy=AlertSe     severitdBm
        # -70 0.0, alue=-7hold_v       thresN,
     or.LESS_THAr=RuleOperatato       oper],
     "_signal=["backhaul_filterme metric_na
           I_MESH],ype.WIFMetricTlter=[tric_type_fi         me],
   te_2"orbi_satellinetgear_ "llite_1",ateear_orbi_slter=["netg_fice  devi          ak",
signal is weh backhaul hen mes"Alert wption=  descri          l",
aul Signa Mesh Backheakme="W  na
          ak",haul_we"mesh_back    rule_id=
        (AlertRule(.add_rule  selfi)
      gear Orb(Netules  mesh riFi        # W
)
           )
     lue}% used"ent_va{currce_name}: vi{despace on isk "Low dge_template=_messastom        cu
    T],STREAMLInel.onChantitifica NoAIL,nnel.EMionChaicatNotifn_channels=[ficatio    noti        =120,
olve_minutes    auto_res       ue,
 _resolve=Tr     auto      s=60,
 uteooldown_min c          uired=1,
 ches_requtive_brea      consec   s=10,
   _minutedown_winvaluatio    e    RNING,
    y.WAertSeveritverity=Al    se       85%
 5.0,  # _value=8old      threshAN,
      ATER_THor.GREratpeRuleO operator=          e"],
 sk_usagfilter=["diic_name_     metr    ES],
   URCEM_RESOSTtricType.SY[Metype_filter= metric_          
 server"],mini_pc_"ter=[device_fil            w",
ing lonns ruspace iisk  when d="Alertdescription          ,
  sk Space"w Di   name="Lo       ow",
  pace_lk_s_id="disrule        le(
    tRudd_rule(Aler self.a      
      
        ))e}%"
   t_valu: {currene_name}on {devicge y usaortical memate="Crisage_templm_mescusto          ],
  l.STREAMLITtionChanneNotificaL, el.EMAIicationChannifels=[Not_channtion notifica
           utes=30,inresolve_m      auto_ue,
      e=Tr_resolv  auto          tes=15,
nuown_micoold           
 2,uired=breaches_reqconsecutive_   
         tes=3,minun_window_atiovalu   e      ICAL,
   ty.CRITeveriy=AlertSeverit  s           # 90%
e=90.0, _valuthreshold           
 THAN,.GREATER_eOperatortor=Rul     opera     sage"],
  mory_u["meter=_filmeetric_na         m  S],
 ESOURCEEM_Rype.SYSTicTMetre_filter=[etric_typ     m  
     r"],rve_pc_seinilter=["mevice_fi        d    
",cally highs critiusage iemory t when m="Alerption    descri      Usage",
  gh Memory e="Hi   nam,
         _usage"ory_memle_id="high   ru   
      le((AlertRuadd_rule      self.
  )
              )"
  e}%rrent_valuame}: {cuvice_nage on {deh CPU us"Higmplate=essage_te_m    custom
        AMLIT],REnnel.STonChatificatiAIL, NoonChannel.EMcati[Notifis=_channelfication    noti       =30,
 es_minutveresol   auto_         
e=True,esolv     auto_r      s=20,
 wn_minuteldo        coo    red=3,
ches_requie_breaivutconsec         utes=5,
   ow_minon_windluati         eva  NING,
 ARerity.Wy=AlertSev    severit        # 85%
ue=85.0,  reshold_val        thTHAN,
    .GREATER_orRuleOperattor=  opera       "],
   cpu_usage"ter=[name_filmetric_         S],
   EM_RESOURCEype.SYST=[MetricTpe_filtertric_ty         me
   r"],pc_serve"mini_=[_filterce   devi        
 ",highnsistently co is  usagewhen CPUon="Alert descripti            ,
 CPU Usage"High    name="    ,
    cpu_usage""high_rule_id=            lertRule(
f.add_rule(A
        selr)i PC Serveles (Mine ruem resourc    # Syst 
           ))
  }"
      valuent_me} = {curreric_nae}: {met{device_namd on aly detectepower anom="DOCSIS latesage_tempm_mesto  cus        AMLIT],
  l.STREationChanneels=[Notificon_channificati        not=120,
    _minutesauto_resolve          e,
  ruve=T_resol      auto0,
      =6tesminuldown_coo          ed=2,
  uirhes_reqve_breacconsecuti            ,
tes=10indow_minuluation_w      evaING,
      .WARNtyriAlertSeverity=seve         TION,
   ALY_DETECerator.ANOMor=RuleOp      operat"],
      stream_powerr", "uptream_powewnslter=["doric_name_fi        metCSIS],
    DOe.etricTyp=[Mtype_filtermetric_        ],
    is_s33"["arr_filter=  device        e",
  ble rangptaof acceels are out  levCSIS powerwhen DOion="Alert  descript        e",
   ang Out of RS PowerDOCSIname="       
     nge",ra_of_is_power_outd="docs    rule_i       
 ule(_rule(AlertRelf.add
        s        ))
   "
     d_value} dB)d: {thresholsholdB (thre} ent_valueurrame}: {cce_n on {devilowoo S SNR tDOCSIplate="message_tem     custom_
       IT],TREAMLionChannel.Sficat Notiannel.EMAIL,ChicationNotifn_channels=[atiotific no       s=60,
    ve_minuteto_resol     au
       rue,resolve=T       auto_30,
     _minutes=owncoold           ,
 ed=2aches_requirutive_breconsec          utes=5,
  window_minevaluation_           
 .CRITICAL,veritySerterity=Ale    sev       # 30 dB
  =30.0, old_valuehresh   t    
     THAN,S_r.LESeOperatooperator=Rul     ],
       ter=["snr"ame_filric_n      met     
 IS],.DOCSTypeiclter=[Metrric_type_fi  met        ,
  rris_s33"]"ater=[ device_fil          ow",
 too lIS SNR is  when DOCSAlertion="descript           SNR",
  OCSIS Low   name="D      nr",
   low_s"docsis__id=   rule(
         ertRulerule(Aladd_f.    sel
    is S33)es (Arrity rulal qualSIS sign     # DOC     
      ))
        lue}ms"
nt_va{curree_name}: n {devicected oy detigh latenc="Hatee_templagustom_mess          cEAMLIT],
  STRnnel.cationChafiannels=[Notiication_ch     notif0,
       tes=2nuresolve_mito_ au  
         ve=True,o_resol   aut    =10,
     own_minutesoold c
           required=3,es_ve_breachonsecuti       c3,
     inutes=indow_mevaluation_w           RNING,
 tSeverity.WAeverity=Aler         s
   0ms.0,  # 10_value=100shold   thre
         AN,EATER_THOperator.GRor=Ruleperat   o        cy"],
 enping_late_filter=["c_nam       metriNCY],
     icType.LATE=[Metrype_filterric_tet      m
       is high",rk latencywoeten nlert whn="Aptio  descri          ncy",
work Late"High Net      name=      ",
ncygh_late"hi   rule_id=      Rule(
   lertd_rule(A  self.ade
       rulencylat    # High    
        ))
       hable"
  and unreacine is offlvice_name} de"Device {plate=essage_tem    custom_m       ],
 TREAMLITChannel.Stification, NoAILel.EMannionChtificatnels=[Non_chanotificatio      n30,
      inutes=ve_mresol    auto_     True,
   o_resolve=      aut
      15,_minutes=wn    cooldo
        equired=2,eaches_rve_brcuti   conse       nutes=5,
  window_mion_ evaluati           NG,
ity.WARNI=AlertSeverseverity          =False,
  old_value     thresh       EQUALS,
Operator.le operator=Ru        ],
   eachable"lter=["rtric_name_fi    me      Y],
  ITTIVe.CONNECricTyp=[Met_type_filter     metric",
        unreachablevice becomesa deert when ription="Alesc    d",
        ce Offlinee="Devi        nam",
    offlineice__id="devle   ru   e(
      rtRuladd_rule(Ale    self.   y rules
 nnectivit# Device co         
"
       ""onitoring.ork mor home netwt rules falerult alize defa"Initi""
        lf):rules(seefault_ze_d _initiali 
    def
     )core
      nce_snfidere=conce_scoconfide          w(),
  time.noated=dpdate     last_u     ),
  luesmeric_va(nu_count=lenmple      sa
      erns,daily_patts=pattern    daily_
        _patterns,lyrns=hourhourly_patte            ,
_99ntilee_99=percetil  percen          95,
e_tile_95=percenrcentilpe         lue,
   lue=max_va max_va        
   ue,min_valalue=     min_v    on,
   td_deviation=sviati    std_de,
        _value_value=mean  mean    me,
      _naetricric.mt_metfirsmetric_name=        type,
    .metric_etricirst_mtric_type=f         med,
   device_imetric.e_id=first_    devic     ata(
   selineDn Ba   retur
           [0]
  = metricsric rst_met    fi   
 tricirst mem f info fro Get device #
        e
       ncher confideig data = hore.0)  # M / 100ric_values) len(nume1.0, min(re =e_sconcideonf      cty
  ata qualised on dscore ba confidence atelcul Ca  #
              lues)
tics.mean(va= statistterns[day] ly_pa  dai              es per day
mplsa # Minimum lues) >= 5: len(va       if     .items():
 daily_groupses in  day, valu     for
   agesaily averlculate d Ca  #      
        
ean(values)tics.m = statisr]patterns[houly_   hour       
      es per hourmum sampl Mini  #lues) >= 3:   if len(va:
         s.items()ouphourly_grues in valr,     for houerages
    y avlate hourl# Calcu 
        
       ntinue     co          
 r):roErTypeor, rrlueEt (Vaxcep    e          
           value)
   pend(week].apof_groups[day_     daily_    []
       _week] = _ofdayps[  daily_grou             s:
      daily_groupinot ek nf_we  if day_o           
                 )
  valueour].append([hpsgrouurly_    ho           ]
 hour] = [s[y_groupurl     ho              :
 roupsin hourly_g hour not           if           
 
          lue)ic.vat(metr floa  value =              :
        try  
    
          eekday().timestamp.w = metric_of_week         dayr
   imestamp.hou= metric.t hour            :
 in metricsetric m    for   
     = {}
    ly_groups      dai   {}
 _groups =ourly
        hof week and day up by hour  # Gro 
            
 tterns = {}ly_pa  dai   
   atterns = {}y_pourl  hns
      based patterme-lculate ti Ca       #  
     ))]
  alues(sorted_v(0.99 * lenvalues[int sorted_9 =ntile_9      percelues))]
  (sorted_va* lenint(0.95 ues[rted_val