# NetArchon Frequently Asked Questions (FAQ)

This document answers common questions about NetArchon usage, configuration, and troubleshooting.

## Table of Contents

1. [General Questions](#general-questions)
2. [Installation and Setup](#installation-and-setup)
3. [Device Support](#device-support)
4. [Connection and Authentication](#connection-and-authentication)
5. [Configuration Management](#configuration-management)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Performance and Scalability](#performance-and-scalability)
8. [Security](#security)
9. [Development and Customization](#development-and-customization)
10. [Troubleshooting](#troubleshooting)

## General Questions

### What is NetArchon?

NetArchon is a comprehensive Python library for network device automation, configuration management, and monitoring. It provides a unified interface for managing network devices from multiple vendors including Cisco, Juniper, Arista, and others.

### What can I do with NetArchon?

- **Device Management**: Connect to and manage network devices via SSH
- **Configuration Management**: Backup, deploy, validate, and rollback configurations
- **Monitoring**: Collect metrics and monitor device performance
- **Alerting**: Set up thresholds and receive notifications
- **Automation**: Automate repetitive network tasks
- **Bulk Operations**: Perform operations across multiple devices simultaneously

### Is NetArchon free to use?

Yes, NetArchon is open-source software released under the MIT License. You can use it freely for both personal and commercial purposes.

### How does NetArchon compare to other network automation tools?

NetArchon focuses on providing a simple, Python-native interface for network automation. Unlike some alternatives:

- **Pure Python**: No external dependencies on network automation frameworks
- **Multi-vendor**: Built-in support for multiple device types
- **Monitoring**: Integrated monitoring and alerting capabilities
- **Extensible**: Easy to extend for custom device types and use cases

## Installation and Setup

### What are the system requirements?

- Python 3.8 or higher
- SSH access to target network devices
- Network connectivity to devices
- Sufficient permissions on devices for intended operations

### How do I install NetArchon?

```bash
# From PyPI (recommended)
pip install netarchon

# From source
git clone https://github.com/yourusername/netarchon.git
cd netarchon
pip install -e .
```

### How do I set up a development environment?

```bash
# Clone the repository
git clone https://github.com/yourusername/netarchon.git
cd netarchon

# Run the setup script
python scripts/setup_dev_env.py

# Activate the virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### Where should I put configuration files?

NetArchon looks for configuration files in these locations (in order):
1. `./config/config.yaml` (current directory)
2. `~/.netarchon/config.yaml` (user home directory)
3. `/etc/netarchon/config.yaml` (system-wide)

### Can I use JSON instead of YAML for configuration?

Yes, NetArchon supports both YAML and JSON configuration files. Use the appropriate file extension (`.yaml`, `.yml`, or `.json`).

## Device Support

### Which device types are supported?

Currently supported:
- **Cisco**: IOS, IOS-XE, NX-OS
- **Juniper**: JunOS
- **Arista**: EOS
- **Generic**: Any SSH-enabled device

Planned support:
- HP/HPE Comware and ProCurve
- Huawei VRP
- Fortinet FortiOS

### How do I add support for a new device type?

1. Create a new device type in `DeviceType` enum
2. Add device-specific command patterns
3. Implement device detection logic
4. Add metric definitions for the device type
5. Write tests for the new device type

See the [Contributing Guide](contributing.md) for detailed instructions.

### Can NetArchon auto-detect device types?

Yes, NetArchon can automatically detect device types using the `DeviceManager.detect_device_type()` method. It analyzes system information to determine the device type.

### What if my device isn't officially supported?

You can use the `DeviceType.GENERIC` type for basic SSH operations. Many features will still work, though device-specific optimizations may not be available.

## Connection and Authentication

### What authentication methods are supported?

- **Password authentication**: Username and password
- **Key-based authentication**: SSH private keys (with optional passphrase)
- **Agent authentication**: SSH agent forwarding
- **Mixed authentication**: Combination of methods

### How do I use SSH keys for authentication?

```python
from netarchon.models.connection import ConnectionParameters

connection_params = ConnectionParameters(
    username="admin",
    private_key_path="/path/to/private/key",
    private_key_passphrase="key_passphrase"  # Optional
)
```

### Can I connect to devices on non-standard SSH ports?

Yes, specify the port in the connection parameters:

```python
connection_params = ConnectionParameters(
    username="admin",
    password="password",
    port=2222  # Custom SSH port
)
```

### How does connection pooling work?

NetArchon automatically manages connection pools to improve performance:
- Connections are reused when possible
- Idle connections are automatically closed after a timeout
- Pool size is configurable (default: 10 connections)
- Thread-safe for concurrent operations

### What happens if a connection is lost?

NetArchon includes several mechanisms to handle connection issues:
- **Automatic reconnection**: Attempts to reconnect on connection loss
- **Circuit breaker**: Prevents repeated connection attempts to failing devices
- **Retry logic**: Configurable retry attempts with backoff strategies
- **Graceful degradation**: Operations continue on other devices if one fails

## Configuration Management

### Can I backup configurations from multiple devices?

Yes, use the bulk configuration management features:

```python
from netarchon.examples.bulk_configuration import BulkConfigManager

bulk_manager = BulkConfigManager()
# Add devices...
backup_results = bulk_manager.backup_all_devices()
```

### How do I validate configurations before deployment?

```python
# Validate before deploying
is_valid = config_manager.validate_config(device, new_config)
if is_valid:
    config_manager.deploy_config(device, new_config)
else:
    print("Configuration validation failed")
```

### What happens if a configuration deployment fails?

NetArchon provides several safety mechanisms:
- **Automatic backup**: Creates backup before changes
- **Validation**: Optional pre-deployment validation
- **Rollback**: Automatic or manual rollback on failure
- **Connectivity checks**: Ensures device remains reachable

### Can I use configuration templates?

Yes, NetArchon supports template-based configuration management:

```python
from netarchon.examples.bulk_configuration import ConfigurationTemplate

template = ConfigurationTemplate(template_content)
config = template.render(variables)
```

### How do I handle different configuration formats?

NetArchon adapts to different device configuration formats automatically based on the device type. You can also specify custom parsers for specific devices.

## Monitoring and Alerting

### What metrics can I collect?

Common metrics include:
- **Performance**: CPU utilization, memory usage
- **Interfaces**: Status, utilization, errors
- **Environment**: Temperature, power consumption
- **Custom**: Any command output can be parsed into metrics

### How do I set up custom metrics?

```python
from netarchon.models.metrics import MetricDefinition

custom_metric = MetricDefinition(
    name="custom_metric",
    description="Custom metric description",
    command="show custom command",
    parser="regex",
    parser_args={"pattern": r"Value: (\d+)", "group": 1},
    result_type="int"
)
```

### Can I monitor multiple devices simultaneously?

Yes, NetArchon supports concurrent monitoring:

```python
# Monitor devices in parallel
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(collect_metrics, device) for device in devices]
    results = [future.result() for future in as_completed(futures)]
```

### How do I set up email alerts?

Configure email settings in your configuration file:

```yaml
alerting:
  enable_alerts: true
  notification_methods: ["email"]
  email:
    server: "smtp.example.com"
    port: 587
    use_tls: true
    username: "alerts@example.com"
    password: "password"
    from_address: "alerts@example.com"
    to_addresses: ["admin@example.com"]
```

### Can I integrate with external monitoring systems?

Yes, NetArchon can export metrics to various formats and systems:
- JSON files for custom processing
- Webhook notifications
- Syslog messages
- Custom notification handlers

## Performance and Scalability

### How many devices can NetArchon handle?

NetArchon's scalability depends on several factors:
- **Hardware resources**: CPU, memory, network bandwidth
- **Device response times**: Faster devices allow higher throughput
- **Operation types**: Simple commands vs. complex configurations
- **Concurrency settings**: Number of parallel connections

Typical performance:
- **Small deployments**: 10-50 devices
- **Medium deployments**: 50-200 devices
- **Large deployments**: 200+ devices (with proper tuning)

### How do I optimize performance?

1. **Tune connection pooling**:
   ```python
   ssh_connector = SSHConnector(pool_size=20, pool_timeout=300)
   ```

2. **Use batch operations**:
   ```python
   results = command_executor.execute_batch_commands(device, commands)
   ```

3. **Optimize concurrency**:
   ```yaml
   core:
     max_concurrent_connections: 15
   ```

4. **Use circuit breakers**:
   ```python
   circuit_breaker = CircuitBreaker("operations", failure_threshold=3)
   ```

### What about memory usage?

NetArchon is designed to be memory-efficient:
- Connection pooling reduces memory overhead
- Streaming output processing for large command outputs
- Automatic cleanup of idle connections
- Configurable data retention policies

### Can I run NetArchon in a distributed setup?

While NetArchon doesn't include built-in distributed capabilities, you can:
- Run multiple NetArchon instances
- Use message queues for coordination
- Implement custom load balancing
- Share configuration and results via databases

## Security

### How secure is NetArchon?

NetArchon follows security best practices:
- **Encrypted connections**: All communication via SSH
- **Credential protection**: Secure storage and handling of credentials
- **Input validation**: Validation of all user inputs
- **Audit logging**: Comprehensive logging of all operations
- **Least privilege**: Encourages minimal required permissions

### How should I store credentials?

Best practices for credential storage:

1. **Environment variables**:
   ```bash
   export DEVICE_USERNAME=admin
   export DEVICE_PASSWORD=secret
   ```

2. **Configuration files** (with restricted permissions):
   ```bash
   chmod 600 ~/.netarchon/config.yaml
   ```

3. **Key-based authentication** (preferred):
   ```python
   connection_params = ConnectionParameters(
       username="admin",
       private_key_path="~/.ssh/id_rsa"
   )
   ```

4. **External secret management** (for production):
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault

### What permissions do I need on devices?

Minimum required permissions:
- **Read access**: For monitoring and information gathering
- **Configuration access**: For configuration management (privilege level 15 on Cisco)
- **Enable access**: For privileged commands

### How do I audit NetArchon operations?

NetArchon provides comprehensive logging:

```python
from netarchon.utils.logger import configure_logging

configure_logging(
    level="INFO",
    file_path="/var/log/netarchon/audit.log",
    json_format=True
)
```

Log entries include:
- Timestamp and user information
- Device and operation details
- Success/failure status
- Error messages and stack traces

## Development and Customization

### How do I extend NetArchon for custom use cases?

NetArchon is designed to be extensible:

1. **Custom device types**: Add support for new vendors
2. **Custom metrics**: Define device-specific metrics
3. **Custom parsers**: Parse command output in custom formats
4. **Custom notifications**: Implement custom alert handlers
5. **Plugins**: Create reusable extensions

### Can I contribute to NetArchon?

Yes! We welcome contributions:
- Bug fixes and improvements
- New device support
- Documentation updates
- Example scripts
- Test coverage improvements

See the [Contributing Guide](contributing.md) for details.

### How do I write tests for my customizations?

NetArchon includes comprehensive testing utilities:

```python
import pytest
from unittest.mock import Mock
from netarchon.core.ssh_connector import SSHConnector

def test_custom_functionality():
    # Use mocks for testing
    mock_device = Mock()
    mock_device.hostname = "test-device"
    
    # Test your custom code
    result = your_custom_function(mock_device)
    assert result is not None
```

### What's the development roadmap?

Planned features:
- Web-based management interface
- REST API for remote management
- Plugin system for extensions
- Advanced analytics and reporting
- Integration with popular monitoring systems

## Troubleshooting

### Why can't I connect to my device?

Common connection issues:

1. **Network connectivity**: Test with `ping` and `telnet`
2. **SSH service**: Ensure SSH is enabled on the device
3. **Authentication**: Verify credentials and permissions
4. **Firewall**: Check for blocking rules
5. **SSH configuration**: Verify SSH settings on device

### Commands are timing out, what should I do?

1. **Increase timeout**:
   ```python
   result = command_executor.execute_command(device, command, timeout=120)
   ```

2. **Disable paging**:
   ```python
   command_executor.execute_command(device, "terminal length 0")
   ```

3. **Use batch commands**:
   ```python
   commands = ["command1", "command2", "command3"]
   results = command_executor.execute_batch_commands(device, commands)
   ```

### How do I enable debug logging?

```python
from netarchon.utils.logger import configure_logging

configure_logging(level="DEBUG", console=True)
```

### My configuration deployment failed, how do I recover?

NetArchon automatically creates backups before configuration changes:

```python
# Manual rollback
config_manager.rollback_config(device, backup_path)

# Or restore from backup file
with open(backup_path, 'r') as f:
    backup_config = f.read()
config_manager.deploy_config(device, backup_config)
```

### How do I report bugs or request features?

1. **Check existing issues**: Search [GitHub Issues](https://github.com/yourusername/netarchon/issues)
2. **Create a new issue**: Provide detailed information including:
   - NetArchon version
   - Python version
   - Device type and OS version
   - Complete error messages
   - Minimal code example
3. **Join discussions**: Participate in [GitHub Discussions](https://github.com/yourusername/netarchon/discussions)

### Where can I get help?

- **Documentation**: [User Guide](user_guide.md), [API Reference](api_reference.md)
- **Examples**: Check the [examples](../examples/) directory
- **Community**: [GitHub Discussions](https://github.com/yourusername/netarchon/discussions)
- **Issues**: [GitHub Issues](https://github.com/yourusername/netarchon/issues)
- **Email**: support@netarchon.dev

---

## Still have questions?

If your question isn't answered here:

1. Check the [User Guide](user_guide.md) for detailed usage information
2. Review the [API Reference](api_reference.md) for technical details
3. Look at [examples](../examples/) for practical implementations
4. Search or create an issue on [GitHub](https://github.com/yourusername/netarchon)
5. Join the community discussions

We're here to help make your network automation journey successful!