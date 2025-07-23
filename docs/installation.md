# NetArchon Installation Guide

**Ready to install NetArchon?** This guide covers everything from simple one-command installation to advanced server deployment.

## 🎯 Choose Your Installation Method

### For Most People: Simple Installation
- **Best for**: Home users who want to try NetArchon
- **Time**: 5 minutes
- **Requirements**: Just a computer with internet

### For Tech Enthusiasts: Advanced Installation  
- **Best for**: Users who want full control and customization
- **Time**: 15-30 minutes
- **Requirements**: Familiarity with command line

### For Dedicated Servers: Production Deployment
- **Best for**: Running NetArchon 24/7 on a dedicated computer
- **Time**: 30-60 minutes
- **Requirements**: Linux server (Ubuntu/Linux Mint recommended)

---

## 🚀 Simple Installation (Recommended)

### Step 1: Check if Python is Installed

**On Windows:**
1. Press `Windows + R`, type `cmd`, press Enter
2. Type: `python --version`
3. If you see a version number (like `Python 3.9.0`), you're good!
4. If not, download Python from [python.org](https://python.org)

**On Mac:**
1. Open Terminal (press `Cmd + Space`, type "Terminal")
2. Type: `python3 --version`
3. If you see a version number, you're good!
4. If not, install using Homebrew: `brew install python3`

**On Linux:**
1. Open Terminal
2. Type: `python3 --version`
3. If you see a version number, you're good!
4. If not, install: `sudo apt install python3 python3-pip`

### Step 2: Install NetArchon

**One simple command:**
```bash
pip install netarchon
```

**If that doesn't work, try:**
```bash
pip3 install netarchon
```

**On Linux, you might need:**
```bash
sudo pip3 install netarchon
```

### Step 3: Start NetArchon

```bash
streamlit run netarchon
```

**You should see something like:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.100:8501
```

### Step 4: Open Your Dashboard

1. Open your web browser
2. Go to: `http://localhost:8501`
3. You should see the NetArchon dashboard!

**🎉 Congratulations!** NetArchon is now running on your computer.

---

## 🔧 Advanced Installation

### Prerequisites

**System Requirements:**
- Python 3.8 or higher
- 2GB RAM minimum (4GB recommended)
- 1GB free disk space
- Network connectivity

**Check Your Python Version:**
```bash
python3 --version
# Should show Python 3.8.0 or higher
```

### Method 1: Install from PyPI (Python Package Index)

**Standard Installation:**
```bash
# Create a virtual environment (recommended)
python3 -m venv netarchon-env
source netarchon-env/bin/activate  # On Mac/Linux
# or
netarchon-env\Scripts\activate     # On Windows

# Install NetArchon
pip install netarchon

# Install additional dependencies for full features
pip install streamlit plotly pandas numpy
```

**With All Optional Dependencies:**
```bash
pip install netarchon[all]
```

### Method 2: Install from Source Code

**Download and Install:**
```bash
# Clone the repository
git clone https://github.com/diszay/AINetwork.git
cd AINetwork

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate     # On Windows

# Install in development mode
pip install -e .

# Install web interface dependencies
pip install -r requirements-web.txt
```

### Method 3: Docker Installation (Advanced)

**Using Docker:**
```bash
# Pull the NetArchon image
docker pull netarchon/netarchon:latest

# Run NetArchon container
docker run -d \
  --name netarchon \
  -p 8501:8501 \
  -v netarchon-data:/data \
  netarchon/netarchon:latest

# Access at http://localhost:8501
```

### Starting NetArchon (Advanced Options)

**Basic Start:**
```bash
streamlit run netarchon
```

**With Custom Configuration:**
```bash
# Custom port
streamlit run netarchon --server.port 8502

# Allow external access
streamlit run netarchon --server.address 0.0.0.0

# With custom config file
export NETARCHON_CONFIG=/path/to/config.yaml
streamlit run netarchon
```

**From Source Code:**
```bash
cd AINetwork
streamlit run src/netarchon/web/streamlit_app.py
```

---

## 🖥️ Production Server Deployment

### Ubuntu 24.04.2 LTS Server Setup (Recommended)

**Step 1: Prepare the Ubuntu Server**
```bash
# Update system packages (Ubuntu 24.04.2 LTS)
sudo apt update && sudo apt upgrade -y

# Install required packages for NetArchon
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    nginx \
    fail2ban \
    ufw \
    htop \
    curl \
    wget

# Create NetArchon system user (no shell login for security)
sudo useradd -r -s /bin/false -d /opt/netarchon netarchon
sudo mkdir -p /opt/netarchon
sudo chown netarchon:netarchon /opt/netarchon
```

**Step 2: Install NetArchon**
```bash
# Switch to netarchon user
sudo su - netarchon

# Navigate to installation directory
cd /opt/netarchon

# Clone repository
git clone https://github.com/diszay/AINetwork.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
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
Group=netarchon
WorkingDirectory=/opt/netarchon
Environment=PATH=/opt/netarchon/venv/bin
ExecStart=/opt/netarchon/venv/bin/streamlit run src/netarchon/web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/netarchon

[Install]
WantedBy=multi-user.target
EOF
```

**Step 4: Enable and Start Service**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable netarchon

# Start the service
sudo systemctl start netarchon

# Check status
sudo systemctl status netarchon
```

**Step 5: Configure Firewall**
```bash
# Allow NetArchon port
sudo ufw allow 8501

# Enable firewall if not already enabled
sudo ufw enable

# Check status
sudo ufw status
```

**Step 6: Optional - Set Up Reverse Proxy (Nginx)**
```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/netarchon > /dev/null <<EOF
server {
    listen 80;
    server_name your-server-name.local;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/netarchon /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Accessing Your Server Installation

**From the same computer:**
- Go to: `http://localhost:8501`

**From other devices on your network:**
- Find your server's IP address: `ip addr show`
- Go to: `http://YOUR-SERVER-IP:8501`
- Example: `http://192.168.1.100:8501`

**With Nginx reverse proxy:**
- Go to: `http://your-server-name.local`

---

## 🔧 Configuration

### Environment Variables

**Common Configuration Options:**
```bash
# Set custom configuration file
export NETARCHON_CONFIG=/path/to/config.yaml

# Set data directory
export NETARCHON_DATA_DIR=/path/to/data

# Set log level
export NETARCHON_LOG_LEVEL=INFO

# BitWarden integration
export BITWARDEN_MASTER_PASSWORD=your_password
```

### Configuration File

**Create `config.yaml`:**
```yaml
# NetArchon Configuration
server:
  host: "0.0.0.0"
  port: 8501
  
database:
  path: "/opt/netarchon/data/netarchon.db"
  
logging:
  level: "INFO"
  file: "/opt/netarchon/logs/netarchon.log"
  
monitoring:
  interval: 60  # seconds
  retention_days: 30
  
alerts:
  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@gmail.com"
    # password stored in environment variable
```

---

## 🧪 Verifying Installation

### Quick Health Check

**1. Check if NetArchon is running:**
```bash
# Look for NetArchon process
ps aux | grep streamlit

# Check if port is open
netstat -tlnp | grep 8501
```

**2. Test web interface:**
- Open browser to `http://localhost:8501`
- You should see the NetArchon dashboard
- Try navigating between different pages

**3. Check logs:**
```bash
# For systemd service
sudo journalctl -u netarchon -f

# For manual installation
tail -f ~/.streamlit/logs/streamlit.log
```

### Troubleshooting Installation Issues

**Problem: "Command not found: streamlit"**
```bash
# Make sure Streamlit is installed
pip install streamlit

# Check if it's in your PATH
which streamlit
```

**Problem: "Permission denied"**
```bash
# Try with sudo (not recommended for production)
sudo pip install netarchon

# Or use user installation
pip install --user netarchon
```

**Problem: "Port already in use"**
```bash
# Find what's using port 8501
sudo lsof -i :8501

# Use a different port
streamlit run netarchon --server.port 8502
```

**Problem: "Module not found"**
```bash
# Make sure you're in the right virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 🔄 Updating NetArchon

### Simple Update

**If installed via pip:**
```bash
pip install --upgrade netarchon
```

### Advanced Update

**If installed from source:**
```bash
cd /path/to/AINetwork
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-web.txt

# Restart service if running as daemon
sudo systemctl restart netarchon
```

### Backup Before Updating

**Important data to backup:**
```bash
# Configuration files
cp config.yaml config.yaml.backup

# Database (if using SQLite)
cp data/netarchon.db data/netarchon.db.backup

# Custom configurations
cp -r ~/.netarchon ~/.netarchon.backup
```

---

## 🆘 Getting Help

**If installation fails:**

1. **Check the [Troubleshooting Guide](troubleshooting.md)**
2. **Search [GitHub Issues](https://github.com/diszay/AINetwork/issues)**
3. **Ask in [GitHub Discussions](https://github.com/diszay/AINetwork/discussions)**
4. **Create a new issue** with:
   - Your operating system
   - Python version (`python --version`)
   - Complete error message
   - Steps you tried

**Include this information when asking for help:**
```bash
# System information
uname -a
python3 --version
pip --version

# NetArchon version (if installed)
pip show netarchon

# Error logs
tail -n 50 ~/.streamlit/logs/streamlit.log
```

---

## ✅ Installation Complete!

**Once NetArchon is running, you can:**

1. **Access your dashboard** at `http://localhost:8501`
2. **Add your first device** using the web interface
3. **Configure monitoring** for your network
4. **Set up alerts** for important events
5. **Explore all features** through the intuitive web interface

**Next steps:**
- Read the [Quick Start Guide](quickstart.md) to get started
- Check out the [User Guide](user_guide.md) for detailed instructions
- Review the [Security Implementation](security_implementation.md) to understand how NetArchon protects you

**Welcome to NetArchon!** Your personal AI network assistant is ready to help you manage your home network.