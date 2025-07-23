#!/usr/bin/env python3
"""Advanced monitoring example with multiple devices and metrics.

This example demonstrates:
- Monitoring multiple devices concurrently
- Collecting multiple metrics per device
- Setting up complex alerting rules
- Storing metrics data for analysis
- Handling monitoring failures gracefully
"""

import os
import sys
import time
import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any

# Add src to path for development
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from netarchon.core.ssh_connector import SSHConnector
from netarchon.core.command_executor import CommandExecutor
from netarchon.core.monitoring import MonitoringManager
from netarchon.core.alerting import AlertManager
from netarchon.models.device import Device, DeviceType
from netarchon.models.connection import ConnectionParameters
from netarchon.models.metrics import MetricDefinition, MetricThreshold, ThresholdOperator
from netarchon.models.alerts import AlertSeverity
from netarchon.utils.logger import get_logger, configure_logging
from netarchon.utils.circuit_breaker import create_circuit_breaker
from netarchon.utils.retry_manager import RetryManager, BackoffStrategy

# Configure logging
configure_logging(level="INFO", console=True)
logger = get_logger(__name__)


class AdvancedMonitor:
    """Advanced monitoring system for network devices."""
    
    def __init__(self):
        """Initialize the monitoring system."""
        self.ssh_connector = SSHConnector(pool_size=20)
        self.command_executor = CommandExecutor(self.ssh_connector)
        self.monitoring_manager = MonitoringManager()
        self.alert_manager = AlertManager()
        
        # Create circuit breaker for device operations
        self.device_breaker = create_circuit_breaker(
            "device_operations",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        # Create retry manager for metric collection
        self.metric_retry = RetryManager(
            max_attempts=3,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            initial_delay=1.0,
            max_delay=10.0
        )
        
        self.devices = []
        self.metrics_data = []
        self.monitoring_active = False
        
    def add_device(self, device: Device) -> None:
        """Add a device to monitor."""
        self.devices.append(device)
        logger.info(f"Added device {device.name} ({device.hostname}) to monitoring")
        
    def setup_metrics(self) -> None:
        """Set up metric definitions for different device types."""
        # CPU metrics for different device types
        cisco_cpu_metric = MetricDefinition(
            name="cpu_utilization",
            description="CPU utilization percentage",
            command="show processes cpu | include CPU utilization",
            parser="regex",
            parser_args={"pattern": r"CPU utilization for.+: (\d+)%", "group": 1},
            result_type="float",
            unit="%",
            tags=["performance", "cpu"]
        )
        
        # Memory metrics
        cisco_memory_metric = MetricDefinition(
            name="memory_usage",
            description="Memory usage percentage",
            command="show memory statistics | include Processor",
            parser="regex",
            parser_args={"pattern": r"Processor\s+\d+\s+\d+\s+(\d+)%", "group": 1},
            result_type="float",
            unit="%",
            tags=["performance", "memory"]
        )
        
        # Interface metrics
        interface_status_metric = MetricDefinition(
            name="interface_up_count",
            description="Number of interfaces in up state",
            command="show ip interface brief | include up",
            parser="line_count",
            parser_args={},
            result_type="int",
            unit="count",
            tags=["interfaces", "availability"]
        )
        
        # Temperature metrics (for devices that support it)
        temperature_metric = MetricDefinition(
            name="temperature",
            description="Device temperature in Celsius",
            command="show environment temperature",
            parser="regex",
            parser_args={"pattern": r"Temperature:\s+(\d+)C", "group": 1},
            result_type="float",
            unit="°C",
            tags=["environment", "temperature"]
        )
        
        # Register metrics
        metrics = [cisco_cpu_metric, cisco_memory_metric, interface_status_metric, temperature_metric]
        for metric in metrics:
            self.monitoring_manager.register_metric_definition(metric)
            
        logger.info(f"Registered {len(metrics)} metric definitions")
        
    def setup_thresholds(self) -> None:
        """Set up alerting thresholds."""
        thresholds = [
            # Critical CPU threshold
            MetricThreshold(
                metric_name="cpu_utilization",
                operator=ThresholdOperator.GREATER_THAN,
                value=90.0,
                severity=AlertSeverity.CRITICAL,
                description="CPU utilization is critically high",
                cooldown_period=300
            ),
            # Warning CPU threshold
            MetricThreshold(
                metric_name="cpu_utilization",
                operator=ThresholdOperator.GREATER_THAN,
                value=75.0,
                severity=AlertSeverity.WARNING,
                description="CPU utilization is high",
                cooldown_period=600
            ),
            # Critical memory threshold
            MetricThreshold(
                metric_name="memory_usage",
                operator=ThresholdOperator.GREATER_THAN,
                value=85.0,
                severity=AlertSeverity.CRITICAL,
                description="Memory usage is critically high",
                cooldown_period=300
            ),
            # Interface availability threshold
            MetricThreshold(
                metric_name="interface_up_count",
                operator=ThresholdOperator.LESS_THAN,
                value=2,
                severity=AlertSeverity.WARNING,
                description="Low number of active interfaces",
                cooldown_period=900
            ),
            # Temperature threshold
            MetricThreshold(
                metric_name="temperature",
                operator=ThresholdOperator.GREATER_THAN,
                value=70.0,
                severity=AlertSeverity.WARNING,
                description="Device temperature is high",
                cooldown_period=1800
            )
        ]
        
        for threshold in thresholds:
            self.alert_manager.register_threshold(threshold)
            
        logger.info(f"Registered {len(thresholds)} alerting thresholds")
        
    def collect_device_metrics(self, device: Device) -> Dict[str, Any]:
        """Collect all metrics from a single device."""
        device_metrics = {
            "device_name": device.name,
            "hostname": device.hostname,
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
            "errors": []
        }
        
        try:
            # Use circuit breaker for connection
            connected = self.device_breaker.call(self.ssh_connector.connect, device)
            if not connected:
                raise Exception("Failed to connect to device")
                
            # Get all registered metrics
            metric_definitions = self.monitoring_manager.get_metric_definitions()
            
            for metric_def in metric_definitions:
                try:
                    # Use retry manager for metric collection
                    value = self.metric_retry.call(
                        self.monitoring_manager.collect_metric,
                        device,
                        metric_def
                    )
                    device_metrics["metrics"][metric_def.name] = {
                        "value": value,
                        "unit": metric_def.unit,
                        "tags": metric_def.tags
                    }
                    
                    # Evaluate thresholds
                    thresholds = self.alert_manager.get_thresholds_for_metric(metric_def.name)
                    for threshold in thresholds:
                        alert_triggered = self.alert_manager.evaluate_threshold(
                            device, metric_def.name, value, threshold
                        )
                        if alert_triggered:
                            logger.warning(
                                f"Alert triggered for {device.name}: {threshold.description} "
                                f"(value: {value}, threshold: {threshold.value})"
                            )
                            
                except Exception as e:
                    error_msg = f"Failed to collect metric {metric_def.name}: {str(e)}"
                    device_metrics["errors"].append(error_msg)
                    logger.error(f"Device {device.name}: {error_msg}")
                    
        except Exception as e:
            error_msg = f"Failed to collect metrics from device: {str(e)}"
            device_metrics["errors"].append(error_msg)
            logger.error(f"Device {device.name}: {error_msg}")
            
        return device_metrics
        
    def monitor_devices_concurrent(self) -> List[Dict[str, Any]]:
        """Monitor all devices concurrently."""
        results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit monitoring tasks
            future_to_device = {
                executor.submit(self.collect_device_metrics, device): device
                for device in self.devices
            }
            
            # Collect results
            for future in as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result(timeout=60)  # 1 minute timeout per device
                    results.append(result)
                    logger.info(f"Collected metrics from {device.name}")
                except Exception as e:
                    logger.error(f"Failed to monitor device {device.name}: {str(e)}")
                    results.append({
                        "device_name": device.name,
                        "hostname": device.hostname,
                        "timestamp": datetime.now().isoformat(),
                        "metrics": {},
                        "errors": [f"Monitoring failed: {str(e)}"]
                    })
                    
        return results
        
    def save_metrics_data(self, metrics_data: List[Dict[str, Any]]) -> None:
        """Save metrics data to file."""
        os.makedirs("metrics", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"metrics/metrics_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            logger.info(f"Saved metrics data to {filename}")
        except Exception as e:
            logger.error(f"Failed to save metrics data: {str(e)}")
            
    def generate_summary_report(self, metrics_data: List[Dict[str, Any]]) -> None:
        """Generate a summary report of collected metrics."""
        print("\n" + "="*60)
        print("MONITORING SUMMARY REPORT")
        print("="*60)
        
        total_devices = len(metrics_data)
        successful_devices = len([d for d in metrics_data if not d["errors"]])
        failed_devices = total_devices - successful_devices
        
        print(f"Total devices monitored: {total_devices}")
        print(f"Successful collections: {successful_devices}")
        print(f"Failed collections: {failed_devices}")
        print()
        
        # Metrics summary
        all_metrics = {}
        for device_data in metrics_data:
            for metric_name, metric_info in device_data["metrics"].items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(metric_info["value"])
                
        print("METRICS SUMMARY:")
        print("-" * 40)
        for metric_name, values in all_metrics.items():
            if values:
                avg_value = sum(values) / len(values)
                min_value = min(values)
                max_value = max(values)
                print(f"{metric_name}:")
                print(f"  Average: {avg_value:.2f}")
                print(f"  Min: {min_value:.2f}")
                print(f"  Max: {max_value:.2f}")
                print(f"  Samples: {len(values)}")
                print()
                
        # Active alerts summary
        active_alerts = self.alert_manager.get_active_alerts()
        print(f"ACTIVE ALERTS: {len(active_alerts)}")
        print("-" * 40)
        for alert in active_alerts:
            print(f"• {alert.device_name}: {alert.description}")
            print(f"  Severity: {alert.severity.value.upper()}")
            print(f"  Value: {alert.value}, Threshold: {alert.threshold_value}")
            print()
            
    def start_continuous_monitoring(self, interval: int = 300) -> None:
        """Start continuous monitoring with specified interval."""
        self.monitoring_active = True
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        def monitoring_loop():
            while self.monitoring_active:
                try:
                    logger.info("Starting monitoring cycle")
                    metrics_data = self.monitor_devices_concurrent()
                    
                    # Save data
                    self.save_metrics_data(metrics_data)
                    
                    # Generate report
                    self.generate_summary_report(metrics_data)
                    
                    # Store for analysis
                    self.metrics_data.extend(metrics_data)
                    
                    # Keep only last 100 monitoring cycles
                    if len(self.metrics_data) > 100 * len(self.devices):
                        self.metrics_data = self.metrics_data[-100 * len(self.devices):]
                        
                    logger.info(f"Monitoring cycle completed, sleeping for {interval}s")
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {str(e)}")
                    time.sleep(60)  # Wait 1 minute on error
                    
        # Start monitoring in background thread
        monitoring_thread = threading.Thread(target=monitoring_loop)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        
    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self.monitoring_active = False
        logger.info("Stopping continuous monitoring")
        
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_monitoring()
        for device in self.devices:
            try:
                self.ssh_connector.disconnect(device.hostname)
            except Exception as e:
                logger.error(f"Error disconnecting from {device.hostname}: {str(e)}")


def main():
    """Main function demonstrating advanced monitoring."""
    # Create monitoring system
    monitor = AdvancedMonitor()
    
    # Add devices to monitor
    devices = [
        Device(
            name="core-router-1",
            hostname="192.168.1.1",
            device_type=DeviceType.CISCO_IOS,
            connection_params=ConnectionParameters(
                username=os.environ.get("DEVICE_USERNAME", "admin"),
                password=os.environ.get("DEVICE_PASSWORD", "password")
            )
        ),
        Device(
            name="access-switch-1",
            hostname="192.168.1.10",
            device_type=DeviceType.CISCO_IOS,
            connection_params=ConnectionParameters(
                username=os.environ.get("DEVICE_USERNAME", "admin"),
                password=os.environ.get("DEVICE_PASSWORD", "password")
            )
        ),
        Device(
            name="distribution-switch-1",
            hostname="192.168.1.20",
            device_type=DeviceType.CISCO_IOS,
            connection_params=ConnectionParameters(
                username=os.environ.get("DEVICE_USERNAME", "admin"),
                password=os.environ.get("DEVICE_PASSWORD", "password")
            )
        )
    ]
    
    for device in devices:
        monitor.add_device(device)
        
    # Setup monitoring
    monitor.setup_metrics()
    monitor.setup_thresholds()
    
    try:
        # Run one-time monitoring
        print("Running one-time monitoring cycle...")
        metrics_data = monitor.monitor_devices_concurrent()
        monitor.save_metrics_data(metrics_data)
        monitor.generate_summary_report(metrics_data)
        
        # Option to start continuous monitoring
        response = input("\nStart continuous monitoring? (y/n): ")
        if response.lower() == 'y':
            interval = int(input("Enter monitoring interval in seconds (default 300): ") or "300")
            monitor.start_continuous_monitoring(interval)
            
            print("Continuous monitoring started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
                monitor.stop_monitoring()
                
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        monitor.cleanup()


if __name__ == "__main__":
    main()