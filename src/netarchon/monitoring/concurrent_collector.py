"""
Concurrent Metrics Collection System

Advanced metrics collection system with ThreadPoolExecutor for home network devices.
Provides device-specific collectors for Arris S33, Netgear Orbi, Xfinity monitoring
with BitWarden credential integration for automated authentication.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import requests
import subprocess
import socket
import re
from pathlib import Path

from netarchon.utils.logger import get_logger
from netarchon.integrations.bitwarden.manager import BitwardenManager
from netarchon.integrations.rustdesk.home_network_integration import RustDeskHomeNetworkMonitor


class DeviceType(Enum):
    """Types of network devices for metrics collection."""
    XFINITY_GATEWAY = "xfinity_gateway"
    ARRIS_S33_MODEM = "arris_s33_modem"
    NETGEAR_ORBI_ROUTER = "netgear_orbi_router"
    NETGEAR_ORBI_SATELLITE = "netgear_orbi_satellite"
    MINI_PC_SERVER = "mini_pc_server"
    GENERIC_DEVICE = "generic_device"


class MetricType(Enum):
    """Types of metrics collected."""
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance"
    DOCSIS = "docsis"
    WIFI_MESH = "wifi_mesh"
    SYSTEM_RESOURCES = "system_resources"
    SECURITY = "security"
    BANDWIDTH = "bandwidth"
    LATENCY = "latency"


@dataclass
class MetricData:
    """Individual metric data point."""
    device_id: str
    device_name: str
    device_type: DeviceType
    metric_type: MetricType
    metric_name: str
    value: Any
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type.value,
            'metric_type': self.metric_type.value,
            'metric_name': self.metric_name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class DeviceConfig:
    """Configuration for a monitored device."""
    device_id: str
    device_name: str
    device_type: DeviceType
    ip_address: str
    credentials_id: Optional[str] = None  # BitWarden item ID
    collection_interval: int = 60  # seconds
    enabled_metrics: List[MetricType] = field(default_factory=list)
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.enabled_metrics:
            # Default metrics based on device type
            if self.device_type == DeviceType.ARRIS_S33_MODEM:
                self.enabled_metrics = [MetricType.CONNECTIVITY, MetricType.DOCSIS, MetricType.PERFORMANCE]
            elif self.device_type in [DeviceType.NETGEAR_ORBI_ROUTER, DeviceType.NETGEAR_ORBI_SATELLITE]:
                self.enabled_metrics = [MetricType.CONNECTIVITY, MetricType.WIFI_MESH, MetricType.PERFORMANCE]
            elif self.device_type == DeviceType.XFINITY_GATEWAY:
                self.enabled_metrics = [MetricType.CONNECTIVITY, MetricType.BANDWIDTH, MetricType.SECURITY]
            elif self.device_type == DeviceType.MINI_PC_SERVER:
                self.enabled_metrics = [MetricType.CONNECTIVITY, MetricType.SYSTEM_RESOURCES, MetricType.PERFORMANCE]
            else:
                self.enabled_metrics = [MetricType.CONNECTIVITY, MetricType.PERFORMANCE]

class
 DeviceCollector:
    """Base class for device-specific metric collectors."""
    
    def __init__(self, config: DeviceConfig, bitwarden_manager: BitwardenManager):
        self.config = config
        self.bitwarden_manager = bitwarden_manager
        self.logger = get_logger(f"DeviceCollector-{config.device_name}")
        self._credentials_cache = {}
        self._last_credential_fetch = None
        
    async def collect_metrics(self) -> List[MetricData]:
        """Collect all enabled metrics for this device."""
        metrics = []
        
        try:
            # Get credentials if needed
            credentials = await self._get_credentials()
            
            # Collect each enabled metric type
            for metric_type in self.config.enabled_metrics:
                try:
                    metric_data = await self._collect_metric_type(metric_type, credentials)
                    if metric_data:
                        metrics.extend(metric_data)
                except Exception as e:
                    self.logger.error(f"Failed to collect {metric_type.value} metrics: {e}")
                    # Create error metric
                    error_metric = MetricData(
                        device_id=self.config.device_id,
                        device_name=self.config.device_name,
                        device_type=self.config.device_type,
                        metric_type=metric_type,
                        metric_name="collection_error",
                        value=str(e),
                        unit="error",
                        timestamp=datetime.now(),
                        metadata={"error_type": type(e).__name__}
                    )
                    metrics.append(error_metric)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for {self.config.device_name}: {e}")
            return []
    
    async def _get_credentials(self) -> Optional[Dict[str, str]]:
        """Get device credentials from BitWarden."""
        if not self.config.credentials_id:
            return None
        
        # Cache credentials for 5 minutes
        if (self._last_credential_fetch and 
            datetime.now() - self._last_credential_fetch < timedelta(minutes=5) and
            self.config.credentials_id in self._credentials_cache):
            return self._credentials_cache[self.config.credentials_id]
        
        try:
            credentials = await self.bitwarden_manager.get_item_credentials(self.config.credentials_id)
            self._credentials_cache[self.config.credentials_id] = credentials
            self._last_credential_fetch = datetime.now()
            return credentials
        except Exception as e:
            self.logger.error(f"Failed to get credentials for {self.config.device_name}: {e}")
            return None
    
    async def _collect_metric_type(self, metric_type: MetricType, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect specific metric type. Override in subclasses."""
        if metric_type == MetricType.CONNECTIVITY:
            return await self._collect_connectivity_metrics()
        elif metric_type == MetricType.PERFORMANCE:
            return await self._collect_performance_metrics()
        else:
            return []
    
    async def _collect_connectivity_metrics(self) -> List[MetricData]:
        """Collect basic connectivity metrics."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Ping test
            result = subprocess.run(
                ['ping', '-c', '3', '-W', '3000', self.config.ip_address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            is_reachable = result.returncode == 0
            
            metrics.append(MetricData(
                device_id=self.config.device_id,
                device_name=self.config.device_name,
                device_type=self.config.device_type,
                metric_type=MetricType.CONNECTIVITY,
                metric_name="reachable",
                value=is_reachable,
                unit="boolean",
                timestamp=timestamp
            ))
            
            if is_reachable:
                # Extract latency from ping output
                latency_match = re.search(r'time=(\d+\.?\d*)', result.stdout)
                if latency_match:
                    latency = float(latency_match.group(1))
                    metrics.append(MetricData(
                        device_id=self.config.device_id,
                        device_name=self.config.device_name,
                        device_type=self.config.device_type,
                        metric_type=MetricType.LATENCY,
                        metric_name="ping_latency",
                        value=latency,
                        unit="ms",
                        timestamp=timestamp
                    ))
            
        except Exception as e:
            self.logger.error(f"Failed to collect connectivity metrics: {e}")
        
        return metrics
    
    async def _collect_performance_metrics(self) -> List[MetricData]:
        """Collect basic performance metrics."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Port scan for common services
            common_ports = [22, 23, 53, 80, 443, 8080]
            open_ports = []
            
            for port in common_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((self.config.ip_address, port))
                    sock.close()
                    
                    if result == 0:
                        open_ports.append(port)
                except:
                    pass
            
            metrics.append(MetricData(
                device_id=self.config.device_id,
                device_name=self.config.device_name,
                device_type=self.config.device_type,
                metric_type=MetricType.PERFORMANCE,
                metric_name="open_ports",
                value=open_ports,
                unit="list",
                timestamp=timestamp,
                metadata={"port_count": len(open_ports)}
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to collect performance metrics: {e}")
        
        return metrics
c
lass ArrisS33Collector(DeviceCollector):
    """Specialized collector for Arris Surfboard S33 DOCSIS 3.1 modem."""
    
    async def _collect_metric_type(self, metric_type: MetricType, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect Arris S33 specific metrics."""
        if metric_type == MetricType.DOCSIS:
            return await self._collect_docsis_metrics(credentials)
        else:
            return await super()._collect_metric_type(metric_type, credentials)
    
    async def _collect_docsis_metrics(self, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect DOCSIS 3.1 specific metrics from Arris S33."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Arris S33 web interface URL
            base_url = f"http://{self.config.ip_address}"
            
            # Create session for web scraping
            session = requests.Session()
            session.timeout = 10
            
            # Login if credentials provided
            if credentials:
                login_data = {
                    'username': credentials.get('username', 'admin'),
                    'password': credentials.get('password', '')
                }
                
                try:
                    login_response = session.post(f"{base_url}/login", data=login_data)
                    if login_response.status_code != 200:
                        self.logger.warning("Failed to login to Arris S33 web interface")
                except:
                    pass  # Continue without authentication
            
            # Get DOCSIS status page
            try:
                status_response = session.get(f"{base_url}/cgi-bin/status_cgi")
                if status_response.status_code == 200:
                    # Parse DOCSIS metrics from HTML
                    docsis_metrics = self._parse_arris_status(status_response.text)
                    
                    for metric_name, value in docsis_metrics.items():
                        metrics.append(MetricData(
                            device_id=self.config.device_id,
                            device_name=self.config.device_name,
                            device_type=self.config.device_type,
                            metric_type=MetricType.DOCSIS,
                            metric_name=metric_name,
                            value=value['value'],
                            unit=value['unit'],
                            timestamp=timestamp,
                            metadata=value.get('metadata', {})
                        ))
            except Exception as e:
                self.logger.error(f"Failed to get DOCSIS status: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to collect DOCSIS metrics: {e}")
        
        return metrics
    
    def _parse_arris_status(self, html_content: str) -> Dict[str, Dict[str, Any]]:
        """Parse DOCSIS metrics from Arris S33 status page."""
        metrics = {}
        
        try:
            # Look for common DOCSIS metrics in HTML
            # This is a simplified parser - real implementation would be more robust
            
            # Downstream power level
            power_match = re.search(r'Power Level.*?(-?\d+\.?\d*)\s*dBmV', html_content, re.IGNORECASE)
            if power_match:
                metrics['downstream_power'] = {
                    'value': float(power_match.group(1)),
                    'unit': 'dBmV',
                    'metadata': {'type': 'downstream'}
                }
            
            # SNR
            snr_match = re.search(r'SNR.*?(\d+\.?\d*)\s*dB', html_content, re.IGNORECASE)
            if snr_match:
                metrics['snr'] = {
                    'value': float(snr_match.group(1)),
                    'unit': 'dB'
                }
            
            # Upstream power
            us_power_match = re.search(r'Upstream.*?Power.*?(\d+\.?\d*)\s*dBmV', html_content, re.IGNORECASE)
            if us_power_match:
                metrics['upstream_power'] = {
                    'value': float(us_power_match.group(1)),
                    'unit': 'dBmV',
                    'metadata': {'type': 'upstream'}
                }
            
        except Exception as e:
            self.logger.error(f"Failed to parse Arris status: {e}")
        
        return metrics


class NetgearOrbiCollector(DeviceCollector):
    """Specialized collector for Netgear Orbi RBK653 mesh system."""
    
    def __init__(self, config: DeviceConfig, bitwarden_manager: BitwardenManager, is_satellite: bool = False):
        super().__init__(config, bitwarden_manager)
        self.is_satellite = is_satellite
    
    async def _collect_metric_type(self, metric_type: MetricType, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect Netgear Orbi specific metrics."""
        if metric_type == MetricType.WIFI_MESH:
            return await self._collect_wifi_mesh_metrics(credentials)
        else:
            return await super()._collect_metric_type(metric_type, credentials)
    
    async def _collect_wifi_mesh_metrics(self, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect WiFi mesh metrics from Netgear Orbi."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Netgear Orbi web interface
            base_url = f"http://{self.config.ip_address}"
            
            session = requests.Session()
            session.timeout = 10
            
            # Login to Orbi interface
            if credentials:
                login_data = {
                    'username': credentials.get('username', 'admin'),
                    'password': credentials.get('password', '')
                }
                
                try:
                    # Netgear login endpoint
                    login_response = session.post(f"{base_url}/api/login", json=login_data)
                    if login_response.status_code == 200:
                        # Get mesh status
                        mesh_response = session.get(f"{base_url}/api/mesh/status")
                        if mesh_response.status_code == 200:
                            mesh_data = mesh_response.json()
                            mesh_metrics = self._parse_orbi_mesh_data(mesh_data)
                            
                            for metric_name, value in mesh_metrics.items():
                                metrics.append(MetricData(
                                    device_id=self.config.device_id,
                                    device_name=self.config.device_name,
                                    device_type=self.config.device_type,
                                    metric_type=MetricType.WIFI_MESH,
                                    metric_name=metric_name,
                                    value=value['value'],
                                    unit=value['unit'],
                                    timestamp=timestamp,
                                    metadata=value.get('metadata', {})
                                ))
                except Exception as e:
                    self.logger.error(f"Failed to get Orbi mesh data: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to collect WiFi mesh metrics: {e}")
        
        return metrics
    
    def _parse_orbi_mesh_data(self, mesh_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Parse mesh metrics from Orbi API response."""
        metrics = {}
        
        try:
            # Connected devices
            if 'connected_devices' in mesh_data:
                metrics['connected_devices'] = {
                    'value': len(mesh_data['connected_devices']),
                    'unit': 'count'
                }
            
            # Mesh status
            if 'mesh_status' in mesh_data:
                metrics['mesh_status'] = {
                    'value': mesh_data['mesh_status'],
                    'unit': 'status'
                }
            
            # Signal strength (for satellites)
            if self.is_satellite and 'signal_strength' in mesh_data:
                metrics['backhaul_signal'] = {
                    'value': mesh_data['signal_strength'],
                    'unit': 'dBm',
                    'metadata': {'type': 'backhaul'}
                }
            
            # Bandwidth utilization
            if 'bandwidth' in mesh_data:
                metrics['bandwidth_utilization'] = {
                    'value': mesh_data['bandwidth'].get('utilization', 0),
                    'unit': 'percent'
                }
            
        except Exception as e:
            self.logger.error(f"Failed to parse Orbi mesh data: {e}")
        
        return metrics


class XfinityGatewayCollector(DeviceCollector):
    """Specialized collector for Xfinity Gateway."""
    
    async def _collect_metric_type(self, metric_type: MetricType, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect Xfinity Gateway specific metrics."""
        if metric_type == MetricType.BANDWIDTH:
            return await self._collect_bandwidth_metrics(credentials)
        elif metric_type == MetricType.SECURITY:
            return await self._collect_security_metrics(credentials)
        else:
            return await super()._collect_metric_type(metric_type, credentials)
    
    async def _collect_bandwidth_metrics(self, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect bandwidth and usage metrics from Xfinity Gateway."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Xfinity Gateway web interface
            base_url = f"http://{self.config.ip_address}"
            
            session = requests.Session()
            session.timeout = 10
            
            # Try to get usage data
            try:
                usage_response = session.get(f"{base_url}/usage.php")
                if usage_response.status_code == 200:
                    usage_metrics = self._parse_xfinity_usage(usage_response.text)
                    
                    for metric_name, value in usage_metrics.items():
                        metrics.append(MetricData(
                            device_id=self.config.device_id,
                            device_name=self.config.device_name,
                            device_type=self.config.device_type,
                            metric_type=MetricType.BANDWIDTH,
                            metric_name=metric_name,
                            value=value['value'],
                            unit=value['unit'],
                            timestamp=timestamp,
                            metadata=value.get('metadata', {})
                        ))
            except Exception as e:
                self.logger.error(f"Failed to get Xfinity usage data: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to collect bandwidth metrics: {e}")
        
        return metrics
    
    async def _collect_security_metrics(self, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect security metrics from Xfinity Gateway."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Check for security events, firewall status, etc.
            # This would require access to Xfinity Gateway's security logs
            
            # Placeholder for security metrics
            metrics.append(MetricData(
                device_id=self.config.device_id,
                device_name=self.config.device_name,
                device_type=self.config.device_type,
                metric_type=MetricType.SECURITY,
                metric_name="firewall_status",
                value="active",
                unit="status",
                timestamp=timestamp
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to collect security metrics: {e}")
        
        return metrics
    
    def _parse_xfinity_usage(self, html_content: str) -> Dict[str, Dict[str, Any]]:
        """Parse usage metrics from Xfinity Gateway."""
        metrics = {}
        
        try:
            # Parse bandwidth usage from HTML
            # This is device-specific and would need to be adapted
            
            # Look for data usage patterns
            usage_match = re.search(r'Data Usage.*?(\d+\.?\d*)\s*(GB|MB)', html_content, re.IGNORECASE)
            if usage_match:
                value = float(usage_match.group(1))
                unit = usage_match.group(2)
                
                # Convert to GB
                if unit.upper() == 'MB':
                    value = value / 1024
                
                metrics['data_usage'] = {
                    'value': value,
                    'unit': 'GB'
                }
            
        except Exception as e:
            self.logger.error(f"Failed to parse Xfinity usage: {e}")
        
        return metrics


class MiniPCServerCollector(DeviceCollector):
    """Specialized collector for Mini PC Ubuntu 24.04 LTS server."""
    
    async def _collect_metric_type(self, metric_type: MetricType, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect Mini PC server specific metrics."""
        if metric_type == MetricType.SYSTEM_RESOURCES:
            return await self._collect_system_resources(credentials)
        else:
            return await super()._collect_metric_type(metric_type, credentials)
    
    async def _collect_system_resources(self, credentials: Optional[Dict[str, str]]) -> List[MetricData]:
        """Collect system resource metrics from Mini PC server."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            if credentials:
                # SSH into server and collect system metrics
                ssh_metrics = await self._collect_ssh_metrics(credentials)
                metrics.extend(ssh_metrics)
            
            # Also collect external metrics (SNMP, web interface, etc.)
            external_metrics = await self._collect_external_metrics()
            metrics.extend(external_metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to collect system resources: {e}")
        
        return metrics
    
    async def _collect_ssh_metrics(self, credentials: Dict[str, str]) -> List[MetricData]:
        """Collect metrics via SSH connection."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Use SSH to run system commands
            commands = {
                'cpu_usage': "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1",
                'memory_usage': "free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100.0}'",
                'disk_usage': "df -h / | awk 'NR==2{printf \"%s\", $5}' | cut -d'%' -f1",
                'load_average': "uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | cut -d',' -f1",
                'docker_containers': "docker ps --format 'table {{.Names}}' | wc -l"
            }
            
            username = credentials.get('username', 'root')
            
            for metric_name, command in commands.items():
                try:
                    result = subprocess.run(
                        ['ssh', f"{username}@{self.config.ip_address}", command],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        value_str = result.stdout.strip()
                        
                        # Parse value based on metric type
                        if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                            try:
                                value = float(value_str)
                                unit = 'percent'
                            except ValueError:
                                continue
                        elif metric_name == 'load_average':
                            try:
                                value = float(value_str)
                                unit = 'load'
                            except ValueError:
                                continue
                        elif metric_name == 'docker_containers':
                            try:
                                value = max(0, int(value_str) - 1)  # Subtract header line
                                unit = 'count'
                            except ValueError:
                                continue
                        else:
                            value = value_str
                            unit = 'string'
                        
                        metrics.append(MetricData(
                            device_id=self.config.device_id,
                            device_name=self.config.device_name,
                            device_type=self.config.device_type,
                            metric_type=MetricType.SYSTEM_RESOURCES,
                            metric_name=metric_name,
                            value=value,
                            unit=unit,
                            timestamp=timestamp
                        ))
                        
                except Exception as e:
                    self.logger.error(f"Failed to collect {metric_name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to collect SSH metrics: {e}")
        
        return metrics
    
    async def _collect_external_metrics(self) -> List[MetricData]:
        """Collect external metrics (web interface, SNMP, etc.)."""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Check for web services
            web_ports = [80, 443, 8080, 8443]
            active_services = []
            
            for port in web_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((self.config.ip_address, port))
                    sock.close()
                    
                    if result == 0:
                        active_services.append(port)
                except:
                    pass
            
            metrics.append(MetricData(
                device_id=self.config.device_id,
                device_name=self.config.device_name,
                device_type=self.config.device_type,
                metric_type=MetricType.SYSTEM_RESOURCES,
                metric_name="active_web_services",
                value=active_services,
                unit="list",
                timestamp=timestamp,
                metadata={"service_count": len(active_services)}
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to collect external metrics: {e}")
        
        return metrics
cla
ss ConcurrentMetricCollector:
    """
    Main concurrent metrics collection system with ThreadPoolExecutor.
    
    Manages multiple device collectors and coordinates concurrent metric collection
    across the home network with BitWarden credential integration.
    """
    
    def __init__(self, max_workers: int = 10, collection_interval: int = 60):
        self.max_workers = max_workers
        self.collection_interval = collection_interval
        self.logger = get_logger("ConcurrentMetricCollector")
        
        # Initialize components
        self.bitwarden_manager = BitwardenManager()
        self.rustdesk_monitor = RustDeskHomeNetworkMonitor()
        
        # Device configurations
        self.device_configs: Dict[str, DeviceConfig] = {}
        self.device_collectors: Dict[str, DeviceCollector] = {}
        
        # Collection state
        self._running = False
        self._collection_thread = None
        self._executor = None
        
        # Metrics storage
        self.metrics_buffer: List[MetricData] = []
        self.metrics_lock = threading.Lock()
        
        # Initialize default home network devices
        self._initialize_home_network_devices()
    
    def _initialize_home_network_devices(self):
        """Initialize default home network device configurations."""
        # Xfinity Gateway
        self.add_device_config(DeviceConfig(
            device_id="xfinity_gateway",
            device_name="Xfinity Gateway",
            device_type=DeviceType.XFINITY_GATEWAY,
            ip_address="192.168.1.1",
            credentials_id="xfinity_gateway_creds",  # BitWarden item ID
            collection_interval=120,  # 2 minutes
            enabled_metrics=[MetricType.CONNECTIVITY, MetricType.BANDWIDTH, MetricType.SECURITY]
        ))
        
        # Arris S33 Modem
        self.add_device_config(DeviceConfig(
            device_id="arris_s33",
            device_name="Arris Surfboard S33",
            device_type=DeviceType.ARRIS_S33_MODEM,
            ip_address="192.168.100.1",
            credentials_id="arris_s33_creds",
            collection_interval=60,  # 1 minute
            enabled_metrics=[MetricType.CONNECTIVITY, MetricType.DOCSIS, MetricType.PERFORMANCE]
        ))
        
        # Netgear Orbi Router
        self.add_device_config(DeviceConfig(
            device_id="netgear_orbi_router",
            device_name="Netgear Orbi RBK653 Router",
            device_type=DeviceType.NETGEAR_ORBI_ROUTER,
            ip_address="192.168.1.10",
            credentials_id="netgear_orbi_creds",
            collection_interval=90,  # 1.5 minutes
            enabled_metrics=[MetricType.CONNECTIVITY, MetricType.WIFI_MESH, MetricType.PERFORMANCE]
        ))
        
        # Netgear Orbi Satellites
        for i, satellite_ip in enumerate(["192.168.1.2", "192.168.1.3"]):
            self.add_device_config(DeviceConfig(
                device_id=f"netgear_orbi_satellite_{i+1}",
                device_name=f"Netgear Orbi Satellite {i+1}",
                device_type=DeviceType.NETGEAR_ORBI_SATELLITE,
                ip_address=satellite_ip,
                credentials_id="netgear_orbi_creds",  # Same creds as router
                collection_interval=120,  # 2 minutes
                enabled_metrics=[MetricType.CONNECTIVITY, MetricType.WIFI_MESH, MetricType.PERFORMANCE]
            ))
        
        # Mini PC Server
        self.add_device_config(DeviceConfig(
            device_id="mini_pc_server",
            device_name="Mini PC Ubuntu Server",
            device_type=DeviceType.MINI_PC_SERVER,
            ip_address="192.168.1.100",
            credentials_id="mini_pc_server_creds",
            collection_interval=30,  # 30 seconds (more frequent for server)
            enabled_metrics=[MetricType.CONNECTIVITY, MetricType.SYSTEM_RESOURCES, MetricType.PERFORMANCE]
        ))
    
    def add_device_config(self, config: DeviceConfig):
        """Add a device configuration for monitoring."""
        self.device_configs[config.device_id] = config
        
        # Create appropriate collector
        if config.device_type == DeviceType.ARRIS_S33_MODEM:
            collector = ArrisS33Collector(config, self.bitwarden_manager)
        elif config.device_type == DeviceType.NETGEAR_ORBI_ROUTER:
            collector = NetgearOrbiCollector(config, self.bitwarden_manager, is_satellite=False)
        elif config.device_type == DeviceType.NETGEAR_ORBI_SATELLITE:
            collector = NetgearOrbiCollector(config, self.bitwarden_manager, is_satellite=True)
        elif config.device_type == DeviceType.XFINITY_GATEWAY:
            collector = XfinityGatewayCollector(config, self.bitwarden_manager)
        elif config.device_type == DeviceType.MINI_PC_SERVER:
            collector = MiniPCServerCollector(config, self.bitwarden_manager)
        else:
            collector = DeviceCollector(config, self.bitwarden_manager)
        
        self.device_collectors[config.device_id] = collector
        self.logger.info(f"Added device collector: {config.device_name}")
    
    def start_collection(self):
        """Start concurrent metrics collection."""
        if self._running:
            self.logger.warning("Collection already running")
            return
        
        self._running = True
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collection_thread.start()
        
        self.logger.info(f"Started concurrent metrics collection with {self.max_workers} workers")
    
    def stop_collection(self):
        """Stop concurrent metrics collection."""
        if not self._running:
            return
        
        self._running = False
        
        if self._executor:
            self._executor.shutdown(wait=True)
        
        if self._collection_thread:
            self._collection_thread.join(timeout=10)
        
        self.logger.info("Stopped concurrent metrics collection")
    
    def _collection_loop(self):
        """Main collection loop running in separate thread."""
        self.logger.info("Starting metrics collection loop")
        
        while self._running:
            try:
                start_time = time.time()
                
                # Submit collection tasks for all devices
                futures = []
                for device_id, collector in self.device_collectors.items():
                    config = self.device_configs[device_id]
                    
                    # Check if it's time to collect for this device
                    if self._should_collect_for_device(device_id):
                        future = self._executor.submit(self._collect_device_metrics, device_id, collector)
                        futures.append((device_id, future))
                
                # Wait for all collections to complete
                for device_id, future in futures:
                    try:
                        metrics = future.result(timeout=30)  # 30 second timeout per device
                        if metrics:
                            with self.metrics_lock:
                                self.metrics_buffer.extend(metrics)
                            self.logger.debug(f"Collected {len(metrics)} metrics from {device_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to collect metrics from {device_id}: {e}")
                
                # Calculate sleep time to maintain collection interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.collection_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def _should_collect_for_device(self, device_id: str) -> bool:
        """Check if it's time to collect metrics for a specific device."""
        # For now, collect from all devices every cycle
        # In a more advanced implementation, this would track last collection time per device
        return True
    
    def _collect_device_metrics(self, device_id: str, collector: DeviceCollector) -> List[MetricData]:
        """Collect metrics from a single device (runs in thread pool)."""
        try:
            # Run async collection in thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                metrics = loop.run_until_complete(collector.collect_metrics())
                return metrics
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"Failed to collect metrics from {device_id}: {e}")
            return []
    
    def get_recent_metrics(self, device_id: Optional[str] = None, 
                          metric_type: Optional[MetricType] = None,
                          minutes_back: int = 60) -> List[MetricData]:
        """Get recent metrics from buffer."""
        with self.metrics_lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes_back)
            
            filtered_metrics = []
            for metric in self.metrics_buffer:
                if metric.timestamp < cutoff_time:
                    continue
                
                if device_id and metric.device_id != device_id:
                    continue
                
                if metric_type and metric.metric_type != metric_type:
                    continue
                
                filtered_metrics.append(metric)
            
            return filtered_metrics
    
    def get_device_status_summary(self) -> Dict[str, Any]:
        """Get summary of all device statuses."""
        summary = {
            'total_devices': len(self.device_configs),
            'active_collectors': len(self.device_collectors),
            'collection_running': self._running,
            'devices': {}
        }
        
        # Get recent connectivity metrics for each device
        recent_metrics = self.get_recent_metrics(minutes_back=10)
        
        for device_id, config in self.device_configs.items():
            device_metrics = [m for m in recent_metrics if m.device_id == device_id]
            
            # Find latest connectivity metric
            connectivity_metrics = [m for m in device_metrics if m.metric_type == MetricType.CONNECTIVITY and m.metric_name == "reachable"]
            
            is_reachable = False
            last_seen = None
            
            if connectivity_metrics:
                latest_connectivity = max(connectivity_metrics, key=lambda x: x.timestamp)
                is_reachable = latest_connectivity.value
                last_seen = latest_connectivity.timestamp
            
            summary['devices'][device_id] = {
                'name': config.device_name,
                'type': config.device_type.value,
                'ip_address': config.ip_address,
                'reachable': is_reachable,
                'last_seen': last_seen.isoformat() if last_seen else None,
                'metrics_count': len(device_metrics),
                'collection_interval': config.collection_interval
            }
        
        return summary
    
    def clear_metrics_buffer(self, older_than_hours: int = 24):
        """Clear old metrics from buffer to prevent memory issues."""
        with self.metrics_lock:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            self.metrics_buffer = [m for m in self.metrics_buffer if m.timestamp >= cutoff_time]
            
        self.logger.info(f"Cleared metrics older than {older_than_hours} hours")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self.metrics_lock:
            total_metrics = len(self.metrics_buffer)
            
            if total_metrics == 0:
                return {
                    'total_metrics': 0,
                    'devices': {},
                    'metric_types': {},
                    'collection_status': 'no_data'
                }
            
            # Group metrics by device
            device_metrics = {}
            metric_type_counts = {}
            
            for metric in self.metrics_buffer:
                # Device grouping
                if metric.device_id not in device_metrics:
                    device_metrics[metric.device_id] = {
                        'name': metric.device_name,
                        'type': metric.device_type.value,
                        'metrics_count': 0,
                        'latest_timestamp': None,
                        'metric_types': set()
                    }
                
                device_metrics[metric.device_id]['metrics_count'] += 1
                device_metrics[metric.device_id]['metric_types'].add(metric.metric_type.value)
                
                if (device_metrics[metric.device_id]['latest_timestamp'] is None or 
                    metric.timestamp > device_metrics[metric.device_id]['latest_timestamp']):
                    device_metrics[metric.device_id]['latest_timestamp'] = metric.timestamp
                
                # Metric type counting
                metric_type_counts[metric.metric_type.value] = metric_type_counts.get(metric.metric_type.value, 0) + 1
            
            # Convert sets to lists for JSON serialization
            for device_data in device_metrics.values():
                device_data['metric_types'] = list(device_data['metric_types'])
                if device_data['latest_timestamp']:
                    device_data['latest_timestamp'] = device_data['latest_timestamp'].isoformat()
            
            return {
                'total_metrics': total_metrics,
                'devices': device_metrics,
                'metric_types': metric_type_counts,
                'collection_status': 'active' if self._running else 'stopped',
                'buffer_size': total_metrics,
                'oldest_metric': min(self.metrics_buffer, key=lambda x: x.timestamp).timestamp.isoformat() if self.metrics_buffer else None,
                'newest_metric': max(self.metrics_buffer, key=lambda x: x.timestamp).timestamp.isoformat() if self.metrics_buffer else None
            }