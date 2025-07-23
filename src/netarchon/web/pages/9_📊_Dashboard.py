"""
Comprehensive Visualization Dashboard

Omniscient network overview dashboard with device-specific views, trend analysis,
forecasting for capacity planning, and security monitoring with threat visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netarchon.monitoring.concurrent_collector import ConcurrentMetricCollector, MetricType, DeviceType
from netarchon.monitoring.storage_manager import MetricStorageManager, QueryFilter
from netarchon.monitoring.alert_manager import EnhancedAlertManager, AlertSeverity
from netarchon.integrations.rustdesk.home_network_integration import RustDeskHomeNetworkMonitor
from netarchon.utils.logger import get_logger
from netarchon.web.utils.security import require_authentication, validate_home_network

# Configure page
st.set_page_config(
    page_title="Network Dashboard - NetArchon",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Security validation
require_authentication()
validate_home_network()

logger = get_logger(__name__)

# Initialize components
@st.cache_resource
def get_dashboard_components():
    """Get cached dashboard components."""
    storage_manager = MetricStorageManager()
    collector = ConcurrentMetricCollector()
    alert_manager = EnhancedAlertManager(storage_manager)
    rustdesk_monitor = RustDeskHomeNetworkMonitor()
    
    return {
        'storage': storage_manager,
        'collector': collector,
        'alerts': alert_manager,
        'rustdesk': rustdesk_monitor
    }

def render_network_overview():
    """Render omniscient network overview dashboard."""
    st.header("🌐 Omniscient Network Overview")
    
    components = get_dashboard_components()
    storage = components['storage']
    collector = components['collector']
    alert_manager = components['alerts']
    
    # Time range selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        time_range = st.selectbox(
            "Time Range",
            options=[1, 6, 12, 24, 48, 168],  # hours
            format_func=lambda x: f"{x}h" if x < 24 else f"{x//24}d",
            index=3  # Default to 24 hours
        )
    
    with col2:
        auto_refresh = st.checkbox("Auto Refresh", value=True)
    
    with col3:
        if st.button("🔄 Refresh Now"):
            st.cache_resource.clear()
            st.rerun()
    
    # Auto refresh logic
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    try:
        # Get recent metrics
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range)
        
        filter_criteria = QueryFilter(
            start_time=start_time,
            end_time=end_time,
            limit=5000
        )
        
        metrics = storage.query_metrics(filter_criteria)
        
        if not metrics:
            st.warning("No metrics data available for the selected time range.")
            return
        
        # Network health overview
        render_network_health_overview(metrics, alert_manager)
        
        # Device status grid
        render_device_status_grid(metrics, collector)
        
        # Network topology visualization
        render_network_topology(metrics)
        
        # Real-time metrics stream
        render_realtime_metrics_stream(metrics)
        
        # Alert summary
        render_alert_summary(alert_manager)
        
    except Exception as e:
        st.error(f"Failed to load network overview: {str(e)}")
        logger.error(f"Network overview error: {e}")

def render_network_health_overview(metrics: List, alert_manager):
    """Render network health overview with key metrics."""
    st.subheader("🏥 Network Health Overview")
    
    # Calculate health metrics
    current_time = datetime.now()
    recent_metrics = [m for m in metrics if (current_time - m.timestamp).total_seconds() < 300]  # Last 5 minutes
    
    # Device connectivity status
    device_connectivity = {}
    for metric in recent_metrics:
        if metric.metric_type == MetricType.CONNECTIVITY and metric.metric_name == "reachable":
            device_connectivity[metric.device_id] = {
                'name': metric.device_name,
                'status': metric.value,
                'timestamp': metric.timestamp
            }
    
    # Calculate overall health score
    total_devices = len(device_connectivity)
    online_devices = sum(1 for d in device_connectivity.values() if d['status'])
    health_score = (online_devices / total_devices * 100) if total_devices > 0 else 0
    
    # Get active alerts
    active_alerts = alert_manager.get_active_alerts()
    critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
    warning_alerts = [a for a in active_alerts if a.severity == AlertSeverity.WARNING]
    
    # Health overview metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        health_color = "🟢" if health_score >= 90 else "🟡" if health_score >= 70 else "🔴"
        st.metric(
            "Network Health",
            f"{health_color} {health_score:.1f}%",
            help="Overall network health based on device connectivity"
        )
    
    with col2:
        st.metric(
            "Online Devices",
            f"{online_devices}/{total_devices}",
            help="Number of reachable devices"
        )
    
    with col3:
        st.metric(
            "Critical Alerts",
            len(critical_alerts),
            delta=f"-{len(critical_alerts)}" if critical_alerts else None,
            delta_color="inverse",
            help="Active critical alerts requiring immediate attention"
        )
    
    with col4:
        st.metric(
            "Warning Alerts", 
            len(warning_alerts),
            help="Active warning alerts"
        )
    
    with col5:
        # Calculate average latency
        latency_metrics = [m for m in recent_metrics if m.metric_type == MetricType.LATENCY]
        avg_latency = np.mean([float(m.value) for m in latency_metrics]) if latency_metrics else 0
        latency_color = "normal" if avg_latency < 50 else "inverse"
        st.metric(
            "Avg Latency",
            f"{avg_latency:.1f}ms",
            delta=f"{avg_latency - 30:.1f}ms" if avg_latency > 30 else None,
            delta_color=latency_color,
            help="Average network latency across all devices"
        )

def render_device_status_grid(metrics: List, collector):
    """Render device status grid with real-time information."""
    st.subheader("🖥️ Device Status Grid")
    
    # Get device status summary
    device_summary = collector.get_device_status_summary()
    
    if not device_summary.get('devices'):
        st.info("No device data available.")
        return
    
    # Create device status cards
    devices = device_summary['devices']
    cols = st.columns(min(3, len(devices)))  # Max 3 columns
    
    for idx, (device_id, device_info) in enumerate(devices.items()):
        col_idx = idx % len(cols)
        
        with cols[col_idx]:
            # Device status card
            is_reachable = device_info.get('reachable', False)
            status_color = "🟢" if is_reachable else "🔴"
            
            st.markdown(f"""
            <div style="
                border: 2px solid {'#28a745' if is_reachable else '#dc3545'};
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                background-color: {'#f8f9fa' if is_reachable else '#fff5f5'};
            ">
                <h4 style="margin: 0; color: {'#28a745' if is_reachable else '#dc3545'};">
                    {status_color} {device_info['name']}
                </h4>
                <p style="margin: 5px 0; font-size: 14px;">
                    <strong>Type:</strong> {device_info['type']}<br>
                    <strong>IP:</strong> {device_info['ip_address']}<br>
                    <strong>Status:</strong> {'Online' if is_reachable else 'Offline'}<br>
                    <strong>Metrics:</strong> {device_info['metrics_count']}<br>
                    <strong>Last Seen:</strong> {device_info.get('last_seen', 'Never')[:19] if device_info.get('last_seen') else 'Never'}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Device-specific quick actions
            if st.button(f"📊 View Details", key=f"details_{device_id}"):
                st.session_state['selected_device'] = device_id
                st.session_state['dashboard_tab'] = 'device_specific'
                st.rerun()

def render_network_topology(metrics: List):
    """Render network topology visualization."""
    st.subheader("🕸️ Network Topology")
    
    # Create network topology graph
    try:
        # Define home network topology
        topology_data = {
            'nodes': [
                {'id': 'internet', 'label': 'Internet', 'type': 'internet', 'color': '#007bff'},
                {'id': 'xfinity_gateway', 'label': 'Xfinity Gateway', 'type': 'gateway', 'color': '#28a745'},
                {'id': 'arris_s33', 'label': 'Arris S33 Modem', 'type': 'modem', 'color': '#ffc107'},
                {'id': 'netgear_orbi_router', 'label': 'Orbi Router', 'type': 'router', 'color': '#17a2b8'},
                {'id': 'netgear_orbi_satellite_1', 'label': 'Orbi Satellite 1', 'type': 'satellite', 'color': '#6c757d'},
                {'id': 'netgear_orbi_satellite_2', 'label': 'Orbi Satellite 2', 'type': 'satellite', 'color': '#6c757d'},
                {'id': 'mini_pc_server', 'label': 'Mini PC Server', 'type': 'server', 'color': '#dc3545'}
            ],
            'edges': [
                {'from': 'internet', 'to': 'xfinity_gateway'},
                {'from': 'xfinity_gateway', 'to': 'arris_s33'},
                {'from': 'arris_s33', 'to': 'netgear_orbi_router'},
                {'from': 'netgear_orbi_router', 'to': 'netgear_orbi_satellite_1'},
                {'from': 'netgear_orbi_router', 'to': 'netgear_orbi_satellite_2'},
                {'from': 'netgear_orbi_router', 'to': 'mini_pc_server'}
            ]
        }
        
        # Get device status for coloring
        current_time = datetime.now()
        recent_metrics = [m for m in metrics if (current_time - m.timestamp).total_seconds() < 300]
        
        device_status = {}
        for metric in recent_metrics:
            if metric.metric_type == MetricType.CONNECTIVITY and metric.metric_name == "reachable":
                device_status[metric.device_id] = metric.value
        
        # Create network diagram using plotly
        fig = go.Figure()
        
        # Add nodes
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        
        # Define positions for nodes (simplified layout)
        positions = {
            'internet': (0, 4),
            'xfinity_gateway': (0, 3),
            'arris_s33': (0, 2),
            'netgear_orbi_router': (0, 1),
            'netgear_orbi_satellite_1': (-2, 0),
            'netgear_orbi_satellite_2': (2, 0),
            'mini_pc_server': (0, 0)
        }
        
        for node in topology_data['nodes']:
            x, y = positions.get(node['id'], (0, 0))
            node_x.append(x)
            node_y.append(y)
            
            # Determine node color based on status
            if node['id'] in device_status:
                color = '#28a745' if device_status[node['id']] else '#dc3545'
            else:
                color = node['color']
            
            node_colors.append(color)
            node_text.append(node['label'])
        
        # Add edges
        edge_x = []
        edge_y = []
        
        for edge in topology_data['edges']:
            from_pos = positions.get(edge['from'], (0, 0))
            to_pos = positions.get(edge['to'], (0, 0))
            
            edge_x.extend([from_pos[0], to_pos[0], None])
            edge_y.extend([from_pos[1], to_pos[1], None])
        
        # Add edge trace
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines'
        ))
        
        # Add node trace
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            marker=dict(
                size=50,
                color=node_colors,
                line=dict(width=2, color='white')
            )
        ))
        
        fig.update_layout(
            title="Home Network Topology",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text="Green: Online, Red: Offline, Blue: External",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Failed to render network topology: {str(e)}")

def render_realtime_metrics_stream(metrics: List):
    """Render real-time metrics stream."""
    st.subheader("📈 Real-Time Metrics Stream")
    
    # Get recent metrics (last 30 minutes)
    current_time = datetime.now()
    recent_metrics = [
        m for m in metrics 
        if (current_time - m.timestamp).total_seconds() < 1800  # 30 minutes
    ]
    
    if not recent_metrics:
        st.info("No recent metrics available.")
        return
    
    # Create tabs for different metric types
    tab1, tab2, tab3, tab4 = st.tabs(["🔗 Connectivity", "⚡ Performance", "🖥️ System", "📡 Network"])
    
    with tab1:
        render_connectivity_metrics(recent_metrics)
    
    with tab2:
        render_performance_metrics(recent_metrics)
    
    with tab3:
        render_system_metrics(recent_metrics)
    
    with tab4:
        render_network_metrics(recent_metrics)

def render_connectivity_metrics(metrics: List):
    """Render connectivity metrics visualization."""
    # Filter connectivity metrics
    connectivity_metrics = [
        m for m in metrics 
        if m.metric_type in [MetricType.CONNECTIVITY, MetricType.LATENCY]
    ]
    
    if not connectivity_metrics:
        st.info("No connectivity metrics available.")
        return
    
    # Create DataFrame for plotting
    df_data = []
    for metric in connectivity_metrics:
        df_data.append({
            'timestamp': metric.timestamp,
            'device': metric.device_name,
            'metric': metric.metric_name,
            'value': float(metric.value) if metric.metric_name == 'ping_latency' else (1 if metric.value else 0),
            'unit': metric.unit
        })
    
    if not df_data:
        return
    
    df = pd.DataFrame(df_data)
    
    # Latency chart
    latency_df = df[df['metric'] == 'ping_latency']
    if not latency_df.empty:
        fig_latency = px.line(
            latency_df,
            x='timestamp',
            y='value',
            color='device',
            title='Network Latency Over Time',
            labels={'value': 'Latency (ms)', 'timestamp': 'Time'}
        )
        fig_latency.update_layout(height=300)
        st.plotly_chart(fig_latency, use_container_width=True)
    
    # Connectivity status
    connectivity_df = df[df['metric'] == 'reachable']
    if not connectivity_df.empty:
        # Create connectivity heatmap
        pivot_df = connectivity_df.pivot_table(
            index='device',
            columns='timestamp',
            values='value',
            fill_value=0
        )
        
        if not pivot_df.empty:
            fig_connectivity = px.imshow(
                pivot_df.values,
                x=[t.strftime('%H:%M') for t in pivot_df.columns],
                y=pivot_df.index,
                title='Device Connectivity Status',
                color_continuous_scale=['red', 'green'],
                aspect='auto'
            )
            fig_connectivity.update_layout(height=200)
            st.plotly_chart(fig_connectivity, use_container_width=True)def rend
er_performance_metrics(metrics: List):
    """Render performance metrics visualization."""
    from netarchon.web.components.dashboard_metrics import render_performance_metrics as render_perf
    render_perf(metrics)

def render_system_metrics(metrics: List):
    """Render system resource metrics visualization."""
    from netarchon.web.components.dashboard_metrics import render_system_metrics as render_sys
    render_sys(metrics)

def render_network_metrics(metrics: List):
    """Render network-specific metrics visualization."""
    from netarchon.web.components.dashboard_metrics import render_network_metrics as render_net
    render_net(metrics)

def render_alert_summary(alert_manager):
    """Render alert summary with recent alerts."""
    from netarchon.web.components.dashboard_metrics import render_alert_summary as render_alerts
    render_alerts(alert_manager)

def render_device_specific_dashboard():
    """Render device-specific dashboard."""
    st.header("🖥️ Device-Specific Dashboard")
    
    components = get_dashboard_components()
    storage = components['storage']
    collector = components['collector']
    
    # Device selector
    device_summary = collector.get_device_status_summary()
    devices = device_summary.get('devices', {})
    
    if not devices:
        st.warning("No devices available for detailed view.")
        return
    
    # Device selection
    selected_device = st.selectbox(
        "Select Device",
        options=list(devices.keys()),
        format_func=lambda x: devices[x]['name'],
        index=0
    )
    
    if not selected_device:
        return
    
    device_info = devices[selected_device]
    
    # Device header
    st.subheader(f"📊 {device_info['name']} Dashboard")
    
    # Device status overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_icon = "🟢" if device_info['reachable'] else "🔴"
        st.metric("Status", f"{status_icon} {'Online' if device_info['reachable'] else 'Offline'}")
    
    with col2:
        st.metric("Device Type", device_info['type'].replace('_', ' ').title())
    
    with col3:
        st.metric("IP Address", device_info['ip_address'])
    
    with col4:
        st.metric("Metrics Count", device_info['metrics_count'])
    
    # Time range for device metrics
    time_range = st.selectbox(
        "Time Range",
        options=[1, 6, 12, 24, 48],
        format_func=lambda x: f"{x}h",
        index=2,
        key="device_time_range"
    )
    
    # Get device-specific metrics
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=time_range)
    
    filter_criteria = QueryFilter(
        device_ids=[selected_device],
        start_time=start_time,
        end_time=end_time,
        limit=2000
    )
    
    device_metrics = storage.query_metrics(filter_criteria)
    
    if not device_metrics:
        st.info(f"No metrics available for {device_info['name']} in the selected time range.")
        return
    
    # Device-specific visualizations based on device type
    device_type = device_info['type']
    
    if device_type == 'arris_s33_modem':
        render_arris_s33_dashboard(device_metrics)
    elif device_type == 'netgear_orbi_router':
        render_netgear_orbi_dashboard(device_metrics)
    elif device_type == 'mini_pc_server':
        render_mini_pc_dashboard(device_metrics)
    elif device_type == 'xfinity_gateway':
        render_xfinity_gateway_dashboard(device_metrics)
    else:
        render_generic_device_dashboard(device_metrics)

def render_arris_s33_dashboard(metrics: List):
    """Render Arris S33 DOCSIS modem dashboard."""
    st.subheader("📡 DOCSIS 3.1 Modem Metrics")
    
    # Filter DOCSIS metrics
    docsis_metrics = [m for m in metrics if m.metric_type == MetricType.DOCSIS]
    
    if docsis_metrics:
        # Create DataFrame
        df_data = []
        for metric in docsis_metrics:
            try:
                df_data.append({
                    'timestamp': metric.timestamp,
                    'metric': metric.metric_name,
                    'value': float(metric.value),
                    'unit': metric.unit
                })
            except (ValueError, TypeError):
                continue
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # SNR Chart
            snr_df = df[df['metric'] == 'snr']
            if not snr_df.empty:
                fig_snr = px.line(
                    snr_df,
                    x='timestamp',
                    y='value',
                    title='Signal-to-Noise Ratio (SNR)',
                    labels={'value': 'SNR (dB)', 'timestamp': 'Time'}
                )
                fig_snr.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Minimum Threshold")
                fig_snr.add_hline(y=35, line_dash="dash", line_color="orange", annotation_text="Good Threshold")
                st.plotly_chart(fig_snr, use_container_width=True)
            
            # Power Levels Chart
            power_df = df[df['metric'].isin(['downstream_power', 'upstream_power'])]
            if not power_df.empty:
                fig_power = px.line(
                    power_df,
                    x='timestamp',
                    y='value',
                    color='metric',
                    title='DOCSIS Power Levels',
                    labels={'value': 'Power (dBmV)', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_power, use_container_width=True)
            
            # Current values summary
            st.subheader("📊 Current DOCSIS Status")
            
            latest_metrics = {}
            for metric in docsis_metrics:
                if metric.metric_name not in latest_metrics or metric.timestamp > latest_metrics[metric.metric_name]['timestamp']:
                    latest_metrics[metric.metric_name] = {
                        'value': metric.value,
                        'unit': metric.unit,
                        'timestamp': metric.timestamp
                    }
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'snr' in latest_metrics:
                    snr_val = float(latest_metrics['snr']['value'])
                    snr_status = "🟢 Good" if snr_val >= 35 else "🟡 Fair" if snr_val >= 30 else "🔴 Poor"
                    st.metric("SNR", f"{snr_val} dB", help=f"Status: {snr_status}")
            
            with col2:
                if 'downstream_power' in latest_metrics:
                    ds_power = float(latest_metrics['downstream_power']['value'])
                    st.metric("Downstream Power", f"{ds_power} dBmV")
            
            with col3:
                if 'upstream_power' in latest_metrics:
                    us_power = float(latest_metrics['upstream_power']['value'])
                    st.metric("Upstream Power", f"{us_power} dBmV")
    
    # Connectivity metrics
    connectivity_metrics = [m for m in metrics if m.metric_type == MetricType.CONNECTIVITY]
    if connectivity_metrics:
        st.subheader("🔗 Connectivity Status")
        
        # Uptime calculation
        reachable_metrics = [m for m in connectivity_metrics if m.metric_name == 'reachable']
        if reachable_metrics:
            total_checks = len(reachable_metrics)
            successful_checks = sum(1 for m in reachable_metrics if m.value)
            uptime_percentage = (successful_checks / total_checks * 100) if total_checks > 0 else 0
            
            st.metric("Uptime", f"{uptime_percentage:.2f}%")

def render_mini_pc_dashboard(metrics: List):
    """Render Mini PC Ubuntu server dashboard."""
    st.subheader("🖥️ Ubuntu Server Metrics")
    
    # Filter system metrics
    system_metrics = [m for m in metrics if m.metric_type == MetricType.SYSTEM_RESOURCES]
    
    if system_metrics:
        # Create DataFrame
        df_data = []
        for metric in system_metrics:
            try:
                if metric.metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                    df_data.append({
                        'timestamp': metric.timestamp,
                        'metric': metric.metric_name,
                        'value': float(metric.value),
                        'unit': metric.unit
                    })
                elif metric.metric_name == 'docker_containers':
                    df_data.append({
                        'timestamp': metric.timestamp,
                        'metric': metric.metric_name,
                        'value': int(metric.value),
                        'unit': 'count'
                    })
            except (ValueError, TypeError):
                continue
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # Resource usage charts
            for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                metric_df = df[df['metric'] == metric_name]
                if not metric_df.empty:
                    fig = px.line(
                        metric_df,
                        x='timestamp',
                        y='value',
                        title=f'{metric_name.replace("_", " ").title()} Over Time',
                        labels={'value': f'{metric_name.replace("_", " ").title()} (%)', 'timestamp': 'Time'}
                    )
                    
                    # Add threshold lines
                    if metric_name == 'cpu_usage':
                        fig.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="Warning")
                    elif metric_name == 'memory_usage':
                        fig.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Critical")
                    elif metric_name == 'disk_usage':
                        fig.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="Warning")
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            # Docker containers chart
            docker_df = df[df['metric'] == 'docker_containers']
            if not docker_df.empty:
                fig_docker = px.line(
                    docker_df,
                    x='timestamp',
                    y='value',
                    title='Docker Containers Over Time',
                    labels={'value': 'Number of Containers', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_docker, use_container_width=True)
            
            # Current system status
            st.subheader("💻 Current System Status")
            
            latest_metrics = {}
            for metric in system_metrics:
                if metric.metric_name not in latest_metrics or metric.timestamp > latest_metrics[metric.metric_name]['timestamp']:
                    latest_metrics[metric.metric_name] = {
                        'value': metric.value,
                        'unit': metric.unit,
                        'timestamp': metric.timestamp
                    }
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if 'cpu_usage' in latest_metrics:
                    cpu_val = float(latest_metrics['cpu_usage']['value'])
                    cpu_delta = f"+{cpu_val - 50:.1f}%" if cpu_val > 50 else None
                    st.metric("CPU Usage", f"{cpu_val:.1f}%", delta=cpu_delta, delta_color="inverse" if cpu_val > 85 else "normal")
            
            with col2:
                if 'memory_usage' in latest_metrics:
                    mem_val = float(latest_metrics['memory_usage']['value'])
                    mem_delta = f"+{mem_val - 60:.1f}%" if mem_val > 60 else None
                    st.metric("Memory Usage", f"{mem_val:.1f}%", delta=mem_delta, delta_color="inverse" if mem_val > 90 else "normal")
            
            with col3:
                if 'disk_usage' in latest_metrics:
                    disk_val = float(latest_metrics['disk_usage']['value'])
                    st.metric("Disk Usage", f"{disk_val:.1f}%", delta_color="inverse" if disk_val > 85 else "normal")
            
            with col4:
                if 'docker_containers' in latest_metrics:
                    containers = int(latest_metrics['docker_containers']['value'])
                    st.metric("Docker Containers", containers)

def render_generic_device_dashboard(metrics: List):
    """Render generic device dashboard."""
    st.subheader("📊 Device Metrics")
    
    # Group metrics by type
    metric_types = {}
    for metric in metrics:
        metric_type = metric.metric_type.value
        if metric_type not in metric_types:
            metric_types[metric_type] = []
        metric_types[metric_type].append(metric)
    
    # Display metrics by type
    for metric_type, type_metrics in metric_types.items():
        st.subheader(f"📈 {metric_type.replace('_', ' ').title()} Metrics")
        
        # Create simple time series for numeric metrics
        df_data = []
        for metric in type_metrics:
            try:
                value = float(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': metric.unit
                })
            except (ValueError, TypeError):
                continue
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # Create chart for each metric
            for metric_name in df['metric'].unique():
                metric_df = df[df['metric'] == metric_name]
                if not metric_df.empty:
                    fig = px.line(
                        metric_df,
                        x='timestamp',
                        y='value',
                        title=f'{metric_name.replace("_", " ").title()} Over Time',
                        labels={'value': f'{metric_name} ({metric_df.iloc[0]["unit"]})', 'timestamp': 'Time'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

def render_capacity_planning():
    """Render capacity planning dashboard."""
    st.header("📊 Capacity Planning & Forecasting")
    
    components = get_dashboard_components()
    storage = components['storage']
    
    # Get recent metrics for analysis
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=168)  # 7 days
    
    filter_criteria = QueryFilter(
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    metrics = storage.query_metrics(filter_criteria)
    
    if not metrics:
        st.warning("No metrics data available for capacity planning.")
        return
    
    from netarchon.web.components.dashboard_metrics import render_capacity_planning as render_capacity
    render_capacity(metrics, storage)

def render_security_dashboard():
    """Render security monitoring dashboard."""
    st.header("🔒 Security Monitoring Dashboard")
    
    components = get_dashboard_components()
    storage = components['storage']
    alert_manager = components['alerts']
    
    # Get recent metrics
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    filter_criteria = QueryFilter(
        start_time=start_time,
        end_time=end_time,
        limit=5000
    )
    
    metrics = storage.query_metrics(filter_criteria)
    
    from netarchon.web.components.dashboard_metrics import render_security_dashboard as render_security
    render_security(metrics, alert_manager)

def main():
    """Main dashboard application."""
    st.title("📊 NetArchon Comprehensive Dashboard")
    st.markdown("Omniscient network monitoring and visualization platform")
    
    # Sidebar navigation
    st.sidebar.title("🧭 Dashboard Navigation")
    
    dashboard_options = {
        "🌐 Network Overview": "network_overview",
        "🖥️ Device-Specific": "device_specific", 
        "📊 Capacity Planning": "capacity_planning",
        "🔒 Security Monitoring": "security_dashboard"
    }
    
    selected_dashboard = st.sidebar.selectbox(
        "Select Dashboard",
        options=list(dashboard_options.keys()),
        index=0
    )
    
    dashboard_key = dashboard_options[selected_dashboard]
    
    # Dashboard routing
    if dashboard_key == "network_overview":
        render_network_overview()
    elif dashboard_key == "device_specific":
        render_device_specific_dashboard()
    elif dashboard_key == "capacity_planning":
        render_capacity_planning()
    elif dashboard_key == "security_dashboard":
        render_security_dashboard()
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NetArchon Comprehensive Dashboard")

if __name__ == "__main__":
    main()