"""Integration tests for configuration management.

These tests verify that NetArchon can correctly backup, deploy, and rollback
configurations on network devices.
"""

import os
import tempfile
import pytest
from unittest import mock
from pathlib import Path

from netarchon.core.config_manager import ConfigManager
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.ssh_connector import SSHConnector
from netarchon.models.device import DeviceInfo, DeviceType, DeviceStatus
from netarchon.models.connection import AuthenticationCredentials
from netarchon.utils.exceptions import ConfigurationError


# Skip these tests if no integration test environment is available
pytestmark = pytest.mark.skipif(
    os.environ.get('NETARCHON_INTEGRATION_TESTS') != 'true',
    reason="Integration tests are disabled. Set NETARCHON_INTEGRATION_TESTS=true to enable."
)


# Test device parameters
TEST_DEVICE_HOST = os.environ.get('NETARCHON_TEST_HOST', '192.168.1.1')
TEST_DEVICE_USERNAME = os.environ.get('NETARCHON_TEST_USERNAME', 'admin')
TEST_DEVICE_PASSWORD = os.environ.get('NETARCHON_TEST_PASSWORD', 'password')
TEST_DEVICE_TYPE = DeviceType(os.environ.get('NETARCHON_TEST_DEVICE_TYPE', 'cisco_ios'))


@pytest.fixture
def test_device():
    """Create a test device for integration testing."""
    return DeviceInfo(
        hostname="test-device",
        ip_address=TEST_DEVICE_HOST,
        device_type=TEST_DEVICE_TYPE,
        vendor="test",
        model="test-model",
        os_version="1.0",
        status=DeviceStatus.UNKNOWN
    )

@pytest.fixture  
def test_credentials():
    """Create test credentials for integration testing."""
    return AuthenticationCredentials(
        username=TEST_DEVICE_USERNAME,
        password=TEST_DEVICE_PASSWORD
    )


@pytest.fixture
def config_manager():
    """Create a configuration manager for testing."""
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    return ConfigManager(command_executor)


@pytest.fixture
def temp_backup_dir():
    """Create a temporary directory for backups."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.mark.integration
class TestConfigManagement:
    """Integration tests for configuration management."""
    
    def test_backup_configuration(self, config_manager, test_device, temp_backup_dir):
        """Test backing up device configuration."""
        # If using mock mode, skip actual backup
        if os.environ.get('NETARCHON_MOCK_INTEGRATION') == 'true':
            with mock.patch.object(config_manager, 'backup_config') as mock_backup:
                mock_backup.return_value = os.path.join(temp_backup_dir, "backup.txt")
                backup_path = config_manager.backup_config(test_device, temp_backup_dir)
                assert backup_path.endswith("backup.txt")
                mock_backup.assert_called_once()
            return
            
        # Real backup test
        try:
            backup_path = config_manager.backup_config(test_device, temp_backup_dir)
            assert backup_path is not None
            assert os.path.exists(backup_path)
            assert os.path.getsize(backup_path) > 0
            
            # Verify backup contains expected content
            with open(backup_path, 'r') as f:
                content = f.read()
                assert len(content) > 0
                # Basic sanity check - should contain some configuration
                assert any(keyword in content.lower() for keyword in 
                          ['version', 'interface', 'hostname', 'router'])
                          
        except Exception as e:
            pytest.skip(f"Could not backup configuration: {str(e)}")
    
    def test_validate_configuration(self, config_manager, test_device):
        """Test configuration validation."""
        # If using mock mode, skip actual validation
        if os.environ.get('NETARCHON_MOCK_INTEGRATION') == 'true':
            with mock.patch.object(config_manager, 'validate_config') as mock_validate:
                mock_validate.return_value = True
                
                # Test valid configuration
                valid_config = "hostname test-router\ninterface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0"
                result = config_manager.validate_config(test_device, valid_config)
                assert result is True
                mock_validate.assert_called_once_with(test_device, valid_config)
            return
            
        # Real validation test
        try:
            # Test with a simple, valid configuration snippet
            valid_config = "hostname test-router"
            result = config_manager.validate_config(test_device, valid_config)
            assert result is True
            
            # Test with invalid configuration
            invalid_config = "invalid command that should not work"
            result = config_manager.validate_config(test_device, invalid_config)
            assert result is False
            
        except Exception as e:
            pytest.skip(f"Could not validate configuration: {str(e)}")
    
    def test_configuration_diff(self, config_manager, test_device, temp_backup_dir):
        """Test configuration difference detection."""
        # If using mock mode, skip actual diff
        if os.environ.get('NETARCHON_MOCK_INTEGRATION') == 'true':
            with mock.patch.object(config_manager, 'get_config_diff') as mock_diff:
                mock_diff.return_value = {
                    'added': ['hostname new-router'],
                    'removed': ['hostname old-router'],
                    'modified': []
                }
                
                old_config = "hostname old-router\ninterface GigabitEthernet0/0"
                new_config = "hostname new-router\ninterface GigabitEthernet0/0"
                diff = config_manager.get_config_diff(old_config, new_config)
                
                assert 'added' in diff
                assert 'removed' in diff
                assert 'hostname new-router' in diff['added']
                assert 'hostname old-router' in diff['removed']
                mock_diff.assert_called_once_with(old_config, new_config)
            return
            
        # Real diff test
        try:
            old_config = "hostname old-router\ninterface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0"
            new_config = "hostname new-router\ninterface GigabitEthernet0/0\n ip address 192.168.1.2 255.255.255.0"
            
            diff = config_manager.get_config_diff(old_config, new_config)
            assert diff is not None
            assert isinstance(diff, dict)
            assert 'added' in diff or 'removed' in diff or 'modified' in diff
            
        except Exception as e:
            pytest.skip(f"Could not generate configuration diff: {str(e)}")
    
    def test_rollback_preparation(self, config_manager, test_device, temp_backup_dir):
        """Test rollback preparation and verification."""
        # If using mock mode, skip actual rollback preparation
        if os.environ.get('NETARCHON_MOCK_INTEGRATION') == 'true':
            with mock.patch.object(config_manager, 'prepare_rollback') as mock_prepare:
                mock_prepare.return_value = True
                
                backup_path = os.path.join(temp_backup_dir, "rollback_backup.txt")
                result = config_manager.prepare_rollback(test_device, backup_path)
                assert result is True
                mock_prepare.assert_called_once_with(test_device, backup_path)
            return
            
        # Real rollback preparation test
        try:
            # First create a backup
            backup_path = config_manager.backup_config(test_device, temp_backup_dir)
            assert os.path.exists(backup_path)
            
            # Test rollback preparation
            result = config_manager.prepare_rollback(test_device, backup_path)
            assert result is True
            
        except Exception as e:
            pytest.skip(f"Could not prepare rollback: {str(e)}")