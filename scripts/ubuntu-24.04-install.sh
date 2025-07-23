#!/bin/bash
# NetArchon Ubuntu 24.04.2 LTS Server Installation Script
# This script automates the complete installation of NetArchon on Ubuntu 24.04.2 LTS Server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NETARCHON_USER="netarchon"
NETARCHON_HOME="/opt/netarchon"
NETARCHON_PORT="8501"
PYTHON_VERSION="3.12"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Check Ubuntu version
check_ubuntu_version() {
    log "Checking Ubuntu version..."
    
    if ! command -v lsb_release &> /dev/null; then
        error "lsb_release not found. Please ensure you're running Ubuntu 24.04.2 LTS."
        exit 1
    fi
    
    VERSION=$(lsb_release -rs)
    CODENAME=$(lsb_release -cs)
    
    if [[ "$VERSION" != "24.04" ]]; then
        error "This script is designed for Ubuntu 24.04.2 LTS. Detected version: $VERSION"
        exit 1
    fi
    
    log "Ubuntu $VERSION ($CODENAME) detected - compatible!"
}

# Update system packages
update_system() {
    log "Updating system packages..."
    
    sudo apt update
    sudo apt upgrade -y
    
    log "System packages updated successfully"
}

# Install required packages
install_packages() {
    log "Installing required packages..."
    
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        sqlite3 \
        nginx \
        fail2ban \
        ufw \
        htop \
        curl \
        wget \
        unzip \
        build-essential \
        libssl-dev \
        libffi-dev \
        libsqlite3-dev
    
    log "Required packages installed successfully"
}

# Create NetArchon user and directories
create_user_and_directories() {
    log "Creating NetArchon user and directories..."
    
    # Create system user (no shell login for security)
    if ! id "$NETARCHON_USER" &>/dev/null; then
        sudo useradd -r -s /bin/false -d "$NETARCHON_HOME" -m "$NETARCHON_USER"
        log "Created NetArchon system user"
    else
        warning "NetArchon user already exists"
    fi
    
    # Create directory structure
    sudo mkdir -p "$NETARCHON_HOME"/{data,logs,config,backups}
    sudo chown -R "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME"
    sudo chmod 755 "$NETARCHON_HOME"
    sudo chmod 750 "$NETARCHON_HOME"/{data,logs,config,backups}
    
    log "Directory structure created successfully"
}

# Install NetArchon
install_netarchon() {
    log "Installing NetArchon..."
    
    # Change to NetArchon directory
    cd "$NETARCHON_HOME"
    
    # Clone repository as NetArchon user
    sudo -u "$NETARCHON_USER" git clone https://github.com/diszay/AINetwork.git .
    
    # Create Python virtual environment
    sudo -u "$NETARCHON_USER" python3 -m venv venv
    
    # Install Python dependencies
    sudo -u "$NETARCHON_USER" bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-web.txt
        pip install streamlit plotly pandas numpy paramiko cryptography
    "
    
    log "NetArchon installed successfully"
}

# Configure systemd service
configure_systemd_service() {
    log "Configuring systemd service..."
    
    sudo tee /etc/systemd/system/netarchon.service > /dev/null <<EOF
[Unit]
Description=NetArchon Network Monitoring System
Documentation=https://github.com/diszay/AINetwork
After=network.target
Wants=network.target

[Service]
Type=simple
User=$NETARCHON_USER
Group=$NETARCHON_USER
WorkingDirectory=$NETARCHON_HOME
Environment=PATH=$NETARCHON_HOME/venv/bin
Environment=PYTHONPATH=$NETARCHON_HOME/src
Environment=STREAMLIT_SERVER_HEADLESS=true
Environment=STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ExecStart=$NETARCHON_HOME/venv/bin/streamlit run src/netarchon/web/streamlit_app.py --server.port $NETARCHON_PORT --server.address 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$NETARCHON_HOME/data
ReadWritePaths=$NETARCHON_HOME/logs
ReadWritePaths=$NETARCHON_HOME/backups

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable netarchon
    
    log "systemd service configured successfully"
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    # Configure UFW
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (current connection)
    sudo ufw allow ssh
    
    # Allow NetArchon web interface
    sudo ufw allow $NETARCHON_PORT/tcp comment "NetArchon Web Interface"
    
    # Enable firewall
    sudo ufw --force enable
    
    log "Firewall configured successfully"
}

# Configure fail2ban
configure_fail2ban() {
    log "Configuring fail2ban..."
    
    # Create NetArchon jail configuration
    sudo tee /etc/fail2ban/jail.d/netarchon.conf > /dev/null <<EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600

[netarchon]
enabled = true
port = $NETARCHON_PORT
filter = netarchon
logpath = $NETARCHON_HOME/logs/netarchon.log
maxretry = 5
bantime = 1800
findtime = 300
EOF
    
    # Create NetArchon filter
    sudo tee /etc/fail2ban/filter.d/netarchon.conf > /dev/null <<EOF
[Definition]
failregex = ^.*\[ERROR\].*Failed login attempt from <HOST>.*$
            ^.*\[WARNING\].*Suspicious activity from <HOST>.*$
ignoreregex =
EOF
    
    # Restart fail2ban
    sudo systemctl restart fail2ban
    sudo systemctl enable fail2ban
    
    log "fail2ban configured successfully"
}

# Configure automatic updates
configure_auto_updates() {
    log "Configuring automatic security updates..."
    
    sudo apt install -y unattended-upgrades
    
    # Configure unattended upgrades
    sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null <<EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
    "\${distro_id}ESMApps:\${distro_codename}-apps-security";
    "\${distro_id}ESM:\${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
    
    # Enable automatic updates
    sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
    
    log "Automatic security updates configured successfully"
}

# Create backup script
create_backup_script() {
    log "Creating backup script..."
    
    sudo tee "$NETARCHON_HOME/scripts/backup.sh" > /dev/null <<'EOF'
#!/bin/bash
# NetArchon Backup Script

BACKUP_DIR="/opt/netarchon/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="netarchon_backup_$DATE.tar.gz"

# Create backup
cd /opt/netarchon
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    config/ data/ src/

# Keep only last 30 backups
find "$BACKUP_DIR" -name "netarchon_backup_*.tar.gz" -type f -mtime +30 -delete

echo "Backup created: $BACKUP_FILE"
EOF
    
    sudo mkdir -p "$NETARCHON_HOME/scripts"
    sudo chown "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME/scripts/backup.sh"
    sudo chmod +x "$NETARCHON_HOME/scripts/backup.sh"
    
    # Add to crontab for NetArchon user
    sudo -u "$NETARCHON_USER" bash -c '
        (crontab -l 2>/dev/null; echo "0 2 * * * /opt/netarchon/scripts/backup.sh") | crontab -
    '
    
    log "Backup script created and scheduled"
}

# Create health check script
create_health_check_script() {
    log "Creating health check script..."
    
    sudo tee "$NETARCHON_HOME/scripts/health-check.sh" > /dev/null <<'EOF'
#!/bin/bash
# NetArchon Health Check Script

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check service status
check_service() {
    if systemctl is-active --quiet netarchon; then
        echo -e "${GREEN}✓ NetArchon service is running${NC}"
        return 0
    else
        echo -e "${RED}✗ NetArchon service is not running${NC}"
        return 1
    fi
}

# Check web interface
check_web_interface() {
    if curl -s http://localhost:8501 > /dev/null; then
        echo -e "${GREEN}✓ Web interface is accessible${NC}"
        return 0
    else
        echo -e "${RED}✗ Web interface is not accessible${NC}"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    USAGE=$(df /opt/netarchon | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓ Disk space OK ($USAGE% used)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Disk space warning ($USAGE% used)${NC}"
        return 1
    fi
}

# Check memory usage
check_memory() {
    USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓ Memory usage OK ($USAGE% used)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Memory usage high ($USAGE% used)${NC}"
        return 1
    fi
}

# Run all checks
echo "NetArchon Health Check - $(date)"
echo "=================================="

check_service
check_web_interface
check_disk_space
check_memory

echo "=================================="
echo "Health check completed"
EOF
    
    sudo chown "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME/scripts/health-check.sh"
    sudo chmod +x "$NETARCHON_HOME/scripts/health-check.sh"
    
    log "Health check script created"
}

# Start NetArchon service
start_netarchon() {
    log "Starting NetArchon service..."
    
    sudo systemctl start netarchon
    
    # Wait for service to start
    sleep 5
    
    if sudo systemctl is-active --quiet netarchon; then
        log "NetArchon service started successfully"
    else
        error "Failed to start NetArchon service"
        sudo journalctl -u netarchon --no-pager -n 20
        exit 1
    fi
}

# Display installation summary
display_summary() {
    local SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo
    echo "=================================="
    echo -e "${GREEN}NetArchon Installation Complete!${NC}"
    echo "=================================="
    echo
    echo "🎉 NetArchon has been successfully installed on Ubuntu 24.04.2 LTS Server"
    echo
    echo "📊 Access your NetArchon dashboard:"
    echo "   • Local access: http://localhost:$NETARCHON_PORT"
    echo "   • Network access: http://$SERVER_IP:$NETARCHON_PORT"
    echo
    echo "🔧 Service management:"
    echo "   • Check status: sudo systemctl status netarchon"
    echo "   • View logs: sudo journalctl -u netarchon -f"
    echo "   • Restart service: sudo systemctl restart netarchon"
    echo
    echo "🛠️ Useful commands:"
    echo "   • Health check: sudo -u $NETARCHON_USER $NETARCHON_HOME/scripts/health-check.sh"
    echo "   • Manual backup: sudo -u $NETARCHON_USER $NETARCHON_HOME/scripts/backup.sh"
    echo "   • View firewall: sudo ufw status"
    echo
    echo "📚 Next steps:"
    echo "   1. Open your web browser and go to http://$SERVER_IP:$NETARCHON_PORT"
    echo "   2. Add your first network device using the web interface"
    echo "   3. Configure monitoring and alerts"
    echo "   4. Review the User Guide: https://github.com/diszay/AINetwork/docs/user_guide.md"
    echo
    echo "🔒 Security features enabled:"
    echo "   • UFW firewall configured"
    echo "   • fail2ban intrusion detection active"
    echo "   • Automatic security updates enabled"
    echo "   • Service running with restricted privileges"
    echo
    echo "💾 Automatic backups scheduled daily at 2:00 AM"
    echo
    echo "🆘 Need help? Check the troubleshooting guide or create an issue on GitHub"
    echo
}

# Main installation function
main() {
    echo "=================================="
    echo "NetArchon Ubuntu 24.04.2 LTS Server Installer"
    echo "=================================="
    echo
    
    check_root
    check_ubuntu_version
    update_system
    install_packages
    create_user_and_directories
    install_netarchon
    configure_systemd_service
    configure_firewall
    configure_fail2ban
    configure_auto_updates
    create_backup_script
    create_health_check_script
    start_netarchon
    display_summary
}

# Run installation
main "$@"