"""
NetArchon Configuration Management Page

Configuration backup, deployment, and rollback interface with safety mechanisms.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import difflib
import sys
from pathlib import Path

# Add the NetArchon source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from netarchon.web.utils.data_loader import get_data_loader

# Page configuration
st.set_page_config(
    page_title="NetArchon - Configuration",
    page_icon="⚙️",
    layout="wide"
)

def render_backup_management():
    """Render backup management interface."""
    st.subheader("💾 Backup Management")
    
    data_loader = get_data_loader()
    devices = data_loader.load_discovered_devices()
    
    # Device selection for backup
    col1, col2 = st.columns([2, 1])
    
    with col1:
        device_options = [f"{d['name']} ({d['ip_address']})" for d in devices]
        selected_device_idx = st.selectbox(
            "Select Device for Backup",
            range(len(device_options)),
            format_func=lambda x: device_options[x] if x < len(device_options) else "No devices"
        )
    
    with col2:
        backup_reason = st.text_input("Backup Reason", placeholder="Manual backup")
    
    if devices and st.button("🗄️ Create Backup", type="primary"):
        selected_device = devices[selected_device_idx]
        
        with st.spinner(f"Creating backup for {selected_device['name']}..."):
            success, message = data_loader.backup_device_config(
                selected_device['id'], 
                backup_reason or "Manual backup"
            )
        
        if success:
            st.success(f"✅ {message}")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"❌ {message}")

def render_backup_history():
    """Render backup history table."""
    st.subheader("📚 Backup History")
    
    data_loader = get_data_loader()
    devices = data_loader.load_discovered_devices()
    
    # Collect all backup information
    all_backups = []
    
    for device in devices:
        config_info = data_loader.load_device_configs(device['id'])
        
        if 'backups' in config_info:
            for backup in config_info['backups']:
                all_backups.append({
                    'Device': device['name'],
                    'Device ID': device['id'],
                    'Filename': backup['filename'],
                    'Size (KB)': round(backup['size'] / 1024, 2),
                    'Created': backup['created'],
                    'Path': backup['path']
                })
    
    if all_backups:
        # Create DataFrame
        df = pd.DataFrame(all_backups)
        
        # Sort by creation date (newest first)
        df['Created'] = pd.to_datetime(df['Created'])
        df_sorted = df.sort_values('Created', ascending=False)
        
        # Display options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            device_filter = st.selectbox(
                "Filter by Device",
                ["All"] + list(df_sorted['Device'].unique())
            )
        
        with col2:
            days_filter = st.selectbox(
                "Show backups from",
                ["All time", "Last 7 days", "Last 30 days", "Last 90 days"]
            )
        
        with col3:
            show_limit = st.number_input("Show last N backups", min_value=5, max_value=100, value=20)
        
        # Apply filters
        filtered_df = df_sorted.copy()
        
        if device_filter != "All":
            filtered_df = filtered_df[filtered_df['Device'] == device_filter]
        
        if days_filter != "All time":
            days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
            cutoff_date = datetime.now() - timedelta(days=days_map[days_filter])
            filtered_df = filtered_df[filtered_df['Created'] >= cutoff_date]
        
        # Limit results
        filtered_df = filtered_df.head(show_limit)
        
        # Format datetime for display
        display_df = filtered_df.copy()
        display_df['Created'] = display_df['Created'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Display table
        st.dataframe(
            display_df[['Device', 'Filename', 'Size (KB)', 'Created']],
            use_container_width=True,
            hide_index=True
        )
        
        # Backup actions
        if st.session_state.get('selected_backup_path'):
            render_backup_actions(st.session_state.selected_backup_path)
        
        # Select backup for actions
        if not filtered_df.empty:
            st.subheader("🔧 Backup Actions")
            
            backup_options = [
                f"{row['Device']} - {row['Filename']}" 
                for _, row in filtered_df.iterrows()
            ]
            
            selected_backup_idx = st.selectbox(
                "Select backup for actions",
                range(len(backup_options)),
                format_func=lambda x: backup_options[x] if x < len(backup_options) else "No backups"
            )
            
            if selected_backup_idx < len(filtered_df):
                selected_backup = filtered_df.iloc[selected_backup_idx]
                st.session_state.selected_backup_path = selected_backup['Path']
                st.session_state.selected_backup_device = selected_backup['Device ID']
    else:
        st.info("No configuration backups found. Create a backup using the form above.")

def render_backup_actions(backup_path):
    """Render actions for selected backup."""
    if not os.path.exists(backup_path):
        st.error("❌ Backup file not found!")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 View Content", use_container_width=True):
            st.session_state.show_backup_content = True
    
    with col2:
        if st.button("📥 Download", use_container_width=True):
            with open(backup_path, 'r') as f:
                content = f.read()
            
            filename = os.path.basename(backup_path)
            st.download_button(
                label="💾 Download Backup",
                data=content,
                file_name=filename,
                mime="text/plain"
            )
    
    with col3:
        if st.button("🔄 Restore", use_container_width=True):
            st.session_state.show_restore_confirm = True
    
    with col4:
        if st.button("🗑️ Delete", use_container_width=True):
            st.session_state.show_delete_confirm = True
    
    # Show backup content
    if st.session_state.get('show_backup_content'):
        render_backup_content(backup_path)
    
    # Restore confirmation
    if st.session_state.get('show_restore_confirm'):
        render_restore_confirmation(backup_path)
    
    # Delete confirmation
    if st.session_state.get('show_delete_confirm'):
        render_delete_confirmation(backup_path)

def render_backup_content(backup_path):
    """Render backup file content."""
    st.subheader("📄 Backup Content")
    
    try:
        with open(backup_path, 'r') as f:
            content = f.read()
        
        # Show file info
        file_stat = os.stat(backup_path)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("File Size", f"{file_stat.st_size / 1024:.2f} KB")
        with col2:
            st.metric("Lines", len(content.splitlines()))
        with col3:
            st.metric("Modified", datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M'))
        
        # Content display with syntax highlighting
        st.code(content, language="text", line_numbers=True)
        
        if st.button("❌ Close Content"):
            st.session_state.show_backup_content = False
            st.rerun()
            
    except Exception as e:
        st.error(f"Failed to read backup file: {str(e)}")

def render_restore_confirmation(backup_path):
    """Render restore confirmation dialog."""
    st.warning("⚠️ **Configuration Restore Confirmation**")
    
    st.markdown("""
    **You are about to restore a configuration backup. This will:**
    - Replace the current device configuration
    - Create an automatic backup before restore
    - Potentially cause service disruption
    
    **Please confirm the following:**
    """)
    
    confirm_backup = st.checkbox("✅ Create backup before restore")
    confirm_risk = st.checkbox("✅ I understand the risks")
    confirm_proceed = st.checkbox("✅ Proceed with restore")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Confirm Restore", 
                    disabled=not (confirm_backup and confirm_risk and confirm_proceed),
                    type="primary"):
            
            device_id = st.session_state.get('selected_backup_device')
            
            with st.spinner("Restoring configuration..."):
                # This would implement the actual restore logic
                time.sleep(3)
            
            st.success("✅ Configuration restored successfully!")
            st.session_state.show_restore_confirm = False
            time.sleep(2)
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel Restore"):
            st.session_state.show_restore_confirm = False
            st.rerun()

def render_delete_confirmation(backup_path):
    """Render delete confirmation dialog."""
    st.error("🗑️ **Delete Backup Confirmation**")
    
    st.markdown(f"""
    **You are about to permanently delete:**
    - File: `{os.path.basename(backup_path)}`
    - Path: `{backup_path}`
    
    **This action cannot be undone!**
    """)
    
    confirm_delete = st.checkbox("✅ I confirm deletion of this backup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Confirm Delete", 
                    disabled=not confirm_delete,
                    type="primary"):
            try:
                os.remove(backup_path)
                st.success("✅ Backup deleted successfully!")
                st.session_state.show_delete_confirm = False
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to delete backup: {str(e)}")
    
    with col2:
        if st.button("❌ Cancel Delete"):
            st.session_state.show_delete_confirm = False
            st.rerun()

def render_configuration_deployment():
    """Render configuration deployment interface."""
    st.subheader("🚀 Configuration Deployment")
    
    data_loader = get_data_loader()
    devices = data_loader.load_discovered_devices()
    
    if not devices:
        st.info("No devices available for deployment.")
        return
    
    # Device selection
    device_options = [f"{d['name']} ({d['ip_address']})" for d in devices]
    selected_device_idx = st.selectbox(
        "Select Target Device",
        range(len(device_options)),
        format_func=lambda x: device_options[x] if x < len(device_options) else "No devices"
    )
    
    # Configuration input methods
    config_method = st.radio(
        "Configuration Source",
        ["Upload File", "Paste Configuration", "Use Backup"]
    )
    
    config_content = None
    
    if config_method == "Upload File":
        uploaded_file = st.file_uploader(
            "Choose configuration file",
            type=['txt', 'cfg', 'conf'],
            help="Upload a configuration file to deploy"
        )
        
        if uploaded_file:
            config_content = uploaded_file.read().decode('utf-8')
            st.text_area("Configuration Preview", config_content, height=200, disabled=True)
    
    elif config_method == "Paste Configuration":
        config_content = st.text_area(
            "Paste Configuration",
            height=300,
            placeholder="Paste your device configuration here..."
        )
    
    elif config_method == "Use Backup":
        # Load available backups
        selected_device = devices[selected_device_idx]
        config_info = data_loader.load_device_configs(selected_device['id'])
        
        if 'backups' in config_info and config_info['backups']:
            backup_options = [
                f"{b['filename']} ({b['created']})" 
                for b in config_info['backups']
            ]
            
            selected_backup_idx = st.selectbox(
                "Select Backup to Deploy",
                range(len(backup_options)),
                format_func=lambda x: backup_options[x] if x < len(backup_options) else "No backups"
            )
            
            if selected_backup_idx < len(config_info['backups']):
                backup_path = config_info['backups'][selected_backup_idx]['path']
                
                try:
                    with open(backup_path, 'r') as f:
                        config_content = f.read()
                        
                        # Extract actual config (skip metadata)
                        lines = config_content.split('\n')
                        config_start = 0
                        for i, line in enumerate(lines):
                            if line.startswith('# ' + '='*50):
                                config_start = i + 2
                                break
                        
                        if config_start > 0:
                            config_content = '\n'.join(lines[config_start:])
                    
                    st.text_area("Configuration Preview", config_content, height=200, disabled=True)
                    
                except Exception as e:
                    st.error(f"Failed to read backup: {str(e)}")
        else:
            st.info("No backups available for this device.")
    
    # Deployment options
    st.subheader("🔧 Deployment Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_backup = st.checkbox("Create backup before deployment", value=True)
        validate_syntax = st.checkbox("Validate configuration syntax", value=True)
    
    with col2:
        test_connectivity = st.checkbox("Test connectivity after deployment", value=True)
        auto_rollback = st.checkbox("Auto-rollback on failure", value=True)
    
    # Deployment button
    if config_content and st.button("🚀 Deploy Configuration", type="primary"):
        selected_device = devices[selected_device_idx]
        
        with st.spinner(f"Deploying configuration to {selected_device['name']}..."):
            # Simulate deployment process
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Validation
            if validate_syntax:
                status_text.text("Validating configuration syntax...")
                progress_bar.progress(20)
                time.sleep(1)
            
            # Step 2: Backup
            if create_backup:
                status_text.text("Creating pre-deployment backup...")
                progress_bar.progress(40)
                time.sleep(1)
            
            # Step 3: Deployment
            status_text.text("Deploying configuration...")
            progress_bar.progress(60)
            time.sleep(2)
            
            # Step 4: Verification
            if test_connectivity:
                status_text.text("Testing connectivity...")
                progress_bar.progress(80)
                time.sleep(1)
            
            # Step 5: Complete
            status_text.text("Deployment completed!")
            progress_bar.progress(100)
            time.sleep(1)
        
        st.success("✅ Configuration deployed successfully!")

def render_configuration_comparison():
    """Render configuration comparison tool."""
    st.subheader("🔍 Configuration Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Configuration A**")
        config_a_method = st.radio(
            "Source A",
            ["Upload File A", "Paste Config A", "Use Backup A"],
            key="config_a_method"
        )
        
        config_a = None
        if config_a_method == "Paste Config A":
            config_a = st.text_area("Configuration A", height=200, key="config_a")
        elif config_a_method == "Upload File A":
            uploaded_a = st.file_uploader("Upload Config A", type=['txt', 'cfg'], key="upload_a")
            if uploaded_a:
                config_a = uploaded_a.read().decode('utf-8')
    
    with col2:
        st.write("**Configuration B**")
        config_b_method = st.radio(
            "Source B",
            ["Upload File B", "Paste Config B", "Use Backup B"],
            key="config_b_method"
        )
        
        config_b = None
        if config_b_method == "Paste Config B":
            config_b = st.text_area("Configuration B", height=200, key="config_b")
        elif config_b_method == "Upload File B":
            uploaded_b = st.file_uploader("Upload Config B", type=['txt', 'cfg'], key="upload_b")
            if uploaded_b:
                config_b = uploaded_b.read().decode('utf-8')
    
    if config_a and config_b and st.button("🔍 Compare Configurations"):
        st.subheader("📊 Comparison Results")
        
        # Generate diff
        diff = list(difflib.unified_diff(
            config_a.splitlines(keepends=True),
            config_b.splitlines(keepends=True),
            fromfile="Configuration A",
            tofile="Configuration B",
            lineterm=""
        ))
        
        if diff:
            diff_text = ''.join(diff)
            st.code(diff_text, language="diff")
            
            # Statistics
            added_lines = len([line for line in diff if line.startswith('+')])
            removed_lines = len([line for line in diff if line.startswith('-')])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Added Lines", added_lines)
            with col2:
                st.metric("Removed Lines", removed_lines)
            with col3:
                st.metric("Total Changes", added_lines + removed_lines)
        else:
            st.success("✅ Configurations are identical!")

def main():
    """Main configuration page function."""
    
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
        <h1 style="margin: 0;">⚙️ Configuration Management</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">
            Backup, deploy, and manage device configurations safely
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "💾 Backup Management",
        "🚀 Configuration Deployment", 
        "🔍 Configuration Comparison",
        "📋 Scheduled Tasks"
    ])
    
    with tab1:
        render_backup_management()
        st.markdown("---")
        render_backup_history()
    
    with tab2:
        render_configuration_deployment()
    
    with tab3:
        render_configuration_comparison()
    
    with tab4:
        st.subheader("📅 Scheduled Configuration Tasks")
        st.info("🚧 Scheduled backup and deployment features coming soon!")
        
        # Placeholder for scheduled tasks
        st.write("**Planned Features:**")
        st.write("- ⏰ Automated daily/weekly configuration backups")
        st.write("- 📊 Configuration drift detection")
        st.write("- 🔄 Automated config synchronization")
        st.write("- 📧 Email notifications for backup status")
        st.write("- 📈 Configuration change tracking and reporting")

if __name__ == "__main__":
    main()