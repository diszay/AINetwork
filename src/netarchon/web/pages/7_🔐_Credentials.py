"""
NetArchon Credential Management Page

BitWarden integration for secure credential management and device authentication.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from netarchon.web.utils.security import require_authentication, get_security_manager
from netarchon.integrations.bitwarden import BitWardenManager, BitWardenError
from netarchon.integrations.bitwarden.models import CredentialType
from netarchon.core.enhanced_ssh_connector import EnhancedSSHConnector

# Page configuration
st.set_page_config(
    page_title="NetArchon - Credentials",
    page_icon="🔐",
    layout="wide"
)

@require_authentication
def main():
    """Main credential management page function."""
    
    # Page header
    st.markdown("""
    <div style="
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    ">
        <h1 style="margin: 0;">🔐 Credential Management</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">
            Secure BitWarden integration for network device authentication
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize BitWarden manager
    if 'bitwarden_manager' not in st.session_state:
        try:
            st.session_state.bitwarden_manager = BitWardenManager()
        except Exception as e:
            st.error(f"Failed to initialize BitWarden manager: {e}")
            return
    
    bw_manager = st.session_state.bitwarden_manager
    
    # Create tabs for different functionalities
    config_tab, vault_tab, mappings_tab, test_tab = st.tabs([
        "⚙️ Configuration",
        "🗄️ Vault Browser", 
        "🔗 Device Mappings",
        "🧪 Connection Testing"
    ])
    
    with config_tab:
        render_bitwarden_configuration(bw_manager)
    
    with vault_tab:
        render_vault_browser(bw_manager)
    
    with mappings_tab:
        render_device_mappings(bw_manager)
    
    with test_tab:
        render_connection_testing()


def render_bitwarden_configuration(bw_manager: BitWardenManager):
    """Render BitWarden configuration interface."""
    st.subheader("⚙️ BitWarden Configuration")
    
    # Get current vault status
    vault_status = bw_manager.get_vault_status()
    
    # Status display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_color = "#28a745" if vault_status.is_authenticated else "#dc3545"
        st.markdown(f"""
        <div style="
            background: {status_color};
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">🔑</h3>
            <p style="margin: 5px 0 0 0;"><strong>Authentication</strong></p>
            <p style="margin: 0; font-size: 0.9em;">
                {"AUTHENTICATED" if vault_status.is_authenticated else "NOT AUTHENTICATED"}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        lock_color = "#28a745" if vault_status.is_unlocked else "#ffc107"
        st.markdown(f"""
        <div style="
            background: {lock_color};
            color: {"white" if vault_status.is_unlocked else "black"};
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">🔓</h3>
            <p style="margin: 5px 0 0 0;"><strong>Vault Status</strong></p>
            <p style="margin: 0; font-size: 0.9em;">
                {"UNLOCKED" if vault_status.is_unlocked else "LOCKED"}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="
            background: #17a2b8;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="margin: 0;">📊</h3>
            <p style="margin: 5px 0 0 0;"><strong>Items</strong></p>
            <p style="margin: 0; font-size: 0.9em;">{vault_status.total_items}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Configuration form
    st.subheader("🔧 API Configuration")
    
    with st.form("bitwarden_config"):
        st.info("Configure BitWarden API access for automated credential retrieval.")
        
        client_id = st.text_input(
            "Client ID",
            help="BitWarden API Client ID from your account settings"
        )
        
        client_secret = st.text_input(
            "Client Secret",
            type="password",
            help="BitWarden API Client Secret"
        )
        
        server_url = st.text_input(
            "Server URL (Optional)",
            placeholder="https://bitwarden.com",
            help="Leave blank for official BitWarden service"
        )
        
        submitted = st.form_submit_button("💾 Save Configuration")
        
        if submitted:
            if client_id and client_secret:
                try:
                    bw_manager.configure_api_access(
                        client_id=client_id,
                        client_secret=client_secret,
                        server_url=server_url if server_url else None
                    )
                    st.success("✅ BitWarden configuration saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Configuration failed: {e}")
            else:
                st.error("❌ Please provide both Client ID and Client Secret")
    
    # Vault operations
    st.markdown("---")
    st.subheader("🔄 Vault Operations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Sync Vault", use_container_width=True):
            with st.spinner("Synchronizing vault..."):
                try:
                    success = bw_manager.sync_vault()
                    if success:
                        st.success("✅ Vault synchronized successfully!")
                    else:
                        st.error("❌ Vault synchronization failed")
                except Exception as e:
                    st.error(f"❌ Sync error: {e}")
    
    with col2:
        if st.button("🔒 Lock Vault", use_container_width=True):
            try:
                success = bw_manager.lock_vault()
                if success:
                    st.success("✅ Vault locked successfully!")
                    st.rerun()
                else:
                    st.warning("⚠️ Failed to lock vault")
            except Exception as e:
                st.error(f"❌ Lock error: {e}")
    
    with col3:
        if st.button("📊 Refresh Status", use_container_width=True):
            st.rerun()
    
    # Display detailed status
    if vault_status.is_authenticated:
        st.markdown("---")
        st.subheader("📋 Vault Details")
        
        details = {
            "Server URL": vault_status.server_url or "Default (bitwarden.com)",
            "User Email": vault_status.user_email or "Not available",
            "Last Sync": vault_status.last_sync.strftime("%Y-%m-%d %H:%M:%S") if vault_status.last_sync else "Never",
            "Total Items": str(vault_status.total_items),
            "Session Expires": vault_status.session_expires.strftime("%Y-%m-%d %H:%M:%S") if vault_status.session_expires else "Not available"
        }
        
        for key, value in details.items():
            st.text(f"{key}: {value}")


def render_vault_browser(bw_manager: BitWardenManager):
    """Render vault browser interface."""
    st.subheader("🗄️ Vault Browser")
    
    # Check vault status
    vault_status = bw_manager.get_vault_status()
    
    if not vault_status.is_authenticated:
        st.warning("⚠️ Please configure and authenticate BitWarden first.")
        return
    
    if not vault_status.is_unlocked:
        st.warning("⚠️ Vault is locked. Please unlock it first.")
        return
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Search vault items",
            placeholder="Enter search term (IP address, device name, etc.)",
            key="vault_search"
        )
    
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    # Search results
    if search_term and search_button:
        with st.spinner("Searching vault..."):
            try:
                items = bw_manager.search_items(search_term)
                
                if items:
                    st.success(f"Found {len(items)} items")
                    
                    for item in items:
                        with st.expander(f"🔑 {item.name}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Item Details:**")
                                st.write(f"- **ID**: {item.id}")
                                st.write(f"- **Name**: {item.name}")
                                st.write(f"- **Type**: {item.item_type.name}")
                                st.write(f"- **Favorite**: {'Yes' if item.favorite else 'No'}")
                                
                                if item.revision_date:
                                    st.write(f"- **Last Modified**: {item.revision_date.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            with col2:
                                if item.login:
                                    st.write("**Login Information:**")
                                    st.write(f"- **Username**: {item.login.username}")
                                    st.write(f"- **Password**: {'*' * len(item.login.password) if item.login.password else 'None'}")
                                    
                                    if item.login.uris:
                                        st.write("**URIs:**")
                                        for uri in item.login.uris:
                                            st.write(f"  - {uri.uri}")
                            
                            if item.notes:
                                st.write("**Notes:**")
                                st.text_area("", value=item.notes, height=100, disabled=True, key=f"notes_{item.id}")
                            
                            # Create mapping button
                            if st.button(f"🔗 Create Device Mapping", key=f"map_{item.id}"):
                                st.session_state[f"create_mapping_{item.id}"] = True
                            
                            # Create mapping form
                            if st.session_state.get(f"create_mapping_{item.id}", False):
                                with st.form(f"mapping_form_{item.id}"):
                                    st.write("**Create Device Mapping**")
                                    
                                    device_ip = st.text_input("Device IP Address", key=f"ip_{item.id}")
                                    device_hostname = st.text_input("Device Hostname", key=f"hostname_{item.id}")
                                    device_type = st.selectbox(
                                        "Device Type",
                                        ["router", "switch", "firewall", "access_point", "server", "other"],
                                        key=f"type_{item.id}"
                                    )
                                    credential_type = st.selectbox(
                                        "Credential Type",
                                        [ct.value for ct in CredentialType],
                                        key=f"cred_type_{item.id}"
                                    )
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        if st.form_submit_button("✅ Create Mapping"):
                                            if device_ip and device_hostname:
                                                try:
                                                    success = bw_manager.create_device_mapping(
                                                        device_ip=device_ip,
                                                        device_hostname=device_hostname,
                                                        device_type=device_type,
                                                        bitwarden_item_id=item.id,
                                                        credential_type=CredentialType(credential_type)
                                                    )
                                                    
                                                    if success:
                                                        st.success(f"✅ Mapping created for {device_ip}")
                                                        st.session_state[f"create_mapping_{item.id}"] = False
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Failed to create mapping")
                                                except Exception as e:
                                                    st.error(f"❌ Mapping error: {e}")
                                            else:
                                                st.error("❌ Please provide IP address and hostname")
                                    
                                    with col2:
                                        if st.form_submit_button("❌ Cancel"):
                                            st.session_state[f"create_mapping_{item.id}"] = False
                                            st.rerun()
                else:
                    st.info("No items found matching the search term.")
                    
            except Exception as e:
                st.error(f"❌ Search failed: {e}")


def render_device_mappings(bw_manager: BitWardenManager):
    """Render device mappings management interface."""
    st.subheader("🔗 Device Mappings")
    
    st.info("""
    **Device mappings** link your network devices to BitWarden credentials for automatic authentication.
    NetArchon uses these mappings to automatically retrieve the correct credentials when connecting to devices.
    """)
    
    # Get all mappings
    try:
        mappings = bw_manager.get_all_device_mappings()
        
        if mappings:
            # Convert to DataFrame for better display
            mapping_data = []
            for device_ip, mapping in mappings.items():
                mapping_data.append({
                    "Device IP": device_ip,
                    "Hostname": mapping.device_hostname,
                    "Type": mapping.device_type,
                    "BitWarden Item": mapping.bitwarden_item_name,
                    "Credential Type": mapping.credential_type.value,
                    "Auto-discovered": "Yes" if mapping.auto_discovered else "No",
                    "Last Verified": mapping.last_verified.strftime("%Y-%m-%d %H:%M:%S") if mapping.last_verified else "Never"
                })
            
            df = pd.DataFrame(mapping_data)
            
            # Display as interactive table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Device IP": st.column_config.TextColumn("Device IP", width="medium"),
                    "Hostname": st.column_config.TextColumn("Hostname", width="medium"),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "BitWarden Item": st.column_config.TextColumn("BitWarden Item", width="large"),
                    "Credential Type": st.column_config.TextColumn("Credential Type", width="medium"),
                    "Auto-discovered": st.column_config.TextColumn("Auto-discovered", width="small"),
                    "Last Verified": st.column_config.TextColumn("Last Verified", width="medium")
                }
            )
            
            # Mapping management
            st.markdown("---")
            st.subheader("🗑️ Manage Mappings")
            
            selected_device = st.selectbox(
                "Select device to remove:",
                options=list(mappings.keys()),
                format_func=lambda x: f"{x} ({mappings[x].device_hostname})"
            )
            
            if st.button("🗑️ Remove Mapping", type="secondary"):
                if selected_device:
                    try:
                        success = bw_manager.remove_device_mapping(selected_device)
                        if success:
                            st.success(f"✅ Removed mapping for {selected_device}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to remove mapping")
                    except Exception as e:
                        st.error(f"❌ Remove error: {e}")
        else:
            st.info("📝 No device mappings configured yet.")
            st.write("Device mappings are created automatically when you search for credentials, or you can create them manually from the Vault Browser.")
            
    except Exception as e:
        st.error(f"❌ Failed to load mappings: {e}")


def render_connection_testing():
    """Render connection testing interface."""
    st.subheader("🧪 Connection Testing")
    
    st.info("""
    **Connection Testing** allows you to test SSH connections using BitWarden credentials.
    This helps verify that your credential mappings are working correctly.
    """)
    
    # Initialize enhanced connector
    if 'enhanced_connector' not in st.session_state:
        st.session_state.enhanced_connector = EnhancedSSHConnector()
    
    connector = st.session_state.enhanced_connector
    
    # BitWarden connection test
    st.subheader("🔐 BitWarden Connection Test")
    
    if st.button("🔍 Test BitWarden Connection"):
        with st.spinner("Testing BitWarden connection..."):
            result = connector.test_bitwarden_connection()
            
            if result['status'] == 'ready':
                st.success(f"✅ {result['message']}")
                
                # Display details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Connection Details:**")
                    st.write(f"- **Authenticated**: {result['authenticated']}")
                    st.write(f"- **Unlocked**: {result['unlocked']}")
                    st.write(f"- **Server**: {result.get('server_url', 'Default')}")
                
                with col2:
                    st.write("**Vault Information:**")
                    st.write(f"- **User**: {result.get('user_email', 'Unknown')}")
                    st.write(f"- **Items**: {result.get('total_items', 0)}")
                    st.write(f"- **Last Sync**: {result.get('last_sync', 'Unknown')}")
                    
            elif result['status'] == 'error':
                st.error(f"❌ {result['message']}")
            else:
                st.warning(f"⚠️ {result['message']}")
    
    # Available credentials display
    st.markdown("---")
    st.subheader("📋 Available Credentials")
    
    if st.button("🔄 Refresh Credentials List"):
        with st.spinner("Loading credentials..."):
            credentials = connector.get_available_credentials()
            
            if credentials:
                st.success(f"Found {len(credentials)} configured credentials")
                
                for cred in credentials:
                    with st.expander(f"🖥️ {cred['device_ip']} ({cred['device_hostname']})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Device Information:**")
                            st.write(f"- **IP Address**: {cred['device_ip']}")
                            st.write(f"- **Hostname**: {cred['device_hostname']}")
                            st.write(f"- **Type**: {cred['device_type']}")
                        
                        with col2:
                            st.write("**Credential Information:**")
                            st.write(f"- **BitWarden Item**: {cred['bitwarden_item_name']}")
                            st.write(f"- **Credential Type**: {cred['credential_type']}")
                            st.write(f"- **Auto-discovered**: {cred['auto_discovered']}")
                            st.write(f"- **Last Verified**: {cred['last_verified'] or 'Never'}")
            else:
                st.info("No credentials configured yet.")
    
    # Device connection test
    st.markdown("---")
    st.subheader("🔌 Device Connection Test")
    
    with st.form("connection_test"):
        st.write("Test SSH connection to a device using BitWarden credentials:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            test_host = st.text_input("Device IP Address", placeholder="192.168.1.1")
            test_port = st.number_input("SSH Port", value=22, min_value=1, max_value=65535)
        
        with col2:
            test_device_type = st.selectbox(
                "Device Type (Optional)",
                ["", "router", "switch", "firewall", "access_point", "server", "other"]
            )
            test_timeout = st.number_input("Timeout (seconds)", value=10, min_value=5, max_value=60)
        
        test_submitted = st.form_submit_button("🧪 Test Connection")
        
        if test_submitted and test_host:
            with st.spinner(f"Testing connection to {test_host}:{test_port}..."):
                try:
                    # This would be a test connection - for demo purposes, we'll just show the attempt
                    st.info(f"🔍 Attempting to connect to {test_host}:{test_port}")
                    st.info(f"🔑 Looking for credentials in BitWarden...")
                    
                    # In a real implementation, you would:
                    # connection = connector.connect_with_bitwarden(
                    #     host=test_host,
                    #     device_type=test_device_type if test_device_type else None,
                    #     port=test_port
                    # )
                    
                    st.success("✅ Connection test completed (demo mode)")
                    st.write("In production, this would attempt an actual SSH connection using BitWarden credentials.")
                    
                except Exception as e:
                    st.error(f"❌ Connection test failed: {e}")


if __name__ == "__main__":
    main()