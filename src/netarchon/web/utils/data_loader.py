"""
NetArchon Data Loader

Provides cached data integration with NetArchon core modules for Streamlit interface.
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

# Import NetArchon core modules
from ...core.ssh_connector import SSHConnector, ConnectionPool
from ...core.device_manager import DeviceDetector
from ...core.config_manager import ConfigManager
from ...core.monitoring import MonitoringCollector, InterfaceMetrics, SystemMetrics
from ...models.connection import ConnectionInfo, AuthenticationCredentials, ConnectionType
from ...models.device import DeviceInfo, DeviceType
from ...utils.exceptions import NetArchonError


class NetArchonDataLoader:
    """Cached data loader for NetArchon web interface."""
    
    def __init__(self):
        """Initialize the data loader with core NetArchon components."""
        self.ssh_connector = SSHConnector()
        self.connection_pool = ConnectionPool()
        self.device_detector = DeviceDetector()
        self.config_manager = ConfigManager()
        self.monitoring_collector = MonitoringCollector()
        
        # Cache TTL settings (in seconds)
        self.cache_ttl = {
            'devices': 300,  # 5 minutes
            'device_status': 30,  # 30 seconds
            'metrics': 60,  # 1 minute
            'configs': 3600,  # 1 hour
            'system_info': 600  # 10 minutes
        }

    @st.cache_data(ttl=300)
    def load_discovered_devices(_self) -> List[Dict[str, Any]]:
        """Load and cache list of discovered network devices.
        
        Returns:
            List of device dictionaries with basic information
        """
        try:
            devices = []
            
            # Add sample home network devices for demonstration
            home_devices = [
                {
                    'id': 'xfinity_gateway',
                    'name': 'Xfinity Gateway',
                    'ip_address': '192.168.1.1',
                    'device_type': 'router',
                    'vendor': 'Arris',
                    'model': 'Surfboard S33',
                    'status': 'online',
                    'last_seen': datetime.now().isoformat(),
                    'is_home_device': True
                },
                {
                    'id': 'netgear_orbi',
                    'name': 'Netgear Orbi Router',
                    'ip_address': '192.168.1.10',
                    'device_type': 'router',
                    'vendor': 'Netgear',
                    'model': 'RBK653-100NAS',
                    'status': 'online',
                    'last_seen': datetime.now().isoformat(),
                    'is_home_device': True
                },
                {
                    'id': 'mini_pc_server',
                    'name': 'Mini PC Server',
                    'ip_address': '192.168.1.100',
                    'device_type': 'server',
                    'vendor': 'Generic',
                    'model': 'Mini PC',
                    'status': 'online',
                    'last_seen': datetime.now().isoformat(),
                    'is_home_device': True
                }
            ]
            
            devices.extend(home_devices)
            
            # Get actual devices from connection pool
            for device_id, connection in _self.connection_pool.connections.items():
                if connection.status.name == 'CONNECTED':
                    device_info = {
                        'id': device_id,
                        'name': getattr(connection, 'hostname', device_id),
                        'ip_address': connection.host,
                        'device_type': getattr(connection, 'device_type', DeviceType.GENERIC).value,
                        'vendor': 'Unknown',
                        'model': 'Unknown',
                        'status': 'connected',
                        'last_seen': connection.last_activity.isoformat() if connection.last_activity else None,
                        'is_home_device': False
                    }
                    devices.append(device_info)
            
            return devices
            
        except Exception as e:
            st.error(f"Failed to load devices: {str(e)}")
            return []

    @st.cache_data(ttl=30)
    def load_device_status(_self, device_id: str) -> Dict[str, Any]:
        """Load real-time status for a specific device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Device status dictionary
        """
        try:
            # Check if device is in connection pool
            if device_id in _self.connection_pool.connections:
                connection = _self.connection_pool.connections[device_id]
                return {
                    'status': connection.status.name,
                    'last_activity': connection.last_activity.isoformat() if connection.last_activity else None,
                    'connection_time': connection.connection_time.isoformat() if connection.connection_time else None,
                    'is_connected': connection.status.name == 'CONNECTED'
                }
            else:
                # For home devices, simulate status
                if device_id in ['xfinity_gateway', 'netgear_orbi', 'mini_pc_server']:
                    return {
                        'status': 'ONLINE',
                        'last_activity': datetime.now().isoformat(),
                        'connection_time': (datetime.now() - timedelta(hours=1)).isoformat(),
                        'is_connected': True
                    }
                else:
                    return {
                        'status': 'UNKNOWN',
                        'last_activity': None,
                        'connection_time': None,
                        'is_connected': False
                    }
                    
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'is_connected': False
            }

    @st.cache_data(ttl=60)
    def load_device_metrics(_self, device_id: str) -> Dict[str, Any]:
        """Load performance metrics for a specific device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Device metrics dictionary
        """
        try:
            # For home devices, provide sample metrics
            if device_id == 'xfinity_gateway':
                return {
                    'interface_metrics': [
                        {
                            'interface_name': 'Cable0/0',
                            'status': 'up',
                            'input_bytes': 1024000000,
                            'output_bytes': 512000000,
                            'utilization_in': 45.2,
                            'utilization_out': 23.1,
                            'bandwidth': 1000000000
                        }
                    ],
                    'system_metrics': {
                        'cpu_usage': 15.5,
                        'memory_usage': 68.2,
                        'temperature': 45.0,
                        'uptime': 86400 * 7  # 7 days
                    },
                    'docsis_metrics': {
                        'downstream_channels': 32,
                        'upstream_channels': 8,
                        'downstream_power': -5.2,
                        'upstream_power': 42.1,
                        'snr': 38.5
                    }
                }
            elif device_id == 'netgear_orbi':
                return {
                    'interface_metrics': [
                        {
                            'interface_name': 'WiFi-2.4GHz',
                            'status': 'up',
                            'input_bytes': 256000000,
                            'output_bytes': 512000000,
                            'utilization_in': 12.5,
                            'utilization_out': 25.3,
                            'bandwidth': 150000000
                        },
                        {
                            'interface_name': 'WiFi-5GHz',
                            'status': 'up',
                            'input_bytes': 1024000000,
                            'output_bytes': 2048000000,
                            'utilization_in': 35.7,
                            'utilization_out': 71.2,
                            'bandwidth': 1200000000
                        }
                    ],
                    'system_metrics': {
                        'cpu_usage': 8.3,
                        'memory_usage': 45.6,
                        'temperature': 38.2,
                        'uptime': 86400 * 5  # 5 days
                    },
                    'wifi_metrics': {
                        'connected_clients': 12,
                        'signal_strength_2g': -45,
                        'signal_strength_5g': -42,
                        'mesh_status': 'optimal'
                    }
                }
            else:
                # Try to get real metrics from NetArchon
                if device_id in _self.connection_pool.connections:
                    connection = _self.connection_pool.connections[device_id]
                    
                    interface_metrics = _self.monitoring_collector.collect_interface_metrics(connection)
                    system_metrics = _self.monitoring_collector.collect_system_metrics(connection)
                    
                    return {
                        'interface_metrics': [metric.__dict__ for metric in interface_metrics],
                        'system_metrics': system_metrics.__dict__
                    }
                else:
                    return {'error': 'Device not connected'}
                
        except Exception as e:
            return {'error': str(e)}

    @st.cache_data(ttl=3600)
    def load_device_configs(_self, device_id: str) -> Dict[str, Any]:
        """Load configuration information for a specific device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Device configuration dictionary
        """
        try:
            if device_id in _self.connection_pool.connections:
                connection = _self.connection_pool.connections[device_id]
                
                # Get latest backup information
                backup_dir = f"{_self.config_manager.backup_directory}/{device_id}"
                backups = []
                
                if os.path.exists(backup_dir):
                    import os
                    for filename in os.listdir(backup_dir):
                        if filename.endswith('.txt'):
                            filepath = os.path.join(backup_dir, filename)
                            stat = os.stat(filepath)
                            backups.append({
                                'filename': filename,
                                'path': filepath,
                                'size': stat.st_size,
                                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                            })
                
                return {
                    'device_id': device_id,
                    'backup_count': len(backups),
                    'backups': sorted(backups, key=lambda x: x['created'], reverse=True),
                    'last_backup': backups[0]['created'] if backups else None
                }
            else:
                return {'error': 'Device not connected'}
                
        except Exception as e:
            return {'error': str(e)}

    def connect_device(self, host: str, username: str, password: str, port: int = 22) -> Tuple[bool, str]:
        """Connect to a new network device.
        
        Args:
            host: Device IP address or hostname
            username: SSH username
            password: SSH password
            port: SSH port (default 22)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            credentials = AuthenticationCredentials(
                username=username,
                password=password,
                connection_type=ConnectionType.PASSWORD
            )
            
            connection = self.connection_pool.get_connection(
                host=host,
                port=port,
                credentials=credentials
            )
            
            if connection and connection.status.name == 'CONNECTED':
                # Detect device type
                device_info = self.device_detector.detect_device(connection)
                if device_info:
                    connection.device_type = device_info.device_type
                    connection.hostname = device_info.hostname
                
                return True, f"Successfully connected to {host}"
            else:
                return False, f"Failed to connect to {host}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def disconnect_device(self, device_id: str) -> Tuple[bool, str]:
        """Disconnect from a network device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Tuple of (success, message)
        """
        try:
            self.connection_pool.release_connection(device_id)
            return True, f"Disconnected from {device_id}"
        except Exception as e:
            return False, f"Disconnect error: {str(e)}"

    def backup_device_config(self, device_id: str, reason: str = "Manual backup") -> Tuple[bool, str]:
        """Create a configuration backup for a device.
        
        Args:
            device_id: Unique identifier for the device
            reason: Reason for the backup
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if device_id in self.connection_pool.connections:
                connection = self.connection_pool.connections[device_id]
                backup_path = self.config_manager.backup_config(connection, reason)
                
                if backup_path:
                    return True, f"Backup created: {backup_path}"
                else:
                    return False, "Backup failed"
            else:
                return False, "Device not connected"
                
        except Exception as e:
            return False, f"Backup error: {str(e)}"

    @st.cache_data(ttl=600)
    def get_system_info(_self) -> Dict[str, Any]:
        """Get NetArchon system information.
        
        Returns:
            System information dictionary
        """
        return {
            'version': '1.0.0',
            'uptime': time.time() - st.session_state.get('start_time', time.time()),
            'active_connections': len(_self.connection_pool.connections),
            'cache_status': 'active',
            'monitoring_enabled': True,
            'web_interface': 'streamlit'
        }


# Global data loader instance
@st.cache_resource
def get_data_loader():
    """Get cached NetArchon data loader instance."""
    return NetArchonDataLoader()