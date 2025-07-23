# NetArchon Web Interface: Your Network Dashboard

## What is the NetArchon Web Interface?

**For Everyone:**
The NetArchon web interface is like a "control panel" for your home network that you can access from any web browser. Think of it like the dashboard in your car - it shows you important information at a glance and lets you control various features.

When you open NetArchon in your browser, you'll see:
- A real-time view of all your network devices
- Charts showing your internet speed and usage
- Alerts when something needs attention
- Easy-to-use controls for managing your network

**For Technical Users:**
The NetArchon web interface provides comprehensive real-time visualization and management capabilities for network operations. Built as a Streamlit application with direct integration to NetArchon core modules, it offers interactive dashboard components, device management interfaces, and advanced monitoring capabilities.

## Architecture Components

### 1. Backend API Server
**Technology Stack**: Flask/FastAPI + SQLAlchemy
**Location**: `src/netarchon/web/`

```
src/netarchon/web/
├── api/
│   ├── __init__.py
│   ├── devices.py          # Device management endpoints
│   ├── configurations.py   # Config management endpoints
│   ├── monitoring.py       # Metrics and monitoring endpoints
│   └── auth.py             # Authentication endpoints
├── app.py                  # Main Flask application
├── database.py             # Database configuration
└── models/
    ├── __init__.py
    ├── web_device.py       # Web-specific device models
    ├── web_metrics.py      # Web-specific metrics models
    └── web_user.py         # User authentication models
```

### 2. Frontend Dashboard
**Technology Stack**: React/Next.js for Vercel deployment, with fallback HTML5 for local
**Location**: `web/frontend/` for Vercel, `src/netarchon/web/` for local

#### Vercel Structure
```
web/
├── frontend/                  # React/Next.js app for Vercel
│   ├── pages/
│   │   ├── index.js          # Dashboard home
│   │   ├── devices.js        # Device management
│   │   ├── configs.js        # Configuration management
│   │   └── monitoring.js     # Real-time monitoring
│   ├── components/
│   │   ├── Dashboard/
│   │   ├── DeviceManager/
│   │   ├── ConfigManager/
│   │   └── MonitoringCharts/
│   ├── styles/
│   │   ├── globals.css
│   │   └── components/
│   ├── package.json
│   └── next.config.js
└── api/                      # Serverless functions
    ├── devices/
    ├── configs/
    └── monitoring/
```

#### Local Development Structure
```
src/netarchon/web/
├── static/
│   ├── css/
│   │   ├── dashboard.css
│   │   ├── devices.css
│   │   └── monitoring.css
│   ├── js/
│   │   ├── dashboard.js
│   │   ├── device-manager.js
│   │   ├── config-manager.js
│   │   └── monitoring.js
│   └── images/
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── devices.html
    ├── configurations.html
    └── monitoring.html
```

### 3. Database Layer
**Technology**: 
- **Vercel**: Serverless database (PlanetScale, Supabase, or Vercel Postgres)
- **Local**: SQLite (development) / PostgreSQL (production)

**Tables**:
- `devices` - Device inventory and status
- `configurations` - Config backups and deployment history
- `metrics` - Time-series monitoring data
- `alerts` - Alert definitions and history
- `users` - User authentication and authorization

#### Vercel Database Options
```bash
# PlanetScale (MySQL)
npm install @planetscale/database

# Supabase (PostgreSQL)
npm install @supabase/supabase-js

# Vercel Postgres
npm install @vercel/postgres
```

## Web Interface Features

### 1. Dashboard (Main View)
**Route**: `/dashboard`
**Features**:
- Network overview with device count and status
- Real-time metrics summary (CPU, memory, interface utilization)
- Recent alerts and notifications
- Quick action buttons (backup all configs, run health check)

### 2. Device Management
**Route**: `/devices`
**Features**:
- Device inventory table with search and filtering
- Device detail views with live status
- Device discovery and auto-detection
- SSH connection testing and troubleshooting

### 3. Configuration Management
**Route**: `/configurations`
**Features**:
- Configuration backup history and comparison
- Safe configuration deployment with rollback
- Configuration validation and syntax checking
- Scheduled backup management

### 4. Monitoring & Metrics
**Route**: `/monitoring`
**Features**:
- Real-time charts and graphs (CPU, memory, interfaces)
- Historical performance trends
- Custom metric dashboards
- Alert threshold configuration

### 5. Network Topology
**Route**: `/topology`
**Features**:
- Interactive network diagram
- Device relationship mapping
- Link utilization visualization
- Topology discovery and updates

## API Endpoints

### Device Management
```
GET    /api/devices                 # List all devices
POST   /api/devices                 # Add new device
GET    /api/devices/{id}            # Get device details
PUT    /api/devices/{id}            # Update device
DELETE /api/devices/{id}            # Remove device
POST   /api/devices/{id}/discover   # Detect device type
POST   /api/devices/{id}/test       # Test connectivity
```

### Configuration Management
```
GET    /api/configs                 # List all configs
POST   /api/configs/backup          # Create backup
GET    /api/configs/{id}            # Get config details
POST   /api/configs/{id}/deploy     # Deploy configuration
POST   /api/configs/{id}/rollback   # Rollback configuration
GET    /api/configs/{id}/diff       # Compare configurations
```

### Monitoring & Metrics
```
GET    /api/metrics                 # Get current metrics
GET    /api/metrics/history         # Get historical data
POST   /api/metrics/collect         # Trigger collection
GET    /api/alerts                  # List active alerts
POST   /api/alerts                  # Create alert rule
PUT    /api/alerts/{id}             # Update alert rule
```

## Real-time Features

### WebSocket Integration
**Endpoint**: `/ws/realtime`
**Data Streams**:
- Live device status updates
- Real-time metric feeds
- Alert notifications
- Configuration deployment progress

### Auto-refresh Components
- Device status indicators (every 30 seconds)
- Metric charts (every 60 seconds)  
- Alert counters (every 15 seconds)
- Connection status (every 10 seconds)

## Visualization Components

### 1. Charts and Graphs
**Library**: Chart.js or D3.js
**Types**:
- Line charts for performance trends
- Gauge charts for utilization percentages
- Bar charts for comparative metrics
- Heatmaps for network topology

### 2. Interactive Tables
**Features**:
- Sortable columns
- Search and filtering
- Pagination for large datasets
- Export to CSV/Excel

### 3. Status Indicators
**Types**:
- Traffic light indicators (red/yellow/green)
- Progress bars for operations
- Badge counters for alerts
- Connection status icons

## Local Development Setup

### 1. Development Server
```bash
# Start development server
cd src/netarchon/web
python3 app.py --dev --port 5000

# Access dashboard
http://localhost:5000
```

### 2. Database Setup
```bash
# Initialize database
python3 -c "from database import init_db; init_db()"

# Load sample data
python3 -c "from database import load_sample_data; load_sample_data()"
```

## Production Deployment

### 1. Vercel Deployment (Recommended)
**Frontend**: React/Next.js application deployed on Vercel
**Backend**: Serverless functions or separate API deployment

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "web/frontend/**",
      "use": "@vercel/static-build"
    },
    {
      "src": "web/api/**/*.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/web/api/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/web/frontend/$1"
    }
  ],
  "env": {
    "DATABASE_URL": "@database_url",
    "SECRET_KEY": "@secret_key"
  }
}
```

```bash
# Vercel deployment commands
npm install -g vercel
vercel login
vercel --prod

# Environment variables
vercel env add DATABASE_URL
vercel env add SECRET_KEY
```

### 2. Alternative: Docker Configuration
```dockerfile
# Dockerfile for web interface
FROM python:3.9-slim
WORKDIR /app
COPY requirements-web.txt .
RUN pip install -r requirements-web.txt
COPY src/ ./src/
EXPOSE 5000
CMD ["gunicorn", "src.netarchon.web.app:app"]
```

### 3. Docker Compose (For self-hosting)
```yaml
# docker-compose.yml
version: '3.8'
services:
  netarchon-web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/netarchon
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=netarchon
      - POSTGRES_USER=netarchon
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Security Considerations

### 1. Authentication
- Session-based authentication for web interface
- JWT tokens for API access
- Role-based access control (admin, operator, viewer)

### 2. API Security
- Rate limiting on all endpoints
- Input validation and sanitization
- CORS policy configuration
- HTTPS enforcement in production

### 3. Data Protection
- Encrypted credential storage
- Audit logging for all operations
- Secure configuration backup storage
- Network device credential isolation

## Integration with Core NetArchon

### 1. Core Component Integration
```python
# Example integration in web app
from src.netarchon.core.ssh_connector import SSHConnector
from src.netarchon.core.device_manager import DeviceDetector
from src.netarchon.core.config_manager import ConfigManager
from src.netarchon.core.monitoring import MonitoringCollector

# Web API uses core components directly
@app.route('/api/devices/<device_id>/backup', methods=['POST'])
def backup_device_config(device_id):
    config_manager = ConfigManager()
    connection = get_device_connection(device_id)
    backup_path = config_manager.backup_config(connection)
    return jsonify({'backup_path': backup_path})
```

### 2. Data Flow
```
Web Dashboard ↔ REST API ↔ Core NetArchon ↔ Network Devices
     ↓              ↓           ↓              ↓
WebSocket      JSON/HTTP    Python APIs    SSH/SNMP
Updates        Responses    Integration    Protocols
```

## Vercel-Specific Features

### 1. Serverless Functions
```javascript
// web/api/devices/index.js
export default async function handler(req, res) {
  if (req.method === 'GET') {
    // List all devices
    const devices = await getDevices();
    res.status(200).json(devices);
  } else if (req.method === 'POST') {
    // Add new device
    const device = await addDevice(req.body);
    res.status(201).json(device);
  }
}
```

### 2. Environment Configuration
```bash
# Vercel environment variables
VERCEL_ENV=production
DATABASE_URL=postgresql://...
NETARCHON_API_KEY=...
MONITORING_WEBHOOK_URL=...
```

### 3. Edge Functions for Real-time Data
```javascript
// web/api/monitoring/live.js
import { createClient } from '@supabase/supabase-js';

export const config = {
  runtime: 'edge',
};

export default async function handler(req) {
  const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_ANON_KEY
  );
  
  // Real-time monitoring data
  const { data } = await supabase
    .from('metrics')
    .select('*')
    .order('timestamp', { ascending: false })
    .limit(100);
    
  return Response.json(data);
}
```

### 4. Next.js Integration
```javascript
// web/frontend/next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: '/api/:path*'
      }
    ];
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
};
```

This architecture provides a comprehensive web interface optimized for both Vercel deployment and local development, while maintaining the simplicity principle and integrating seamlessly with NetArchon's core functionality.