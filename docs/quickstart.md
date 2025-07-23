# NetArchon Quick Start Guide

**Welcome to NetArchon!** This guide will get you up and running in just a few minutes, whether you're a complete beginner or a networking expert.

## 🎯 What You'll Accomplish

**In the next 10 minutes, you'll:**
- Install NetArchon on your computer
- Open your personal network dashboard
- Connect your first network device
- See real-time monitoring of your internet connection

## 📋 What You Need

**For Everyone:**
- A computer (Windows, Mac, or Linux)
- Internet connection
- Admin password for your router (usually on a sticker on the device)

**For Ubuntu 24.04.2 LTS Server Users:**
- **Hardware**: Mini PC with at least 4GB RAM, 128GB storage (SSD recommended)
- **Operating System**: Ubuntu 24.04.2 LTS Server (what you're installing!)
- **Network**: Works with any internet setup (Xfinity, Comcast, AT&T, Verizon, etc.)
- **Access**: SSH access to your server and network devices for monitoring

## 🚀 Installation (Choose Your Method)

### Method 1: Simple Installation (Recommended for Beginners)

**Step 1: Install Python (if you don't have it)**
- **Windows**: Download from [python.org](https://python.org) and install
- **Mac**: Install using Homebrew: `brew install python` or download from python.org
- **Linux**: Usually pre-installed, or use: `sudo apt install python3 python3-pip`

**Step 2: Install NetArchon**
```bash
# This downloads and installs NetArchon automatically:
pip install netarchon
```

**Step 3: Start NetArchon**
```bash
# This starts your network dashboard:
streamlit run netarchon
```

**Step 4: Open Your Dashboard**
- Open your web browser
- Go to: `http://localhost:8501`
- You should see your NetArchon dashboard!

### Method 2: Ubuntu 24.04.2 LTS Server Installation (Recommended for Your Setup)

**One-Command Installation for Ubuntu 24.04.2 LTS Server:**
```bash
# Download and run the automated installation script:
curl -fsSL https://raw.githubusercontent.com/diszay/AINetwork/main/scripts/ubuntu-24.04-install.sh | bash
```

**Manual Ubuntu Server Installation:**
```bash
# Clone the repository
git clone https://github.com/diszay/AINetwork.git
cd AINetwork

# Run the Ubuntu installation script
chmod +x scripts/ubuntu-24.04-install.sh
./scripts/ubuntu-24.04-install.sh
```

**What the script does:**
- Installs all required packages for Ubuntu 24.04.2 LTS
- Creates NetArchon system user with proper security
- Sets up Python 3.12 virtual environment
- Configures systemd service for automatic startup
- Sets up UFW firewall and fail2ban security
- Creates automated backup system
- Starts NetArchon service

**After installation:**
- Access your dashboard at: `http://your-server-ip:8501`
- NetArchon runs automatically on system boot
- Automatic security updates enabled
- Daily backups scheduled at 2:00 AM

### Method 3: Advanced Installation (For Technical Users)

**Step 1: Download Source Code**
```bash
# Download the latest version from GitHub:
git clone https://github.com/diszay/AINetwork.git
cd AINetwork

# Install all dependencies:
pip install -r requirements.txt
pip install -r requirements-web.txt
```

**Step 2: Configure Environment**
```bash
# Set up development environment:
python scripts/setup_dev_env.py
source .venv/bin/activate  # On Mac/Linux
# or
.venv\Scripts\activate     # On Windows
```

**Step 3: Start with Custom Settings**
```bash
# Start with full features:
streamlit run src/netarchon/web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

## 🏠 First-Time Setup

### Adding Your First Device

**Step 1: Find Your Router's Information**
- **IP Address**: Usually `192.168.1.1`, `192.168.0.1`, or `10.0.0.1`
- **Username**: Often `admin`
- **Password**: Check the sticker on your router, or try `admin`, `password`, or blank

**Step 2: Add Device in NetArchon**
1. In your NetArchon dashboard, click "📱 Devices" in the sidebar
2. Click "Add New Device"
3. Fill in the information:
   - **Name**: "My Router" (or whatever you want to call it)
   - **IP Address**: Your router's IP (like `192.168.1.1`)
   - **Username**: Your router's admin username
   - **Password**: Your router's admin password
4. Click "Test Connection" to make sure it works
5. Click "Add Device" to start monitoring

### Understanding Your Dashboard

**Main Dashboard Sections:**
- **🏠 Network Overview**: Shows overall health of your network
- **📱 Devices**: List of all your network devices and their status
- **📊 Monitoring**: Real-time charts and graphs of your network performance
- **🔒 Security**: Security alerts and device access monitoring
- **⚙️ Configuration**: Backup and manage device settings

**What the Colors Mean:**
- **🟢 Green**: Everything is working normally
- **🟡 Yellow**: Minor issues or warnings
- **🔴 Red**: Problems that need attention
- **⚫ Gray**: Device is offline or not responding

## 🔧 Common Setup Tasks

### Setting Up Alerts

**For Everyone:**
1. Go to "📊 Monitoring" in your dashboard
2. Click "Alert Settings"
3. Choose what you want to be notified about:
   - Internet connection problems
   - Device going offline
   - High data usage
   - Security issues
4. Enter your email address for notifications
5. Click "Save Settings"

**For Technical Users:**
```python
# Configure advanced alert rules programmatically:
from netarchon.monitoring.alert_manager import AlertManager
from netarchon.models.alerts import AlertRule, AlertSeverity

alert_manager = AlertManager()

# Create custom alert for high CPU usage
cpu_alert = AlertRule(
    name="High CPU Usage",
    metric_name="cpu_usage",
    threshold_value=85.0,
    severity=AlertSeverity.WARNING,
    notification_channels=["email", "slack"]
)

alert_manager.add_rule(cpu_alert)
```

### Monitoring Your Internet Speed

**For Everyone:**
1. In your dashboard, look for the "Internet Speed" section
2. NetArchon automatically tests your speed periodically
3. You can click "Test Now" for an immediate speed test
4. Historical speed data is shown in charts

**For Technical Users:**
- Speed tests run every 30 minutes by default
- Data is stored in SQLite database for historical analysis
- Custom speed test intervals can be configured in settings
- API endpoints available for external monitoring integration

### Setting Up Security Monitoring

**For Everyone:**
1. Go to "🔒 Security" in your dashboard
2. NetArchon automatically scans for:
   - Unknown devices connecting to your network
   - Suspicious login attempts
   - Unusual network activity
3. Review the security recommendations and apply them

**For Technical Users:**
- Advanced threat detection using statistical analysis
- Integration with firewall rules for automatic blocking
- Compliance monitoring for RFC 1918 private networks
- Custom security rules and automated responses

## 🌐 Accessing NetArchon from Other Devices

### From Other Computers on Your Network

**For Everyone:**
1. Find your computer's IP address:
   - **Windows**: Open Command Prompt, type `ipconfig`
   - **Mac**: System Preferences → Network
   - **Linux**: Type `ip addr show`
2. On another device, open a web browser
3. Go to: `http://YOUR-COMPUTER-IP:8501`
   - For example: `http://192.168.1.100:8501`

### Setting Up a Dedicated Server (Advanced)

**For Technical Users with a Mini PC or Server:**

**Step 1: Install on Ubuntu/Linux Mint**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git sqlite3

# Create NetArchon user and directory
sudo useradd -m -s /bin/bash netarchon
sudo mkdir -p /opt/netarchon
sudo chown netarchon:netarchon /opt/netarchon
```

**Step 2: Install NetArchon as Service**
```bash
# Switch to netarchon user
sudo su - netarchon

# Install NetArchon
cd /opt/netarchon
git clone https://github.com/diszay/AINetwork.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-web.txt
```

**Step 3: Create System Service**
```bash
# Create systemd service file
sudo tee /etc/systemd/system/netarchon.service > /dev/null <<EOF
[Unit]
Description=NetArchon Network Monitoring
After=network.target

[Service]
Type=simple
User=netarchon
WorkingDirectory=/opt/netarchon
ExecStart=/opt/netarchon/venv/bin/streamlit run src/netarchon/web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable netarchon
sudo systemctl start netarchon
```

**Step 4: Access from Anywhere on Your Network**
- From any device, go to: `http://your-server-ip:8501`
- For example: `http://192.168.1.100:8501`

## 🔍 Verifying Everything Works

### Quick Health Check

**For Everyone:**
1. **Dashboard Loads**: You can see the NetArchon interface at `http://localhost:8501`
2. **Device Connected**: Your router shows as "🟢 Online" in the Devices section
3. **Data Flowing**: You see real-time charts updating in the Monitoring section
4. **Alerts Working**: Test alerts are delivered to your email

**For Technical Users:**
```bash
# Check service status
sudo systemctl status netarchon

# View logs
sudo journalctl -u netarchon -f

# Test database connection
sqlite3 /opt/netarchon/data/metrics.db ".tables"

# Verify network connectivity
ping your-router-ip
```

### Troubleshooting Common Issues

**Problem: Can't access dashboard**
- **Solution**: Make sure NetArchon is running: `streamlit run netarchon`
- **Check**: Firewall isn't blocking port 8501

**Problem: Device won't connect**
- **Solution**: Verify IP address, username, and password
- **Check**: Device has SSH enabled (for advanced monitoring)

**Problem: No data showing**
- **Solution**: Wait 2-3 minutes for initial data collection
- **Check**: Device credentials are correct

## 🎉 What's Next?

### Explore More Features

**For Everyone:**
- **📊 Historical Data**: View trends over days, weeks, and months
- **🔔 Custom Alerts**: Set up notifications for specific conditions
- **📱 Mobile Access**: Access your dashboard from your phone
- **🔒 Security Monitoring**: Keep track of who's on your network

**For Technical Users:**
- **🤖 Automation**: Set up automated responses to network issues
- **📈 Advanced Analytics**: Deep dive into network performance metrics
- **🔧 Custom Integrations**: Connect NetArchon to other systems
- **🌐 Multi-Site Monitoring**: Monitor multiple locations from one dashboard

### Getting Help

**If you need assistance:**
- **Documentation**: Check the [User Guide](user_guide.md) for detailed instructions
- **Troubleshooting**: See the [Troubleshooting Guide](troubleshooting.md) for common issues
- **Community**: Join our [GitHub Discussions](https://github.com/diszay/AINetwork/discussions)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/diszay/AINetwork/issues)

## 📊 Success Checklist

**✅ Installation Complete When:**
- [ ] NetArchon dashboard loads at `http://localhost:8501`
- [ ] At least one device shows as connected
- [ ] Real-time monitoring data is visible
- [ ] Test alert successfully delivered

**✅ Advanced Setup Complete When:**
- [ ] Service runs automatically on system startup
- [ ] Dashboard accessible from other devices on network
- [ ] All desired devices are monitored
- [ ] Custom alerts configured and tested
- [ ] Security monitoring active

**Congratulations!** You now have your own personal AI network assistant monitoring your home network 24/7. NetArchon will keep watch over your internet connection, alert you to problems, and help you maintain optimal network performance.

---

**Next Steps:** Check out the [User Guide](user_guide.md) to learn about all of NetArchon's features, or visit the [Troubleshooting Guide](troubleshooting.md) if you encounter any issues.