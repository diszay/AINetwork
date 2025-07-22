"""
Tests for NetArchon Configuration Deployment and Rollback
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime

from src.netarchon.core.config_manager import ConfigManager
from src.netarchon.models.connection import ConnectionInfo, CommandResult, ConnectionType, ConnectionStatus
from src.netarchon.models.device import DeviceType
from src.netarchon.utils.exceptions import ConfigurationError


class TestConfigDeployment:
    """Test ConfigManager deployment and rollback functionality."""
    
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
        
        # Sample configuration content
        self.config_content = """hostname test_router
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
!
end"""
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_apply_config_success(self, mock_executor_class):
        """Test successful configuration application."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock successful command results
        def mock_execute_command(connection, command, timeout=30):
            if 'show version' in command:
                return CommandResult(True, "Cisco IOS Software", "", 1.0, datetime.now(), command, "test_router")
            elif 'show running-config' in command:
                return CommandResult(True, "Current config", "", 1.0, datetime.now(), command, "test_router")
            elif 'configure terminal' in command:
                return CommandResult(True, "Config mode", "", 1.0, datetime.now(), command, "test_router")
            elif 'copy running-config' in command:
                return CommandResult(True, "Config saved", "", 1.0, datetime.now(), command, "test_router")
            else:
                return CommandResult(True, "OK", "", 1.0, datetime.now(), command, "test_router")
        
        mock_executor.execute_command.side_effect = mock_execute_command
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test configuration application
        result = manager.apply_config(self.connection, self.config_content)
        
        # Verify result
        assert result is True
        
        # Verify backup was created
        backup_calls = [call for call in mock_executor.execute_command.call_args_list 
                       if 'show running-config' in str(call)]
        assert len(backup_calls) >= 1  # Backup call made
        
        # Verify configuration commands were executed
        config_calls = [call for call in mock_executor.execute_command.call_args_list 
                       if 'configure terminal' in str(call)]
        assert len(config_calls) >= 1  # Configuration mode entered
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_apply_config_validation_failure(self, mock_executor_class):
        """Test configuration application with validation failure."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Create manager with mocked executor - bypass backup for this test
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test with invalid configuration (too short)
        invalid_config = "hostname test"
        
        # Should raise ConfigurationError due to validation failure
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            manager.apply_config(self.connection, invalid_config, backup_first=False)
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_apply_config_connectivity_failure(self, mock_executor_class):
        """Test configuration application with connectivity failure."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock connectivity test failure
        mock_executor.execute_command.return_value = CommandResult(
            False, "", "Connection failed", 1.0, datetime.now(), "show version", "test_router"
        )
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Should raise ConfigurationError due to connectivity failure
        with pytest.raises(ConfigurationError, match="Device connectivity test failed before deployment"):
            manager.apply_config(self.connection, self.config_content, backup_first=False)
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_apply_config_no_backup(self, mock_executor_class):
        """Test configuration application without backup."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock successful command results
        def mock_execute_command(connection, command, timeout=30):
            if 'show version' in command:
                return CommandResult(True, "Cisco IOS Software", "", 1.0, datetime.now(), command, "test_router")
            elif 'configure terminal' in command:
                return CommandResult(True, "Config mode", "", 1.0, datetime.now(), command, "test_router")
            elif 'copy running-config' in command:
                return CommandResult(True, "Config saved", "", 1.0, datetime.now(), command, "test_router")
            else:
                return CommandResult(True, "OK", "", 1.0, datetime.now(), command, "test_router")
        
        mock_executor.execute_command.side_effect = mock_execute_command
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test configuration application without backup
        result = manager.apply_config(self.connection, self.config_content, backup_first=False)
        
        # Verify result
        assert result is True
        
        # Verify no backup calls were made
        backup_calls = [call for call in mock_executor.execute_command.call_args_list 
                       if 'show running-config' in str(call) and len(call[0]) == 2]
        assert len(backup_calls) == 0  # No backup calls
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_apply_config_command_failures(self, mock_executor_class):
        """Test configuration application with some command failures."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock command results with some failures
        def mock_execute_command(connection, command, timeout=30):
            if 'show version' in command:
                return CommandResult(True, "Cisco IOS Software", "", 1.0, datetime.now(), command, "test_router")
            elif 'show running-config' in command:
                return CommandResult(True, "Current config", "", 1.0, datetime.now(), command, "test_router")
            elif 'configure terminal' in command:
                return CommandResult(True, "Config mode", "", 1.0, datetime.now(), command, "test_router")
            elif 'router ospf' in command:
                return CommandResult(False, "", "OSPF not supported", 1.0, datetime.now(), command, "test_router")
            else:
                return CommandResult(True, "OK", "", 1.0, datetime.now(), command, "test_router")
        
        mock_executor.execute_command.side_effect = mock_execute_command
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test configuration application
        result = manager.apply_config(self.connection, self.config_content)
        
        # Should return False due to failed commands
        assert result is False
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_rollback_config_success(self, mock_executor_class):
        """Test successful configuration rollback."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Create a test backup file
        backup_content = """# NetArchon Configuration Backup
# Device: test_router
# Timestamp: 2025-07-22T10:00:00
# Reason: Test backup
# Checksum: abc123
# Command: show running-config
# ==================================================

hostname old_router
interface GigabitEthernet0/0
 ip address 192.168.2.1 255.255.255.0
!
end"""
        
        backup_path = os.path.join(self.temp_dir, "test_backup.txt")
        with open(backup_path, 'w') as f:
            f.write(backup_content)
        
        # Mock successful command results for rollback
        def mock_execute_command(connection, command, timeout=30):
            return CommandResult(True, "OK", "", 1.0, datetime.now(), command, "test_router")
        
        mock_executor.execute_command.side_effect = mock_execute_command
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test rollback
        result = manager.rollback_config(self.connection, backup_path)
        
        # Verify result
        assert result is True
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_rollback_config_file_not_found(self, mock_executor_class):
        """Test rollback with non-existent backup file."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test rollback with non-existent file
        non_existent_path = os.path.join(self.temp_dir, "non_existent.txt")
        
        with pytest.raises(ConfigurationError, match="Backup file not found"):
            manager.rollback_config(self.connection, non_existent_path)
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_rollback_config_invalid_format(self, mock_executor_class):
        """Test rollback with invalid backup file format."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Create invalid backup file (no separator)
        invalid_backup = """hostname old_router
interface GigabitEthernet0/0
 ip address 192.168.2.1 255.255.255.0"""
        
        backup_path = os.path.join(self.temp_dir, "invalid_backup.txt")
        with open(backup_path, 'w') as f:
            f.write(invalid_backup)
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test rollback with invalid format
        with pytest.raises(ConfigurationError, match="Invalid backup file format"):
            manager.rollback_config(self.connection, backup_path)
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_connectivity_test_success(self, mock_executor_class):
        """Test successful connectivity test."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock successful show version command
        mock_executor.execute_command.return_value = CommandResult(
            True, "Cisco IOS Software", "", 1.0, datetime.now(), "show version", "test_router"
        )
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test connectivity
        result = manager._test_connectivity(self.connection)
        
        assert result is True
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_connectivity_test_failure(self, mock_executor_class):
        """Test failed connectivity test."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock failed show version command
        mock_executor.execute_command.return_value = CommandResult(
            False, "", "Connection timeout", 1.0, datetime.now(), "show version", "test_router"
        )
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test connectivity
        result = manager._test_connectivity(self.connection)
        
        assert result is False
    
    @patch('src.netarchon.core.config_manager.CommandExecutor')
    def test_connectivity_test_exception(self, mock_executor_class):
        """Test connectivity test with exception."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock exception during command execution
        mock_executor.execute_command.side_effect = Exception("Network error")
        
        # Create manager with mocked executor
        manager = ConfigManager(backup_directory=self.temp_dir)
        manager.command_executor = mock_executor
        
        # Test connectivity
        result = manager._test_connectivity(self.connection)
        
        assert result is False