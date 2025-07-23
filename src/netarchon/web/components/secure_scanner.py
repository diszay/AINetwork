"""
NetArchon Secure Network Scanner

Safe and controlled network scanning limited to home network devices only.
Focuses on security assessment and vulnerability detection for home networks.
"""

import streamlit as st
import subprocess
import socket
import threading
import time
import ipaddress
import re
import os
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class VulnerabilityLevel(Enum):
    """Vulnerability severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ServiceType(Enum):
    """Network service types."""
    SSH = "ssh"
    HTTP = "http"
    HTTPS = "https"
    TELNET = "telnet"
    FTP = "ftp"
    SNMP = "snmp"
    DNS = "dns"
    SMB = "smb"
    UNKNOWN = "unknown"

@dataclass
class NetworkService:
    """Represents a network service found on a device."""
    port: int
    protocol: str
    service: ServiceType
    version: str = ""
    banner: str = ""
    is_secure: bool = True
    vulnerabilities: List[str] = None
    
    def __post_init__(self):
        if self.vulnerabilities is None:
            self.vulnerabilities = []

@dataclass
class SecurityAssessment:
    """Security assessment results for a device."""
    device_ip: str
    hostname: str
    mac_address: str
    os_fingerprint: str
    open_ports: List[int]
    services: List[NetworkService]
    vulnerabilities: List[Dict]
    security_score: int  # 0-100
    recommendations: List[str]
    scan_timestamp: datetime

class SecureNetworkScanner:
    """Secure network scanner for home networks only."""
    
    def __init__(self):
        """Initialize secure network scanner."""
        self.logger = logging.getLogger("SecureNetworkScanner")
        
        # Home network ranges (RFC 1918 private addresses)
        self.home_network_ranges = [
            ipaddress.IPv4Network('192.168.0.0/16'),
            ipaddress.IPv4Network('10.0.0.0/8'), 
            ipaddress.IPv4Network('172.16.0.0/12')
        ]
        
        # Common home network services to check
        self.home_service_ports = {
            22: ServiceType.SSH,
            23: ServiceType.TELNET,
            53: ServiceType.DNS,
            80: ServiceType.HTTP,
            135: ServiceType.UNKNOWN,  # RPC
            139: ServiceType.SMB,
            161: ServiceType.SNMP,
            443: ServiceType.HTTPS,
            445: ServiceType.SMB,
            993: ServiceType.UNKNOWN,  # IMAPS
            995: ServiceType.UNKNOWN,  # POP3S
            8080: ServiceType.HTTP,
            8443: ServiceType.HTTPS
        }
        
        # Known vulnerable service patterns
        self.vulnerability_patterns = {
            'telnet': {
                'level': VulnerabilityLevel.HIGH,
                'description': 'Unencrypted remote access protocol',
                'recommendation': 'Disable Telnet and use SSH instead'
            },
            'http': {
                'level': VulnerabilityLevel.MEDIUM,
                'description': 'Unencrypted web interface',
                'recommendation': 'Use HTTPS instead of HTTP'
            },
            'snmp_v1': {
                'level': VulnerabilityLevel.HIGH,
                'description': 'SNMPv1 uses weak community strings',
                'recommendation': 'Upgrade to SNMPv3 with encryption'
            },
            'smb_v1': {
                'level': VulnerabilityLevel.CRITICAL,
                'description': 'SMBv1 has known security vulnerabilities',
                'recommendation': 'Disable SMBv1 and use SMBv3'
            }
        }
    
    def is_home_network_address(self, ip_address: str) -> bool:
        """Check if IP address is within home network ranges."""
        try:
            ip = ipaddress.IPv4Address(ip_address)
            return any(ip in network for network in self.home_network_ranges)
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    def get_local_network_range(self) -> Optional[ipaddress.IPv4Network]:
        """Get the local network range for the current interface."""
        try:
            # Get default route
            result = subprocess.run(['route', '-n', 'get', 'default'], 
                                  capture_output=True, text=True, timeout=5)
            
            gateway_ip = None
            for line in result.stdout.split('\n'):
                if 'gateway:' in line:
                    gateway_ip = line.split(':')[1].strip()
                    break
            
            if gateway_ip and self.is_home_network_address(gateway_ip):
                # Determine network range based on gateway
                if gateway_ip.startswith('192.168.'):
                    return ipaddress.IPv4Network(f"{gateway_ip.rsplit('.', 1)[0]}.0/24", strict=False)
                elif gateway_ip.startswith('10.'):
                    return ipaddress.IPv4Network(f"{gateway_ip.split('.')[0]}.0.0.0/8", strict=False)
                elif gateway_ip.startswith('172.'):
                    return ipaddress.IPv4Network(f"{'.'.join(gateway_ip.split('.')[:2])}.0.0/12", strict=False)
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Default to common home network
        return ipaddress.IPv4Network('192.168.1.0/24')
    
    def discover_home_devices(self, network_range: Optional[ipaddress.IPv4Network] = None) -> List[str]:
        """Discover devices on home network using safe methods."""
        if network_range is None:
            network_range = self.get_local_network_range()
        
        if not network_range:
            return []
        
        active_ips = []
        
        try:
            # Use ARP table first (fastest and safest)
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=30)
            
            for line in result.stdout.split('\n'):
                # Parse ARP entries
                match = re.search(r'\(([0-9.]+)\)', line)
                if match:
                    ip = match.group(1)
                    if ipaddress.IPv4Address(ip) in network_range:
                        active_ips.append(ip)
            
            # If ARP table is empty, do limited ping sweep (home network only)
            if not active_ips and network_range.num_addresses <= 256:  # Only small networks
                active_ips = self._safe_ping_sweep(network_range)
                
        except Exception as e:
            self.logger.error(f"Device discovery failed: {e}")
        
        return sorted(set(active_ips))
    
    def _safe_ping_sweep(self, network_range: ipaddress.IPv4Network) -> List[str]:
        """Perform safe ping sweep on small home networks only."""
        active_ips = []
        
        # Only scan small networks to avoid being intrusive
        if network_range.num_addresses > 256:
            return active_ips
        
        def ping_host(ip_str: str) -> Optional[str]:
            try:
                # Single ping with short timeout
                result = subprocess.run(['ping', '-c', '1', '-W', '1000', ip_str],
                                      capture_output=True, timeout=2)
                if result.returncode == 0:
                    return ip_str
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
            return None
        
        # Use limited concurrency to be network-friendly
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Skip network and broadcast addresses
            for ip in list(network_range.hosts())[:50]:  # Limit to first 50 IPs
                futures.append(executor.submit(ping_host, str(ip)))
            
            for future in as_completed(futures, timeout=30):
                result = future.result()
                if result:
                    active_ips.append(result)
        
        return active_ips
    
    def scan_device_ports(self, ip_address: str, port_list: Optional[List[int]] = None) -> List[int]:
        """Scan common ports on a home network device."""
        if not self.is_home_network_address(ip_address):
            self.logger.warning(f"Skipping port scan for non-home network IP: {ip_address}")
            return []
        
        if port_list is None:
            port_list = list(self.home_service_ports.keys())
        
        open_ports = []
        
        def scan_port(port: int) -> Optional[int]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)  # Short timeout
                result = sock.connect_ex((ip_address, port))
                sock.close()
                
                if result == 0:
                    return port
            except Exception:
                pass
            return None
        
        # Scan ports with limited concurrency
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(scan_port, port) for port in port_list]
            
            for future in as_completed(futures, timeout=30):
                result = future.result()
                if result:
                    open_ports.append(result)
        
        return sorted(open_ports)
    
    def get_service_banner(self, ip_address: str, port: int) -> str:
        """Get service banner for vulnerability assessment."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            sock.settimeout(3)
            
            if sock.connect_ex((ip_address, port)) == 0:
                # Try to get banner
                if port in [21, 22, 23, 25, 53, 80, 110, 143, 993, 995]:
                    banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                    sock.close()
                    return banner[:200]  # Limit banner length
            
            sock.close()
        except Exception:
            pass
        
        return ""
    
    def assess_service_security(self, service: NetworkService) -> List[Dict]:
        """Assess security of a network service."""
        vulnerabilities = []
        
        # Check for known insecure services
        if service.service == ServiceType.TELNET:
            vulnerabilities.append({
                'id': 'insecure_telnet',
                'level': VulnerabilityLevel.HIGH,
                'description': 'Telnet transmits data in plaintext',
                'recommendation': 'Disable Telnet and use SSH instead',
                'port': service.port
            })
        
        elif service.service == ServiceType.HTTP and service.port == 80:
            vulnerabilities.append({
                'id': 'insecure_http',
                'level': VulnerabilityLevel.MEDIUM,
                'description': 'HTTP web interface is unencrypted',
                'recommendation': 'Use HTTPS (port 443) instead',
                'port': service.port
            })
        
        elif service.service == ServiceType.SNMP:
            # Check for SNMPv1/v2c community strings
            if 'public' in service.banner.lower() or 'private' in service.banner.lower():
                vulnerabilities.append({
                    'id': 'weak_snmp_community',
                    'level': VulnerabilityLevel.HIGH,
                    'description': 'SNMP using default community strings',
                    'recommendation': 'Change default community strings or upgrade to SNMPv3',
                    'port': service.port
                })
        
        elif service.service == ServiceType.SMB:
            # Check for SMBv1
            if 'smb' in service.banner.lower() and ('1.0' in service.banner or 'cifs' in service.banner):
                vulnerabilities.append({
                    'id': 'smbv1_enabled',
                    'level': VulnerabilityLevel.CRITICAL,
                    'description': 'SMBv1 protocol has known vulnerabilities',
                    'recommendation': 'Disable SMBv1 and use SMBv2/v3',
                    'port': service.port
                })
        
        # Check for default credentials (common on home devices)
        if service.port in [22, 23, 80, 443, 8080, 8443]:
            vulnerabilities.append({
                'id': 'potential_default_creds',
                'level': VulnerabilityLevel.MEDIUM,
                'description': 'Service may be using default credentials',
                'recommendation': 'Verify that default passwords have been changed',
                'port': service.port
            })
        
        return vulnerabilities
    
    def perform_security_assessment(self, ip_address: str) -> SecurityAssessment:
        """Perform comprehensive security assessment of a home network device."""
        if not self.is_home_network_address(ip_address):
            raise ValueError(f"IP address {ip_address} is not in home network range")
        
        # Get basic device info
        hostname = self._get_hostname(ip_address)
        mac_address = self._get_mac_address(ip_address)
        
        # Scan ports
        open_ports = self.scan_device_ports(ip_address)
        
        # Identify services
        services = []
        all_vulnerabilities = []
        
        for port in open_ports:
            service_type = self.home_service_ports.get(port, ServiceType.UNKNOWN)
            banner = self.get_service_banner(ip_address, port)
            
            service = NetworkService(
                port=port,
                protocol='tcp',
                service=service_type,
                banner=banner
            )
            
            # Assess service security
            service_vulns = self.assess_service_security(service)
            all_vulnerabilities.extend(service_vulns)
            service.vulnerabilities = [v['id'] for v in service_vulns]
            
            services.append(service)
        
        # Calculate security score
        security_score = self._calculate_security_score(services, all_vulnerabilities)
        
        # Generate recommendations
        recommendations = self._generate_security_recommendations(services, all_vulnerabilities)
        
        return SecurityAssessment(
            device_ip=ip_address,
            hostname=hostname,
            mac_address=mac_address,
            os_fingerprint="",  # Not implemented for safety
            open_ports=open_ports,
            services=services,
            vulnerabilities=all_vulnerabilities,
            security_score=security_score,
            recommendations=recommendations,
            scan_timestamp=datetime.now()
        )
    
    def _get_hostname(self, ip_address: str) -> str:
        """Get hostname for IP address."""
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
            return hostname
        except socket.herror:
            return f"device-{ip_address.split('.')[-1]}"
    
    def _get_mac_address(self, ip_address: str) -> str:
        """Get MAC address from ARP table."""
        try:
            result = subprocess.run(['arp', '-n', ip_address], 
                                  capture_output=True, text=True, timeout=5)
            
            for line in result.stdout.split('\n'):
                if ip_address in line:
                    match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', line)
                    if match:
                        return match.group(0).lower()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        
        return "unknown"
    
    def _calculate_security_score(self, services: List[NetworkService], vulnerabilities: List[Dict]) -> int:
        """Calculate security score (0-100) based on findings."""
        base_score = 80  # Start with good score
        
        # Deduct points for vulnerabilities
        for vuln in vulnerabilities:
            level = vuln['level']
            if level == VulnerabilityLevel.CRITICAL:
                base_score -= 30
            elif level == VulnerabilityLevel.HIGH:
                base_score -= 20
            elif level == VulnerabilityLevel.MEDIUM:
                base_score -= 10
            elif level == VulnerabilityLevel.LOW:
                base_score -= 5
        
        # Deduct points for insecure services
        insecure_services = [s for s in services if s.service in [ServiceType.TELNET, ServiceType.HTTP]]
        base_score -= len(insecure_services) * 15
        
        # Bonus for secure services
        secure_services = [s for s in services if s.service in [ServiceType.SSH, ServiceType.HTTPS]]
        base_score += len(secure_services) * 5
        
        return max(0, min(100, base_score))
    
    def _generate_security_recommendations(self, services: List[NetworkService], 
                                         vulnerabilities: List[Dict]) -> List[str]:
        """Generate security recommendations based on assessment."""
        recommendations = []
        
        # Service-specific recommendations
        telnet_services = [s for s in services if s.service == ServiceType.TELNET]
        if telnet_services:
            recommendations.append("🔒 Disable Telnet and use SSH for secure remote access")
        
        http_services = [s for s in services if s.service == ServiceType.HTTP and s.port == 80]
        if http_services:
            recommendations.append("🔐 Enable HTTPS for web interfaces instead of HTTP")
        
        smb_services = [s for s in services if s.service == ServiceType.SMB]
        if smb_services:
            recommendations.append("🛡️ Ensure SMBv1 is disabled and use SMBv3")
        
        snmp_services = [s for s in services if s.service == ServiceType.SNMP]
        if snmp_services:
            recommendations.append("🔑 Change default SNMP community strings or upgrade to SNMPv3")
        
        # General recommendations
        if len(services) > 5:
            recommendations.append("⚡ Close unnecessary network services to reduce attack surface")
        
        recommendations.extend([
            "🔄 Regularly update device firmware",
            "🔐 Change all default passwords",
            "🧱 Enable device firewall if available",
            "📊 Monitor device logs for suspicious activity"
        ])
        
        return recommendations


def render_secure_network_scanner():
    """Render secure network scanner interface."""
    st.subheader("🔍 Secure Network Scanner")
    
    st.info("""
    **🛡️ Security Notice**: This scanner only operates on home network devices (RFC 1918 private addresses) 
    and uses safe, non-intrusive scanning methods to protect your network.
    """)
    
    scanner = SecureNetworkScanner()
    
    # Scanner controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Discover Devices", type="primary"):
            with st.spinner("Discovering home network devices..."):
                network_range = scanner.get_local_network_range()
                st.session_state.discovered_devices = scanner.discover_home_devices(network_range)
                st.session_state.network_range = str(network_range)
    
    with col2:
        if st.button("🔒 Security Scan") and 'discovered_devices' in st.session_state:
            with st.spinner("Performing security assessment..."):
                assessments = []
                
                for ip in st.session_state.discovered_devices[:5]:  # Limit to 5 devices
                    try:
                        assessment = scanner.perform_security_assessment(ip)
                        assessments.append(assessment)
                    except Exception as e:
                        st.error(f"Assessment failed for {ip}: {e}")
                
                st.session_state.security_assessments = assessments
    
    with col3:
        if st.button("📊 Generate Report") and 'security_assessments' in st.session_state:
            st.session_state.show_security_report = True
    
    # Display network range
    if 'network_range' in st.session_state:
        st.success(f"📡 Scanning network: {st.session_state.network_range}")
    
    # Display discovered devices
    if 'discovered_devices' in st.session_state:
        devices = st.session_state.discovered_devices
        
        st.markdown(f"### 📱 Discovered Devices ({len(devices)})")
        
        # Create columns for device display
        cols = st.columns(min(4, len(devices)))
        
        for i, device_ip in enumerate(devices):
            with cols[i % 4]:
                hostname = scanner._get_hostname(device_ip)  
                mac = scanner._get_mac_address(device_ip)
                
                st.markdown(f"""
                <div style="
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    margin: 5px 0;
                    background: white;
                    text-align: center;
                ">
                    <strong>{hostname}</strong><br>
                    <small>{device_ip}</small><br>
                    <small style="color: #666;">{mac}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # Display security assessments
    if 'security_assessments' in st.session_state:
        assessments = st.session_state.security_assessments
        
        st.markdown("### 🔒 Security Assessment Results")
        
        for assessment in assessments:
            with st.expander(f"🖥️ {assessment.hostname} ({assessment.device_ip}) - Score: {assessment.security_score}/100"):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Device Information:**")
                    st.write(f"- **IP Address**: {assessment.device_ip}")
                    st.write(f"- **Hostname**: {assessment.hostname}")
                    st.write(f"- **MAC Address**: {assessment.mac_address}")
                    st.write(f"- **Open Ports**: {', '.join(map(str, assessment.open_ports)) if assessment.open_ports else 'None'}")
                
                with col2:
                    # Security score with color coding
                    score_color = "green" if assessment.security_score >= 80 else "orange" if assessment.security_score >= 60 else "red"
                    
                    st.markdown(f"""
                    **Security Score**: <span style="color: {score_color}; font-size: 1.2em; font-weight: bold;">
                    {assessment.security_score}/100
                    </span>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"- **Services Found**: {len(assessment.services)}")
                    st.write(f"- **Vulnerabilities**: {len(assessment.vulnerabilities)}")
                    st.write(f"- **Scan Time**: {assessment.scan_timestamp.strftime('%H:%M:%S')}")
                
                # Services
                if assessment.services:
                    st.write("**Network Services:**")
                    for service in assessment.services:
                        vuln_indicator = "⚠️" if service.vulnerabilities else "✅"
                        st.write(f"- {vuln_indicator} Port {service.port}: {service.service.value}")
                
                # Vulnerabilities
                if assessment.vulnerabilities:
                    st.write("**Security Issues:**")
                    for vuln in assessment.vulnerabilities:
                        level_color = {
                            VulnerabilityLevel.CRITICAL: "red",
                            VulnerabilityLevel.HIGH: "orange",
                            VulnerabilityLevel.MEDIUM: "gold",
                            VulnerabilityLevel.LOW: "blue"
                        }.get(vuln['level'], "gray")
                        
                        st.markdown(f"""
                        <div style="border-left: 4px solid {level_color}; padding: 8px; margin: 5px 0; background: rgba(255,255,255,0.1);">
                            <strong>{vuln['level'].value.upper()}</strong>: {vuln['description']}<br>
                            <small>💡 {vuln['recommendation']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Recommendations
                if assessment.recommendations:
                    st.write("**Security Recommendations:**")
                    for rec in assessment.recommendations:
                        st.write(f"- {rec}")
    
    # Security report
    if st.session_state.get('show_security_report') and 'security_assessments' in st.session_state:
        render_security_report(st.session_state.security_assessments)


def render_security_report(assessments: List[SecurityAssessment]):
    """Render comprehensive security report."""
    st.markdown("### 📊 Network Security Report")
    
    if not assessments:
        st.warning("No security assessments available")
        return
    
    # Summary metrics
    total_devices = len(assessments)
    avg_score = sum(a.security_score for a in assessments) / total_devices
    total_vulns = sum(len(a.vulnerabilities) for a in assessments)
    critical_vulns = sum(1 for a in assessments for v in a.vulnerabilities if v['level'] == VulnerabilityLevel.CRITICAL)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Devices Scanned", total_devices)
    
    with col2:
        score_delta = "Good" if avg_score >= 80 else "Fair" if avg_score >= 60 else "Poor"
        st.metric("Average Security Score", f"{avg_score:.1f}/100", delta=score_delta)
    
    with col3:
        st.metric("Total Vulnerabilities", total_vulns)
    
    with col4:
        st.metric("Critical Issues", critical_vulns, delta="Immediate attention required" if critical_vulns > 0 else "None")
    
    # Vulnerability breakdown
    vuln_levels = {}
    for assessment in assessments:
        for vuln in assessment.vulnerabilities:
            level = vuln['level'].value
            vuln_levels[level] = vuln_levels.get(level, 0) + 1
    
    if vuln_levels:
        st.markdown("### 🚨 Vulnerability Breakdown")
        
        # Create pie chart data
        import plotly.express as px
        import pandas as pd
        
        df = pd.DataFrame(list(vuln_levels.items()), columns=['Level', 'Count'])
        
        fig = px.pie(df, values='Count', names='Level', 
                    title="Vulnerabilities by Severity Level",
                    color_discrete_map={
                        'critical': '#ff4444',
                        'high': '#ff8800', 
                        'medium': '#ffcc00',
                        'low': '#4488ff',
                        'info': '#888888'
                    })
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Top recommendations
    all_recommendations = set()
    for assessment in assessments:
        all_recommendations.update(assessment.recommendations)
    
    if all_recommendations:
        st.markdown("### 💡 Top Security Recommendations")
        for rec in sorted(all_recommendations):
            st.markdown(f"- {rec}")
            
    # Export report
    if st.button("📥 Export Security Report"):
        report_data = {
            'scan_date': datetime.now().isoformat(),
            'total_devices': total_devices,
            'average_score': avg_score,
            'vulnerability_summary': vuln_levels,
            'device_details': [
                {
                    'ip': a.device_ip,
                    'hostname': a.hostname,
                    'score': a.security_score,
                    'vulnerabilities': len(a.vulnerabilities),
                    'open_ports': a.open_ports
                }
                for a in assessments
            ]
        }
        
        st.download_button(
            label="💾 Download Report (JSON)",
            data=str(report_data),
            file_name=f"netarchon_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )