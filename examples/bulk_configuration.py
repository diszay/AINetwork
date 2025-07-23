#!/usr/bin/env python3
"""Bulk configuration management example.

This example demonstrates:
- Managing configurations for multiple devices
- Template-based configuration generation
- Parallel configuration deployment
- Configuration validation and rollback
- Progress tracking and reporting
"""

import os
import sys
import json
import yaml
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.config_manager import ConfigManager
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters
from netarchon.utils.logger import get_logger, configure_logging
from netarchon.utils.circuit_breaker import create_circuit_breaker
from netarchon.utils.retry_manager import RetryManager

# Configure logging
configure_logging(level="INFO", console=True)
logger = get_logger(__name__)


class ConfigurationTemplate:
    """Template for generating device configurations."""
    
    def __init__(self, template_content: str):
        """Initialize with template content."""
        self.template_content = template_content
        
    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        rendered = self.template_content
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered


class BulkConfigManager:
    """Manages bulk configuration operations across multiple devices."""
    
    def __init__(self):
        """Initialize bulk configuration manager."""
        self.ssh_connector = SSHConnector(pool_size=20)
        self.command_executor = CommandExecutor(self.ssh_connector)
        self.config_manager = ConfigManager(self.command_executor)
        
        # Create circuit breaker for device operations
        self.device_breaker = create_circuit_breaker(
            "bulk_config_operations",
            failure_threshold=3,
            recovery_timeout=120
        )
        
        # Create retry manager
        self.retry_manager = RetryManager(
            max_attempts=3,
            initial_delay=2.0,
            max_delay=30.0
        )
        
        self.devices = []
        self.templates = {}
        self.deployment_results = []
        
    def add_device(self, device: Device) -> None:
        """Add a device to the bulk operation."""
        self.devices.append(device)
        logger.info(f"Added device {device.name} ({device.hostname})")
        
    def load_devices_from_file(self, file_path: str) -> None:
        """Load devices from YAML or JSON file."""
        with open(file_path, 'r') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
                
        for device_data in data.get('devices', []):
            device = Device(
                name=device_data['name'],
                hostname=device_data['hostname'],
                device_type=DeviceType(device_data['device_type']),
                connection_params=ConnectionParameters(
                    username=device_data['connection']['username'],
                    password=device_data['connection'].get('password'),
                    private_key_path=device_data['connection'].get('private_key_path'),
                    port=device_data['connection'].get('port', 22),
                    timeout=device_data['connection'].get('timeout', 30)
                ),
                description=device_data.get('description'),
                tags=device_data.get('tags', [])
            )
            self.add_device(device)
            
        logger.info(f"Loaded {len(self.devices)} devices from {file_path}")
        
    def load_template(self, name: str, file_path: str) -> None:
        """Load a configuration template from file."""
        with open(file_path, 'r') as f:
            template_content = f.read()
        self.templates[name] = ConfigurationTemplate(template_content)
        logger.info(f"Loaded template '{name}' from {file_path}")
        
    def backup_all_devices(self, backup_dir: str = "./backups") -> Dict[str, Any]:
        """Backup configurations from all devices."""
        backup_results = {
            "timestamp": datetime.now().isoformat(),
            "backup_dir": backup_dir,
            "results": []
        }
        
        def backup_device(device: Device) -> Dict[str, Any]:
            """Backup a single device."""
            result = {
                "device_name": device.name,
                "hostname": device.hostname,
                "success": False,
                "backup_path": None,
                "error": None
            }
            
            try:
                # Use circuit breaker and retry for backup
                backup_path = self.device_breaker.call(
                    self.retry_manager.call,
                    self.config_manager.backup_config,
                    device,
                    backup_dir
                )
                result["success"] = True
                result["backup_path"] = backup_path
                logger.info(f"Backed up {device.name} to {backup_path}")
                
            except Exception as e:
                result["error"] = str(e)
                logger.error(f"Failed to backup {device.name}: {str(e)}")
                
            return result
            
        # Execute backups in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_device = {
                executor.submit(backup_device, device): device
                for device in self.devices
            }
            
            for future in as_completed(future_to_device):
                result = future.result()
                backup_results["results"].append(result)
                
        # Generate summary
        successful = len([r for r in backup_results["results"] if r["success"]])
        total = len(backup_results["results"])
        logger.info(f"Backup completed: {successful}/{total} devices successful")
        
        return backup_results
        
    def deploy_template_to_devices(
        self, 
        template_name: str, 
        device_variables: Dict[str, Dict[str, Any]],
        validate_before_deploy: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Deploy a template to multiple devices with device-specific variables."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
            
        deployment_results = {
            "timestamp": datetime.now().isoformat(),
            "template_name": template_name,
            "dry_run": dry_run,
            "validate_before_deploy": validate_before_deploy,
            "results": []
        }
        
        def deploy_to_device(device: Device) -> Dict[str, Any]:
            """Deploy configuration to a single device."""
            result = {
                "device_name": device.name,
                "hostname": device.hostname,
                "success": False,
                "backup_path": None,
                "config_applied": False,
                "validation_passed": None,
                "error": None,
                "warnings": []
            }
            
            try:
                # Get device-specific variables
                variables = device_variables.get(device.name, {})
                
                # Add default variables
                variables.update({
                    "device_name": device.name,
                    "hostname": device.hostname,
                    "device_type": device.device_type.value
                })
                
                # Render configuration from template
                template = self.templates[template_name]
                config = template.render(variables)
                
                if dry_run:
                    result["success"] = True
                    result["config_preview"] = config[:500] + "..." if len(config) > 500 else config
                    logger.info(f"Dry run for {device.name}: Configuration generated")
                    return result
                    
                # Backup current configuration
                backup_path = self.config_manager.backup_config(device)
                result["backup_path"] = backup_path
                
                # Validate configuration if requested
                if validate_before_deploy:
                    is_valid = self.config_manager.validate_config(device, config)
                    result["validation_passed"] = is_valid
                    if not is_valid:
                        result["warnings"].append("Configuration validation failed")
                        if not input(f"Continue with {device.name} despite validation failure? (y/n): ").lower().startswith('y'):
                            result["error"] = "Deployment cancelled due to validation failure"
                            return result
                            
                # Deploy configuration
                self.device_breaker.call(
                    self.retry_manager.call,
                    self.config_manager.deploy_config,
                    device,
                    config,
                    validate_before_deploy
                )
                
                result["success"] = True
                result["config_applied"] = True
                logger.info(f"Successfully deployed configuration to {device.name}")
                
            except Exception as e:
                result["error"] = str(e)
                logger.error(f"Failed to deploy to {device.name}: {str(e)}")
                
                # Attempt rollback if backup exists
                if result["backup_path"]:
                    try:
                        self.config_manager.rollback_config(device, result["backup_path"])
                        result["warnings"].append("Configuration rolled back after failure")
                        logger.info(f"Rolled back configuration for {device.name}")
                    except Exception as rollback_error:
                        result["warnings"].append(f"Rollback failed: {str(rollback_error)}")
                        logger.error(f"Rollback failed for {device.name}: {str(rollback_error)}")
                        
            return result
            
        # Execute deployments in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:  # Limit concurrency for config changes
            future_to_device = {
                executor.submit(deploy_to_device, device): device
                for device in self.devices
                if device.name in device_variables or not device_variables  # Deploy to all if no specific variables
            }
            
            for future in as_completed(future_to_device):
                result = future.result()
                deployment_results["results"].append(result)
                
        # Store results
        self.deployment_results.append(deployment_results)
        
        return deployment_results
        
    def generate_deployment_report(self, deployment_results: Dict[str, Any]) -> None:
        """Generate a detailed deployment report."""
        print("\n" + "="*80)
        print("BULK CONFIGURATION DEPLOYMENT REPORT")
        print("="*80)
        
        print(f"Template: {deployment_results['template_name']}")
        print(f"Timestamp: {deployment_results['timestamp']}")
        print(f"Dry Run: {deployment_results['dry_run']}")
        print(f"Validation Enabled: {deployment_results['validate_before_deploy']}")
        print()
        
        results = deployment_results["results"]
        successful = len([r for r in results if r["success"]])
        total = len(results)
        
        print(f"SUMMARY:")
        print(f"  Total devices: {total}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {total - successful}")
        print(f"  Success rate: {(successful/total*100):.1f}%" if total > 0 else "N/A")
        print()
        
        # Detailed results
        print("DETAILED RESULTS:")
        print("-" * 80)
        
        for result in results:
            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
            print(f"{status} - {result['device_name']} ({result['hostname']})")
            
            if result.get("validation_passed") is not None:
                validation_status = "✅" if result["validation_passed"] else "❌"
                print(f"  Validation: {validation_status}")
                
            if result.get("backup_path"):
                print(f"  Backup: {result['backup_path']}")
                
            if result.get("config_applied"):
                print(f"  Configuration: Applied")
                
            if result.get("error"):
                print(f"  Error: {result['error']}")
                
            if result.get("warnings"):
                for warning in result["warnings"]:
                    print(f"  Warning: {warning}")
                    
            if result.get("config_preview"):
                print(f"  Preview: {result['config_preview']}")
                
            print()
            
    def save_deployment_report(self, deployment_results: Dict[str, Any], file_path: Optional[str] = None) -> str:
        """Save deployment report to file."""
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"deployment_report_{timestamp}.json"
            
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(deployment_results, f, indent=2)
            
        logger.info(f"Deployment report saved to {file_path}")
        return file_path
        
    def cleanup(self) -> None:
        """Clean up resources."""
        for device in self.devices:
            try:
                self.ssh_connector.disconnect(device.hostname)
            except Exception as e:
                logger.error(f"Error disconnecting from {device.hostname}: {str(e)}")


def create_sample_files():
    """Create sample configuration files for demonstration."""
    # Create sample devices file
    devices_data = {
        "devices": [
            {
                "name": "core-router-1",
                "hostname": "192.168.1.1",
                "device_type": "cisco_ios",
                "connection": {
                    "username": "admin",
                    "password": "password"
                },
                "description": "Core router in main datacenter",
                "tags": ["core", "datacenter"]
            },
            {
                "name": "access-switch-1",
                "hostname": "192.168.1.10",
                "device_type": "cisco_ios",
                "connection": {
                    "username": "admin",
                    "password": "password"
                },
                "description": "Access switch floor 1",
                "tags": ["access", "floor1"]
            }
        ]
    }
    
    os.makedirs("config_templates", exist_ok=True)
    
    with open("config_templates/devices.yaml", 'w') as f:
        yaml.dump(devices_data, f, default_flow_style=False)
        
    # Create sample configuration template
    template_content = """!
! Configuration for {device_name}
! Generated on {timestamp}
!
hostname {hostname}
!
! Management interface
interface {mgmt_interface}
 description Management interface
 ip address {mgmt_ip} {mgmt_mask}
 no shutdown
!
! SNMP configuration
snmp-server community {snmp_community} RO
snmp-server location "{location}"
snmp-server contact "{contact}"
!
! NTP configuration
ntp server {ntp_server}
!
! Logging configuration
logging {syslog_server}
!
! Banner
banner motd ^
{banner_text}
^
!
end
"""
    
    with open("config_templates/basic_config.txt", 'w') as f:
        f.write(template_content)
        
    # Create sample variables file
    variables_data = {
        "core-router-1": {
            "mgmt_interface": "GigabitEthernet0/0",
            "mgmt_ip": "192.168.100.1",
            "mgmt_mask": "255.255.255.0",
            "snmp_community": "public",
            "location": "Datacenter Rack 1",
            "contact": "Network Admin <admin@company.com>",
            "ntp_server": "pool.ntp.org",
            "syslog_server": "192.168.100.10",
            "banner_text": "Authorized access only - Core Router 1",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "access-switch-1": {
            "mgmt_interface": "Vlan1",
            "mgmt_ip": "192.168.100.10",
            "mgmt_mask": "255.255.255.0",
            "snmp_community": "public",
            "location": "Floor 1 IDF",
            "contact": "Network Admin <admin@company.com>",
            "ntp_server": "pool.ntp.org",
            "syslog_server": "192.168.100.10",
            "banner_text": "Authorized access only - Access Switch 1",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    with open("config_templates/variables.yaml", 'w') as f:
        yaml.dump(variables_data, f, default_flow_style=False)
        
    print("Sample configuration files created in config_templates/")


def main():
    """Main function demonstrating bulk configuration management."""
    # Create sample files if they don't exist
    if not os.path.exists("config_templates"):
        create_sample_files()
        
    # Create bulk configuration manager
    bulk_manager = BulkConfigManager()
    
    try:
        # Load devices from file
        bulk_manager.load_devices_from_file("config_templates/devices.yaml")
        
        # Load configuration template
        bulk_manager.load_template("basic_config", "config_templates/basic_config.txt")
        
        # Load device variables
        with open("config_templates/variables.yaml", 'r') as f:
            device_variables = yaml.safe_load(f)
            
        print(f"Loaded {len(bulk_manager.devices)} devices and configuration template")
        
        # Menu-driven interface
        while True:
            print("\n" + "="*50)
            print("BULK CONFIGURATION MANAGEMENT")
            print("="*50)
            print("1. Backup all device configurations")
            print("2. Deploy configuration (dry run)")
            print("3. Deploy configuration (live)")
            print("4. View deployment history")
            print("5. Exit")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                print("\nBacking up all device configurations...")
                backup_results = bulk_manager.backup_all_devices()
                
                successful = len([r for r in backup_results["results"] if r["success"]])
                total = len(backup_results["results"])
                print(f"\nBackup completed: {successful}/{total} devices successful")
                
                # Save backup report
                report_path = f"backup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_path, 'w') as f:
                    json.dump(backup_results, f, indent=2)
                print(f"Backup report saved to {report_path}")
                
            elif choice == "2":
                print("\nRunning configuration deployment (dry run)...")
                deployment_results = bulk_manager.deploy_template_to_devices(
                    "basic_config",
                    device_variables,
                    validate_before_deploy=True,
                    dry_run=True
                )
                bulk_manager.generate_deployment_report(deployment_results)
                
            elif choice == "3":
                print("\nDeploying configuration (LIVE)...")
                confirm = input("This will modify device configurations. Continue? (yes/no): ")
                if confirm.lower() == "yes":
                    deployment_results = bulk_manager.deploy_template_to_devices(
                        "basic_config",
                        device_variables,
                        validate_before_deploy=True,
                        dry_run=False
                    )
                    bulk_manager.generate_deployment_report(deployment_results)
                    bulk_manager.save_deployment_report(deployment_results)
                else:
                    print("Deployment cancelled")
                    
            elif choice == "4":
                print(f"\nDeployment history: {len(bulk_manager.deployment_results)} deployments")
                for i, deployment in enumerate(bulk_manager.deployment_results):
                    successful = len([r for r in deployment["results"] if r["success"]])
                    total = len(deployment["results"])
                    print(f"{i+1}. {deployment['timestamp']} - {deployment['template_name']} "
                          f"({successful}/{total} successful)")
                          
            elif choice == "5":
                break
                
            else:
                print("Invalid option. Please select 1-5.")
                
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        bulk_manager.cleanup()


if __name__ == "__main__":
    main()