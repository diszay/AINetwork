# NetArchon CLI Usage Guide for Ubuntu 24.04.2 LTS Server

**Welcome to NetArchon CLI!** This guide covers everything you need to know about deploying, managing, and using NetArchon on Ubuntu 24.04.2 LTS Server from the command line.

## 🎯 What This Guide Covers

**For Server Administrators:**
- Complete CLI-based installation and deployment
- Service management and monitoring commands
- System administration and maintenance
- Troubleshooting from the command line

**For Network Engineers:**
- Advanced configuration through CLI
- Automation and scripting
- Integration with other systems
- Performance monitoring and optimization

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- Ubuntu 24.04.2 LTS Server (fresh installation)
- 2GB RAM (4GB recommended)
- 32GB storage (128GB SSD recommended)
- Network connectivity
- sudo privileges

**Verify Your System:**
```bash
# Check Ubuntu version
lsb_release -a
# Should show: Ubuntu 24.04.2 LTS

# Check available memory
free -h

# Check disk space
df -h

# Check network connectivity
ping -c 4 google.com
```

## 🚀 Installation Process

### Step 1: Install Dependencies

**Download and run the dependencies installer:**
```bash
# Download the dependencies installation script
curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/install-dependencies.sh -o install-dependencies.sh

# Make it executable
chmod +x install-dependencies.sh

# Run the installer
./install-dependencies.sh
```

**What this installs:**
- Python 3.12 with development tools
- Node.js 20 with npm packages
- Docker with docker-compose
- Database tools (SQLite, PostgreSQL, MySQL clients)
- Network and security tools (nmap, tcpdump, iftop, etc.)
- Development tools (gcc, make, cmake, etc.)
- System monitoring utilities (htop, iotop, nethogs, etc.)

### Step 2: Install NetArchon

**Option A: One-Command Installation (Recommended)**
```bash
# Download and run the NetArchon installer
curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/ubuntu-24.04-install.sh | bash
```

**Option B: Manual Installation**
```bash
# Clone the repository
git clone https://github.com/diszay/AINetwork.git
cd AINetwork

# Run the installation script
chmod +x scripts/ubuntu-24.04-install.sh
./scripts/ubuntu-24.04-install.sh
```

### Step 3: Verify Installation

**Check service status:**
```bash
# Check if NetArchon service is running
sudo systemctl status netarchon

# Check if service is enabled for startup
sudo systemctl is-enabled netarchon

# View recent logs
sudo journalctl -u netarchon -n 20
```

**Test web interface:**
```bash
# Check if web interface is responding
curl -I http://localhost:8501

# Check what's listening on port 8501
sudo netstat -tlnp | grep 8501

# Test from another machine (replace with your server IP)
curl -I http://192.168.1.100:8501
```

## 🔧 Service Management

### systemd Service Commands

**Basic Service Control:**
```bash
# Check service status
sudo systemctl status netarchon

# Start the service
sudo systemctl start netarchon

# Stop the service
sudo systemctl stop netarchon

# Restart the service
sudo systemctl restart netarchon

# Reload service configuration
sudo systemctl reload netarchon

# Enable service to start on boot
sudo systemctl enable netarchon

# Disable service from starting on boot
sudo systemctl disable netarchon
```

**Service Information:**
```bash
# Show service configuration
sudo systemctl show netarchon

# Show service dependencies
sudo systemctl list-dependencies netarchon

# Check if service failed
sudo systemctl is-failed netarchon

# Reset failed state
sudo systemctl reset-failed netarchon
```

### Log Management

**View Logs:**
```bash
# Follow logs in real-time
sudo journalctl -u netarchon -f

# View logs since today
sudo journalctl -u netarchon --since today

# View logs from last hour
sudo journalctl -u netarchon --since "1 hour ago"

# View last 50 log entries
sudo journalctl -u netarchon -n 50

# View logs with specific priority (error, warning, info)
sudo journalctl -u netarchon -p err

# Export logs to file
sudo journalctl -u netarchon --since "24 hours ago" > netarchon-logs.txt
```

**Log Analysis:**
```bash
# Search for errors in logs
sudo journalctl -u netarchon | grep -i error

# Search for specific patterns
sudo journalctl -u netarchon | grep "connection"

# Count log entries by type
sudo journalctl -u netarchon | grep -c "ERROR"
sudo journalctl -u netarchon | grep -c "WARNING"
sudo journalctl -u netarchon | grep -c "INFO"
```

## 📊 Monitoring and Health Checks

### Built-in Health Check

**Run health check script:**
```bash
# Run comprehensive health check
sudo -u netarchon /opt/netarchon/scripts/health-check.sh

# Run health check with verbose output
sudo -u netarchon /opt/netarchon/scripts/health-check.sh -v
```

### System Resource Monitoring

**CPU and Memory:**
```bash
# Real-time system monitor
htop

# CPU information
lscpu

# Memory usage
free -h

# Memory usage by process
ps aux --sort=-%mem | head -10

# CPU usage by process
ps aux --sort=-%cpu | head -10
```

**Disk Usage:**
```bash
# Disk space usage
df -h

# Directory sizes
du -sh /opt/netarchon/*

# Find large files
find /opt/netarchon -type f -size +100M -exec ls -lh {} \;

# Disk I/O monitoring
sudo iotop
```

**Network Monitoring:**
```bash
# Network connections
netstat -tulpn

# Active connections
ss -tulpn

# Network traffic by process
sudo nethogs

# Network interface statistics
cat /proc/net/dev

# Real-time network usage
sudo iftop
```

### NetArchon-Specific Monitoring

**Process Information:**
```bash
# Find NetArchon processes
ps aux | grep streamlit

# Process tree
pstree -p $(pgrep -f streamlit)

# Memory usage of NetArchon
ps -o pid,ppid,cmd,%mem,%cpu -p $(pgrep -f streamlit)

# Open files by NetArchon process
sudo lsof -p $(pgrep -f streamlit)
```

**Database Monitoring:**
```bash
# Check database file
ls -lh /opt/netarchon/data/netarchon.db

# Database integrity check
sqlite3 /opt/netarchon/data/netarchon.db "PRAGMA integrity_check;"

# Database size and statistics
sqlite3 /opt/netarchon/data/netarchon.db ".dbinfo"

# List database tables
sqlite3 /opt/netarchon/data/netarchon.db ".tables"
```

## 🔒 Security Management

### Firewall Management

**UFW Firewall:**
```bash
# Check firewall status
sudo ufw status verbose

# List numbered rules
sudo ufw status numbered

# Allow specific port
sudo ufw allow 8501/tcp

# Allow from specific IP
sudo ufw allow from 192.168.1.0/24 to any port 8501

# Delete rule by number
sudo ufw delete 2

# Reset firewall
sudo ufw --force reset

# Enable/disable firewall
sudo ufw enable
sudo ufw disable
```

### fail2ban Management

**fail2ban Status:**
```bash
# Check fail2ban status
sudo systemctl status fail2ban

# List active jails
sudo fail2ban-client status

# Check specific jail status
sudo fail2ban-client status sshd
sudo fail2ban-client status netarchon

# Unban IP address
sudo fail2ban-client set sshd unbanip 192.168.1.100

# Show banned IPs
sudo fail2ban-client status sshd | grep "Banned IP"
```

### SSH Security

**SSH Configuration:**
```bash
# Check SSH service status
sudo systemctl status ssh

# View SSH configuration
sudo cat /etc/ssh/sshd_config

# Check active SSH connections
who

# View SSH login attempts
sudo grep "sshd" /var/log/auth.log | tail -20

# Generate SSH key pair (if needed)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

## 🛠️ Configuration Management

### NetArchon Configuration

**Configuration Files:**
```bash
# Main configuration directory
ls -la /opt/netarchon/config/

# View current configuration
sudo -u netarchon cat /opt/netarchon/config/netarchon.yaml

# Edit configuration (if exists)
sudo -u netarchon nano /opt/netarchon/config/netarchon.yaml

# Backup configuration
sudo -u netarchon cp /opt/netarchon/config/netarchon.yaml /opt/netarchon/backups/config-$(date +%Y%m%d).yaml
```

**Environment Variables:**
```bash
# View current environment for NetArchon service
sudo systemctl show-environment

# Check NetArchon service environment
sudo systemctl show netarchon | grep Environment

# Set environment variable for service
sudo systemctl edit netarchon
# Add:
# [Service]
# Environment="VARIABLE_NAME=value"
```

### Database Management

**Database Operations:**
```bash
# Connect to database
sqlite3 /opt/netarchon/data/netarchon.db

# Backup database
sudo -u netarchon sqlite3 /opt/netarchon/data/netarchon.db ".backup '/opt/netarchon/backups/db-$(date +%Y%m%d).db'"

# Restore database from backup
sudo systemctl stop netarchon
sudo -u netarchon cp /opt/netarchon/backups/db-20240122.db /opt/netarchon/data/netarchon.db
sudo systemctl start netarchon

# Vacuum database (optimize)
sudo -u netarchon sqlite3 /opt/netarchon/data/netarchon.db "VACUUM;"

# Analyze database
sudo -u netarchon sqlite3 /opt/netarchon/data/netarchon.db "ANALYZE;"
```

## 🔄 Backup and Restore

### Automated Backups

**Backup Script:**
```bash
# Run manual backup
sudo -u netarchon /opt/netarchon/scripts/backup.sh

# Check backup schedule
sudo -u netarchon crontab -l

# View backup files
ls -la /opt/netarchon/backups/

# Check backup file integrity
tar -tzf /opt/netarchon/backups/netarchon_backup_20240122_020000.tar.gz
```

### Manual Backup and Restore

**Create Manual Backup:**
```bash
# Stop service
sudo systemctl stop netarchon

# Create backup
sudo tar -czf /tmp/netarchon-manual-backup-$(date +%Y%m%d).tar.gz \
    -C /opt/netarchon \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    config/ data/ src/

# Start service
sudo systemctl start netarchon

# Move backup to safe location
sudo mv /tmp/netarchon-manual-backup-*.tar.gz /opt/netarchon/backups/
```

**Restore from Backup:**
```bash
# Stop service
sudo systemctl stop netarchon

# Extract backup
sudo tar -xzf /opt/netarchon/backups/netarchon-manual-backup-20240122.tar.gz -C /opt/netarchon/

# Fix permissions
sudo chown -R netarchon:netarchon /opt/netarchon/config /opt/netarchon/data

# Start service
sudo systemctl start netarchon

# Verify restoration
sudo systemctl status netarchon
```

## 🔧 Troubleshooting

### Common Issues and Solutions

**Service Won't Start:**
```bash
# Check service status and logs
sudo systemctl status netarchon
sudo journalctl -u netarchon -n 50

# Check if port is already in use
sudo netstat -tlnp | grep 8501

# Check file permissions
ls -la /opt/netarchon/
sudo chown -R netarchon:netarchon /opt/netarchon/

# Restart service
sudo systemctl restart netarchon
```

**Web Interface Not Accessible:**
```bash
# Check if service is running
sudo systemctl is-active netarchon

# Check firewall
sudo ufw status | grep 8501

# Test local connection
curl -v http://localhost:8501

# Check network interface binding
sudo netstat -tlnp | grep 8501
```

**High Resource Usage:**
```bash
# Check resource usage
htop
sudo iotop
sudo nethogs

# Check NetArchon process
ps aux | grep streamlit

# Restart service to clear memory
sudo systemctl restart netarchon

# Check for memory leaks
sudo journalctl -u netarchon | grep -i memory
```

**Database Issues:**
```bash
# Check database integrity
sqlite3 /opt/netarchon/data/netarchon.db "PRAGMA integrity_check;"

# Check database locks
sudo lsof /opt/netarchon/data/netarchon.db

# Backup and recreate database if corrupted
sudo systemctl stop netarchon
sudo -u netarchon cp /opt/netarchon/data/netarchon.db /opt/netarchon/data/netarchon.db.corrupt
sudo -u netarchon rm /opt/netarchon/data/netarchon.db
sudo systemctl start netarchon
```

### Performance Optimization

**System Optimization:**
```bash
# Check system performance
vmstat 1 5
iostat -x 1 5

# Optimize database
sudo -u netarchon sqlite3 /opt/netarchon/data/netarchon.db "VACUUM; ANALYZE;"

# Clear system caches
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Check swap usage
swapon --show
free -h
```

**Service Optimization:**
```bash
# Adjust service resource limits
sudo systemctl edit netarchon
# Add:
# [Service]
# MemoryMax=4G
# CPUQuota=75%

# Reload systemd configuration
sudo systemctl daemon-reload
sudo systemctl restart netarchon
```

## 📈 Advanced Usage

### Automation and Scripting

**Create Custom Scripts:**
```bash
# Create script directory
mkdir -p ~/netarchon-scripts

# Example monitoring script
cat > ~/netarchon-scripts/monitor.sh << 'EOF'
#!/bin/bash
# NetArchon monitoring script

# Check service status
if ! systemctl is-active --quiet netarchon; then
    echo "NetArchon service is not running!"
    sudo systemctl start netarchon
fi

# Check disk space
DISK_USAGE=$(df /opt/netarchon | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "Warning: Disk usage is ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -gt 80 ]; then
    echo "Warning: Memory usage is ${MEM_USAGE}%"
fi
EOF

chmod +x ~/netarchon-scripts/monitor.sh
```

**Schedule with Cron:**
```bash
# Edit crontab
crontab -e

# Add monitoring script (runs every 5 minutes)
*/5 * * * * /home/$(whoami)/netarchon-scripts/monitor.sh

# Add daily health check
0 6 * * * sudo -u netarchon /opt/netarchon/scripts/health-check.sh
```

### Integration with Other Systems

**API Access:**
```bash
# Test API endpoints (if available)
curl -X GET http://localhost:8501/api/health
curl -X GET http://localhost:8501/api/status

# Use jq for JSON parsing
curl -s http://localhost:8501/api/status | jq '.'
```

**Log Integration:**
```bash
# Send logs to external system
sudo journalctl -u netarchon -f | while read line; do
    echo "$line" | curl -X POST -H "Content-Type: text/plain" \
        --data-binary @- http://your-log-server/netarchon
done
```

## 📚 Useful Commands Reference

### Quick Reference

**Service Management:**
```bash
sudo systemctl status netarchon     # Check status
sudo systemctl restart netarchon    # Restart service
sudo journalctl -u netarchon -f     # Follow logs
```

**Health Monitoring:**
```bash
sudo -u netarchon /opt/netarchon/scripts/health-check.sh  # Health check
htop                                 # System monitor
sudo netstat -tlnp | grep 8501     # Check port
```

**Backup and Maintenance:**
```bash
sudo -u netarchon /opt/netarchon/scripts/backup.sh  # Manual backup
ls -la /opt/netarchon/backups/      # List backups
df -h /opt/netarchon                # Check disk space
```

**Troubleshooting:**
```bash
curl -I http://localhost:8501       # Test web interface
sudo ufw status                     # Check firewall
ps aux | grep streamlit             # Find processes
```

### Aliases (Added by Dependencies Script)

The dependencies installation script adds these useful aliases to `~/.bash_aliases`:

```bash
# NetArchon specific
netarchon-status     # sudo systemctl status netarchon
netarchon-logs       # sudo journalctl -u netarchon -f
netarchon-restart    # sudo systemctl restart netarchon
netarchon-health     # sudo -u netarchon /opt/netarchon/scripts/health-check.sh

# System monitoring
ports               # netstat -tulanp
meminfo             # free -m -l -t
psmem10             # ps auxf | sort -nr -k 4 | head -10
pscpu10             # ps auxf | sort -nr -k 3 | head -10

# Network tools
myip                # curl -s ifconfig.me
netlisteners        # netstat -tulpn | grep LISTEN
```

## 🎯 Next Steps

### After Installation

1. **Verify Installation:**
   ```bash
   netarchon-status
   netarchon-health
   curl -I http://localhost:8501
   ```

2. **Access Web Interface:**
   - Find your server IP: `hostname -I`
   - Access from browser: `http://your-server-ip:8501`

3. **Add Network Devices:**
   - Use web interface to add your router, modem, etc.
   - Configure monitoring intervals and thresholds

4. **Set Up Monitoring:**
   - Configure alerts and notifications
   - Set up automated health checks
   - Review backup schedule

### Advanced Configuration

1. **Security Hardening:**
   - Configure SSH key-only authentication
   - Set up additional firewall rules
   - Configure intrusion detection

2. **Performance Tuning:**
   - Optimize database settings
   - Adjust service resource limits
   - Configure log rotation

3. **Integration:**
   - Set up external monitoring
   - Configure API access
   - Integrate with other systems

---

## ✅ CLI Usage Complete!

You now have comprehensive knowledge of managing NetArchon on Ubuntu 24.04.2 LTS Server from the command line. This includes installation, configuration, monitoring, troubleshooting, and advanced usage scenarios.

**Key Benefits of CLI Management:**
- 🚀 **Efficient Administration** - Manage everything from SSH
- 🔧 **Automation Ready** - Script all operations
- 📊 **Comprehensive Monitoring** - Real-time system visibility
- 🔒 **Security Focused** - Command-line security tools
- 🛠️ **Troubleshooting Power** - Deep system diagnostics

Your NetArchon server is ready for professional network monitoring and management!