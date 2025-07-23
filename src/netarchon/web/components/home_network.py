"""
NetArchon Home Network Security Component

Secure monitoring and management specifically for home network devices with 
firewall integration and threat detection capabilities.
"""

import streamlit as st
import subprocess
import socket
import ipaddress
import time
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import hashlib
import hmac
import os
import re
import logging
from dataclasses import dataclass
from enum import Enum

class SecurityLevel(Enum):
    """Security threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DeviceType(Enum):
    """Home network device types."""
    MODEM = "modem"
    ROUTER = "router"
    ACCESS_POINT = "access_point"
    SWITCH = "switch"
    COMPUTER = "computer"
    MOBILE = "mobile"
    IOT = "iot"
    UNKNOWN = "unknown"

@dataclass
class HomeDevice:
    """Secure representation of home network device."""
    mac_address: str  # Primary identifier
    ip_address: str
    hostname: str
    device_type: DeviceType
    vendor: str
    first_seen: datetime
    last_seen: datetime
    is_authorized: bool = False
    security_score: int = 0
    open_ports: List[int] = None
    services: List[str] = None
    
    def __post_init__(self):
        if self.open_ports is None:
            self.open_ports = []
        if self.services is None:
            self.services = []

class SecureHomeNetworkMonitor:
    """Secure home network monitoring with firewall integration."""
    
    def __init__(self):
        """Initialize secure home network monitoring."""
        self.logger = logging.getLogger("HomeNetworkMonitor")
        self.home_network_ranges = [
            ipaddress.IPv4Network('192.168.1.0/24'),
            ipaddress.IPv4Network('10.0.0.0/8'),
            ipaddress.IPv4Network('172.16.0.0/12')
        ]
        
        # Known home devices (configured by user)
        self.authorized_devices = {
            "00:1A:2B:3C:4D:5E": {  # Arris Modem
                "name": "Xfinity Gateway",
                "type": DeviceType.MODEM,
                "expected_ip": "192.168.1.1",
                "vendor": "Arris",
                "model": "Surfboard S33"
            },
            "A1:B2:C3:D4:E5:F6": {  # Netgear Router
                "name": "Netgear Orbi Router", 
                "type": DeviceType.ROUTER,
                "expected_ip": "192.168.1.10",
                "vendor": "Netgear",
                "model": "RBK653"
            }
        }
        
        # Security monitoring
        self.security_events = []
        self.blocked_ips = set()
        self.suspicious_activity = {}
        
    def is_home_network_ip(self, ip_address: str) -> bool:
        """Check if IP address is within home network ranges."""
        try:
            ip = ipaddress.IPv4Address(ip_address)
            return any(ip in network for network in self.home_network_ranges)
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    def get_network_interface(self) -> Optional[str]:
        """Get primary network interface for home network."""
        try:
            # Get default route interface
            result = subprocess.run(['route', '-n', 'get', 'default'], 
                                  capture_output=True, text=True, timeout=5)
            
            for line in result.stdout.split('\n'):
                if 'interface:' in line:
                    return line.split(':')[1].strip()
            
            # Fallback to common interfaces
            for interface in ['en0', 'eth0', 'wlan0']:
                if os.path.exists(f'/sys/class/net/{interface}'):
                    return interface
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return None
    
    def scan_home_network(self, timeout: int = 30) -> List[HomeDevice]:
        """Secure scan of home network devices only."""
        devices = []
        
        # Get current network info
        interface = self.get_network_interface()
        if not interface:
            self.logger.error("Could not determine network interface")
            return devices
        
        try:
            # Use ARP table for local network discovery (safer than ping sweep)
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=timeout)
            
            for line in result.stdout.split('\n'):
                # Parse ARP entries: hostname (ip) at mac [ether] on interface
                match = re.search(r'(\S+)\s+\(([0-9.]+)\)\s+at\s+([0-9a-fA-F:]+)', line)
                if match:
                    hostname, ip, mac = match.groups()
                    
                    # Only process home network IPs
                    if self.is_home_network_ip(ip):
                        device = HomeDevice(
                            mac_address=mac.lower(),
                            ip_address=ip,
                            hostname=hostname if hostname != '?' else f"device-{ip.split('.')[-1]}",
                            device_type=self._classify_device(mac, ip, hostname),
                            vendor=self._get_vendor_from_mac(mac),
                            first_seen=datetime.now(),
                            last_seen=datetime.now(),
                            is_authorized=mac.lower() in self.authorized_devices
                        )
                        
                        # Security assessment
                        device.security_score = self._assess_device_security(device)
                        devices.append(device)
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            self.logger.error(f"Network scan failed: {e}")
        
        return devices
    
    def _classify_device(self, mac: str, ip: str, hostname: str) -> DeviceType:
        """Classify device type based on available information."""
        mac_lower = mac.lower()
        hostname_lower = hostname.lower()
        
        # Check against known devices
        if mac_lower in self.authorized_devices:
            return self.authorized_devices[mac_lower]["type"]
        
        # Classification based on MAC address OUI
        oui = mac_lower[:8]  # First 3 octets
        
        # Common router/modem MAC prefixes
        router_ouis = ['00:1a:2b', 'a1:b2:c3', '20:aa:4b', '44:d9:e7']
        if any(oui.startswith(prefix) for prefix in router_ouis):
            return DeviceType.ROUTER
        
        # Common mobile device patterns
        mobile_patterns = ['iphone', 'android', 'samsung', 'apple']
        if any(pattern in hostname_lower for pattern in mobile_patterns):
            return DeviceType.MOBILE
        
        # IoT device patterns
        iot_patterns = ['smart', 'echo', 'nest', 'ring', 'philips']
        if any(pattern in hostname_lower for pattern in iot_patterns):
            return DeviceType.IOT
        
        # Computer patterns
        computer_patterns = ['pc', 'laptop', 'desktop', 'macbook']
        if any(pattern in hostname_lower for pattern in computer_patterns):
            return DeviceType.COMPUTER
        
        return DeviceType.UNKNOWN
    
    def _get_vendor_from_mac(self, mac: str) -> str:
        """Get vendor name from MAC address OUI."""
        # Simplified vendor lookup (in production, use IEEE OUI database)
        oui_vendors = {
            '00:1a:2b': 'Arris',
            'a1:b2:c3': 'Netgear',
            '20:aa:4b': 'Apple',
            '44:d9:e7': 'Samsung',
            '00:50:56': 'VMware',
            '08:00:27': 'Oracle'
        }
        
        oui = mac.lower()[:8]
        return oui_vendors.get(oui, 'Unknown')
    
    def _assess_device_security(self, device: HomeDevice) -> int:
        """Assess device security score (0-100)."""
        score = 50  # Base score
        
        # Authorized device bonus
        if device.is_authorized:
            score += 30
        
        # Device type considerations
        if device.device_type in [DeviceType.MODEM, DeviceType.ROUTER]:
            score += 10  # Critical infrastructure
        elif device.device_type == DeviceType.IOT:
            score -= 20  # Often vulnerable
        elif device.device_type == DeviceType.UNKNOWN:
            score -= 30  # Suspicious
        
        # IP address patterns
        if device.ip_address.startswith('192.168.1.'):
            score += 10  # Expected range
        
        # Hostname analysis
        if 'unknown' in device.hostname.lower() or device.hostname == device.ip_address:
            score -= 15  # Suspicious naming
        
        return max(0, min(100, score))
    
    def check_device_ports(self, device: HomeDevice, common_ports: List[int] = None) -> List[int]:
        """Safely check common ports on home network device."""
        if common_ports is None:
            # Only check common administrative and service ports
            common_ports = [22, 23, 53, 80, 135, 139, 443, 445, 993, 995, 8080, 8443]
        
        open_ports = []
        
        # Only scan authorized devices or with explicit permission
        if not device.is_authorized:
            self.logger.warning(f"Skipping port scan for unauthorized device: {device.ip_address}")
            return open_ports
        
        try:
            for port in common_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)  # Short timeout for responsiveness
                
                result = sock.connect_ex((device.ip_address, port))
                if result == 0:
                    open_ports.append(port)
                    
                sock.close()
                
        except Exception as e:
            self.logger.error(f"Port scan failed for {device.ip_address}: {e}")
        
        device.open_ports = open_ports
        return open_ports
    
    def detect_security_threats(self, devices: List[HomeDevice]) -> List[Dict]:
        """Detect potential security threats in home network."""
        threats = []
        
        for device in devices:
            # Unauthorized device detection
            if not device.is_authorized:
                threats.append({
                    'type': 'unauthorized_device',
                    'severity': SecurityLevel.HIGH,
                    'device': device.ip_address,
                    'mac': device.mac_address,
                    'description': f'Unauthorized device detected: {device.hostname}',
                    'recommendation': 'Verify device identity and authorize if legitimate'
                })
            
            # Low security score
            if device.security_score < 30:
                threats.append({
                    'type': 'low_security_score',
                    'severity': SecurityLevel.MEDIUM,
                    'device': device.ip_address,
                    'score': device.security_score,
                    'description': f'Device has low security score: {device.security_score}/100',
                    'recommendation': 'Review device configuration and update if needed'
                })
            
            # Suspicious port configurations
            if device.open_ports:
                dangerous_ports = [23, 135, 139, 445]  # Telnet, RPC, NetBIOS
                open_dangerous = [p for p in device.open_ports if p in dangerous_ports]
                
                if open_dangerous:
                    threats.append({
                        'type': 'dangerous_ports_open',
                        'severity': SecurityLevel.HIGH,
                        'device': device.ip_address,
                        'ports': open_dangerous,
                        'description': f'Dangerous ports open: {open_dangerous}',
                        'recommendation': 'Close unnecessary ports and enable firewall'
                    })
        
        # Network-wide threats
        device_count = len(devices)
        if device_count > 20:  # Unusual number of devices
            threats.append({
                'type': 'unusual_device_count',
                'severity': SecurityLevel.MEDIUM,
                'count': device_count,
                'description': f'Unusual number of devices detected: {device_count}',
                'recommendation': 'Verify all devices are legitimate'
            })
        
        return threats
    
    def get_firewall_rules(self) -> List[Dict]:
        """Get current firewall rules (macOS/Linux)."""
        rules = []
        
        try:
            # Try pfctl (macOS)
            result = subprocess.run(['sudo', 'pfctl', '-sr'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        rules.append({
                            'type': 'pf',
                            'rule': line.strip(),
                            'active': True
                        })
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try iptables (Linux)
                result = subprocess.run(['sudo', 'iptables', '-L', '-n'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.strip() and not line.startswith('Chain'):
                            rules.append({
                                'type': 'iptables',
                                'rule': line.strip(),
                                'active': True
                            })
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return rules
    
    def block_suspicious_ip(self, ip_address: str, reason: str = "Security threat detected") -> bool:
        """Block suspicious IP address using system firewall."""
        if not self.is_home_network_ip(ip_address):
            return False  # Only block home network IPs
        
        try:
            # Block using pfctl (macOS)
            rule = f"block in quick from {ip_address} to any"
            result = subprocess.run(['sudo', 'pfctl', '-a', 'netarchon', '-f', '-'], 
                                  input=rule, text=True, timeout=10)
            
            if result.returncode == 0:
                self.blocked_ips.add(ip_address)
                self.logger.info(f"Blocked IP {ip_address}: {reason}")
                return True
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Block using iptables (Linux)
                result = subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-s', ip_address, '-j', 'DROP'],
                                      timeout=10)
                
                if result.returncode == 0:
                    self.blocked_ips.add(ip_address)
                    self.logger.info(f"Blocked IP {ip_address}: {reason}")
                    return True
                    
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return False
    
    def generate_security_report(self, devices: List[HomeDevice], threats: List[Dict]) -> Dict:
        """Generate comprehensive security report."""
        authorized_count = sum(1 for d in devices if d.is_authorized)
        unauthorized_count = len(devices) - authorized_count
        
        avg_security_score = sum(d.security_score for d in devices) / len(devices) if devices else 0
        
        high_threats = [t for t in threats if t['severity'] == SecurityLevel.HIGH]
        medium_threats = [t for t in threats if t['severity'] == SecurityLevel.MEDIUM]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'devices': {
                'total': len(devices),
                'authorized': authorized_count,  
                'unauthorized': unauthorized_count,
                'avg_security_score': round(avg_security_score, 1)
            },
            'threats': {
                'total': len(threats),
                'high': len(high_threats),
                'medium': len(medium_threats),
                'low': len(threats) - len(high_threats) - len(medium_threats)
            },
            'network_security': {
                'blocked_ips': len(self.blocked_ips),
                'firewall_active': len(self.get_firewall_rules()) > 0,
                'monitoring_active': True
            },
            'recommendations': self._generate_recommendations(devices, threats)
        }
    
    def _generate_recommendations(self, devices: List[HomeDevice], threats: List[Dict]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        unauthorized_devices = [d for d in devices if not d.is_authorized]
        if unauthorized_devices:
            recommendations.append(f"Review {len(unauthorized_devices)} unauthorized devices and authorize if legitimate")
        
        low_score_devices = [d for d in devices if d.security_score < 50]
        if low_score_devices:
            recommendations.append(f"Improve security for {len(low_score_devices)} devices with low security scores")
        
        if any(t['severity'] == SecurityLevel.HIGH for t in threats):
            recommendations.append("Address high-severity security threats immediately")
        
        if not self.get_firewall_rules():
            recommendations.append("Enable system firewall for additional protection")
        
        recommendations.append("Regularly update device firmware and passwords")
        recommendations.append("Enable WPA3 encryption on wireless networks")
        recommendations.append("Disable WPS and unnecessary network services")
        
        return recommendations


def render_home_network_security():
    """Render home network security monitoring interface."""
    st.subheader("🏠 Home Network Security Monitor")
    
    monitor = SecureHomeNetworkMonitor()
    
    # Security scan controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Scan Network", type="primary"):
            with st.spinner("Scanning home network..."):
                st.session_state.home_devices = monitor.scan_home_network()
                st.session_state.last_scan = datetime.now()
    
    with col2:
        if st.button("🔒 Security Check"):
            if 'home_devices' in st.session_state:
                with st.spinner("Analyzing security threats..."):
                    st.session_state.security_threats = monitor.detect_security_threats(st.session_state.home_devices)
    
    with col3:
        if st.button("📊 Generate Report"):
            if 'home_devices' in st.session_state and 'security_threats' in st.session_state:
                st.session_state.security_report = monitor.generate_security_report(
                    st.session_state.home_devices, 
                    st.session_state.security_threats
                )
    
    # Display results
    if 'home_devices' in st.session_state:
        devices = st.session_state.home_devices
        
        st.markdown("### 📱 Discovered Devices")
        
        for device in devices:
            status_color = "green" if device.is_authorized else "red"
            security_color = "green" if device.security_score >= 70 else "orange" if device.security_score >= 50 else "red"
            
            with st.expander(f"{'✅' if device.is_authorized else '❌'} {device.hostname} ({device.ip_address})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**MAC Address**: {device.mac_address}")
                    st.write(f"**Device Type**: {device.device_type.value}")
                    st.write(f"**Vendor**: {device.vendor}")
                    st.write(f"**Authorized**: <span style='color: {status_color}'>{'Yes' if device.is_authorized else 'No'}</span>", unsafe_allow_html=True)
                
                with col2:
                    st.write(f"**Security Score**: <span style='color: {security_color}'>{device.security_score}/100</span>", unsafe_allow_html=True)
                    st.write(f"**First Seen**: {device.first_seen.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Last Seen**: {device.last_seen.strftime('%Y-%m-%d %H:%M')}")
                    
                    if device.open_ports:
                        st.write(f"**Open Ports**: {', '.join(map(str, device.open_ports))}")
    
    # Security threats
    if 'security_threats' in st.session_state:
        threats = st.session_state.security_threats
        
        if threats:
            st.markdown("### 🚨 Security Threats")
            
            for threat in threats:
                severity_color = {
                    SecurityLevel.CRITICAL: "red",
                    SecurityLevel.HIGH: "orange", 
                    SecurityLevel.MEDIUM: "yellow",
                    SecurityLevel.LOW: "blue"
                }.get(threat['severity'], "gray")
                
                st.markdown(f"""
                <div style="border-left: 4px solid {severity_color}; padding: 10px; margin: 10px 0; background: rgba(255,255,255,0.1);">
                    <strong>{threat['severity'].value.upper()}: {threat['description']}</strong><br>
                    <small>Recommendation: {threat['recommendation']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No security threats detected!")
    
    # Security report
    if 'security_report' in st.session_state:
        report = st.session_state.security_report
        
        st.markdown("### 📊 Security Report")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Devices", report['devices']['total'])
            
        with col2:
            st.metric("Authorized", report['devices']['authorized'], 
                     delta=f"+{report['devices']['authorized'] - report['devices']['unauthorized']}")
        
        with col3:
            st.metric("Avg Security Score", f"{report['devices']['avg_security_score']}/100")
        
        with col4:
            st.metric("Active Threats", report['threats']['total'],
                     delta=f"High: {report['threats']['high']}")
        
        # Recommendations
        if report['recommendations']:
            st.markdown("### 💡 Security Recommendations")
            for rec in report['recommendations']:
                st.markdown(f"- {rec}")


def render_firewall_management():
    """Render firewall management interface."""
    st.subheader("🔥 Firewall Management")
    
    monitor = SecureHomeNetworkMonitor()
    
    # Get current firewall rules
    rules = monitor.get_firewall_rules()
    
    if rules:
        st.markdown("### Current Firewall Rules")
        
        for rule in rules:
            st.code(rule['rule'], language='bash')
    else:
        st.warning("⚠️ Firewall not detected or not configured")
        
        if st.button("🛡️ Enable Basic Firewall Protection"):
            st.info("This would enable basic firewall rules for your system")
    
    # Manual IP blocking
    st.markdown("### 🚫 Manual IP Blocking")
    
    col1, col2 = st.columns(2)
    
    with col1:
        block_ip = st.text_input("IP Address to Block", placeholder="192.168.1.100")
        block_reason = st.text_input("Reason", placeholder="Suspicious activity")
    
    with col2:
        if st.button("🚫 Block IP") and block_ip:
            if monitor.is_home_network_ip(block_ip):
                success = monitor.block_suspicious_ip(block_ip, block_reason)
                if success:
                    st.success(f"✅ Blocked IP: {block_ip}")
                else:
                    st.error("❌ Failed to block IP")
            else:
                st.error("❌ IP address not in home network range")
    
    # Show blocked IPs
    if monitor.blocked_ips:
        st.markdown("### 🚫 Blocked IP Addresses")
        for ip in monitor.blocked_ips:
            st.code(ip)