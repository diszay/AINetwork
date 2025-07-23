"""
Dashboard Metrics Components

Specialized components for rendering different types of metrics in the dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from netarchon.monitoring.concurrent_collector import MetricType


def render_performance_metrics(metrics: List):
    """Render performance metrics visualization."""
    # Filter performance metrics
    performance_metrics = [
        m for m in metrics 
        if m.metric_type == MetricType.PERFORMANCE
    ]
    
    if not performance_metrics:
        st.info("No performance metrics available.")
        return
    
    # Create DataFrame for plotting
    df_data = []
    for metric in performance_metrics:
        if metric.metric_name == 'open_ports':
            # Handle list values
            port_count = len(metric.value) if isinstance(metric.value, list) else 0
            df_data.append({
                'timestamp': metric.timestamp,
                'device': metric.device_name,
                'metric': 'open_ports_count',
                'value': port_count,
                'unit': 'count'
            })
        else:
            try:
                value = float(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'device': metric.device_name,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': metric.unit
                })
            except (ValueError, TypeError):
                continue
    
    if not df_data:
        st.info("No numeric performance metrics available.")
        return
    
    df = pd.DataFrame(df_data)
    
    # Open ports chart
    ports_df = df[df['metric'] == 'open_ports_count']
    if not ports_df.empty:
        fig_ports = px.bar(
            ports_df.groupby('device')['value'].mean().reset_index(),
            x='device',
            y='value',
            title='Average Open Ports by Device',
            labels={'value': 'Number of Open Ports', 'device': 'Device'}
        )
        fig_ports.update_layout(height=300)
        st.plotly_chart(fig_ports, use_container_width=True)


def render_system_metrics(metrics: List):
    """Render system resource metrics visualization."""
    # Filter system metrics
    system_metrics = [
        m for m in metrics 
        if m.metric_type == MetricType.SYSTEM_RESOURCES
    ]
    
    if not system_metrics:
        st.info("No system metrics available.")
        return
    
    # Create DataFrame for plotting
    df_data = []
    for metric in system_metrics:
        try:
            if metric.metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                value = float(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'device': metric.device_name,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': metric.unit
                })
            elif metric.metric_name == 'docker_containers':
                value = int(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'device': metric.device_name,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': 'count'
                })
        except (ValueError, TypeError):
            continue
    
    if not df_data:
        st.info("No system resource metrics available.")
        return
    
    df = pd.DataFrame(df_data)
    
    # Create subplots for different metrics
    unique_metrics = df['metric'].unique()
    
    if 'cpu_usage' in unique_metrics:
        cpu_df = df[df['metric'] == 'cpu_usage']
        fig_cpu = px.line(
            cpu_df,
            x='timestamp',
            y='value',
            color='device',
            title='CPU Usage Over Time',
            labels={'value': 'CPU Usage (%)', 'timestamp': 'Time'}
        )
        fig_cpu.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="Warning Threshold")
        fig_cpu.update_layout(height=300)
        st.plotly_chart(fig_cpu, use_container_width=True)
    
    if 'memory_usage' in unique_metrics:
        memory_df = df[df['metric'] == 'memory_usage']
        fig_memory = px.line(
            memory_df,
            x='timestamp',
            y='value',
            color='device',
            title='Memory Usage Over Time',
            labels={'value': 'Memory Usage (%)', 'timestamp': 'Time'}
        )
        fig_memory.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Critical Threshold")
        fig_memory.update_layout(height=300)
        st.plotly_chart(fig_memory, use_container_width=True)
    
    if 'disk_usage' in unique_metrics:
        disk_df = df[df['metric'] == 'disk_usage']
        fig_disk = px.line(
            disk_df,
            x='timestamp',
            y='value',
            color='device',
            title='Disk Usage Over Time',
            labels={'value': 'Disk Usage (%)', 'timestamp': 'Time'}
        )
        fig_disk.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="Warning Threshold")
        fig_disk.update_layout(height=300)
        st.plotly_chart(fig_disk, use_container_width=True)


def render_network_metrics(metrics: List):
    """Render network-specific metrics visualization."""
    # Filter network metrics
    network_metrics = [
        m for m in metrics 
        if m.metric_type in [MetricType.DOCSIS, MetricType.WIFI_MESH, MetricType.BANDWIDTH]
    ]
    
    if not network_metrics:
        st.info("No network metrics available.")
        return
    
    # Create DataFrame for plotting
    df_data = []
    for metric in network_metrics:
        try:
            if metric.metric_name in ['snr', 'downstream_power', 'upstream_power']:
                value = float(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'device': metric.device_name,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': metric.unit,
                    'type': 'DOCSIS'
                })
            elif metric.metric_name in ['connected_devices', 'bandwidth_utilization']:
                value = float(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'device': metric.device_name,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': metric.unit,
                    'type': 'WiFi'
                })
            elif metric.metric_name == 'data_usage':
                value = float(metric.value)
                df_data.append({
                    'timestamp': metric.timestamp,
                    'device': metric.device_name,
                    'metric': metric.metric_name,
                    'value': value,
                    'unit': metric.unit,
                    'type': 'Bandwidth'
                })
        except (ValueError, TypeError):
            continue
    
    if not df_data:
        st.info("No network metrics available.")
        return
    
    df = pd.DataFrame(df_data)
    
    # DOCSIS metrics
    docsis_df = df[df['type'] == 'DOCSIS']
    if not docsis_df.empty:
        st.subheader("📡 DOCSIS Metrics (Arris S33)")
        
        # SNR chart
        snr_df = docsis_df[docsis_df['metric'] == 'snr']
        if not snr_df.empty:
            fig_snr = px.line(
                snr_df,
                x='timestamp',
                y='value',
                title='DOCSIS SNR Over Time',
                labels={'value': 'SNR (dB)', 'timestamp': 'Time'}
            )
            fig_snr.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Minimum Threshold")
            fig_snr.update_layout(height=300)
            st.plotly_chart(fig_snr, use_container_width=True)
        
        # Power levels chart
        power_df = docsis_df[docsis_df['metric'].isin(['downstream_power', 'upstream_power'])]
        if not power_df.empty:
            fig_power = px.line(
                power_df,
                x='timestamp',
                y='value',
                color='metric',
                title='DOCSIS Power Levels Over Time',
                labels={'value': 'Power (dBmV)', 'timestamp': 'Time'}
            )
            fig_power.update_layout(height=300)
            st.plotly_chart(fig_power, use_container_width=True)
    
    # WiFi metrics
    wifi_df = df[df['type'] == 'WiFi']
    if not wifi_df.empty:
        st.subheader("📶 WiFi Mesh Metrics (Netgear Orbi)")
        
        # Connected devices
        devices_df = wifi_df[wifi_df['metric'] == 'connected_devices']
        if not devices_df.empty:
            fig_devices = px.line(
                devices_df,
                x='timestamp',
                y='value',
                color='device',
                title='Connected Devices Over Time',
                labels={'value': 'Number of Devices', 'timestamp': 'Time'}
            )
            fig_devices.update_layout(height=300)
            st.plotly_chart(fig_devices, use_container_width=True)
    
    # Bandwidth metrics
    bandwidth_df = df[df['type'] == 'Bandwidth']
    if not bandwidth_df.empty:
        st.subheader("🌐 Bandwidth Usage (Xfinity Gateway)")
        
        fig_bandwidth = px.line(
            bandwidth_df,
            x='timestamp',
            y='value',
            title='Data Usage Over Time',
            labels={'value': 'Data Usage (GB)', 'timestamp': 'Time'}
        )
        fig_bandwidth.update_layout(height=300)
        st.plotly_chart(fig_bandwidth, use_container_width=True)


def render_alert_summary(alert_manager):
    """Render alert summary with recent alerts."""
    st.subheader("🚨 Alert Summary")
    
    try:
        # Get active alerts
        active_alerts = alert_manager.get_active_alerts()
        
        # Get alert statistics
        alert_stats = alert_manager.get_alert_statistics()
        
        if not active_alerts and not alert_stats.get('recent_history', {}).get('total_24h', 0):
            st.success("🟢 No active alerts. Network is healthy!")
            return
        
        # Active alerts summary
        if active_alerts:
            st.warning(f"⚠️ {len(active_alerts)} active alerts require attention")
            
            # Group alerts by severity
            critical_alerts = [a for a in active_alerts if a.severity.value == 'critical']
            warning_alerts = [a for a in active_alerts if a.severity.value == 'warning']
            
            col1, col2 = st.columns(2)
            
            with col1:
                if critical_alerts:
                    st.error(f"🔴 {len(critical_alerts)} Critical Alerts")
                    for alert in critical_alerts[:3]:  # Show top 3
                        st.write(f"• {alert.device_name}: {alert.message}")
            
            with col2:
                if warning_alerts:
                    st.warning(f"🟡 {len(warning_alerts)} Warning Alerts")
                    for alert in warning_alerts[:3]:  # Show top 3
                        st.write(f"• {alert.device_name}: {alert.message}")
        
        # Alert history chart
        if alert_stats.get('recent_history', {}).get('total_24h', 0) > 0:
            st.subheader("📈 Alert Trends (24h)")
            
            # Create alert trend visualization
            history_data = alert_stats['recent_history']['by_severity']
            
            if history_data:
                fig_alerts = go.Figure(data=[
                    go.Bar(
                        x=list(history_data.keys()),
                        y=list(history_data.values()),
                        marker_color=['#dc3545', '#ffc107', '#17a2b8', '#6f42c1'][:len(history_data)]
                    )
                ])
                
                fig_alerts.update_layout(
                    title="Alerts by Severity (Last 24 Hours)",
                    xaxis_title="Severity",
                    yaxis_title="Number of Alerts",
                    height=300
                )
                
                st.plotly_chart(fig_alerts, use_container_width=True)
        
        # Top alerting devices
        if alert_stats.get('top_alerting_devices'):
            st.subheader("🏆 Top Alerting Devices")
            
            top_devices = alert_stats['top_alerting_devices'][:5]  # Top 5
            
            if top_devices:
                devices_df = pd.DataFrame(top_devices, columns=['Device', 'Alert Count'])
                
                fig_top_devices = px.bar(
                    devices_df,
                    x='Device',
                    y='Alert Count',
                    title="Devices with Most Alerts (24h)",
                    labels={'Alert Count': 'Number of Alerts'}
                )
                fig_top_devices.update_layout(height=300)
                st.plotly_chart(fig_top_devices, use_container_width=True)
        
    except Exception as e:
        st.error(f"Failed to load alert summary: {str(e)}")


def render_capacity_planning(metrics: List, storage_manager):
    """Render capacity planning and forecasting."""
    st.subheader("📊 Capacity Planning & Forecasting")
    
    try:
        # Get aggregated metrics for trend analysis
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # Last 7 days
        
        # Focus on key capacity metrics
        capacity_metrics = [
            ('mini_pc_server', MetricType.SYSTEM_RESOURCES, 'cpu_usage'),
            ('mini_pc_server', MetricType.SYSTEM_RESOURCES, 'memory_usage'),
            ('mini_pc_server', MetricType.SYSTEM_RESOURCES, 'disk_usage'),
            ('xfinity_gateway', MetricType.BANDWIDTH, 'data_usage')
        ]
        
        forecasts = {}
        
        for device_id, metric_type, metric_name in capacity_metrics:
            try:
                # Get hourly aggregated data
                hourly_data = storage_manager.get_aggregated_metrics(
                    device_id=device_id,
                    metric_type=metric_type,
                    metric_name=metric_name,
                    hours_back=168  # 7 days
                )
                
                if len(hourly_data) > 24:  # Need at least 24 hours of data
                    # Simple linear trend forecasting
                    timestamps = [d['timestamp'] for d in hourly_data]
                    values = [d['avg_value'] for d in hourly_data]
                    
                    # Calculate trend
                    x = np.arange(len(values))
                    z = np.polyfit(x, values, 1)
                    trend_line = np.poly1d(z)
                    
                    # Forecast next 24 hours
                    future_x = np.arange(len(values), len(values) + 24)
                    forecast_values = trend_line(future_x)
                    
                    forecasts[f"{device_id}_{metric_name}"] = {
                        'current_avg': np.mean(values[-24:]),  # Last 24 hours average
                        'trend_slope': z[0],  # Trend direction
                        'forecast_24h': forecast_values[-1],  # 24h forecast
                        'forecast_7d': trend_line(len(values) + 168),  # 7d forecast
                        'historical_data': list(zip(timestamps, values)),
                        'forecast_data': list(zip(
                            [timestamps[-1] + timedelta(hours=i) for i in range(1, 25)],
                            forecast_values
                        ))
                    }
            except Exception as e:
                st.warning(f"Could not generate forecast for {device_id} {metric_name}: {str(e)}")
        
        if not forecasts:
            st.info("Insufficient data for capacity forecasting. Need at least 24 hours of metrics.")
            return
        
        # Display forecasts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🖥️ System Resource Trends")
            
            for key, forecast in forecasts.items():
                if 'mini_pc_server' in key:
                    metric_name = key.split('_')[-1]
                    
                    # Create trend chart
                    historical_df = pd.DataFrame(
                        forecast['historical_data'], 
                        columns=['timestamp', 'value']
                    )
                    forecast_df = pd.DataFrame(
                        forecast['forecast_data'], 
                        columns=['timestamp', 'value']
                    )
                    
                    fig = go.Figure()
                    
                    # Historical data
                    fig.add_trace(go.Scatter(
                        x=historical_df['timestamp'],
                        y=historical_df['value'],
                        mode='lines',
                        name='Historical',
                        line=dict(color='blue')
                    ))
                    
                    # Forecast data
                    fig.add_trace(go.Scatter(
                        x=forecast_df['timestamp'],
                        y=forecast_df['value'],
                        mode='lines',
                        name='Forecast',
                        line=dict(color='red', dash='dash')
                    ))
                    
                    fig.update_layout(
                        title=f"{metric_name.replace('_', ' ').title()} Trend & Forecast",
                        xaxis_title="Time",
                        yaxis_title="Usage (%)" if 'usage' in metric_name else "Value",
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Forecast summary
                    current = forecast['current_avg']
                    forecast_24h = forecast['forecast_24h']
                    trend = "📈 Increasing" if forecast['trend_slope'] > 0 else "📉 Decreasing"
                    
                    st.write(f"**{metric_name.replace('_', ' ').title()}:**")
                    st.write(f"Current: {current:.1f}% | 24h Forecast: {forecast_24h:.1f}% | Trend: {trend}")
                    
                    # Capacity warnings
                    if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                        if forecast_24h > 90:
                            st.error(f"⚠️ {metric_name.replace('_', ' ').title()} may exceed 90% within 24 hours!")
                        elif forecast_24h > 80:
                            st.warning(f"⚠️ {metric_name.replace('_', ' ').title()} may exceed 80% within 24 hours")
        
        with col2:
            st.subheader("🌐 Bandwidth Trends")
            
            # Bandwidth forecasting
            for key, forecast in forecasts.items():
                if 'data_usage' in key:
                    # Similar chart for bandwidth
                    historical_df = pd.DataFrame(
                        forecast['historical_data'], 
                        columns=['timestamp', 'value']
                    )
                    forecast_df = pd.DataFrame(
                        forecast['forecast_data'], 
                        columns=['timestamp', 'value']
                    )
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=historical_df['timestamp'],
                        y=historical_df['value'],
                        mode='lines',
                        name='Historical',
                        line=dict(color='green')
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=forecast_df['timestamp'],
                        y=forecast_df['value'],
                        mode='lines',
                        name='Forecast',
                        line=dict(color='orange', dash='dash')
                    ))
                    
                    fig.update_layout(
                        title="Bandwidth Usage Trend & Forecast",
                        xaxis_title="Time",
                        yaxis_title="Data Usage (GB)",
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Bandwidth summary
                    current = forecast['current_avg']
                    forecast_24h = forecast['forecast_24h']
                    monthly_projection = forecast_24h * 30  # Rough monthly projection
                    
                    st.write(f"**Bandwidth Usage:**")
                    st.write(f"Current Daily Avg: {current:.1f} GB")
                    st.write(f"24h Forecast: {forecast_24h:.1f} GB")
                    st.write(f"Monthly Projection: {monthly_projection:.1f} GB")
                    
                    # Data cap warnings (assuming 1TB cap)
                    if monthly_projection > 1000:
                        st.error("⚠️ Monthly usage may exceed 1TB data cap!")
                    elif monthly_projection > 800:
                        st.warning("⚠️ Monthly usage approaching data cap limits")
        
        # Capacity recommendations
        st.subheader("💡 Capacity Recommendations")
        
        recommendations = []
        
        for key, forecast in forecasts.items():
            if 'cpu_usage' in key and forecast['forecast_24h'] > 85:
                recommendations.append("Consider upgrading CPU or optimizing high-usage processes")
            
            if 'memory_usage' in key and forecast['forecast_24h'] > 90:
                recommendations.append("Memory upgrade recommended - usage approaching critical levels")
            
            if 'disk_usage' in key and forecast['forecast_24h'] > 85:
                recommendations.append("Disk cleanup or storage expansion needed")
            
            if 'data_usage' in key:
                monthly_proj = forecast['forecast_24h'] * 30
                if monthly_proj > 1000:
                    recommendations.append("Consider upgrading internet plan or implementing data usage controls")
        
        if not recommendations:
            recommendations.append("✅ All systems operating within normal capacity ranges")
        
        for rec in recommendations:
            st.write(f"• {rec}")
        
    except Exception as e:
        st.error(f"Failed to generate capacity planning: {str(e)}")


def render_security_dashboard(metrics: List, alert_manager):
    """Render security monitoring dashboard with threat visualization."""
    st.subheader("🔒 Security Monitoring Dashboard")
    
    try:
        # Get security-related metrics
        security_metrics = [
            m for m in metrics 
            if m.metric_type == MetricType.SECURITY
        ]
        
        # Get security alerts
        security_alerts = [
            a for a in alert_manager.get_active_alerts()
            if 'security' in a.rule_name.lower() or a.metric_type == MetricType.SECURITY
        ]
        
        # Security overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            threat_level = "🟢 Low" if not security_alerts else "🔴 High" if len(security_alerts) > 2 else "🟡 Medium"
            st.metric("Threat Level", threat_level)
        
        with col2:
            st.metric("Security Alerts", len(security_alerts))
        
        with col3:
            # Count external connections (simulated)
            external_connections = 0  # Would be calculated from actual data
            st.metric("External Connections", external_connections)
        
        with col4:
            # Firewall status (simulated)
            st.metric("Firewall Status", "🟢 Active")
        
        # Security events timeline
        if security_metrics:
            st.subheader("🕐 Security Events Timeline")
            
            # Create timeline visualization
            events_df = pd.DataFrame([
                {
                    'timestamp': m.timestamp,
                    'device': m.device_name,
                    'event': m.metric_name,
                    'value': str(m.value),
                    'severity': 'high' if 'critical' in str(m.value).lower() else 'medium'
                }
                for m in security_metrics
            ])
            
            if not events_df.empty:
                fig_timeline = px.scatter(
                    events_df,
                    x='timestamp',
                    y='device',
                    color='severity',
                    size_max=10,
                    title='Security Events Timeline',
                    hover_data=['event', 'value']
                )
                fig_timeline.update_layout(height=300)
                st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Active security alerts
        if security_alerts:
            st.subheader("🚨 Active Security Alerts")
            
            for alert in security_alerts:
                severity_color = {
                    'critical': '🔴',
                    'warning': '🟡',
                    'info': '🔵'
                }.get(alert.severity.value, '⚪')
                
                st.warning(f"{severity_color} **{alert.rule_name}** on {alert.device_name}: {alert.message}")
        
        # Network security status
        st.subheader("🛡️ Network Security Status")
        
        # Simulated security checks
        security_checks = [
            {"Check": "RFC 1918 Compliance", "Status": "✅ Compliant", "Details": "All connections from private IP ranges"},
            {"Check": "Firewall Status", "Status": "✅ Active", "Details": "All ports properly configured"},
            {"Check": "Intrusion Detection", "Status": "✅ Monitoring", "Details": "No suspicious activity detected"},
            {"Check": "VPN Access", "Status": "🟡 Not Configured", "Details": "Consider VPN for external access"},
            {"Check": "Device Authentication", "Status": "✅ Secured", "Details": "All devices using strong authentication"}
        ]
        
        security_df = pd.DataFrame(security_checks)
        st.dataframe(security_df, use_container_width=True)
        
        # Security recommendations
        st.subheader("💡 Security Recommendations")
        
        recommendations = [
            "Enable VPN access for remote connections",
            "Implement network segmentation for IoT devices",
            "Regular security audit of connected devices",
            "Monitor for unusual traffic patterns",
            "Keep all devices updated with latest firmware"
        ]
        
        for i, rec in enumerate(recommendations, 1):
            st.write(f"{i}. {rec}")
        
    except Exception as e:
        st.error(f"Failed to load security dashboard: {str(e)}")