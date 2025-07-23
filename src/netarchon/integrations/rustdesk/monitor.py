"""
RustDesk Monitor

Comprehensive monitoring and analysis of RustDesk server and client activity.
Provides real-time session tracking, security monitoring, and performance analysis.
"""

import sqlite3
import json
import subprocess
import psutil
import time
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import re
from threading import Lock
import socket

from netarchon.utils.logger import get_logger
from netarchon.core.monitoring import MonitoringCollector

from .models import (
    RustDeskSession, RustDeskDevice, RustDeskConnection, RustDeskServerStatus,
    RustDeskServerComponent, RustDeskNetworkMetrics, RustDeskSecurityEvent,
    ConnectionType, SessionStatus, DeviceStatus, ServerComponentType
)
from .exceptions import (
    RustDeskMonitoringError, RustDeskDatabaseError, RustDeskServerError,
    RustDeskSecurityError
)


class RustDeskMonitor:
    """
    Comprehensive RustDesk monitoring system.
    
    Monitors server health, active sessions, security events, and performance metrics.
    Integrates with NetArchon's monitoring framework for unified visibility.
    """
    
    def __init__(self, 
                 server_data_dir: str = "/opt/rustdesk-server/data",
                 config_dir: str = "config"):
        """Initialize RustDesk monitor."""
        self.logger = get_logger("RustDeskMonitor")
        self.server_data_dir = Path(server_data_dir)
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Database paths
        self.db_path = self.server_data_dir / "db_v2.sqlite3"
        self.log_path = self.server_data_dir / "logs"
        
        # Monitoring state
        self._monitoring_lock = Lock()
        self._last_check = datetime.now()
        self._session_cache: Dict[str, RustDeskSession] = {}
        self._device_cache: Dict[str, RustDeskDevice] = {}
        
        # RustDesk server ports for monitoring
        self.server_ports = {
            'signal': 21116,      # hbbs signal server
            'relay': 21117,       # hbbr relay server
            'web': 21114,         # web interface
            'websocket': 21118,   # websocket
            'websocket_ssl': 21119 # websocket SSL
        }
        
        # Security monitoring patterns
        self.security_patterns = {
            'failed_auth': [
                r'authentication failed',
                r'invalid credentials',
                r'login denied'
            ],
            'unauthorized_access': [
                r'unauthorized connection attempt',
                r'access denied',
                r'permission denied'
            ],
            'suspicious_activity': [
                r'multiple failed attempts',
                r'unusual connection pattern',
                r'potential brute force'
            ]
        }
        
        # Initialize monitoring collector integration
        try:
            self.monitoring_collector = MonitoringCollector()
        except Exception as e:
            self.logger.warning(f"Could not initialize monitoring collector: {e}")
            self.monitoring_collector = None
    
    def get_server_status(self) -> RustDeskServerStatus:
        """Get comprehensive RustDesk server status."""
        try:
            components = []
            
            # Check Docker containers if using Docker deployment
            docker_components = self._check_docker_services()
            if docker_components:
                components.extend(docker_components)
            else:
                # Check system processes for binary deployment
                process_components = self._check_system_processes()
                components.extend(process_components)
            
            # Get database and log statistics
            db_size = self._get_database_size()
            log_size = self._get_log_size()
            
            # Count active connections and devices
            active_connections = len(self.get_active_connections())
            total_devices = len(self.get_all_devices())
            sessions_today = len(self.get_sessions_since(datetime.now().replace(hour=0, minute=0, second=0)))
            
            # Calculate server uptime
            uptime = self._calculate_server_uptime()
            
            return RustDeskServerStatus(
                components=components,
                total_devices=total_devices,
                active_connections=active_connections,
                total_sessions_today=sessions_today,
                server_uptime=uptime,
                database_size=db_size,
                log_size=log_size,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get server status: {e}")
            raise RustDeskMonitoringError("server_status", str(e))
    
    def _check_docker_services(self) -> List[RustDeskServerComponent]:
        """Check Docker-based RustDesk services."""
        components = []
        
        try:
            # Check if Docker Compose is available
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd="/opt/rustdesk-server",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                services = json.loads(result.stdout)
                
                for service in services:
                    service_name = service.get('Service', '')
                    state = service.get('State', 'unknown')
                    
                    if service_name == 'hbbs':
                        component_type = ServerComponentType.SIGNAL_SERVER
                        port = self.server_ports['signal']
                    elif service_name == 'hbbr':
                        component_type = ServerComponentType.RELAY_SERVER
                        port = self.server_ports['relay']
                    else:
                        continue
                    
                    # Get container stats
                    container_name = service.get('Name', '')
                    cpu_usage, memory_usage = self._get_container_stats(container_name)
                    
                    components.append(RustDeskServerComponent(
                        name=service_name,
                        component_type=component_type,
                        status="running" if state == "running" else "stopped",
                        port=port,
                        cpu_usage=cpu_usage,
                        memory_usage=memory_usage,
                        start_time=self._parse_container_start_time(service.get('CreatedAt', ''))
                    ))
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError) as e:
            self.logger.debug(f"Docker services check failed: {e}")
        
        return components
    
    def _check_system_processes(self) -> List[RustDeskServerComponent]:
        """Check system processes for RustDesk services."""
        components = []
        
        try:
            # Check for hbbs process
            hbbs_processes = []
            hbbr_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] == 'hbbs' or 'hbbs' in ' '.join(proc_info['cmdline'] or []):
                        hbbs_processes.append(proc_info)
                    elif proc_info['name'] == 'hbbr' or 'hbbr' in ' '.join(proc_info['cmdline'] or []):
                        hbbr_processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Create components for found processes
            if hbbs_processes:
                proc = hbbs_processes[0]  # Take first process
                components.append(RustDeskServerComponent(
                    name="hbbs",
                    component_type=ServerComponentType.SIGNAL_SERVER,
                    status="running",
                    pid=proc['pid'],
                    port=self.server_ports['signal'],
                    start_time=datetime.fromtimestamp(proc['create_time']),
                    cpu_usage=proc['cpu_percent'],
                    memory_usage=proc['memory_percent']
                ))
            
            if hbbr_processes:
                proc = hbbr_processes[0]  # Take first process
                components.append(RustDeskServerComponent(
                    name="hbbr",
                    component_type=ServerComponentType.RELAY_SERVER,
                    status="running",
                    pid=proc['pid'],
                    port=self.server_ports['relay'],
                    start_time=datetime.fromtimestamp(proc['create_time']),
                    cpu_usage=proc['cpu_percent'],
                    memory_usage=proc['memory_percent']
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to check system processes: {e}")
        
        return components
    
    def _get_container_stats(self, container_name: str) -> Tuple[Optional[float], Optional[float]]:
        """Get CPU and memory usage for Docker container."""
        try:
            result = subprocess.run(
                ["docker", "stats", container_name, "--no-stream", "--format", "table {{.CPUPerc}}\t{{.MemPerc}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    stats = lines[1].split('\t')
                    if len(stats) >= 2:
                        cpu_str = stats[0].replace('%', '')
                        mem_str = stats[1].replace('%', '')
                        
                        return float(cpu_str), float(mem_str)
                        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
            self.logger.debug(f"Failed to get container stats for {container_name}: {e}")
        
        return None, None
    
    def _parse_container_start_time(self, created_at: str) -> Optional[datetime]:
        """Parse container creation time."""
        try:
            # Docker timestamp format: "2025-01-15 10:30:00 +0000 UTC"
            if created_at:
                # Remove timezone info for simple parsing
                timestamp_str = created_at.split(' +')[0]
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        
        return None
    
    def _get_database_size(self) -> Optional[int]:
        """Get RustDesk database file size."""
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size
        except Exception as e:
            self.logger.debug(f"Failed to get database size: {e}")
        
        return None
    
    def _get_log_size(self) -> Optional[int]:
        """Get total size of RustDesk log files."""
        try:
            if self.log_path.exists():
                total_size = 0
                for log_file in self.log_path.rglob("*.log"):
                    total_size += log_file.stat().st_size
                return total_size
        except Exception as e:
            self.logger.debug(f"Failed to get log size: {e}")
        
        return None
    
    def _calculate_server_uptime(self) -> Optional[int]:
        """Calculate server uptime in seconds."""
        try:
            # Try to get uptime from the oldest running component
            server_status = self._check_system_processes()
            if not server_status:
                server_status = self._check_docker_services()
            
            if server_status:
                oldest_start = min(
                    comp.start_time for comp in server_status 
                    if comp.start_time and comp.status == "running"
                )
                
                if oldest_start:
                    return int((datetime.now() - oldest_start).total_seconds())
                    
        except Exception as e:
            self.logger.debug(f"Failed to calculate uptime: {e}")
        
        return None
    
    def get_active_connections(self) -> List[RustDeskConnection]:
        """Get all active RustDesk connections."""
        try:
            with self._monitoring_lock:
                if not self.db_path.exists():
                    self.logger.warning("RustDesk database not found")
                    return []
                
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row  # Enable column access by name
                
                try:
                    # Query active connections from database
                    cursor = conn.execute("""
                        SELECT * FROM connections 
                        WHERE status = 'active' OR status = 'connected'
                        ORDER BY start_time DESC
                    """)
                    
                    connections = []
                    for row in cursor.fetchall():
                        connection = RustDeskConnection(
                            connection_id=row['id'],
                            from_device_id=row['from_id'],
                            to_device_id=row['to_id'],
                            from_device_name=row.get('from_name', 'Unknown'),
                            to_device_name=row.get('to_name', 'Unknown'),
                            connection_type=ConnectionType(row.get('type', 'unknown')),
                            start_time=datetime.fromisoformat(row['start_time']),
                            end_time=datetime.fromisoformat(row['end_time']) if row.get('end_time') else None,
                            status=SessionStatus(row.get('status', 'pending')),
                            remote_ip=row.get('remote_ip'),
                            local_ip=row.get('local_ip'),
                            relay_server=row.get('relay_server')
                        )
                        connections.append(connection)
                    
                    return connections
                    
                finally:
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Failed to get active connections: {e}")
            raise RustDeskDatabaseError("get_active_connections", str(e))
    
    def get_all_devices(self) -> List[RustDeskDevice]:
        """Get all registered RustDesk devices."""
        try:
            with self._monitoring_lock:
                if not self.db_path.exists():
                    self.logger.warning("RustDesk database not found")
                    return []
                
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                
                try:
                    cursor = conn.execute("""
                        SELECT * FROM devices 
                        ORDER BY last_seen DESC
                    """)
                    
                    devices = []
                    for row in cursor.fetchall():
                        device = RustDeskDevice.from_db_row(dict(row))
                        devices.append(device)
                        
                        # Cache device
                        self._device_cache[device.device_id] = device
                    
                    return devices
                    
                finally:
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Failed to get devices: {e}")
            raise RustDeskDatabaseError("get_all_devices", str(e))
    
    def get_sessions_since(self, since_time: datetime) -> List[RustDeskSession]:
        """Get all sessions since specified time."""
        try:
            with self._monitoring_lock:
                if not self.db_path.exists():
                    return []
                
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                
                try:
                    cursor = conn.execute("""
                        SELECT * FROM sessions 
                        WHERE start_time >= ? 
                        ORDER BY start_time DESC
                    """, (since_time.isoformat(),))
                    
                    sessions = []
                    for row in cursor.fetchall():
                        session = RustDeskSession(
                            session_id=row['id'],
                            user_id=row.get('user_id'),
                            device_id=row['device_id'],
                            device_name=row.get('device_name', 'Unknown'),
                            start_time=datetime.fromisoformat(row['start_time']),
                            end_time=datetime.fromisoformat(row['end_time']) if row.get('end_time') else None,
                            total_duration=row.get('duration'),
                            total_bytes=row.get('bytes_transferred'),
                            session_type=row.get('type', 'remote_desktop')
                        )
                        
                        # Get connections for this session
                        conn_cursor = conn.execute("""
                            SELECT * FROM connections WHERE session_id = ?
                        """, (session.session_id,))
                        
                        for conn_row in conn_cursor.fetchall():
                            connection = RustDeskConnection.from_log_entry(dict(conn_row))
                            session.add_connection(connection)
                        
                        sessions.append(session)
                        
                        # Cache session
                        self._session_cache[session.session_id] = session
                    
                    return sessions
                    
                finally:
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Failed to get sessions: {e}")
            raise RustDeskDatabaseError("get_sessions_since", str(e))
    
    def get_network_metrics(self, time_range_minutes: int = 60) -> List[RustDeskNetworkMetrics]:
        """Get network metrics for specified time range."""
        try:
            metrics = []
            
            # Get connections from the last hour
            since_time = datetime.now() - timedelta(minutes=time_range_minutes)
            recent_connections = []
            
            # Query database for connection history
            if self.db_path.exists():
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                
                try:
                    cursor = conn.execute("""
                        SELECT * FROM connections 
                        WHERE start_time >= ? 
                        ORDER BY start_time ASC
                    """, (since_time.isoformat(),))
                    
                    for row in cursor.fetchall():
                        recent_connections.append(dict(row))
                        
                finally:
                    conn.close()
            
            # Generate metrics for each 5-minute interval
            interval_minutes = 5
            intervals = time_range_minutes // interval_minutes
            
            for i in range(intervals):
                interval_start = since_time + timedelta(minutes=i * interval_minutes)
                interval_end = interval_start + timedelta(minutes=interval_minutes)
                
                # Filter connections for this interval
                interval_connections = [
                    conn for conn in recent_connections
                    if interval_start <= datetime.fromisoformat(conn['start_time']) < interval_end
                ]
                
                # Calculate metrics
                total_connections = len(interval_connections)
                active_connections = len([
                    conn for conn in interval_connections 
                    if conn.get('status') in ['active', 'connected']
                ])
                
                relay_connections = len([
                    conn for conn in interval_connections 
                    if conn.get('type') == 'relay'
                ])
                
                direct_connections = total_connections - relay_connections
                
                relay_percent = (relay_connections / total_connections * 100) if total_connections > 0 else 0
                direct_percent = (direct_connections / total_connections * 100) if total_connections > 0 else 0
                
                # Estimate bandwidth (simplified calculation)
                bytes_per_second = sum(conn.get('bytes_transferred', 0) for conn in interval_connections) / (interval_minutes * 60)
                
                metric = RustDeskNetworkMetrics(
                    timestamp=interval_start,
                    total_connections=total_connections,
                    active_connections=active_connections,
                    bytes_per_second=bytes_per_second,
                    packets_per_second=bytes_per_second / 1024,  # Rough estimate
                    relay_usage_percent=relay_percent,
                    direct_connection_percent=direct_percent
                )
                
                metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get network metrics: {e}")
            raise RustDeskMonitoringError("network_metrics", str(e))
    
    def scan_security_events(self, hours_back: int = 24) -> List[RustDeskSecurityEvent]:
        """Scan for security events in RustDesk logs."""
        try:
            security_events = []
            
            if not self.log_path.exists():
                return security_events
            
            # Scan log files for security patterns
            since_time = datetime.now() - timedelta(hours=hours_back)
            
            for log_file in self.log_path.rglob("*.log"):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f):
                            # Try to extract timestamp from log line
                            timestamp = self._extract_log_timestamp(line)
                            if timestamp and timestamp < since_time:
                                continue
                            
                            # Check for security patterns
                            for event_type, patterns in self.security_patterns.items():
                                for pattern in patterns:
                                    if re.search(pattern, line, re.IGNORECASE):
                                        event = RustDeskSecurityEvent(
                                            event_id=f"{log_file.name}_{line_num}_{int(time.time())}",
                                            event_type=event_type,
                                            timestamp=timestamp or datetime.now(),
                                            description=line.strip(),
                                            severity=self._determine_severity(event_type),
                                            details={
                                                'log_file': str(log_file),
                                                'line_number': line_num,
                                                'pattern_matched': pattern
                                            }
                                        )
                                        
                                        # Extract additional details
                                        device_id = self._extract_device_id(line)
                                        if device_id:
                                            event.device_id = device_id
                                            event.device_name = self._get_device_name(device_id)
                                        
                                        remote_ip = self._extract_ip_address(line)
                                        if remote_ip:
                                            event.remote_ip = remote_ip
                                        
                                        security_events.append(event)
                                        break  # Only match first pattern per line
                
                except Exception as e:
                    self.logger.debug(f"Failed to scan log file {log_file}: {e}")
                    continue
            
            return security_events
            
        except Exception as e:
            self.logger.error(f"Failed to scan security events: {e}")
            raise RustDeskSecurityError("security_scan", str(e))
    
    def _extract_log_timestamp(self, log_line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        # Common timestamp formats in RustDesk logs
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})',
            r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, log_line)
            if match:
                timestamp_str = match.group(1)
                try:
                    if 'T' in timestamp_str:
                        return datetime.fromisoformat(timestamp_str)
                    else:
                        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
        
        return None
    
    def _determine_severity(self, event_type: str) -> str:
        """Determine severity level for security event type."""
        severity_map = {
            'failed_auth': 'medium',
            'unauthorized_access': 'high',
            'suspicious_activity': 'high'
        }
        
        return severity_map.get(event_type, 'medium')
    
    def _extract_device_id(self, log_line: str) -> Optional[str]:
        """Extract device ID from log line."""
        # Look for device ID patterns
        device_patterns = [
            r'device_id[:\s]+([a-zA-Z0-9_-]+)',
            r'device[:\s]+([a-zA-Z0-9_-]+)',
            r'client[:\s]+([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in device_patterns:
            match = re.search(pattern, log_line, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_ip_address(self, log_line: str) -> Optional[str]:
        """Extract IP address from log line."""
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        match = re.search(ip_pattern, log_line)
        return match.group(0) if match else None
    
    def _get_device_name(self, device_id: str) -> Optional[str]:
        """Get device name from cache or database."""
        if device_id in self._device_cache:
            return self._device_cache[device_id].device_name
        
        try:
            if self.db_path.exists():
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.execute("SELECT name FROM devices WHERE id = ?", (device_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return row[0]
        except Exception:
            pass
        
        return None
    
    def test_server_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to RustDesk server ports."""
        results = {}
        
        for service_name, port in self.server_ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                results[service_name] = {
                    'port': port,
                    'status': 'open' if result == 0 else 'closed',
                    'accessible': result == 0
                }
                
            except Exception as e:
                results[service_name] = {
                    'port': port,
                    'status': 'error',
                    'accessible': False,
                    'error': str(e)
                }
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for RustDesk server."""
        try:
            server_status = self.get_server_status()
            network_metrics = self.get_network_metrics(60)  # Last hour
            
            # Calculate average metrics
            avg_connections = sum(m.active_connections for m in network_metrics) / len(network_metrics) if network_metrics else 0
            avg_bandwidth = sum(m.bytes_per_second for m in network_metrics) / len(network_metrics) if network_metrics else 0
            avg_relay_usage = sum(m.relay_usage_percent for m in network_metrics) / len(network_metrics) if network_metrics else 0
            
            return {
                'server_health': 'healthy' if server_status.is_healthy else 'unhealthy',
                'uptime_hours': server_status.server_uptime // 3600 if server_status.server_uptime else 0,
                'total_devices': server_status.total_devices,
                'active_connections': server_status.active_connections,
                'sessions_today': server_status.total_sessions_today,
                'avg_connections_per_hour': avg_connections,
                'avg_bandwidth_mbps': avg_bandwidth / 1024 / 1024,  # Convert to MB/s
                'relay_usage_percent': avg_relay_usage,
                'database_size_mb': server_status.database_size / 1024 / 1024 if server_status.database_size else 0,
                'log_size_mb': server_status.log_size / 1024 / 1024 if server_status.log_size else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance summary: {e}")
            return {
                'server_health': 'error',
                'error': str(e)
            }
    
    def cleanup(self):
        """Clean up monitoring resources."""
        with self._monitoring_lock:
            self._session_cache.clear()
            self._device_cache.clear()
        
        self.logger.info("RustDesk monitor cleaned up")