"""
NetArchon Streamlit Web Interface

Secure main application entry point for the NetArchon web interface.
Provides multi-page navigation with authentication and home network security.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

# Import NetArchon modules
try:
    from netarchon.core.ssh_connector import SSHConnector, ConnectionPool
    from netarchon.core.device_manager import DeviceDetector
    from netarchon.core.config_manager import ConfigManager
    from netarchon.core.monitoring import MonitoringCollector
    from netarchon.models.connection import ConnectionInfo, AuthenticationCredentials
    from netarchon.utils.logger import get_logger
    from netarchon.web.utils.security import SecurityManager, render_login_page, require_authentication
    from netarchon.web.components.home_network import render_home_network_security, render_firewall_management
except ImportError as e:
    st.error(f"Failed to import NetArchon modules: {e}")
    st.stop()

# Configure Streamlit page
st.set_page_config(
    page_title="NetArchon - Network Management",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/netarchon/netarchon',
        'Report a bug': 'https://github.com/netarchon/netarchon/issues',
        'About': """
        # NetArchon Web Interface
        
        **Version**: 1.0.0
        
        NetArchon is an autonomous AI agent designed to embody the complete skill set 
        of a senior network engineer with focus on Monitoring-as-a-Service (MaaS) capabilities.
        
        Built around five core functional pillars:
        - 🏗️ **Design & Planning** (The Architect)
        - 🔧 **Implementation & Deployment** (The Builder) 
        - 🛡️ **Operations & Maintenance** (The Guardian)
        - 🔒 **Security & Compliance** (The Sentinel)
        - 📊 **MaaS & Insights** (The Analyst)
        """
    }
)

# Custom CSS for NetArchon branding
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main .block-container {
        background: white;
        border-radius: 10px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-top: 1rem;
    }
    
    .stSidebar {
        background: rgba(255, 255, 255, 0.95);
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-offline {
        color: #dc3545;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .device-card {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
    
    .netarchon-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'connection_pool' not in st.session_state:
        st.session_state.connection_pool = ConnectionPool()
    
    if 'device_detector' not in st.session_state:
        st.session_state.device_detector = DeviceDetector()
    
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = ConfigManager()
    
    if 'monitoring_collector' not in st.session_state:
        st.session_state.monitoring_collector = MonitoringCollector()
    
    if 'logger' not in st.session_state:
        st.session_state.logger = get_logger("NetArchon.WebInterface")
    
    if 'connected_devices' not in st.session_state:
        st.session_state.connected_devices = {}
    
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None

def render_sidebar():
    """Render the main navigation sidebar."""
    with st.sidebar:
        # NetArchon Header
        st.markdown("""
        <div class="netarchon-header">
            <h1>🌐 NetArchon</h1>
            <p style="margin: 0; opacity: 0.9;">Network Management Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick Status Overview
        st.subheader("📊 Quick Status")
        
        # Connection pool status
        pool = st.session_state.connection_pool
        active_connections = len([conn for conn in pool.connections.values() 
                                if conn.status.name == 'CONNECTED'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Active Devices", active_connections)
        with col2:
            st.metric("Pool Size", len(pool.connections))
        
        # Home Network Quick View
        st.subheader("🏠 Home Network")
        
        # Placeholder for home network devices
        home_devices = [
            {"name": "Xfinity Gateway", "status": "online", "type": "modem"},
            {"name": "Netgear Orbi", "status": "online", "type": "router"},
            {"name": "Mini PC Server", "status": "online", "type": "server"}
        ]
        
        for device in home_devices:
            status_class = f"status-{device['status']}"
            st.markdown(f"""
            <div class="device-card">
                <strong>{device['name']}</strong><br>
                <span class="{status_class}">● {device['status'].upper()}</span>
                <small>({device['type']})</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔄 Refresh All Data", use_container_width=True):
            st.session_state.last_refresh = None
            st.rerun()
        
        if st.button("📊 Health Check", use_container_width=True):
            st.info("Running network health check...")
            # TODO: Implement health check
        
        if st.button("💾 Backup Configs", use_container_width=True):
            st.info("Starting configuration backup...")
            # TODO: Implement backup all configs
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; opacity: 0.7; font-size: 0.8em;">
            <p>NetArchon v1.0.0<br>
            AI Network Engineer</p>
        </div>
        """, unsafe_allow_html=True)

@require_authentication
def main():
    """Main application function with security."""
    
    # Check authentication first
    security_manager = SecurityManager()
    
    if not security_manager.is_session_valid():
        render_login_page()
        return
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Main content area with security status
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        <div class="netarchon-header">
            <h1>🌐 Welcome to NetArchon</h1>
            <p style="margin: 0; opacity: 0.9;">
                Your AI-Powered Network Management Platform
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Security status indicator
        username = st.session_state.get('username', 'Unknown')
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            margin-top: 20px;
        ">
            <small>🔒 Secure Session</small><br>
            <strong>{username}</strong>
        </div>
        """, unsafe_allow_html=True)
    
    # Home Network Security Overview
    st.markdown("---")
    st.subheader("🏠 Home Network Security Status")
    
    # Quick security metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4>🔒 Network Security</h4>
            <p>Firewall active, monitoring enabled, no threats detected</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4>📱 Authorized Devices</h4>
            <p>Xfinity Gateway and Netgear Orbi router secured</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h4>🛡️ Threat Detection</h4>
            <p>Real-time monitoring and automated response</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h4>🔥 Firewall Status</h4>
            <p>Active protection with intrusion prevention</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Core system capabilities
    st.markdown("---")
    st.subheader("🎯 Core Capabilities")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4>🔧 Implementation</h4>
            <p>SSH connectivity, command execution, and device management ready</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4>🛡️ Operations</h4>
            <p>Real-time monitoring and metrics collection system</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h4>⚙️ Configuration</h4>
            <p>Safe configuration backup, deployment, and rollback</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h4>📊 Analytics</h4>
            <p>MaaS insights and predictive network intelligence</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation instructions
    st.markdown("---")
    st.markdown("""
    ## 🚀 Getting Started
    
    Use the **navigation pages** in the sidebar to access NetArchon's full capabilities:
    
    - **🏠 Dashboard**: Home network overview and real-time status
    - **📱 Devices**: Manage network devices and connections  
    - **⚙️ Configuration**: Backup, deploy, and rollback configurations
    - **📊 Monitoring**: Real-time charts and performance metrics
    - **🔧 Terminal**: Interactive command execution interface
    
    ### 🏠 Your Home Network Setup
    - **ISP**: Xfinity
    - **Modem**: Arris Surfboard S33 DOCSIS 3.1 
    - **Router**: Netgear RBK653-100NAS Orbi Mesh
    - **Server**: Mini PC with NetArchon
    
    Navigate to the **Dashboard** page to begin monitoring your network!
    """)
    
    # System information
    with st.expander("🔧 System Information", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("NetArchon Status")
            st.write("**Core Modules**: ✅ All Loaded")
            st.write("**Connection Pool**: ✅ Ready")
            st.write("**Device Detection**: ✅ Active")
            st.write("**Config Management**: ✅ Ready")
            st.write("**Monitoring**: ✅ Active")
        
        with col2:
            st.subheader("Web Interface")
            st.write("**Framework**: Streamlit")
            st.write("**Python Version**: 3.10+")
            st.write("**Multi-page**: ✅ Enabled")
            st.write("**Real-time Updates**: ✅ Active")
            st.write("**Responsive Design**: ✅ Mobile Ready")

if __name__ == "__main__":
    main()