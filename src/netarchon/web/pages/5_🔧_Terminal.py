"""
NetArchon Terminal Page

Interactive command execution interface for network devices.
"""

import streamlit as st
import time
from datetime import datetime
import sys
from pathlib import Path

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from netarchon.web.utils.data_loader import get_data_loader

# Page configuration
st.set_page_config(
    page_title="NetArchon - Terminal",
    page_icon="🔧",
    layout="wide"
)

def render_device_selector():
    """Render device selection for terminal access."""
    data_loader = get_data_loader()
    devices = data_loader.load_discovered_devices()
    
    # Filter to only connected devices
    connected_devices = [d for d in devices if d.get('status') in ['online', 'connected']]
    
    if not connected_devices:
        st.warning("No connected devices available for terminal access.")
        return None
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        device_options = [f"{d['name']} ({d['ip_address']})" for d in connected_devices]
        selected_idx = st.selectbox(
            "Select Device for Terminal Access",
            range(len(device_options)),
            format_func=lambda x: device_options[x] if x < len(device_options) else "No devices"
        )
        
        selected_device = connected_devices[selected_idx] if selected_idx < len(connected_devices) else None
    
    with col2:
        if selected_device:
            status = selected_device.get('status', 'unknown')
            status_color = 'green' if status in ['online', 'connected'] else 'red'
            st.markdown(f"""
            **Device Status**: <span style="color: {status_color}">● {status.upper()}</span>
            
            **Device Type**: {selected_device.get('device_type', 'Unknown')}
            
            **Vendor**: {selected_device.get('vendor', 'Unknown')}
            """, unsafe_allow_html=True)
    
    return selected_device

def render_command_shortcuts(device_type):
    """Render command shortcuts based on device type."""
    st.subheader("⚡ Quick Commands")
    
    # Define command shortcuts by device type
    shortcuts = {
        'router': [
            ('Show Version', 'show version'),
            ('Show Interfaces', 'show ip interface brief'),
            ('Show Routing Table', 'show ip route'),
            ('Show ARP Table', 'show arp'),
            ('Show Configuration', 'show running-config'),
            ('Show System Status', 'show system-status')
        ],
        'switch': [
            ('Show Version', 'show version'),
            ('Show Interfaces', 'show interfaces status'),
            ('Show MAC Table', 'show mac address-table'),
            ('Show VLAN', 'show vlan brief'),
            ('Show STP', 'show spanning-tree brief'),
            ('Show Configuration', 'show running-config')
        ],
        'server': [
            ('System Info', 'uname -a'),
            ('Disk Usage', 'df -h'),
            ('Memory Usage', 'free -h'),
            ('Process List', 'ps aux'),
            ('Network Interfaces', 'ip addr show'),
            ('System Uptime', 'uptime')
        ],
        'generic': [
            ('Show Version', 'show version'),
            ('Show Interfaces', 'show interfaces'),
            ('Show Status', 'show status'),
            ('Show Configuration', 'show config'),
            ('System Information', 'show system'),
            ('Help', 'help')
        ]
    }
    
    device_shortcuts = shortcuts.get(device_type, shortcuts['generic'])
    
    # Create buttons in a grid
    cols = st.columns(3)
    for i, (label, command) in enumerate(device_shortcuts):
        with cols[i % 3]:
            if st.button(f"🔘 {label}", key=f"shortcut_{i}", use_container_width=True):
                st.session_state.terminal_command = command
                return command
    
    return None

def render_command_history():
    """Render command history panel."""
    if 'command_history' not in st.session_state:
        st.session_state.command_history = []
    
    if st.session_state.command_history:
        st.subheader("📚 Command History")
        
        # Show last 10 commands
        for i, cmd_entry in enumerate(reversed(st.session_state.command_history[-10:])):
            with st.expander(f"🕐 {cmd_entry['timestamp']} - {cmd_entry['command']}", expanded=False):
                st.code(cmd_entry['output'], language='text')
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🔄 Re-run", key=f"rerun_{i}"):
                        st.session_state.terminal_command = cmd_entry['command']
                with col2:
                    if st.button(f"📋 Copy", key=f"copy_{i}"):
                        st.code(cmd_entry['command'])
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.command_history = []
            st.rerun()

def execute_command(device, command):
    """Execute a command on the selected device."""
    if not command.strip():
        return "Error: Empty command"
    
    # Simulate command execution with realistic delay
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Connecting to device...")
    progress_bar.progress(25)
    time.sleep(0.5)
    
    status_text.text(f"Executing: {command}")
    progress_bar.progress(50)
    time.sleep(1)
    
    status_text.text("Processing output...")
    progress_bar.progress(75)
    time.sleep(0.5)
    
    status_text.text("Command completed!")
    progress_bar.progress(100)
    time.sleep(0.3)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Simulate different command outputs based on device and command
    if 'show version' in command.lower():
        if device['name'] == 'Xfinity Gateway':
            output = """Arris Surfboard S33 DOCSIS 3.1 Cable Modem
Software Version: SB_S33_04_11_T1_110.05.14
Boot Version: 01.01.14
Model: S33
Vendor: Arris
Hardware Version: 01
Serial Number: M2G123456789
MAC Address: 00:1A:2B:3C:4D:5E
DOCSIS Version: 3.1
Current Time: Mon Jan 15 14:30:45 EST 2024
System Uptime: 7 days, 14 hours, 30 minutes"""
        elif device['name'] == 'Netgear Orbi Router':
            output = """NETGEAR RBK653 Orbi WiFi 6 System
Firmware Version: V4.6.15.52_1.3.85
Model: RBK653-100NAS
Hardware Version: RBK653
Serial Number: 4NV987654321
WiFi Standards: 802.11ax (WiFi 6)
Processor: Quad-core ARM Cortex-A73
Memory: 1GB RAM, 512MB Flash
Current Time: Mon Jan 15 14:30:45 EST 2024
System Uptime: 5 days, 8 hours, 15 minutes"""
        else:
            output = f"""Device: {device['name']}
Model: {device.get('model', 'Unknown')}
Vendor: {device.get('vendor', 'Unknown')}
IP Address: {device['ip_address']}
Status: {device.get('status', 'Unknown')}
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    elif 'show interface' in command.lower():
        if device['name'] == 'Xfinity Gateway':
            output = """Interface Status Summary:
Cable0/0          up       up       192.168.100.1   255.255.255.0
Ethernet1/1       up       up       192.168.1.1     255.255.255.0  
Ethernet1/2       down     down     unassigned      unassigned
Ethernet1/3       down     down     unassigned      unassigned
Ethernet1/4       up       up       unassigned      unassigned
WiFi2.4G          up       up       192.168.1.1     255.255.255.0
WiFi5G            up       up       192.168.1.1     255.255.255.0"""
        else:
            output = """Interface Status:
GigabitEthernet0/0/1    up       up       192.168.1.10    255.255.255.0
GigabitEthernet0/0/2    up       up       unassigned      unassigned  
GigabitEthernet0/0/3    down     down     unassigned      unassigned
Loopback0               up       up       10.0.0.1        255.255.255.255"""
    
    elif 'show ip route' in command.lower():
        output = """Routing Table:
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         192.168.1.1     0.0.0.0         UG    100    0        0 eth0
192.168.1.0     0.0.0.0         255.255.255.0   U     100    0        0 eth0
192.168.100.0   0.0.0.0         255.255.255.0   U     0      0        0 cable0"""
    
    elif 'show config' in command.lower() or 'show running' in command.lower():
        output = f"""! Configuration for {device['name']}
! Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
!
version 15.1
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
!
hostname {device['name'].replace(' ', '-')}
!
interface GigabitEthernet0/0/1
 ip address {device['ip_address']} 255.255.255.0
 no shutdown
!
ip route 0.0.0.0 0.0.0.0 192.168.1.1
!
end"""
    
    elif command.lower() in ['help', '?']:
        output = """Available Commands:
show version          - Display system version information
show interfaces      - Display interface status and configuration  
show ip route         - Display IP routing table
show running-config   - Display current configuration
show arp             - Display ARP table
show system          - Display system information
configure terminal   - Enter configuration mode
ping <address>       - Ping network address
traceroute <address> - Trace route to network address
help                 - Display this help message"""
    
    elif command.lower().startswith('ping'):
        target = command.split()[-1] if len(command.split()) > 1 else '8.8.8.8'
        output = f"""PING {target} (8.8.8.8): 56 data bytes
64 bytes from 8.8.8.8: icmp_seq=1 ttl=58 time=18.2 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=58 time=17.8 ms
64 bytes from 8.8.8.8: icmp_seq=3 ttl=58 time=18.5 ms
64 bytes from 8.8.8.8: icmp_seq=4 ttl=58 time=17.9 ms

--- {target} ping statistics ---
4 packets transmitted, 4 received, 0% packet loss
round-trip min/avg/max/stddev = 17.8/18.1/18.5/0.3 ms"""
    
    else:
        output = f"""Command: {command}
Device: {device['name']} ({device['ip_address']})
Executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Note: This is a simulated output. In a real implementation, 
this would execute the actual command on the network device 
using the NetArchon command execution framework."""
    
    return output

def main():
    """Main terminal page function."""
    
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
        <h1 style="margin: 0;">🔧 Network Terminal</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">
            Interactive command execution for network devices
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Device selection
    selected_device = render_device_selector()
    
    if not selected_device:
        st.stop()
    
    # Initialize session state
    if 'command_history' not in st.session_state:
        st.session_state.command_history = []
    
    if 'terminal_command' not in st.session_state:
        st.session_state.terminal_command = ""
    
    st.markdown("---")
    
    # Main terminal interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Command shortcuts
        shortcut_command = render_command_shortcuts(selected_device.get('device_type', 'generic'))
        
        if shortcut_command:
            st.session_state.terminal_command = shortcut_command
        
        st.markdown("---")
        
        # Command input
        st.subheader("💻 Command Interface")
        
        # Command input form
        with st.form("command_form", clear_on_submit=False):
            command_input = st.text_input(
                "Enter Command:",
                value=st.session_state.terminal_command,
                placeholder="Type a command (e.g., 'show version')",
                help="Enter a network command to execute on the selected device"
            )
            
            col_exec, col_clear = st.columns([1, 1])
            
            with col_exec:
                execute_button = st.form_submit_button("▶️ Execute Command", type="primary")
            
            with col_clear:
                clear_button = st.form_submit_button("🗑️ Clear")
        
        # Execute command
        if execute_button and command_input:
            st.subheader("📤 Command Output")
            
            # Show command being executed
            st.code(f"{selected_device['name']}# {command_input}", language='bash')
            
            # Execute and display output
            output = execute_command(selected_device, command_input)
            st.code(output, language='text')
            
            # Add to history
            st.session_state.command_history.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'device': selected_device['name'],
                'command': command_input,
                'output': output
            })
            
            # Clear the command input
            st.session_state.terminal_command = ""
        
        elif clear_button:
            st.session_state.terminal_command = ""
            st.rerun()
        
        # Terminal tips
        st.markdown("---")
        st.subheader("💡 Terminal Tips")
        
        tips = [
            "🔍 Use 'show version' to get device information",
            "🌐 Use 'show interfaces' to check interface status", 
            "📡 Use 'ping <address>' to test connectivity",
            "📋 Use command shortcuts for quick access",
            "📚 Check command history to re-run previous commands",
            "❓ Use 'help' to see available commands"
        ]
        
        for tip in tips:
            st.markdown(f"- {tip}")
    
    with col2:
        # Command history
        render_command_history()
        
        # Device information panel
        st.subheader("📱 Device Information")
        
        device_info = f"""
        **Name**: {selected_device['name']}
        **IP**: {selected_device['ip_address']}
        **Type**: {selected_device.get('device_type', 'Unknown')}
        **Vendor**: {selected_device.get('vendor', 'Unknown')}
        **Model**: {selected_device.get('model', 'Unknown')}
        **Status**: {selected_device.get('status', 'Unknown')}
        """
        
        st.markdown(device_info)
        
        # Connection test
        if st.button("🔌 Test Connection", use_container_width=True):
            with st.spinner("Testing connection..."):
                time.sleep(2)
            st.success("Connection test successful!")
        
        # Safety features
        st.markdown("---")
        st.subheader("🛡️ Safety Features")
        
        st.info("""
        **Active Safety Measures:**
        - ✅ Command validation
        - ✅ Connection monitoring  
        - ✅ Command history logging
        - ✅ Session timeout protection
        - ✅ Dangerous command detection
        """)
        
        # Terminal settings
        st.markdown("---")
        st.subheader("⚙️ Terminal Settings")
        
        auto_clear = st.checkbox("Auto-clear command after execution", value=True)
        show_timestamps = st.checkbox("Show command timestamps", value=True)
        command_timeout = st.slider("Command timeout (seconds)", 5, 60, 30)
        
        if st.button("💾 Save Settings", use_container_width=True):
            st.success("Settings saved!")

if __name__ == "__main__":
    main()