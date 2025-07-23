# NetArchon Ubuntu Server Deployment Guide

This guide provides complete instructions for deploying NetArchon with Streamlit web interface on Ubuntu Server, specifically optimized for mini PC environments.

## Overview

**Target Environment**: Mini PC with Ubuntu Server 24.04 LTS  
**Recommended Specs**: 8GB RAM, 256GB storage, 4+ CPU cores  
**Network Setup**: Home network with Xfinity modem and Netgear Orbi router  

## Pre-Installation Requirements

### Hardware Requirements
- **CPU**: 4+ cores (Intel i5/i7 or AMD Ryzen equivalent)
- **RAM**: 8GB minimum, 16GB recommended  
- **Storage**: 256GB SSD minimum
- **Network**: Gigabit Ethernet connection
- **USB**: For initial OS installation

### Network Prerequisites
- Static IP address or DHCP reservation
- Port 8501 accessible on local network
- SSH access (port 22) for remote management
- Internet connectivity for package installation

## Step 1: Ubuntu Server Installation

### 1.1 Download Ubuntu Server 24.04 LTS
```bash
# Download official ISO
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso

# Create bootable USB drive (on another system)
sudo dd if=ubuntu-24.04-live-server-amd64.iso of=/dev/sdX bs=4M status=progress
```

### 1.2 Installation Configuration
During Ubuntu Server installation:

1. **Network Configuration**:
   - Configure static IP (e.g., 192.168.1.100)
   - Set DNS servers (1.1.1.1, 8.8.8.8)
   - Enable SSH server

2. **User Account**:
   - Username: `netarchon`
   - Strong password
   - Enable sudo access

3. **Storage**:
   - Use entire disk with LVM
   - Allocate sufficient space for logs and backups

### 1.3 Initial System Update
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git vim htop iotop ufw fail2ban
```

## Step 2: System Security Hardening

### 2.1 Configure Firewall
```bash
# Enable and configure UFW
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH and Streamlit
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 8501/tcp comment 'NetArchon Streamlit'

# Check firewall status
sudo ufw status verbose
```

### 2.2 Configure Fail2Ban
```bash
# Configure fail2ban for SSH protection
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check fail2ban status
sudo fail2ban-client status
```

### 2.3 Set Up Automatic Updates
```bash
# Install unattended upgrades
sudo apt install -y unattended-upgrades

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Step 3: Python Environment Setup

### 3.1 Install Python and Dependencies
```bash
# Install Python 3.12 and pip
sudo apt install -y python3.12 python3.12-pip python3.12-venv python3.12-dev

# Install system dependencies for NetArchon
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
sudo apt install -y libxml2-dev libxslt1-dev zlib1g-dev libjpeg-dev
```

### 3.2 Create NetArchon User and Directories
```bash
# Create NetArchon system user
sudo useradd -r -m -s /bin/bash netarchon
sudo usermod -aG sudo netarchon

# Create application directories
sudo mkdir -p /opt/netarchon
sudo chown netarchon:netarchon /opt/netarchon
```

## Step 4: NetArchon Installation

### 4.1 Clone NetArchon Repository
```bash
# Switch to netarchon user
sudo su - netarchon

# Clone the repository
cd /opt/netarchon
git clone https://github.com/your-username/NetArchon.git AINetwork-2
cd AINetwork-2
```

### 4.2 Set Up Python Virtual Environment
```bash
# Create virtual environment
python3.12 -m venv /opt/netarchon/venv

# Activate virtual environment
source /opt/netarchon/venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 4.3 Install NetArchon Dependencies
```bash
# Install core NetArchon requirements
pip install -r requirements.txt

# Install web interface requirements
pip install -r requirements-web.txt

# Verify installation
python -c "import streamlit; print('Streamlit installed successfully')"
```

## Step 5: NetArchon Configuration

### 5.1 Create Configuration Directories
```bash
# Create necessary directories
mkdir -p /opt/netarchon/AINetwork-2/{logs,backups,config}

# Set proper permissions
chmod 755 /opt/netarchon/AINetwork-2/{logs,backups,config}
```

### 5.2 Configure Environment Variables
```bash
# Create environment file
cat > /opt/netarchon/AINetwork-2/.env << 'EOF'
PYTHONPATH=/opt/netarchon/AINetwork-2/src
NETARCHON_LOG_LEVEL=INFO
NETARCHON_BACKUP_DIR=/opt/netarchon/AINetwork-2/backups
NETARCHON_LOG_DIR=/opt/netarchon/AINetwork-2/logs
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
EOF

# Set proper permissions
chmod 600 /opt/netarchon/AINetwork-2/.env
```

### 5.3 Test NetArchon Installation
```bash
# Test core NetArchon functionality
cd /opt/netarchon/AINetwork-2
python3 -m pytest tests/ -v --tb=short

# Test Streamlit application
streamlit run src/netarchon/web/streamlit_app.py --server.port=8502 --server.headless=true &
sleep 5
curl -f http://localhost:8502 && echo "Streamlit test successful"
pkill -f streamlit
```

## Step 6: Systemd Service Configuration

### 6.1 Install Systemd Service
```bash
# Copy service file
sudo cp /opt/netarchon/AINetwork-2/deployment/netarchon-streamlit.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable netarchon-streamlit.service
sudo systemctl start netarchon-streamlit.service
```

### 6.2 Verify Service Status
```bash
# Check service status
sudo systemctl status netarchon-streamlit.service

# Check service logs
sudo journalctl -u netarchon-streamlit.service -f

# Test web interface
curl -f http://localhost:8501
```

## Step 7: Network Access Configuration

### 7.1 Configure Static IP (if not done during installation)
```bash
# Edit netplan configuration
sudo vim /etc/netplan/01-netcfg.yaml

# Example configuration:
network:
  version: 2
  ethernets:
    ens18:  # Replace with your interface name
      dhcp4: false
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 1.1.1.1
          - 8.8.8.8

# Apply configuration
sudo netplan apply
```

### 7.2 Configure Router Port Forwarding (Optional)
For external access, configure your Netgear Orbi router:

1. Access router admin panel (http://192.168.1.1)
2. Navigate to Advanced → Port Forwarding
3. Add rule:
   - Service: NetArchon
   - External Port: 8501
   - Internal IP: 192.168.1.100
   - Internal Port: 8501
   - Protocol: TCP

## Step 8: SSL/TLS Configuration (Optional)

### 8.1 Install Nginx Reverse Proxy
```bash
# Install Nginx
sudo apt install -y nginx

# Create NetArchon site configuration
sudo cat > /etc/nginx/sites-available/netarchon << 'EOF'
server {
    listen 80;
    server_name netarchon.local;  # Replace with your domain/IP
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/netarchon /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 8.2 Install SSL Certificate (Let's Encrypt)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate (if you have a domain)
sudo certbot --nginx -d your-domain.com

# Set up automatic renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Step 9: Monitoring and Maintenance

### 9.1 Set Up Log Rotation
```bash
# Create logrotate configuration
sudo cat > /etc/logrotate.d/netarchon << 'EOF'
/opt/netarchon/AINetwork-2/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    su netarchon netarchon
}
EOF
```

### 9.2 Create Backup Script
```bash
# Create backup script
cat > /opt/netarchon/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/netarchon/backups/system"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup NetArchon configuration
tar -czf $BACKUP_DIR/netarchon_config_$DATE.tar.gz \
    /opt/netarchon/AINetwork-2/config \
    /opt/netarchon/AINetwork-2/.env \
    /etc/systemd/system/netarchon-streamlit.service

# Backup device configurations
tar -czf $BACKUP_DIR/device_configs_$DATE.tar.gz \
    /opt/netarchon/AINetwork-2/backups

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

# Make executable
chmod +x /opt/netarchon/backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/netarchon/backup.sh >> /opt/netarchon/AINetwork-2/logs/backup.log 2>&1") | crontab -
```

### 9.3 System Monitoring
```bash
# Install system monitoring tools
sudo apt install -y htop iotop nethogs

# Create monitoring script
cat > /opt/netarchon/monitor.sh << 'EOF'
#!/bin/bash
echo "=== NetArchon System Status $(date) ==="
echo "System Load:"
uptime
echo ""
echo "Memory Usage:"
free -h
echo ""
echo "Disk Usage:"
df -h /opt/netarchon
echo ""
echo "NetArchon Service Status:"
systemctl status netarchon-streamlit.service --no-pager
echo ""
echo "Network Connections:"
ss -tlnp | grep :8501
EOF

chmod +x /opt/netarchon/monitor.sh
```

## Step 10: Testing and Validation

### 10.1 Comprehensive Testing
```bash
# Test NetArchon core functionality
cd /opt/netarchon/AINetwork-2
python3 -m pytest tests/ -v

# Test web interface accessibility
curl -f http://localhost:8501/_stcore/health
curl -f http://192.168.1.100:8501

# Test from another device on network
# From laptop/phone: http://192.168.1.100:8501
```

### 10.2 Performance Testing
```bash
# Monitor resource usage
htop &
iotop &

# Load test (install apache2-utils first)
sudo apt install -y apache2-utils
ab -n 100 -c 10 http://localhost:8501/
```

## Step 11: Troubleshooting Guide

### 11.1 Common Issues

**Service won't start:**
```bash
# Check service status and logs
sudo systemctl status netarchon-streamlit.service
sudo journalctl -u netarchon-streamlit.service -n 50

# Check permissions
ls -la /opt/netarchon/AINetwork-2/
sudo chown -R netarchon:netarchon /opt/netarchon/
```

**Web interface not accessible:**
```bash
# Check if service is listening
sudo ss -tlnp | grep 8501

# Check firewall
sudo ufw status
sudo ufw allow 8501/tcp

# Check logs
tail -f /opt/netarchon/AINetwork-2/logs/*.log
```

**Import errors:**
```bash
# Check Python path
echo $PYTHONPATH
export PYTHONPATH=/opt/netarchon/AINetwork-2/src

# Reinstall dependencies
source /opt/netarchon/venv/bin/activate
pip install -r requirements-web.txt --force-reinstall
```

### 11.2 Log Locations
- **System logs**: `/var/log/syslog`
- **Service logs**: `journalctl -u netarchon-streamlit.service`
- **NetArchon logs**: `/opt/netarchon/AINetwork-2/logs/`
- **Nginx logs**: `/var/log/nginx/`

## Step 12: Maintenance Tasks

### 12.1 Regular Maintenance
```bash
# Weekly tasks (run every Sunday)
cat > /opt/netarchon/weekly_maintenance.sh << 'EOF'
#!/bin/bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean package cache
sudo apt autoremove -y
sudo apt autoclean

# Restart NetArchon service
sudo systemctl restart netarchon-streamlit.service

# Check disk space
df -h /opt/netarchon

# Backup device configurations
/opt/netarchon/backup.sh
EOF

chmod +x /opt/netarchon/weekly_maintenance.sh

# Add to crontab (run every Sunday at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/netarchon/weekly_maintenance.sh >> /opt/netarchon/AINetwork-2/logs/maintenance.log 2>&1") | crontab -
```

### 12.2 Update NetArchon
```bash
# Create update script
cat > /opt/netarchon/update.sh << 'EOF'
#!/bin/bash
cd /opt/netarchon/AINetwork-2

# Stop service
sudo systemctl stop netarchon-streamlit.service

# Backup current version
tar -czf ../netarchon_backup_$(date +%Y%m%d_%H%M%S).tar.gz .

# Pull updates
git pull origin main

# Update dependencies
source /opt/netarchon/venv/bin/activate
pip install -r requirements-web.txt --upgrade

# Restart service
sudo systemctl start netarchon-streamlit.service

echo "NetArchon updated successfully"
EOF

chmod +x /opt/netarchon/update.sh
```

## Step 13: Access and Usage

### 13.1 Access Methods
- **Local access**: http://192.168.1.100:8501
- **With Nginx**: http://netarchon.local (if configured)
- **Mobile devices**: Use same URL, interface is responsive

### 13.2 Default Credentials
The web interface doesn't require authentication by default. To add authentication, modify the Streamlit configuration.

### 13.3 First-Time Setup
1. Access the web interface
2. Navigate to Devices page
3. Add your network devices (router, switches, etc.)
4. Configure monitoring intervals
5. Set up configuration backup schedules

## Step 14: Production Considerations

### 14.1 Performance Optimization
```bash
# Increase file descriptor limits
echo "netarchon soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "netarchon hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize Python for production
echo 'export PYTHONUNBUFFERED=1' >> /opt/netarchon/.bashrc
echo 'export PYTHONOPTIMIZE=1' >> /opt/netarchon/.bashrc
```

### 14.2 Security Recommendations
- Change default SSH port
- Use key-based SSH authentication
- Implement fail2ban for additional protection
- Regular security updates
- Monitor system logs for suspicious activity

## Conclusion

Your NetArchon installation is now complete and ready for production use. The system will automatically start on boot and provide a web interface for managing your home network.

**Next Steps:**
1. Access the web interface at http://192.168.1.100:8501
2. Add your Xfinity modem and Netgear router
3. Configure monitoring and alerting
4. Set up regular configuration backups
5. Explore the advanced features and customization options

For support and updates, refer to the NetArchon documentation and community resources.