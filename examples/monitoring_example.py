#!/usr/bin/env python3
"""Monitoring and alerting example.

This example demonstrates how to collect metrics from network devices
and set up basic alerting based on thresholds.
"""

import sys
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.monitoring import MonitoringManager
from netarchon.core.alerting import AlertManager
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters
from netarchon.models.metrics import MetricDefinition, MetricThreshold, ThresholdOperator
from netarchon.models.alerts import AlertSeverity
from netarchon.utils.logger import get_logger
from netarchon.utils.exceptions import ConnectionError, MonitoringError

# Configure logging
logger = get_logger(__name__)


def create_sample_metrics():
    """Create sample metric definitions for demonstration."""
    metrics = []
    
    # CPU utilization metric
    cpu_metric = MetricDefinition(
        name="cpu_utilization",
        description="CPU utilization percentage",
        command="show processes cpu | include CPU utilization",
        parser="regex",
        parser_args={"pattern": r"CPU utilization for.+: (\d+)%", "group": 1},
        result_type="float",
        unit="%"
    )
    metrics.append(cpu_metric)
    
    # Memory usage metric
    memory_metric = MetricDefinition(
        name="memory_usage",
        description="Memory usage percentage",
        command="show memory statistics | include Processor",
        parser="regex",
        parser_args={"pattern": r"Processor\s+\d+\s+\d+\s+(\d+)%", "group": 1},
        result_type="float",
        unit="%"
    )
    metrics.append(memory_metric)
    
    # Interface utilization metric
    interface_metric = MetricDefinition(
        name="interface_utilization",
        description="Interface utilization",
        command="show interfaces summary",
        parser="custom",
        parser_args={"function": "parse_interface_stats"},
        result_type="dict",
        unit="various"
    )
    metrics.append(interface_metric)
    
    return metrics


def create_sample_thresholds():
    """Create sample threshold definitions for demonstration."""
    thresholds = []
    
    # High CPU threshold
    cpu_threshold = MetricThreshold(
        metric_name="cpu_utilization",
        operator=ThresholdOperator.GREATER_THAN,
        value=80.0,
        severity=AlertSeverity.WARNING,
        description="CPU utilization is high"
    )
    thresholds.append(cpu_threshold)
    
    # Critical CPU threshold
    cpu_critical = MetricThreshold(
        metric_name="cpu_utilization",
        operator=ThresholdOperator.GREATER_THAN,
        value=95.0,
        severity=AlertSeverity.CRITICAL,
        description="CPU utilization is critical"
    )
    thresholds.append(cpu_critical)
    
    # High memory threshold
    memory_threshold = MetricThreshold(
        metric_name="memory_usage",
        operator=ThresholdOperator.GREATER_THAN,
        value=85.0,
        severity=AlertSeverity.WARNING,
        description="Memory usage is high"
    )
    thresholds.append(memory_threshold)
    
    return thresholds


def main():
    """Main function demonstrating monitoring and alerting."""
    # Device configuration - modify these values for your environment
    device_config = {
        'name': 'example-router',
        'hostname': '192.168.1.1',
        'device_type': DeviceType.CISCO_IOS,
        'username': 'admin',
        'password': 'password'
    }
    
    # Override with environment variables if available
    import os
    device_config['hostname'] = os.environ.get('DEVICE_HOST', device_config['hostname'])
    device_config['username'] = os.environ.get('DEVICE_USERNAME', device_config['username'])
    device_config['password'] = os.environ.get('DEVICE_PASSWORD', device_config['password'])
    
    # Create device object
    device = Device(
        name=device_config['name'],
        hostname=device_config['hostname'],
        device_type=device_config['device_type'],
        connection_params=ConnectionParameters(
            username=device_config['username'],
            password=device_config['password']
        )
    )
    
    # Initialize components
    ssh_connector = SSHConnector()
    command_executor = CommandExecutor(ssh_connector)
    monitoring_manager = MonitoringManager()
    alert_manager = AlertManager()
    
    try:
        print(f"Connecting to device: {device.hostname}")
        
        # Connect to the device
        if not ssh_connector.connect(device):
            print("Failed to connect to device")
            return 1
            
        print("Successfully connected!")
        
        # 1. Register metric definitions
        print("\n1. Registering metric definitions...")
        metrics = create_sample_metrics()
        for metric in metrics:
            monitoring_manager.register_metric_definition(metric)
            print(f"  Registered metric: {metric.name}")
        
        # 2. Register alert thresholds
        print("\n2. Registering alert thresholds...")
        thresholds = create_sample_thresholds()
        for threshold in thresholds:
            alert_manager.register_threshold(threshold)
            print(f"  Registered threshold: {threshold.metric_name} {threshold.operator.value} {threshold.value}")
        
        # 3. Collect metrics
        print("\n3. Collecting metrics...")
        collected_metrics = {}
        
        for metric in metrics[:2]:  # Only collect CPU and memory for demo
            try:
                print(f"  Collecting {metric.name}...")
                value = monitoring_manager.collect_metric(device, metric)
                collected_metrics[metric.name] = value
                print(f"    {metric.name}: {value} {metric.unit}")
                
            except MonitoringError as e:
                print(f"    Failed to collect {metric.name}: {str(e)}")
                # Use mock data for demonstration
                if metric.name == "cpu_utilization":
                    collected_metrics[metric.name] = 25.0
                elif metric.name == "memory_usage":
                    collected_metrics[metric.name] = 45.0
                print(f"    Using mock data: {metric.name}: {collected_metrics[metric.name]} {metric.unit}")
        
        # 4. Evaluate thresholds and generate alerts
        print("\n4. Evaluating thresholds...")
        alerts_generated = 0
        
        for threshold in thresholds:
            metric_name = threshold.metric_name
            if metric_name in collected_metrics:
                value = collected_metrics[metric_name]
                
                try:
                    alert_triggered = alert_manager.evaluate_threshold(
                        device, metric_name, value, threshold
                    )
                    
                    if alert_triggered:
                        alerts_generated += 1
                        print(f"  ALERT: {threshold.description} (value: {value}, threshold: {threshold.value})")
                    else:
                        print(f"  OK: {metric_name} = {value} (threshold: {threshold.value})")
                        
                except Exception as e:
                    print(f"  Error evaluating threshold for {metric_name}: {str(e)}")
        
        # 5. Show active alerts
        print(f"\n5. Active alerts summary:")
        try:
            active_alerts = alert_manager.get_active_alerts()
            if active_alerts:
                print(f"  Total active alerts: {len(active_alerts)}")
                for alert in active_alerts[:5]:  # Show first 5 alerts
                    print(f"    - {alert.severity.value}: {alert.description}")
                    print(f"      Device: {alert.device_name}, Metric: {alert.metric_name}")
                    print(f"      Value: {alert.current_value}, Threshold: {alert.threshold_value}")
            else:
                print("  No active alerts")
                
        except Exception as e:
            print(f"  Error retrieving alerts: {str(e)}")
        
        # 6. Demonstrate continuous monitoring (brief example)
        print("\n6. Demonstrating continuous monitoring (3 cycles)...")
        for cycle in range(3):
            print(f"  Monitoring cycle {cycle + 1}/3")
            
            # Collect a single metric
            try:
                cpu_metric = metrics[0]  # CPU utilization
                value = monitoring_manager.collect_metric(device, cpu_metric)
                print(f"    CPU utilization: {value}%")
                
                # Simulate some variation in mock mode
                if not ssh_connector.is_connected(device.hostname):
                    import random
                    value = random.uniform(20, 90)
                    print(f"    Mock CPU utilization: {value}%")
                
            except Exception as e:
                print(f"    Monitoring error: {str(e)}")
            
            if cycle < 2:  # Don't sleep after last cycle
                time.sleep(2)
        
        print(f"\nGenerated {alerts_generated} alerts during this session")
        print("Monitoring example completed successfully!")
        return 0
        
    except ConnectionError as e:
        print(f"Connection error: {str(e)}")
        return 1
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1
        
    finally:
        # Always disconnect
        if ssh_connector.is_connected(device.hostname):
            ssh_connector.disconnect(device.hostname)
            print("Disconnected from device")


if __name__ == "__main__":
    sys.exit(main())