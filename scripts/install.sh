#!/bin/bash

# NetArchon Installation Script
# For Ubuntu 24.04 LTS Mini PC deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NETARCHON_USER="netarchon"
NETARCHON_HOME="/opt/netarchon"
NETARCHON_DATA="/opt/netarchon/data"
NETARCHON_LOGS="/opt/netarchon/logs"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release; then
        log_error "This script is designed for Ubuntu. Detected: $(lsb_release -d | cut -f2)"
        exit 1
    fi
    
    VERSION=$(lsb_release -rs)
    if [[ "$VERSION" != "24.04" && "$VERSION" != "22.04" ]]; then
        log_warning "This script is optimized for Ubuntu 24.04 LTS. Detected: $VERSION"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

update_system() {
    log_info "Updating system packages..."
    apt update
    apt upgrade -y
    apt install -y build-essential git curl wget python3-pip python3-dev python3-venv
    apt install -y libssl-dev libffi-dev sqlite3 libsqlite3-dev
    apt install -y net-tools iputils-ping
    log_success "System updated successfully"
}

install_docker() {
    log_info "Installing Docker..."
    
    # Remove old versions
    apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Install Docker Compose
    apt install -y docker-compose-plugin
    
    # Add netarchon user to docker group
    usermod -aG docker $NETARCHON_USER 2>/dev/null || true
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    log_success "Docker installed successfully"
}

create_user() {
    log_info "Creating NetArchon user..."
    
    if ! id "$NETARCHON_USER" &>/dev/null; then
        useradd -r -m -d "$NETARCHON_HOME" -s /bin/bash "$NETARCHON_USER"
        log_success "User $NETARCHON_USER created"
    else
        log_info "User $NETARCHON_USER already exists"
    fi
}

setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p "$NETARCHON_HOME"
    mkdir -p "$NETARCHON_DATA"
    mkdir -p "$NETARCHON_LOGS"
    mkdir -p "$NETARCHON_HOME/config"
    mkdir -p "$NETARCHON_HOME/backups"
    
    chown -R "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME"
    chmod 755 "$NETARCHON_HOME"
    chmod 750 "$NETARCHON_DATA"
    chmod 750 "$NETARCHON_LOGS"
    
    log_success "Directories created successfully"
}

install_netarchon() {
    log_info "Installing NetArchon..."
    
    # Clone repository
    if [[ ! -d "$NETARCHON_HOME/netarchon" ]]; then
        cd "$NETARCHON_HOME"
        git clone https://github.com/yourusername/netarchon.git
        chown -R "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME/netarchon"
    else
        log_info "NetArchon repository already exists, updating..."
        cd "$NETARCHON_HOME/netarchon"
        sudo -u "$NETARCHON_USER" git pull
    fi
    
    cd "$NETARCHON_HOME/netarchon"
    
    # Copy configuration files
    if [[ ! -f "$NETARCHON_HOME/config/netarchon.yaml" ]]; then
        cp config/netarchon.yaml.example "$NETARCHON_HOME/config/netarchon.yaml"
        chown "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME/config/netarchon.yaml"
        log_info "Configuration file created at $NETARCHON_HOME/config/netarchon.yaml"
    fi
    
    if [[ ! -f "$NETARCHON_HOME/.env" ]]; then
        cp .env.example "$NETARCHON_HOME/.env"
        chown "$NETARCHON_USER:$NETARCHON_USER" "$NETARCHON_HOME/.env"
        log_info "Environment file created at $NETARCHON_HOME/.env"
    fi
    
    log_success "NetArchon installed successfully"
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    # Install ufw if not present
    apt install -y ufw
    
    # Configure firewall rules
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow NetArchon ports
    ufw allow 8501/tcp comment "NetArchon Web Interface"
    ufw allow 21118/tcp comment "RustDesk Server"
    ufw allow 21117/tcp comment "RustDesk Relay"
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured successfully"
}

create_systemd_services() {
    log_info "Creating systemd services..."
    
    # NetArchon Web Service
    cat > /etc/systemd/system/netarchon-web.service << EOF
[Unit]
Description=NetArchon Web Interface
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$NETARCHON_HOME/netarchon
ExecStart=/usr/bin/docker compose up -d netarchon-web
ExecStop=/usr/bin/docker compose stop netarchon-web
User=$NETARCHON_USER
Group=$NETARCHON_USER

[Install]
WantedBy=multi-user.target
EOF

    # NetArchon Collector Service
    cat > /etc/systemd/system/netarchon-collector.service << EOF
[Unit]
Description=NetArchon Metrics Collector
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$NETARCHON_HOME/netarchon
ExecStart=/usr/bin/docker compose up -d netarchon-collector
ExecStop=/usr/bin/docker compose stop netarchon-collector
User=$NETARCHON_USER
Group=$NETARCHON_USER

[Install]
WantedBy=multi-user.target
EOF

    # NetArchon Alerts Service
    cat > /etc/systemd/system/netarchon-alerts.service << EOF
[Unit]
Description=NetArchon Alert Manager
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$NETARCHON_HOME/netarchon
ExecStart=/usr/bin/docker compose up -d netarchon-alerts
ExecStop=/usr/bin/docker compose stop netarchon-alerts
User=$NETARCHON_USER
Group=$NETARCHON_USER

[Install]
WantedBy=multi-user.target
EOF

    # NetArchon Master Service (starts all components)
    cat > /etc/systemd/system/netarchon.service << EOF
[Unit]
Description=NetArchon Network Management System
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$NETARCHON_HOME/netarchon
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$NETARCHON_USER
Group=$NETARCHON_USER

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    log_success "Systemd services created successfully"
}

setup_logrotate() {
    log_info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/netarchon << EOF
$NETARCHON_LOGS/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $NETARCHON_USER $NETARCHON_USER
    postrotate
        systemctl reload netarchon 2>/dev/null || true
    endscript
}
EOF
    
    log_success "Log rotation configured successfully"
}

configure_network() {
    log_info "Configuring network settings..."
    
    # Get current IP address
    CURRENT_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')
    
    log_info "Current server IP: $CURRENT_IP"
    log_warning "Please ensure this IP is static or configure a static IP"
    log_info "You can access NetArchon at: http://$CURRENT_IP:8501"
    
    # Update environment file with current IP
    sed -i "s/NETARCHON_SERVER_IP=.*/NETARCHON_SERVER_IP=$CURRENT_IP/" "$NETARCHON_HOME/.env"
    
    log_success "Network configuration updated"
}

start_services() {
    log_info "Starting NetArchon services..."
    
    cd "$NETARCHON_HOME/netarchon"
    
    # Build and start containers
    sudo -u "$NETARCHON_USER" docker compose build
    sudo -u "$NETARCHON_USER" docker compose up -d
    
    # Enable systemd services
    systemctl enable netarchon
    systemctl start netarchon
    
    log_success "NetArchon services started successfully"
}

show_status() {
    log_info "Checking service status..."
    
    cd "$NETARCHON_HOME/netarchon"
    sudo -u "$NETARCHON_USER" docker compose ps
    
    echo
    log_info "Service status:"
    systemctl status netarchon --no-pager -l
}

print_summary() {
    echo
    echo "=============================================="
    log_success "NetArchon Installation Complete!"
    echo "=============================================="
    echo
    log_info "Access Information:"
    echo "  Web Interface: http://$(ip route get 1.1.1.1 | grep -oP 'src \K\S+'):8501"
    echo "  Configuration: $NETARCHON_HOME/config/netarchon.yaml"
    echo "  Environment: $NETARCHON_HOME/.env"
    echo "  Data Directory: $NETARCHON_DATA"
    echo "  Logs Directory: $NETARCHON_LOGS"
    echo
    log_info "Service Management:"
    echo "  Start all services: sudo systemctl start netarchon"
    echo "  Stop all services: sudo systemctl stop netarchon"
    echo "  View logs: sudo journalctl -u netarchon -f"
    echo "  Docker logs: cd $NETARCHON_HOME/netarchon && docker compose logs -f"
    echo
    log_info "Next Steps:"
    echo "  1. Edit $NETARCHON_HOME/config/netarchon.yaml for your network"
    echo "  2. Update device IP addresses in $NETARCHON_HOME/.env"
    echo "  3. Configure email/Slack notifications (optional)"
    echo "  4. Access the web interface to complete setup"
    echo
    log_warning "Important: Please review and update the configuration files before first use!"
}

# Main installation process
main() {
    echo "=============================================="
    echo "NetArchon Installation Script"
    echo "Ubuntu 24.04 LTS Mini PC Deployment"
    echo "=============================================="
    echo
    
    check_root
    check_ubuntu
    
    log_info "Starting NetArchon installation..."
    
    update_system
    install_docker
    create_user
    setup_directories
    install_netarchon
    setup_firewall
    create_systemd_services
    setup_logrotate
    configure_network
    start_services
    
    sleep 5  # Give services time to start
    
    show_status
    print_summary
}

# Run main function
main "$@"