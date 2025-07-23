"""
NetArchon Dashboard Page

Home network overview with real-time status and key metrics.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import time
import sys
from pathlib import Path

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from netarchon.web.utils.data_loader import get_data_loader
from netarchon.web.utils.security import require_authentication, get_security_manager
from netarchon.web.components.home_network import render_home_network_security, render_firewall_management

# Page configuration
st.set_page_config(
    page_title="NetArchon - Dashboard",
    page_icon="🏠",
    layout="wide"
)

def create_gauge_chart(value, title, max_value=100, color="blue"):
    """Create a gauge chart for metrics display."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': max_value * 0.7},
        gauge = {
            'axis': {'range': [None, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "lightgray"},
                {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_bandwidth_chart():
    """Create bandwidth utilization chart."""
    # Sample data for the last 24 hours
    times = pd.date_range(start=datetime.now() - timedelta(hours=24), 
                         end=datetime.now(), freq='1H')
    
    # Simulate bandwidth data
    download = [45 + 20 * (i % 3) + 10 * (i % 7) for i in range(len(times))]
    upload = [15 + 10 * (i % 4) + 5 * (i % 5) for i in range(len(times))]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=times, y=download,
        mode='lines+markers',
        name='Download (Mbps)',
        line=dict(color='#1f77b4', width=2),
        fill='tonexty'
    ))
    
    fig.add_trace(go.Scatter(
        x=times, y=upload,
        mode='lines+markers',
        name='Upload (Mbps)',
        line=dict(color='#ff7f0e', width=2),
        fill='tozeroy'
    ))
    
    fig.update_layout(
        title="Bandwidth Utilization (24h)",
        xaxis_title="Time",
        yaxis_title="Speed (Mbps)",
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_device_status_chart(devices):
    """Create device status pie chart."""
    status_counts = {}
    for device in devices:
        status = device.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(status_counts.keys()),
        values=list(status_counts.values()),
        hole=.3,
        marker_colors=['#28a745', '#dc3545', '#ffc107', '#6c757d']
    )])
    
    fig.update_layout(
        title="Device Status Overview",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def render_home_network_status():
    """Render the home network status section."""
    st.subheader("🏠 Home Network Status")
    
    # Get data loader
    data_loader = get_data_loader()
    
    # Load device data
    devices = data_loader.load_discovered_devices()
    home_devices = [d for d in devices if d.get('is_home_device', False)]
    
    # Create columns for each home device
    cols = st.columns(len(home_devices))
    
    for i, device in enumerate(home_devices):
        with cols[i]:
            # Device status card
            status = device.get('status', 'unknown')
            status_color = {
                'online': '#28a745',
                'offline': '#dc3545', 
                'warning': '#ffc107'
            }.get(status, '#6c757d')
            
            st.markdown(f"""
            <div style="
                border: 2px solid {status_color};
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <h4 style="margin: 0; color: #333;">{device['name']}</h4>
                <p style="margin: 5px 0; color: {status_color}; font-weight: bold;">
                    ● {status.upper()}
                </p>
                <p style="margin: 0; font-size: 0.9em; color: #666;">
                    {device['vendor']} {device['model']}<br>
                    {device['ip_address']}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Load device metrics if available
            metrics = data_loader.load_device_metrics(device['id'])
            if 'system_metrics' in metrics:
                cpu = metrics['system_metrics'].get('cpu_usage', 0)
                memory = metrics['system_metrics'].get('memory_usage', 0)
                
                st.metric("CPU Usage", f"{cpu:.1f}%", 
                         delta=f"{cpu-50:.1f}%" if cpu > 50 else None)
                st.metric("Memory", f"{memory:.1f}%",
                         delta=f"{memory-60:.1f}%" if memory > 60 else None)

def render_network_overview():
    """Render network overview metrics."""
    st.subheader("📊 Network Overview")
    
    # Get data loader
    data_loader = get_data_loader()
    devices = data_loader.load_discovered_devices()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_devices = len(devices)
        st.metric("Total Devices", total_devices, delta=1)
    
    with col2:
        online_devices = len([d for d in devices if d.get('status') == 'online'])
        st.metric("Online Devices", online_devices, delta=0)
    
    with col3:
        # Simulate current bandwidth
        current_bandwidth = 47.3
        st.metric("Current Download", f"{current_bandwidth} Mbps", delta="5.2 Mbps")
    
    with col4:
        # Simulate uptime
        uptime_hours = 168  # 7 days
        st.metric("Network Uptime", f"{uptime_hours}h", delta="24h")

def render_performance_dashboard():
    """Render performance dashboard with charts."""
    st.subheader("📈 Performance Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Bandwidth chart
        bandwidth_fig = create_bandwidth_chart()
        st.plotly_chart(bandwidth_fig, use_container_width=True)
    
    with col2:
        # Device status chart
        data_loader = get_data_loader()
        devices = data_loader.load_discovered_devices()
        status_fig = create_device_status_chart(devices)
        st.plotly_chart(status_fig, use_container_width=True)

def render_gauge_metrics():
    """Render gauge metrics for key network parameters."""
    st.subheader("🎛️ Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Internet connectivity gauge
        internet_health = 95.2
        fig = create_gauge_chart(internet_health, "Internet Health (%)", 100, "green")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # WiFi signal strength
        wifi_strength = 78.5
        fig = create_gauge_chart(wifi_strength, "WiFi Signal (%)", 100, "blue")
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        # Network latency (inverted - lower is better)
        latency = 12.5  # ms
        latency_score = max(0, 100 - latency * 2)  # Convert to score
        fig = create_gauge_chart(latency_score, "Response Time", 100, "orange")
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Overall network score
        network_score = 88.7
        fig = create_gauge_chart(network_score, "Network Score", 100, "purple")
        st.plotly_chart(fig, use_container_width=True)

def render_recent_activity():
    """Render recent network activity."""
    st.subheader("📋 Recent Activity")
    
    # Sample activity data
    activities = [
        {"time": "2 minutes ago", "event": "Configuration backup completed", "device": "Netgear Orbi", "status": "success"},
        {"time": "15 minutes ago", "event": "New device connected", "device": "iPhone-14", "status": "info"},
        {"time": "1 hour ago", "event": "Bandwidth threshold alert", "device": "Xfinity Gateway", "status": "warning"},
        {"time": "3 hours ago", "event": "Firmware update available", "device": "Netgear Orbi", "status": "info"},
        {"time": "6 hours ago", "event": "Weekly backup scheduled", "device": "All Devices", "status": "success"}
    ]
    
    for activity in activities:
        status_color = {
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
            'info': '#17a2b8'
        }.get(activity['status'], '#6c757d')
        
        st.markdown(f"""
        <div style="
            border-left: 4px solid {status_color};
            padding: 10px 15px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        ">
            <strong>{activity['event']}</strong><br>
            <small style="color: #666;">
                {activity['device']} • {activity['time']}
            </small>
        </div>
        """, unsafe_allow_html=True)

@require_authentication
def main():
    """Main dashboard page function with security."""
    
    # Page header with security status
    security_manager = get_security_manager()
    username = st.session_state.get('username', 'User')
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown("""
        <div style="
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        ">
            <h1 style="margin: 0;">🏠 NetArchon Dashboard</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">
                Your Secure Home Network Command Center
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: rgba(102, 126, 234, 0.1);
            border: 1px solid rgba(102, 126, 234, 0.3);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        ">
            <small>🔒 Secure Session</small><br>
            <strong>{username}</strong><br>
            <small>{security_manager.get_client_ip()}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Auto-refresh mechanism
    if st.button("🔄 Refresh Dashboard", type="primary"):
        st.rerun()
    
    # Home Network Security Monitoring
    st.markdown("---")
    
    # Create tabs for different security views
    security_tab, monitoring_tab, firewall_tab = st.tabs([
        "🔒 Security Overview", 
        "📊 Network Monitoring", 
        "🔥 Firewall Management"
    ])
    
    with security_tab:
        render_home_network_security()
    
    with monitoring_tab:
        # Home network status
        render_home_network_status()
        
        st.markdown("---")
        
        # Network overview
        render_network_overview()
        
        st.markdown("---")
        
        # Performance dashboard
        render_performance_dashboard()
        
        st.markdown("---")
        
        # Gauge metrics
        render_gauge_metrics()
    
    with firewall_tab:
        render_firewall_management()
    
    st.markdown("---")
    
    # Recent activity
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_recent_activity()
    
    with col2:
        # Quick actions panel
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔍 Run Network Scan", use_container_width=True):
            with st.spinner("Scanning network..."):
                time.sleep(2)
            st.success("Network scan completed!")
        
        if st.button("💾 Backup All Configs", use_container_width=True):
            with st.spinner("Creating backups..."):
                time.sleep(3)
            st.success("All configurations backed up!")
        
        if st.button("📊 Generate Report", use_container_width=True):
            with st.spinner("Generating report..."):
                time.sleep(2)
            st.success("Network report generated!")
        
        if st.button("🔧 Health Check", use_container_width=True):
            with st.spinner("Running health check..."):
                time.sleep(2)
            st.success("All systems operational!")
    
    # Auto-refresh timer (refresh every 30 seconds)
    time.sleep(1)

if __name__ == "__main__":
    main()