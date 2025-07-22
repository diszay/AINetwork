"""
NetArchon Metrics Models

Data structures for monitoring metrics and performance data.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Union, Dict, Any, Optional


class MetricType(Enum):
    """Types of metrics that can be collected."""
    INTERFACE_UTILIZATION = "interface_utilization"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    INTERFACE_STATUS = "interface_status"
    INTERFACE_ERRORS = "interface_errors"
    TEMPERATURE = "temperature"
    POWER_CONSUMPTION = "power_consumption"
    UPTIME = "uptime"


class MetricUnit(Enum):
    """Units for metric values."""
    PERCENTAGE = "percentage"
    BYTES = "bytes"
    BITS_PER_SECOND = "bps"
    PACKETS_PER_SECOND = "pps"
    CELSIUS = "celsius"
    WATTS = "watts"
    SECONDS = "seconds"
    COUNT = "count"
    BOOLEAN = "boolean"


@dataclass
class MetricData:
    """Individual metric data point."""
    device_id: str
    metric_type: MetricType
    value: Union[int, float, str, bool]
    timestamp: datetime
    unit: MetricUnit
    interface: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate metric data after initialization."""
        if not self.device_id:
            raise ValueError("Device ID cannot be empty")
        if self.additional_data is None:
            self.additional_data = {}
    
    def is_numeric(self) -> bool:
        """Check if metric value is numeric."""
        return isinstance(self.value, (int, float))
    
    def get_numeric_value(self) -> Union[int, float]:
        """Get numeric value, raising error if not numeric."""
        if not self.is_numeric():
            raise ValueError(f"Metric value {self.value} is not numeric")
        return self.value
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the metric."""
        self.additional_data[key] = value


@dataclass
class InterfaceMetrics:
    """Interface-specific metrics collection."""
    device_id: str
    interface_name: str
    timestamp: datetime
    status: str
    input_bytes: int
    output_bytes: int
    input_packets: int
    output_packets: int
    input_errors: int
    output_errors: int
    utilization_percent: float
    
    def __post_init__(self):
        """Validate interface metrics."""
        if not self.device_id:
            raise ValueError("Device ID cannot be empty")
        if not self.interface_name:
            raise ValueError("Interface name cannot be empty")
        if self.utilization_percent < 0 or self.utilization_percent > 100:
            raise ValueError("Utilization percent must be between 0 and 100")
    
    def is_up(self) -> bool:
        """Check if interface is up."""
        return self.status.lower() == "up"
    
    def has_errors(self) -> bool:
        """Check if interface has errors."""
        return self.input_errors > 0 or self.output_errors > 0
    
    def get_total_bytes(self) -> int:
        """Get total bytes (input + output)."""
        return self.input_bytes + self.output_bytes
    
    def get_total_packets(self) -> int:
        """Get total packets (input + output)."""
        return self.input_packets + self.output_packets


@dataclass
class SystemMetrics:
    """System-level metrics for a device."""
    device_id: str
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    uptime_seconds: int
    temperature_celsius: Optional[float] = None
    power_consumption_watts: Optional[float] = None
    
    def __post_init__(self):
        """Validate system metrics."""
        if not self.device_id:
            raise ValueError("Device ID cannot be empty")
        if self.cpu_usage_percent < 0 or self.cpu_usage_percent > 100:
            raise ValueError("CPU usage percent must be between 0 and 100")
        if self.memory_usage_percent < 0 or self.memory_usage_percent > 100:
            raise ValueError("Memory usage percent must be between 0 and 100")
        if self.uptime_seconds < 0:
            raise ValueError("Uptime cannot be negative")
    
    def is_high_cpu(self, threshold: float = 80.0) -> bool:
        """Check if CPU usage is above threshold."""
        return self.cpu_usage_percent > threshold
    
    def is_high_memory(self, threshold: float = 80.0) -> bool:
        """Check if memory usage is above threshold."""
        return self.memory_usage_percent > threshold
    
    def get_uptime_days(self) -> float:
        """Get uptime in days."""
        return self.uptime_seconds / 86400  # 24 * 60 * 60