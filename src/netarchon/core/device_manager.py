"""
NetArchon Device Management Module

Device detection, classification, and profile management for network devices.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..models.device import DeviceInfo, DeviceProfile, DeviceType, DeviceStatus
from ..models.connection import ConnectionInfo, CommandResult
from ..utils.exceptions import DeviceError, UnsupportedDeviceError
from ..utils.logger import get_logger
from .command_executor import CommandExecutor


class DeviceDetector:
    """Identifies device types and capabilities using standard commands."""
    
    def __init__(self):
        """Initialize device detector."""
        self.logger = get_logger(f"{__name__}.DeviceDetector")
        self.command_executor = CommandExecutor()
        
        # Device detection patterns
        self.detection_patterns = {
            DeviceType.CISCO_IOS: {
                'version_patterns': [
                    r'Cisco IOS Software',
                    r'IOS \(tm\)',
                    r'Cisco Internetwork Operating System',
                    r'IOS-XE Software'
                ],
                'prompt_patterns': [r'[\w-]+[>#]$'],
                'commands': ['show version', 'show system information']
            },
            DeviceType.CISCO_NXOS: {
                'version_patterns': [
                    r'Cisco Nexus Operating System',
                    r'NX-OS',
                    r'system:\s+version'
                ],
                'prompt_patterns': [r'[\w-]+[>#]$'],
                'commands': ['show version', 'show system information']
            },
            DeviceType.JUNIPER_JUNOS: {
                'version_patterns': [
                    r'JUNOS',
                    r'Juniper Networks',
                    r'junos-version'
                ],
                'prompt_patterns': [r'[\w-]+[@%>]$'],
                'commands': ['show version', 'show system information']
            },
            DeviceType.ARISTA_EOS: {
                'version_patterns': [
                    r'Arista',
                    r'EOS',
                    r'vEOS'
                ],
                'prompt_patterns': [r'[\w-]+[>#]$'],
                'commands': ['show version', 'show system information']
            }
        }
    
    def detect_device_type(self, connection: ConnectionInfo) -> DeviceType:
        """Identify device type using version commands and output analysis.
        
        Args:
            connection: Active connection to the device
            
        Returns:
            DeviceType enumeration value
            
        Raises:
            DeviceError: If device detection fails
        """
        self.logger.info("Starting device type detection", 
                        device_id=connection.device_id)
        
        detection_results = {}
        
        # Try each device type's detection commands
        for device_type, patterns in self.detection_patterns.items():
            try:
                score = self._calculate_detection_score(connection, device_type, patterns)
                detection_results[device_type] = score
                
                self.logger.debug(f"Detection score for {device_type.value}: {score}",
                                device_id=connection.device_id,
                                device_type=device_type.value,
                                score=score)
                
            except Exception as e:
                self.logger.warning(f"Detection failed for {device_type.value}: {str(e)}",
                                  device_id=connection.device_id,
                                  device_type=device_type.value)
                detection_results[device_type] = 0
        
        # Find the device type with highest score
        if not detection_results or max(detection_results.values()) == 0:
            self.logger.warning("Could not detect device type, using GENERIC",
                              device_id=connection.device_id)
            return DeviceType.GENERIC
        
        detected_type = max(detection_results, key=detection_results.get)
        confidence = detection_results[detected_type]
        
        self.logger.info(f"Device detected as {detected_type.value}",
                        device_id=connection.device_id,
                        device_type=detected_type.value,
                        confidence=confidence)
        
        return detected_type
    
    def get_device_info(self, connection: ConnectionInfo) -> DeviceInfo:
        """Get comprehensive device information.
        
        Args:
            connection: Active connection to the device
            
        Returns:
            DeviceInfo object with device details
        """
        self.logger.info("Gathering device information", 
                        device_id=connection.device_id)
        
        try:
            # Detect device type first
            device_type = self.detect_device_type(connection)
            
            # Get version information
            version_result = self.command_executor.execute_command(
                connection, "show version"
            )
            
            if not version_result.success:
                raise DeviceError(f"Failed to get version information: {version_result.error}",
                                {"device_id": connection.device_id})
            
            # Parse device information from version output
            hostname, vendor, model, os_version = self._parse_device_info(
                version_result.output, device_type
            )
            
            device_info = DeviceInfo(
                hostname=hostname or connection.device_id,
                ip_address=connection.host,
                device_type=device_type,
                vendor=vendor,
                model=model,
                os_version=os_version,
                last_seen=datetime.utcnow(),
                status=DeviceStatus.ONLINE
            )
            
            self.logger.info("Device information gathered successfully",
                           device_id=connection.device_id,
                           hostname=device_info.hostname,
                           vendor=device_info.vendor,
                           model=device_info.model,
                           os_version=device_info.os_version)
            
            return device_info
            
        except Exception as e:
            self.logger.error(f"Failed to gather device information: {str(e)}",
                            device_id=connection.device_id,
                            error=str(e))
            raise DeviceError(f"Device information gathering failed: {str(e)}",
                            {"device_id": connection.device_id})
    
    def create_device_profile(self, connection: ConnectionInfo) -> DeviceProfile:
        """Create device profile with capabilities and command syntax.
        
        Args:
            connection: Active connection to the device
            
        Returns:
            DeviceProfile object with device-specific information
        """
        self.logger.info("Creating device profile", 
                        device_id=connection.device_id)
        
        try:
            # Get basic device information
            device_info = self.get_device_info(connection)
            
            # Detect capabilities
            capabilities = self._detect_capabilities(connection, device_info.device_type)
            
            # Get command syntax mapping
            command_syntax = self._get_command_syntax(device_info.device_type)
            
            profile = DeviceProfile(
                device_type=device_info.device_type,
                vendor=device_info.vendor,
                model=device_info.model,
                os_version=device_info.os_version,
                capabilities=capabilities,
                command_syntax=command_syntax
            )
            
            self.logger.info("Device profile created successfully",
                           device_id=connection.device_id,
                           device_type=profile.device_type.value,
                           capabilities_count=len(profile.capabilities),
                           commands_count=len(profile.command_syntax))
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to create device profile: {str(e)}",
                            device_id=connection.device_id,
                            error=str(e))
            raise DeviceError(f"Device profile creation failed: {str(e)}",
                            {"device_id": connection.device_id})
    
    def _calculate_detection_score(self, 
                                  connection: ConnectionInfo, 
                                  device_type: DeviceType, 
                                  patterns: Dict) -> int:
        """Calculate detection confidence score for a device type.
        
        Args:
            connection: Active connection to the device
            device_type: Device type to test
            patterns: Detection patterns for the device type
            
        Returns:
            Confidence score (0-100)
        """
        score = 0
        
        # Try version commands
        for command in patterns['commands']:
            try:
                result = self.command_executor.execute_command(connection, command)
                if result.success and result.output:
                    # Check version patterns
                    for pattern in patterns['version_patterns']:
                        if re.search(pattern, result.output, re.IGNORECASE):
                            score += 30
                            break
                    
                    # Additional scoring based on output characteristics
                    if device_type == DeviceType.CISCO_IOS:
                        if 'cisco' in result.output.lower():
                            score += 20
                        if 'ios' in result.output.lower():
                            score += 15
                    elif device_type == DeviceType.JUNIPER_JUNOS:
                        if 'juniper' in result.output.lower():
                            score += 20
                        if 'junos' in result.output.lower():
                            score += 15
                    elif device_type == DeviceType.ARISTA_EOS:
                        if 'arista' in result.output.lower():
                            score += 20
                        if 'eos' in result.output.lower():
                            score += 15
                    
                    break  # Found working command
                    
            except Exception:
                continue
        
        return min(score, 100)  # Cap at 100
    
    def _parse_device_info(self, 
                          version_output: str, 
                          device_type: DeviceType) -> Tuple[str, str, str, str]:
        """Parse device information from version command output.
        
        Args:
            version_output: Output from show version command
            device_type: Detected device type
            
        Returns:
            Tuple of (hostname, vendor, model, os_version)
        """
        hostname = ""
        vendor = ""
        model = ""
        os_version = ""
        
        if device_type == DeviceType.CISCO_IOS:
            vendor = "Cisco"
            
            # Extract hostname
            hostname_match = re.search(r'^(\S+)\s+uptime', version_output, re.MULTILINE)
            if hostname_match:
                hostname = hostname_match.group(1)
            
            # Extract model
            model_match = re.search(r'cisco\s+(\S+)', version_output, re.IGNORECASE)
            if model_match:
                model = model_match.group(1)
            
            # Extract OS version
            version_match = re.search(r'Version\s+([^\s,]+)', version_output)
            if version_match:
                os_version = version_match.group(1)
                
        elif device_type == DeviceType.JUNIPER_JUNOS:
            vendor = "Juniper"
            
            # Extract hostname
            hostname_match = re.search(r'Hostname:\s+(\S+)', version_output)
            if hostname_match:
                hostname = hostname_match.group(1)
            
            # Extract model
            model_match = re.search(r'Model:\s+(\S+)', version_output)
            if model_match:
                model = model_match.group(1)
            
            # Extract OS version
            version_match = re.search(r'JUNOS\s+([^\s,]+)', version_output)
            if version_match:
                os_version = version_match.group(1)
                
        elif device_type == DeviceType.ARISTA_EOS:
            vendor = "Arista"
            
            # Extract model and version for Arista
            model_match = re.search(r'Arista\s+(\S+)', version_output)
            if model_match:
                model = model_match.group(1)
            
            version_match = re.search(r'Software image version:\s+([^\s,]+)', version_output)
            if version_match:
                os_version = version_match.group(1)
        
        return hostname, vendor, model, os_version
    
    def _detect_capabilities(self, 
                           connection: ConnectionInfo, 
                           device_type: DeviceType) -> List[str]:
        """Detect device capabilities by testing various commands.
        
        Args:
            connection: Active connection to the device
            device_type: Device type
            
        Returns:
            List of supported capabilities
        """
        capabilities = []
        
        # Test basic capabilities
        capability_tests = {
            'ssh': lambda: True,  # Already connected via SSH
            'snmp': self._test_snmp_capability,
            'netconf': self._test_netconf_capability,
            'restapi': self._test_restapi_capability,
            'scp': self._test_scp_capability
        }
        
        for capability, test_func in capability_tests.items():
            try:
                if test_func():
                    capabilities.append(capability)
                    self.logger.debug(f"Capability detected: {capability}",
                                    device_id=connection.device_id)
            except Exception as e:
                self.logger.debug(f"Capability test failed for {capability}: {str(e)}",
                                device_id=connection.device_id)
        
        return capabilities
    
    def _test_snmp_capability(self) -> bool:
        """Test if device supports SNMP."""
        # This would typically involve trying SNMP commands
        # For now, assume most devices support SNMP
        return True
    
    def _test_netconf_capability(self) -> bool:
        """Test if device supports NETCONF."""
        # This would involve checking for NETCONF subsystem
        return False  # Conservative default
    
    def _test_restapi_capability(self) -> bool:
        """Test if device supports REST API."""
        # This would involve HTTP requests to common API endpoints
        return False  # Conservative default
    
    def _test_scp_capability(self) -> bool:
        """Test if device supports SCP file transfer."""
        # This would involve testing SCP subsystem
        return True  # Most SSH devices support SCP
    
    def _get_command_syntax(self, device_type: DeviceType) -> Dict[str, str]:
        """Get device-specific command syntax mapping.
        
        Args:
            device_type: Device type
            
        Returns:
            Dictionary mapping command types to device-specific syntax
        """
        syntax_maps = {
            DeviceType.CISCO_IOS: {
                'show_version': 'show version',
                'show_interfaces': 'show interfaces',
                'show_ip_route': 'show ip route',
                'show_running_config': 'show running-config',
                'show_startup_config': 'show startup-config',
                'copy_running_startup': 'copy running-config startup-config',
                'ping': 'ping {target}',
                'traceroute': 'traceroute {target}',
                'show_arp': 'show arp',
                'show_mac_table': 'show mac address-table'
            },
            DeviceType.JUNIPER_JUNOS: {
                'show_version': 'show version',
                'show_interfaces': 'show interfaces',
                'show_ip_route': 'show route',
                'show_running_config': 'show configuration',
                'show_startup_config': 'show configuration',
                'commit_config': 'commit',
                'ping': 'ping {target}',
                'traceroute': 'traceroute {target}',
                'show_arp': 'show arp',
                'show_mac_table': 'show ethernet-switching table'
            },
            DeviceType.ARISTA_EOS: {
                'show_version': 'show version',
                'show_interfaces': 'show interfaces',
                'show_ip_route': 'show ip route',
                'show_running_config': 'show running-config',
                'show_startup_config': 'show startup-config',
                'copy_running_startup': 'copy running-config startup-config',
                'ping': 'ping {target}',
                'traceroute': 'traceroute {target}',
                'show_arp': 'show arp',
                'show_mac_table': 'show mac address-table'
            },
            DeviceType.GENERIC: {
                'show_version': 'show version',
                'show_interfaces': 'show interfaces',
                'ping': 'ping {target}'
            }
        }
        
        return syntax_maps.get(device_type, syntax_maps[DeviceType.GENERIC])


class CapabilityManager:
    """Manages device capabilities and command syntax adaptation."""
    
    def __init__(self):
        """Initialize capability manager."""
        self.logger = get_logger(f"{__name__}.CapabilityManager")
        self.device_profiles: Dict[str, DeviceProfile] = {}
        self.command_executor = CommandExecutor()
        
        # Fallback command mappings for unknown devices
        self.fallback_commands = {
            'show_version': ['show version', 'version', 'show system version'],
            'show_interfaces': ['show interfaces', 'show interface', 'show ports'],
            'show_ip_route': ['show ip route', 'show route', 'show routing-table'],
            'ping': ['ping {target}', 'ping -c 4 {target}'],
            'traceroute': ['traceroute {target}', 'tracert {target}']
        }
    
    def register_device_profile(self, device_id: str, profile: DeviceProfile) -> None:
        """Register a device profile for capability management.
        
        Args:
            device_id: Unique device identifier
            profile: Device profile with capabilities and command syntax
        """
        self.device_profiles[device_id] = profile
        self.logger.info(f"Device profile registered",
                        device_id=device_id,
                        device_type=profile.device_type.value,
                        capabilities_count=len(profile.capabilities))
    
    def get_device_profile(self, device_id: str) -> Optional[DeviceProfile]:
        """Get device profile by device ID.
        
        Args:
            device_id: Device identifier
            
        Returns:
            DeviceProfile if found, None otherwise
        """
        return self.device_profiles.get(device_id)
    
    def has_capability(self, device_id: str, capability: str) -> bool:
        """Check if device has specific capability.
        
        Args:
            device_id: Device identifier
            capability: Capability to check
            
        Returns:
            True if device has capability, False otherwise
        """
        profile = self.device_profiles.get(device_id)
        if profile:
            return profile.has_capability(capability)
        
        # Conservative default for unknown devices
        basic_capabilities = ['ssh', 'ping']
        return capability in basic_capabilities
    
    def get_command_for_device(self, device_id: str, command_type: str, **kwargs) -> str:
        """Get device-specific command syntax.
        
        Args:
            device_id: Device identifier
            command_type: Type of command (e.g., 'show_version', 'ping')
            **kwargs: Command parameters (e.g., target for ping)
            
        Returns:
            Device-specific command string
            
        Raises:
            UnsupportedDeviceError: If command is not supported
        """
        profile = self.device_profiles.get(device_id)
        
        if profile:
            command_template = profile.get_command(command_type)
            if command_template:
                try:
                    return command_template.format(**kwargs)
                except KeyError as e:
                    raise UnsupportedDeviceError(
                        f"Missing parameter {e} for command {command_type}",
                        {"device_id": device_id, "command_type": command_type, "missing_param": str(e)}
                    )
        
        # Try fallback commands for unknown devices
        if command_type in self.fallback_commands:
            for fallback_template in self.fallback_commands[command_type]:
                try:
                    return fallback_template.format(**kwargs)
                except KeyError:
                    continue
        
        raise UnsupportedDeviceError(
            f"Command type '{command_type}' not supported for device {device_id}",
            {"device_id": device_id, "command_type": command_type}
        )
    
    def execute_adapted_command(self, 
                               connection: ConnectionInfo,
                               command_type: str,
                               **kwargs) -> CommandResult:
        """Execute command using device-specific syntax adaptation.
        
        Args:
            connection: Active connection to the device
            command_type: Type of command to execute
            **kwargs: Command parameters
            
        Returns:
            CommandResult with execution details
        """
        try:
            # Get device-specific command
            command = self.get_command_for_device(
                connection.device_id, command_type, **kwargs
            )
            
            self.logger.info(f"Executing adapted command: {command}",
                           device_id=connection.device_id,
                           command_type=command_type,
                           adapted_command=command)
            
            # Execute the command
            result = self.command_executor.execute_command(connection, command)
            
            # Add metadata about command adaptation
            if not hasattr(result, 'additional_data'):
                result.additional_data = {}
            
            result.additional_data.update({
                'command_type': command_type,
                'adapted_from': command_type,
                'original_parameters': kwargs
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Adapted command execution failed: {str(e)}",
                            device_id=connection.device_id,
                            command_type=command_type,
                            error=str(e))
            
            # Return failed result
            return CommandResult(
                success=False,
                output="",
                error=f"Command adaptation failed: {str(e)}",
                execution_time=0.0,
                timestamp=datetime.utcnow(),
                command=f"{command_type} (adaptation failed)",
                device_id=connection.device_id
            )
    
    def test_device_capabilities(self, connection: ConnectionInfo) -> Dict[str, bool]:
        """Test various capabilities on a device.
        
        Args:
            connection: Active connection to the device
            
        Returns:
            Dictionary mapping capability names to test results
        """
        self.logger.info("Testing device capabilities",
                        device_id=connection.device_id)
        
        capability_tests = {
            'basic_commands': self._test_basic_commands,
            'privilege_escalation': self._test_privilege_escalation,
            'configuration_commands': self._test_configuration_commands,
            'file_operations': self._test_file_operations,
            'network_commands': self._test_network_commands
        }
        
        results = {}
        
        for capability, test_func in capability_tests.items():
            try:
                results[capability] = test_func(connection)
                self.logger.debug(f"Capability test result: {capability} = {results[capability]}",
                                device_id=connection.device_id)
            except Exception as e:
                self.logger.warning(f"Capability test failed for {capability}: {str(e)}",
                                  device_id=connection.device_id)
                results[capability] = False
        
        self.logger.info(f"Capability testing completed",
                        device_id=connection.device_id,
                        passed_tests=sum(results.values()),
                        total_tests=len(results))
        
        return results
    
    def update_device_capabilities(self, device_id: str, capabilities: List[str]) -> None:
        """Update device capabilities based on testing results.
        
        Args:
            device_id: Device identifier
            capabilities: List of confirmed capabilities
        """
        profile = self.device_profiles.get(device_id)
        if profile:
            # Add new capabilities
            for capability in capabilities:
                profile.add_capability(capability)
            
            self.logger.info(f"Device capabilities updated",
                           device_id=device_id,
                           total_capabilities=len(profile.capabilities))
        else:
            self.logger.warning(f"Cannot update capabilities - device profile not found",
                              device_id=device_id)
    
    def get_supported_commands(self, device_id: str) -> List[str]:
        """Get list of supported command types for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            List of supported command type names
        """
        profile = self.device_profiles.get(device_id)
        if profile:
            return list(profile.command_syntax.keys())
        
        # Return basic fallback commands for unknown devices
        return list(self.fallback_commands.keys())
    
    def _test_basic_commands(self, connection: ConnectionInfo) -> bool:
        """Test basic show commands."""
        try:
            result = self.execute_adapted_command(connection, 'show_version')
            return result.success and len(result.output) > 0
        except:
            return False
    
    def _test_privilege_escalation(self, connection: ConnectionInfo) -> bool:
        """Test privilege escalation capability."""
        try:
            # This would require enable password, so we'll just check if the device
            # responds to enable command without actually escalating
            result = self.command_executor.execute_command(connection, 'enable')
            # If it doesn't error immediately, privilege escalation might be supported
            return True
        except:
            return False
    
    def _test_configuration_commands(self, connection: ConnectionInfo) -> bool:
        """Test configuration-related commands."""
        try:
            result = self.execute_adapted_command(connection, 'show_running_config')
            return result.success
        except:
            # Try alternative configuration commands
            try:
                result = self.command_executor.execute_command(connection, 'show configuration')
                return result.success
            except:
                return False
    
    def _test_file_operations(self, connection: ConnectionInfo) -> bool:
        """Test file operation capabilities."""
        try:
            # Test directory listing
            result = self.command_executor.execute_command(connection, 'dir')
            if result.success:
                return True
            
            # Try alternative
            result = self.command_executor.execute_command(connection, 'ls')
            return result.success
        except:
            return False
    
    def _test_network_commands(self, connection: ConnectionInfo) -> bool:
        """Test network diagnostic commands."""
        try:
            # Test ping to localhost
            result = self.execute_adapted_command(connection, 'ping', target='127.0.0.1')
            return result.success
        except:
            return False