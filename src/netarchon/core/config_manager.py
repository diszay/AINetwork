"""
NetArchon Configuration Management Module

Safe configuration backup, deployment, and rollback for network devices.
"""

import hashlib
import os
import time
from datetime import datetime
from typing import Dict, Optional, List

from ..models.connection import ConnectionInfo, CommandResult
from ..models.device import DeviceType
from ..utils.exceptions import ConfigurationError
from ..utils.logger import get_logger
from .command_executor import CommandExecutor


class ConfigManager:
    """Main configuration management logic for network devices."""
    
    def __init__(self, backup_directory: str = "backups"):
        """Initialize configuration manager.
        
        Args:
            backup_directory: Directory to store configuration backups
        """
        self.backup_directory = backup_directory
        self.logger = get_logger(f"{__name__}.ConfigManager")
        self.command_executor = CommandExecutor()
        
        # Device-specific configuration commands
        self.config_commands = {
            DeviceType.CISCO_IOS: {
                'show_config': 'show running-config',
                'save_config': 'copy running-config startup-config',
                'configure_mode': 'configure terminal',
                'exit_config': 'exit',
                'reload': 'reload'
            },
            DeviceType.CISCO_NXOS: {
                'show_config': 'show running-config',
                'save_config': 'copy running-config startup-config',
                'configure_mode': 'configure terminal',
                'exit_config': 'exit',
                'reload': 'reload'
            },
            DeviceType.JUNIPER_JUNOS: {
                'show_config': 'show configuration',
                'save_config': 'commit',
                'configure_mode': 'configure',
                'exit_config': 'exit',
                'reload': 'request system reboot'
            },
            DeviceType.ARISTA_EOS: {
                'show_config': 'show running-config',
                'save_config': 'copy running-config startup-config',
                'configure_mode': 'configure terminal',
                'exit_config': 'exit',
                'reload': 'reload'
            },
            DeviceType.GENERIC: {
                'show_config': 'show running-config',
                'save_config': 'write memory',
                'configure_mode': 'configure terminal',
                'exit_config': 'exit',
                'reload': 'reload'
            }
        }
        
        # Ensure backup directory exists
        os.makedirs(self.backup_directory, exist_ok=True)
    
    def backup_config(self, connection: ConnectionInfo, reason: str = "Manual backup") -> Optional[str]:
        """Create a backup of the current device configuration.
        
        Args:
            connection: Active connection to the device
            reason: Reason for the backup
            
        Returns:
            Path to the backup file or None if backup failed
            
        Raises:
            ConfigurationError: If backup operation fails
        """
        self.logger.info(f"Starting configuration backup for device {connection.device_id}",
                        device_id=connection.device_id, reason=reason)
        
        try:
            # Get device type from connection or default to generic
            device_type = getattr(connection, 'device_type', DeviceType.GENERIC)
            show_config_cmd = self.config_commands[device_type]['show_config']
            
            # Execute show config command
            result = self.command_executor.execute_command(connection, show_config_cmd)
            
            if not result.success:
                raise ConfigurationError(f"Failed to retrieve configuration: {result.error}")
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{connection.device_id}_config_{timestamp}.txt"
            backup_path = os.path.join(self.backup_directory, connection.device_id)
            
            # Ensure device-specific backup directory exists
            os.makedirs(backup_path, exist_ok=True)
            full_path = os.path.join(backup_path, filename)
            
            # Calculate configuration checksum
            config_content = result.output
            checksum = hashlib.md5(config_content.encode()).hexdigest()
            
            # Write backup file with metadata
            with open(full_path, 'w') as f:
                f.write(f"# NetArchon Configuration Backup\n")
                f.write(f"# Device: {connection.device_id}\n")
                f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"# Reason: {reason}\n")
                f.write(f"# Checksum: {checksum}\n")
                f.write(f"# Command: {show_config_cmd}\n")
                f.write("# " + "="*50 + "\n\n")
                f.write(config_content)
            
            self.logger.info(f"Configuration backup completed: {full_path}",
                           device_id=connection.device_id, 
                           backup_path=full_path,
                           checksum=checksum)
            
            return full_path
            
        except Exception as e:
            error_msg = f"Configuration backup failed for {connection.device_id}: {str(e)}"
            self.logger.error(error_msg, device_id=connection.device_id)
            raise ConfigurationError(error_msg) from e
    
    def validate_config_syntax(self, config_content: str, device_type: DeviceType) -> bool:
        """Basic validation of configuration syntax.
        
        Args:
            config_content: Configuration content to validate
            device_type: Type of device for syntax validation
            
        Returns:
            True if configuration appears valid, False otherwise
        """
        if not config_content or not config_content.strip():
            return False
        
        # Basic validation checks
        config_lines = config_content.strip().split('\n')
        
        # Check for minimum configuration length
        if len(config_lines) < 5:
            return False
        
        # Device-specific validation patterns
        if device_type in [DeviceType.CISCO_IOS, DeviceType.CISCO_NXOS, DeviceType.ARISTA_EOS]:
            # Look for basic Cisco-style configuration elements
            has_version = any('version' in line.lower() for line in config_lines[:10])
            has_hostname = any('hostname' in line.lower() for line in config_lines)
            return has_version or has_hostname
            
        elif device_type == DeviceType.JUNIPER_JUNOS:
            # Look for Juniper configuration structure
            has_juniper_syntax = any('{' in line and '}' in config_content for line in config_lines)
            return has_juniper_syntax
        
        # Generic validation - just check for reasonable content
        return len(config_content) > 100
    
    def apply_config(self, connection: ConnectionInfo, config_content: str, 
                    backup_first: bool = True, timeout: int = 300) -> bool:
        """Apply configuration to a network device with safety mechanisms.
        
        Args:
            connection: Active connection to the device
            config_content: Configuration content to apply
            backup_first: Whether to create backup before applying
            timeout: Maximum time to wait for configuration application
            
        Returns:
            True if configuration was applied successfully, False otherwise
            
        Raises:
            ConfigurationError: If configuration application fails
        """
        device_type = getattr(connection, 'device_type', DeviceType.GENERIC)
        
        self.logger.info(f"Starting configuration deployment for device {connection.device_id}",
                        device_id=connection.device_id, backup_first=backup_first)
        
        try:
            # Step 1: Create backup if requested
            backup_path = None
            if backup_first:
                backup_path = self.backup_config(connection, "Pre-deployment backup")
                if not backup_path:
                    raise ConfigurationError("Failed to create pre-deployment backup")
            
            # Step 2: Validate configuration syntax
            if not self.validate_config_syntax(config_content, device_type):
                raise ConfigurationError("Configuration validation failed")
            
            # Step 3: Test connectivity before deployment
            if not self._test_connectivity(connection):
                raise ConfigurationError("Device connectivity test failed before deployment")
            
            # Step 4: Enter configuration mode
            config_mode_cmd = self.config_commands[device_type]['configure_mode']
            result = self.command_executor.execute_command(connection, config_mode_cmd)
            if not result.success:
                raise ConfigurationError(f"Failed to enter configuration mode: {result.error}")
            
            # Step 5: Apply configuration line by line
            config_lines = [line.strip() for line in config_content.split('\n') 
                          if line.strip() and not line.startswith('#')]
            
            failed_commands = []
            for line in config_lines:
                if line:  # Skip empty lines
                    result = self.command_executor.execute_command(connection, line, timeout=30)
                    if not result.success:
                        failed_commands.append((line, result.error))
                        self.logger.warning(f"Configuration command failed: {line}",
                                          device_id=connection.device_id, 
                                          command=line, error=result.error)
            
            # Step 6: Exit configuration mode
            exit_cmd = self.config_commands[device_type]['exit_config']
            self.command_executor.execute_command(connection, exit_cmd)
            
            # Step 7: Save configuration if no failures
            if not failed_commands:
                save_cmd = self.config_commands[device_type]['save_config']
                result = self.command_executor.execute_command(connection, save_cmd)
                if not result.success:
                    self.logger.error(f"Failed to save configuration: {result.error}",
                                    device_id=connection.device_id)
                    return False
            
            # Step 8: Test connectivity after deployment
            time.sleep(5)  # Wait for configuration to take effect
            if not self._test_connectivity(connection):
                self.logger.error("Connectivity lost after configuration deployment",
                                device_id=connection.device_id)
                if backup_path:
                    self.logger.info("Attempting automatic rollback due to connectivity loss")
                    return self.rollback_config(connection, backup_path)
                return False
            
            # Step 9: Check for failed commands
            if failed_commands:
                self.logger.warning(f"Configuration applied with {len(failed_commands)} failed commands",
                                  device_id=connection.device_id,
                                  failed_count=len(failed_commands))
                return False
            
            self.logger.info("Configuration deployment completed successfully",
                           device_id=connection.device_id, backup_path=backup_path)
            return True
            
        except Exception as e:
            error_msg = f"Configuration deployment failed for {connection.device_id}: {str(e)}"
            self.logger.error(error_msg, device_id=connection.device_id)
            raise ConfigurationError(error_msg) from e
    
    def rollback_config(self, connection: ConnectionInfo, backup_path: str) -> bool:
        """Rollback to a previous configuration backup.
        
        Args:
            connection: Active connection to the device
            backup_path: Path to the backup file to restore
            
        Returns:
            True if rollback was successful, False otherwise
            
        Raises:
            ConfigurationError: If rollback operation fails
        """
        self.logger.info(f"Starting configuration rollback for device {connection.device_id}",
                        device_id=connection.device_id, backup_path=backup_path)
        
        try:
            # Step 1: Verify backup file exists
            if not os.path.exists(backup_path):
                raise ConfigurationError(f"Backup file not found: {backup_path}")
            
            # Step 2: Read backup content
            with open(backup_path, 'r') as f:
                backup_content = f.read()
            
            # Extract actual configuration (skip metadata header)
            config_lines = backup_content.split('\n')
            config_start = 0
            for i, line in enumerate(config_lines):
                if line.startswith('# ' + '='*50):
                    config_start = i + 2  # Skip the separator and empty line
                    break
            
            if config_start == 0:
                raise ConfigurationError("Invalid backup file format")
            
            actual_config = '\n'.join(config_lines[config_start:])
            
            # Step 3: Apply the backup configuration
            result = self.apply_config(connection, actual_config, backup_first=False)
            
            if result:
                self.logger.info("Configuration rollback completed successfully",
                               device_id=connection.device_id, backup_path=backup_path)
            else:
                self.logger.error("Configuration rollback failed",
                                device_id=connection.device_id, backup_path=backup_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Configuration rollback failed for {connection.device_id}: {str(e)}"
            self.logger.error(error_msg, device_id=connection.device_id)
            raise ConfigurationError(error_msg) from e
    
    def _test_connectivity(self, connection: ConnectionInfo) -> bool:
        """Test basic connectivity to the device.
        
        Args:
            connection: Active connection to the device
            
        Returns:
            True if device is reachable, False otherwise
        """
        try:
            # Try a simple command to test connectivity
            result = self.command_executor.execute_command(connection, "show version", timeout=10)
            return result.success
        except Exception:
            return False