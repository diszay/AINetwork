"""
NetArchon Configuration Management Module

Safe configuration backup, deployment, and rollback for network devices.
"""

import hashlib
import os
from datetime import datetime
from typing import Dict, Optional

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
                'save_config': 'copy running-config startup-config'
            },
            DeviceType.CISCO_NXOS: {
                'show_config': 'show running-config',
                'save_config': 'copy running-config startup-config'
            },
            DeviceType.JUNIPER_JUNOS: {
                'show_config': 'show configuration',
                'save_config': 'commit'
            },
            DeviceType.ARISTA_EOS: {
                'show_config': 'show running-config',
                'save_config': 'copy running-config startup-config'
            },
            DeviceType.GENERIC: {
                'show_config': 'show running-config',
                'save_config': 'write memory'
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