from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Optional, List
import json
from datetime import datetime, timedelta
import logging
from app.core.metrics import metrics_collector
from app.core.health_check import health_checker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Monitoring Dashboard"])

# @router.get("/", response_class=HTMLResponse, summary="Dashboard de monitoring")
async def monitoring_dashboard():
    """Interface web du dashboard de monitoring"""
    html_content = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI CSS Backend - Monitoring Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                background: rgba(255, 255, 255, 0.95);
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
            }
            
            .header h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            
            .header p {
                text-align: center;
                color: #7f8c8d;
                font-size: 1.1em;
            }
            
            .status-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(255, 255, 255, 0.9);
                padding: 15px 25px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }
            
            .status-item {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            
            .status-healthy { background-color: #27ae60; }
            .status-warning { background-color: #f39c12; }
            .status-critical { background-color: #e74c3c; }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
            
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 25px;
                margin-bottom: 30px;
            }
            
            .card {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
            }
            
            .card h3 {
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.3em;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }
            
            .metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            
            .metric-label {
                font-weight: 500;
                color: #555;
            }
            
            .metric-value {
                font-weight: bold;
                font-size: 1.1em;
            }
            
            .metric-value.good { color: #27ae60; }
            .metric-value.warning { color: #f39c12; }
            .metric-value.critical { color: #e74c3c; }
            
            .chart-container {
                position: relative;
                height: 300px;
                margin-top: 20px;
            }
            
            .alerts-container {
                max-height: 400px;
                overflow-y: auto;
            }
            
            .alert {
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 8px;
                border-left: 4px solid;
            }
            
            .alert.critical {
                background-color: #fdf2f2;
                border-color: #e74c3c;
                color: #c0392b;
            }
            
            .alert.warning {
                background-color: #fef9e7;
                border-color: #f39c12;
                color: #d68910;
            }
            
            .refresh-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 50%;
                width: 60px;
                height: 60px;
                font-size: 20px;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
                transition: all 0.3s ease;
            }
            
            .refresh-btn:hover {
                background: #2980b9;
                transform: scale(1.1);
            }
            
            .loading {
                text-align: center;
                padding: 20px;
                color: #7f8c8d;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 AI CSS Backend</h1>
                <p>Monitoring Dashboard - Surveillance en temps réel</p>
            </div>
            
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-indicator status-healthy" id="api-status"></div>
                    <span>API Status</span>
                </div>
                <div class="status-item">
                    <div class="status-indicator status-healthy" id="redis-status"></div>
                    <span>Redis</span>
                </div>
                <div class="status-item">
                    <div class="status-indicator status-healthy" id="rag-status"></div>
                    <span>RAG System</span>
                </div>
                <div class="status-item">
                    <span id="last-update">Dernière mise à jour: --:--</span>
                </div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>📊 Métriques Système</h3>
                    <div id="system-metrics">
                        <div class="loading">Chargement...</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🌐 Métriques API</h3>
                    <div id="api-metrics">
                        <div class="loading">Chargement...</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🧠 Métriques RAG</h3>
                    <div id="rag-metrics">
                        <div class="loading">Chargement...</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>💾 Cache Redis</h3>
                    <div id="cache-metrics">
                        <div class="loading">Chargement...</div>
                    </div>
                </div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>📈 Temps de Réponse</h3>
                    <div class="chart-container">
                        <canvas id="response-time-chart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🚨 Alertes Actives</h3>
                    <div class="alerts-container" id="alerts-container">
                        <div class="loading">Chargement...</div>
                    </div>
                </div>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="refreshData()" title="Actualiser">
            🔄
        </button>
        
        <script>
            let responseTimeChart;
            
            function formatBytes(bytes) {
                if (bytes === 0) return '0 B';
                const k = 1024;
                const sizes = ['B', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
            
            function getMetricClass(value, thresholds) {
                if (value >= thresholds.critical) return 'critical';
                if (value >= thresholds.warning) return 'warning';
                return 'good';
            }
            
            function updateSystemMetrics(data) {
                const container = document.getElementById('system-metrics');
                const system = data.system || {};
                
                container.innerHTML = `
                    <div class="metric">
                        <span class="metric-label">CPU Usage</span>
                        <span class="metric-value ${getMetricClass(system.cpu_percent || 0, {warning: 70, critical: 90})}">
                            ${(system.cpu_percent || 0).toFixed(1)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Memory Usage</span>
                        <span class="metric-value ${getMetricClass(system.memory_percent || 0, {warning: 80, critical: 90})}">
                            ${(system.memory_percent || 0).toFixed(1)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Memory Used</span>
                        <span class="metric-value">${system.memory_used_gb || 0} GB</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Disk Usage</span>
                        <span class="metric-value ${getMetricClass(system.disk_percent || 0, {warning: 85, critical: 95})}">
                            ${(system.disk_percent || 0).toFixed(1)}%
                        </span>
                    </div>
                `;
            }
            
            function updateApiMetrics(data) {
                const container = document.getElementById('api-metrics');
                const metrics = data.metrics_collector || {};
                const apiMetrics = metrics.api_metrics || {};
                
                container.innerHTML = `
                    <div class="metric">
                        <span class="metric-label">Total Requests</span>
                        <span class="metric-value good">${apiMetrics.total_requests || 0}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Avg Response Time</span>
                        <span class="metric-value ${getMetricClass(apiMetrics.avg_response_time || 0, {warning: 2, critical: 5})}">
                            ${(apiMetrics.avg_response_time || 0).toFixed(2)}s
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Error Rate</span>
                        <span class="metric-value ${getMetricClass(apiMetrics.error_rate || 0, {warning: 5, critical: 10})}">
                            ${(apiMetrics.error_rate || 0).toFixed(2)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Active Connections</span>
                        <span class="metric-value good">${apiMetrics.active_connections || 0}</span>
                    </div>
                `;
            }
            
            function updateRagMetrics(data) {
                const container = document.getElementById('rag-metrics');
                const rag = data.rag || {};
                
                container.innerHTML = `
                    <div class="metric">
                        <span class="metric-label">Total Documents</span>
                        <span class="metric-value good">${rag.total_documents || 0}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Embedding Model</span>
                        <span class="metric-value ${rag.embedding_model_loaded ? 'good' : 'critical'}">
                            ${rag.embedding_model_loaded ? '✅ Loaded' : '❌ Not Loaded'}
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Reranker</span>
                        <span class="metric-value ${rag.reranker_loaded ? 'good' : 'warning'}">
                            ${rag.reranker_loaded ? '✅ Loaded' : '⚠️ Not Loaded'}
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">System Status</span>
                        <span class="metric-value ${data.api.multimodal_system_loaded ? 'good' : 'critical'}">
                            ${data.api.multimodal_system_loaded ? '🟢 Online' : '🔴 Offline'}
                        </span>
                    </div>
                `;
            }
            
            function updateCacheMetrics(data) {
                const container = document.getElementById('cache-metrics');
                const cache = data.cache || {};
                
                if (cache.error) {
                    container.innerHTML = `
                        <div class="metric">
                            <span class="metric-label">Status</span>
                            <span class="metric-value critical">❌ Error</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Error</span>
                            <span class="metric-value critical">${cache.error}</span>
                        </div>
                    `;
                } else {
                    const hitRate = cache.keyspace_hits && cache.keyspace_misses ? 
                        (cache.keyspace_hits / (cache.keyspace_hits + cache.keyspace_misses) * 100) : 0;
                    
                    container.innerHTML = `
                        <div class="metric">
                            <span class="metric-label">Connected Clients</span>
                            <span class="metric-value good">${cache.connected_clients || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Memory Used</span>
                            <span class="metric-value good">${cache.used_memory_human || '0B'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Hit Rate</span>
                            <span class="metric-value ${getMetricClass(100 - hitRate, {warning: 20, critical: 50})}">
                                ${hitRate.toFixed(1)}%
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Total Hits</span>
                            <span class="metric-value good">${cache.keyspace_hits || 0}</span>
                        </div>
                    `;
                }
            }
            
            function updateAlerts(alerts) {
                const container = document.getElementById('alerts-container');
                
                if (!alerts || alerts.length === 0) {
                    container.innerHTML = '<div class="loading">✅ Aucune alerte active</div>';
                    return;
                }
                
                container.innerHTML = alerts.map(alert => `
                    <div class="alert ${alert.level}">
                        <strong>${alert.level.toUpperCase()}</strong> - ${alert.component}<br>
                        ${alert.message}<br>
                        <small>${new Date(alert.timestamp).toLocaleString()}</small>
                    </div>
                `).join('');
            }
            
            function initResponseTimeChart() {
                const ctx = document.getElementById('response-time-chart').getContext('2d');
                responseTimeChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Temps de réponse (ms)',
                            data: [],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Temps (ms)'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Temps'
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        }
                    }
                });
            }
            
            function updateResponseTimeChart(responseTime) {
                const now = new Date().toLocaleTimeString();
                const data = responseTimeChart.data;
                
                data.labels.push(now);
                data.datasets[0].data.push(responseTime * 1000); // Convert to ms
                
                // Keep only last 20 points
                if (data.labels.length > 20) {
                    data.labels.shift();
                    data.datasets[0].data.shift();
                }
                
                responseTimeChart.update('none');
            }
            
            async function fetchData() {
                try {
                    const [metricsResponse, alertsResponse] = await Promise.all([
                        fetch('/performance-metrics'),
                        fetch('/alerts')
                    ]);
                    
                    const metricsData = await metricsResponse.json();
                    const alertsData = await alertsResponse.json();
                    
                    return { metrics: metricsData, alerts: alertsData };
                } catch (error) {
                    console.error('Erreur lors de la récupération des données:', error);
                    return null;
                }
            }
            
            async function refreshData() {
                const data = await fetchData();
                if (!data) return;
                
                const { metrics, alerts } = data;
                
                // Update metrics
                updateSystemMetrics(metrics);
                updateApiMetrics(metrics);
                updateRagMetrics(metrics);
                updateCacheMetrics(metrics);
                
                // Update alerts
                updateAlerts(alerts.alerts);
                
                // Update status indicators
                document.getElementById('api-status').className = 
                    `status-indicator ${alerts.critical_count > 0 ? 'status-critical' : alerts.warning_count > 0 ? 'status-warning' : 'status-healthy'}`;
                
                document.getElementById('redis-status').className = 
                    `status-indicator ${metrics.api.redis_available ? 'status-healthy' : 'status-critical'}`;
                
                document.getElementById('rag-status').className = 
                    `status-indicator ${metrics.api.multimodal_system_loaded ? 'status-healthy' : 'status-critical'}`;
                
                // Update chart
                const avgResponseTime = metrics.metrics_collector?.api_metrics?.avg_response_time || 0;
                updateResponseTimeChart(avgResponseTime);
                
                // Update timestamp
                document.getElementById('last-update').textContent = 
                    `Dernière mise à jour: ${new Date().toLocaleTimeString()}`;
            }
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {
                initResponseTimeChart();
                refreshData();
                
                // Auto-refresh every 30 seconds
                setInterval(refreshData, 30000);
            });
        </script>
    </body>
    </html>
    """
    return html_content

@router.get("/api/metrics", summary="API des métriques pour le dashboard")
async def get_dashboard_metrics():
    """Endpoint API pour récupérer les métriques formatées pour le dashboard"""
    try:
        # Récupérer les métriques de performance
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Métriques du collecteur
        metrics_summary = metrics_collector.get_metrics_summary()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2)
            },
            "metrics_collector": metrics_summary,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Erreur récupération métriques dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/alerts", summary="API des alertes pour le dashboard")
async def get_dashboard_alerts():
    """Endpoint API pour récupérer les alertes formatées pour le dashboard"""
    try:
        alerts = []
        
        # Vérification des seuils
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        if cpu_percent > 80:
            alerts.append({
                "level": "warning" if cpu_percent < 90 else "critical",
                "component": "system",
                "message": f"CPU usage: {cpu_percent:.1f}%",
                "timestamp": datetime.now().isoformat()
            })
        
        if memory.percent > 85:
            alerts.append({
                "level": "warning" if memory.percent < 95 else "critical",
                "component": "system",
                "message": f"Memory usage: {memory.percent:.1f}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_alerts": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Erreur récupération alertes dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/health-summary", summary="Résumé de santé pour le dashboard")
async def get_health_summary():
    """Endpoint pour récupérer un résumé de santé du système"""
    try:
        health_status = await health_checker.check_system_health()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": health_status.status.value if hasattr(health_status.status, 'value') else str(health_status.status),
            "components": {
                component_name: {
                    "status": component["status"].value if hasattr(component["status"], 'value') else str(component["status"]),
                    "message": component["message"],
                    "response_time_ms": component["response_time_ms"]
                }
                for component_name, component in health_status.components.items()
            },
            "system_info": health_status.system_info
        }
    except Exception as e:
        logger.error(f"Erreur récupération résumé santé: {e}")
        raise HTTPException(status_code=500, detail=str(e))