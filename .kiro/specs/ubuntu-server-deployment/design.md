# Ubuntu 24.04.2 LTS Server Deployment Design

## Overview

This design document outlines the architecture and implementation approach for deploying NetArchon on Ubuntu 24.04.2 LTS Server, providing a robust, secure, and maintainable home network monitoring solution.

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Ubuntu 24.04.2 LTS Server                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │   systemd   │ │    nginx    │ │      fail2ban           │ │
│  │   Services  │ │ (optional)  │ │   Security              │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              NetArchon Application                      │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │  Streamlit  │ │   Python    │ │     SQLite          │ │ │
│  │  │    Web UI   │ │    Core     │ │    Database         │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Network Monitoring                       │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ BitWarden   │ │  RustDesk   │ │   Device Monitoring │ │ │
│  │  │Integration  │ │Integration  │ │     & Alerting      │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
           │                 │                      │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│ Home Network    │ │  Remote Access  │ │    External APIs    │
│    Devices      │ │   (SSH/Web)     │ │   (BitWarden/etc)   │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
```

### Directory Structure

```
/opt/netarchon/                    # Main application directory
├── venv/                          # Python virtual environment
├── src/                           # NetArchon source code
├── config/                        # Configuration files
│   ├── netarchon.yaml            # Main configuration
│   ├── systemd/                  # systemd service files
│   └── nginx/                    # nginx configuration (optional)
├── data/                          # Data storage
│   ├── database/                 # SQLite databases
│   ├── logs/                     # Application logs
│   └── backups/                  # Automated backups
├── scripts/                       # Deployment and maintenance scripts
│   ├── install.sh                # Installation script
│   ├── backup.sh                 # Backup script
│   ├── update.sh                 # Update script
│   └── health-check.sh           # Health monitoring
└── docs/                          # Local documentation
```

### User and Permissions Structure

```
User: netarchon (system user, no shell login)
Group: netarchon
Home: /opt/netarchon

Permissions:
/opt/netarchon/          755 netarchon:netarchon
/opt/netarchon/data/     750 netarchon:netarchon
/opt/netarchon/config/   750 netarchon:netarchon
/opt/netarchon/logs/     750 netarchon:netarchon
```

## Components and Interfaces

### 1. Base System Configuration

**Ubuntu 24.04.2 LTS Server Setup:**
- Minimal server installation (no GUI)
- Static IP configuration
- Automatic security updates enabled
- Essential packages only
- Optimized for headless operation

**Key Packages:**
```bash
# System packages
python3 (3.12+)
python3-pip
python3-venv
git
sqlite3
nginx (optional)
fail2ban
ufw (firewall)
htop
curl
wget

# Python packages (in virtual environment)
streamlit>=1.28.0
plotly>=5.15.0
pandas>=2.0.0
numpy>=1.24.0
paramiko>=3.0.0
cryptography>=41.0.0
```

### 2. Network Configuration

**Static IP Configuration:**
```yaml
# /etc/netplan/01-netcfg.yaml
network:
  version: 2
  ethernets:
    enp0s3:  # Adjust interface name as needed
      dhcp4: false
      addresses:
        - 192.168.1.100/24  # Adjust to your network
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

**Firewall Configuration:**
```bash
# UFW rules
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 8501/tcp  # NetArchon web interface
ufw enable
```

### 3. Service Management

**systemd Service Configuration:**
```ini
# /etc/systemd/system/netarchon.service
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
```

### 4. Database Configuration

**SQLite Database Setup:**
- Primary database: `/opt/netarchon/data/database/netarchon.db`
- WAL mode enabled for concurrent access
- Automatic backup every 6 hours
- 30-day retention policy for backups
- Database integrity checks on startup

**Database Schema:**
```sql
-- Core tables for Ubuntu deployment
CREATE TABLE system_info (
    id INTEGER PRIMARY KEY,
    hostname TEXT,
    os_version TEXT,
    kernel_version TEXT,
    uptime INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE network_interfaces (
    id INTEGER PRIMARY KEY,
    interface_name TEXT,
    ip_address TEXT,
    mac_address TEXT,
    status TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE service_status (
    id INTEGER PRIMARY KEY,
    service_name TEXT,
    status TEXT,
    pid INTEGER,
    memory_usage INTEGER,
    cpu_usage REAL,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Monitoring Integration

**System Monitoring:**
- CPU, memory, disk usage monitoring
- Network interface statistics
- Service health monitoring
- Log file monitoring
- Temperature monitoring (if available)

**Network Device Monitoring:**
- Home router monitoring
- Internet connectivity checks
- Device discovery and tracking
- Bandwidth usage monitoring
- Security event detection

## Data Models

### Configuration Model

```python
@dataclass
class UbuntuServerConfig:
    """Ubuntu 24.04.2 LTS Server specific configuration."""
    
    # System configuration
    hostname: str
    static_ip: str
    gateway: str
    dns_servers: List[str]
    
    # NetArchon configuration
    web_port: int = 8501
    data_directory: str = "/opt/netarchon/data"
    log_directory: str = "/opt/netarchon/logs"
    backup_directory: str = "/opt/netarchon/data/backups"
    
    # Service configuration
    auto_start: bool = True
    restart_policy: str = "always"
    resource_limits: Dict[str, str] = field(default_factory=lambda: {
        "memory": "2G",
        "cpu": "50%"
    })
    
    # Security configuration
    firewall_enabled: bool = True
    ssh_key_only: bool = True
    fail2ban_enabled: bool = True
    auto_updates: bool = True
```

### System Metrics Model

```python
@dataclass
class UbuntuSystemMetrics:
    """System metrics specific to Ubuntu server deployment."""
    
    timestamp: datetime
    
    # System resources
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    load_average: Tuple[float, float, float]
    
    # Network statistics
    network_interfaces: List[NetworkInterfaceStats]
    network_connections: int
    
    # Service status
    netarchon_status: str
    nginx_status: Optional[str]
    ssh_status: str
    
    # Security metrics
    failed_login_attempts: int
    firewall_blocked_connections: int
    
    # System information
    uptime: int
    kernel_version: str
    system_load: float
```

## Error Handling

### Service Recovery

**Automatic Recovery Mechanisms:**
1. **Service Restart**: systemd automatically restarts failed services
2. **Database Recovery**: Automatic database repair on corruption detection
3. **Network Recovery**: Automatic reconnection on network issues
4. **Resource Management**: Automatic cleanup when resource limits exceeded

**Monitoring and Alerting:**
```python
class UbuntuServiceMonitor:
    """Monitor Ubuntu-specific services and system health."""
    
    def check_system_health(self) -> SystemHealthStatus:
        """Check overall system health."""
        return SystemHealthStatus(
            cpu_ok=self.check_cpu_usage(),
            memory_ok=self.check_memory_usage(),
            disk_ok=self.check_disk_space(),
            services_ok=self.check_services(),
            network_ok=self.check_network()
        )
    
    def handle_service_failure(self, service: str, error: Exception):
        """Handle service failure with Ubuntu-specific recovery."""
        if service == "netarchon":
            self.restart_netarchon_service()
        elif service == "nginx":
            self.restart_nginx_service()
        
        self.log_service_failure(service, error)
        self.send_alert(f"Service {service} failed: {error}")
```

### Log Management

**Centralized Logging:**
- systemd journal integration
- Automatic log rotation
- Error aggregation and alerting
- Performance monitoring

```bash
# Log monitoring commands
journalctl -u netarchon -f          # Follow NetArchon logs
journalctl -u netarchon --since today  # Today's logs
systemctl status netarchon           # Service status
```

## Testing Strategy

### Installation Testing

**Automated Installation Verification:**
```bash
#!/bin/bash
# test-installation.sh

# Test system requirements
test_ubuntu_version() {
    version=$(lsb_release -rs)
    if [[ "$version" == "24.04" ]]; then
        echo "✓ Ubuntu 24.04.2 LTS detected"
        return 0
    else
        echo "✗ Wrong Ubuntu version: $version"
        return 1
    fi
}

# Test Python environment
test_python_environment() {
    if /opt/netarchon/venv/bin/python --version | grep -q "3.12"; then
        echo "✓ Python 3.12 environment ready"
        return 0
    else
        echo "✗ Python environment not ready"
        return 1
    fi
}

# Test NetArchon service
test_netarchon_service() {
    if systemctl is-active --quiet netarchon; then
        echo "✓ NetArchon service is running"
        return 0
    else
        echo "✗ NetArchon service is not running"
        return 1
    fi
}

# Test web interface
test_web_interface() {
    if curl -s http://localhost:8501 > /dev/null; then
        echo "✓ Web interface is accessible"
        return 0
    else
        echo "✗ Web interface is not accessible"
        return 1
    fi
}

# Run all tests
main() {
    echo "Testing NetArchon Ubuntu 24.04.2 LTS deployment..."
    
    test_ubuntu_version || exit 1
    test_python_environment || exit 1
    test_netarchon_service || exit 1
    test_web_interface || exit 1
    
    echo "✓ All tests passed! NetArchon is ready."
}

main "$@"
```

### Performance Testing

**System Performance Benchmarks:**
- Boot time: < 60 seconds to full NetArchon availability
- Memory usage: < 1GB under normal load
- CPU usage: < 10% average during monitoring
- Web response time: < 2 seconds for dashboard load
- Database query time: < 100ms for standard queries

### Security Testing

**Security Validation:**
- Firewall configuration verification
- SSH key-only authentication test
- Service privilege verification
- File permission validation
- Network access restriction testing

## Deployment Considerations

### Hardware Requirements

**Minimum Specifications:**
- CPU: 2 cores, 1.5GHz (ARM64 or x86_64)
- RAM: 2GB
- Storage: 32GB (SSD recommended)
- Network: Ethernet connection preferred

**Recommended Specifications:**
- CPU: 4 cores, 2.0GHz
- RAM: 4GB
- Storage: 128GB SSD
- Network: Gigabit Ethernet

### Network Integration

**Home Network Compatibility:**
- Works with any router/modem combination
- Supports both IPv4 and IPv6
- Compatible with mesh networks
- Handles DHCP and static IP configurations
- Integrates with existing network security

### Maintenance Procedures

**Regular Maintenance Tasks:**
```bash
# Weekly maintenance script
#!/bin/bash
# weekly-maintenance.sh

# Update system packages
apt update && apt upgrade -y

# Clean up old logs
journalctl --vacuum-time=30d

# Backup database
/opt/netarchon/scripts/backup.sh

# Check disk space
df -h /opt/netarchon

# Restart services if needed
systemctl restart netarchon

echo "Weekly maintenance completed"
```

This design provides a robust, secure, and maintainable deployment of NetArchon specifically optimized for Ubuntu 24.04.2 LTS Server, ensuring reliable home network monitoring with minimal administrative overhead.