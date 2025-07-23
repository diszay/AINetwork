# NetArchon Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using NetArchon.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Authentication Problems](#authentication-problems)
3. [Command Execution Failures](#command-execution-failures)
4. [Configuration Management Issues](#configuration-management-issues)
5. [Monitoring and Alerting Problems](#monitoring-and-alerting-problems)
6. [Performance Issues](#performance-issues)
7. [Error Messages](#error-messages)
8. [Debugging Tips](#debugging-tips)

## Connection Issues

### Problem: Cannot connect to device

**Symptoms:**
- Connection timeouts
- "Connection refused" errors
- SSH handshake failures

**Possible Causes and Solutions:**

1. **Network connectivity**
   ```bash
   # Test basic connectivity
   ping 192.168.1.1
   telnet 192.168.1.1 22
   ```

2. **SSH service not running**
   ```python
   # Check if SSH is enabled on device
   # For Cisco devices, ensure SSH is configured:
   # ip domain-name example.com
   # crypto key generate rsa
   # ip ssh version 2
   ```

3. **Firewall blocking connection**
   - Check firewall rules on both client and device
   - Verify ACLs on network devices

4. **Wrong port number**
   ```python
   # Specify correct SSH port
   connection_params = ConnectionParameters(
       username="admin",
       password="password",
       port=2222  # If SSH is on non-standard port
   )
   ```

5. **SSL/TLS issues**
   ```python
   # Disable strict host key checking for testing
   connection_params = ConnectionParameters(
       username="admin",
       password="password",
       strict_host_key_checking=False
   )
   ```

### Problem: Connection drops frequently

**Symptoms:**
- Intermittent connection losses
- "Connection reset by peer" errors

**Solutions:**

1. **Enable keepalive**
   ```python
   connection_params = ConnectionParameters(
       username="admin",
       password="password",
       keepalive_interval=30  # Send keepalive every 30 seconds
   )
   ```

2. **Increase timeout values**
   ```python
   connection_params = ConnectionParameters(
       username="admin",
       password="password",
       timeout=60,  # Connection timeout
       auth_timeout=30  # Authentication timeout
   )
   ```

3. **Check network stability**
   ```bash
   # Monitor network connectivity
   ping -c 100 192.168.1.1
   ```

## Authentication Problems

### Problem: Authentication failed

**Symptoms:**
- "Authentication failed" errors
- "Permission denied" messages
- Login prompts appearing repeatedly

**Solutions:**

1. **Verify credentials**
   ```python
   # Test with correct username/password
   connection_params = ConnectionParameters(
       username="correct_username",
       password="correct_password"
   )
   ```

2. **Check account status**
   - Ensure account is not locked
   - Verify account has appropriate privileges
   - Check password expiration

3. **Use key-based authentication**
   ```python
   connection_params = ConnectionParameters(
       username="admin",
       private_key_path="/path/to/private/key",
       private_key_passphrase="key_passphrase"  # If key is encrypted
   )
   ```

4. **Enable password authentication on device**
   ```bash
   # For some devices, ensure password auth is enabled
   # Cisco: ip ssh password-authentication
   ```

### Problem: Privilege escalation fails

**Symptoms:**
- Cannot enter enable mode
- "Access denied" when running privileged commands

**Solutions:**

1. **Provide enable password**
   ```python
   # Enable privileged mode with password
   command_executor.enable_privilege_mode(device, enable_password="enable_secret")
   ```

2. **Check user privileges**
   ```bash
   # Verify user has privilege 15 or enable access
   # show privilege
   ```

3. **Use AAA authentication**
   ```python
   # For AAA environments, ensure proper configuration
   connection_params = ConnectionParameters(
       username="admin",
       password="password",
       enable_password="enable_secret"
   )
   ```

## Command Execution Failures

### Problem: Commands timeout

**Symptoms:**
- Commands hang indefinitely
- Timeout errors for long-running commands

**Solutions:**

1. **Increase command timeout**
   ```python
   # Set longer timeout for slow commands
   result = command_executor.execute_command(
       device, 
       "show tech-support",
       timeout=300  # 5 minutes
   )
   ```

2. **Use paging for large outputs**
   ```python
   # Disable paging to prevent hanging
   command_executor.execute_command(device, "terminal length 0")
   result = command_executor.execute_command(device, "show running-config")
   ```

3. **Break down complex commands**
   ```python
   # Instead of one large command, use multiple smaller ones
   commands = [
       "show version",
       "show interfaces",
       "show ip route summary"
   ]
   results = command_executor.execute_batch_commands(device, commands)
   ```

### Problem: Command output truncated

**Symptoms:**
- Incomplete command output
- Missing lines from expected output

**Solutions:**

1. **Disable terminal paging**
   ```python
   # Cisco devices
   command_executor.execute_command(device, "terminal length 0")
   
   # Juniper devices
   command_executor.execute_command(device, "set cli screen-length 0")
   ```

2. **Increase buffer size**
   ```python
   # Configure larger buffer in settings
   from netarchon.config.settings import set_setting
   set_setting("command.buffer_size", 131072)  # 128KB
   ```

3. **Use specific output modifiers**
   ```python
   # Use device-specific modifiers
   result = command_executor.execute_command(device, "show running-config | no-more")
   ```

### Problem: Command parsing errors

**Symptoms:**
- Unexpected command output format
- Parsing failures in monitoring

**Solutions:**

1. **Verify device type**
   ```python
   # Ensure correct device type is set
   device = Device(
       name="router1",
       hostname="192.168.1.1",
       device_type=DeviceType.CISCO_IOS,  # Correct type
       connection_params=connection_params
   )
   ```

2. **Update command patterns**
   ```python
   # Adjust regex patterns for your device version
   metric = MetricDefinition(
       name="cpu_utilization",
       command="show processes cpu",
       parser="regex",
       parser_args={"pattern": r"CPU utilization.+?(\d+)%", "group": 1}
   )
   ```

3. **Use device auto-detection**
   ```python
   from netarchon.core.device_manager import DeviceManager
   
   device_manager = DeviceManager()
   detected_type = device_manager.detect_device_type(device)
   device.device_type = detected_type
   ```

## Configuration Management Issues

### Problem: Configuration backup fails

**Symptoms:**
- Empty backup files
- Backup process hangs
- Permission errors

**Solutions:**

1. **Check backup directory permissions**
   ```python
   import os
   backup_dir = "./backups"
   os.makedirs(backup_dir, exist_ok=True)
   ```

2. **Verify device access**
   ```python
   # Test if you can read configuration
   result = command_executor.execute_command(device, "show running-config")
   if result.exit_code == 0:
       print("Can read configuration")
   ```

3. **Use appropriate backup command**
   ```python
   # Different devices use different commands
   # Cisco: show running-config
   # Juniper: show configuration
   # Arista: show running-config
   ```

### Problem: Configuration deployment fails

**Symptoms:**
- Configuration not applied
- Syntax errors during deployment
- Device becomes unreachable after deployment

**Solutions:**

1. **Validate configuration first**
   ```python
   # Always validate before deploying
   is_valid = config_manager.validate_config(device, new_config)
   if not is_valid:
       print("Configuration has errors, aborting deployment")
       return
   ```

2. **Use configuration sessions**
   ```python
   # For supported devices, use configuration sessions
   config_manager.start_config_session(device)
   try:
       config_manager.deploy_config(device, new_config)
       config_manager.commit_config_session(device)
   except Exception:
       config_manager.rollback_config_session(device)
   ```

3. **Test connectivity during deployment**
   ```python
   # Implement connectivity checks
   def deploy_with_connectivity_check(device, config):
       # Backup current config
       backup_path = config_manager.backup_config(device)
       
       try:
           # Deploy new config
           config_manager.deploy_config(device, config)
           
           # Test connectivity
           if not test_connectivity(device):
               raise ConfigurationError("Lost connectivity after deployment")
               
       except Exception:
           # Rollback on any failure
           config_manager.rollback_config(device, backup_path)
           raise
   ```

### Problem: Configuration rollback fails

**Symptoms:**
- Cannot restore previous configuration
- Rollback command not recognized
- Device in inconsistent state

**Solutions:**

1. **Verify rollback support**
   ```python
   # Check if device supports rollback
   if device.device_type == DeviceType.CISCO_IOS:
       # IOS may not support automatic rollback
       # Use manual configuration restore
       pass
   ```

2. **Use manual configuration restore**
   ```python
   # Read backup file and apply manually
   with open(backup_path, 'r') as f:
       backup_config = f.read()
   
   config_manager.deploy_config(device, backup_config)
   ```

3. **Implement custom rollback logic**
   ```python
   def custom_rollback(device, backup_path):
       # Enter configuration mode
       command_executor.execute_command(device, "configure terminal")
       
       # Clear current configuration
       command_executor.execute_command(device, "write erase")
       
       # Apply backup configuration
       with open(backup_path, 'r') as f:
           for line in f:
               if line.strip():
                   command_executor.execute_command(device, line.strip())
       
       # Save configuration
       command_executor.execute_command(device, "write memory")
   ```

## Monitoring and Alerting Problems

### Problem: Metrics collection fails

**Symptoms:**
- No metric data collected
- Metric parsing errors
- Inconsistent metric values

**Solutions:**

1. **Verify metric commands**
   ```python
   # Test metric command manually
   result = command_executor.execute_command(device, "show processes cpu")
   print(result.output)  # Check if output matches expected format
   ```

2. **Update metric definitions**
   ```python
   # Adjust metric definition for your device
   cpu_metric = MetricDefinition(
       name="cpu_utilization",
       command="show processes cpu sorted",  # Try different command
       parser="regex",
       parser_args={"pattern": r"CPU utilization.+?(\d+)%", "group": 1}
   )
   ```

3. **Use device-specific metrics**
   ```python
   # Create device-specific metric definitions
   if device.device_type == DeviceType.CISCO_IOS:
       cpu_command = "show processes cpu"
   elif device.device_type == DeviceType.JUNIPER_JUNOS:
       cpu_command = "show chassis routing-engine"
   ```

### Problem: Alerts not triggering

**Symptoms:**
- No alerts generated despite threshold breaches
- Alert notifications not sent
- Incorrect alert severity

**Solutions:**

1. **Verify threshold configuration**
   ```python
   # Check threshold values and operators
   threshold = MetricThreshold(
       metric_name="cpu_utilization",
       operator=ThresholdOperator.GREATER_THAN,  # Correct operator
       value=80.0,  # Appropriate threshold
       severity=AlertSeverity.WARNING
   )
   ```

2. **Test threshold evaluation**
   ```python
   # Manually test threshold evaluation
   test_value = 85.0
   alert_triggered = alert_manager.evaluate_threshold(
       device, "cpu_utilization", test_value, threshold
   )
   print(f"Alert triggered: {alert_triggered}")
   ```

3. **Check alert cooldown**
   ```python
   # Verify alert cooldown settings
   from netarchon.config.settings import get_setting
   cooldown = get_setting("alerting.cooldown_period", default=300)
   print(f"Alert cooldown: {cooldown} seconds")
   ```

### Problem: Alert notifications not working

**Symptoms:**
- Alerts generated but no notifications sent
- Email/webhook failures
- Notification delays

**Solutions:**

1. **Verify notification configuration**
   ```python
   # Check email settings
   email_config = {
       "server": "smtp.example.com",
       "port": 587,
       "use_tls": True,
       "username": "alerts@example.com",
       "password": "password"
   }
   ```

2. **Test notification methods**
   ```python
   # Test email notification
   from netarchon.core.alerting import EmailNotifier
   
   notifier = EmailNotifier(email_config)
   notifier.send_test_notification()
   ```

3. **Check notification logs**
   ```python
   # Enable debug logging for notifications
   import logging
   logging.getLogger('netarchon.core.alerting').setLevel(logging.DEBUG)
   ```

## Performance Issues

### Problem: Slow operations

**Symptoms:**
- Long response times
- High CPU/memory usage
- Operations timing out

**Solutions:**

1. **Use connection pooling**
   ```python
   # Enable connection pooling
   ssh_connector = SSHConnector(
       pool_size=10,
       pool_timeout=30
   )
   ```

2. **Optimize concurrent operations**
   ```python
   # Limit concurrent connections
   from netarchon.config.settings import set_setting
   set_setting("core.max_concurrent_connections", 5)
   ```

3. **Batch operations**
   ```python
   # Use batch commands instead of individual commands
   commands = ["show version", "show interfaces", "show ip route"]
   results = command_executor.execute_batch_commands(device, commands)
   ```

4. **Profile performance**
   ```python
   import time
   
   start_time = time.time()
   result = command_executor.execute_command(device, "show version")
   end_time = time.time()
   
   print(f"Command took {end_time - start_time:.2f} seconds")
   ```

### Problem: Memory leaks

**Symptoms:**
- Increasing memory usage over time
- Out of memory errors
- Application crashes

**Solutions:**

1. **Properly close connections**
   ```python
   try:
       ssh_connector.connect(device)
       # Perform operations
   finally:
       ssh_connector.disconnect(device.hostname)
   ```

2. **Use context managers**
   ```python
   # Use with statements for automatic cleanup
   with SSHConnector() as connector:
       connector.connect(device)
       result = command_executor.execute_command(device, "show version")
   ```

3. **Monitor memory usage**
   ```python
   import psutil
   import gc
   
   process = psutil.Process()
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
   
   # Force garbage collection
   gc.collect()
   ```

## Error Messages

### Common Error Messages and Solutions

#### "Connection refused"
- **Cause**: SSH service not running or wrong port
- **Solution**: Verify SSH is enabled and check port number

#### "Authentication failed"
- **Cause**: Wrong credentials or account locked
- **Solution**: Verify username/password and account status

#### "Command not found"
- **Cause**: Command not available on device or wrong syntax
- **Solution**: Check device documentation and command syntax

#### "Permission denied"
- **Cause**: Insufficient privileges
- **Solution**: Use privileged mode or check user permissions

#### "Connection timeout"
- **Cause**: Network issues or device not responding
- **Solution**: Check network connectivity and increase timeout

#### "Circuit breaker is open"
- **Cause**: Too many failures, circuit breaker activated
- **Solution**: Wait for recovery timeout or reset circuit breaker

#### "All retry attempts exhausted"
- **Cause**: Operation failed multiple times
- **Solution**: Check underlying issue and increase retry attempts

## Debugging Tips

### Enable Debug Logging

```python
import logging
from netarchon.utils.logger import configure_logging

# Enable debug logging
configure_logging(
    level="DEBUG",
    console=True,
    file_path="./logs/debug.log"
)

# Enable specific module debugging
logging.getLogger('netarchon.core.ssh_connector').setLevel(logging.DEBUG)
logging.getLogger('netarchon.core.command_executor').setLevel(logging.DEBUG)
```

### Use Interactive Debugging

```python
import pdb

# Set breakpoint for debugging
pdb.set_trace()

# Or use ipdb for better debugging experience
import ipdb
ipdb.set_trace()
```

### Test Individual Components

```python
# Test SSH connection separately
ssh_connector = SSHConnector()
if ssh_connector.connect(device):
    print("SSH connection successful")
else:
    print("SSH connection failed")

# Test command execution separately
result = command_executor.execute_command(device, "show version")
print(f"Command result: {result.exit_code}")
print(f"Output length: {len(result.output)}")
```

### Monitor Network Traffic

```bash
# Use tcpdump to monitor SSH traffic
sudo tcpdump -i any port 22 and host 192.168.1.1

# Use Wireshark for detailed analysis
wireshark -i any -f "port 22 and host 192.168.1.1"
```

### Check Device Logs

```python
# Check device logs for connection attempts
result = command_executor.execute_command(device, "show logging | include SSH")
print(result.output)
```

### Validate Configuration Files

```python
import yaml

# Validate YAML configuration
try:
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    print("Configuration file is valid")
except yaml.YAMLError as e:
    print(f"Configuration file error: {e}")
```

## Getting Help

If you're still experiencing issues:

1. **Check the documentation**: Review the [User Guide](user_guide.md) and [API Reference](api_reference.md)
2. **Search existing issues**: Look through the [GitHub issues](https://github.com/yourusername/netarchon/issues)
3. **Create a new issue**: Provide detailed information including:
   - NetArchon version
   - Python version
   - Device type and OS version
   - Complete error messages
   - Minimal code example to reproduce the issue
4. **Join the community**: Participate in [GitHub Discussions](https://github.com/yourusername/netarchon/discussions)

## Reporting Bugs

When reporting bugs, please include:

```python
# Version information
import netarchon
print(f"NetArchon version: {netarchon.__version__}")

import sys
print(f"Python version: {sys.version}")

# Device information (sanitized)
print(f"Device type: {device.device_type}")
print(f"Device OS version: {device_info.get('os_version', 'unknown')}")

# Error traceback
import traceback
traceback.print_exc()
```