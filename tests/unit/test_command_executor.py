"""
Unit tests for NetArchon command executor.
"""

import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.netarchon.core.command_executor import (
    CommandExecutor,
    CommandParser,
    ResponseProcessor
)
from src.netarchon.models.connection import (
    ConnectionInfo,
    ConnectionType,
    ConnectionStatus,
    CommandResult
)
from src.netarchon.utils.exceptions import (
    CommandExecutionError,
    TimeoutError
)


class TestCommandExecutor:
    """Test CommandExecutor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.executor = CommandExecutor(default_timeout=10)
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
    
    def test_executor_initialization(self):
        """Test command executor initialization."""
        executor = CommandExecutor(default_timeout=30)
        assert executor.default_timeout == 30
        assert executor.logger is not None
    
    def test_default_initialization(self):
        """Test command executor with default parameters."""
        executor = CommandExecutor()
        assert executor.default_timeout == 30
    
    def test_successful_command_execution(self):
        """Test successful command execution."""
        # Setup mock SSH client
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"Version 16.09.04"
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
        
        self.connection._ssh_client = mock_ssh_client
        
        # Execute command
        result = self.executor.execute_command(self.connection, "show version")
        
        # Verify result
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.output == "Version 16.09.04"
        assert result.error == ""
        assert result.command == "show version"
        assert result.device_id == "router1"
        assert result.execution_time > 0
        
        # Verify SSH client calls
        mock_ssh_client.exec_command.assert_called_once_with("show version", timeout=10)
    
    def test_command_execution_with_custom_timeout(self):
        """Test command execution with custom timeout."""
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"OK"
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
        
        self.connection._ssh_client = mock_ssh_client
        
        result = self.executor.execute_command(self.connection, "show version", timeout=60)
        
        assert result.success is True
        mock_ssh_client.exec_command.assert_called_once_with("show version", timeout=60)
    
    def test_command_execution_failure(self):
        """Test command execution with non-zero exit status."""
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"Command output"
        mock_stdout.channel.recv_exit_status.return_value = 1
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b"Command failed"
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
        
        self.connection._ssh_client = mock_ssh_client
        
        result = self.executor.execute_command(self.connection, "invalid command")
        
        assert result.success is False
        assert result.output == "Command output"
        assert result.error == "Command failed"
    
    def test_command_execution_no_ssh_client(self):
        """Test command execution without SSH client."""
        with pytest.raises(CommandExecutionError) as exc_info:
            self.executor.execute_command(self.connection, "show version")
        
        assert "No active SSH connection" in str(exc_info.value)
        assert exc_info.value.details["device_id"] == "router1"
    
    def test_command_execution_timeout(self):
        """Test command execution timeout."""
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.side_effect = Exception("timeout")
        
        self.connection._ssh_client = mock_ssh_client
        
        with pytest.raises(TimeoutError) as exc_info:
            self.executor.execute_command(self.connection, "show version", timeout=5)
        
        assert "timed out after 5 seconds" in str(exc_info.value)
        assert exc_info.value.details["timeout"] == 5
    
    def test_command_execution_exception(self):
        """Test command execution with general exception."""
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.side_effect = Exception("Connection lost")
        
        self.connection._ssh_client = mock_ssh_client
        
        result = self.executor.execute_command(self.connection, "show version")
        
        assert result.success is False
        assert result.error == "Connection lost"
        assert result.output == ""
    
    def test_execute_multiple_commands_success(self):
        """Test executing multiple commands successfully."""
        mock_stdout1 = Mock()
        mock_stdout1.read.return_value = b"Version info"
        mock_stdout1.channel.recv_exit_status.return_value = 0
        
        mock_stdout2 = Mock()
        mock_stdout2.read.return_value = b"Interface info"
        mock_stdout2.channel.recv_exit_status.return_value = 0
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.side_effect = [
            (None, mock_stdout1, mock_stderr),
            (None, mock_stdout2, mock_stderr)
        ]
        
        self.connection._ssh_client = mock_ssh_client
        
        commands = ["show version", "show interfaces"]
        results = self.executor.execute_commands(self.connection, commands)
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].output == "Version info"
        assert results[1].output == "Interface info"
        assert mock_ssh_client.exec_command.call_count == 2
    
    def test_execute_multiple_commands_stop_on_error(self):
        """Test executing multiple commands with stop on error."""
        mock_stdout1 = Mock()
        mock_stdout1.read.return_value = b"Version info"
        mock_stdout1.channel.recv_exit_status.return_value = 0
        
        mock_stdout2 = Mock()
        mock_stdout2.read.return_value = b"Error output"
        mock_stdout2.channel.recv_exit_status.return_value = 1
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b"Command error"
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.side_effect = [
            (None, mock_stdout1, mock_stderr),
            (None, mock_stdout2, mock_stderr)
        ]
        
        self.connection._ssh_client = mock_ssh_client
        
        commands = ["show version", "invalid command", "show interfaces"]
        results = self.executor.execute_commands(
            self.connection, commands, stop_on_error=True
        )
        
        assert len(results) == 2  # Should stop after second command fails
        assert results[0].success is True
        assert results[1].success is False
        assert mock_ssh_client.exec_command.call_count == 2
    
    def test_execute_multiple_commands_continue_on_error(self):
        """Test executing multiple commands continuing on error."""
        mock_stdout1 = Mock()
        mock_stdout1.read.return_value = b"Version info"
        mock_stdout1.channel.recv_exit_status.return_value = 0
        
        mock_stdout2 = Mock()
        mock_stdout2.read.return_value = b"Error output"
        mock_stdout2.channel.recv_exit_status.return_value = 1
        
        mock_stdout3 = Mock()
        mock_stdout3.read.return_value = b"Interface info"
        mock_stdout3.channel.recv_exit_status.return_value = 0
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.side_effect = [
            (None, mock_stdout1, mock_stderr),
            (None, mock_stdout2, mock_stderr),
            (None, mock_stdout3, mock_stderr)
        ]
        
        self.connection._ssh_client = mock_ssh_client
        
        commands = ["show version", "invalid command", "show interfaces"]
        results = self.executor.execute_commands(
            self.connection, commands, stop_on_error=False
        )
        
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert mock_ssh_client.exec_command.call_count == 3


class TestCommandParser:
    """Test CommandParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()
    
    def test_parser_initialization(self):
        """Test command parser initialization."""
        parser = CommandParser()
        assert parser.logger is not None
        assert len(parser.dangerous_commands) > 0
        assert 'reload' in parser.dangerous_commands
    
    def test_validate_command_valid(self):
        """Test validation of valid commands."""
        valid_commands = [
            "show version",
            "show interfaces",
            "show ip route",
            "ping 8.8.8.8",
            "traceroute 1.1.1.1"
        ]
        
        for command in valid_commands:
            assert self.parser.validate_command(command) is True
    
    def test_validate_command_empty(self):
        """Test validation of empty commands."""
        invalid_commands = ["", "   ", "\t\n", None]
        
        for command in invalid_commands:
            assert self.parser.validate_command(command) is False
    
    def test_validate_command_dangerous(self):
        """Test validation of dangerous commands."""
        dangerous_commands = [
            "reload",
            "reboot now",
            "shutdown",
            "erase startup-config",
            "format flash:",
            "write erase"
        ]
        
        for command in dangerous_commands:
            assert self.parser.validate_command(command) is False
    
    def test_validate_command_too_long(self):
        """Test validation of overly long commands."""
        long_command = "show " + "x" * 1000
        assert self.parser.validate_command(long_command) is False
    
    def test_validate_command_suspicious_patterns(self):
        """Test validation of commands with suspicious patterns."""
        suspicious_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "echo test > /dev/null",
            "mkfs.ext4 /dev/sda1"
        ]
        
        for command in suspicious_commands:
            assert self.parser.validate_command(command) is False
    
    def test_sanitize_command_basic(self):
        """Test basic command sanitization."""
        command = "  show   version  "
        sanitized = self.parser.sanitize_command(command)
        assert sanitized == "show version"
    
    def test_sanitize_command_multiple_spaces(self):
        """Test sanitization of commands with multiple spaces."""
        command = "show     interfaces     brief"
        sanitized = self.parser.sanitize_command(command)
        assert sanitized == "show interfaces brief"
    
    def test_sanitize_command_control_characters(self):
        """Test sanitization of commands with control characters."""
        command = "show\x00version\x01"
        sanitized = self.parser.sanitize_command(command)
        assert sanitized == "showversion"
    
    def test_sanitize_command_empty(self):
        """Test sanitization of empty command."""
        assert self.parser.sanitize_command("") == ""
        assert self.parser.sanitize_command(None) == ""


class TestResponseProcessor:
    """Test ResponseProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ResponseProcessor()
        self.sample_result = CommandResult(
            success=True,
            output="Sample output\nLine 2\nLine 3",
            error="",
            execution_time=1.5,
            timestamp=datetime.utcnow(),
            command="show version",
            device_id="router1"
        )
    
    def test_processor_initialization(self):
        """Test response processor initialization."""
        processor = ResponseProcessor()
        assert processor.logger is not None
    
    def test_process_response_success(self):
        """Test processing successful response."""
        result = self.processor.process_response(self.sample_result)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.command == "show version"
        assert result.device_id == "router1"
        assert hasattr(result, 'additional_data')
        assert 'output_lines' in result.additional_data
        assert 'command_type' in result.additional_data
    
    def test_process_response_failed(self):
        """Test processing failed response."""
        failed_result = CommandResult(
            success=False,
            output="",
            error="Command failed",
            execution_time=0.5,
            timestamp=datetime.utcnow(),
            command="invalid command",
            device_id="router1"
        )
        
        result = self.processor.process_response(failed_result)
        assert result.success is False
        assert result.error == "Command failed"
    
    def test_clean_output_ansi_sequences(self):
        """Test cleaning output with ANSI escape sequences."""
        output_with_ansi = "\x1b[32mGreen text\x1b[0m Normal text"
        cleaned = self.processor._clean_output(output_with_ansi)
        assert cleaned == "Green text Normal text"
    
    def test_clean_output_carriage_returns(self):
        """Test cleaning output with carriage returns."""
        output_with_cr = "Line 1\r\nLine 2\r\nLine 3"
        cleaned = self.processor._clean_output(output_with_cr)
        assert "\r" not in cleaned
        assert "Line 1\nLine 2\nLine 3" == cleaned
    
    def test_clean_output_excessive_blank_lines(self):
        """Test cleaning output with excessive blank lines."""
        output_with_blanks = "Line 1\n\n\n\nLine 2\n\n\nLine 3"
        cleaned = self.processor._clean_output(output_with_blanks)
        # Should reduce multiple blank lines to double newlines
        assert "\n\n\n" not in cleaned
    
    def test_clean_output_empty(self):
        """Test cleaning empty output."""
        assert self.processor._clean_output("") == ""
        assert self.processor._clean_output(None) == ""
    
    def test_extract_metadata_version_command(self):
        """Test metadata extraction for version command."""
        metadata = self.processor._extract_metadata("show version", "Version info")
        assert metadata['command_type'] == 'version_info'
        assert metadata['output_lines'] == 1
    
    def test_extract_metadata_interface_command(self):
        """Test metadata extraction for interface command."""
        metadata = self.processor._extract_metadata("show interfaces", "Interface info")
        assert metadata['command_type'] == 'interface_info'
    
    def test_extract_metadata_routing_command(self):
        """Test metadata extraction for routing command."""
        metadata = self.processor._extract_metadata("show ip route", "Route info")
        assert metadata['command_type'] == 'routing_info'
        
        metadata = self.processor._extract_metadata("show route", "Route info")
        assert metadata['command_type'] == 'routing_info'
    
    def test_extract_metadata_config_command(self):
        """Test metadata extraction for configuration command."""
        metadata = self.processor._extract_metadata("show running-config", "Config")
        assert metadata['command_type'] == 'configuration'
        
        metadata = self.processor._extract_metadata("show configuration", "Config")
        assert metadata['command_type'] == 'configuration'
    
    def test_extract_metadata_general_command(self):
        """Test metadata extraction for general command."""
        metadata = self.processor._extract_metadata("ping 8.8.8.8", "Ping results")
        assert metadata['command_type'] == 'general'
    
    def test_extract_metadata_multiline_output(self):
        """Test metadata extraction with multiline output."""
        output = "Line 1\nLine 2\nLine 3\nLine 4"
        metadata = self.processor._extract_metadata("show version", output)
        assert metadata['output_lines'] == 4