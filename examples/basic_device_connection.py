#!/usr/bin/env python3
"""Basic device connection example.

This example demonstrates how to connect to a network device,
execute basic commands, and handle the results.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters
from netarchon.utils.logger import get_logger
from netarchon.utils.exceptions import ConnectionError, CommandError

# Configure logging
logger = get_logger(__name__)


def main():
    """Main function demonstrating basic device connection."""
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
    
    # Initialize SSH connector and command executor
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    
    try:
        print(f"Connecting to device: {device.hostname}")
        
        # Connect to the device
        if not ssh_connector.connect(device):
            print("Failed to connect to device")
            return 1
            
        print("Successfully connected!")
        
        # Execute basic commands
        commands = [
            "show version",
            "show ip interface brief",
            "show running-config | include hostname"
        ]
        
        for command in commands:
            print(f"\nExecuting command: {command}")
            try:
                result = command_executor.execute_command(device, command)
                print("Command output:")
                print("-" * 40)
                print(result.output)
                print("-" * 40)
                print(f"Exit code: {result.exit_code}")
                print(f"Execution time: {result.execution_time:.2f}s")
                
            except CommandError as e:
                print(f"Command failed: {str(e)}")
                continue
        
        print("\nExample completed successfully!")
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