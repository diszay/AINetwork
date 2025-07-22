"""
Unit tests for NetArchon metrics models.
"""

import pytest
from datetime import datetime

from src.netarchon.models.metrics import (
    MetricType,
    MetricUnit,
    MetricData,
    InterfaceMetrics,
    SystemMetrics
)


class TestMetricType:
    """Test MetricType enumeration."""
    
    def test_metric_types(self):
        """Test all metric types are defined."""
        assert MetricType.INTERFACE_UTILIZATION.value == "interface_utilization"
        assert MetricType.CPU_USAGE.value == "cpu_usage"
        assert MetricType.MEMORY_USAGE.value == "memory_usage"
        assert MetricType.INTERFACE_STATUS.value == "interface_status"
        assert MetricType.INTERFACE_ERRORS.value == "interface_errors"
        assert MetricType.TEMPERATURE.value == "temperature"
        assert MetricType.POWER_CONSUMPTION.value == "power_consumption"
        assert MetricType.UPTIME.value == "uptime"


class TestMetricUnit:
    """Test MetricUnit enumeration."""
    
    def test_metric_units(self):
        """Test all metric units are defined."""
        assert MetricUnit.PERCENTAGE.value == "percentage"
        assert MetricUnit.BYTES.value == "bytes"
        assert MetricUnit.BITS_PER_SECOND.value == "bps"
        assert MetricUnit.PACKETS_PER_SECOND.value == "pps"
        assert MetricUnit.CELSIUS.value == "celsius"
        assert MetricUnit.WATTS.value == "watts"
        assert MetricUnit.SECONDS.value == "seconds"
        assert MetricUnit.COUNT.value == "count"
        assert MetricUnit.BOOLEAN.value == "boolean"


class TestMetricData:
    """Test MetricData dataclass."""
    
    def test_valid_metric_data(self):
        """Test creating valid metric data."""
        now = datetime.utcnow()
        metric = MetricData(
            device_id="router1",
            metric_type=MetricType.CPU_USAGE,
            value=75.5,
            timestamp=now,
            unit=MetricUnit.PERCENTAGE
        )
        
        assert metric.device_id == "router1"
        assert metric.metric_type == MetricType.CPU_USAGE
        assert metric.value == 75.5
        assert metric.timestamp == now
        assert metric.unit == MetricUnit.PERCENTAGE
        assert metric.interface is None
        assert metric.additional_data == {}
    
    def test_metric_with_interface(self):
        """Test metric data with interface."""
        metric = MetricData(
            device_id="router1",
            metric_type=MetricType.INTERFACE_UTILIZATION,
            value=45.2,
            timestamp=datetime.utcnow(),
            unit=MetricUnit.PERCENTAGE,
            interface="GigabitEthernet0/0/1"
        )
        
        assert metric.interface == "GigabitEthernet0/0/1"
    
    def test_empty_device_id_validation(self):
        """Test validation for empty device ID."""
        with pytest.raises(ValueError, match="Device ID cannot be empty"):
            MetricData(
                device_id="",
                metric_type=MetricType.CPU_USAGE,
                value=75.5,
                timestamp=datetime.utcnow(),
                unit=MetricUnit.PERCENTAGE
            )
    
    def test_additional_data_initialization(self):
        """Test additional_data initialization."""
        metric = MetricData(
            device_id="router1",
            metric_type=MetricType.CPU_USAGE,
            value=75.5,
            timestamp=datetime.utcnow(),
            unit=MetricUnit.PERCENTAGE,
            additional_data=None
        )
        
        assert metric.additional_data == {}
    
    def test_is_numeric(self):
        """Test is_numeric method."""
        # Numeric values
        metric = MetricData(
            device_id="router1",
            metric_type=MetricType.CPU_USAGE,
            value=75.5,
            timestamp=datetime.utcnow(),
            unit=MetricUnit.PERCENTAGE
        )
        assert metric.is_numeric() is True
        
        metric.value = 100
        assert metric.is_numeric() is True
        
        # Non-numeric values
        metric.value = "up"
        assert metric.is_numeric() is False
        
        metric.value = True
        assert metric.is_numeric() is False
    
    def test_get_numeric_value(self):
        """Test get_numeric_value method."""
        metric = MetricData(
            device_id="router1",
            metric_type=MetricType.CPU_USAGE,
            value=75.5,
            timestamp=datetime.utcnow(),
            unit=MetricUnit.PERCENTAGE
        )
        
        assert metric.get_numeric_value() == 75.5
        
        metric.value = "up"
        with pytest.raises(ValueError, match="Metric value up is not numeric"):
            metric.get_numeric_value()
    
    def test_add_metadata(self):
        """Test add_metadata method."""
        metric = MetricData(
            device_id="router1",
            metric_type=MetricType.CPU_USAGE,
            value=75.5,
            timestamp=datetime.utcnow(),
            unit=MetricUnit.PERCENTAGE
        )
        
        metric.add_metadata("source", "snmp")
        metric.add_metadata("collection_method", "polling")
        
        assert metric.additional_data["source"] == "snmp"
        assert metric.additional_data["collection_method"] == "polling"


class TestInterfaceMetrics:
    """Test InterfaceMetrics dataclass."""
    
    def test_valid_interface_metrics(self):
        """Test creating valid interface metrics."""
        now = datetime.utcnow()
        metrics = InterfaceMetrics(
            device_id="router1",
            interface_name="GigabitEthernet0/0/1",
            timestamp=now,
            status="up",
            input_bytes=1000000,
            output_bytes=2000000,
            input_packets=1500,
            output_packets=2500,
            input_errors=0,
            output_errors=1,
            utilization_percent=45.5
        )
        
        assert metrics.device_id == "router1"
        assert metrics.interface_name == "GigabitEthernet0/0/1"
        assert metrics.timestamp == now
        assert metrics.status == "up"
        assert metrics.input_bytes == 1000000
        assert metrics.output_bytes == 2000000
        assert metrics.input_packets == 1500
        assert metrics.output_packets == 2500
        assert metrics.input_errors == 0
        assert metrics.output_errors == 1
        assert metrics.utilization_percent == 45.5
    
    def test_empty_device_id_validation(self):
        """Test validation for empty device ID."""
        with pytest.raises(ValueError, match="Device ID cannot be empty"):
            InterfaceMetrics(
                device_id="",
                interface_name="GigabitEthernet0/0/1",
                timestamp=datetime.utcnow(),
                status="up",
                input_bytes=1000000,
                output_bytes=2000000,
                input_packets=1500,
                output_packets=2500,
                input_errors=0,
                output_errors=1,
                utilization_percent=45.5
            )
    
    def test_empty_interface_name_validation(self):
        """Test validation for empty interface name."""
        with pytest.raises(ValueError, match="Interface name cannot be empty"):
            InterfaceMetrics(
                device_id="router1",
                interface_name="",
                timestamp=datetime.utcnow(),
                status="up",
                input_bytes=1000000,
                output_bytes=2000000,
                input_packets=1500,
                output_packets=2500,
                input_errors=0,
                output_errors=1,
                utilization_percent=45.5
            )
    
    def test_invalid_utilization_validation(self):
        """Test validation for invalid utilization percentage."""
        with pytest.raises(ValueError, match="Utilization percent must be between 0 and 100"):
            InterfaceMetrics(
                device_id="router1",
                interface_name="GigabitEthernet0/0/1",
                timestamp=datetime.utcnow(),
                status="up",
                input_bytes=1000000,
                output_bytes=2000000,
                input_packets=1500,
                output_packets=2500,
                input_errors=0,
                output_errors=1,
                utilization_percent=150.0
            )
        
        with pytest.raises(ValueError, match="Utilization percent must be between 0 and 100"):
            InterfaceMetrics(
                device_id="router1",
                interface_name="GigabitEthernet0/0/1",
                timestamp=datetime.utcnow(),
                status="up",
                input_bytes=1000000,
                output_bytes=2000000,
                input_packets=1500,
                output_packets=2500,
                input_errors=0,
                output_errors=1,
                utilization_percent=-5.0
            )
    
    def test_is_up(self):
        """Test is_up method."""
        metrics = InterfaceMetrics(
            device_id="router1",
            interface_name="GigabitEthernet0/0/1",
            timestamp=datetime.utcnow(),
            status="up",
            input_bytes=1000000,
            output_bytes=2000000,
            input_packets=1500,
            output_packets=2500,
            input_errors=0,
            output_errors=1,
            utilization_percent=45.5
        )
        
        assert metrics.is_up() is True
        
        metrics.status = "down"
        assert metrics.is_up() is False
        
        metrics.status = "UP"  # Test case insensitive
        assert metrics.is_up() is True
    
    def test_has_errors(self):
        """Test has_errors method."""
        metrics = InterfaceMetrics(
            device_id="router1",
            interface_name="GigabitEthernet0/0/1",
            timestamp=datetime.utcnow(),
            status="up",
            input_bytes=1000000,
            output_bytes=2000000,
            input_packets=1500,
            output_packets=2500,
            input_errors=0,
            output_errors=0,
            utilization_percent=45.5
        )
        
        assert metrics.has_errors() is False
        
        metrics.input_errors = 5
        assert metrics.has_errors() is True
        
        metrics.input_errors = 0
        metrics.output_errors = 3
        assert metrics.has_errors() is True
    
    def test_get_total_bytes(self):
        """Test get_total_bytes method."""
        metrics = InterfaceMetrics(
            device_id="router1",
            interface_name="GigabitEthernet0/0/1",
            timestamp=datetime.utcnow(),
            status="up",
            input_bytes=1000000,
            output_bytes=2000000,
            input_packets=1500,
            output_packets=2500,
            input_errors=0,
            output_errors=1,
            utilization_percent=45.5
        )
        
        assert metrics.get_total_bytes() == 3000000
    
    def test_get_total_packets(self):
        """Test get_total_packets method."""
        metrics = InterfaceMetrics(
            device_id="router1",
            interface_name="GigabitEthernet0/0/1",
            timestamp=datetime.utcnow(),
            status="up",
            input_bytes=1000000,
            output_bytes=2000000,
            input_packets=1500,
            output_packets=2500,
            input_errors=0,
            output_errors=1,
            utilization_percent=45.5
        )
        
        assert metrics.get_total_packets() == 4000


class TestSystemMetrics:
    """Test SystemMetrics dataclass."""
    
    def test_valid_system_metrics(self):
        """Test creating valid system metrics."""
        now = datetime.utcnow()
        metrics = SystemMetrics(
            device_id="router1",
            timestamp=now,
            cpu_usage_percent=75.5,
            memory_usage_percent=60.2,
            uptime_seconds=86400
        )
        
        assert metrics.device_id == "router1"
        assert metrics.timestamp == now
        assert metrics.cpu_usage_percent == 75.5
        assert metrics.memory_usage_percent == 60.2
        assert metrics.uptime_seconds == 86400
        assert metrics.temperature_celsius is None
        assert metrics.power_consumption_watts is None
    
    def test_system_metrics_with_optional_fields(self):
        """Test system metrics with optional fields."""
        metrics = SystemMetrics(
            device_id="router1",
            timestamp=datetime.utcnow(),
            cpu_usage_percent=75.5,
            memory_usage_percent=60.2,
            uptime_seconds=86400,
            temperature_celsius=45.0,
            power_consumption_watts=150.5
        )
        
        assert metrics.temperature_celsius == 45.0
        assert metrics.power_consumption_watts == 150.5
    
    def test_empty_device_id_validation(self):
        """Test validation for empty device ID."""
        with pytest.raises(ValueError, match="Device ID cannot be empty"):
            SystemMetrics(
                device_id="",
                timestamp=datetime.utcnow(),
                cpu_usage_percent=75.5,
                memory_usage_percent=60.2,
                uptime_seconds=86400
            )
    
    def test_invalid_cpu_usage_validation(self):
        """Test validation for invalid CPU usage."""
        with pytest.raises(ValueError, match="CPU usage percent must be between 0 and 100"):
            SystemMetrics(
                device_id="router1",
                timestamp=datetime.utcnow(),
                cpu_usage_percent=150.0,
                memory_usage_percent=60.2,
                uptime_seconds=86400
            )
        
        with pytest.raises(ValueError, match="CPU usage percent must be between 0 and 100"):
            SystemMetrics(
                device_id="router1",
                timestamp=datetime.utcnow(),
                cpu_usage_percent=-5.0,
                memory_usage_percent=60.2,
                uptime_seconds=86400
            )
    
    def test_invalid_memory_usage_validation(self):
        """Test validation for invalid memory usage."""
        with pytest.raises(ValueError, match="Memory usage percent must be between 0 and 100"):
            SystemMetrics(
                device_id="router1",
                timestamp=datetime.utcnow(),
                cpu_usage_percent=75.5,
                memory_usage_percent=150.0,
                uptime_seconds=86400
            )
    
    def test_invalid_uptime_validation(self):
        """Test validation for invalid uptime."""
        with pytest.raises(ValueError, match="Uptime cannot be negative"):
            SystemMetrics(
                device_id="router1",
                timestamp=datetime.utcnow(),
                cpu_usage_percent=75.5,
                memory_usage_percent=60.2,
                uptime_seconds=-100
            )
    
    def test_is_high_cpu(self):
        """Test is_high_cpu method."""
        metrics = SystemMetrics(
            device_id="router1",
            timestamp=datetime.utcnow(),
            cpu_usage_percent=75.5,
            memory_usage_percent=60.2,
            uptime_seconds=86400
        )
        
        assert metrics.is_high_cpu() is False  # Default threshold 80%
        assert metrics.is_high_cpu(70.0) is True  # Custom threshold
        
        metrics.cpu_usage_percent = 85.0
        assert metrics.is_high_cpu() is True
    
    def test_is_high_memory(self):
        """Test is_high_memory method."""
        metrics = SystemMetrics(
            device_id="router1",
            timestamp=datetime.utcnow(),
            cpu_usage_percent=75.5,
            memory_usage_percent=60.2,
            uptime_seconds=86400
        )
        
        assert metrics.is_high_memory() is False  # Default threshold 80%
        assert metrics.is_high_memory(50.0) is True  # Custom threshold
        
        metrics.memory_usage_percent = 85.0
        assert metrics.is_high_memory() is True
    
    def test_get_uptime_days(self):
        """Test get_uptime_days method."""
        metrics = SystemMetrics(
            device_id="router1",
            timestamp=datetime.utcnow(),
            cpu_usage_percent=75.5,
            memory_usage_percent=60.2,
            uptime_seconds=86400  # 1 day
        )
        
        assert metrics.get_uptime_days() == 1.0
        
        metrics.uptime_seconds = 172800  # 2 days
        assert metrics.get_uptime_days() == 2.0