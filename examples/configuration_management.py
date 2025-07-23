#!/usr/bin/env python3
"""Configuration management example.

This example demonstrates how to backup, validate, and deploy
configurations to network devices.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.config_manager import ConfigManager
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters
from netarchon.utils.logger import get_logger
from netarchon.utils.exceptions import ConnectionError, ConfigurationError

# Configure logging
logger = get_logger(__name__)


def main():
    """Main function demonstrating configuration management."""
    # Device configuration - modify these values for your environment
    device_config = {
        'name': 'example-router',
        'hostname': '192.168.1.1',
        'device_type': DeviceType.CISCO_IOS,
        'username': 'admin',
        'password': 'password'
    }
    
    # Override with environment variables if available
    device_config['hostname'] = os.environ.get('DEVICE_HOST', device_config['hostname'])
    device_config['username'] = os.environ.get('DEVICE_USERNAME', device_config['username'])
    device_config['password'] = os.environ.get('DEVICE_PASSWORD', device_config['password'])
    
    # Create device object
    device = Device(
        name=device_config['name'],
        hostname=device_config['hostname'],
        device_type=device_config['device_type'],
        connection_params=ConnectionParameters(
            username=device_config['username'],
            password=device_config['password']
        )
    )
    
    # Initialize components
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    config_manager = ConfigManager(command_executor)
    
    try:
        print(f"Connecting to device: {device.hostname}")
        
        # Connect to the device
        if not ssh_connector.connect(device):
            print("Failed to connect to device")
            return 1
            
        print("Successfully connected!")
        
        # Create temporary directory for backups
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"\nUsing temporary directory: {temp_dir}")
            
            # 1. Backup current configuration
            print("\n1. Backing up current configuration...")
            try:
                backup_path = config_manager.backup_config(device, temp_dir)
                print(f"Configuration backed up to: {backup_path}")
                
                # Show backup file size
                backup_size = os.path.getsize(backup_path)
                print(f"Backup file size: {backup_size} bytes")
                
            except ConfigurationError as e:
                print(f"Backup failed: {str(e)}")
                return 1
            
            # 2. Validate a sample configuration
            print("\n2. Validating sample configuration...")
            sample_config = '''
            ! Sample configuration snippet
            hostname example-router-new
            !
            interface Loopback0
             ip address 10.0.0.1 255.255.255.255
             description Management loopback
            !
            '''
            
            try:
                is_valid = config_manager.validate_config(device, sample_config)
                print(f"Configuration validation result: {'VALID' if is_valid else 'INVALID'}")
                
            except ConfigurationError as e:
                print(f"Validation failed: {str(e)}")
            
            # 3. Show configuration diff
            print("\n3. Generating configuration diff...")
            try:
                # Read the backup file
                with open(backup_path, 'r') as f:
                    current_config = f.read()
                
                # Create a modified version for diff demonstration
                modified_config = current_config.replace(
                    device_config['name'], 
                    f"{device_config['name']}-modified"
                )
                
                diff = config_manager.get_config_diff(current_config, modified_config)
                print("Configuration differences:")
                
                if diff.get('added'):
                    print("  Added lines:")
                    for line in diff['added'][:5]:  # Show first 5 lines
                        print(f"    + {line}")
                
                if diff.get('removed'):
                    print("  Removed lines:")
                    for line in diff['removed'][:5]:  # Show first 5 lines
                        print(f"    - {line}")
                
                if diff.get('modified'):
                    print("  Modified lines:")
                    for line in diff['modified'][:5]:  # Show first 5 lines
                        print(f"    ~ {line}")
                
            except Exception as e:
                print(f"Diff generation failed: {str(e)}")
            
            # 4. Demonstrate rollback preparation
            print("\n4. Preparing rollback capability...")
            try:
                rollback_ready = config_manager.prepare_rollback(device, backup_path)
                print(f"Rollback preparation: {'READY' if rollback_ready else 'FAILED'}")
                
            except ConfigurationError as e:
                print(f"Rollback preparation failed: {str(e)}")
            
            # 5. Show backup file contents (first few lines)
            print("\n5. Backup file preview:")
            try:
                with open(backup_path, 'r') as f:
                    lines = f.readlines()
                    print("First 10 lines of backup:")
                    for i, line in enumerate(lines[:10], 1):
                        print(f"  {i:2d}: {line.rstrip()}")
                    
                    if len(lines) > 10:
                        print(f"  ... ({len(lines) - 10} more lines)")
                        
            except Exception as e:
                print(f"Could not read backup file: {str(e)}")
        
        print("\nConfiguration management example completed successfully!")
        return 0
        
    except ConnectionError as e:
        print(f"Connection error: {str(e)}")
        return 1
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1
        
    finally:
        # Always disconnect
        if ssh_connector.is_connected(device.hostname):
            ssh_connector.disconnect(device.hostname)
            print("Disconnected from device")


if __name__ == "__main__":
    sys.exit(main())