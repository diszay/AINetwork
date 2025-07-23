# NetArchon Ubuntu Server CLI Deployment Guide

**Complete deployment guide for NetArchon on Ubuntu 24.04.2 LTS Server using command line interface.**

## 🎯 Overview

This guide provides step-by-step instructions for deploying NetArchon on Ubuntu 24.04.2 LTS Server entirely through the command line interface (CLI). Perfect for headless server installations and remote deployments.

## 📋 Pre-Deployment Checklist

### System Verification

**1. Verify Ubuntu Installation:**
```bash
# Check Ubuntu version
lsb_release -a
# Expected output: Ubuntu 24.04.2 LTS (Noble Numbat)

# Check system architecture
uname -m
# Expected: x86_64 or aarch64

# Check available resources
free -h && df -h
```

**2. Network Configuration:**
```bash
# Check network interfaces
ip addr show

# Test internet connectivity
ping -c 4 google.com

# Check DNS resolution
nslookup google.com

# Verify SSH access (if remote)
sudo systemctl status ssh
```

**3. User Privileges:**
```bash
# Verify sudo access
sudo whoami
# Should return: root

# Check user groups
groups $USER
# Should include: sudo
```

## 🚀 Phase 1: System Preparation

### Update System

```bash
# Update package lists
sudo apt update

# Upgrade existing packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git nano vim htop tree
```

### Configure Static IP (Recommended)

**1. Identify Network Interface:**
```bash
# List network interfaces
ip link show

# Note your interface name (e.g., enp0s3, eth0, ens18)
INTERFACE_NAME="enp0s3"  # Replace with your interface
```

**2. Configure Static IP:**
```bash
# Backup current configuration
sudo cp /etc/netplan/*.yaml /etc/netplan/backup-$(date +%Y%m%d).yaml

# Create new netplan configuration
sudo tee /etc/netplan/01-netcfg.yaml > /dev/null << EOF
network:
  version: 2
  ethernets:
    $INTERFACE_NAME:
      dhcp4: false
      addresses:
        - 192.168.1.100/24  # Change to available IP on your network
      gateway4: 192.168.1.1  # Your router's IP
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
          - 1.1.1.1
EOF

# Apply configuration
sudo netplan apply

# Verify new IP
ip addr show $INTERFACE_NAME
```

### Configure Hostname

```bash
# Set hostname
sudo hostnamectl set-hostname netarchon-server

# Update /etc/hosts
echo "127.0.1.1 netarchon-server" | sudo tee -a /etc/hosts

# Verify hostname
hostnamectl
```

## 🔧 Phase 2: Dependencies Installation

### Install Dependencies Script

```bash
# Download dependencies installer
curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/install-dependencies.sh -o install-dependencies.sh

# Make executable
chmod +x install-dependencies.sh

# Run installer
./install-dependencies.sh

# Verify installation
python3 --version
node --version
docker --version
```

### Manual Dependencies (Alternative)

**If you prefer manual installation:**

```bash
# System packages
sudo apt install -y \
    python3 python3-pip python3-venv python3-dev \
    git sqlite3 nginx fail2ban ufw \
    build-essential libssl-dev libffi-dev \
    htop iotop nethogs net-tools \
    curl wget unzip zip

# Python packages (global)
sudo pip3 install --upgrade pip setuptools wheel

# Node.js (optional)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Docker (optional)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

## 🏗️ Phase 3: NetArchon Installation

### Automated Installation

```bash
# Download NetArchon installer
curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/ubuntu-24.04-install.sh -o netarchon-install.sh

# Make executable
chmod +x netarchon-install.sh

# Run installer
./netarchon-install.sh
```

### Manual Installation Steps

**If you prefer step-by-step manual installation:**

**1. Create NetArchon User:**
```bash
# Create system user
sudo useradd -r -s /bin/false -d /opt/netarchon -m netarchon

# Create directory structure
sudo mkdir -p /opt/netarchon/{data,logs,config,backups,scripts}
sudo chown -R netarchon:netarchon /opt/netarchon
sudo chmod 755 /opt/netarchon
sudo chmod 750 /opt/netarchon/{data,logs,config,backups}
```

**2. Install NetArchon:**
```bash
# Change to NetArchon directory
cd /opt/netarchon

# Clone repository
sudo -u netarchon git clone https://github.com/diszay/AINetwork.git .

# Create virtual environment
sudo -u netarchon python3 -m venv venv

# Install dependencies
sudo -u netarchon bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-web.txt
"
```

**3. Configure systemd Service:**
```bash
# Create service file
sudo tee /etc/systemd/system/netarchon.service > /dev/null << 'EOF'
[Unit]
Description=NetArchon Network Monitoring System
Documentation=https://github.com/diszay/AINetwork
After=network.target
Wants=network.target

[Service]
Type=simple
User=netarchon
Group=netarchon
WorkingDirectory=/opt/netarchon
Environment=PATH=/opt/netarchon/venv/bin
Environment=PYTHONPATH=/opt/netarchon/src
Environment=STREAMLIT_SERVER_HEADLESS=true
Environment=STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ExecStart=/opt/netarchon/venv/bin/streamlit run src/netarchon/web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/netarchon/data
ReadWritePaths=/opt/netarchon/logs
ReadWritePaths=/opt/netarchon/backups

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
```

## 🔒 Phase 4: Security Configuration

### Firewall Setup

```bash
# Reset UFW to defaults
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (important - don't lock yourself out!)
sudo ufw allow ssh

# Allow NetArchon web interface
sudo ufw allow 8501/tcp comment "NetArchon Web Interface"

# Allow from specific network only (more secure)
# sudo ufw allow from 192.168.1.0/24 to any port 8501

# Enable firewall
sudo ufw --force enable

# Verify configuration
sudo ufw status verbose
```

### fail2ban Configuration

```bash
# Configure fail2ban for SSH protection
sudo tee /etc/fail2ban/jail.d/netarchon.conf > /dev/null << 'EOF'
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
port = 8501
filter = netarchon
logpath = /opt/netarchon/logs/netarchon.log
maxretry = 5
bantime = 1800
findtime = 300
EOF

# Create NetArchon filter
sudo tee /etc/fail2ban/filter.d/netarchon.conf > /dev/null << 'EOF'
[Definition]
failregex = ^.*\[ERROR\].*Failed login attempt from <HOST>.*$
            ^.*\[WARNING\].*Suspicious activity from <HOST>.*$
ignoreregex =
EOF

# Restart and enable fail2ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban

# Check status
sudo fail2ban-client status
```

### SSH Hardening (Optional but Recommended)

```bash
# Backup SSH config
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Configure SSH security
sudo tee -a /etc/ssh/sshd_config > /dev/null << 'EOF'

# NetArchon SSH Security Settings
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

# Restart SSH service
sudo systemctl restart ssh
```

### Automatic Updates

```bash
# Install unattended upgrades
sudo apt install -y unattended-upgrades

# Configure automatic updates
sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

# Enable automatic updates
sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
```

## 🔄 Phase 5: Backup and Monitoring Setup

### Create Backup Script

```bash
# Create backup script
sudo -u netarchon tee /opt/netarchon/scripts/backup.sh > /dev/null << 'EOF'
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

# Make executable
sudo chmod +x /opt/netarchon/scripts/backup.sh

# Test backup
sudo -u netarchon /opt/netarchon/scripts/backup.sh
```

### Create Health Check Script

```bash
# Create health check script
sudo -u netarchon tee /opt/netarchon/scripts/health-check.sh > /dev/null << 'EOF'
#!/bin/bash
# NetArchon Health Check Script

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "NetArchon Health Check - $(date)"
echo "=================================="

# Check service status
if systemctl is-active --quiet netarchon; then
    echo -e "${GREEN}✓ NetArchon service is running${NC}"
else
    echo -e "${RED}✗ NetArchon service is not running${NC}"
fi

# Check web interface
if curl -s http://localhost:8501 > /dev/null; then
    echo -e "${GREEN}✓ Web interface is accessible${NC}"
else
    echo -e "${RED}✗ Web interface is not accessible${NC}"
fi

# Check disk space
USAGE=$(df /opt/netarchon | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$USAGE" -lt 80 ]; then
    echo -e "${GREEN}✓ Disk space OK ($USAGE% used)${NC}"
else
    echo -e "${YELLOW}⚠ Disk space warning ($USAGE% used)${NC}"
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✓ Memory usage OK ($MEM_USAGE% used)${NC}"
else
    echo -e "${YELLOW}⚠ Memory usage high ($MEM_USAGE% used)${NC}"
fi

echo "=================================="
echo "Health check completed"
EOF

# Make executable
sudo chmod +x /opt/netarchon/scripts/health-check.sh

# Test health check
sudo -u netarchon /opt/netarchon/scripts/health-check.sh
```

### Schedule Automated Tasks

```bash
# Add cron jobs for NetArchon user
sudo -u netarchon crontab -e

# Add these lines to crontab:
# Daily backup at 2:00 AM
0 2 * * * /opt/netarchon/scripts/backup.sh

# Health check every 30 minutes
*/30 * * * * /opt/netarchon/scripts/health-check.sh

# Or add directly:
sudo -u netarchon bash -c '
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/netarchon/scripts/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/30 * * * * /opt/netarchon/scripts/health-check.sh") | crontab -
'
```

## 🚀 Phase 6: Service Startup and Verification

### Start NetArchon Service

```bash
# Start the service
sudo systemctl start netarchon

# Check service status
sudo systemctl status netarchon

# Follow logs to verify startup
sudo journalctl -u netarchon -f
# Press Ctrl+C to stop following logs
```

### Verify Installation

**1. Service Verification:**
```bash
# Check if service is active
sudo systemctl is-active netarchon

# Check if service is enabled
sudo systemctl is-enabled netarchon

# View service details
sudo systemctl show netarchon
```

**2. Network Verification:**
```bash
# Check if port 8501 is listening
sudo netstat -tlnp | grep 8501

# Test local web interface
curl -I http://localhost:8501

# Get server IP for remote access
hostname -I
```

**3. Security Verification:**
```bash
# Check firewall status
sudo ufw status

# Check fail2ban status
sudo fail2ban-client status

# Verify service user
ps aux | grep streamlit
```

## 🌐 Phase 7: Access and Initial Configuration

### Access Web Interface

**From Local Network:**
```bash
# Find your server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Access NetArchon at: http://$SERVER_IP:8501"

# Test from another machine
curl -I http://$SERVER_IP:8501
```

**From Server (if GUI available):**
```bash
# Install text-based browser for testing
sudo apt install -y lynx

# Access web interface
lynx http://localhost:8501
```

### Initial Web Configuration

**Through SSH Tunnel (Secure Remote Access):**
```bash
# From your local machine, create SSH tunnel:
ssh -L 8501:localhost:8501 username@your-server-ip

# Then access http://localhost:8501 on your local machine
```

## 📊 Phase 8: Monitoring and Maintenance

### Set Up Monitoring Commands

**Create useful aliases:**
```bash
# Add to ~/.bashrc
cat >> ~/.bashrc << 'EOF'
# NetArchon aliases
alias netarchon-status='sudo systemctl status netarchon'
alias netarchon-logs='sudo journalctl -u netarchon -f'
alias netarchon-restart='sudo systemctl restart netarchon'
alias netarchon-health='sudo -u netarchon /opt/netarchon/scripts/health-check.sh'
alias netarchon-backup='sudo -u netarchon /opt/netarchon/scripts/backup.sh'

# System monitoring
alias ports='sudo netstat -tlnp'
alias meminfo='free -h'
alias diskinfo='df -h'
alias sysload='uptime'
EOF

# Reload bashrc
source ~/.bashrc
```

### Regular Maintenance Tasks

**Weekly Maintenance Script:**
```bash
# Create maintenance script
sudo tee /opt/netarchon/scripts/weekly-maintenance.sh > /dev/null << 'EOF'
#!/bin/bash
# Weekly NetArchon Maintenance

echo "Starting weekly maintenance - $(date)"

# Update system packages
apt update && apt upgrade -y

# Clean package cache
apt autoremove -y
apt autoclean

# Rotate logs
journalctl --vacuum-time=30d

# Run health check
/opt/netarchon/scripts/health-check.sh

# Backup database
/opt/netarchon/scripts/backup.sh

# Restart NetArchon service
systemctl restart netarchon

echo "Weekly maintenance completed - $(date)"
EOF

sudo chmod +x /opt/netarchon/scripts/weekly-maintenance.sh

# Schedule weekly maintenance (Sundays at 3 AM)
echo "0 3 * * 0 /opt/netarchon/scripts/weekly-maintenance.sh" | sudo crontab -
```

## 🔧 Troubleshooting Common Issues

### Service Issues

**Service won't start:**
```bash
# Check service status
sudo systemctl status netarchon

# Check logs for errors
sudo journalctl -u netarchon -n 50

# Check file permissions
ls -la /opt/netarchon/
sudo chown -R netarchon:netarchon /opt/netarchon/

# Restart service
sudo systemctl restart netarchon
```

**Port already in use:**
```bash
# Find what's using port 8501
sudo lsof -i :8501

# Kill process if necessary
sudo kill -9 $(sudo lsof -t -i:8501)

# Restart NetArchon
sudo systemctl restart netarchon
```

### Network Issues

**Can't access web interface:**
```bash
# Check if service is running
sudo systemctl is-active netarchon

# Check firewall
sudo ufw status | grep 8501

# Test local connection
curl -v http://localhost:8501

# Check network binding
sudo netstat -tlnp | grep 8501
```

### Performance Issues

**High resource usage:**
```bash
# Check system resources
htop
sudo iotop

# Check NetArchon process
ps aux | grep streamlit

# Check memory usage
free -h

# Restart service if needed
sudo systemctl restart netarchon
```

## ✅ Deployment Complete!

### Verification Checklist

**Run these commands to verify successful deployment:**

```bash
# Service status
netarchon-status

# Health check
netarchon-health

# Network test
curl -I http://localhost:8501

# Security check
sudo ufw status
sudo fail2ban-client status

# Backup test
ls -la /opt/netarchon/backups/
```

### Next Steps

1. **Access Web Interface:**
   - Open browser to `http://your-server-ip:8501`
   - Complete initial setup wizard

2. **Add Network Devices:**
   - Add your router, modem, switches
   - Configure monitoring intervals

3. **Configure Alerts:**
   - Set up email notifications
   - Configure alert thresholds

4. **Security Review:**
   - Change default passwords
   - Review firewall rules
   - Set up SSH key authentication

### Success Indicators

**Your deployment is successful when:**
- ✅ NetArchon service is active and enabled
- ✅ Web interface accessible on port 8501
- ✅ Firewall configured with minimal required ports
- ✅ fail2ban active and monitoring
- ✅ Automated backups scheduled
- ✅ Health monitoring in place
- ✅ All verification commands pass

**Congratulations!** You now have NetArchon successfully deployed on Ubuntu 24.04.2 LTS Server with enterprise-grade security, monitoring, and maintenance procedures.