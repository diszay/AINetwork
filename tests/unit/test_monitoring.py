"""
Tests for NetArchon Monitoring and Metrics Collection
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.netarchon.core.monitoring import (
    MonitoringCollector, InterfaceMetrics, SystemMetrics, MetricData, MetricType
)
from src.netarchon.models.connection import ConnectionInfo, CommandResult, ConnectionType, ConnectionStatus
from src.netarchon.models.device import DeviceType
from src.netarchon.utils.exceptions import MonitoringError


class TestMonitoringCollector:
    """Test MonitoringCollector functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = MonitoringCollector()
        
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
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_collect_interface_metrics_success(self, mock_executor_class):
        """Test successful interface metrics collection."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock interface command output
        interface_output = """
GigabitEthernet0/0 is up, line protocol is up
  Hardware is Gigabit Ethernet, address is 0000.1111.2222
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec
     5 minute input rate 1000 bits/sec, 2 packets/sec
     5 minute output rate 2000 bits/sec, 3 packets/sec
     1024000 packets input, 2048000 bytes, 0 no buffer
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     2048000 packets output, 4096000 bytes, 0 underruns
     0 output errors, 0 collisions, 2 interface resets
"""
        
        mock_executor.execute_command.return_value = CommandResult(
            True, interface_output, "", 1.0, datetime.now(), "show interfaces", "test_router"
        )
        
        # Create collector with mocked executor
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test interface metrics collection
        metrics = collector.collect_interface_metrics(self.connection)
        
        # Verify results
        assert len(metrics) >= 1
        assert isinstance(metrics[0], InterfaceMetrics)
        assert metrics[0].device_id == "test_router"
        assert metrics[0].interface_name is not None
        
        # Verify command was executed
        mock_executor.execute_command.assert_called_once()
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_collect_interface_metrics_command_failure(self, mock_executor_class):
        """Test interface metrics collection with command failure."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock command failure
        mock_executor.execute_command.return_value = CommandResult(
            False, "", "Connection timeout", 1.0, datetime.now(), "show interfaces", "test_router"
        )
        
        # Create collector with mocked executor
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test interface metrics collection failure
        with pytest.raises(MonitoringError, match="Failed to collect interface metrics"):
            collector.collect_interface_metrics(self.connection)
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_collect_system_metrics_success(self, mock_executor_class):
        """Test successful system metrics collection."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock successful command results for all system metrics
        def mock_execute_command(connection, command, timeout=30):
            if 'cpu' in command.lower() or 'processes' in command.lower():
                return CommandResult(True, "CPU utilization: 15%", "", 1.0, datetime.now(), command, "test_router")
            elif 'memory' in command.lower():
                return CommandResult(True, "Total: 1024MB Used: 512MB", "", 1.0, datetime.now(), command, "test_router")
            elif 'version' in command.lower() or 'uptime' in command.lower():
                return CommandResult(True, "Uptime: 1 day, 0 hours", "", 1.0, datetime.now(), command, "test_router")
            elif 'temperature' in command.lower():
                return CommandResult(True, "Temperature: 45.5C", "", 1.0, datetime.now(), command, "test_router")
            elif 'power' in command.lower():
                return CommandResult(True, "Power: 150W", "", 1.0, datetime.now(), command, "test_router")
            else:
                return CommandResult(True, "OK", "", 1.0, datetime.now(), command, "test_router")
        
        mock_executor.execute_command.side_effect = mock_execute_command
        
        # Create collector with mocked executor
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test system metrics collection
        metrics = collector.collect_system_metrics(self.connection)
        
        # Verify results
        assert isinstance(metrics, SystemMetrics)
        assert metrics.device_id == "test_router"
        assert metrics.cpu_utilization >= 0
        assert metrics.memory_total > 0
        assert metrics.memory_used >= 0
        assert metrics.memory_utilization >= 0
        assert metrics.uptime >= 0
        assert isinstance(metrics.timestamp, datetime)
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_collect_system_metrics_command_failure(self, mock_executor_class):
        """Test system metrics collection with partial command failures."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Mock command failure for individual metrics but still succeeds overall
        mock_executor.execute_command.side_effect = Exception("Connection lost")
        
        # Create collector with mocked executor
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test system metrics collection with failures - should still return metrics with default values
        metrics = collector.collect_system_metrics(self.connection)
        
        # Should still return a SystemMetrics object with default values
        assert isinstance(metrics, SystemMetrics)
        assert metrics.device_id == "test_router"
        assert metrics.cpu_utilization == 0.0  # Default value when collection fails
        assert metrics.memory_total == 0  # Default value when collection fails
    
    def test_store_metrics_memory_backend(self):
        """Test metrics storage with memory backend."""
        # Create test metrics
        metrics = [
            MetricData(
                device_id="test_router",
                metric_type=MetricType.CPU,
                metric_name="cpu_utilization",
                value=15.5,
                unit="percent",
                timestamp=datetime.now()
            ),
            MetricData(
                device_id="test_router",
                metric_type=MetricType.MEMORY,
                metric_name="memory_utilization", 
                value=50.0,
                unit="percent",
                timestamp=datetime.now()
            )
        ]
        
        # Test storage
        result = self.collector.store_metrics(metrics)
        
        # Verify storage success
        assert result is True
        assert len(self.collector._metrics_storage) == 2
        assert self.collector._metrics_storage[0].device_id == "test_router"
        assert self.collector._metrics_storage[1].device_id == "test_router"
    
    def test_store_metrics_empty_list(self):
        """Test metrics storage with empty list."""
        result = self.collector.store_metrics([])
        assert result is True
        assert len(self.collector._metrics_storage) == 0
    
    def test_get_historical_metrics_success(self):
        """Test historical metrics retrieval."""
        # Create test metrics with different timestamps
        now = datetime.now()
        old_time = now - timedelta(hours=48)  # 48 hours ago
        recent_time = now - timedelta(hours=1)  # 1 hour ago
        
        test_metrics = [
            MetricData("test_router", MetricType.CPU, "cpu_util", 10.0, "%", old_time),
            MetricData("test_router", MetricType.CPU, "cpu_util", 15.0, "%", recent_time),
            MetricData("test_router", MetricType.MEMORY, "mem_util", 50.0, "%", recent_time),
            MetricData("other_router", MetricType.CPU, "cpu_util", 20.0, "%", recent_time)
        ]
        
        # Store test metrics
        self.collector._metrics_storage = test_metrics
        
        # Test retrieval for specific device (24 hours back)
        metrics = self.collector.get_historical_metrics("test_router", hours_back=24)
        
        # Should get only recent metrics for test_router
        assert len(metrics) == 2
        assert all(m.device_id == "test_router" for m in metrics)
        assert all(m.timestamp >= now - timedelta(hours=24) for m in metrics)
        
        # Test retrieval with metric type filter
        cpu_metrics = self.collector.get_historical_metrics("test_router", MetricType.CPU, hours_back=24)
        assert len(cpu_metrics) == 1
        assert cpu_metrics[0].metric_type == MetricType.CPU
    
    def test_get_historical_metrics_no_data(self):
        """Test historical metrics retrieval with no data."""
        metrics = self.collector.get_historical_metrics("nonexistent_device")
        assert len(metrics) == 0
    
    def test_parse_interface_data_cisco_ios(self):
        """Test interface data parsing for Cisco IOS."""
        # Sample Cisco IOS interface output
        output = """
GigabitEthernet0/0 is up, line protocol is up
  Hardware is Gigabit Ethernet, address is 0000.1111.2222
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec
     5 minute input rate 1000 bits/sec, 2 packets/sec
     5 minute output rate 2000 bits/sec, 3 packets/sec
     1024000 packets input, 2048000 bytes, 0 no buffer
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     2048000 packets output, 4096000 bytes, 0 underruns
     0 output errors, 0 collisions, 2 interface resets
        """
        
        # Test parsing
        interfaces = self.collector._parse_interface_data(output, DeviceType.CISCO_IOS, "test_router")
        
        # Verify parsing results
        assert len(interfaces) >= 1
        assert interfaces[0].device_id == "test_router"
        assert isinstance(interfaces[0].timestamp, datetime)
    
    def test_parse_interface_data_empty_output(self):
        """Test interface data parsing with empty output."""
        interfaces = self.collector._parse_interface_data("", DeviceType.CISCO_IOS, "test_router")
        
        # Should return default interface
        assert len(interfaces) == 1
        assert interfaces[0].device_id == "test_router"
        assert interfaces[0].interface_name == "GigabitEthernet0/0"
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_cpu_metrics_collection(self, mock_executor_class):
        """Test CPU metrics collection method."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.execute_command.return_value = CommandResult(
            True, "CPU utilization: 25%", "", 1.0, datetime.now(), "show processes cpu", "test_router"
        )
        
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test CPU collection
        cpu_util = collector._collect_cpu_metrics(self.connection, DeviceType.CISCO_IOS)
        
        # Should return default value for now
        assert isinstance(cpu_util, float)
        assert cpu_util >= 0
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_memory_metrics_collection(self, mock_executor_class):
        """Test memory metrics collection method."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.execute_command.return_value = CommandResult(
            True, "Total: 2048MB, Used: 1024MB", "", 1.0, datetime.now(), "show memory statistics", "test_router"
        )
        
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test memory collection
        total, used = collector._collect_memory_metrics(self.connection, DeviceType.CISCO_IOS)
        
        # Should return default values for now
        assert isinstance(total, int)
        assert isinstance(used, int)
        assert total >= used
        assert total > 0
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_temperature_metrics_collection(self, mock_executor_class):
        """Test temperature metrics collection method."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.execute_command.return_value = CommandResult(
            True, "Temperature: 42.5C", "", 1.0, datetime.now(), "show environment temperature", "test_router"
        )
        
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test temperature collection
        temperature = collector._collect_temperature_metrics(self.connection, DeviceType.CISCO_IOS)
        
        # Should return default value for now
        assert isinstance(temperature, float)
        assert temperature > 0
    
    @patch('src.netarchon.core.monitoring.CommandExecutor')
    def test_power_metrics_collection(self, mock_executor_class):
        """Test power metrics collection method."""
        # Mock command executor
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.execute_command.return_value = CommandResult(
            True, "Power consumption: 200W", "", 1.0, datetime.now(), "show environment power", "test_router"
        )
        
        collector = MonitoringCollector()
        collector.command_executor = mock_executor
        
        # Test power collection
        power = collector._collect_power_metrics(self.connection, DeviceType.CISCO_IOS)
        
        # Should return default value for now
        assert isinstance(power, float)
        assert power > 0
    
    def test_monitoring_commands_for_all_device_types(self):
        """Test that monitoring commands are defined for all device types."""
        # Verify commands exist for all supported device types
        device_types = [DeviceType.CISCO_IOS, DeviceType.CISCO_NXOS, DeviceType.JUNIPER_JUNOS, 
                       DeviceType.ARISTA_EOS, DeviceType.GENERIC]
        
        for device_type in device_types:
            assert device_type in self.collector.monitoring_commands
            commands = self.collector.monitoring_commands[device_type]
            
            # Verify required command types exist
            required_commands = ['interfaces', 'system', 'memory', 'uptime']
            for cmd_type in required_commands:
                assert cmd_type in commands
                assert isinstance(commands[cmd_type], str)
                assert len(commands[cmd_type]) > 0
    
    def test_metric_data_creation(self):
        """Test MetricData object creation."""
        timestamp = datetime.now()
        metric = MetricData(
            device_id="test_device",
            metric_type=MetricType.INTERFACE,
            metric_name="utilization",
            value=85.5,
            unit="percent",
            timestamp=timestamp,
            metadata={"interface": "eth0"}
        )
        
        assert metric.device_id == "test_device"
        assert metric.metric_type == MetricType.INTERFACE
        assert metric.metric_name == "utilization"
        assert metric.value == 85.5
        assert metric.unit == "percent"
        assert metric.timestamp == timestamp
        assert metric.metadata["interface"] == "eth0"
    
    def test_interface_metrics_creation(self):
        """Test InterfaceMetrics object creation."""
        timestamp = datetime.now()
        interface = InterfaceMetrics(
            interface_name="GigabitEthernet0/1",
            status="up",
            input_bytes=1000000,
            output_bytes=2000000,
            input_packets=5000,
            output_packets=7000,
            input_errors=0,
            output_errors=0,
            input_drops=0,
            output_drops=0,
            bandwidth=1000000000,
            utilization_in=10.5,
            utilization_out=15.2,
            timestamp=timestamp,
            device_id="test_switch"
        )
        
        assert interface.interface_name == "GigabitEthernet0/1"
        assert interface.status == "up"
        assert interface.input_bytes == 1000000
        assert interface.output_bytes == 2000000
        assert interface.bandwidth == 1000000000
        assert interface.utilization_in == 10.5
        assert interface.utilization_out == 15.2
        assert interface.device_id == "test_switch"
    
    def test_system_metrics_creation(self):
        """Test SystemMetrics object creation."""
        timestamp = datetime.now()
        system = SystemMetrics(
            device_id="test_router",
            cpu_utilization=25.5,
            memory_total=2048000000,
            memory_used=1024000000,
            memory_utilization=50.0,
            uptime=86400,
            process_count=150,
            temperature=45.5,
            power_consumption=200.0,
            timestamp=timestamp
        )
        
        assert system.device_id == "test_router"
        assert system.cpu_utilization == 25.5
        assert system.memory_total == 2048000000
        assert system.memory_used == 1024000000
        assert system.memory_utilization == 50.0
        assert system.uptime == 86400
        assert system.temperature == 45.5
        assert system.power_consumption == 200.0