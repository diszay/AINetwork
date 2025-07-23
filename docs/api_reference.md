# NetArchon API Reference

This document provides comprehensive API reference for all NetArchon modules and classes.

## Table of Contents

1. [Core Modules](#core-modules)
2. [Data Models](#data-models)
3. [Utilities](#utilities)
4. [Configuration](#configuration)
5. [Examples](#examples)

## Core Modules

### SSH Connector

#### `netarchon.core.ssh_connector.SSHConnector`

Main class for managing SSH connections to network devices.

```python
class SSHConnector:
    """Manages SSH connections to network devices with connection pooling."""
    
    def __init__(self, pool_size: int = 10, pool_timeout: int = 300) -> None:
        """Initialize SSH connector with connection pooling.
        
        Args:
            pool_size: Maximum number of connections in the pool
            pool_timeout: Timeout for idle connections in seconds
        """
```

**Methods:**

##### `connect(device: Device) -> bool`

Establish SSH connection to a device.

```python
def connect(device: Device) -> bool:
    """Connect to a network device via SSH.
    
    Args:
        device: Device object containing connection information
        
    Returns:
        True if connection successful, False otherwise
        
    Raises:
        ConnectionError: If connection fails
        AuthenticationError: If authentication fails
    """
```

**Example:**
```python
from netarchon.core.ssh_connector import SSHConnector
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters

device = Device(
    name="router1",
    hostname="192.168.1.1",
    device_type=DeviceType.CISCO_IOS,
    connection_params=ConnectionParameters(username="admin", password="password")
)

ssh_connector = SSHConnector()
if ssh_connector.connect(device):
    print("Connected successfully")
```

##### `disconnect(hostname: str) -> bool`

Disconnect from a device.

```python
def disconnect(hostname: str) -> bool:
    """Disconnect from a device.
    
    Args:
        hostname: Hostname or IP address of the device
        
    Returns:
        True if disconnection successful, False otherwise
    """
```

##### `is_connected(hostname: str) -> bool`

Check if device is connected.

```python
def is_connected(hostname: str) -> bool:
    """Check if device is currently connected.
    
    Args:
        hostname: Hostname or IP address of the device
        
    Returns:
        True if connected, False otherwise
    """
```

##### `get_connection_info(hostname: str) -> Optional[Dict[str, Any]]`

Get connection information for a device.

```python
def get_connection_info(hostname: str) -> Optional[Dict[str, Any]]:
    """Get connection information for a device.
    
    Args:
        hostname: Hostname or IP address of the device
        
    Returns:
        Dictionary with connection information or None if not connected
    """
```

### Command Executor

#### `netarchon.core.command_executor.CommandExecutor`

Executes commands on network devices via SSH.

```python
class CommandExecutor:
    """Executes commands on network devices."""
    
    def __init__(self, ssh_connector: SSHConnector) -> None:
        """Initialize command executor.
        
        Args:
            ssh_connector: SSH connector instance to use
        """
```

**Methods:**

##### `execute_command(device: Device, command: str, timeout: int = 30) -> CommandResult`

Execute a single command on a device.

```python
def execute_command(
    self, 
    device: Device, 
    command: str, 
    timeout: int = 30
) -> CommandResult:
    """Execute a command on a network device.
    
    Args:
        device: Target device
        command: Command to execute
        timeout: Command timeout in seconds
        
    Returns:
        CommandResult object with output and metadata
        
    Raises:
        CommandError: If command execution fails
        TimeoutError: If command times out
    """
```

**Example:**
```python
from netarchon.core.command_executor import CommandExecutor

command_executor = CommandExecutor(ssh_connector)
result = command_executor.execute_command(device, "show version")

print(f"Output: {result.output}")
print(f"Exit code: {result.exit_code}")
print(f"Execution time: {result.execution_time}")
```

##### `execute_batch_commands(device: Device, commands: List[str], timeout: int = 30) -> List[CommandResult]`

Execute multiple commands in sequence.

```python
def execute_batch_commands(
    self, 
    device: Device, 
    commands: List[str], 
    timeout: int = 30
) -> List[CommandResult]:
    """Execute multiple commands in sequence.
    
    Args:
        device: Target device
        commands: List of commands to execute
        timeout: Timeout per command in seconds
        
    Returns:
        List of CommandResult objects
        
    Raises:
        CommandError: If any command fails
    """
```

##### `enable_privilege_mode(device: Device, enable_password: Optional[str] = None) -> bool`

Enable privileged mode on the device.

```python
def enable_privilege_mode(
    self, 
    device: Device, 
    enable_password: Optional[str] = None
) -> bool:
    """Enable privileged mode on the device.
    
    Args:
        device: Target device
        enable_password: Enable password (if required)
        
    Returns:
        True if privilege mode enabled successfully
        
    Raises:
        CommandError: If privilege escalation fails
    """
```

### Device Manager

#### `netarchon.core.device_manager.DeviceManager`

Manages device detection, capabilities, and profiles.

```python
class DeviceManager:
    """Manages device detection and capabilities."""
    
    def __init__(self) -> None:
        """Initialize device manager."""
```

**Methods:**

##### `detect_device_type(device: Device) -> DeviceType`

Auto-detect device type based on system information.

```python
def detect_device_type(device: Device) -> DeviceType:
    """Detect device type automatically.
    
    Args:
        device: Device to detect (connection must be established)
        
    Returns:
        Detected device type
        
    Raises:
        DeviceError: If detection fails
    """
```

##### `get_device_info(device: Device) -> Dict[str, Any]`

Get comprehensive device information.

```python
def get_device_info(device: Device) -> Dict[str, Any]:
    """Get device information including model, OS version, etc.
    
    Args:
        device: Target device
        
    Returns:
        Dictionary with device information
        
    Raises:
        DeviceError: If information retrieval fails
    """
```

**Example:**
```python
from netarchon.core.device_manager import DeviceManager

device_manager = DeviceManager()
device_info = device_manager.get_device_info(device)

print(f"Hostname: {device_info['hostname']}")
print(f"Model: {device_info['model']}")
print(f"OS Version: {device_info['os_version']}")
print(f"Serial: {device_info['serial']}")
```

##### `get_device_capabilities(device: Device) -> Dict[str, bool]`

Get device capabilities and supported features.

```python
def get_device_capabilities(device: Device) -> Dict[str, bool]:
    """Get device capabilities.
    
    Args:
        device: Target device
        
    Returns:
        Dictionary mapping capability names to availability
    """
```

### Configuration Manager

#### `netarchon.core.config_manager.ConfigManager`

Manages device configuration backup, deployment, and rollback.

```python
class ConfigManager:
    """Manages device configuration operations."""
    
    def __init__(self, command_executor: CommandExecutor) -> None:
        """Initialize configuration manager.
        
        Args:
            command_executor: Command executor instance
        """
```

**Methods:**

##### `backup_config(device: Device, backup_dir: str = "./backups") -> str`

Backup device configuration to file.

```python
def backup_config(
    self, 
    device: Device, 
    backup_dir: str = "./backups",
    filename_template: str = "{hostname}_{timestamp}.cfg"
) -> str:
    """Backup device configuration.
    
    Args:
        device: Target device
        backup_dir: Directory to store backup files
        filename_template: Template for backup filename
        
    Returns:
        Path to the backup file
        
    Raises:
        ConfigurationError: If backup fails
    """
```

**Example:**
```python
from netarchon.core.config_manager import ConfigManager

config_manager = ConfigManager(command_executor)
backup_path = config_manager.backup_config(device)
print(f"Configuration backed up to: {backup_path}")
```

##### `deploy_config(device: Device, config: str, validate: bool = True) -> bool`

Deploy configuration to device.

```python
def deploy_config(
    self, 
    device: Device, 
    config: str, 
    validate: bool = True
) -> bool:
    """Deploy configuration to device.
    
    Args:
        device: Target device
        config: Configuration text to deploy
        validate: Whether to validate configuration before deployment
        
    Returns:
        True if deployment successful
        
    Raises:
        ConfigurationError: If deployment fails
    """
```

##### `validate_config(device: Device, config: str) -> bool`

Validate configuration syntax.

```python
def validate_config(device: Device, config: str) -> bool:
    """Validate configuration syntax.
    
    Args:
        device: Target device
        config: Configuration to validate
        
    Returns:
        True if configuration is valid
    """
```

##### `rollback_config(device: Device, backup_path: Optional[str] = None) -> bool`

Rollback to previous configuration.

```python
def rollback_config(
    self, 
    device: Device, 
    backup_path: Optional[str] = None
) -> bool:
    """Rollback to previous configuration.
    
    Args:
        device: Target device
        backup_path: Path to backup file (uses latest if None)
        
    Returns:
        True if rollback successful
        
    Raises:
        ConfigurationError: If rollback fails
    """
```

### Monitoring Manager

#### `netarchon.core.monitoring.MonitoringManager`

Collects metrics and monitors device performance.

```python
class MonitoringManager:
    """Manages device monitoring and metrics collection."""
    
    def __init__(self) -> None:
        """Initialize monitoring manager."""
```

**Methods:**

##### `register_metric_definition(metric: MetricDefinition) -> None`

Register a metric definition for collection.

```python
def register_metric_definition(metric: MetricDefinition) -> None:
    """Register a metric definition.
    
    Args:
        metric: Metric definition to register
    """
```

##### `collect_metric(device: Device, metric: MetricDefinition) -> Union[int, float, str]`

Collect a single metric from a device.

```python
def collect_metric(
    self, 
    device: Device, 
    metric: MetricDefinition
) -> Union[int, float, str]:
    """Collect a metric from a device.
    
    Args:
        device: Target device
        metric: Metric definition
        
    Returns:
        Collected metric value
        
    Raises:
        MonitoringError: If metric collection fails
    """
```

**Example:**
```python
from netarchon.core.monitoring import MonitoringManager
from netarchon.models.metrics import MetricDefinition

monitoring_manager = MonitoringManager()

cpu_metric = MetricDefinition(
    name="cpu_utilization",
    description="CPU utilization percentage",
    command="show processes cpu | include CPU utilization",
    parser="regex",
    parser_args={"pattern": r"CPU utilization for.+: (\d+)%", "group": 1},
    result_type="float",
    unit="%"
)

monitoring_manager.register_metric_definition(cpu_metric)
cpu_value = monitoring_manager.collect_metric(device, cpu_metric)
print(f"CPU utilization: {cpu_value}%")
```

##### `collect_metrics(device: Device, metrics: List[MetricDefinition]) -> Dict[str, Union[int, float, str]]`

Collect multiple metrics from a device.

```python
def collect_metrics(
    self, 
    device: Device, 
    metrics: List[MetricDefinition]
) -> Dict[str, Union[int, float, str]]:
    """Collect multiple metrics from a device.
    
    Args:
        device: Target device
        metrics: List of metric definitions
        
    Returns:
        Dictionary mapping metric names to values
        
    Raises:
        MonitoringError: If any metric collection fails
    """
```

### Alert Manager

#### `netarchon.core.alerting.AlertManager`

Manages alerting based on metric thresholds.

```python
class AlertManager:
    """Manages alerting and notifications."""
    
    def __init__(self) -> None:
        """Initialize alert manager."""
```

**Methods:**

##### `register_threshold(threshold: MetricThreshold) -> None`

Register a metric threshold for alerting.

```python
def register_threshold(threshold: MetricThreshold) -> None:
    """Register a metric threshold.
    
    Args:
        threshold: Threshold definition
    """
```

##### `evaluate_threshold(device: Device, metric_name: str, value: Union[int, float], threshold: MetricThreshold) -> bool`

Evaluate a threshold against a metric value.

```python
def evaluate_threshold(
    self, 
    device: Device, 
    metric_name: str, 
    value: Union[int, float], 
    threshold: MetricThreshold
) -> bool:
    """Evaluate a threshold against a metric value.
    
    Args:
        device: Source device
        metric_name: Name of the metric
        value: Metric value to evaluate
        threshold: Threshold to evaluate against
        
    Returns:
        True if threshold is breached (alert triggered)
    """
```

**Example:**
```python
from netarchon.core.alerting import AlertManager
from netarchon.models.metrics import MetricThreshold, ThresholdOperator
from netarchon.models.alerts import AlertSeverity

alert_manager = AlertManager()

cpu_threshold = MetricThreshold(
    metric_name="cpu_utilization",
    operator=ThresholdOperator.GREATER_THAN,
    value=80.0,
    severity=AlertSeverity.WARNING,
    description="CPU utilization is high"
)

alert_manager.register_threshold(cpu_threshold)

# Evaluate threshold
cpu_value = 85.0
alert_triggered = alert_manager.evaluate_threshold(
    device, "cpu_utilization", cpu_value, cpu_threshold
)

if alert_triggered:
    print("Alert triggered: CPU utilization is high")
```

##### `get_active_alerts() -> List[Alert]`

Get all active alerts.

```python
def get_active_alerts() -> List[Alert]:
    """Get all active alerts.
    
    Returns:
        List of active Alert objects
    """
```

##### `acknowledge_alert(alert_id: str) -> bool`

Acknowledge an alert.

```python
def acknowledge_alert(alert_id: str) -> bool:
    """Acknowledge an alert.
    
    Args:
        alert_id: ID of the alert to acknowledge
        
    Returns:
        True if acknowledgment successful
    """
```

## Data Models

### Device Models

#### `netarchon.models.device.Device`

Represents a network device.

```python
@dataclass
class Device:
    """Represents a network device."""
    
    name: str
    hostname: str
    device_type: DeviceType
    connection_params: ConnectionParameters
    description: Optional[str] = None
    tags: Optional[List[str]] = None
```

**Attributes:**
- `name`: Unique device name
- `hostname`: IP address or hostname
- `device_type`: Type of device (enum)
- `connection_params`: Connection parameters
- `description`: Optional description
- `tags`: Optional list of tags

#### `netarchon.models.device.DeviceType`

Enumeration of supported device types.

```python
class DeviceType(Enum):
    """Supported device types."""
    
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    JUNIPER_JUNOS = "juniper_junos"
    ARISTA_EOS = "arista_eos"
    GENERIC = "generic"
```

### Connection Models

#### `netarchon.models.connection.ConnectionParameters`

Connection parameters for device authentication.

```python
@dataclass
class ConnectionParameters:
    """Connection parameters for device authentication."""
    
    username: str
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    port: int = 22
    timeout: int = 30
    auth_timeout: int = 15
    banner_timeout: int = 5
    keepalive_interval: int = 0
    strict_host_key_checking: bool = True
```

#### `netarchon.models.connection.CommandResult`

Result of command execution.

```python
@dataclass
class CommandResult:
    """Result of command execution."""
    
    command: str
    output: str
    exit_code: int
    execution_time: float
    timestamp: datetime
    error: Optional[str] = None
```

### Metrics Models

#### `netarchon.models.metrics.MetricDefinition`

Defines how to collect a metric.

```python
@dataclass
class MetricDefinition:
    """Defines how to collect a metric from a device."""
    
    name: str
    description: str
    command: str
    parser: str
    parser_args: Dict[str, Any]
    result_type: str
    unit: Optional[str] = None
    tags: Optional[List[str]] = None
```

#### `netarchon.models.metrics.MetricThreshold`

Defines alerting thresholds for metrics.

```python
@dataclass
class MetricThreshold:
    """Defines alerting thresholds for metrics."""
    
    metric_name: str
    operator: ThresholdOperator
    value: Union[int, float]
    severity: AlertSeverity
    description: str
    cooldown_period: int = 300
```

#### `netarchon.models.metrics.ThresholdOperator`

Operators for threshold comparison.

```python
class ThresholdOperator(Enum):
    """Operators for threshold comparison."""
    
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"
```

### Alert Models

#### `netarchon.models.alerts.Alert`

Represents an alert.

```python
@dataclass
class Alert:
    """Represents an alert."""
    
    id: str
    device_name: str
    metric_name: str
    severity: AlertSeverity
    description: str
    value: Union[int, float]
    threshold_value: Union[int, float]
    state: AlertState
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
```

#### `netarchon.models.alerts.AlertSeverity`

Alert severity levels.

```python
class AlertSeverity(Enum):
    """Alert severity levels."""
    
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
```

#### `netarchon.models.alerts.AlertState`

Alert states.

```python
class AlertState(Enum):
    """Alert states."""
    
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
```

## Utilities

### Exception Classes

#### `netarchon.utils.exceptions.NetArchonError`

Base exception class for NetArchon.

```python
class NetArchonError(Exception):
    """Base exception class for NetArchon."""
    pass
```

#### `netarchon.utils.exceptions.ConnectionError`

Connection-related errors.

```python
class ConnectionError(NetArchonError):
    """Raised when connection operations fail."""
    pass
```

#### `netarchon.utils.exceptions.CommandError`

Command execution errors.

```python
class CommandError(NetArchonError):
    """Raised when command execution fails."""
    pass
```

#### `netarchon.utils.exceptions.ConfigurationError`

Configuration management errors.

```python
class ConfigurationError(NetArchonError):
    """Raised when configuration operations fail."""
    pass
```

### Circuit Breaker

#### `netarchon.utils.circuit_breaker.CircuitBreaker`

Implements circuit breaker pattern for fault tolerance.

```python
class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ) -> None:
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exceptions: Exception types that count as failures
        """
```

**Usage as decorator:**
```python
from netarchon.utils.circuit_breaker import CircuitBreaker

circuit_breaker = CircuitBreaker("device_connection", failure_threshold=3)

@circuit_breaker
def connect_to_device(device):
    return ssh_connector.connect(device)
```

**Usage directly:**
```python
try:
    result = circuit_breaker.call(ssh_connector.connect, device)
except CircuitBreakerError:
    print("Circuit breaker is open")
```

### Retry Manager

#### `netarchon.utils.retry_manager.RetryManager`

Implements retry logic with configurable backoff strategies.

```python
class RetryManager:
    """Manages retry attempts with configurable backoff strategies."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        backoff_strategy: Union[BackoffStrategy, str] = BackoffStrategy.EXPONENTIAL,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,)
    ) -> None:
        """Initialize retry manager.
        
        Args:
            max_attempts: Maximum retry attempts
            backoff_strategy: Backoff strategy to use
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add randomness to delays
            retryable_exceptions: Exception types that trigger retries
        """
```

**Usage as decorator:**
```python
from netarchon.utils.retry_manager import RetryManager, BackoffStrategy

retry_manager = RetryManager(
    max_attempts=3,
    backoff_strategy=BackoffStrategy.EXPONENTIAL
)

@retry_manager
def execute_command_with_retry(device, command):
    return command_executor.execute_command(device, command)
```

### Logging

#### `netarchon.utils.logger.get_logger(name: str) -> logging.Logger`

Get a configured logger instance.

```python
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
```

**Example:**
```python
from netarchon.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Starting operation")
logger.debug("Debug information")
logger.error("Error occurred")
```

#### `netarchon.utils.logger.configure_logging(**kwargs) -> None`

Configure logging settings.

```python
def configure_logging(
    level: str = "INFO",
    file_path: Optional[str] = None,
    console: bool = True,
    json_format: bool = False,
    max_size: int = 10485760,
    backup_count: int = 5
) -> None:
    """Configure logging settings.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_path: Path to log file
        console: Whether to log to console
        json_format: Whether to use JSON formatting
        max_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """
```

## Configuration

### Settings Manager

#### `netarchon.config.settings.SettingsManager`

Manages application configuration from files.

```python
class SettingsManager:
    """Manages application settings from configuration files."""
    
    def load_settings(
        self,
        config_paths: Optional[List[str]] = None,
        default_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Load settings from configuration files.
        
        Args:
            config_paths: List of paths to configuration files
            default_config: Default configuration to use as base
        """
```

#### Global Functions

##### `netarchon.config.settings.load_settings(config_paths, default_config)`

Load settings using the global settings manager.

```python
def load_settings(
    config_paths: Optional[List[str]] = None,
    default_config: Optional[Dict[str, Any]] = None
) -> None:
    """Load settings using the global settings manager."""
```

##### `netarchon.config.settings.get_setting(key, default)`

Get a setting value.

```python
def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value.
    
    Args:
        key: Setting key (supports dot notation)
        default: Default value if key not found
        
    Returns:
        Setting value or default
    """
```

**Example:**
```python
from netarchon.config.settings import load_settings, get_setting

# Load configuration
load_settings(["./config/config.yaml"])

# Get settings
timeout = get_setting("ssh.timeout", default=30)
max_connections = get_setting("core.max_concurrent_connections", default=10)
```

## Examples

### Basic Device Connection

```python
#!/usr/bin/env python3
"""Example: Basic device connection and command execution."""

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters

def main():
    # Create device
    device = Device(
        name="router1",
        hostname="192.168.1.1",
        device_type=DeviceType.CISCO_IOS,
        connection_params=ConnectionParameters(
            username="admin",
            password="password"
        )
    )
    
    # Initialize components
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    
    try:
        # Connect to device
        if ssh_connector.connect(device):
            print(f"Connected to {device.hostname}")
            
            # Execute commands
            commands = ["show version", "show ip interface brief"]
            for command in commands:
                result = command_executor.execute_command(device, command)
                print(f"\nCommand: {command}")
                print(f"Output:\n{result.output}")
        else:
            print(f"Failed to connect to {device.hostname}")
            
    finally:
        # Disconnect
        ssh_connector.disconnect(device.hostname)

if __name__ == "__main__":
    main()
```

### Configuration Management

```python
#!/usr/bin/env python3
"""Example: Configuration backup and deployment."""

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.config_manager import ConfigManager
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters

def main():
    # Create device
    device = Device(
        name="router1",
        hostname="192.168.1.1",
        device_type=DeviceType.CISCO_IOS,
        connection_params=ConnectionParameters(
            username="admin",
            password="password"
        )
    )
    
    # Initialize components
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    config_manager = ConfigManager(command_executor)
    
    try:
        # Connect to device
        ssh_connector.connect(device)
        
        # Backup current configuration
        backup_path = config_manager.backup_config(device)
        print(f"Configuration backed up to: {backup_path}")
        
        # Example configuration change
        new_config = """
        interface loopback 100
         description Test interface
         ip address 10.0.0.1 255.255.255.255
        """
        
        # Validate configuration
        if config_manager.validate_config(device, new_config):
            print("Configuration is valid")
            
            # Deploy configuration
            config_manager.deploy_config(device, new_config)
            print("Configuration deployed successfully")
        else:
            print("Configuration validation failed")
            
    except Exception as e:
        print(f"Error: {e}")
        # Rollback on error
        config_manager.rollback_config(device)
        
    finally:
        ssh_connector.disconnect(device.hostname)

if __name__ == "__main__":
    main()
```

### Monitoring and Alerting

```python
#!/usr/bin/env python3
"""Example: Device monitoring and alerting."""

import time
from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.monitoring import MonitoringManager
from netarchon.core.alerting import AlertManager
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters
from netarchon.models.metrics import MetricDefinition, MetricThreshold, ThresholdOperator
from netarchon.models.alerts import AlertSeverity

def main():
    # Create device
    device = Device(
        name="router1",
        hostname="192.168.1.1",
        device_type=DeviceType.CISCO_IOS,
        connection_params=ConnectionParameters(
            username="admin",
            password="password"
        )
    )
    
    # Initialize components
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    monitoring_manager = MonitoringManager()
    alert_manager = AlertManager()
    
    # Define metrics
    cpu_metric = MetricDefinition(
        name="cpu_utilization",
        description="CPU utilization percentage",
        command="show processes cpu | include CPU utilization",
        parser="regex",
        parser_args={"pattern": r"CPU utilization for.+: (\d+)%", "group": 1},
        result_type="float",
        unit="%"
    )
    
    # Define thresholds
    cpu_threshold = MetricThreshold(
        metric_name="cpu_utilization",
        operator=ThresholdOperator.GREATER_THAN,
        value=80.0,
        severity=AlertSeverity.WARNING,
        description="CPU utilization is high"
    )
    
    # Register components
    monitoring_manager.register_metric_definition(cpu_metric)
    alert_manager.register_threshold(cpu_threshold)
    
    try:
        # Connect to device
        ssh_connector.connect(device)
        
        # Monitoring loop
        for i in range(5):
            print(f"\nMonitoring cycle {i + 1}")
            
            # Collect metrics
            cpu_value = monitoring_manager.collect_metric(device, cpu_metric)
            print(f"CPU utilization: {cpu_value}%")
            
            # Evaluate thresholds
            alert_triggered = alert_manager.evaluate_threshold(
                device, "cpu_utilization", cpu_value, cpu_threshold
            )
            
            if alert_triggered:
                print("⚠️  Alert: CPU utilization is high!")
            
            # Wait before next collection
            time.sleep(10)
            
    finally:
        ssh_connector.disconnect(device.hostname)

if __name__ == "__main__":
    main()
```

## Error Handling

### Exception Hierarchy

```
NetArchonError
├── ConnectionError
│   ├── AuthenticationError
│   └── TimeoutError
├── CommandError
│   └── PrivilegeError
├── ConfigurationError
│   └── ValidationError
├── MonitoringError
│   └── MetricCollectionError
└── DeviceError
    └── DetectionError
```

### Best Practices

1. **Always use specific exception types** when catching exceptions
2. **Implement proper cleanup** in finally blocks
3. **Use circuit breakers** for unreliable operations
4. **Implement retry logic** for transient failures
5. **Log errors appropriately** with context information

```python
from netarchon.utils.exceptions import ConnectionError, CommandError
from netarchon.utils.circuit_breaker import CircuitBreaker
from netarchon.utils.retry_manager import RetryManager

# Use circuit breaker for connection operations
connection_breaker = CircuitBreaker("device_connection")

# Use retry manager for command execution
command_retry = RetryManager(max_attempts=3)

try:
    # Protected operations
    connection_breaker.call(ssh_connector.connect, device)
    result = command_retry.call(command_executor.execute_command, device, "show version")
    
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
except CommandError as e:
    logger.error(f"Command execution failed: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
finally:
    # Cleanup
    ssh_connector.disconnect(device.hostname)
```

---

This API reference provides comprehensive documentation for all NetArchon components. For more examples and usage patterns, see the [User Guide](user_guide.md) and [examples](../examples/) directory.