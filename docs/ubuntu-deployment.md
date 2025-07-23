# NetArchon Ubuntu 24.04.2 LTS Server Deployment Guide

**Congratulations on installing Ubuntu 24.04.2 LTS Server!** This guide will help you deploy NetArchon on your fresh Ubuntu server installation, following the CLAUDE.md Essential Development Workflow.

## 🎯 What This Guide Covers

**For Everyone:**
- Simple one-command installation on your Ubuntu server
- Step-by-step setup verification
- How to access NetArchon from other devices
- Basic troubleshooting for Ubuntu-specific issues

**For Technical Users:**
- Complete Ubuntu 24.04.2 LTS optimization
- systemd service configuration
- Security hardening with UFW and fail2ban
- Performance tuning and monitoring
- Advanced configuration options

## 📋 Pre-Installation Checklist

### Verify Your Ubuntu Installation

**Check your Ubuntu version:**
```bash
lsb_release -a
# Should show: Ubuntu 24.04.2 LTS (Noble Numbat)
```

**Verify network connectivity:**
```bash
# Check internet connection
ping -c 4 google.com

# Check your server's IP address
ip addr show
```

**Update your system:**
```bash
sudo apt update && sudo apt upgrade -y
```

### Network Configuration (Optional but Recommended)

**Set a static IP address for your server:**

1. **Find your network interface:**
```bash
ip link show
# Note the interface name (usually something like enp0s3, eth0, or ens18)
```

2. **Configure static IP:**
```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

3. **Add this configuration (adjust for your network):**
```yaml
network:
  version: 2
  ethernets:
    enp0s3:  # Replace with your interface name
      dhcp4: false
      addresses:
        - 192.168.1.100/24  # Choose an available IP on your network
      gateway4: 192.168.1.1  # Your router's IP
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

4. **Apply the configuration:**
```bash
sudo netplan apply
```

## 🚀 NetArchon Installation

### Method 1: One-Command Installation (Recommended)

**For most users, this is the easiest way:**

```bash
# Download and run the automated installation script
curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/ubuntu-24.04-install.sh | bash
```

**What this script does:**
- ✅ Verifies Ubuntu 24.04.2 LTS compatibility
- ✅ Installs all required packages (Python 3.12, git, etc.)
- ✅ Creates NetArchon system user with proper security
- ✅ Sets up Python virtual environment
- ✅ Downloads and installs NetArchon
- ✅ Configures systemd service for automatic startup
- ✅ Sets up UFW firewall with secure defaults
- ✅ Configures fail2ban for intrusion detection
- ✅ Enables automatic security updates
- ✅ Creates automated backup system
- ✅ Starts NetArchon service

**Installation time:** 5-10 minutes depending on your internet speed.

### Method 2: Manual Installation (For Advanced Users)

**If you prefer to install manually or want to understand each step:**

**Step 1: Install Required Packages**
```bash
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
```

**Step 2: Create NetArchon User**
```bash
# Create system user (no shell login for security)
sudo useradd -r -s /bin/false -d /opt/netarchon -m netarchon

# Create directory structure
sudo mkdir -p /opt/netarchon/{data,logs,config,backups}
sudo chown -R netarchon:netarchon /opt/netarchon
sudo chmod 755 /opt/netarchon
sudo chmod 750 /opt/netarchon/{data,logs,config,backups}
```

**Step 3: Install NetArchon**
```bash
# Change to NetArchon directory
cd /opt/netarchon

# Clone repository as NetArchon user
sudo -u netarchon git clone https://github.com/diszay/AINetwork.git .

# Create Python virtual environment
sudo -u netarchon python3 -m venv venv

# Install dependencies
sudo -u netarchon bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-web.txt
"
```

**Step 4: Configure systemd Service**
```bash
sudo tee /etc/systemd/system/netarchon.service > /dev/null <<EOF
[Unit]
Description=NetArchon Network Monitoring System
After=network.target
Wants=network.target

[Service]
Type=simple
User=netarchon
Group=netarchon
WorkingDirectory=/opt/netarchon
Environment=PATH=/opt/netarchon/venv/bin
Environment=PYTHONPATH=/opt/netarchon/src
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

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable netarchon
sudo systemctl start netarchon
```

**Step 5: Configure Firewall**
```bash
# Reset and configure UFW
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8501/tcp comment "NetArchon Web Interface"
sudo ufw --force enable
```

## 🔍 Verification and Testing

### Check Installation Status

**Verify NetArchon service is running:**
```bash
sudo systemctl status netarchon
# Should show "active (running)"
```

**Check service logs:**
```bash
sudo journalctl -u netarchon -f
# Should show Streamlit starting up successfully
```

**Test web interface:**
```bash
# From your server
curl -I http://localhost:8501
# Should return HTTP/1.1 200 OK

# Check if port is open
sudo netstat -tlnp | grep 8501
# Should show streamlit listening on port 8501
```

### Access Your NetArchon Dashboard

**From your server (if you have a desktop environment):**
- Open a web browser
- Go to: `http://localhost:8501`

**From other devices on your network:**
1. **Find your server's IP address:**
```bash
hostname -I
# Note the first IP address (e.g., 192.168.1.100)
```

2. **Access from any device on your network:**
- Open a web browser on your computer, phone, or tablet
- Go to: `http://YOUR-SERVER-IP:8501`
- Example: `http://192.168.1.100:8501`

**You should see the NetArchon dashboard with:**
- 🏠 Dashboard - Network overview
- 📱 Devices - Device management
- ⚙️ Configuration - Config management
- 📊 Monitoring - Real-time metrics
- 🔧 Terminal - Command execution
- 🔒 Security - Security monitoring
- 🔐 Credentials - BitWarden integration
- 🖥️ RustDesk - Remote desktop monitoring

## 🔧 Ubuntu-Specific Configuration

### System Optimization for NetArchon

**Optimize Python performance:**
```bash
# Add to NetArchon user's environment
sudo -u netarchon tee -a /opt/netarchon/.bashrc > /dev/null <<EOF
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
EOF
```

**Configure log rotation:**
```bash
sudo tee /etc/logrotate.d/netarchon > /dev/null <<EOF
/opt/netarchon/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 netarchon netarchon
    postrotate
        systemctl reload netarchon
    endscript
}
EOF
```

### Security Hardening

**Configure fail2ban for NetArchon:**
```bash
sudo tee /etc/fail2ban/jail.d/netarchon.conf > /dev/null <<EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[netarchon]
enabled = true
port = 8501
filter = netarchon
logpath = /opt/netarchon/logs/netarchon.log
maxretry = 5
bantime = 1800
EOF

sudo systemctl restart fail2ban
```

**Enable automatic security updates:**
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Performance Monitoring

**Install system monitoring tools:**
```bash
sudo apt install -y htop iotop nethogs
```

**Monitor NetArchon performance:**
```bash
# Check system resources
htop

# Monitor NetArchon process
sudo systemctl status netarchon

# Check memory usage
free -h

# Check disk space
df -h /opt/netarchon
```

## 🛠️ Management Commands

### Service Management

```bash
# Check service status
sudo systemctl status netarchon

# Start/stop/restart service
sudo systemctl start netarchon
sudo systemctl stop netarchon
sudo systemctl restart netarchon

# View logs
sudo journalctl -u netarchon -f          # Follow logs
sudo journalctl -u netarchon --since today  # Today's logs
sudo journalctl -u netarchon -n 50       # Last 50 lines
```

### Health Monitoring

**Run health check:**
```bash
sudo -u netarchon /opt/netarchon/scripts/health-check.sh
```

**Manual backup:**
```bash
sudo -u netarchon /opt/netarchon/scripts/backup.sh
```

**Check firewall status:**
```bash
sudo ufw status verbose
```

### Updates and Maintenance

**Update NetArchon:**
```bash
cd /opt/netarchon
sudo -u netarchon git pull
sudo -u netarchon bash -c "source venv/bin/activate && pip install -r requirements.txt"
sudo systemctl restart netarchon
```

**Update system packages:**
```bash
sudo apt update && sudo apt upgrade -y
```

## 🔧 Troubleshooting Ubuntu-Specific Issues

### Service Won't Start

**Check service status:**
```bash
sudo systemctl status netarchon
sudo journalctl -u netarchon --no-pager -n 20
```

**Common fixes:**
```bash
# Fix permissions
sudo chown -R netarchon:netarchon /opt/netarchon

# Reinstall dependencies
cd /opt/netarchon
sudo -u netarchon bash -c "source venv/bin/activate && pip install --upgrade -r requirements.txt"

# Restart service
sudo systemctl restart netarchon
```

### Can't Access Web Interface

**Check if service is running:**
```bash
sudo systemctl is-active netarchon
```

**Check firewall:**
```bash
sudo ufw status
# Should show 8501/tcp ALLOW
```

**Check network connectivity:**
```bash
# From server
curl http://localhost:8501

# Check what's listening on port 8501
sudo netstat -tlnp | grep 8501
```

### Performance Issues

**Check system resources:**
```bash
# CPU and memory usage
htop

# Disk space
df -h

# Network usage
sudo nethogs
```

**Optimize if needed:**
```bash
# Increase swap if low memory
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Database Issues

**Check database integrity:**
```bash
sqlite3 /opt/netarchon/data/netarchon.db "PRAGMA integrity_check;"
```

**Backup and restore database:**
```bash
# Backup
sudo -u netarchon cp /opt/netarchon/data/netarchon.db /opt/netarchon/backups/

# Restore from backup
sudo systemctl stop netarchon
sudo -u netarchon cp /opt/netarchon/backups/netarchon.db /opt/netarchon/data/
sudo systemctl start netarchon
```

## 🔄 Maintenance Schedule

### Daily (Automated)
- ✅ Automatic security updates
- ✅ Database backup (2:00 AM)
- ✅ Log rotation
- ✅ Health monitoring

### Weekly (Manual)
```bash
# Run weekly maintenance
sudo apt update && sudo apt upgrade -y
sudo -u netarchon /opt/netarchon/scripts/health-check.sh
sudo systemctl restart netarchon
```

### Monthly (Manual)
```bash
# Clean up old logs and backups
sudo journalctl --vacuum-time=30d
find /opt/netarchon/backups -name "*.tar.gz" -mtime +30 -delete

# Update NetArchon
cd /opt/netarchon
sudo -u netarchon git pull
sudo systemctl restart netarchon
```

## 🎯 Next Steps

### Initial Configuration

1. **Access your dashboard:** `http://your-server-ip:8501`
2. **Add your first device:** Use the web interface to add your router
3. **Configure monitoring:** Set up alerts and thresholds
4. **Test functionality:** Verify all features work correctly

### Advanced Setup

1. **BitWarden Integration:** Configure credential management
2. **RustDesk Setup:** Enable remote desktop monitoring  
3. **Custom Alerts:** Set up email/webhook notifications
4. **API Access:** Configure programmatic access

### Security Review

1. **Change default passwords:** Update any default credentials
2. **Review firewall rules:** Ensure only necessary ports are open
3. **Configure SSH keys:** Disable password authentication for SSH
4. **Enable monitoring:** Set up intrusion detection alerts

## 📚 Additional Resources

**Ubuntu-Specific Documentation:**
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)
- [systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [UFW Firewall Configuration](https://help.ubuntu.com/community/UFW)

**NetArchon Documentation:**
- [User Guide](user_guide.md) - Complete usage instructions
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [API Documentation](api_documentation.md) - Programmatic access
- [Security Implementation](security_implementation.md) - Security features

**Community Support:**
- [GitHub Issues](https://github.com/diszay/AINetwork/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/diszay/AINetwork/discussions) - Community help

---

## ✅ Ubuntu 24.04.2 LTS Deployment Complete!

**Congratulations!** You now have NetArchon running on Ubuntu 24.04.2 LTS Server with:

- 🔒 **Secure Configuration** - UFW firewall, fail2ban, automatic updates
- 🚀 **High Performance** - Optimized for Ubuntu Server environment
- 🔄 **Automatic Operation** - systemd service, automated backups, health monitoring
- 📊 **Full Monitoring** - Complete network visibility and management
- 🛡️ **Enterprise Security** - Production-ready security configuration

Your personal AI network assistant is now ready to monitor and manage your home network 24/7!