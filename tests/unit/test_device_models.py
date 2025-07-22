"""
Unit tests for NetArchon device models.
"""

import pytest
from datetime import datetime

from src.netarchon.models.device import (
    DeviceType,
    DeviceStatus,
    DeviceInfo,
    DeviceProfile
)


class TestDeviceType:
    """Test DeviceType enumeration."""
    
    def test_device_types(self):
        """Test all device types are defined."""
        assert DeviceType.CISCO_IOS.value == "cisco_ios"
        assert DeviceType.CISCO_NXOS.value == "cisco_nxos"
        assert DeviceType.JUNIPER_JUNOS.value == "juniper_junos"
        assert DeviceType.ARISTA_EOS.value == "arista_eos"
        assert DeviceType.GENERIC.value == "generic"


class TestDeviceStatus:
    """Test DeviceStatus enumeration."""
    
    def test_device_statuses(self):
        """Test all device statuses are defined."""
        assert DeviceStatus.ONLINE.value == "online"
        assert DeviceStatus.OFFLINE.value == "offline"
        assert DeviceStatus.UNREACHABLE.value == "unreachable"
        assert DeviceStatus.UNKNOWN.value == "unknown"


class TestDeviceInfo:
    """Test DeviceInfo dataclass."""
    
    def test_valid_device_info(self):
        """Test creating valid device info."""
        now = datetime.utcnow()
        device = DeviceInfo(
            hostname="router1",
            ip_address="192.168.1.1",
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            last_seen=now,
            status=DeviceStatus.ONLINE
        )
        
        assert device.hostname == "router1"
        assert device.ip_address == "192.168.1.1"
        assert device.device_type == DeviceType.CISCO_IOS
        assert device.vendor == "Cisco"
        assert device.model == "ISR4321"
        assert device.os_version == "16.09.04"
        assert device.last_seen == now
        assert device.status == DeviceStatus.ONLINE
    
    def test_empty_hostname_validation(self):
        """Test validation for empty hostname."""
        with pytest.raises(ValueError, match="Hostname cannot be empty"):
            DeviceInfo(
                hostname="",
                ip_address="192.168.1.1",
                device_type=DeviceType.CISCO_IOS,
                vendor="Cisco",
                model="ISR4321",
                os_version="16.09.04",
                last_seen=datetime.utcnow(),
                status=DeviceStatus.ONLINE
            )
    
    def test_empty_ip_validation(self):
        """Test validation for empty IP address."""
        with pytest.raises(ValueError, match="IP address cannot be empty"):
            DeviceInfo(
                hostname="router1",
                ip_address="",
                device_type=DeviceType.CISCO_IOS,
                vendor="Cisco",
                model="ISR4321",
                os_version="16.09.04",
                last_seen=datetime.utcnow(),
                status=DeviceStatus.ONLINE
            )
    
    def test_is_online(self):
        """Test is_online method."""
        device = DeviceInfo(
            hostname="router1",
            ip_address="192.168.1.1",
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            last_seen=datetime.utcnow(),
            status=DeviceStatus.ONLINE
        )
        
        assert device.is_online() is True
        
        device.status = DeviceStatus.OFFLINE
        assert device.is_online() is False
    
    def test_update_status(self):
        """Test update_status method."""
        device = DeviceInfo(
            hostname="router1",
            ip_address="192.168.1.1",
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            last_seen=datetime.utcnow(),
            status=DeviceStatus.UNKNOWN
        )
        
        old_time = device.last_seen
        device.update_status(DeviceStatus.ONLINE)
        
        assert device.status == DeviceStatus.ONLINE
        assert device.last_seen > old_time


class TestDeviceProfile:
    """Test DeviceProfile dataclass."""
    
    def test_valid_device_profile(self):
        """Test creating valid device profile."""
        capabilities = ["ssh", "snmp", "netconf"]
        commands = {"show_version": "show version", "show_interfaces": "show interfaces"}
        
        profile = DeviceProfile(
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            capabilities=capabilities,
            command_syntax=commands
        )
        
        assert profile.device_type == DeviceType.CISCO_IOS
        assert profile.vendor == "Cisco"
        assert profile.model == "ISR4321"
        assert profile.os_version == "16.09.04"
        assert profile.capabilities == capabilities
        assert profile.command_syntax == commands
    
    def test_empty_capabilities_initialization(self):
        """Test initialization with empty capabilities."""
        profile = DeviceProfile(
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            capabilities=None,
            command_syntax=None
        )
        
        assert profile.capabilities == []
        assert profile.command_syntax == {}
    
    def test_has_capability(self):
        """Test has_capability method."""
        profile = DeviceProfile(
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            capabilities=["ssh", "snmp"],
            command_syntax={}
        )
        
        assert profile.has_capability("ssh") is True
        assert profile.has_capability("netconf") is False
    
    def test_get_command(self):
        """Test get_command method."""
        commands = {"show_version": "show version"}
        profile = DeviceProfile(
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            capabilities=[],
            command_syntax=commands
        )
        
        assert profile.get_command("show_version") == "show version"
        assert profile.get_command("nonexistent") is None
    
    def test_add_capability(self):
        """Test add_capability method."""
        profile = DeviceProfile(
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            capabilities=["ssh"],
            command_syntax={}
        )
        
        profile.add_capability("snmp")
        assert "snmp" in profile.capabilities
        
        # Test duplicate addition
        profile.add_capability("ssh")
        assert profile.capabilities.count("ssh") == 1
    
    def test_set_command_syntax(self):
        """Test set_command_syntax method."""
        profile = DeviceProfile(
            device_type=DeviceType.CISCO_IOS,
            vendor="Cisco",
            model="ISR4321",
            os_version="16.09.04",
            capabilities=[],
            command_syntax={}
        )
        
        profile.set_command_syntax("show_version", "show version")
        assert profile.command_syntax["show_version"] == "show version"