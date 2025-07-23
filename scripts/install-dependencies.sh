#!/bin/bash
# NetArchon Dependencies Installation Script for Ubuntu 24.04.2 LTS Server
# This script installs all required dependencies for NetArchon deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.12"
NODE_VERSION="20"

# Logging functions
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
    log "Checking Ubuntu version compatibility..."
    
    if ! command -v lsb_release &> /dev/null; then
        error "lsb_release not found. Please ensure you're running Ubuntu 24.04.2 LTS."
        exit 1
    fi
    
    VERSION=$(lsb_release -rs)
    CODENAME=$(lsb_release -cs)
    
    if [[ "$VERSION" != "24.04" ]]; then
        error "This script is optimized for Ubuntu 24.04.2 LTS. Detected version: $VERSION"
        warning "Continuing anyway, but some packages may not be available or compatible."
    fi
    
    log "Ubuntu $VERSION ($CODENAME) detected"
}

# Update system packages
update_system() {
    log "Updating system package lists..."
    sudo apt update
    
    log "Upgrading existing packages..."
    sudo apt upgrade -y
    
    log "System packages updated successfully"
}

# Install system dependencies
install_system_dependencies() {
    log "Installing system dependencies..."
    
    # Core system packages
    sudo apt install -y \
        curl \
        wget \
        git \
        unzip \
        zip \
        htop \
        tree \
        nano \
        vim \
        tmux \
        screen \
        net-tools \
        dnsutils \
        iputils-ping \
        traceroute \
        nmap \
        tcpdump \
        iftop \
        nethogs \
        iotop \
        lsof \
        strace \
        jq \
        bc \
        rsync \
        cron \
        logrotate \
        fail2ban \
        ufw \
        ca-certificates \
        gnupg \
        lsb-release \
        software-properties-common \
        apt-transport-https
    
    log "System dependencies installed successfully"
}

# Install Python and related packages
install_python_dependencies() {
    log "Installing Python $PYTHON_VERSION and related packages..."
    
    # Python packages
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        python3-wheel \
        python3-distutils \
        python3-apt \
        python3-yaml \
        python3-requests \
        python3-urllib3 \
        python3-certifi \
        python3-chardet \
        python3-idna
    
    # Verify Python version
    INSTALLED_PYTHON=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "$INSTALLED_PYTHON" == "3.12" ]]; then
        log "Python $INSTALLED_PYTHON installed successfully"
    else
        warning "Expected Python 3.12, but got $INSTALLED_PYTHON"
    fi
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    log "Python dependencies installed successfully"
}

# Install development tools
install_development_tools() {
    log "Installing development tools..."
    
    sudo apt install -y \
        build-essential \
        gcc \
        g++ \
        make \
        cmake \
        pkg-config \
        autoconf \
        automake \
        libtool \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libxcb1-dev
    
    log "Development tools installed successfully"
}

# Install database dependencies
install_database_dependencies() {
    log "Installing database dependencies..."
    
    sudo apt install -y \
        sqlite3 \
        libsqlite3-dev \
        postgresql-client \
        libpq-dev \
        mysql-client \
        libmysqlclient-dev \
        redis-tools
    
    log "Database dependencies installed successfully"
}

# Install network and security tools
install_network_security_tools() {
    log "Installing network and security tools..."
    
    sudo apt install -y \
        openssh-server \
        openssh-client \
        openssl \
        ca-certificates \
        gnupg2 \
        curl \
        wget \
        netcat-openbsd \
        telnet \
        whois \
        dig \
        nslookup \
        host \
        mtr-tiny \
        iperf3 \
        speedtest-cli \
        wireshark-common \
        tshark
    
    log "Network and security tools installed successfully"
}

# Install Node.js (for potential web development)
install_nodejs() {
    log "Installing Node.js $NODE_VERSION..."
    
    # Add NodeSource repository
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
    
    # Install Node.js
    sudo apt install -y nodejs
    
    # Verify installation
    NODE_INSTALLED=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ "$NODE_INSTALLED" == "$NODE_VERSION" ]]; then
        log "Node.js $NODE_INSTALLED installed successfully"
    else
        warning "Expected Node.js $NODE_VERSION, but got $NODE_INSTALLED"
    fi
    
    # Install global npm packages
    sudo npm install -g \
        pm2 \
        nodemon \
        http-server \
        json-server
    
    log "Node.js and global packages installed successfully"
}

# Install Docker (optional but useful)
install_docker() {
    log "Installing Docker..."
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add Docker repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package list
    sudo apt update
    
    # Install Docker
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Enable and start Docker
    sudo systemctl enable docker
    sudo systemctl start docker
    
    log "Docker installed successfully"
    warning "You may need to log out and back in for Docker group membership to take effect"
}

# Install Python packages for NetArchon
install_python_packages() {
    log "Installing Python packages for NetArchon..."
    
    # Create temporary virtual environment to test package installation
    python3 -m venv /tmp/test_venv
    source /tmp/test_venv/bin/activate
    
    # Core packages
    pip install --upgrade pip setuptools wheel
    
    # NetArchon dependencies
    pip install \
        streamlit>=1.28.0 \
        plotly>=5.15.0 \
        pandas>=2.0.0 \
        numpy>=1.24.0 \
        paramiko>=3.0.0 \
        cryptography>=41.0.0 \
        pyyaml>=6.0 \
        requests>=2.31.0 \
        urllib3>=2.0.0 \
        certifi>=2023.0.0 \
        charset-normalizer>=3.0.0 \
        idna>=3.4 \
        click>=8.0.0 \
        jinja2>=3.1.0 \
        markupsafe>=2.1.0 \
        itsdangerous>=2.1.0 \
        werkzeug>=2.3.0 \
        flask>=2.3.0 \
        gunicorn>=21.0.0 \
        psutil>=5.9.0 \
        netifaces>=0.11.0 \
        netaddr>=0.8.0 \
        scapy>=2.5.0 \
        python-nmap>=0.7.1
    
    # Test imports
    python -c "import streamlit, plotly, pandas, numpy, paramiko, cryptography" || {
        error "Failed to import required packages"
        deactivate
        rm -rf /tmp/test_venv
        exit 1
    }
    
    deactivate
    rm -rf /tmp/test_venv
    
    log "Python packages verified successfully"
}

# Configure system services
configure_system_services() {
    log "Configuring system services..."
    
    # Configure SSH
    sudo systemctl enable ssh
    sudo systemctl start ssh
    
    # Configure UFW firewall
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw --force enable
    
    # Configure fail2ban
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    # Configure automatic updates
    sudo apt install -y unattended-upgrades
    echo 'APT::Periodic::Update-Package-Lists "1";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
    echo 'APT::Periodic::Unattended-Upgrade "1";' | sudo tee -a /etc/apt/apt.conf.d/20auto-upgrades
    
    log "System services configured successfully"
}

# Create useful aliases and functions
create_cli_helpers() {
    log "Creating CLI helpers and aliases..."
    
    # Create .bash_aliases file
    cat >> ~/.bash_aliases << 'EOF'
# NetArchon CLI Helpers
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

# System monitoring
alias ports='netstat -tulanp'
alias meminfo='free -m -l -t'
alias psmem='ps auxf | sort -nr -k 4'
alias psmem10='ps auxf | sort -nr -k 4 | head -10'
alias pscpu='ps auxf | sort -nr -k 3'
alias pscpu10='ps auxf | sort -nr -k 3 | head -10'
alias cpuinfo='lscpu'
alias gpumeminfo='grep -i --color memory /proc/meminfo'

# Network tools
alias myip='curl -s ifconfig.me'
alias netlisteners='netstat -tulpn | grep LISTEN'
alias netcons='netstat -ntu | grep ESTABLISHED'

# NetArchon specific
alias netarchon-status='sudo systemctl status netarchon'
alias netarchon-logs='sudo journalctl -u netarchon -f'
alias netarchon-restart='sudo systemctl restart netarchon'
alias netarchon-health='sudo -u netarchon /opt/netarchon/scripts/health-check.sh'

# Docker helpers (if Docker is installed)
alias dps='docker ps'
alias dpsa='docker ps -a'
alias di='docker images'
alias dlog='docker logs'
alias dexec='docker exec -it'
EOF
    
    # Source the aliases
    echo "source ~/.bash_aliases" >> ~/.bashrc
    
    log "CLI helpers created successfully"
}

# Display installation summary
display_summary() {
    echo
    echo "=================================="
    echo -e "${GREEN}Dependencies Installation Complete!${NC}"
    echo "=================================="
    echo
    echo "🎉 All dependencies for NetArchon have been successfully installed on Ubuntu 24.04.2 LTS"
    echo
    echo "📦 Installed Components:"
    echo "   • Python 3.12 with development tools"
    echo "   • Node.js $NODE_VERSION with npm packages"
    echo "   • Docker with docker-compose"
    echo "   • Database tools (SQLite, PostgreSQL client, MySQL client)"
    echo "   • Network and security tools"
    echo "   • Development and build tools"
    echo "   • System monitoring utilities"
    echo
    echo "🔧 System Configuration:"
    echo "   • UFW firewall enabled with SSH access"
    echo "   • fail2ban configured for intrusion detection"
    echo "   • Automatic security updates enabled"
    echo "   • SSH server enabled and running"
    echo "   • Docker service enabled"
    echo
    echo "🚀 Next Steps:"
    echo "   1. Log out and back in (for Docker group membership)"
    echo "   2. Run the NetArchon installation script:"
    echo "      curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/ubuntu-24.04-install.sh | bash"
    echo "   3. Or clone the repository and install manually:"
    echo "      git clone https://github.com/diszay/AINetwork.git"
    echo "      cd AINetwork && ./scripts/ubuntu-24.04-install.sh"
    echo
    echo "💡 Useful Commands (added to ~/.bash_aliases):"
    echo "   • netarchon-status    - Check NetArchon service status"
    echo "   • netarchon-logs      - View NetArchon logs"
    echo "   • netarchon-health    - Run health check"
    echo "   • ports               - Show open ports"
    echo "   • meminfo             - Show memory information"
    echo "   • myip                - Show public IP address"
    echo
    echo "📚 Documentation:"
    echo "   • Installation Guide: docs/installation.md"
    echo "   • Ubuntu Deployment: docs/ubuntu-deployment.md"
    echo "   • CLI Usage Guide: docs/cli-usage.md"
    echo
    echo "🔄 To reload your shell with new aliases:"
    echo "   source ~/.bashrc"
    echo
}

# Main installation function
main() {
    echo "=================================="
    echo "NetArchon Dependencies Installer"
    echo "Ubuntu 24.04.2 LTS Server"
    echo "=================================="
    echo
    
    check_root
    check_ubuntu_version
    update_system
    install_system_dependencies
    install_python_dependencies
    install_development_tools
    install_database_dependencies
    install_network_security_tools
    install_nodejs
    install_docker
    install_python_packages
    configure_system_services
    create_cli_helpers
    display_summary
}

# Run installation
main "$@"