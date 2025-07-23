"""
NetArchon Monitoring Page

Real-time monitoring dashboard with interactive charts and performance metrics.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sys
from pathlib import Path

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from netarchon.web.utils.data_loader import get_data_loader

# Page configuration
st.set_page_config(
    page_title="NetArchon - Monitoring",
    page_icon="📊",
    layout="wide"
)

def generate_time_series_data(hours=24, interval_minutes=5):
    """Generate sample time series data for monitoring."""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # Create time range
    time_range = pd.date_range(start=start_time, end=end_time, 
                              freq=f'{interval_minutes}min')
    
    # Generate sample data with realistic patterns
    np.random.seed(42)  # For consistent demo data
    
    data = []
    for i, timestamp in enumerate(time_range):
        # Simulate daily usage patterns
        hour = timestamp.hour
        base_multiplier = 1.0
        
        # Higher usage during day hours (8-22)
        if 8 <= hour <= 22:
            base_multiplier = 1.5 + 0.3 * np.sin((hour - 8) * np.pi / 14)
        else:
            base_multiplier = 0.3 + 0.2 * np.random.random()
        
        # Add some noise and trends
        noise = np.random.normal(0, 0.1)
        
        data.append({
            'timestamp': timestamp,
            'cpu_usage': max(0, min(100, 30 + 20 * base_multiplier + 10 * noise)),
            'memory_usage': max(0, min(100, 45 + 25 * base_multiplier + 15 * noise)),
            'bandwidth_in': max(0, 50 + 30 * base_multiplier + 20 * noise),
            'bandwidth_out': max(0, 20 + 15 * base_multiplier + 10 * noise),
            'latency': max(1, 15 + 5 * (1/base_multiplier) + 3 * noise),
            'packet_loss': max(0, min(5, 0.1 + 0.5 * (1/base_multiplier) + 0.3 * noise))
        })
    
    return pd.DataFrame(data)

def create_real_time_cpu_memory_chart(df):
    """Create real-time CPU and memory usage chart."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('CPU Usage (%)', 'Memory Usage (%)'),
        vertical_spacing=0.1
    )
    
    # CPU usage
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['cpu_usage'],
            mode='lines',
            name='CPU Usage',
            line=dict(color='#FF6B6B', width=2),
            fill='tonexty'
        ),
        row=1, col=1
    )
    
    # Memory usage
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['memory_usage'],
            mode='lines',
            name='Memory Usage',
            line=dict(color='#4ECDC4', width=2),
            fill='tonexty'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="System Performance Metrics",
        height=500,
        showlegend=False,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="CPU %", row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text="Memory %", row=2, col=1, range=[0, 100])
    
    return fig

def create_bandwidth_chart(df):
    """Create bandwidth utilization chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['bandwidth_in'],
        mode='lines',
        name='Download (Mbps)',
        line=dict(color='#45B7D1', width=2),
        fill='tonexty'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['bandwidth_out'],
        mode='lines',
        name='Upload (Mbps)',
        line=dict(color='#FFA07A', width=2),
        fill='tozeroy'
    ))
    
    fig.update_layout(
        title="Bandwidth Utilization",
        xaxis_title="Time",
        yaxis_title="Speed (Mbps)",
        height=400,
        hovermode='x unified',
        legend=dict(x=0, y=1)
    )
    
    return fig

def create_network_quality_chart(df):
    """Create network quality metrics chart."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Latency (ms)', 'Packet Loss (%)'),
        vertical_spacing=0.15
    )
    
    # Latency
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['latency'],
            mode='lines+markers',
            name='Latency',
            line=dict(color='#FF9500', width=2),
            marker=dict(size=3)
        ),
        row=1, col=1
    )
    
    # Packet loss
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['packet_loss'],
            mode='lines+markers',
            name='Packet Loss',
            line=dict(color='#FF3B30', width=2),
            marker=dict(size=3)
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="Network Quality Metrics",
        height=500,
        showlegend=False,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Latency (ms)", row=1, col=1)
    fig.update_yaxes(title_text="Packet Loss (%)", row=2, col=1, range=[0, 5])
    
    return fig

def create_interface_utilization_heatmap():
    """Create interface utilization heatmap."""
    # Sample interface data
    interfaces = ['GigE0/0/1', 'GigE0/0/2', 'GigE0/0/3', 'WiFi-2.4G', 'WiFi-5G']
    hours = [f"{i:02d}:00" for i in range(24)]
    
    # Generate sample utilization data
    np.random.seed(42)
    data = np.random.rand(len(interfaces), len(hours)) * 100
    
    # Add some patterns
    for i, interface in enumerate(interfaces):
        if 'WiFi' in interface:
            # WiFi has higher usage during day
            for j, hour in enumerate(hours):
                if 8 <= int(hour.split(':')[0]) <= 22:
                    data[i][j] = min(95, data[i][j] + 30)
        else:
            # Ethernet more consistent
            data[i] = data[i] * 0.6 + 20
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=hours,
        y=interfaces,
        colorscale='RdYlGn_r',
        colorbar=dict(title="Utilization %")
    ))
    
    fig.update_layout(
        title="Interface Utilization Heatmap (24h)",
        xaxis_title="Hour of Day",
        yaxis_title="Interface",
        height=400
    )
    
    return fig

def render_device_selector():
    """Render device selection for monitoring."""
    data_loader = get_data_loader()
    devices = data_loader.load_discovered_devices()
    
    if not devices:
        st.warning("No devices available for monitoring.")
        return None
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        device_options = [f"{d['name']} ({d['ip_address']})" for d in devices]
        selected_idx = st.selectbox(
            "Select Device to Monitor",
            range(len(device_options)),
            format_func=lambda x: device_options[x] if x < len(device_options) else "No devices"
        )
        
        selected_device = devices[selected_idx] if selected_idx < len(devices) else None
    
    with col2:
        time_range = st.selectbox(
            "Time Range",
            ["Last 1 hour", "Last 6 hours", "Last 24 hours", "Last 7 days"]
        )
    
    with col3:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
    
    return {
        'device': selected_device,
        'time_range': time_range,
        'auto_refresh': auto_refresh
    }

def render_key_metrics(device):
    """Render key performance metrics cards."""
    data_loader = get_data_loader()
    
    if device:
        metrics = data_loader.load_device_metrics(device['id'])
        
        if 'system_metrics' in metrics:
            system = metrics['system_metrics']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                cpu = system.get('cpu_usage', 0)
                cpu_delta = f"+{cpu-50:.1f}%" if cpu > 50 else f"{cpu-50:.1f}%"
                st.metric("CPU Usage", f"{cpu:.1f}%", delta=cpu_delta)
            
            with col2:
                memory = system.get('memory_usage', 0)
                memory_delta = f"+{memory-60:.1f}%" if memory > 60 else f"{memory-60:.1f}%"
                st.metric("Memory Usage", f"{memory:.1f}%", delta=memory_delta)
            
            with col3:
                temp = system.get('temperature', 0)
                if temp > 0:
                    temp_status = "🔥" if temp > 70 else "🟢"
                    st.metric("Temperature", f"{temp:.1f}°C", delta=temp_status)
                else:
                    st.metric("Temperature", "N/A")
            
            with col4:
                uptime = system.get('uptime', 0)
                uptime_days = uptime // 86400
                st.metric("Uptime", f"{uptime_days} days")
        
        # Network specific metrics
        if 'docsis_metrics' in metrics:
            st.subheader("📡 Cable Modem Metrics")
            docsis = metrics['docsis_metrics']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                downstream = docsis.get('downstream_power', 0)
                downstream_status = "🟢" if -15 <= downstream <= 15 else "🟡"
                st.metric("Downstream Power", f"{downstream:.1f} dBmV", delta=downstream_status)
            
            with col2:
                upstream = docsis.get('upstream_power', 0)
                upstream_status = "🟢" if 35 <= upstream <= 50 else "🟡"
                st.metric("Upstream Power", f"{upstream:.1f} dBmV", delta=upstream_status)
            
            with col3:
                snr = docsis.get('snr', 0)
                snr_status = "🟢" if snr >= 30 else "🟡" if snr >= 25 else "🔴"
                st.metric("SNR", f"{snr:.1f} dB", delta=snr_status)
            
            with col4:
                channels = docsis.get('downstream_channels', 0)
                st.metric("DS Channels", channels)
        
        elif 'wifi_metrics' in metrics:
            st.subheader("📶 WiFi Router Metrics")
            wifi = metrics['wifi_metrics']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                clients = wifi.get('connected_clients', 0)
                st.metric("Connected Clients", clients)
            
            with col2:
                signal_2g = wifi.get('signal_strength_2g', 0)
                signal_2g_status = "🟢" if signal_2g > -50 else "🟡" if signal_2g > -70 else "🔴"
                st.metric("2.4GHz Signal", f"{signal_2g} dBm", delta=signal_2g_status)
            
            with col3:
                signal_5g = wifi.get('signal_strength_5g', 0)
                signal_5g_status = "🟢" if signal_5g > -50 else "🟡" if signal_5g > -70 else "🔴"
                st.metric("5GHz Signal", f"{signal_5g} dBm", delta=signal_5g_status)
            
            with col4:
                mesh_status = wifi.get('mesh_status', 'unknown')
                mesh_icon = "🟢" if mesh_status == 'optimal' else "🟡"
                st.metric("Mesh Status", mesh_status.title(), delta=mesh_icon)

def render_alert_panel():
    """Render active alerts panel."""
    st.subheader("🚨 Active Alerts")
    
    # Sample alerts
    alerts = [
        {
            "severity": "warning",
            "device": "Xfinity Gateway",
            "message": "High bandwidth utilization detected",
            "time": "2 minutes ago",
            "metric": "Bandwidth: 85%"
        },
        {
            "severity": "info",
            "device": "Netgear Orbi",
            "message": "New client connected",
            "time": "15 minutes ago",
            "metric": "Clients: 13"
        },
        {
            "severity": "error",
            "device": "Mini PC Server",
            "message": "High temperature alert",
            "time": "1 hour ago",
            "metric": "Temperature: 78°C"
        }
    ]
    
    for alert in alerts:
        severity_color = {
            'error': '#FF3B30',
            'warning': '#FF9500',
            'info': '#007AFF'
        }
        
        severity_icon = {
            'error': '🔴',
            'warning': '🟡',
            'info': '🔵'
        }
        
        color = severity_color.get(alert['severity'], '#6C757D')
        icon = severity_icon.get(alert['severity'], '⚪')
        
        st.markdown(f"""
        <div style="
            border-left: 4px solid {color};
            padding: 10px 15px;
            margin: 5px 0;
            background: rgba(255,255,255,0.9);
            border-radius: 0 5px 5px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; justify-content: between; align-items: center;">
                <div>
                    <strong>{icon} {alert['message']}</strong><br>
                    <small style="color: #666;">
                        {alert['device']} • {alert['time']} • {alert['metric']}
                    </small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main monitoring page function."""
    
    # Page header
    st.markdown("""
    <div style="
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    ">
        <h1 style="margin: 0;">📊 Network Monitoring</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">
            Real-time performance monitoring and analytics
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Device selector
    monitoring_config = render_device_selector()
    
    if not monitoring_config or not monitoring_config['device']:
        st.stop()
    
    device = monitoring_config['device']
    
    # Auto-refresh setup
    if monitoring_config['auto_refresh']:
        if st.button("🔄 Refresh Data", key="auto_refresh"):
            st.rerun()
        
        # Auto-refresh every 30 seconds
        time.sleep(1)
    
    # Key metrics cards
    render_key_metrics(device)
    
    st.markdown("---")
    
    # Main monitoring charts
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Generate sample data based on time range
        time_ranges = {
            "Last 1 hour": 1,
            "Last 6 hours": 6,
            "Last 24 hours": 24,
            "Last 7 days": 168
        }
        
        hours = time_ranges.get(monitoring_config['time_range'], 24)
        df = generate_time_series_data(hours=hours)
        
        # System performance chart
        cpu_memory_fig = create_real_time_cpu_memory_chart(df)
        st.plotly_chart(cpu_memory_fig, use_container_width=True)
        
        # Bandwidth chart
        bandwidth_fig = create_bandwidth_chart(df)
        st.plotly_chart(bandwidth_fig, use_container_width=True)
        
        # Network quality chart
        quality_fig = create_network_quality_chart(df)
        st.plotly_chart(quality_fig, use_container_width=True)
    
    with col2:
        # Alert panel
        render_alert_panel()
        
        st.markdown("---")
        
        # Quick stats
        st.subheader("📈 Quick Stats")
        
        # Calculate stats from sample data
        avg_cpu = df['cpu_usage'].mean()
        max_bandwidth = df['bandwidth_in'].max()
        avg_latency = df['latency'].mean()
        
        st.metric("Avg CPU", f"{avg_cpu:.1f}%")
        st.metric("Peak Download", f"{max_bandwidth:.1f} Mbps")
        st.metric("Avg Latency", f"{avg_latency:.1f} ms")
        
        st.markdown("---")
        
        # Export options
        st.subheader("📤 Export Data")
        
        if st.button("📊 Generate Report", use_container_width=True):
            with st.spinner("Generating monitoring report..."):
                time.sleep(2)
            st.success("Report generated!")
        
        if st.button("📥 Export CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"monitoring_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    st.markdown("---")
    
    # Additional monitoring sections
    col1, col2 = st.columns(2)
    
    with col1:
        # Interface utilization heatmap
        heatmap_fig = create_interface_utilization_heatmap()
        st.plotly_chart(heatmap_fig, use_container_width=True)
    
    with col2:
        # Top talkers/applications
        st.subheader("🔝 Top Network Applications")
        
        app_data = [
            {"Application": "Web Browsing", "Bandwidth": "45.2 Mbps", "Percentage": 68},
            {"Application": "Video Streaming", "Bandwidth": "12.8 Mbps", "Percentage": 19},
            {"Application": "File Downloads", "Bandwidth": "5.4 Mbps", "Percentage": 8},
            {"Application": "Video Calls", "Bandwidth": "2.1 Mbps", "Percentage": 3},
            {"Application": "Other", "Bandwidth": "1.5 Mbps", "Percentage": 2}
        ]
        
        app_df = pd.DataFrame(app_data)
        
        # Create pie chart
        fig = px.pie(app_df, values='Percentage', names='Application',
                    title="Bandwidth by Application")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Performance summary table
    st.subheader("📋 Performance Summary")
    
    summary_data = {
        'Metric': ['CPU Usage', 'Memory Usage', 'Download Speed', 'Upload Speed', 'Latency', 'Packet Loss'],
        'Current': ['15.2%', '68.4%', '47.3 Mbps', '12.1 Mbps', '18.5 ms', '0.02%'],
        'Average (24h)': ['22.8%', '72.1%', '42.7 Mbps', '10.8 Mbps', '16.2 ms', '0.05%'],
        'Peak (24h)': ['89.3%', '91.2%', '95.6 Mbps', '23.4 Mbps', '45.2 ms', '0.15%'],
        'Status': ['🟢 Good', '🟡 Fair', '🟢 Good', '🟢 Good', '🟢 Good', '🟢 Good']
    }
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # Monitoring controls
    st.markdown("---")
    st.subheader("🔧 Monitoring Controls")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("▶️ Start Monitoring", use_container_width=True):
            st.success("Monitoring started!")
    
    with col2:
        if st.button("⏸️ Pause Monitoring", use_container_width=True):
            st.warning("Monitoring paused!")
    
    with col3:
        if st.button("🔄 Reset Counters", use_container_width=True):
            st.info("Counters reset!")
    
    with col4:
        if st.button("⚙️ Configure Alerts", use_container_width=True):
            st.info("Alert configuration opened!")

if __name__ == "__main__":
    main()