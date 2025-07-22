"""
Tests for NetArchon Configuration Management Module
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.netarchon.core.config_manager import ConfigManager
from src.netarchon.models.connection import ConnectionInfo, CommandResult, ConnectionType, ConnectionStatus
from src.netarchon.models.device import DeviceType
from src.netarchon.utils.exceptions import ConfigurationError


class TestConfigManager:
    """Test ConfigManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ConfigManager(backup_directory=self.temp_dir)
        
        # Create test connection
        self.connection = ConnectionInfo(
            device_id="test_router",
            host="192.168.1.1",
            port=22,
            username="admin",
            connection_type=ConnectionType.SSH,
            established_at=datetime.now(),
            last_activity=datetime.now(),
            status=ConnectionStatus.CONNECTED
        )
        self.connection.device_type = DeviceType.CISCO_IOS
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manager_initialization(self):
        """Test ConfigManager initialization."""
        manager = ConfigManager()
        assert manager.backup_directory == "backups"
        assert manager.command_executor is not None
        assert len(manager.config_commands) == 5  # All device types
    
    def test_manager_initialization_custom_directory(self):
        """Test ConfigManager initialization with custom directory."""
        custom_dir = "/tmp/test_backups"
        manager = ConfigManager(backup_directory=custom_dir)
        assert manager.backup_directory == custom_dir
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_backup_config_success(self, mock_executor_class):
        """Test successful configuration backup."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock successful show config result
        config_content = """version 15.1
hostname test_router
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
!
end"""
        
        success_result = CommandResult(
            success=True,
            output=config_content,
            error="",
            execution_time=1.0,
            timestamp=datetime.now(),
            command="show running-config",
            device_id="test_router"
        )
        mock_executor.execute_command.return_value = success_result
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test backup
        backup_path = manager.backup_config(self.connection, "Test backup")
        
        # Verify backup was created
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert "test_router" in backup_path
        
        # Verify backup content
        with open(backup_path, 'r') as f:
            backup_content = f.read()
            assert "NetArchon Configuration Backup" in backup_content
            assert "test_router" in backup_content
            assert "Test backup" in backup_content
            assert config_content in backup_content
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_backup_config_command_failure(self, mock_executor_class):
        """Test configuration backup with command failure."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock failed show config result
        failed_result = CommandResult(
            success=False,
            output="",
            error="Command failed",
            execution_time=1.0,
            timestamp=datetime.now(),
            command="show running-config",
            device_id="test_router"
        )
        mock_executor.execute_command.return_value = failed_result
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test backup should raise exception
        with pytest.raises(ConfigurationError):
            manager.backup_config(self.connection, "Test backup")
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_backup_config_exception(self, mock_executor_class):
        """Test configuration backup with executor exception."""
        # Mock command executor to raise exception
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.execute_command.side_effect = Exception("Connection lost")
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test backup should raise ConfigurationError
        with pytest.raises(ConfigurationError):
            manager.backup_config(self.connection, "Test backup")
    
    def test_validate_config_syntax_cisco_valid(self):
        """Test valid Cisco configuration validation."""
        cisco_config = """version 15.1
hostname test_router
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
!
end"""
        
        result = self.manager.validate_config_syntax(cisco_config, DeviceType.CISCO_IOS)
        assert result is True
    
    def test_validate_config_syntax_juniper_valid(self):
        """Test valid Juniper configuration validation."""
        juniper_config = """system {
    host-name test_router;
}
interfaces {
    ge-0/0/0 {
        unit 0 {
            family inet {
                address 192.168.1.1/24;
            }
        }
    }
}"""
        
        result = self.manager.validate_config_syntax(juniper_config, DeviceType.JUNIPER_JUNOS)
        assert result is True
    
    def test_validate_config_syntax_empty(self):
        """Test empty configuration validation."""
        result = self.manager.validate_config_syntax("", DeviceType.CISCO_IOS)
        assert result is False
        
        result = self.manager.validate_config_syntax(None, DeviceType.CISCO_IOS)
        assert result is False
    
    def test_validate_config_syntax_too_short(self):
        """Test configuration that is too short."""
        short_config = "version 15.1\nhostname router"
        result = self.manager.validate_config_syntax(short_config, DeviceType.CISCO_IOS)
        assert result is False
    
    def test_device_type_commands(self):
        """Test device-specific command mappings."""
        # Test all device types have required commands
        for device_type in [DeviceType.CISCO_IOS, DeviceType.CISCO_NXOS, 
                           DeviceType.JUNIPER_JUNOS, DeviceType.ARISTA_EOS, DeviceType.GENERIC]:
            assert device_type in self.manager.config_commands
            assert 'show_config' in self.manager.config_commands[device_type]
            assert 'save_config' in self.manager.config_commands[device_type]
    
    def test_backup_directory_creation(self):
        """Test backup directory creation."""
        test_dir = os.path.join(self.temp_dir, "new_backup_dir")
        manager = ConfigManager(backup_directory=test_dir)
        assert os.path.exists(test_dir)