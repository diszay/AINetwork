# NetArchon User Guide

**Welcome to NetArchon!** This guide will help you understand and use your personal AI network assistant, whether you're a complete beginner or a networking expert.

## 🎯 What You'll Learn

**For Everyone:**
- How to install NetArchon on your computer
- How to access the web dashboard
- How to monitor your internet and devices
- How to understand alerts and notifications

**For Technical Users:**
- How to configure advanced monitoring
- How to manage device credentials securely
- How to automate network tasks
- How to troubleshoot network issues

## Table of Contents

1. [Getting Started](#getting-started) - Installation and first steps
2. [Understanding Your Network](#understanding-your-network) - Basic concepts explained simply
3. [Using the Web Dashboard](#using-the-web-dashboard) - Point-and-click interface
4. [Managing Your Devices](#managing-your-devices) - Adding and monitoring devices
5. [Monitoring and Alerts](#monitoring-and-alerts) - Staying informed about your network
6. [Security Features](#security-features) - Keeping your network safe
7. [Advanced Features](#advanced-features) - For power users
8. [Troubleshooting](#troubleshooting) - When things go wrong

## Getting Started

### What You Need Before Installing

**For Everyone:**
- A computer running Windows, Mac, or Linux
- Your home WiFi network (NetArchon works best when installed on a computer that stays connected to your network)
- Admin passwords for your router/modem (if you want advanced features)

**Technical Requirements:**
- Python 3.8 or higher
- Network connectivity to your home devices
- SSH access to network devices (for advanced monitoring)

### Easy Installation (Recommended)

**Step 1: Download NetArchon**
```bash
# If you have Python installed, this is the easiest way:
pip install netarchon
```

**Step 2: Start NetArchon**
```bash
# Run this command to start your network dashboard:
streamlit run netarchon
```

**Step 3: Open Your Dashboard**
- Open your web browser
- Go to: `http://localhost:8501`
- You should see your NetArchon dashboard!

### Advanced Installation (For Developers)

**Install from Source Code:**
```bash
# Download the latest version from GitHub:
git clone https://github.com/yourusername/netarchon.git
cd netarchon
pip install -e .
```

**Development Setup:**
```bash
# Set up a development environment:
python scripts/setup_dev_env.py
source .venv/bin/activate  # On Mac/Linux
# or
.venv\Scripts\activate     # On Windows
```

## Understanding Your Network

### What is a "Network Device"?

**For Everyone:**
Think of network devices as the "traffic controllers" of your internet. These include:
- **Your Router** - The box that creates your WiFi network (like Netgear, Linksys, etc.)
- **Your Modem** - The device that connects to your internet provider (like Arris, Motorola)
- **Switches** - Devices that connect multiple wired devices together
- **Access Points** - Devices that extend your WiFi coverage

**Technical Details:**
NetArchon represents each network device as a `Device` object with specific properties:

```python
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters

device = Device(
    name="router1",                    # Friendly name you choose
    hostname="192.168.1.1",           # IP address of the device
    device_type=DeviceType.CISCO_IOS, # What type of device it is
    connection_params=ConnectionParameters(
        username="admin",              # Login username
        password="password",           # Login password
        port=22                        # Connection port (usually 22 for SSH)
    )
)
```

### Types of Devices NetArchon Supports

**For Everyone:**
NetArchon works with most common home and business network equipment, including:
- Popular home routers (Netgear, Linksys, ASUS, etc.)
- Cable/DSL modems (Arris, Motorola, etc.)
- Business-grade equipment (Cisco, Juniper, etc.)
- Generic devices that support remote management

**Technical Device Types:**
- `DeviceType.CISCO_IOS` - Cisco routers and switches
- `DeviceType.CISCO_NXOS` - Cisco Nexus data center switches
- `DeviceType.JUNIPER_JUNOS` - Juniper Networks equipment
- `DeviceType.ARISTA_EOS` - Arista Networks switches
- `DeviceType.GENERIC` - Any device that supports SSH connections

### How NetArchon Connects to Your Devices

**For Everyone:**
NetArchon needs to "log in" to your network devices to monitor them, just like you would log into a website. It uses the admin username and password for each device.

**Technical Connection Details:**
```python
from netarchon.models.connection import ConnectionParameters

# Basic username/password authentication
conn_params = ConnectionParameters(
    username="admin",
    password="password"
)

# More secure key-based authentication
conn_params = ConnectionParameters(
    username="admin",
    private_key_path="/path/to/private/key"
)

# Advanced connection settings
conn_params = ConnectionParameters(
    username="admin",
    password="password",
    port=2222,              # Custom port if not using standard port 22
    timeout=30,             # How long to wait for connection
    keepalive_interval=60   # Keep connection alive every 60 seconds
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