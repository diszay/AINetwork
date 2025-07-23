# NetArchon Web Development Plan

## Overview
This document outlines the comprehensive web development strategy for NetArchon following the Essential Development Workflow from CLAUDE.md. The web interface will use Streamlit for rapid development and will run locally on your mini PC with optional cloud deployment.

## 🔥 ESSENTIAL DEVELOPMENT WORKFLOW COMPLIANCE

All web development MUST follow the principles outlined in CLAUDE.md:

### 1. Simplicity Principle
- **Minimal Dependencies**: Use Streamlit for rapid UI development with minimal complexity
- **Progressive Enhancement**: Start with basic dashboard, add interactive features incrementally
- **Atomic Changes**: Each page/component implemented as a single, complete unit

### 2. Development Process
1. **Plan**: Create detailed task breakdown in `tasks/web_todo.md`
2. **Implement**: Write minimal, simple code following existing patterns
3. **Test**: Ensure functionality works in both local and Vercel environments
4. **Document**: Update `docs/activity.md` with all changes
5. **Commit**: Make atomic commits with clear messages

## 📋 IMPLEMENTATION PHASES

### Phase 1: Foundation Setup (After Core Tasks 11-18 Complete)

#### Web Infrastructure Foundation
- [ ] Create `src/netarchon/web/` directory for Streamlit application
- [ ] Set up Streamlit configuration for local deployment
- [ ] Create modular page structure following Streamlit best practices
- [ ] Implement custom CSS styling with NetArchon branding
- [ ] Configure multi-page navigation

#### Streamlit Application Structure
```
src/netarchon/web/
├── streamlit_app.py          # Main Streamlit application entry point
├── pages/
│   ├── 1_Dashboard.py        # Main overview dashboard
│   ├── 2_Devices.py          # Device management interface
│   ├── 3_Configurations.py   # Configuration management
│   ├── 4_Monitoring.py       # Real-time monitoring
│   └── 5_Settings.py         # Application settings
├── components/
│   ├── __init__.py
│   ├── device_card.py        # Device status display component
│   ├── metrics_chart.py      # Metrics visualization component
│   ├── config_manager.py     # Configuration interface component
│   └── alert_panel.py        # Alert display component
├── utils/
│   ├── __init__.py
│   ├── data_loader.py        # Data fetching utilities
│   ├── chart_helpers.py      # Chart generation helpers
│   └── session_state.py     # Session management
├── assets/
│   ├── style.css             # Custom CSS styling
│   ├── logo.png              # NetArchon logo
│   └── icons/                # UI icons
├── config/
│   ├── streamlit_config.toml # Streamlit configuration
│   └── app_config.py         # Application configuration
└── database.py               # SQLite database interface
```

### Phase 2: Core Web Components

#### Task W1: Basic Streamlit Application Framework
**Following CLAUDE.md Task Structure**
- **Phase 1**: Create main Streamlit application with multi-page setup
- **Phase 2**: Implement navigation and page routing
- **Phase 3**: Add custom CSS styling and NetArchon branding
- **Phase 4**: Create data integration layer with core NetArchon modules

**Required Implementation**:
```python
class StreamlitApp:
    def setup_pages(self) -> None
    def render_navigation(self) -> None
    def load_netarchon_data(self) -> dict
    def update_session_state(self) -> None
```

#### Task W2: Device Management Interface
- **Phase 1**: Create device listing and status display
- **Phase 2**: Implement device discovery and connection testing
- **Phase 3**: Add device configuration management
- **Phase 4**: Create device detail views with live status

#### Task W3: Configuration Management Interface
- **Phase 1**: Display configuration backup history
- **Phase 2**: Implement configuration deployment interface
- **Phase 3**: Add configuration comparison and diff views
- **Phase 4**: Create rollback interface with safety confirmations

#### Task W4: Real-time Monitoring Dashboard
- **Phase 1**: Create metrics display with Plotly charts
- **Phase 2**: Implement auto-refresh for live updates
- **Phase 3**: Add alert management interface
- **Phase 4**: Create historical data visualization with interactive filters

### Phase 3: Advanced Features

#### Task W5: Data Integration Layer
- Create direct integration with NetArchon core modules
- Implement caching for improved performance
- Add session state management for user interactions
- Create data refresh mechanisms

#### Task W6: Advanced Data Visualization
- Implement Plotly/Streamlit charts for performance metrics
- Create network topology visualization with interactive graphs
- Add metric correlation analysis
- Implement data export functionality (CSV, JSON)

#### Task W7: User Experience Enhancement
- Optimize Streamlit layout for different screen sizes
- Add sidebar navigation and collapsible sections
- Implement keyboard shortcuts and accessibility features
- Create user preferences and settings persistence

### Phase 4: Production Readiness

#### Task W8: Security Implementation
- Implement basic authentication for Streamlit
- Add secure session management
- Create secure credential storage integration
- Add audit logging for user actions

#### Task W9: Performance Optimization
- Implement Streamlit caching (@st.cache_data)
- Optimize data loading and refresh intervals
- Create efficient metric aggregation
- Add performance monitoring and metrics

#### Task W10: Mini PC Deployment
- Create systemd service for Streamlit app
- Add reverse proxy configuration (Nginx)
- Implement automatic startup and monitoring
- Create backup and maintenance scripts

## 🚀 LOCAL DEPLOYMENT ARCHITECTURE

### Mini PC Setup Requirements
```bash
# System requirements
- Python 3.9+
- Streamlit
- SQLite (development) / PostgreSQL (production)
- Nginx (reverse proxy, optional)
- Systemd (service management)

# Installation process
git clone <repository>
cd NetArchon/AINetwork
pip install -r requirements.txt
pip install streamlit plotly

# Local Streamlit server
streamlit run src/netarchon/web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0

# Production deployment with systemd
sudo systemctl enable netarchon-streamlit
sudo systemctl start netarchon-streamlit
```

### Local Development Commands
```bash
# Start development server
cd src/netarchon/web
streamlit run streamlit_app.py --server.port=8501

# Run with custom config
export STREAMLIT_CONFIG_DIR=./config
streamlit run streamlit_app.py

# Run tests
python3 -m pytest tests/web/ -v

# Access local interface
http://localhost:8501
http://mini-pc-ip:8501  # From other devices on network
```

## 🌐 STREAMLIT CLOUD DEPLOYMENT (OPTIONAL)

### Streamlit Cloud Configuration
```toml
# .streamlit/config.toml
[server]
port = 8501
enableCORS = false
enableXsrfProtection = true

[theme]
primaryColor = "#0066CC"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[browser]
gatherUsageStats = false
```

### Cloud Deployment Process (Optional)
```bash
# For Streamlit Cloud deployment
1. Push code to GitHub repository
2. Connect repository to Streamlit Cloud
3. Configure environment variables
4. Deploy automatically on git push

# For custom cloud deployment
pip install streamlit
streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0

# Access deployment
https://netarchon-web.streamlit.app  # Streamlit Cloud
https://your-domain.com:8501         # Custom deployment
```

## 🎯 INTEGRATION WITH CORE NETARCHON

### Direct Integration Pattern
```python
# src/netarchon/web/utils/data_loader.py
import streamlit as st
from src.netarchon.core.ssh_connector import SSHConnector
from src.netarchon.core.device_manager import DeviceDetector
from src.netarchon.core.config_manager import ConfigManager
from src.netarchon.core.monitoring import MonitoringCollector

@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_device_list():
    """Load and cache device list."""
    detector = DeviceDetector()
    devices = detector.get_all_devices()
    return [device.to_dict() for device in devices]

@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_device_metrics(device_id: str):
    """Load and cache device metrics."""
    collector = MonitoringCollector()
    connection = get_device_connection(device_id)
    
    # Get interface and system metrics
    interface_metrics = collector.collect_interface_metrics(connection)
    system_metrics = collector.collect_system_metrics(connection)
    
    return {
        'interfaces': [metric.__dict__ for metric in interface_metrics],
        'system': system_metrics.__dict__
    }

def backup_device_config(device_id: str):
    """Trigger configuration backup."""
    config_manager = ConfigManager()
    connection = get_device_connection(device_id)
    backup_path = config_manager.backup_config(connection)
    return {'backup_path': backup_path, 'status': 'success'}
```

### Real-time Data Flow
```
Local NetArchon Core ← → Streamlit App ← → Browser Dashboard
       ↓                      ↓                ↓
  Network Devices        SQLite Database   Auto-refresh UI
       ↓                      ↓                ↓
   SSH/SNMP              Cached Data       Interactive Charts
```

## 📊 FEATURE PRIORITY MATRIX

### High Priority (Core Functionality)
1. **Device Status Dashboard** - Real-time device connectivity and health
2. **Configuration Management** - Backup, deploy, rollback interfaces
3. **Basic Monitoring** - Interface statistics and system metrics with Plotly charts
4. **Data Integration** - Direct integration with NetArchon core modules

### Medium Priority (Enhanced UX)
1. **Advanced Monitoring** - Historical charts and trending with Plotly
2. **Alert Management** - Notification center and alert rules
3. **User Authentication** - Streamlit authentication and session management
4. **Responsive Layout** - Optimized for different screen sizes

### Low Priority (Advanced Features)
1. **Network Topology** - Visual network diagrams
2. **Bulk Operations** - Multi-device management
3. **Reporting** - PDF/Excel report generation
4. **Integrations** - Third-party system connections

## 🔧 DEVELOPMENT TOOLS & STACK

### Streamlit Development Stack
- **Framework**: Streamlit (Python-based web framework)
- **Visualization**: Plotly, Altair, Matplotlib
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Caching**: Streamlit built-in caching (@st.cache_data)
- **Testing**: pytest + Streamlit testing framework
- **Deployment**: Streamlit Cloud or custom server

### Mini PC Production Stack
- **Runtime**: Python 3.9+ with Streamlit
- **Process Management**: systemd
- **Reverse Proxy**: Nginx (optional)
- **Database**: SQLite or PostgreSQL
- **Monitoring**: Streamlit built-in metrics
- **Backup**: Automated database and config backups

## 📋 SUCCESS CRITERIA

### Mini PC Deployment Success
- [ ] Streamlit interface accessible at `http://mini-pc-ip:8501`
- [ ] All core NetArchon features available through web UI
- [ ] Real-time monitoring with auto-refresh capabilities
- [ ] Responsive layout works on tablets and desktops
- [ ] Reliable service with automatic restart capability

### Streamlit Cloud Deployment Success (Optional)
- [ ] Public web interface at streamlit.app subdomain
- [ ] Data loads within 2-3 seconds with caching
- [ ] Interactive charts and visualizations working
- [ ] Mobile-friendly responsive design
- [ ] Secure authentication and session management

## 🎯 NEXT STEPS

After completing core Tasks 11-18, web development will begin following this plan:

1. **Immediate**: Create web development todo list in `tasks/web_todo.md`
2. **Week 1**: Implement basic Streamlit application structure and navigation
3. **Week 2**: Add device management and configuration interfaces with real-time data
4. **Week 3**: Create monitoring dashboard with Plotly charts and auto-refresh
5. **Week 4**: Deploy to mini PC with systemd service and optional Streamlit Cloud

### Development Approach
- **Simplicity First**: Start with basic Streamlit pages, add complexity incrementally
- **Direct Integration**: Use NetArchon core modules directly, no API layer needed
- **Caching Strategy**: Implement @st.cache_data for performance optimization
- **Responsive Design**: Optimize for desktop and tablet viewing
- **Local Focus**: Primary deployment target is your mini PC environment

All development will strictly follow the Essential Development Workflow from CLAUDE.md with atomic commits, comprehensive testing, and detailed documentation.

## 📦 REQUIREMENTS UPDATE

Add to `requirements-web.txt`:
```
streamlit>=1.28.0
plotly>=5.15.0
altair>=5.0.0
pandas>=2.0.0
numpy>=1.24.0
```