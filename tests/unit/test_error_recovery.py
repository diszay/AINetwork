"""
Tests for NetArchon Error Handling and Recovery Integration
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.netarchon.core.ssh_connector import SSHConnector, ConnectionPool
from src.netarchon.core.command_executor import CommandExecutor
from src.netarchon.models.connection import ConnectionInfo, ConnectionType, ConnectionStatus, AuthenticationCredentials
from src.netarchon.utils.circuit_breaker import CircuitBreakerError, CircuitState
from src.netarchon.utils.retry_manager import RetryExhaustedError
from src.netarchon.utils.exceptions import ConnectionError, AuthenticationError, TimeoutError


class TestSSHConnectorErrorRecovery:
    """Test SSH connector with circuit breaker integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ssh_connector = SSHConnector(timeout=5, retry_attempts=2)
        self.credentials = AuthenticationCredentials(
            username="test_user",
            password="test_password"
        )
    
    @patch('paramiko.SSHClient')
    def test_successful_connection_with_circuit_breaker(self, mock_ssh_client_class):
        """Test successful connection through circuit breaker."""
        # Mock successful SSH connection
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.return_value = None
        
        # Test connection
        connection = self.ssh_connector.connect("192.168.1.1", self.credentials, device_id="test_device")
        
        assert connection.device_id == "test_device"
        assert connection.status == ConnectionStatus.CONNECTED
        assert self.ssh_connector.circuit_breaker.state == CircuitState.CLOSED
        assert self.ssh_connector.circuit_breaker.total_successes == 1
    
    @patch('paramiko.SSHClient')
    def test_circuit_breaker_opens_after_failures(self, mock_ssh_client_class):
        """Test circuit breaker opens after repeated failures."""
        # Mock SSH client that always fails
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.side_effect = ConnectionError("Connection failed")
        
        # Fail enough times to open circuit breaker (5 failures)
        for i in range(5):
            with pytest.raises(ConnectionError):
                self.ssh_connector.connect("192.168.1.1", self.credentials, device_id=f"test_device_{i}")
        
        # Circuit should now be open
        assert self.ssh_connector.circuit_breaker.state == CircuitState.OPEN
        
        # Next connection should fail fast with CircuitBreakerError
        with pytest.raises(CircuitBreakerError, match="Circuit breaker 'ssh_connections' is open"):
            self.ssh_connector.connect("192.168.1.1", self.credentials, device_id="test_device_fail_fast")
    
    @patch('paramiko.SSHClient')
    def test_circuit_breaker_recovery(self, mock_ssh_client_class):
        """Test circuit breaker recovery after timeout."""
        # Force circuit breaker to open
        self.ssh_connector.circuit_breaker.force_open()
        
        # Set last failure time to past recovery timeout
        self.ssh_connector.circuit_breaker.last_failure_time = datetime.utcnow() - \
            self.ssh_connector.circuit_breaker.config.recovery_timeout * 2
        
        # Mock successful connection
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.return_value = None
        
        # Connection should succeed and transition to half-open
        connection = self.ssh_connector.connect("192.168.1.1", self.credentials, device_id="recovery_test")
        
        assert connection.status == ConnectionStatus.CONNECTED
        assert self.ssh_connector.circuit_breaker.state == CircuitState.HALF_OPEN
    
    @patch('paramiko.SSHClient')
    def test_authentication_error_bypasses_circuit_breaker(self, mock_ssh_client_class):
        """Test that authentication errors don't trigger circuit breaker."""
        # Mock authentication failure
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.side_effect = AuthenticationError("Auth failed")
        
        # Authentication error should be raised immediately
        with pytest.raises(AuthenticationError, match="Auth failed"):
            self.ssh_connector.connect("192.168.1.1", self.credentials, device_id="auth_test")
        
        # Circuit breaker should record this as a failure
        assert self.ssh_connector.circuit_breaker.total_failures == 1


class TestConnectionPoolErrorRecovery:
    """Test connection pool with error recovery."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pool = ConnectionPool(max_connections=2, idle_timeout=1)
        self.credentials = AuthenticationCredentials(
            username="test_user",
            password="test_password"
        )
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_pool_handles_connection_failures_gracefully(self, mock_ssh_connector_class):
        """Test connection pool handles failures gracefully."""
        # Mock SSH connector that fails
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        mock_connector.connect.side_effect = ConnectionError("Connection failed")
        
        # Connection attempt should propagate the error
        with pytest.raises(ConnectionError, match="Connection failed"):
            self.pool.get_connection("device1", "192.168.1.1", self.credentials)
        
        # Pool should remain empty
        assert len(self.pool.connections) == 0
    
    @patch('src.netarchon.core.ssh_connector.SSHConnector')
    def test_pool_removes_stale_connections(self, mock_ssh_connector_class):
        """Test connection pool removes stale connections."""
        # Mock SSH connector
        mock_connector = Mock()
        mock_ssh_connector_class.return_value = mock_connector
        
        # Mock successful connection first time
        mock_connection = Mock(spec=ConnectionInfo)
        mock_connection.device_id = "device1"
        mock_connector.connect.return_value = mock_connection
        mock_connector.is_connected.return_value = True
        
        # Get connection
        connection1 = self.pool.get_connection("device1", "192.168.1.1", self.credentials)
        assert len(self.pool.connections) == 1
        
        # Mock connection becomes stale
        mock_connector.is_connected.return_value = False
        
        # Mock new connection for retry
        mock_new_connection = Mock(spec=ConnectionInfo)
        mock_new_connection.device_id = "device1"
        mock_connector.connect.return_value = mock_new_connection
        
        # Get connection again - should create new one
        connection2 = self.pool.get_connection("device1", "192.168.1.1", self.credentials)
        
        # Should have removed stale connection and created new one
        assert len(self.pool.connections) == 1
        assert connection2 is mock_new_connection


class TestCommandExecutorErrorRecovery:
    """Test command executor error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.executor = CommandExecutor(default_timeout=5)
        self.connection = Mock(spec=ConnectionInfo)
        self.connection.device_id = "test_device"
        self.connection._ssh_client = Mock()
    
    def test_command_timeout_handling(self):
        """Test command timeout handling."""
        # Mock SSH client that times out
        mock_ssh_client = self.connection._ssh_client
        mock_ssh_client.exec_command.side_effect = TimeoutError("Command timed out")
        
        result = self.executor.execute_command(self.connection, "show version")
        
        # Should return failed result instead of raising exception
        assert result.success is False
        assert "Command timed out" in result.error
        assert result.device_id == "test_device"
    
    def test_command_execution_with_ssh_errors(self):
        """Test command execution with SSH errors."""
        # Mock SSH client that raises exception
        mock_ssh_client = self.connection._ssh_client
        mock_ssh_client.exec_command.side_effect = Exception("SSH connection lost")
        
        result = self.executor.execute_command(self.connection, "show interfaces")
        
        # Should return failed result
        assert result.success is False
        assert "SSH connection lost" in result.error
        assert result.command == "show interfaces"
    
    def test_batch_command_execution_with_stop_on_error(self):
        """Test batch command execution stops on error when configured."""
        # Mock SSH client responses
        mock_ssh_client = self.connection._ssh_client
        
        def mock_exec_command(command, timeout=30):
            if "fail" in command:
                raise Exception("Command failed")
            
            # Mock successful response
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.read.return_value = b"Success output"
            mock_stderr.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 0
            return mock_stdin, mock_stdout, mock_stderr
        
        mock_ssh_client.exec_command = mock_exec_command
        
        commands = ["show version", "show fail", "show interfaces"]
        results = self.executor.execute_commands(self.connection, commands, stop_on_error=True)
        
        # Should stop after second command fails
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "Command failed" in results[1].error


class TestIntegratedErrorRecovery:
    """Integration tests for error recovery across components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ssh_connector = SSHConnector(timeout=1, retry_attempts=2)
        self.pool = ConnectionPool(max_connections=2)
        self.executor = CommandExecutor(default_timeout=1)
        self.credentials = AuthenticationCredentials(
            username="test_user",
            password="test_password"
        )
    
    @patch('paramiko.SSHClient')
    def test_end_to_end_error_recovery_scenario(self, mock_ssh_client_class):
        """Test realistic end-to-end error recovery scenario."""
        # Scenario: Network device becomes temporarily unreachable, then recovers
        
        call_count = 0
        
        def mock_connect_behavior(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # First 3 attempts fail (network unreachable)
            if call_count <= 3:
                raise ConnectionError("Network unreachable")
            
            # 4th attempt succeeds (network recovered)
            return None
        
        # Mock SSH client
        mock_ssh_client = Mock()
        mock_ssh_client_class.return_value = mock_ssh_client
        mock_ssh_client.connect.side_effect = mock_connect_behavior
        
        # First connection attempt should fail after retries
        with pytest.raises(ConnectionError):
            self.pool.get_connection("device1", "192.168.1.1", self.credentials)
        
        # Circuit breaker should have recorded failures but not be open yet
        cb = self.ssh_connector.circuit_breaker
        assert cb.failure_count > 0
        assert cb.state == CircuitState.CLOSED  # Not enough failures to open
        
        # Second connection attempt should succeed (simulating network recovery)
        connection = self.pool.get_connection("device1", "192.168.1.1", self.credentials)
        
        assert connection.status == ConnectionStatus.CONNECTED
        assert len(self.pool.connections) == 1
    
    def test_graceful_degradation_with_partial_failures(self):
        """Test graceful degradation when some operations fail."""
        # Mock connection that works for connection but fails for some commands
        mock_connection = Mock(spec=ConnectionInfo)
        mock_connection.device_id = "test_device"
        mock_connection._ssh_client = Mock()
        
        # Mock SSH client that fails for specific commands
        def mock_exec_command(command, timeout=30):
            if "privileged" in command:
                raise Exception("Privilege escalation failed")
            
            # Mock successful response for other commands
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.read.return_value = b"Command output"
            mock_stderr.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 0
            return mock_stdin, mock_stdout, mock_stderr
        
        mock_connection._ssh_client.exec_command = mock_exec_command
        
        # Execute mixed commands
        commands = ["show version", "show privileged info", "show interfaces"]
        results = self.executor.execute_commands(mock_connection, commands, stop_on_error=False)
        
        # Should execute all commands, with middle one failing
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False  # Privileged command failed
        assert results[2].success is True
        
        # System should continue operating despite partial failure
        assert "Privilege escalation failed" in results[1].error


class TestErrorRecoveryStatistics:
    """Test error recovery statistics and monitoring."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ssh_connector = SSHConnector()
    
    def test_circuit_breaker_statistics_tracking(self):
        """Test circuit breaker statistics are properly tracked."""
        cb = self.ssh_connector.circuit_breaker
        
        # Get initial status
        initial_status = cb.get_status()
        assert initial_status["total_calls"] == 0
        assert initial_status["total_failures"] == 0
        assert initial_status["total_successes"] == 0
        
        # Simulate some operations
        try:
            cb.call(lambda: "success")
        except:
            pass
        
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("test error")))
        except:
            pass
        
        # Check updated status
        updated_status = cb.get_status()
        assert updated_status["total_calls"] == 2
        assert updated_status["total_successes"] == 1
        assert updated_status["total_failures"] == 1
        assert updated_status["failure_rate"] == 0.5
    
    def test_circuit_breaker_reset_functionality(self):
        """Test circuit breaker can be reset for recovery."""
        cb = self.ssh_connector.circuit_breaker
        
        # Force circuit to open
        cb.force_open()
        assert cb.state == CircuitState.OPEN
        
        # Reset circuit
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0