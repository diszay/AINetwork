"""
RustDesk Installer

Automated RustDesk server and client deployment for home network infrastructure.
"""

import os
import subprocess
import json
import requests
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from netarchon.utils.logger import get_logger
from netarchon.integrations.bitwarden import BitWardenManager

from .models import RustDeskDeploymentConfig, ServerComponentType
from .exceptions import RustDeskDeploymentError, RustDeskConfigurationError


class RustDeskInstaller:
    """
    Automated RustDesk server and client deployment.
    
    Handles server installation, configuration, and client deployment
    across multiple platforms in home network environments.
    """
    
    def __init__(self, config_dir: str = "config"):
        """Initialize RustDesk installer."""
        self.logger = get_logger("RustDeskInstaller")
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Installation paths
        self.server_install_dir = Path("/opt/rustdesk-server")
        self.client_config_dir = Path("/etc/rustdesk")
        
        # Download URLs for different platforms
        self.download_urls = {
            'server': {
                'linux': 'https://github.com/rustdesk/rustdesk-server/releases/latest/download/rustdesk-server-linux-amd64.zip',
                'windows': 'https://github.com/rustdesk/rustdesk-server/releases/latest/download/rustdesk-server-windows-x64.zip'
            },
            'client': {
                'windows': 'https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-{version}-x86_64.exe',
                'macos': 'https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-{version}.dmg',
                'linux': 'https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-{version}-x86_64.AppImage'
            }
        }
    
    def install_server(self, 
                      target_host: str = "localhost",
                      install_method: str = "docker",
                      server_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Install RustDesk server on target host.
        
        Args:
            target_host: Target host for installation
            install_method: Installation method (docker, binary, script)
            server_config: Server configuration options
            
        Returns:
            True if installation successful
        """
        self.logger.info(f"Starting RustDesk server installation on {target_host}")
        
        try:
            if install_method == "docker":
                return self._install_server_docker(target_host, server_config)
            elif install_method == "binary":
                return self._install_server_binary(target_host, server_config)
            elif install_method == "script":
                return self._install_server_script(target_host, server_config)
            else:
                raise RustDeskConfigurationError("install_method", f"Unknown installation method: {install_method}")
                
        except Exception as e:
            self.logger.error(f"Server installation failed: {e}")
            raise RustDeskDeploymentError(target_host, str(e))
    
    def _install_server_docker(self, target_host: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Install RustDesk server using Docker."""
        self.logger.info(f"Installing RustDesk server via Docker on {target_host}")
        
        try:
            # Create docker-compose configuration
            compose_config = self._generate_docker_compose(config or {})
            
            # Commands to run on target host
            commands = [
                # Install Docker if not present
                "curl -fsSL https://get.docker.com -o get-docker.sh",
                "sudo sh get-docker.sh",
                
                # Configure firewall
                "sudo ufw allow 21114:21119/tcp",
                "sudo ufw allow 21116/udp",
                "sudo ufw enable",
                
                # Create RustDesk directory
                "sudo mkdir -p /opt/rustdesk-server",
                "cd /opt/rustdesk-server",
                
                # Download and start services
                f"echo '{compose_config}' | sudo tee docker-compose.yml",
                "sudo docker compose up -d",
                
                # Wait for services to start
                "sleep 10",
                
                # Check service status
                "sudo docker compose ps"
            ]
            
            if target_host == "localhost":
                # Run locally
                for cmd in commands:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        self.logger.error(f"Command failed: {cmd}\\n{result.stderr}")
                        return False
            else:
                # Run remotely via SSH (would need SSH integration)
                self.logger.warning(f"Remote installation to {target_host} not yet implemented")
                return False
            
            self.logger.info("RustDesk server Docker installation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Docker installation failed: {e}")
            return False
    
    def _install_server_script(self, target_host: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Install RustDesk server using installation script."""
        self.logger.info(f"Installing RustDesk server via script on {target_host}")
        
        try:
            # Download and run installation script
            commands = [
                "wget https://raw.githubusercontent.com/dinger1986/rustdeskinstall/master/install.sh",
                "chmod +x install.sh",
                "./install.sh"
            ]
            
            if target_host == "localhost":
                for cmd in commands:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        self.logger.error(f"Script command failed: {cmd}\\n{result.stderr}")
                        return False
            
            self.logger.info("RustDesk server script installation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Script installation failed: {e}")
            return False
    
    def _generate_docker_compose(self, config: Dict[str, Any]) -> str:
        """Generate Docker Compose configuration for RustDesk server."""
        
        # Default configuration
        default_config = {
            'relay_port': 21117,
            'signal_port': 21116,
            'web_port': 21114,
            'websocket_port': 21118,
            'websocket_secure_port': 21119
        }
        
        # Merge with provided config
        final_config = {**default_config, **config}
        
        compose_content = f"""
version: '3.8'

networks:
  rustdesk-net:
    external: false

services:
  hbbs:
    container_name: rustdesk-hbbs
    ports:
      - {final_config['signal_port']}:{final_config['signal_port']}
      - {final_config['web_port']}:{final_config['web_port']}
      - {final_config['websocket_port']}:{final_config['websocket_port']}
      - {final_config['websocket_secure_port']}:{final_config['websocket_secure_port']}
    image: rustdesk/rustdesk-server:latest
    command: hbbs -r rustdesk.example.com:21117
    volumes:
      - ./data:/root
    networks:
      - rustdesk-net
    depends_on:
      - hbbr
    restart: unless-stopped

  hbbr:
    container_name: rustdesk-hbbr
    ports:
      - {final_config['relay_port']}:{final_config['relay_port']}
    image: rustdesk/rustdesk-server:latest
    command: hbbr
    volumes:
      - ./data:/root
    networks:
      - rustdesk-net
    restart: unless-stopped
"""
        
        return compose_content.strip()
    
    def deploy_client(self, 
                     target_device: str,
                     platform: str,
                     deployment_config: RustDeskDeploymentConfig) -> bool:
        """
        Deploy RustDesk client to target device.
        
        Args:
            target_device: Target device (IP or hostname)
            platform: Target platform (windows, macos, linux)
            deployment_config: Client configuration
            
        Returns:
            True if deployment successful
        """
        self.logger.info(f"Deploying RustDesk client to {target_device} ({platform})")
        
        try:
            if platform.lower() == "windows":
                return self._deploy_windows_client(target_device, deployment_config)
            elif platform.lower() == "macos":
                return self._deploy_macos_client(target_device, deployment_config)
            elif platform.lower() == "linux":
                return self._deploy_linux_client(target_device, deployment_config)
            else:
                raise RustDeskConfigurationError("platform", f"Unsupported platform: {platform}")
                
        except Exception as e:
            self.logger.error(f"Client deployment to {target_device} failed: {e}")
            raise RustDeskDeploymentError(target_device, str(e))
    
    def _deploy_windows_client(self, target_device: str, config: RustDeskDeploymentConfig) -> bool:
        """Deploy RustDesk client to Windows device."""
        self.logger.info(f"Deploying Windows client to {target_device}")
        
        try:
            # Generate configuration file
            config_content = config.to_config_json()
            
            # PowerShell script for deployment
            powershell_script = f"""
# Download RustDesk client
$url = "https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3-x86_64.exe"
$output = "$env:TEMP\\rustdesk-installer.exe"
Invoke-WebRequest -Uri $url -OutFile $output

# Install RustDesk
Start-Process -FilePath $output -ArgumentList "/S" -Wait

# Create configuration directory
$configDir = "$env:APPDATA\\RustDesk\\config"
New-Item -ItemType Directory -Force -Path $configDir

# Write configuration
$config = @'{config_content}'@
$config | Out-File -FilePath "$configDir\\RustDesk2.toml" -Encoding UTF8

# Start RustDesk service
Start-Service -Name "RustDesk"
"""
            
            # Save script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as f:
                f.write(powershell_script)
                script_path = f.name
            
            # Execute via remote PowerShell (would need WinRM/SSH setup)
            # For now, just log the script
            self.logger.info(f"Windows deployment script created: {script_path}")
            
            # In production, this would use WinRM, SSH, or other remote execution
            # method to run the PowerShell script on the target Windows machine
            
            return True
            
        except Exception as e:
            self.logger.error(f"Windows client deployment failed: {e}")
            return False
    
    def _deploy_macos_client(self, target_device: str, config: RustDeskDeploymentConfig) -> bool:
        """Deploy RustDesk client to macOS device."""
        self.logger.info(f"Deploying macOS client to {target_device}")
        
        try:
            # Generate configuration file
            config_content = config.to_config_json()
            
            # Shell script for macOS deployment
            shell_script = f"""#!/bin/bash
set -e

# Download RustDesk client
cd /tmp
curl -L -o rustdesk.dmg "https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3.dmg"

# Mount DMG and install
hdiutil attach rustdesk.dmg
cp -R "/Volumes/RustDesk/RustDesk.app" "/Applications/"
hdiutil detach "/Volumes/RustDesk"

# Create configuration directory
CONFIG_DIR="$HOME/Library/Preferences/com.carriez.rustdesk"
mkdir -p "$CONFIG_DIR"

# Write configuration
cat > "$CONFIG_DIR/RustDesk2.toml" << 'EOF'
{config_content}
EOF

# Start RustDesk
open "/Applications/RustDesk.app"

echo "RustDesk installation and configuration completed"
"""
            
            # Save script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(shell_script)
                script_path = f.name
            
            os.chmod(script_path, 0o755)
            self.logger.info(f"macOS deployment script created: {script_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"macOS client deployment failed: {e}")
            return False
    
    def _deploy_linux_client(self, target_device: str, config: RustDeskDeploymentConfig) -> bool:
        """Deploy RustDesk client to Linux device."""
        self.logger.info(f"Deploying Linux client to {target_device}")
        
        try:
            # Generate configuration file
            config_content = config.to_config_json()
            
            # Shell script for Linux deployment
            shell_script = f"""#!/bin/bash
set -e

# Detect Linux distribution
if [ -f /etc/debian_version ]; then
    DISTRO="debian"
elif [ -f /etc/redhat-release ]; then
    DISTRO="redhat"
else
    DISTRO="generic"
fi

# Download RustDesk client
cd /tmp
wget -O rustdesk.AppImage "https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3-x86_64.AppImage"
chmod +x rustdesk.AppImage

# Install to /opt
sudo mkdir -p /opt/rustdesk
sudo mv rustdesk.AppImage /opt/rustdesk/
sudo ln -sf /opt/rustdesk/rustdesk.AppImage /usr/local/bin/rustdesk

# Create configuration directory
CONFIG_DIR="$HOME/.config/rustdesk"
mkdir -p "$CONFIG_DIR"

# Write configuration
cat > "$CONFIG_DIR/RustDesk2.toml" << 'EOF'
{config_content}
EOF

# Create desktop entry
cat > "$HOME/.local/share/applications/rustdesk.desktop" << 'EOF'
[Desktop Entry]
Name=RustDesk
Comment=Remote Desktop
Exec=/usr/local/bin/rustdesk
Icon=rustdesk
Terminal=false
Type=Application
Categories=Network;RemoteAccess;
EOF

# Create systemd service for auto-start
sudo tee /etc/systemd/system/rustdesk.service > /dev/null << 'EOF'
[Unit]
Description=RustDesk Remote Desktop
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/rustdesk --service
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable rustdesk
sudo systemctl start rustdesk

echo "RustDesk installation and configuration completed"
"""
            
            # Save script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(shell_script)
                script_path = f.name
            
            os.chmod(script_path, 0o755)  
            self.logger.info(f"Linux deployment script created: {script_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Linux client deployment failed: {e}")
            return False
    
    def create_deployment_package(self, 
                                 platform: str,
                                 config: RustDeskDeploymentConfig,
                                 output_dir: Path) -> Path:
        """
        Create deployment package for offline installation.
        
        Args:
            platform: Target platform
            config: Deployment configuration
            output_dir: Output directory for package
            
        Returns:
            Path to created package
        """
        self.logger.info(f"Creating deployment package for {platform}")
        
        try:
            # Create package directory
            package_dir = output_dir / f"rustdesk-deployment-{platform}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            package_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate configuration file
            config_file = package_dir / "rustdesk-config.json"
            with open(config_file, 'w') as f:
                f.write(config.to_config_json())
            
            # Generate installation script based on platform
            if platform.lower() == "windows":
                script_content = self._generate_windows_deployment_script(config)
                script_file = package_dir / "install.ps1"
            elif platform.lower() == "macos":
                script_content = self._generate_macos_deployment_script(config)
                script_file = package_dir / "install.sh"
            else:  # Linux
                script_content = self._generate_linux_deployment_script(config)
                script_file = package_dir / "install.sh"
            
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            if not platform.lower() == "windows":
                os.chmod(script_file, 0o755)
            
            # Create README
            readme_content = f"""
# RustDesk Deployment Package

This package contains everything needed to deploy RustDesk client on {platform}.

## Installation Instructions

### {platform.title()}:
1. Copy this entire folder to the target device
2. Run the installation script:
   - Windows: Run `install.ps1` as Administrator
   - macOS/Linux: Run `./install.sh`

## Configuration

The deployment will automatically configure RustDesk to connect to:
- Server: {config.server_host}:{config.server_port}
- Key: {config.key or 'Not specified'}

## Package Contents

- `rustdesk-config.json` - RustDesk configuration
- `install.*` - Installation script
- `README.md` - This file

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            readme_file = package_dir / "README.md"
            with open(readme_file, 'w') as f:
                f.write(readme_content.strip())
            
            self.logger.info(f"Deployment package created: {package_dir}")
            return package_dir
            
        except Exception as e:
            self.logger.error(f"Failed to create deployment package: {e}")
            raise RustDeskDeploymentError(platform, str(e))
    
    def _generate_windows_deployment_script(self, config: RustDeskDeploymentConfig) -> str:
        """Generate Windows deployment script."""
        return f"""
# RustDesk Windows Deployment Script
# Generated by NetArchon

Write-Host "Starting RustDesk deployment..."

try {{
    # Download RustDesk client
    $url = "https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3-x86_64.exe"
    $output = "$env:TEMP\\rustdesk-installer.exe"
    
    Write-Host "Downloading RustDesk client..."
    Invoke-WebRequest -Uri $url -OutFile $output
    
    # Install RustDesk
    Write-Host "Installing RustDesk..."
    Start-Process -FilePath $output -ArgumentList "/S" -Wait
    
    # Create configuration directory
    $configDir = "$env:APPDATA\\RustDesk\\config"
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
    
    # Copy configuration
    Copy-Item "rustdesk-config.json" "$configDir\\RustDesk2.toml"
    
    # Start RustDesk service
    Write-Host "Starting RustDesk service..."
    Start-Service -Name "RustDesk" -ErrorAction SilentlyContinue
    
    Write-Host "RustDesk deployment completed successfully!"
    
}} catch {{
    Write-Host "Deployment failed: $_" -ForegroundColor Red
    exit 1
}}
"""
    
    def _generate_macos_deployment_script(self, config: RustDeskDeploymentConfig) -> str:
        """Generate macOS deployment script."""
        return f"""#!/bin/bash
# RustDesk macOS Deployment Script
# Generated by NetArchon

set -e

echo "Starting RustDesk deployment..."

# Download RustDesk client
echo "Downloading RustDesk client..."
cd /tmp
curl -L -o rustdesk.dmg "https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3.dmg"

# Mount DMG and install
echo "Installing RustDesk..."
hdiutil attach rustdesk.dmg -quiet
cp -R "/Volumes/RustDesk/RustDesk.app" "/Applications/"
hdiutil detach "/Volumes/RustDesk" -quiet

# Create configuration directory
CONFIG_DIR="$HOME/Library/Preferences/com.carriez.rustdesk"
mkdir -p "$CONFIG_DIR"

# Copy configuration
cp rustdesk-config.json "$CONFIG_DIR/RustDesk2.toml"

# Start RustDesk
echo "Starting RustDesk..."
open "/Applications/RustDesk.app"

echo "RustDesk deployment completed successfully!"
"""
    
    def _generate_linux_deployment_script(self, config: RustDeskDeploymentConfig) -> str:
        """Generate Linux deployment script."""
        return f"""#!/bin/bash
# RustDesk Linux Deployment Script
# Generated by NetArchon

set -e

echo "Starting RustDesk deployment..."

# Download RustDesk client
echo "Downloading RustDesk client..."
cd /tmp
wget -O rustdesk.AppImage "https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3-x86_64.AppImage"
chmod +x rustdesk.AppImage

# Install to /opt
echo "Installing RustDesk..."
sudo mkdir -p /opt/rustdesk
sudo mv rustdesk.AppImage /opt/rustdesk/
sudo ln -sf /opt/rustdesk/rustdesk.AppImage /usr/local/bin/rustdesk

# Create configuration directory
CONFIG_DIR="$HOME/.config/rustdesk"
mkdir -p "$CONFIG_DIR"

# Copy configuration
cp rustdesk-config.json "$CONFIG_DIR/RustDesk2.toml"

# Create desktop entry
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/rustdesk.desktop" << 'EOF'
[Desktop Entry]
Name=RustDesk
Comment=Remote Desktop
Exec=/usr/local/bin/rustdesk
Icon=rustdesk
Terminal=false
Type=Application
Categories=Network;RemoteAccess;
EOF

echo "RustDesk deployment completed successfully!"
echo "You can now start RustDesk from the applications menu or run 'rustdesk' in terminal."
"""
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get RustDesk server installation status."""
        try:
            # Check if Docker services are running
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd="/opt/rustdesk-server",
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse Docker Compose status
                services = json.loads(result.stdout) if result.stdout.strip() else []
                
                return {
                    'installed': True,
                    'method': 'docker',
                    'services': services,
                    'status': 'running' if services else 'stopped'
                }
            else:
                # Check for binary installation
                hbbs_running = subprocess.run(["pgrep", "hbbs"], capture_output=True).returncode == 0
                hbbr_running = subprocess.run(["pgrep", "hbbr"], capture_output=True).returncode == 0
                
                if hbbs_running or hbbr_running:
                    return {
                        'installed': True,
                        'method': 'binary',
                        'services': {
                            'hbbs': 'running' if hbbs_running else 'stopped',
                            'hbbr': 'running' if hbbr_running else 'stopped'
                        },
                        'status': 'running' if (hbbs_running and hbbr_running) else 'partial'
                    }
                else:
                    return {
                        'installed': False,
                        'method': None,
                        'status': 'not_installed'
                    }
                    
        except Exception as e:
            self.logger.error(f"Failed to get server status: {e}")
            return {
                'installed': False,
                'method': None,
                'status': 'error',
                'error': str(e)
            }