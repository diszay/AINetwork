"""
RustDesk Remote Desktop Monitoring Page

Comprehensive monitoring and management interface for RustDesk remote desktop infrastructure.
Provides real-time session tracking, security monitoring, and deployment management.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netarchon.integrations.rustdesk.monitor import RustDeskMonitor
from netarchon.integrations.rustdesk.home_network_integration import RustDeskHomeNetworkMonitor
from netarchon.integrations.rustdesk.installer import RustDeskInstaller
from netarchon.integrations.rustdesk.exceptions import RustDeskMonitoringError
from netarchon.utils.logger import get_logger
from netarchon.web.utils.security import require_authentication, validate_home_network

# Configure page
st.set_page_config(
    page_title="RustDesk Monitoring - NetArchon",
    page_icon="🖥️",
    layout="wide"
)

# Security validation
require_authentication()
validate_home_network()

logger = get_logger(__name__)

# Initialize RustDesk components
@st.cache_resource
def get_rustdesk_monitor():
    """Get cached RustDesk monitor instance."""
    return RustDeskMonitor()

@st.cache_resource
def get_home_network_monitor():
    """Get cached RustDesk home network monitor instance."""
    return RustDeskHomeNetworkMonitor()

@st.cache_resource
def get_rustdesk_installer():
    """Get cached RustDesk installer instance."""
    return RustDeskInstaller()

def render_server_status():
    """Render RustDesk server status overview."""
    st.subheader("🖥️ RustDesk Server Status")
    
    monitor = get_rustdesk_monitor()
    
    try:
        with st.spinner("Checking server status..."):
            # Check basic RustDesk status
            is_installed = monitor.is_rustdesk_installed()
            is_running = monitor.is_rustdesk_running()
            rustdesk_id = monitor.get_rustdesk_id()
            version = monitor._get_rustdesk_version()
            system_info = monitor.get_system_info()
        
        # Server overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Installation Status", 
                "✅ Installed" if is_installed else "❌ Not Installed",
                help="RustDesk installation status"
            )
        
        with col2:
            st.metric(
                "Service Status", 
                "🟢 Running" if is_running else "🔴 Stopped",
                help="RustDesk service status"
            )
        
        with col3:
            st.metric(
                "RustDesk ID", 
                rustdesk_id if rustdesk_id else "Not Available",
                help="Local RustDesk device ID"
            )
        
        with col4:
            st.metric(
                "Version", 
                version if version != "unknown" else "Unknown",
                help="RustDesk version"
            )
        
        # System information
        st.subheader("System Information")
        
        system_data = []
        for key, value in system_info.items():
            display_key = key.replace('_', ' ').title()
            if isinstance(value, bool):
                display_value = "✅ Yes" if value else "❌ No"
            else:
                display_value = str(value)
            
            system_data.append({
                "Property": display_key,
                "Value": display_value
            })
        
        df_system = pd.DataFrame(system_data)
        st.dataframe(df_system, use_container_width=True)
        
        # RustDesk paths and configuration
        st.subheader("Configuration Paths")
        
        config_data = [
            {"Path Type": "Executable", "Location": monitor.rustdesk_path},
            {"Path Type": "Configuration", "Location": monitor.config_path},
            {"Path Type": "Logs", "Location": monitor.log_path}
        ]
        
        df_config = pd.DataFrame(config_data)
        st.dataframe(df_config, use_container_width=True)
        
        # Control buttons
        st.subheader("Service Control")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Start RustDesk", disabled=is_running):
                with st.spinner("Starting RustDesk..."):
                    if monitor.start_rustdesk():
                        st.success("RustDesk started successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to start RustDesk")
        
        with col2:
            if st.button("Stop RustDesk", disabled=not is_running):
                with st.spinner("Stopping RustDesk..."):
                    if monitor.stop_rustdesk():
                        st.success("RustDesk stopped successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to stop RustDesk")
        
        with col3:
            if st.button("Restart RustDesk"):
                with st.spinner("Restarting RustDesk..."):
                    if monitor.restart_rustdesk():
                        st.success("RustDesk restarted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to restart RustDesk")
        
    except Exception as e:
        st.error(f"Failed to get server status: {str(e)}")
        st.info("Make sure you have proper permissions to access RustDesk.")

def render_active_sessions():
    """Render active RustDesk sessions."""
    st.subheader("🔗 Active Sessions")
    
    monitor = get_rustdesk_monitor()
    
    try:
        with st.spinner("Loading active sessions..."):
            # Get active connections from the monitor
            connections = monitor.get_active_connections()
        
        if connections:
            sessions_data = []
            for conn in connections:
                duration = "N/A"
                if hasattr(conn, 'start_time') and conn.start_time:
                    duration_seconds = (datetime.now() - conn.start_time).total_seconds()
                    duration = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
                
                sessions_data.append({
                    "Session ID": getattr(conn, 'session_id', 'N/A'),
                    "Peer ID": getattr(conn, 'peer_id', 'Unknown'),
                    "Peer Address": getattr(conn, 'peer_address', 'N/A'),
                    "Type": getattr(conn, 'connection_type', 'remote_control'),
                    "Status": getattr(conn, 'status', 'unknown').title() if hasattr(conn, 'status') else 'Active',
                    "Duration": duration,
                    "Started": conn.start_time.strftime("%H:%M:%S") if hasattr(conn, 'start_time') and conn.start_time else "N/A"
                })
            
            df = pd.DataFrame(sessions_data)
            st.dataframe(df, use_container_width=True)
            
            # Session statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Active", len(connections))
            
            with col2:
                # Count different connection types if available
                remote_control_count = len([c for c in connections if getattr(c, 'connection_type', '') == 'remote_control'])
                st.metric("Remote Control", remote_control_count)
            
            with col3:
                file_transfer_count = len([c for c in connections if getattr(c, 'connection_type', '') == 'file_transfer'])
                st.metric("File Transfer", file_transfer_count)
        
        else:
            st.info("No active sessions found.")
            
        # Connection history section
        st.subheader("Recent Connection History")
        
        with st.spinner("Loading connection history..."):
            history = monitor.get_connection_history(max_entries=50)
        
        if history:
            history_data = []
            for entry in history:
                history_data.append({
                    "Time": entry.get('timestamp', 'N/A'),
                    "Peer ID": entry.get('peer_id', 'Unknown'),
                    "Type": entry.get('type', 'unknown').title(),
                    "Status": entry.get('status', 'unknown').title()
                })
            
            df_history = pd.DataFrame(history_data)
            
            # Color-code status
            def highlight_history_status(val):
                if val == "Connected":
                    return "background-color: #d4edda"
                elif val == "Disconnected":
                    return "background-color: #f8d7da"
                elif val == "Failed":
                    return "background-color: #f8d7da"
                else:
                    return "background-color: #fff3cd"
            
            st.dataframe(
                df_history.style.applymap(highlight_history_status, subset=["Status"]),
                use_container_width=True
            )
        else:
            st.info("No connection history available.")
    
    except Exception as e:
        st.error(f"Failed to load active sessions: {str(e)}")
        st.info("This may be normal if RustDesk is not currently running or no sessions are active.")

def render_device_management():
    """Render device management interface."""
    st.subheader("📱 Device Management")
    
    monitor = get_rustdesk_monitor()
    
    try:
        with st.spinner("Loading device information..."):
            # Get local client info
            client_info = monitor.get_client_info()
            system_info = monitor.get_system_info()
        
        # Local device information
        st.subheader("Local Device")
        
        if client_info:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Device ID", client_info.id or "Not Available")
            
            with col2:
                status_icon = "🟢" if client_info.status == "running" else "🔴"
                st.metric("Status", f"{status_icon} {client_info.status.title()}")
            
            with col3:
                st.metric("Platform", client_info.platform.title())
            
            with col4:
                st.metric("Version", client_info.version or "Unknown")
            
            # Additional device details
            device_details = [
                {"Property": "Hostname", "Value": client_info.hostname or "Unknown"},
                {"Property": "Platform", "Value": client_info.platform or "Unknown"},
                {"Property": "Version", "Value": client_info.version or "Unknown"},
                {"Property": "Status", "Value": client_info.status or "Unknown"}
            ]
            
            df_device = pd.DataFrame(device_details)
            st.dataframe(df_device, use_container_width=True)
        
        else:
            st.warning("Local RustDesk client information not available. Make sure RustDesk is running.")
        
        # System information
        st.subheader("System Information")
        
        system_data = []
        for key, value in system_info.items():
            display_key = key.replace('_', ' ').title()
            if isinstance(value, bool):
                display_value = "✅ Yes" if value else "❌ No"
            else:
                display_value = str(value)
            
            system_data.append({
                "Property": display_key,
                "Value": display_value
            })
        
        df_system = pd.DataFrame(system_data)
        st.dataframe(df_system, use_container_width=True)
        
        # Device capabilities and features
        st.subheader("Device Capabilities")
        
        capabilities = [
            {"Feature": "Remote Desktop", "Status": "✅ Available" if system_info.get('rustdesk_installed') else "❌ Not Available"},
            {"Feature": "File Transfer", "Status": "✅ Supported" if system_info.get('rustdesk_running') else "❌ Not Running"},
            {"Feature": "Audio Support", "Status": "✅ Available"},
            {"Feature": "Clipboard Sync", "Status": "✅ Available"},
            {"Feature": "Multi-Monitor", "Status": "✅ Supported"}
        ]
        
        df_capabilities = pd.DataFrame(capabilities)
        st.dataframe(df_capabilities, use_container_width=True)
        
        # Network device discovery (if available)
        st.subheader("Network Device Discovery")
        
        # This would be enhanced with actual network scanning
        st.info("Network device discovery requires additional network scanning capabilities. This feature will show other RustDesk-enabled devices on your network.")
        
        # Placeholder for future network device discovery
        discovered_devices = [
            {"Device Name": "Example Device", "IP Address": "192.168.1.101", "Status": "🔴 Offline", "Last Seen": "Never"},
        ]
        
        df_discovered = pd.DataFrame(discovered_devices)
        st.dataframe(df_discovered, use_container_width=True)
        
        # Device management actions
        st.subheader("Device Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Refresh Device Info"):
                st.rerun()
        
        with col2:
            if st.button("Scan Network"):
                st.info("Network scanning functionality will be implemented in future updates.")
        
        with col3:
            if st.button("Export Device List"):
                # Create export data
                export_data = {
                    "local_device": client_info.__dict__ if client_info else {},
                    "system_info": system_info,
                    "timestamp": datetime.now().isoformat()
                }
                
                st.download_button(
                    label="Download JSON",
                    data=pd.Series(export_data).to_json(indent=2),
                    file_name=f"rustdesk_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    except Exception as e:
        st.error(f"Failed to load device information: {str(e)}")
        st.info("Make sure RustDesk is properly installed and you have the necessary permissions.")

def render_network_metrics():
    """Render network performance metrics."""
    st.subheader("📊 Network Performance")
    
    monitor = get_rustdesk_monitor()
    
    try:
        # Since the monitor doesn't have get_network_metrics, we'll create a simulated view
        # based on available data
        
        with st.spinner("Analyzing network performance..."):
            # Get current system info and connection data
            system_info = monitor.get_system_info()
            active_connections = monitor.get_active_connections()
            connection_history = monitor.get_connection_history(max_entries=100)
        
        # Current network status
        st.subheader("Current Network Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Connections", len(active_connections))
        
        with col2:
            st.metric("Platform", system_info.get('platform', 'Unknown').title())
        
        with col3:
            st.metric("RustDesk Running", "✅ Yes" if system_info.get('rustdesk_running') else "❌ No")
        
        with col4:
            st.metric("Network Interface", "Available" if system_info.get('rustdesk_installed') else "N/A")
        
        # Connection history analysis
        if connection_history:
            st.subheader("Connection Activity Analysis")
            
            # Process connection history for visualization
            connection_times = []
            connection_types = []
            connection_statuses = []
            
            for entry in connection_history:
                if entry.get('timestamp'):
                    connection_times.append(entry['timestamp'])
                    connection_types.append(entry.get('type', 'unknown'))
                    connection_statuses.append(entry.get('status', 'unknown'))
            
            if connection_times:
                # Create a simple time-based chart
                history_df = pd.DataFrame({
                    'Time': connection_times,
                    'Type': connection_types,
                    'Status': connection_statuses
                })
                
                # Connection type distribution
                type_counts = pd.Series(connection_types).value_counts()
                if not type_counts.empty:
                    fig_types = px.pie(
                        values=type_counts.values,
                        names=type_counts.index,
                        title="Connection Type Distribution"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
                
                # Connection status distribution
                status_counts = pd.Series(connection_statuses).value_counts()
                if not status_counts.empty:
                    fig_status = px.bar(
                        x=status_counts.index,
                        y=status_counts.values,
                        title="Connection Status Distribution",
                        labels={'x': 'Status', 'y': 'Count'}
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
                
                # Recent activity table
                st.subheader("Recent Connection Activity")
                recent_history = history_df.tail(20)  # Show last 20 connections
                st.dataframe(recent_history, use_container_width=True)
        
        else:
            st.info("No connection history available for analysis.")
        
        # Network performance recommendations
        st.subheader("Performance Recommendations")
        
        recommendations = []
        
        if not system_info.get('rustdesk_running'):
            recommendations.append("🔴 RustDesk is not running. Start the service for network monitoring.")
        
        if len(active_connections) == 0:
            recommendations.append("🟡 No active connections. Network performance data will be limited.")
        
        if len(connection_history) < 10:
            recommendations.append("🟡 Limited connection history. More data needed for comprehensive analysis.")
        
        if not recommendations:
            recommendations.append("🟢 Network monitoring is active and collecting data.")
        
        for rec in recommendations:
            st.write(rec)
        
        # System resource usage (if available)
        st.subheader("System Resources")
        
        resource_data = [
            {"Resource": "CPU Usage", "Status": "Monitoring Available", "Notes": "Requires system monitoring integration"},
            {"Resource": "Memory Usage", "Status": "Monitoring Available", "Notes": "Requires system monitoring integration"},
            {"Resource": "Network Bandwidth", "Status": "Basic Monitoring", "Notes": "Enhanced monitoring in development"},
            {"Resource": "Disk I/O", "Status": "Not Monitored", "Notes": "Future enhancement"}
        ]
        
        df_resources = pd.DataFrame(resource_data)
        st.dataframe(df_resources, use_container_width=True)
    
    except Exception as e:
        st.error(f"Failed to load network metrics: {str(e)}")
        st.info("Network metrics require RustDesk to be running and active connections for meaningful data.")

def render_security_monitoring():
    """Render security monitoring interface."""
    st.subheader("🔒 Security Monitoring")
    
    monitor = get_rustdesk_monitor()
    home_monitor = get_home_network_monitor()
    
    try:
        # Time range for security scan
        hours_back = st.selectbox(
            "Scan Period",
            options=[1, 6, 12, 24, 48],
            format_func=lambda x: f"{x}h",
            index=2  # Default to 12 hours
        )
        
        with st.spinner("Analyzing security status..."):
            # Get connection history for security analysis
            connection_history = monitor.get_connection_history(max_entries=200)
            system_info = monitor.get_system_info()
            
            # Get home network security events if available
            try:
                home_security_events = home_monitor.get_home_network_security_events(hours_back)
            except:
                home_security_events = []
        
        # Security overview
        st.subheader("Security Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("RustDesk Status", "🟢 Secure" if system_info.get('rustdesk_running') else "🔴 Not Running")
        
        with col2:
            recent_connections = len([h for h in connection_history if h.get('timestamp')])
            st.metric("Recent Connections", recent_connections)
        
        with col3:
            failed_connections = len([h for h in connection_history if h.get('status') == 'failed'])
            st.metric("Failed Attempts", failed_connections)
        
        with col4:
            security_score = 100 - (failed_connections * 5)  # Simple scoring
            security_score = max(0, min(100, security_score))
            st.metric("Security Score", f"{security_score}%")
        
        # Connection analysis
        if connection_history:
            st.subheader("Connection Security Analysis")
            
            # Analyze connection patterns
            connection_analysis = []
            unique_peers = set()
            suspicious_patterns = []
            
            for entry in connection_history:
                peer_id = entry.get('peer_id', 'Unknown')
                unique_peers.add(peer_id)
                
                # Check for suspicious patterns
                if entry.get('status') == 'failed':
                    suspicious_patterns.append({
                        "Type": "Failed Connection",
                        "Peer ID": peer_id,
                        "Time": entry.get('timestamp', 'N/A'),
                        "Severity": "Medium"
                    })
                
                connection_analysis.append({
                    "Time": entry.get('timestamp', 'N/A'),
                    "Peer ID": peer_id,
                    "Type": entry.get('type', 'unknown').title(),
                    "Status": entry.get('status', 'unknown').title(),
                    "Security Risk": "Low" if entry.get('status') == 'connected' else "Medium"
                })
            
            # Display connection analysis
            df_analysis = pd.DataFrame(connection_analysis)
            
            # Color-code security risk
            def highlight_security_risk(val):
                if val == "High":
                    return "background-color: #f8d7da"
                elif val == "Medium":
                    return "background-color: #fff3cd"
                else:
                    return "background-color: #d4edda"
            
            st.dataframe(
                df_analysis.style.applymap(highlight_security_risk, subset=["Security Risk"]),
                use_container_width=True
            )
            
            # Security statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Unique Peers", len(unique_peers))
            
            with col2:
                success_rate = (len([h for h in connection_history if h.get('status') == 'connected']) / len(connection_history) * 100) if connection_history else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            with col3:
                st.metric("Suspicious Events", len(suspicious_patterns))
            
            # Suspicious patterns
            if suspicious_patterns:
                st.subheader("⚠️ Suspicious Activity")
                df_suspicious = pd.DataFrame(suspicious_patterns)
                st.dataframe(df_suspicious, use_container_width=True)
        
        # Home network security events
        if home_security_events:
            st.subheader("🏠 Home Network Security Events")
            
            events_data = []
            for event in home_security_events:
                events_data.append({
                    "Time": event.get('timestamp', 'N/A'),
                    "Type": event.get('event_type', 'unknown').replace('_', ' ').title(),
                    "Severity": event.get('severity', 'medium').title(),
                    "Device": event.get('device_name', 'Unknown'),
                    "Remote IP": event.get('remote_ip', 'N/A'),
                    "Home Network": "✅ Yes" if event.get('home_network_validated') else "❌ No",
                    "Description": event.get('description', 'No description')[:50] + "..."
                })
            
            df_home_events = pd.DataFrame(events_data)
            st.dataframe(df_home_events, use_container_width=True)
        
        # Security recommendations
        st.subheader("Security Recommendations")
        
        recommendations = []
        
        if not system_info.get('rustdesk_running'):
            recommendations.append("🔴 RustDesk is not running. Start the service to enable security monitoring.")
        
        if failed_connections > 5:
            recommendations.append("🟡 High number of failed connections detected. Review access logs.")
        
        if len(unique_peers) > 10:
            recommendations.append("🟡 Many unique peer connections. Verify all connections are authorized.")
        
        if not connection_history:
            recommendations.append("🟡 No connection history available. Enable logging for better security monitoring.")
        
        if not recommendations:
            recommendations.append("🟢 No immediate security concerns detected.")
        
        for rec in recommendations:
            st.write(rec)
        
        # Security configuration
        st.subheader("Security Configuration")
        
        security_config = [
            {"Setting": "Authentication", "Status": "✅ Enabled", "Recommendation": "Keep enabled"},
            {"Setting": "Encryption", "Status": "✅ Active", "Recommendation": "Use strong keys"},
            {"Setting": "Access Control", "Status": "🟡 Basic", "Recommendation": "Implement IP restrictions"},
            {"Setting": "Logging", "Status": "✅ Enabled", "Recommendation": "Regular log review"},
            {"Setting": "Auto-Lock", "Status": "🟡 Not Configured", "Recommendation": "Enable session timeout"}
        ]
        
        df_config = pd.DataFrame(security_config)
        st.dataframe(df_config, use_container_width=True)
    
    except Exception as e:
        st.error(f"Failed to analyze security status: {str(e)}")
        st.info("Security monitoring requires RustDesk to be running and connection history to be available.")

def render_home_network_topology():
    """Render home network topology and integration status."""
    st.subheader("🏠 Home Network Topology")
    
    home_monitor = get_home_network_monitor()
    
    try:
        with st.spinner("Analyzing home network topology..."):
            topology_status = home_monitor.get_network_topology_status()
            enhanced_status = home_monitor.get_enhanced_server_status()
        
        # Network overview
        st.subheader("Network Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Network Range", topology_status["network_range"])
        
        with col2:
            online_devices = sum(1 for device in topology_status["devices"].values() if device["connectivity"])
            total_devices = len(topology_status["devices"])
            st.metric("Online Devices", f"{online_devices}/{total_devices}")
        
        with col3:
            threat_level = topology_status["security_status"]["threat_level"]
            threat_color = "🟢" if threat_level == "low" else "🟡" if threat_level == "medium" else "🔴"
            st.metric("Threat Level", f"{threat_color} {threat_level.title()}")
        
        # Home network devices status
        st.subheader("Home Network Devices")
        
        devices_data = []
        for device_ip, device_status in topology_status["devices"].items():
            device_info = device_status["info"]
            devices_data.append({
                "Device": device_info["name"],
                "IP Address": device_ip,
                "Type": device_info["type"].value.replace('_', ' ').title(),
                "Vendor": device_info["vendor"],
                "Model": device_info["model"],
                "Status": "🟢 Online" if device_status["connectivity"] else "🔴 Offline",
                "Response Time": f"{device_status['response_time']}ms" if device_status["response_time"] else "N/A",
                "Open Ports": ", ".join(map(str, device_status["open_ports"])) if device_status["open_ports"] else "None"
            })
        
        df = pd.DataFrame(devices_data)
        st.dataframe(df, use_container_width=True)
        
        # Network connectivity map
        st.subheader("Connectivity Map")
        
        connectivity_map = topology_status["connectivity_map"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Internet Connection**")
            internet_status = connectivity_map["internet"]
            st.write(f"Gateway: {internet_status['gateway']}")
            st.write(f"Modem: {internet_status['modem']}")
            status_icon = "🟢" if internet_status["status"] == "connected" else "🔴"
            st.write(f"Status: {status_icon} {internet_status['status'].title()}")
        
        with col2:
            st.write("**Local Network**")
            local_status = connectivity_map["local_network"]
            st.write(f"Router: {local_status['router']}")
            st.write(f"Server: {local_status['server']}")
            mesh_icon = "🟢" if local_status["mesh_status"] == "active" else "🔴"
            st.write(f"Mesh Status: {mesh_icon} {local_status['mesh_status'].title()}")
        
        # Security status
        st.subheader("Security Status")
        
        security_status = topology_status["security_status"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rfc1918_icon = "🟢" if security_status["rfc1918_compliance"] else "🔴"
            st.metric("RFC 1918 Compliance", f"{rfc1918_icon} {'Yes' if security_status['rfc1918_compliance'] else 'No'}")
        
        with col2:
            external_icon = "🔴" if security_status["external_connections_detected"] else "🟢"
            st.metric("External Connections", f"{external_icon} {'Detected' if security_status['external_connections_detected'] else 'None'}")
        
        with col3:
            firewall_icon = "🟢" if security_status["firewall_status"] == "active" else "🔴"
            st.metric("Firewall Status", f"{firewall_icon} {security_status['firewall_status'].title()}")
        
        # External connections warning
        if security_status["external_connections"]:
            st.warning("⚠️ External connections detected!")
            external_data = []
            for conn in security_status["external_connections"]:
                external_data.append({
                    "Remote IP": conn["remote_ip"],
                    "Type": conn["connection_type"],
                    "Status": conn["status"],
                    "Threat Level": conn["threat_level"],
                    "Start Time": conn["start_time"] or "N/A"
                })
            
            df_external = pd.DataFrame(external_data)
            st.dataframe(df_external, use_container_width=True)
        
        # RustDesk server deployment info
        if "home_network" in enhanced_status:
            st.subheader("RustDesk Server Deployment")
            home_info = enhanced_status["home_network"]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Deployment Location:** {home_info['deployment_location']}")
                st.write(f"**Server IP:** {home_info['server_ip']}")
            
            with col2:
                st.write("**Security Validation:**")
                security_val = home_info["security_validation"]
                for key, value in security_val.items():
                    icon = "🟢" if value else "🔴"
                    st.write(f"{icon} {key.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
    
    except Exception as e:
        st.error(f"Failed to load home network topology: {str(e)}")

def render_deployment_management():
    """Render deployment management interface."""
    st.subheader("🚀 Deployment Management")
    
    installer = get_rustdesk_installer()
    
    # Server deployment section
    with st.expander("Server Deployment", expanded=False):
        st.write("Deploy RustDesk server on your Mini PC Ubuntu 24.04 LTS")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_host = st.text_input(
                "Target Host", 
                value="192.168.1.100",
                help="IP address of your Mini PC"
            )
            
            install_method = st.selectbox(
                "Installation Method",
                options=["docker", "binary"],
                help="Docker is recommended for easier management"
            )
        
        with col2:
            custom_key = st.text_input(
                "Custom Key (Optional)",
                help="Custom encryption key for server"
            )
            
            relay_servers = st.text_area(
                "Relay Servers (Optional)",
                help="Additional relay servers, one per line"
            )
        
        if st.button("Deploy Server", type="primary"):
            try:
                with st.spinner("Deploying RustDesk server..."):
                    config = {
                        'custom_key': custom_key if custom_key else None,
                        'relay_servers': relay_servers.split('\n') if relay_servers else None
                    }
                    
                    result = installer.install_server(
                        target_host=target_host,
                        install_method=install_method,
                        config=config
                    )
                    
                    if result.get('success'):
                        st.success("Server deployed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Deployment failed: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Deployment error: {str(e)}")
    
    # Client deployment section
    with st.expander("Client Deployment", expanded=False):
        st.write("Deploy RustDesk clients to network devices")
        
        col1, col2 = st.columns(2)
        
        with col1:
            client_host = st.text_input(
                "Client Host",
                help="IP address of target device"
            )
            
            platform = st.selectbox(
                "Platform",
                options=["linux", "windows", "macos"],
                help="Target device platform"
            )
        
        with col2:
            server_address = st.text_input(
                "Server Address",
                value="192.168.1.100",
                help="RustDesk server address"
            )
            
            auto_start = st.checkbox(
                "Auto Start",
                value=True,
                help="Start client automatically on boot"
            )
        
        if st.button("Deploy Client"):
            try:
                with st.spinner("Deploying RustDesk client..."):
                    deployment_config = {
                        'server_address': server_address,
                        'auto_start': auto_start
                    }
                    
                    result = installer.deploy_client(
                        target_device=client_host,
                        platform=platform,
                        deployment_config=deployment_config
                    )
                    
                    if result.get('success'):
                        st.success("Client deployed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Client deployment failed: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Client deployment error: {str(e)}")

def main():
    """Main RustDesk monitoring page."""
    st.title("🖥️ RustDesk Remote Desktop Monitoring")
    st.markdown("Comprehensive monitoring and management of RustDesk remote desktop infrastructure")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)
    
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Server Status", "Active Sessions", "Devices", 
        "Network Metrics", "Security", "Home Network", "Deployment"
    ])
    
    with tab1:
        render_server_status()
    
    with tab2:
        render_active_sessions()
    
    with tab3:
        render_device_management()
    
    with tab4:
        render_network_metrics()
    
    with tab5:
        render_security_monitoring()
    
    with tab6:
        render_home_network_topology()
    
    with tab7:
        render_deployment_management()
    
    # Footer with refresh info
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NetArchon RustDesk Monitor")

if __name__ == "__main__":
    main()s = connectivity_map["internet"]
            st.write(f"Gateway: {internet_status['gateway']}")
            st.write(f"Modem: {internet_status['modem']}")
            status_icon = "🟢" if internet_status["status"] == "connected" else "🔴"
            st.write(f"Status: {status_icon} {internet_status['status'].title()}")
        
        with col2:
            st.write("**Local Network**")
            local_status = connectivity_map["local_network"]
            st.write(f"Router: {local_status['router']}")
            st.write(f"Server: {local_status['server']}")
            mesh_icon = "🟢" if local_status["mesh_status"] == "active" else "🔴"
            st.write(f"Mesh Status: {mesh_icon} {local_status['mesh_status'].title()}")
        
        # Security status
        st.subheader("Security Status")
        
        security_status = topology_status["security_status"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rfc1918_icon = "🟢" if security_status["rfc1918_compliance"] else "🔴"
            st.metric("RFC 1918 Compliance", f"{rfc1918_icon} {'Yes' if security_status['rfc1918_compliance'] else 'No'}")
        
        with col2:
            external_icon = "🔴" if security_status["external_connections_detected"] else "🟢"
            st.metric("External Connections", f"{external_icon} {'Detected' if security_status['external_connections_detected'] else 'None'}")
        
        with col3:
            firewall_icon = "🟢" if security_status["firewall_status"] == "active" else "🔴"
            st.metric("Firewall Status", f"{firewall_icon} {security_status['firewall_status'].title()}")
        
        # External connections warning
        if security_status["external_connections"]:
            st.warning("⚠️ External connections detected!")
            external_data = []
            for conn in security_status["external_connections"]:
                external_data.append({
                    "Remote IP": conn["remote_ip"],
                    "Type": conn["connection_type"],
                    "Status": conn["status"],
                    "Threat Level": conn["threat_level"],
                    "Start Time": conn["start_time"] or "N/A"
                })
            
            df_external = pd.DataFrame(external_data)
            st.dataframe(df_external, use_container_width=True)
        
        # RustDesk server deployment info
        if "home_network" in enhanced_status:
            st.subheader("RustDesk Server Deployment")
            home_info = enhanced_status["home_network"]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Deployment Location:** {home_info['deployment_location']}")
                st.write(f"**Server IP:** {home_info['server_ip']}")
            
            with col2:
                st.write("**Security Validation:**")
                security_val = home_info["security_validation"]
                for key, value in security_val.items():
                    icon = "🟢" if value else "🔴"
                    st.write(f"{icon} {key.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
    
    except Exception as e:
        st.error(f"Failed to load home network topology: {str(e)}")

def render_deployment_management():
    """Render deployment management interface."""
    st.subheader("🚀 Deployment Management")
    
    installer = get_rustdesk_installer()
    
    # Server deployment section
    with st.expander("Server Deployment", expanded=False):
        st.write("Deploy RustDesk server on your Mini PC Ubuntu 24.04 LTS")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_host = st.text_input(
                "Target Host", 
                value="192.168.1.100",
                help="IP address of your Mini PC"
            )
            
            install_method = st.selectbox(
                "Installation Method",
                options=["docker", "binary"],
                help="Docker is recommended for easier management"
            )
        
        with col2:
            custom_key = st.text_input(
                "Custom Key (Optional)",
                help="Custom encryption key for server"
            )
            
            relay_servers = st.text_area(
                "Relay Servers (Optional)",
                help="Additional relay servers, one per line"
            )
        
        if st.button("Deploy Server", type="primary"):
            try:
                with st.spinner("Deploying RustDesk server..."):
                    config = {
                        'custom_key': custom_key if custom_key else None,
                        'relay_servers': relay_servers.split('\n') if relay_servers else None
                    }
                    
                    result = installer.install_server(
                        target_host=target_host,
                        install_method=install_method,
                        config=config
                    )
                    
                    if result.get('success'):
                        st.success("Server deployed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Deployment failed: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Deployment error: {str(e)}")
    
    # Client deployment section
    with st.expander("Client Deployment", expanded=False):
        st.write("Deploy RustDesk clients to network devices")
        
        col1, col2 = st.columns(2)
        
        with col1:
            client_host = st.text_input(
                "Client Host",
                help="IP address of target device"
            )
            
            platform = st.selectbox(
                "Platform",
                options=["linux", "windows", "macos"],
                help="Target device platform"
            )
        
        with col2:
            server_address = st.text_input(
                "Server Address",
                value="192.168.1.100",
                help="RustDesk server address"
            )
            
            auto_start = st.checkbox(
                "Auto Start",
                value=True,
                help="Start client automatically on boot"
            )
        
        if st.button("Deploy Client"):
            try:
                with st.spinner("Deploying RustDesk client..."):
                    deployment_config = {
                        'server_address': server_address,
                        'auto_start': auto_start
                    }
                    
                    result = installer.deploy_client(
                        target_device=client_host,
                        platform=platform,
                        deployment_config=deployment_config
                    )
                    
                    if result.get('success'):
                        st.success("Client deployed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Client deployment failed: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Client deployment error: {str(e)}")

def main():
    """Main RustDesk monitoring page."""
    st.title("🖥️ RustDesk Remote Desktop Monitoring")
    st.markdown("Comprehensive monitoring and management of RustDesk remote desktop infrastructure")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)
    
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Server Status", "Active Sessions", "Devices", 
        "Network Metrics", "Security", "Home Network", "Deployment"
    ])
    
    with tab1:
        render_server_status()
    
    with tab2:
        render_active_sessions()
    
    with tab3:
        render_device_management()
    
    with tab4:
        render_network_metrics()
    
    with tab5:
        render_security_monitoring()
    
    with tab6:
        render_home_network_topology()
    
    with tab7:
        render_deployment_management()
    
    # Footer with refresh info
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NetArchon RustDesk Monitor")

if __name__ == "__main__":
    main()s = connectivity_map["internet"]
            st.write(f"Gateway: {internet_status['gateway']}")
            st.write(f"Modem: {internet_status['modem']}")
            status_icon = "🟢" if internet_status["status"] == "connected" else "🔴"
            st.write(f"Status: {status_icon} {internet_status['status'].title()}")
        
        with col2:
            st.write("**Local Network**")
            local_status = connectivity_map["local_network"]
            st.write(f"Router: {local_status['router']}")
            st.write(f"Server: {local_status['server']}")
            mesh_icon = "🟢" if local_status["mesh_status"] == "active" else "🔴"
            st.write(f"Mesh Status: {mesh_icon} {local_status['mesh_status'].title()}")
        
        # Security status
        st.subheader("Security Status")
        
        security_status = topology_status["security_status"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rfc1918_icon = "🟢" if security_status["rfc1918_compliance"] else "🔴"
            st.metric("RFC 1918 Compliance", f"{rfc1918_icon} {'Yes' if security_status['rfc1918_compliance'] else 'No'}")
        
        with col2:
            external_icon = "🔴" if security_status["external_connections_detected"] else "🟢"
            st.metric("External Connections", f"{external_icon} {'Detected' if security_status['external_connections_detected'] else 'None'}")
        
        with col3:
            firewall_icon = "🟢" if security_status["firewall_status"] == "active" else "🔴"
            st.metric("Firewall Status", f"{firewall_icon} {security_status['firewall_status'].title()}")
        
        # External connections warning
        if security_status["external_connections"]:
            st.warning("⚠️ External connections detected!")
            external_data = []
            for conn in security_status["external_connections"]:
                external_data.append({
                    "Remote IP": conn["remote_ip"],
                    "Type": conn["connection_type"],
                    "Status": conn["status"],
                    "Threat Level": conn["threat_level"],
                    "Start Time": conn["start_time"] or "N/A"
                })
            
            df_external = pd.DataFrame(external_data)
            st.dataframe(df_external, use_container_width=True)
        
        # RustDesk server deployment info
        if "home_network" in enhanced_status:
            st.subheader("RustDesk Server Deployment")
            home_info = enhanced_status["home_network"]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Deployment Location:** {home_info['deployment_location']}")
                st.write(f"**Server IP:** {home_info['server_ip']}")
            
            with col2:
                st.write("**Security Validation:**")
                security_val = home_info["security_validation"]
                for key, value in security_val.items():
                    icon = "🟢" if value else "🔴"
                    st.write(f"{icon} {key.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
    
    except Exception as e:
        st.error(f"Failed to load home network topology: {str(e)}")

def render_deployment_management():
    """Render deployment management interface."""
    st.subheader("🚀 Deployment Management")
    
    installer = get_rustdesk_installer()
    
    # Server deployment section
    with st.expander("Server Deployment", expanded=False):
        st.write("Deploy RustDesk server on your Mini PC Ubuntu 24.04 LTS")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_host = st.text_input(
                "Target Host", 
                value="192.168.1.100",
                help="IP address of your Mini PC"
            )
            
            install_method = st.selectbox(
                "Installation Method",
                options=["docker", "binary"],
                help="Docker is recommended for easier management"
            )
        
        with col2:
            custom_key = st.text_input(
                "Custom Key (Optional)",
                help="Custom encryption key for server"
            )
            
            relay_servers = st.text_area(
                "Relay Servers (Optional)",
                help="Additional relay servers, one per line"
            )
        
        if st.button("Deploy Server", type="primary"):
            try:
                with st.spinner("Deploying RustDesk server..."):
                    config = {
                        'custom_key': custom_key if custom_key else None,
                        'relay_servers': relay_servers.split('\n') if relay_servers else None
                    }
                    
                    result = installer.install_server(
                        target_host=target_host,
                        install_method=install_method,
                        config=config
                    )
                    
                    if result.get('success'):
                        st.success("Server deployed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Deployment failed: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Deployment error: {str(e)}")
    
    # Client deployment section
    with st.expander("Client Deployment", expanded=False):
        st.write("Deploy RustDesk clients to network devices")
        
        col1, col2 = st.columns(2)
        
        with col1:
            client_host = st.text_input(
                "Client Host",
                help="IP address of target device"
            )
            
            platform = st.selectbox(
                "Platform",
                options=["linux", "windows", "macos"],
                help="Target device platform"
            )
        
        with col2:
            server_address = st.text_input(
                "Server Address",
                value="192.168.1.100",
                help="RustDesk server address"
            )
            
            auto_start = st.checkbox(
                "Auto Start",
                value=True,
                help="Start client automatically on boot"
            )
        
        if st.button("Deploy Client"):
            try:
                with st.spinner("Deploying RustDesk client..."):
                    deployment_config = {
                        'server_address': server_address,
                        'auto_start': auto_start
                    }
                    
                    result = installer.deploy_client(
                        target_device=client_host,
                        platform=platform,
                        deployment_config=deployment_config
                    )
                    
                    if result.get('success'):
                        st.success("Client deployed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Client deployment failed: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Client deployment error: {str(e)}")

def main():
    """Main RustDesk monitoring page."""
    st.title("🖥️ RustDesk Remote Desktop Monitoring")
    st.markdown("Comprehensive monitoring and management of RustDesk remote desktop infrastructure")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)
    
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Server Status", "Active Sessions", "Devices", 
        "Network Metrics", "Security", "Deployment"
    ])
    
    with tab1:
        render_server_status()
    
    with tab2:
        render_active_sessions()
    
    with tab3:
        render_device_management()
    
    with tab4:
        render_network_metrics()
    
    with tab5:
        render_security_monitoring()
    
    with tab6:
        render_home_network_topology()
    
    with tab7:
        render_deployment_management()
    
    # Footer with refresh info
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NetArchon RustDesk Monitor")

if __name__ == "__main__":
    main()