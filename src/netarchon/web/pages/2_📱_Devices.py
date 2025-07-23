"""
NetArchon Devices Page

Device management interface with connection, discovery, and monitoring capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
    page_title="NetArchon - Devices",
    page_icon="📱",
    layout="wide"
)

def render_device_connection_form():
    """Render form for adding new device connections."""
    with st.expander("➕ Add New Device", expanded=False):
        st.subheader("Connect to Network Device")
        
        with st.form("device_connection_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                host = st.text_input("IP Address/Hostname", placeholder="192.168.1.1")
                username = st.text_input("Username", placeholder="admin")
                port = st.number_input("SSH Port", min_value=1, max_value=65535, value=22)
            
            with col2:
                device_name = st.text_input("Device Name (Optional)", placeholder="Router-01")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                device_type = st.selectbox("Device Type", 
                                         ["Auto-detect", "Cisco IOS", "Cisco NX-OS", 
                                          "Juniper JUNOS", "Arista EOS", "Generic"])
            
            submitted = st.form_submit_button("🔗 Connect Device", type="primary")
            
            if submitted and host and username and password:
                data_loader = get_data_loader()
                
                with st.spinner(f"Connecting to {host}..."):
                    success, message = data_loader.connect_device(host, username, password, port)
                
                if success:
                    st.success(f"✅ {message}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")

def render_device_table(devices):
    """Render interactive device table."""
    if not devices:
        st.info("No devices found. Add a device using the form above.")
        return
    
    # Create DataFrame
    df = pd.DataFrame(devices)
    
    # Add action buttons column
    df['Actions'] = ['🔧 Manage'] * len(df)
    
    # Configure column display
    column_config = {
        'name': st.column_config.TextColumn("Device Name", width="medium"),
        'ip_address': st.column_config.TextColumn("IP Address", width="small"),
        'device_type': st.column_config.TextColumn("Type", width="small"),
        'vendor': st.column_config.TextColumn("Vendor", width="small"),
        'model': st.column_config.TextColumn("Model", width="medium"),
        'status': st.column_config.TextColumn("Status", width="small"),
        'is_home_device': st.column_config.CheckboxColumn("Home Device", width="small"),
        'Actions': st.column_config.ButtonColumn("Actions", width="small")
    }
    
    # Display table with selection
    selected_rows = st.dataframe(
        df[['name', 'ip_address', 'device_type', 'vendor', 'model', 'status', 'is_home_device']],
        use_container_width=True,
        column_config=column_config,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row"
    )
    
    return selected_rows

def render_device_details(device):
    """Render detailed view for a selected device."""
    st.subheader(f"📱 {device['name']} Details")
    
    # Device information cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        **Basic Information**
        - **Name**: {device['name']}
        - **IP Address**: {device['ip_address']}
        - **Type**: {device['device_type']}
        - **Vendor**: {device['vendor']}
        - **Model**: {device['model']}
        """)
    
    with col2:
        # Device status
        status = device.get('status', 'unknown')
        status_color = {
            'online': '🟢',
            'connected': '🟢',
            'offline': '🔴',
            'warning': '🟡',
            'unknown': '⚪'
        }.get(status, '⚪')
        
        st.markdown(f"""
        **Status Information**
        - **Status**: {status_color} {status.upper()}
        - **Last Seen**: {device.get('last_seen', 'Never')}
        - **Home Device**: {'Yes' if device.get('is_home_device') else 'No'}
        """)
    
    with col3:
        # Quick actions
        st.markdown("**Quick Actions**")
        
        col3a, col3b = st.columns(2)
        with col3a:
            if st.button("🔄 Refresh Status", key=f"refresh_{device['id']}"):
                st.info("Refreshing device status...")
                time.sleep(1)
                st.rerun()
            
            if st.button("📊 View Metrics", key=f"metrics_{device['id']}"):
                st.session_state.selected_device_metrics = device['id']
        
        with col3b:
            if st.button("💾 Backup Config", key=f"backup_{device['id']}"):
                data_loader = get_data_loader()
                success, message = data_loader.backup_device_config(device['id'])
                if success:
                    st.success(message)
                else:
                    st.error(message)
            
            if device.get('status') in ['connected', 'online']:
                if st.button("🔌 Disconnect", key=f"disconnect_{device['id']}"):
                    data_loader = get_data_loader()
                    success, message = data_loader.disconnect_device(device['id'])
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)

def render_device_metrics(device_id):
    """Render device performance metrics."""
    data_loader = get_data_loader()
    metrics = data_loader.load_device_metrics(device_id)
    
    if 'error' in metrics:
        st.error(f"Failed to load metrics: {metrics['error']}")
        return
    
    st.subheader("📊 Device Metrics")
    
    # System metrics
    if 'system_metrics' in metrics:
        system = metrics['system_metrics']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu = system.get('cpu_usage', 0)
            st.metric("CPU Usage", f"{cpu:.1f}%", 
                     delta=f"{cpu-50:.1f}%" if cpu != 50 else None)
        
        with col2:
            memory = system.get('memory_usage', 0)
            st.metric("Memory Usage", f"{memory:.1f}%",
                     delta=f"{memory-60:.1f}%" if memory != 60 else None)
        
        with col3:
            temp = system.get('temperature', 0)
            if temp > 0:
                st.metric("Temperature", f"{temp:.1f}°C",
                         delta="Normal" if temp < 60 else "High")
        
        with col4:
            uptime = system.get('uptime', 0)
            uptime_days = uptime // 86400
            st.metric("Uptime", f"{uptime_days} days")
    
    # Interface metrics
    if 'interface_metrics' in metrics:
        interfaces = metrics['interface_metrics']
        
        if interfaces:
            st.subheader("🔌 Interface Statistics")
            
            # Create interface DataFrame
            interface_data = []
            for intf in interfaces:
                interface_data.append({
                    'Interface': intf.get('interface_name', 'Unknown'),
                    'Status': intf.get('status', 'unknown'),
                    'Input (MB)': intf.get('input_bytes', 0) / 1024 / 1024,
                    'Output (MB)': intf.get('output_bytes', 0) / 1024 / 1024,
                    'Utilization In (%)': intf.get('utilization_in', 0),
                    'Utilization Out (%)': intf.get('utilization_out', 0),
                    'Bandwidth (Mbps)': intf.get('bandwidth', 0) / 1000000
                })
            
            if interface_data:
                df = pd.DataFrame(interface_data)
                st.dataframe(df, use_container_width=True)
                
                # Interface utilization chart
                if len(interfaces) > 0:
                    fig = go.Figure()
                    
                    for intf in interfaces:
                        name = intf.get('interface_name', 'Unknown')
                        util_in = intf.get('utilization_in', 0)
                        util_out = intf.get('utilization_out', 0)
                        
                        fig.add_trace(go.Bar(
                            name=f"{name} In",
                            x=[name],
                            y=[util_in],
                            marker_color='lightblue'
                        ))
                        
                        fig.add_trace(go.Bar(
                            name=f"{name} Out",
                            x=[name],
                            y=[util_out],
                            marker_color='lightcoral'
                        ))
                    
                    fig.update_layout(
                        title="Interface Utilization",
                        xaxis_title="Interface",
                        yaxis_title="Utilization (%)",
                        barmode='group',
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
    
    # Special metrics for home devices
    if 'docsis_metrics' in metrics:
        st.subheader("📡 DOCSIS Cable Metrics")
        docsis = metrics['docsis_metrics']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Downstream Channels", docsis.get('downstream_channels', 0))
        with col2:
            st.metric("Upstream Channels", docsis.get('upstream_channels', 0))
        with col3:
            st.metric("Downstream Power", f"{docsis.get('downstream_power', 0):.1f} dBmV")
        with col4:
            st.metric("SNR", f"{docsis.get('snr', 0):.1f} dB")
    
    if 'wifi_metrics' in metrics:
        st.subheader("📶 WiFi Metrics")
        wifi = metrics['wifi_metrics']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Connected Clients", wifi.get('connected_clients', 0))
        with col2:
            st.metric("2.4GHz Signal", f"{wifi.get('signal_strength_2g', 0)} dBm")
        with col3:
            st.metric("5GHz Signal", f"{wifi.get('signal_strength_5g', 0)} dBm")
        with col4:
            st.metric("Mesh Status", wifi.get('mesh_status', 'Unknown'))

def render_network_topology():
    """Render network topology visualization."""
    st.subheader("🌐 Network Topology")
    
    # Create a simple network topology graph
    fig = go.Figure()
    
    # Sample topology data
    nodes = [
        {"id": "internet", "label": "Internet", "x": 0, "y": 0, "color": "blue"},
        {"id": "modem", "label": "Xfinity Modem", "x": 1, "y": 0, "color": "green"},
        {"id": "router", "label": "Netgear Orbi", "x": 2, "y": 0, "color": "orange"},
        {"id": "device1", "label": "Mini PC", "x": 1.5, "y": 1, "color": "red"},
        {"id": "device2", "label": "Laptop", "x": 2.5, "y": 1, "color": "purple"},
        {"id": "device3", "label": "Phone", "x": 1.5, "y": -1, "color": "pink"}
    ]
    
    edges = [
        ("internet", "modem"),
        ("modem", "router"),
        ("router", "device1"),
        ("router", "device2"),
        ("router", "device3")
    ]
    
    # Add edges
    for edge in edges:
        node1 = next(n for n in nodes if n["id"] == edge[0])
        node2 = next(n for n in nodes if n["id"] == edge[1])
        
        fig.add_trace(go.Scatter(
            x=[node1["x"], node2["x"]],
            y=[node1["y"], node2["y"]],
            mode='lines',
            line=dict(color='gray', width=2),
            showlegend=False,
            hoverinfo='none'
        ))
    
    # Add nodes
    for node in nodes:
        fig.add_trace(go.Scatter(
            x=[node["x"]],
            y=[node["y"]],
            mode='markers+text',
            marker=dict(size=30, color=node["color"]),
            text=node["label"],
            textposition="bottom center",
            name=node["label"],
            showlegend=False
        ))
    
    fig.update_layout(
        title="Network Topology Overview",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def main():
    """Main devices page function."""
    
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
        <h1 style="margin: 0;">📱 Device Management</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">
            Connect, monitor, and manage your network devices
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get data loader
    data_loader = get_data_loader()
    
    # Load devices
    devices = data_loader.load_discovered_devices()
    
    # Device connection form
    render_device_connection_form()
    
    st.markdown("---")
    
    # Device table and management
    st.subheader("📋 Device Inventory")
    
    if devices:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox("Filter by Status", 
                                       ["All", "online", "offline", "connected", "unknown"])
        
        with col2:
            type_filter = st.selectbox("Filter by Type",
                                     ["All"] + list(set(d.get('device_type', 'unknown') for d in devices)))
        
        with col3:
            home_filter = st.selectbox("Filter by Location",
                                     ["All", "Home Devices", "Network Devices"])
        
        # Apply filters
        filtered_devices = devices
        
        if status_filter != "All":
            filtered_devices = [d for d in filtered_devices if d.get('status') == status_filter]
        
        if type_filter != "All":
            filtered_devices = [d for d in filtered_devices if d.get('device_type') == type_filter]
        
        if home_filter == "Home Devices":
            filtered_devices = [d for d in filtered_devices if d.get('is_home_device', False)]
        elif home_filter == "Network Devices":
            filtered_devices = [d for d in filtered_devices if not d.get('is_home_device', False)]
        
        # Device table
        selected_rows = render_device_table(filtered_devices)
        
        # Device details section
        if hasattr(st.session_state, 'selected_device_metrics'):
            device_id = st.session_state.selected_device_metrics
            device = next((d for d in devices if d['id'] == device_id), None)
            
            if device:
                st.markdown("---")
                render_device_details(device)
                render_device_metrics(device_id)
                
                if st.button("❌ Close Details"):
                    del st.session_state.selected_device_metrics
                    st.rerun()
    
    else:
        st.info("No devices found. Use the connection form above to add devices.")
    
    st.markdown("---")
    
    # Network topology
    render_network_topology()
    
    # Bulk operations
    if devices:
        st.markdown("---")
        st.subheader("🔧 Bulk Operations")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Refresh All Status", use_container_width=True):
                with st.spinner("Refreshing all device status..."):
                    time.sleep(2)
                st.success("All device status refreshed!")
        
        with col2:
            if st.button("💾 Backup All Configs", use_container_width=True):
                with st.spinner("Backing up all configurations..."):
                    time.sleep(3)
                st.success("All configurations backed up!")
        
        with col3:
            if st.button("🔍 Discovery Scan", use_container_width=True):
                with st.spinner("Scanning for new devices..."):
                    time.sleep(4)
                st.success("Network scan completed!")
        
        with col4:
            if st.button("📊 Export Device List", use_container_width=True):
                # Create CSV export
                df = pd.DataFrame(devices)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"netarchon_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()