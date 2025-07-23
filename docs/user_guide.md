# NetArchon User Guide

This guide provides comprehensive information on how to use NetArchon for network device automation, configuration management, and monitoring.

## Table of Contents

1. [Installation](#installation)
2. [Basic Concepts](#basic-concepts)
3. [Device Connection](#device-connection)
4. [Command Execution](#command-execution)
5. [Configuration Management](#configuration-management)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Error Handling](#error-handling)
8. [Advanced Features](#advanced-features)

## Installation

### Requirements

- Python 3.8 or higher
- SSH access to network devices
- Network connectivity to target devices

### Install from PyPI

```bash
pip install netarchon
```

### Install from Source

```bash
git clone https://github.com/yourusername/netarchon.git
cd netarchon
pip install -e .
```

### Development Installation

```bash
python scripts/setup_dev_env.py
source .venv/bin/activate
```

## Basic Concepts

### Device Model

NetArchon uses a `Device` object to represent network devices:

```python
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters

device = Device(
    name="router1",
    hostname="192.168.1.1",
    device_type=DeviceType.CISCO_IOS,
    connection_params=ConnectionParameters(
        username="admin",
        password="password",
        port=22
    )
)
```

### Supported Device Types

- `DeviceType.CISCO_IOS` - Cisco IOS devices
- `DeviceType.CISCO_NXOS` - Cisco Nexus devices
- `DeviceType.JUNIPER_JUNOS` - Juniper JunOS devices
- `DeviceType.ARISTA_EOS` - Arista EOS devices
- `DeviceType.GENERIC` - Generic SSH devices

### Connection Parameters

```python
from netarchon.models.connection import ConnectionParameters

# Basic authentication
conn_params = ConnectionParameters(
    username="admin",
    password="password"
)

# Key-based authentication
conn_params = ConnectionParameters(
    username="admin",
    private_key_path="/path/to/private/key"
)

# Advanced options
conn_params = ConnectionParameters(
    username="admin",
    password="password",
    port=2222,
    timeout=30,
    keepalive_interval=60
)
```

## Device Connection

### Basic Connection

```python
from netarchon.core.ssh_connector import SSHConnector

ssh_connector = SSHConnector()

# Connect to device
if ssh_connector.connect(device):
    print("Connected successfully!")
else:
    print("Connection failed!")

# Check connection status
if ssh_connector.is_connected(device.hostname):
    print("Device is connected")

# Disconnect
ssh_connector.disconnect(device.hostname)
```

### Connection Pooling

NetArchon automatically manages connection pools for efficient resource usage:

```python
# Connection pooling is handled automatically
# Multiple operations on the same device will reuse connections

ssh_connector = SSHConnector()

# These operations will share connections
ssh_connector.connect(device1)
ssh_connector.connect(device2)
ssh_connector.connect(device1)  # Reuses existing connection
```

### Concurrent Connections

```python
import concurrent.futures
from netarchon.core.ssh_connector import SSHConnector

def connect_device(device):
    ssh_connector = SSHConnector()
    return ssh_connector.connect(device)

devices = [device1, device2, device3]

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(connect_device, device) for device in devices]
    results = [future.result() for future in concurrent.futures.as_completed(futures)]
```

## Command Execution

### Basic Command Execution

```python
from netarchon.core.command_executor import CommandExecutor

ssh_connector = SSHConnector()
command_executor = CommandExecutor(ssh_connector)

# Connect to device
ssh_connector.connect(device)

# Execute command
result = command_executor.execute_command(device, "show version")

print(f"Output: {result.output}")
print(f"Exit code: {result.exit_code}")
print(f"Execution time: {result.execution_time}s")
```

### Batch Command Execution

```python
commands = [
    "show version",
    "show ip interface brief",
    "show running-config | include hostname"
]

results = command_executor.execute_batch_commands(device, commands)

for command, result in zip(commands, results):
    print(f"Command: {command}")
    print(f"Output: {result.output}")
    print("-" * 40)
```

### Privilege Escalation

```python
# Enable privileged mode
command_executor.enable_privilege_mode(device, enable_password="enable_secret")

# Execute privileged commands
result = command_executor.execute_command(device, "show running-config")

# Disable privileged mode
command_executor.disable_privilege_mode(device)
```

### Command Timeout and Error Handling

```python
from netarchon.utils.exceptions import CommandError, TimeoutError

try:
    # Set custom timeout
    result = command_executor.execute_command(
        device, 
        "show tech-support",  # Long-running command
        timeout=300  # 5 minutes
    )
except TimeoutError:
    print("Command timed out")
except CommandError as e:
    print(f"Command failed: {e}")
```

## Configuration Management

### Configuration Backup

```python
from netarchon.core.config_manager import ConfigManager

config_manager = ConfigManager(command_executor)

# Backup configuration
backup_path = config_manager.backup_config(device, backup_dir="./backups")
print(f"Configuration backed up to: {backup_path}")

# Backup with custom filename
backup_path = config_manager.backup_config(
    device, 
    backup_dir="./backups",
    filename_template="{hostname}_{timestamp}.cfg"
)
```

### Configuration Validation

```python
# Read configuration from file
with open("new_config.txt", "r") as f:
    new_config = f.read()

# Validate configuration
is_valid = config_manager.validate_config(device, new_config)

if is_valid:
    print("Configuration is valid")
else:
    print("Configuration has errors")
```

### Configuration Deployment

```python
# Deploy configuration
try:
    config_manager.deploy_config(device, new_config)
    print("Configuration deployed successfully")
except ConfigurationError as e:
    print(f"Deployment failed: {e}")
```

### Configuration Rollback

```python
# Prepare rollback (creates checkpoint)
config_manager.prepare_rollback(device, backup_path)

try:
    # Deploy new configuration
    config_manager.deploy_config(device, new_config)
except ConfigurationError:
    # Rollback on failure
    config_manager.rollback_config(device)
    print("Configuration rolled back")
```

### Configuration Diff

```python
# Get current configuration
current_config = config_manager.get_running_config(device)

# Compare configurations
diff = config_manager.get_config_diff(current_config, new_config)

print("Added lines:")
for line in diff.get('added', []):
    print(f"+ {line}")

print("Removed lines:")
for line in diff.get('removed', []):
    print(f"- {line}")

print("Modified lines:")
for line in diff.get('modified', []):
    print(f"~ {line}")
```

## Monitoring and Alerting

### Metric Collection

```python
from netarchon.core.monitoring import MonitoringManager
from netarchon.models.metrics import MetricDefinition

monitoring_manager = MonitoringManager()

# Define a metric
cpu_metric = MetricDefinition(
    name="cpu_utilization",
    description="CPU utilization percentage",
    command="show processes cpu | include CPU utilization",
    parser="regex",
    parser_args={"pattern": r"CPU utilization for.+: (\\d+)%", "group": 1},
    result_type="float",
    unit="%"
)

# Register metric
monitoring_manager.register_metric_definition(cpu_metric)

# Collect metric
value = monitoring_manager.collect_metric(device, cpu_metric)
print(f"CPU utilization: {value}%")
```

### Multiple Metrics

```python
# Define multiple metrics
metrics = [
    MetricDefinition(
        name="cpu_utilization",
        description="CPU utilization",
        command="show processes cpu",
        parser="regex",
        parser_args={"pattern": r"CPU utilization.+: (\\d+)%", "group": 1},
        result_type="float",
        unit="%"
    ),
    MetricDefinition(
        name="memory_usage",
        description="Memory usage",
        command="show memory statistics",
        parser="regex", 
        parser_args={"pattern": r"Processor\\s+\\d+\\s+\\d+\\s+(\\d+)%", "group": 1},
        result_type="float",
        unit="%"
    )
]

# Register all metrics
for metric in metrics:
    monitoring_manager.register_metric_definition(metric)

# Collect all metrics
values = monitoring_manager.collect_metrics(device, metrics)
for name, value in values.items():
    print(f"{name}: {value}")
```

### Alerting

```python
from netarchon.core.alerting import AlertManager
from netarchon.models.metrics import MetricThreshold, ThresholdOperator
from netarchon.models.alerts import AlertSeverity

alert_manager = AlertManager()

# Define threshold
cpu_threshold = MetricThreshold(
    metric_name="cpu_utilization",
    operator=ThresholdOperator.GREATER_THAN,
    value=80.0,
    severity=AlertSeverity.WARNING,
    description="CPU utilization is high"
)

# Register threshold
alert_manager.register_threshold(cpu_threshold)

# Evaluate threshold
cpu_value = 85.0  # From monitoring
alert_triggered = alert_manager.evaluate_threshold(
    device, "cpu_utilization", cpu_value, cpu_threshold
)

if alert_triggered:
    print("Alert triggered!")

# Get active alerts
active_alerts = alert_manager.get_active_alerts()
for alert in active_alerts:
    print(f"Alert: {alert.description}")
    print(f"Device: {alert.device_name}")
    print(f"Severity: {alert.severity}")
```

### Continuous Monitoring

```python
import time
import threading

def monitor_device(device, metrics, thresholds):
    while True:
        try:
            # Collect metrics
            values = monitoring_manager.collect_metrics(device, metrics)
            
            # Evaluate thresholds
            for threshold in thresholds:
                if threshold.metric_name in values:
                    value = values[threshold.metric_name]
                    alert_manager.evaluate_threshold(
                        device, threshold.metric_name, value, threshold
                    )
            
            # Wait before next collection
            time.sleep(300)  # 5 minutes
            
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(60)  # Wait 1 minute on error

# Start monitoring in background thread
monitor_thread = threading.Thread(
    target=monitor_device,
    args=(device, metrics, [cpu_threshold])
)
monitor_thread.daemon = True
monitor_thread.start()
```

## Error Handling

### Circuit Breaker Pattern

```python
from netarchon.utils.circuit_breaker import CircuitBreaker, create_circuit_breaker

# Create circuit breaker
circuit_breaker = create_circuit_breaker(
    name="device_connection",
    failure_threshold=5,
    recovery_timeout=60
)

# Use as decorator
@circuit_breaker
def connect_to_device(device):
    return ssh_connector.connect(device)

# Use directly
try:
    result = circuit_breaker.call(ssh_connector.connect, device)
except CircuitBreakerError:
    print("Circuit breaker is open, skipping operation")
```

### Retry Mechanism

```python
from netarchon.utils.retry_manager import RetryManager, BackoffStrategy

# Create retry manager
retry_manager = RetryManager(
    max_attempts=3,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    initial_delay=1.0,
    max_delay=30.0
)

# Use as decorator
@retry_manager
def execute_command_with_retry(device, command):
    return command_executor.execute_command(device, command)

# Use directly
try:
    result = retry_manager.call(
        command_executor.execute_command,
        device,
        "show version"
    )
except RetryError:
    print("All retry attempts exhausted")
```

### Exception Handling

```python
from netarchon.utils.exceptions import (
    NetArchonError,
    ConnectionError,
    CommandError,
    ConfigurationError,
    MonitoringError
)

try:
    # Your NetArchon operations
    ssh_connector.connect(device)
    result = command_executor.execute_command(device, "show version")
    
except ConnectionError as e:
    print(f"Connection failed: {e}")
    # Handle connection issues
    
except CommandError as e:
    print(f"Command execution failed: {e}")
    # Handle command issues
    
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Handle configuration issues
    
except NetArchonError as e:
    print(f"NetArchon error: {e}")
    # Handle general NetArchon errors
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle unexpected errors
```

## Advanced Features

### Custom Device Types

```python
from netarchon.models.device import DeviceType

# Define custom device type
class CustomDeviceType(DeviceType):
    CUSTOM_VENDOR = "custom_vendor"

# Use custom device type
device = Device(
    name="custom_device",
    hostname="192.168.1.100",
    device_type=CustomDeviceType.CUSTOM_VENDOR,
    connection_params=connection_params
)
```

### Configuration Management

```python
from netarchon.config.settings import load_settings, get_setting

# Load configuration
load_settings(["./config/config.yaml", "~/.netarchon/config.yaml"])

# Get configuration values
timeout = get_setting("ssh.timeout", default=30)
max_connections = get_setting("core.max_concurrent_connections", default=10)
```

### Logging Configuration

```python
from netarchon.utils.logger import get_logger, configure_logging

# Configure logging
configure_logging(
    level="INFO",
    file_path="./logs/netarchon.log",
    console=True,
    json_format=True
)

# Get logger
logger = get_logger(__name__)
logger.info("Starting NetArchon operations")
```

### Performance Optimization

```python
# Use connection pooling for better performance
ssh_connector = SSHConnector(pool_size=10)

# Batch operations when possible
commands = ["show version", "show ip route", "show interfaces"]
results = command_executor.execute_batch_commands(device, commands)

# Use concurrent operations for multiple devices
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    for device in devices:
        future = executor.submit(command_executor.execute_command, device, "show version")
        futures.append(future)
    
    results = [future.result() for future in concurrent.futures.as_completed(futures)]
```

## Best Practices

### Connection Management

1. Always disconnect when done
2. Use connection pooling for multiple operations
3. Handle connection failures gracefully
4. Set appropriate timeouts

### Error Handling

1. Use specific exception types
2. Implement retry logic for transient failures
3. Use circuit breakers for failing services
4. Log errors appropriately

### Configuration Management

1. Always backup before changes
2. Validate configurations before deployment
3. Use rollback mechanisms
4. Test changes in non-production first

### Monitoring

1. Set appropriate collection intervals
2. Use meaningful thresholds
3. Implement proper alerting
4. Monitor the monitoring system itself

### Security

1. Use key-based authentication when possible
2. Store credentials securely
3. Use least privilege access
4. Audit access and changes

## Troubleshooting

See the [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.