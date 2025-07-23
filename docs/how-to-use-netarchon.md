# How to Successfully Use NetArchon

**Your complete guide to getting the most out of NetArchon for home network monitoring and management.**

## 🎯 What You'll Learn

**For Everyone:**
- How to access and navigate the NetArchon dashboard
- Adding and managing your network devices
- Understanding monitoring data and alerts
- Basic troubleshooting and maintenance

**For Advanced Users:**
- Advanced configuration and customization
- API usage and automation
- Integration with other systems
- Performance optimization

## 🚀 Getting Started

### First Access

**1. Access Your NetArchon Dashboard:**
```bash
# Find your server IP
hostname -I

# Access from any device on your network
# Open browser to: http://your-server-ip:8501
# Example: http://192.168.1.100:8501
```

**2. Initial Dashboard Overview:**
When you first access NetArchon, you'll see:
- **🏠 Dashboard** - Network overview and status
- **📱 Devices** - Device management
- **⚙️ Configuration** - Settings and config management
- **📊 Monitoring** - Real-time metrics and charts
- **🔧 Terminal** - Command execution interface
- **🔒 Security** - Security monitoring
- **🔐 Credentials** - Password management (BitWarden)
- **🖥️ RustDesk** - Remote desktop monitoring

## 📱 Managing Your Devices

### Adding Your First Device

**1. Navigate to Devices Page:**
- Click "📱 Devices" in the sidebar
- Click "Add New Device" button

**2. Device Information:**
```
Device Name: My Router (or any name you prefer)
IP Address: 192.168.1.1 (your router's IP)
Device Type: Select from dropdown (Generic, Cisco, etc.)
Username: admin (router's admin username)
Password: [your router password]
```

**3. Common Device Types and IPs:**
- **Router**: Usually 192.168.1.1 or 192.168.0.1
- **Modem**: Often 192.168.100.1 or 10.0.0.1
- **Access Points**: Various IPs in your network range
- **Switches**: Configured IP addresses

**4. Test Connection:**
- Click "Test Connection" before saving
- Green checkmark = successful connection
- Red X = connection failed (check IP, username, password)

### Managing Multiple Devices

**Device Categories:**
- **Core Infrastructure**: Router, modem, main switch
- **WiFi Equipment**: Access points, mesh nodes
- **Network Appliances**: Firewalls, VPN devices
- **Servers**: Your Ubuntu server, NAS devices

**Best Practices:**
- Use descriptive names: "Living Room Router", "Main Switch"
- Group similar devices with consistent naming
- Document device locations and purposes
- Keep credentials updated and secure

## 📊 Understanding Monitoring Data

### Dashboard Overview

**Network Health Indicators:**
- **🟢 Green**: Everything working normally
- **🟡 Yellow**: Minor issues or warnings
- **🔴 Red**: Problems requiring attention
- **⚫ Gray**: Device offline or unreachable

**Key Metrics to Watch:**
- **CPU Usage**: Should typically be under 80%
- **Memory Usage**: Monitor for memory leaks
- **Interface Utilization**: Network traffic levels
- **Connection Status**: Device reachability
- **Response Time**: Network latency

### Real-Time Monitoring

**1. Monitoring Page Features:**
- Live charts updating every 30-60 seconds
- Historical data graphs
- Performance trends
- Alert status indicators

**2. Understanding Charts:**
- **Line Charts**: Show trends over time
- **Bar Charts**: Compare current values
- **Gauge Charts**: Show current levels vs. thresholds
- **Status Indicators**: Real-time device status

**3. Time Range Selection:**
- Last hour: Real-time troubleshooting
- Last 24 hours: Daily patterns
- Last week: Weekly trends
- Last month: Long-term analysis

## 🔔 Setting Up Alerts

### Basic Alert Configuration

**1. Navigate to Monitoring:**
- Click "📊 Monitoring" in sidebar
- Look for "Alert Settings" or "Configure Alerts"

**2. Common Alert Types:**
- **Device Offline**: When device stops responding
- **High CPU**: CPU usage above threshold (e.g., 85%)
- **High Memory**: Memory usage above threshold (e.g., 90%)
- **Interface Down**: Network interface goes down
- **High Latency**: Response time above threshold

**3. Alert Thresholds:**
```
CPU Usage Warning: 80%
CPU Usage Critical: 90%
Memory Usage Warning: 85%
Memory Usage Critical: 95%
Response Time Warning: 100ms
Response Time Critical: 500ms
```

### Email Notifications

**1. Configure Email Settings:**
```
SMTP Server: smtp.gmail.com (for Gmail)
SMTP Port: 587
Username: your-email@gmail.com
Password: [app password for Gmail]
```

**2. Test Email Alerts:**
- Send test alert to verify configuration
- Check spam folder if not received
- Adjust alert frequency to avoid spam

### Advanced Alerting

**1. Alert Correlation:**
- Group related alerts together
- Avoid alert storms from single issues
- Set up escalation procedures

**2. Custom Alert Rules:**
- Create device-specific thresholds
- Set up business hours vs. after-hours alerts
- Configure different notification methods

## 🔧 Using the Terminal Interface

### Command Execution

**1. Access Terminal:**
- Click "🔧 Terminal" in sidebar
- Select target device from dropdown

**2. Basic Commands:**
```bash
# Check device status
show version
show system

# View interfaces
show interfaces
show ip interface brief

# Check routing
show ip route
show route

# System information
show memory
show processes
```

**3. Safety Features:**
- Commands are validated before execution
- Dangerous commands are blocked
- All commands are logged
- Read-only commands are preferred

### Batch Operations

**1. Multiple Commands:**
- Enter multiple commands, one per line
- Commands execute in sequence
- Results displayed for each command

**2. Command Templates:**
- Save frequently used command sets
- Create device-specific templates
- Share templates across devices

## ⚙️ Configuration Management

### Backup Configurations

**1. Automatic Backups:**
- NetArchon automatically backs up device configs
- Backups stored with timestamps
- Retention policy removes old backups

**2. Manual Backup:**
- Navigate to "⚙️ Configuration"
- Select device
- Click "Backup Configuration"
- Download or store locally

**3. Backup Schedule:**
```
Daily: Critical devices (router, firewall)
Weekly: Standard devices (switches, APs)
Monthly: Static devices (rarely changed)
```

### Configuration Deployment

**1. Safe Deployment Process:**
- Always backup before changes
- Validate configuration syntax
- Test connectivity after deployment
- Have rollback plan ready

**2. Configuration Validation:**
- Syntax checking before deployment
- Compatibility verification
- Impact assessment

**3. Rollback Procedures:**
- Keep previous configuration versions
- Quick rollback in case of issues
- Automated rollback on connectivity loss

## 🔒 Security Monitoring

### Security Dashboard

**1. Security Overview:**
- Current threat level
- Active security alerts
- Device security status
- Network access monitoring

**2. Security Metrics:**
- Failed login attempts
- Unauthorized access attempts
- Configuration changes
- Unusual network activity

### Network Security

**1. Device Authentication:**
- Monitor login attempts
- Track configuration changes
- Alert on unauthorized access

**2. Network Monitoring:**
- Scan for new devices
- Monitor for rogue access points
- Track unusual traffic patterns

## 🔐 Credential Management (BitWarden Integration)

### Setting Up BitWarden

**1. BitWarden Configuration:**
- Install BitWarden CLI on server
- Configure API access
- Set up device credential mapping

**2. Credential Storage:**
- Store device passwords securely
- Organize by device type/location
- Use strong, unique passwords

**3. Automatic Credential Retrieval:**
- NetArchon automatically retrieves passwords
- No need to enter passwords manually
- Secure encrypted storage

## 🖥️ Remote Desktop Monitoring (RustDesk)

### RustDesk Integration

**1. Server Setup:**
- Install RustDesk server
- Configure client connections
- Monitor active sessions

**2. Session Monitoring:**
- Track active remote desktop sessions
- Monitor connection quality
- Security event logging

## 📈 Performance Optimization

### System Performance

**1. Monitor System Resources:**
```bash
# Check system performance
htop                    # CPU and memory usage
sudo iotop             # Disk I/O
sudo nethogs           # Network usage by process
```

**2. NetArchon Performance:**
- Monitor dashboard response times
- Check database performance
- Optimize monitoring intervals

**3. Network Performance:**
- Monitor bandwidth usage
- Check for network bottlenecks
- Optimize device polling intervals

### Database Maintenance

**1. Regular Maintenance:**
```bash
# Database optimization
sudo -u netarchon sqlite3 /opt/netarchon/data/netarchon.db "VACUUM; ANALYZE;"

# Check database size
ls -lh /opt/netarchon/data/netarchon.db

# Database integrity check
sudo -u netarchon sqlite3 /opt/netarchon/data/netarchon.db "PRAGMA integrity_check;"
```

## 🔄 Automation and Integration

### API Usage

**1. REST API Access:**
```bash
# Get network status
curl http://localhost:8501/api/network/status

# Get device information
curl http://localhost:8501/api/devices

# Get metrics data
curl http://localhost:8501/api/metrics?device=router1
```

**2. Webhook Integration:**
```bash
# Configure webhook for alerts
curl -X POST http://localhost:8501/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-webhook-url.com", "events": ["alert"]}'
```

### Automation Scripts

**1. Health Check Automation:**
```bash
#!/bin/bash
# Automated health check script

# Check NetArchon status
if ! systemctl is-active --quiet netarchon; then
    echo "NetArchon is down, restarting..."
    sudo systemctl restart netarchon
fi

# Check disk space
DISK_USAGE=$(df /opt/netarchon | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "Warning: Disk usage is ${DISK_USAGE}%"
    # Send alert or clean up old files
fi
```

**2. Scheduled Tasks:**
```bash
# Add to crontab
crontab -e

# Health check every 15 minutes
*/15 * * * * /path/to/health-check.sh

# Daily backup verification
0 6 * * * /path/to/backup-verify.sh
```

## 🛠️ Troubleshooting Common Issues

### Dashboard Issues

**1. Dashboard Won't Load:**
```bash
# Check service status
sudo systemctl status netarchon

# Check logs
sudo journalctl -u netarchon -n 50

# Test local connection
curl -I http://localhost:8501
```

**2. Slow Dashboard Performance:**
```bash
# Check system resources
htop

# Restart service
sudo systemctl restart netarchon

# Clear browser cache
# Ctrl+F5 or Cmd+Shift+R
```

### Device Connection Issues

**1. Device Shows Offline:**
```bash
# Test connectivity
ping device-ip-address

# Check credentials
# Verify username/password in device settings

# Check firewall
sudo ufw status
```

**2. Authentication Failures:**
- Verify device credentials
- Check if device admin interface is accessible
- Ensure SSH is enabled on device
- Try connecting manually via SSH

### Monitoring Issues

**1. No Data Showing:**
- Wait 2-3 minutes for initial data collection
- Check device connectivity
- Verify monitoring is enabled for device
- Check device-specific monitoring commands

**2. Alerts Not Working:**
- Verify alert thresholds are set
- Check email configuration
- Test alert system
- Review alert logs

## 📚 Best Practices

### Daily Operations

**1. Morning Routine:**
- Check dashboard for overnight alerts
- Review system health status
- Verify all devices are online
- Check for any configuration changes

**2. Regular Monitoring:**
- Review performance trends weekly
- Update device credentials as needed
- Check backup status monthly
- Review and adjust alert thresholds

### Security Best Practices

**1. Access Control:**
- Use strong passwords for NetArchon access
- Limit network access to trusted devices
- Regularly review user access
- Monitor for unauthorized access attempts

**2. Device Security:**
- Keep device firmware updated
- Use strong, unique passwords
- Enable security features on devices
- Monitor for security vulnerabilities

### Maintenance Schedule

**1. Daily (Automated):**
- Health checks
- Backup verification
- Alert monitoring
- Performance monitoring

**2. Weekly (Manual):**
- Review performance trends
- Check for system updates
- Verify backup integrity
- Review security logs

**3. Monthly (Manual):**
- Update device credentials
- Review and adjust monitoring thresholds
- Clean up old data and logs
- Performance optimization review

## 🎯 Advanced Usage Scenarios

### Multi-Site Monitoring

**1. Branch Office Setup:**
- Configure VPN connections
- Set up remote device monitoring
- Implement centralized alerting
- Create site-specific dashboards

**2. Home Office Integration:**
- Monitor work-from-home setups
- Integrate with corporate networks
- Implement security monitoring
- Create performance reports

### Custom Integrations

**1. Third-Party Tools:**
- Integrate with existing monitoring systems
- Export data to external databases
- Create custom dashboards
- Implement automated responses

**2. Reporting and Analytics:**
- Generate performance reports
- Create capacity planning reports
- Implement trend analysis
- Set up executive dashboards

## ✅ Success Metrics

### Key Performance Indicators

**1. Network Reliability:**
- Device uptime percentage
- Mean time to detection (MTTD)
- Mean time to resolution (MTTR)
- Alert accuracy rate

**2. System Performance:**
- Dashboard response time
- Data collection success rate
- Alert delivery time
- System resource utilization

### Continuous Improvement

**1. Regular Reviews:**
- Monthly performance reviews
- Quarterly threshold adjustments
- Annual system optimization
- Ongoing training and education

**2. Feedback Loop:**
- Monitor alert effectiveness
- Adjust thresholds based on experience
- Optimize monitoring intervals
- Improve automation processes

---

## 🎉 Congratulations!

You now have comprehensive knowledge of how to successfully use NetArchon for network monitoring and management. With proper setup, monitoring, and maintenance, NetArchon will provide reliable 24/7 network visibility and help you maintain optimal network performance.

**Key Success Factors:**
- 📊 **Regular Monitoring** - Check dashboard daily
- 🔔 **Proper Alerting** - Set meaningful thresholds
- 🔒 **Security Focus** - Monitor for threats
- 🛠️ **Proactive Maintenance** - Regular system care
- 📈 **Continuous Improvement** - Optimize over time

Your network is now under professional-grade monitoring and management!