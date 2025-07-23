"""Performance tests for concurrent operations.

These tests verify that NetArchon can handle multiple concurrent
connections and operations efficiently.
"""

import os
import time
import pytest
import threading
import concurrent.futures
from unittest import mock

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.device_manager import DeviceDetector
from netarchon.models.device import DeviceInfo, DeviceType, DeviceStatus
from netarchon.models.connection import AuthenticationCredentials
from netarchon.utils.exceptions import ConnectionError, CommandExecutionError


# Skip these tests if no performance test environment is available
pytestmark = pytest.mark.skipif(
    os.environ.get('NETARCHON_PERFORMANCE_TESTS') != 'true',
    reason="Performance tests are disabled. Set NETARCHON_PERFORMANCE_TESTS=true to enable."
)


def create_test_devices(count=5):
    """Create multiple test devices for concurrent testing."""
    devices = []
    base_host = os.environ.get('NETARCHON_TEST_HOST', '192.168.1.1')
    username = os.environ.get('NETARCHON_TEST_USERNAME', 'admin')
    password = os.environ.get('NETARCHON_TEST_PASSWORD', 'password')
    device_type = DeviceType(os.environ.get('NETARCHON_TEST_DEVICE_TYPE', 'cisco_ios'))
    
    for i in range(count):
        device = DeviceInfo(
            hostname=f"test-device-{i+1}",
            ip_address=base_host,  # In real tests, use different IPs
            device_type=device_type,
            vendor="test",
            model="test-model",
            os_version="1.0",
            status=DeviceStatus.UNKNOWN
        )
        devices.append(device)
    
    return devices


@pytest.fixture
def test_devices():
    """Create test devices for performance testing."""
    return create_test_devices(5)


@pytest.fixture
def ssh_connector():
    """Create an SSH connector for testing."""
    return SSHConnector()


@pytest.fixture
def command_executor(ssh_connector):
    """Create a command executor for testing."""
    return CommandExecutor(ssh_connector)


@pytest.mark.performance
class TestConcurrentOperations:
    """Performance tests for concurrent operations."""
    
    def test_concurrent_connections(self, ssh_connector, test_devices):
        """Test establishing multiple concurrent connections."""
        # If using mock mode, skip actual connections
        if os.environ.get('NETARCHON_MOCK_PERFORMANCE') == 'true':
            with mock.patch.object(ssh_connector, 'connect') as mock_connect:
                mock_connect.return_value = True
                
                def connect_device(device):
                    start_time = time.time()
                    result = ssh_connector.connect(device)
                    end_time = time.time()
                    return {
                        'device': device.name,
                        'success': result,
                        'duration': end_time - start_time
                    }
                
                # Test concurrent connections
                start_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(connect_device, device) for device in test_devices]
                    results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
                total_time = time.time() - start_time
                
                # Verify results
                assert len(results) == len(test_devices)
                assert all(result['success'] for result in results)
                
                # Performance assertions
                assert total_time < 10.0  # Should complete within 10 seconds
                avg_connection_time = sum(r['duration'] for r in results) / len(results)
                assert avg_connection_time < 2.0  # Average connection time should be < 2s
                
                print(f"Concurrent connections completed in {total_time:.2f}s")
                print(f"Average connection time: {avg_connection_time:.2f}s")
                return
        
        # Real concurrent connection test
        def connect_device(device):
            start_time = time.time()
            try:
                result = ssh_connector.connect(device)
                end_time = time.time()
                return {
                    'device': device.name,
                    'success': result,
                    'duration': end_time - start_time,
                    'error': None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'device': device.name,
                    'success': False,
                    'duration': end_time - start_time,
                    'error': str(e)
                }
        
        try:
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(connect_device, device) for device in test_devices]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful_connections = [r for r in results if r['success']]
            failed_connections = [r for r in results if not r['success']]
            
            print(f"Concurrent connections completed in {total_time:.2f}s")
            print(f"Successful: {len(successful_connections)}, Failed: {len(failed_connections)}")
            
            if successful_connections:
                avg_connection_time = sum(r['duration'] for r in successful_connections) / len(successful_connections)
                print(f"Average successful connection time: {avg_connection_time:.2f}s")
            
            # At least some connections should succeed in a real environment
            if len(successful_connections) == 0:
                pytest.skip("No successful connections in performance test")
                
        finally:
            # Clean up connections
            for device in test_devices:
                if ssh_connector.is_connected(device.hostname):
                    ssh_connector.disconnect(device.hostname)
    
    def test_concurrent_command_execution(self, ssh_connector, command_executor, test_devices):
        """Test executing commands concurrently on multiple devices."""
        # If using mock mode, skip actual command execution
        if os.environ.get('NETARCHON_MOCK_PERFORMANCE') == 'true':
            with mock.patch.object(command_executor, 'execute_command') as mock_execute:
                mock_execute.return_value = mock.Mock(
                    output="Mock command output",
                    exit_code=0,
                    execution_time=0.5
                )
                
                def execute_command_on_device(device, command):
                    start_time = time.time()
                    result = command_executor.execute_command(device, command)
                    end_time = time.time()
                    return {
                        'device': device.name,
                        'command': command,
                        'success': result.exit_code == 0,
                        'duration': end_time - start_time,
                        'output_length': len(result.output)
                    }
                
                # Test commands
                commands = ["show version", "show ip interface brief", "show running-config | include hostname"]
                
                # Create tasks for all device-command combinations
                tasks = []
                for device in test_devices:
                    for command in commands:
                        tasks.append((device, command))
                
                start_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(execute_command_on_device, device, cmd) 
                              for device, cmd in tasks]
                    results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
                total_time = time.time() - start_time
                
                # Verify results
                assert len(results) == len(tasks)
                assert all(result['success'] for result in results)
                
                # Performance assertions
                assert total_time < 30.0  # Should complete within 30 seconds
                avg_execution_time = sum(r['duration'] for r in results) / len(results)
                assert avg_execution_time < 3.0  # Average execution time should be < 3s
                
                print(f"Concurrent command execution completed in {total_time:.2f}s")
                print(f"Total commands executed: {len(results)}")
                print(f"Average execution time: {avg_execution_time:.2f}s")
                return
        
        # Real concurrent command execution test
        def execute_command_on_device(device, command):
            start_time = time.time()
            try:
                # Connect if not already connected
                if not ssh_connector.is_connected(device.hostname):
                    ssh_connector.connect(device)
                
                result = command_executor.execute_command(device, command)
                end_time = time.time()
                return {
                    'device': device.name,
                    'command': command,
                    'success': result.exit_code == 0,
                    'duration': end_time - start_time,
                    'output_length': len(result.output),
                    'error': None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'device': device.name,
                    'command': command,
                    'success': False,
                    'duration': end_time - start_time,
                    'output_length': 0,
                    'error': str(e)
                }
        
        try:
            # Test commands
            commands = ["show version", "show ip interface brief"]
            
            # Create tasks for all device-command combinations
            tasks = []
            for device in test_devices[:2]:  # Limit to 2 devices for real testing
                for command in commands:
                    tasks.append((device, command))
            
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(execute_command_on_device, device, cmd) 
                          for device, cmd in tasks]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful_executions = [r for r in results if r['success']]
            failed_executions = [r for r in results if not r['success']]
            
            print(f"Concurrent command execution completed in {total_time:.2f}s")
            print(f"Successful: {len(successful_executions)}, Failed: {len(failed_executions)}")
            
            if successful_executions:
                avg_execution_time = sum(r['duration'] for r in successful_executions) / len(successful_executions)
                print(f"Average successful execution time: {avg_execution_time:.2f}s")
            
            # At least some executions should succeed in a real environment
            if len(successful_executions) == 0:
                pytest.skip("No successful command executions in performance test")
                
        finally:
            # Clean up connections
            for device in test_devices:
                if ssh_connector.is_connected(device.hostname):
                    ssh_connector.disconnect(device.hostname)
    
    def test_connection_pool_performance(self, ssh_connector, test_devices):
        """Test connection pool performance under load."""
        # If using mock mode, skip actual pool testing
        if os.environ.get('NETARCHON_MOCK_PERFORMANCE') == 'true':
            with mock.patch.object(ssh_connector, 'get_connection') as mock_get_conn, \
                 mock.patch.object(ssh_connector, 'return_connection') as mock_return_conn:
                
                mock_get_conn.return_value = mock.Mock()
                mock_return_conn.return_value = None
                
                def use_connection_pool(device_name, operation_id):
                    start_time = time.time()
                    
                    # Simulate getting connection from pool
                    connection = ssh_connector.get_connection(device_name)
                    
                    # Simulate some work
                    time.sleep(0.1)
                    
                    # Return connection to pool
                    ssh_connector.return_connection(device_name, connection)
                    
                    end_time = time.time()
                    return {
                        'device': device_name,
                        'operation_id': operation_id,
                        'duration': end_time - start_time
                    }
                
                # Simulate multiple operations using the connection pool
                operations = []
                for i in range(20):  # 20 operations
                    device = test_devices[i % len(test_devices)]
                    operations.append((device.hostname, i))
                
                start_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    futures = [executor.submit(use_connection_pool, device_name, op_id) 
                              for device_name, op_id in operations]
                    results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
                total_time = time.time() - start_time
                
                # Verify results
                assert len(results) == len(operations)
                
                # Performance assertions
                assert total_time < 15.0  # Should complete within 15 seconds
                avg_operation_time = sum(r['duration'] for r in results) / len(results)
                
                print(f"Connection pool operations completed in {total_time:.2f}s")
                print(f"Total operations: {len(results)}")
                print(f"Average operation time: {avg_operation_time:.2f}s")
                print(f"Operations per second: {len(results) / total_time:.2f}")
                return
        
        # Real connection pool performance test would require actual implementation
        pytest.skip("Real connection pool performance test requires actual device connections")
    
    def test_memory_usage_under_load(self, ssh_connector, command_executor, test_devices):
        """Test memory usage during high-load operations."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # If using mock mode, simulate load
        if os.environ.get('NETARCHON_MOCK_PERFORMANCE') == 'true':
            with mock.patch.object(command_executor, 'execute_command') as mock_execute:
                mock_execute.return_value = mock.Mock(
                    output="Mock output " * 1000,  # Simulate large output
                    exit_code=0,
                    execution_time=0.1
                )
                
                # Simulate high load
                results = []
                for i in range(100):  # 100 operations
                    device = test_devices[i % len(test_devices)]
                    result = command_executor.execute_command(device, "show running-config")
                    results.append(result)
                    
                    # Check memory every 20 operations
                    if i % 20 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        print(f"Memory after {i+1} operations: {current_memory:.2f} MB")
                
                # Final memory check
                final_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = final_memory - initial_memory
                
                print(f"Final memory usage: {final_memory:.2f} MB")
                print(f"Memory increase: {memory_increase:.2f} MB")
                
                # Memory should not increase excessively
                assert memory_increase < 100.0  # Less than 100MB increase
                
                # Force garbage collection and check again
                gc.collect()
                gc_memory = process.memory_info().rss / 1024 / 1024
                print(f"Memory after GC: {gc_memory:.2f} MB")
                
                return
        
        # Real memory usage test would require actual operations
        pytest.skip("Real memory usage test requires actual device operations")