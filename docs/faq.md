# NetArchon Frequently Asked Questions (FAQ)

**Got questions about NetArchon?** This FAQ covers the most common questions from both beginners and technical users.

## 🤔 General Questions

### What is NetArchon?

**Simple Answer:**
NetArchon is like having a professional network engineer living in your home, watching over your internet connection 24/7. It monitors your internet speed, tracks all your connected devices, and alerts you when something needs attention.

**Technical Answer:**
NetArchon is an AI-powered network management system that provides comprehensive monitoring, automated configuration management, intelligent alerting, and security analysis for home and small business networks. It integrates with BitWarden for credential management and RustDesk for remote desktop monitoring.

### Do I need to be technical to use NetArchon?

**No!** NetArchon is designed for everyone:
- **Beginners**: Use the simple web dashboard to monitor your network
- **Tech enthusiasts**: Access advanced features and automation
- **Network professionals**: Full API access and customization options

### What devices does NetArchon work with?

**Home Devices:**
- Any WiFi router (Netgear, Linksys, ASUS, etc.)
- Cable/DSL modems (Arris, Motorola, etc.)
- Smart home devices
- Computers, phones, tablets

**Professional Equipment:**
- Cisco routers and switches
- Juniper Networks equipment
- Arista switches
- Any device that supports SSH

### Is NetArchon free?

**Yes!** NetArchon is open-source software that you can use for free. You can:
- Download and install it at no cost
- Use all features without limitations
- Modify it for your needs (if you're technical)
- Contribute improvements back to the community

## 🔧 Installation & Setup

### How do I install NetArchon?

**Simple Installation:**
```bash
pip install netarchon
streamlit run netarchon
```
Then open `http://localhost:8501` in your browser.

**Detailed Instructions:**
See our [Installation Guide](installation.md) for complete step-by-step instructions.

### What do I need to run NetArchon?

**Minimum Requirements:**
- Any computer (Windows, Mac, or Linux)
- Python 3.8 or higher
- 2GB RAM
- Internet connection

**Recommended Setup:**
- Dedicated Mini PC or server
- 4GB RAM
- Ubuntu 24.04 LTS or Linux Mint
- Always-on internet connection

### Can I run NetArchon on a Raspberry Pi?

**Yes!** NetArchon works great on Raspberry Pi:
- Raspberry Pi 4 with 4GB RAM (recommended)
- Raspberry Pi 3B+ with 2GB RAM (minimum)
- Use Raspberry Pi OS or Ubuntu Server
- Follow the Linux installation instructions

### How do I access NetArchon from other devices?

**From other computers on your network:**
1. Find your NetArchon computer's IP address
2. Open a browser on any device
3. Go to: `http://YOUR-COMPUTER-IP:8501`
4. Example: `http://192.168.1.100:8501`

## 🏠 Home Network Monitoring

### What will NetArchon monitor in my home?

**Automatically Monitored:**
- Internet speed and connectivity
- All connected devices (phones, laptops, smart TVs, etc.)
- WiFi signal strength and quality
- Data usage and bandwidth consumption
- Device connection/disconnection events

**With Device Credentials:**
- Router configuration and status
- Modem signal quality
- Advanced network metrics
- Security settings and logs

### How does NetArchon know about my devices?

**Automatic Discovery:**
NetArchon scans your network to find devices automatically. It can detect:
- Device names and types
- IP and MAC addresses
- Connection status
- Basic information

**Enhanced Monitoring:**
For routers and modems, you can provide admin credentials for detailed monitoring of:
- Configuration settings
- Performance metrics
- Security logs
- Advanced diagnostics

### Will NetArchon slow down my internet?

**No!** NetArchon is designed to be network-friendly:
- Uses minimal bandwidth for monitoring
- Runs lightweight scans that don't impact performance
- Configurable monitoring intervals
- Optimized for home network environments

### Can NetArchon monitor my internet usage?

**Yes!** NetArchon tracks:
- Total data usage over time
- Usage by device
- Peak usage times
- Trends and patterns
- Data cap warnings (if applicable)

## 🔒 Security & Privacy

### Is NetArchon secure?

**Absolutely!** Security is our top priority:
- **Local Operation**: All data stays on your computer
- **Encrypted Storage**: Passwords protected with military-grade encryption
- **Home Network Only**: Cannot access anything outside your network
- **No Data Collection**: We don't collect or transmit your personal data
- **Open Source**: Code is publicly auditable

### What information does NetArchon collect?

**NetArchon only collects information about your network:**
- Device connection status
- Network performance metrics
- Configuration backups (stored locally)
- Security events and alerts

**NetArchon NEVER collects:**
- Personal files or documents
- Web browsing history
- Personal communications
- Data from outside your network

### Where is my data stored?

**Everything stays local:**
- Data stored on your computer only
- SQLite database in your NetArchon directory
- Configuration backups in local folders
- No cloud storage or external transmission

### Can NetArchon access my personal files?

**No!** NetArchon only monitors network-related information:
- Network device status and configuration
- Internet connectivity and performance
- Device connection events
- Network security events

It cannot and does not access personal files, documents, or applications.

## 🔐 Password Management

### How does BitWarden integration work?

**For Everyone:**
If you use BitWarden password manager, NetArchon can automatically retrieve your router and device passwords, so you don't have to enter them manually.

**Technical Details:**
- Secure API integration with BitWarden CLI
- Encrypted credential storage with AES-256
- Automatic device-to-credential mapping
- Fallback to manual credentials if needed

### Do I need BitWarden to use NetArchon?

**No!** BitWarden integration is optional:
- **With BitWarden**: Automatic password management
- **Without BitWarden**: Enter device passwords manually
- Both methods work equally well

### Is it safe to store my router passwords in NetArchon?

**Yes!** NetArchon uses enterprise-grade security:
- AES-256 encryption for all stored passwords
- PBKDF2 password hashing with 100,000 iterations
- Secure key derivation and storage
- Local storage only (never transmitted)

## 📊 Monitoring & Alerts

### What kind of alerts can NetArchon send?

**Common Alerts:**
- Internet connection problems
- Device going offline
- High data usage
- Slow internet speeds
- Security threats
- Configuration changes

**Alert Methods:**
- Email notifications
- In-dashboard notifications
- Webhook integrations
- Slack messages (if configured)

### How do I set up email alerts?

**Simple Setup:**
1. Go to "📊 Monitoring" in your dashboard
2. Click "Alert Settings"
3. Enter your email address
4. Configure what you want to be notified about
5. Test the alert system

**Technical Setup:**
Configure SMTP settings in the configuration file or environment variables.

### Can I customize alert thresholds?

**Yes!** You can adjust:
- CPU usage thresholds
- Memory usage limits
- Internet speed minimums
- Data usage warnings
- Device offline timeouts
- Custom metric thresholds

## 🖥️ Remote Desktop Monitoring

### What is RustDesk integration?

**For Everyone:**
If you use remote desktop software to access your computers from anywhere, NetArchon can monitor those connections to ensure they're secure and working properly.

**Technical Details:**
RustDesk is an open-source remote desktop solution. NetArchon can:
- Monitor active remote desktop sessions
- Track connection security and performance
- Deploy RustDesk clients automatically
- Analyze connection logs for security events

### Do I need RustDesk to use NetArchon?

**No!** RustDesk integration is optional:
- NetArchon works perfectly without RustDesk
- RustDesk features are additional capabilities
- You can enable it later if interested

## 🔧 Technical Questions

### What programming language is NetArchon written in?

**Python** - NetArchon is built entirely in Python, making it:
- Easy to install and run
- Highly portable across platforms
- Simple to modify and extend
- Well-supported with extensive libraries

### Can I integrate NetArchon with other systems?

**Yes!** NetArchon provides:
- **REST API**: Full programmatic access
- **WebSocket API**: Real-time data streaming
- **Webhook Support**: Send alerts to external systems
- **Database Access**: Direct SQLite database access
- **Plugin Architecture**: Extensible design for custom integrations

### How do I backup my NetArchon configuration?

**Simple Backup:**
```bash
# Backup configuration and data
cp -r ~/.netarchon ~/.netarchon.backup
cp config.yaml config.yaml.backup
cp data/netarchon.db data/netarchon.db.backup
```

**Automated Backup:**
NetArchon can automatically backup configurations and create restore points.

### Can I run multiple instances of NetArchon?

**Yes, but typically not needed:**
- One instance can monitor multiple networks
- Multiple instances can run on different ports
- Useful for managing separate network segments
- Each instance needs its own configuration

### How do I update NetArchon?

**Simple Update:**
```bash
pip install --upgrade netarchon
```

**From Source:**
```bash
cd AINetwork
git pull origin main
pip install -r requirements.txt
```

## 🌐 Network Compatibility

### What internet providers does NetArchon work with?

**All of them!** NetArchon works with any internet provider:
- Xfinity/Comcast
- AT&T
- Verizon
- Spectrum
- Local ISPs
- Fiber, cable, DSL, satellite

### What router brands are supported?

**Popular Home Routers:**
- Netgear (including Orbi mesh)
- Linksys
- ASUS
- TP-Link
- D-Link
- Belkin

**Professional Equipment:**
- Cisco
- Juniper
- Arista
- Ubiquiti
- MikroTik

### Does NetArchon work with mesh networks?

**Yes!** NetArchon fully supports mesh networks:
- Monitors main router and satellites
- Tracks device connections across mesh nodes
- Monitors backhaul connections
- Supports popular mesh systems (Orbi, Eero, etc.)

### Can NetArchon monitor VLANs?

**Yes!** For advanced users:
- VLAN discovery and monitoring
- Inter-VLAN traffic analysis
- VLAN configuration management
- Security monitoring across VLANs

## 🚀 Performance & Scaling

### How much system resources does NetArchon use?

**Typical Usage:**
- **CPU**: 1-5% on average
- **RAM**: 200-500MB
- **Disk**: 100MB for application, variable for data
- **Network**: Minimal bandwidth usage

### How many devices can NetArchon monitor?

**Practical Limits:**
- **Home Networks**: 50-100 devices easily
- **Small Business**: 200-500 devices
- **Large Networks**: 1000+ devices (with proper hardware)

Performance depends on your computer's specifications and monitoring frequency.

### Can I monitor multiple locations?

**Yes!** NetArchon can monitor:
- Multiple network segments
- Remote locations (with VPN)
- Branch offices
- Multiple homes/properties

## 🆘 Troubleshooting

### NetArchon won't start - what do I do?

**Common Solutions:**
1. Check if Python is installed: `python --version`
2. Reinstall NetArchon: `pip install --upgrade netarchon`
3. Check for port conflicts: Try a different port
4. Review error messages in the terminal

**Get Help:**
- Check the [Troubleshooting Guide](troubleshooting.md)
- Search [GitHub Issues](https://github.com/diszay/AINetwork/issues)
- Ask in [GitHub Discussions](https://github.com/diszay/AINetwork/discussions)

### My devices show as offline but they're working

**Common Causes:**
- Incorrect IP addresses
- Firewall blocking NetArchon
- Device doesn't support monitoring protocol
- Network connectivity issues

**Solutions:**
- Verify device IP addresses
- Check firewall settings
- Test manual connection to device
- Review NetArchon logs for errors

### I'm not receiving email alerts

**Check These:**
1. Email address entered correctly
2. SMTP settings configured properly
3. Check spam/junk folder
4. Test email settings
5. Verify internet connectivity

## 🤝 Community & Support

### How do I get help with NetArchon?

**Self-Help Resources:**
1. [Installation Guide](installation.md)
2. [User Guide](user_guide.md)
3. [Troubleshooting Guide](troubleshooting.md)
4. [API Documentation](api_documentation.md)

**Community Support:**
- [GitHub Discussions](https://github.com/diszay/AINetwork/discussions) - Ask questions
- [GitHub Issues](https://github.com/diszay/AINetwork/issues) - Report bugs
- Community forums and chat groups

### How can I contribute to NetArchon?

**Everyone Can Help:**
- Report bugs and issues
- Suggest new features
- Improve documentation
- Share your experience

**Technical Contributors:**
- Fix bugs and add features
- Write tests and documentation
- Review code and help others
- Create integrations and plugins

See our [Contributing Guide](contributing.md) for details.

### Is there commercial support available?

**Currently:**
NetArchon is a community-driven open-source project with community support through GitHub.

**Future:**
Commercial support options may be available in the future for enterprise users.

## 🔮 Future Plans

### What new features are planned?

**Short Term:**
- Enhanced RustDesk integration
- Advanced security monitoring
- Mobile-responsive dashboard
- Additional device support

**Long Term:**
- AI-powered network optimization
- Predictive failure detection
- Advanced analytics and reporting
- Cloud integration options

### Can I request new features?

**Absolutely!** We welcome feature requests:
1. Check existing [GitHub Issues](https://github.com/diszay/AINetwork/issues)
2. Create a new feature request
3. Participate in [GitHub Discussions](https://github.com/diszay/AINetwork/discussions)
4. Contribute code if you're technical

---

## 📞 Still Have Questions?

**If you can't find your answer here:**

1. **Search the documentation** - Check all our guides
2. **Search GitHub Issues** - Someone may have asked before
3. **Ask the community** - Post in GitHub Discussions
4. **Report bugs** - Create a GitHub Issue
5. **Contact maintainers** - For urgent issues

**When asking for help, please include:**
- Your operating system
- Python version
- NetArchon version
- Complete error messages
- Steps to reproduce the problem

**We're here to help!** The NetArchon community is friendly and welcoming to users of all skill levels.