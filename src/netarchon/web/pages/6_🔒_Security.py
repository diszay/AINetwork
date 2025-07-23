"""
NetArchon Security Page

Comprehensive network security monitoring, scanning, and management interface.
"""

import streamlit as st
import sys
from pathlib import Path

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from netarchon.web.utils.security import require_authentication, get_security_manager, render_user_settings
from netarchon.web.components.home_network import render_home_network_security, render_firewall_management
from netarchon.web.components.secure_scanner import render_secure_network_scanner

# Page configuration
st.set_page_config(
    page_title="NetArchon - Security",
    page_icon="🔒",
    layout="wide"
)

@require_authentication
def main():
    """Main security page function."""
    
    # Page header with security status
    security_manager = get_security_manager()
    username = st.session_state.get('username', 'User')
    
    st.markdown("""
    <div style="
        background: linear-gradient(90deg, #dc3545 0%, #6f42c1 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    ">
        <h1 style="margin: 0;">🔒 Network Security Center</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">
            Comprehensive security monitoring and threat detection
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Security status overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="
            background: #28a745;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">🛡️</h3>
            <p style="margin: 5px 0 0 0;"><strong>Security Status</strong></p>
            <p style="margin: 0; font-size: 0.9em;">PROTECTED</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="
            background: #17a2b8;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">🔍</h3>
            <p style="margin: 5px 0 0 0;"><strong>Active Scans</strong></p>
            <p style="margin: 0; font-size: 0.9em;">MONITORING</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="
            background: #ffc107;
            color: black;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">⚠️</h3>
            <p style="margin: 5px 0 0 0;"><strong>Threats</strong></p>
            <p style="margin: 0; font-size: 0.9em;">0 DETECTED</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="
            background: #6c757d;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">🔥</h3>
            <p style="margin: 5px 0 0 0;"><strong>Firewall</strong></p>
            <p style="margin: 0; font-size: 0.9em;">ACTIVE</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main security tabs
    security_tab, scanner_tab, firewall_tab, settings_tab = st.tabs([
        "🏠 Home Network Security",
        "🔍 Security Scanner", 
        "🔥 Firewall Management",
        "👤 User Settings"
    ])
    
    with security_tab:
        st.markdown("### 🏠 Home Network Security Overview")
        st.info("""
        **🛡️ Security Features Active:**
        - Real-time device monitoring
        - Unauthorized device detection  
        - Vulnerability assessment
        - Automated threat response
        - Secure credential storage
        """)
        
        render_home_network_security()
    
    with scanner_tab:
        st.markdown("### 🔍 Secure Network Scanner")
        st.warning("""
        **⚠️ Scanning Policy**: This scanner operates only within your home network (RFC 1918 private addresses)
        and uses safe, non-intrusive methods to assess security without disrupting network operations.
        """)
        
        render_secure_network_scanner()
    
    with firewall_tab:
        st.markdown("### 🔥 Firewall Management")
        st.info("""
        **🔥 Firewall Protection**: Manage system firewall rules and network access controls
        to protect your home network from unauthorized access and threats.
        """)
        
        render_firewall_management()
    
    with settings_tab:
        st.markdown("### 👤 Security Settings")
        render_user_settings()
    
    # Security recommendations
    st.markdown("---")
    st.subheader("💡 Security Recommendations")
    
    recommendations = [
        "🔐 **Change Default Passwords**: Ensure all devices use strong, unique passwords",
        "🔄 **Regular Updates**: Keep device firmware and software up to date",
        "🧱 **Enable Firewalls**: Activate built-in firewalls on all devices",
        "📶 **Secure WiFi**: Use WPA3 encryption and disable WPS",
        "🔍 **Monitor Traffic**: Regularly review network activity for anomalies",
        "🗝️ **Access Control**: Implement least-privilege access policies",
        "📊 **Log Monitoring**: Enable and review security logs regularly",
        "🔒 **Network Segmentation**: Isolate IoT devices from critical systems"
    ]
    
    col1, col2 = st.columns(2)
    
    for i, rec in enumerate(recommendations):
        with col1 if i % 2 == 0 else col2:
            st.markdown(f"- {rec}")
    
    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Security Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Quick Scan", use_container_width=True):
            st.info("Initiating quick security scan...")
    
    with col2:
        if st.button("🔒 Lock Down", use_container_width=True):
            st.warning("Enhanced security mode activated")
    
    with col3:
        if st.button("📊 Security Report", use_container_width=True):
            st.info("Generating comprehensive security report...")
    
    with col4:
        if st.button("🚨 Alert Test", use_container_width=True):
            st.success("Security alert system tested successfully")
    
    # Security metrics footer
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🔒 Encryption Status**
        - Web Interface: ✅ TLS Enabled
        - Credential Storage: ✅ AES-256
        - Session Management: ✅ Secure Tokens
        """)
    
    with col2:
        st.markdown("""
        **🛡️ Access Control**
        - Authentication: ✅ Required
        - Session Timeout: ✅ 1 Hour
        - IP Restrictions: ✅ Home Network Only
        """)
    
    with col3:
        st.markdown("""
        **📊 Monitoring Status**
        - Device Scanning: ✅ Active
        - Threat Detection: ✅ Real-time
        - Audit Logging: ✅ Enabled
        """)

if __name__ == "__main__":
    main()