# NetArchon

A comprehensive Python library for network device automation, configuration management, and monitoring.

## Features

- **Multi-vendor Support**: Works with Cisco IOS, NX-OS, Juniper JunOS, Arista EOS, and more
- **SSH Connection Management**: Robust connection pooling and management
- **Configuration Management**: Backup, deploy, validate, and rollback configurations
- **Real-time Monitoring**: Collect metrics and generate alerts based on thresholds
- **Error Handling**: Circuit breaker patterns and retry mechanisms for reliability
- **Concurrent Operations**: Handle multiple devices simultaneously
- **Extensible Architecture**: Easy to add support for new device types

## Quick Start

### Installation

```bash
pip install netarchon
```

### Basic Usage

```python
from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters

# Create a device
device = Device(
    name="router1",
    hostname="192.168.1.1",
    device_type=DeviceType.CISCO_IOS,
    connection_params=ConnectionParameters(
        username="admin",
        password="password"
    )
)

# Connect and execute commands
ssh_connector = SSHConnector()
command_executor = CommandExecutor(ssh_connector)

ssh_connector.connect(device)
result = command_executor.execute_command(device, "show version")
print(result.output)
```

## Documentation

- [User Guide](docs/user_guide.md)
- [API Reference](docs/api_reference.md)
- [Configuration Guide](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md)

## Examples

Check out the [examples](examples/) directory for complete working examples:

- [Basic Device Connection](examples/basic_device_connection.py)
- [Configuration Management](examples/configuration_management.py)
- [Monitoring and Alerting](examples/monitoring_example.py)

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/netarchon.git
cd netarchon

# Setup development environment
python scripts/setup_dev_env.py

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-performance

# Run with coverage
make test-coverage
```

### Code Quality

```bash
# Run linting
make lint

# Fix formatting
make format

# Check formatting
make format-check
```

## Configuration

NetArchon can be configured using YAML or JSON files. Default configuration locations:

- `./config/config.yaml`
- `~/.netarchon/config.yaml`
- `/etc/netarchon/config.yaml`

Example configuration:

```yaml
# Core settings
core:
  default_timeout: 30
  max_concurrent_connections: 10
  connection_retries: 3

# SSH settings
ssh:
  port: 22
  timeout: 10
  keepalive_interval: 30

# Monitoring settings
monitoring:
  interval: 300
  enable_metrics: true
  metrics_dir: "./metrics"

# Alerting settings
alerting:
  enable_alerts: true
  notification_methods: ["email"]
  cooldown_period: 300
```

## Supported Devices

| Vendor | Device Types | Status |
|--------|-------------|--------|
| Cisco | IOS, IOS-XE, NX-OS | ✅ Supported |
| Juniper | JunOS | ✅ Supported |
| Arista | EOS | ✅ Supported |
| HP/HPE | Comware, ProCurve | 🚧 In Progress |
| Huawei | VRP | 🚧 In Progress |

## Architecture

NetArchon follows a modular architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Applications  │    │    Examples     │    │     Tests       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
┌─────────────────────────────────────────────────────────────────┐
│                        Core Modules                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ SSH Connector   │ Command Executor│ Device Manager              │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ Config Manager  │ Monitoring      │ Alerting                    │
└─────────────────┴─────────────────┴─────────────────────────────┘
         │                       │                       │
┌─────────────────────────────────────────────────────────────────┐
│                        Data Models                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Device Models   │ Connection      │ Metrics & Alerts            │
└─────────────────┴─────────────────┴─────────────────────────────┘
         │                       │                       │
┌─────────────────────────────────────────────────────────────────┐
│                        Utilities                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Exceptions      │ Logging         │ Circuit Breaker & Retry     │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/yourusername/netarchon/issues)
- 💬 [Discussions](https://github.com/yourusername/netarchon/discussions)
- 📧 Email: support@netarchon.dev

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Roadmap

- [ ] Web-based management interface
- [ ] REST API for remote management
- [ ] Plugin system for custom device types
- [ ] Advanced analytics and reporting
- [ ] Integration with popular monitoring systems

---

**NetArchon** - Simplifying network automation, one device at a time.