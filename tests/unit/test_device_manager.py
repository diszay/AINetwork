"""
Unit tests for NetArchon device manager.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.netarchon.core.device_manager import DeviceDetector
from src.netarchon.models.device import DeviceInfo, DeviceProfile, DeviceType, DeviceStatus
from src.netarchon.models.connection import (
    ConnectionInfo,
    ConnectionType,
    ConnectionStatus,
    CommandResult
)
from src.netarchon.utils.exceptions import DeviceError


class TestDeviceDetector:
    """Test DeviceDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = DeviceDetector()
        self.connection = ConnectionInfo(
            device_id="router1",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status=ConnectionStatus.CONNECTED
        )
    
    def test_detector_initialization(self):
        """Test device detector initialization."""
        detector = DeviceDetector()
        assert detector.logger is not None
        assert detector.command_executor is not None
        assert len(detector.detection_patterns) > 0
        assert DeviceType.CISCO_IOS in detector.detection_patterns
        assert DeviceType.JUNIPER_JUNOS in detector.detection_patterns
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_detect_cisco_ios_device(self, mock_executor_class):
        """Test detection of Cisco IOS device."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock version command response
        cisco_version_output = """
        Cisco IOS Software, C2900 Software (C2900-UNIVERSALK9-M), Version 15.1(4)M4
        Technical Support: http://www.cisco.com/techsupport
        Copyright (c) 1986-2012 by Cisco Systems, Inc.
        """
        
        version_result = CommandResult(
            success=True,
            output=cisco_version_output,
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = version_result
        
        # Create new detector to use mocked executor
        detector = DeviceDetector()
        
        device_type = detector.detect_device_type(self.connection)
        
        assert device_type == DeviceType.CISCO_IOS
        mock_executor.execute_command.assert_called()
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_detect_juniper_device(self, mock_executor_class):
        """Test detection of Juniper device."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        juniper_version_output = """
        Hostname: mx-router
        Model: MX240
        JUNOS Base OS boot [12.3R2.5]
        JUNOS Base OS Software Suite [12.3R2.5]
        """
        
        version_result = CommandResult(
            success=True,
            output=juniper_version_output,
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = version_result
        
        detector = DeviceDetector()
        device_type = detector.detect_device_type(self.connection)
        
        assert device_type == DeviceType.JUNIPER_JUNOS
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_detect_arista_device(self, mock_executor_class):
        """Test detection of Arista device."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        arista_version_output = """
        Arista DCS-7050S-64
        Hardware version:    01.00
        Serial number:       JPE12345678
        Software image version: 4.14.5F
        Architecture:           i386
        """
        
        version_result = CommandResult(
            success=True,
            output=arista_version_output,
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = version_result
        
        detector = DeviceDetector()
        device_type = detector.detect_device_type(self.connection)
        
        assert device_type == DeviceType.ARISTA_EOS
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_detect_generic_device(self, mock_executor_class):
        """Test detection falls back to generic for unknown devices."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock unknown device output
        unknown_version_output = "Unknown device version information"
        
        version_result = CommandResult(
            success=True,
            output=unknown_version_output,
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = version_result
        
        detector = DeviceDetector()
        device_type = detector.detect_device_type(self.connection)
        
        assert device_type == DeviceType.GENERIC
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_detect_device_command_failure(self, mock_executor_class):
        """Test device detection when commands fail."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock failed command
        failed_result = CommandResult(
            success=False,
            output="",
            error="Command failed",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = failed_result
        
        detector = DeviceDetector()
        device_type = detector.detect_device_type(self.connection)
        
        assert device_type == DeviceType.GENERIC
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_get_device_info_cisco(self, mock_executor_class):
        """Test getting device info for Cisco device."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        cisco_version_output = """
        router1 uptime is 5 weeks, 2 days, 3 hours, 45 minutes
        System returned to ROM by power-on
        System restarted at 09:32:15 UTC Wed Mar 3 1993
        System image file is "flash:c2900-universalk9-mz.SPA.151-4.M4.bin"
        
        cisco ISR4321 (1RU) processor with 1863679K/6147K bytes of memory.
        Processor board ID FDO1728W0ME
        2 Gigabit Ethernet interfaces
        DRAM configuration is 64 bits wide with parity disabled.
        255K bytes of non-volatile configuration memory.
        4194304K bytes of physical memory.
        
        Configuration register is 0x2102
        """
        
        version_result = CommandResult(
            success=True,
            output=cisco_version_output,
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = version_result
        
        detector = DeviceDetector()
        device_info = detector.get_device_info(self.connection)
        
        assert isinstance(device_info, DeviceInfo)
        assert device_info.hostname == "router1"
        assert device_info.ip_address == "192.168.1.1"
        assert device_info.device_type == DeviceType.CISCO_IOS
        assert device_info.vendor == "Cisco"
        assert device_info.model == "ISR4321"
        assert device_info.status == DeviceStatus.ONLINE
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_get_device_info_command_failure(self, mock_executor_class):
        """Test device info gathering when version command fails."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        failed_result = CommandResult(
            success=False,
            output="",
            error="Command failed",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = failed_result
        
        detector = DeviceDetector()
        
        with pytest.raises(DeviceError) as exc_info:
            detector.get_device_info(self.connection)
        
        assert "Failed to get version information" in str(exc_info.value)
    
    @patch('src.netarchon.core.device_manager.CommandExecutor')
    def test_create_device_profile_cisco(self, mock_executor_class):
        """Test creating device profile for Cisco device."""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        cisco_version_output = """
        Cisco IOS Software, ISR4300 Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
        Version 16.09.04, RELEASE SOFTWARE (fc2)
        cisco ISR4321 (1RU) processor with 1863679K/6147K bytes of memory.
        """
        
        version_result = CommandResult(
            success=True,
            output=cisco_version_output,
            error="",
            execution_time=1.0,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
        
        mock_executor.execute_command.return_value = version_result
        
        detector = DeviceDetector()
        profile = detector.create_device_profile(self.connection)
        
        assert isinstance(profile, DeviceProfile)
        assert profile.device_type == DeviceType.CISCO_IOS
        assert profile.vendor == "Cisco"
        assert profile.model == "ISR4321"
        assert len(profile.capabilities) > 0
        assert 'ssh' in profile.capabilities
        assert len(profile.command_syntax) > 0
        assert 'show_version' in profile.command_syntax
        assert profile.command_syntax['show_version'] == 'show version'
    
    def test_calculate_detection_score_high(self):
        """Test detection score calculation with high confidence."""
        patterns = {
            'version_patterns': [r'Cisco IOS Software'],
            'commands': ['show version']
        }
        
        with patch.object(self.detector.command_executor, 'execute_command') as mock_exec:
            mock_exec.return_value = CommandResult(
                success=True,
                output="Cisco IOS Software, Version 15.1",
                error="",
                execution_time=1.0,
                timestamp=datetime.utcnow(),
                command="show version",
                device_id="router1"
            )
            
            score = self.detector._calculate_detection_score(
                self.connection, DeviceType.CISCO_IOS, patterns
            )
            
            assert score > 0
            assert score <= 100
    
    def test_calculate_detection_score_zero(self):
        """Test detection score calculation with no matches."""
        patterns = {
            'version_patterns': [r'NonExistentPattern'],
            'commands': ['show version']
        }
        
        with patch.object(self.detector.command_executor, 'execute_command') as mock_exec:
            mock_exec.return_value = CommandResult(
                success=True,
                output="Some other device output",
                error="",
                execution_time=1.0,
                timestamp=datetime.utcnow(),
                command="show version",
                device_id="router1"
            )
            
            score = self.detector._calculate_detection_score(
                self.connection, DeviceType.CISCO_IOS, patterns
            )
            
            assert score == 0
    
    def test_parse_device_info_cisco(self):
        """Test parsing Cisco device information."""
        version_output = """
        router1 uptime is 5 weeks, 2 days, 3 hours, 45 minutes
        cisco ISR4321 (1RU) processor with memory.
        Cisco IOS Software, Version 16.09.04
        """
        
        hostname, vendor, model, os_version = self.detector._parse_device_info(
            version_output, DeviceType.CISCO_IOS
        )
        
        assert hostname == "router1"
        assert vendor == "Cisco"
        assert model == "ISR4321"
        assert os_version == "16.09.04"
    
    def test_parse_device_info_juniper(self):
        """Test parsing Juniper device information."""
        version_output = """
        Hostname: mx-router
        Model: MX240
        JUNOS Base OS boot [12.3R2.5]
        """
        
        hostname, vendor, model, os_version = self.detector._parse_device_info(
            version_output, DeviceType.JUNIPER_JUNOS
        )
        
        assert hostname == "mx-router"
        assert vendor == "Juniper"
        assert model == "MX240"
        assert os_version == "12.3R2.5"
    
    def test_parse_device_info_arista(self):
        """Test parsing Arista device information."""
        version_output = """
        Arista DCS-7050S-64
        Software image version: 4.14.5F
        """
        
        hostname, vendor, model, os_version = self.detector._parse_device_info(
            version_output, DeviceType.ARISTA_EOS
        )
        
        assert hostname == ""  # No hostname in this output
        assert vendor == "Arista"
        assert model == "DCS-7050S-64"
        assert os_version == "4.14.5F"
    
    def test_detect_capabilities(self):
        """Test capability detection."""
        capabilities = self.detector._detect_capabilities(
            self.connection, DeviceType.CISCO_IOS
        )
        
        assert isinstance(capabilities, list)
        assert 'ssh' in capabilities  # Should always be present since we're connected via SSH
        assert 'snmp' in capabilities  # Default assumption
        assert 'scp' in capabilities   # Default assumption
    
    def test_get_command_syntax_cisco(self):
        """Test getting Cisco command syntax."""
        syntax = self.detector._get_command_syntax(DeviceType.CISCO_IOS)
        
        assert isinstance(syntax, dict)
        assert 'show_version' in syntax
        assert syntax['show_version'] == 'show version'
        assert 'show_interfaces' in syntax
        assert syntax['show_interfaces'] == 'show interfaces'
        assert 'ping' in syntax
        assert '{target}' in syntax['ping']
    
    def test_get_command_syntax_juniper(self):
        """Test getting Juniper command syntax."""
        syntax = self.detector._get_command_syntax(DeviceType.JUNIPER_JUNOS)
        
        assert isinstance(syntax, dict)
        assert 'show_version' in syntax
        assert syntax['show_version'] == 'show version'
        assert 'show_ip_route' in syntax
        assert syntax['show_ip_route'] == 'show route'
        assert 'commit_config' in syntax
    
    def test_get_command_syntax_generic(self):
        """Test getting generic command syntax."""
        syntax = self.detector._get_command_syntax(DeviceType.GENERIC)
        
        assert isinstance(syntax, dict)
        assert 'show_version' in syntax
        assert len(syntax) < 10  # Generic should have fewer commands
    
    def test_capability_test_methods(self):
        """Test individual capability test methods."""
        assert self.detector._test_snmp_capability() is True
        assert self.detector._test_netconf_capability() is False
        assert self.detector._test_restapi_capability() is False
        assert self.detector._test_scp_capability() is True