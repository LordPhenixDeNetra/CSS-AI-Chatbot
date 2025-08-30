# Guide du Système de Monitoring AI CSS Backend

## Vue d'ensemble

Ce guide décrit le système de monitoring complet implémenté pour l'API AI CSS Backend. Le système comprend :

- **Collecte de métriques** : Métriques système, API, RAG et métier
- **Health checks** : Surveillance de l'état des composants
- **Alertes intelligentes** : Système d'alertes basé sur des seuils configurables
- **Dashboard temps réel** : Interface web pour visualiser les métriques
- **Middlewares automatiques** : Collecte transparente des métriques

## Architecture du Monitoring

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Middlewares   │───►│  Collecteur de  │───►│   Système       │
│   Métriques     │    │   Métriques     │    │   d'Alertes     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Health Check  │    │   Dashboard     │    │   Notifications │
│   Service       │    │   Temps Réel    │    │   (Email/Webhook)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Endpoints de Monitoring

### Health Checks

#### `/health` - Health Check Rapide
```bash
curl http://localhost:8000/health
```

Réponse :
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600.5
}
```

#### `/health/detailed` - Health Check Complet
```bash
curl http://localhost:8000/health/detailed
```

Réponse :
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600.5,
  "components": {
    "system": {
      "status": "healthy",
      "cpu_percent": 45.2,
      "memory_percent": 62.1,
      "disk_percent": 78.5
    },
    "redis": {
      "status": "healthy",
      "connected": true,
      "response_time_ms": 2.3
    },
    "ai_models": {
      "status": "healthy",
      "loaded_models": ["clip", "blip", "text_embedding"]
    }
  }
}
```

### Métriques

#### `/metrics` - Métriques JSON
```bash
curl http://localhost:8000/metrics
```

#### `/metrics/prometheus` - Export Prometheus
```bash
curl http://localhost:8000/metrics/prometheus
```

#### `/metrics/history/{metric_name}` - Historique d'une métrique
```bash
curl http://localhost:8000/metrics/history/api.response_time
```

### Alertes

#### `/alerts` - Alertes actives
```bash
curl http://localhost:8000/alerts
```

Réponse :
```json
{
  "active_alerts": [
    {
      "id": "high_cpu_usage_1642248600",
      "rule_name": "high_cpu_usage",
      "severity": "high",
      "message": "Utilisation CPU élevée. Valeur actuelle: 85.2, Seuil: 80.0",
      "triggered_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total_active": 1
}
```

### Dashboard

#### `/dashboard` - Interface Web
Accédez au dashboard via votre navigateur :
```
http://localhost:8000/dashboard
```

Le dashboard affiche :
- Métriques système en temps réel
- Graphiques des performances API
- Alertes actives
- Statistiques RAG et cache

## Configuration des Alertes

### Règles d'Alerte par Défaut

| Règle | Métrique | Condition | Seuil | Sévérité |
|-------|----------|-----------|-------|----------|
| `high_cpu_usage` | `system.cpu_percent` | `>` | 80% | HIGH |
| `high_memory_usage` | `system.memory_percent` | `>` | 85% | HIGH |
| `low_disk_space` | `system.disk_percent` | `>` | 90% | CRITICAL |
| `high_api_error_rate` | `api.error_rate` | `>` | 5% | HIGH |
| `slow_api_response` | `api.avg_response_time` | `>` | 2000ms | MEDIUM |
| `redis_connection_failed` | `cache.redis_available` | `==` | 0 | CRITICAL |
| `low_cache_hit_rate` | `cache.hit_rate` | `<` | 70% | MEDIUM |

### Personnalisation des Alertes

Pour ajouter une nouvelle règle d'alerte :

```python
from app.core.alert_system import alert_system, AlertRule, AlertSeverity

# Créer une nouvelle règle
rule = AlertRule(
    name="custom_metric_alert",
    description="Alerte personnalisée",
    metric_name="custom.metric",
    condition=">",
    threshold=100.0,
    severity=AlertSeverity.MEDIUM,
    duration=300,  # 5 minutes
    cooldown=900,  # 15 minutes
    tags={"component": "custom", "type": "business"}
)

# Ajouter la règle
alert_system.add_rule(rule)
```

### Canaux de Notification

#### Email
```python
from app.core.alert_system import EmailAlertChannel

email_channel = EmailAlertChannel(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="alerts@yourcompany.com",
    password="your_password",
    recipients=["admin@yourcompany.com", "devops@yourcompany.com"]
)

alert_system.add_channel(email_channel)
```

#### Webhook (Slack, Discord, etc.)
```python
from app.core.alert_system import WebhookAlertChannel

slack_channel = WebhookAlertChannel(
    webhook_url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    headers={"Content-Type": "application/json"}
)

alert_system.add_channel(slack_channel)
```

## Métriques Collectées

### Métriques Système
- `system.cpu_percent` : Utilisation CPU (%)
- `system.memory_percent` : Utilisation mémoire (%)
- `system.disk_percent` : Utilisation disque (%)
- `system.load_average` : Charge système
- `system.network_io` : I/O réseau

### Métriques API
- `api.total_requests` : Nombre total de requêtes
- `api.response_time` : Temps de réponse (ms)
- `api.error_count` : Nombre d'erreurs
- `api.error_rate` : Taux d'erreur (%)
- `api.requests_per_second` : Requêtes par seconde
- `api.slow_requests` : Requêtes lentes (>2s)

### Métriques RAG
- `rag.queries_total` : Nombre total de requêtes RAG
- `rag.embedding_time` : Temps de génération d'embeddings
- `rag.search_time` : Temps de recherche
- `rag.rerank_time` : Temps de re-ranking
- `rag.llm_time` : Temps de génération LLM
- `rag.total_time` : Temps total RAG

### Métriques Cache
- `cache.hits` : Nombre de hits cache
- `cache.misses` : Nombre de miss cache
- `cache.hit_rate` : Taux de hit (%)
- `cache.redis_available` : Disponibilité Redis (0/1)
- `cache.memory_usage` : Utilisation mémoire cache

### Métriques Métier
- `business.predefined_qa_queries` : Requêtes Q&A prédéfinies
- `business.rag_queries` : Requêtes RAG
- `business.cache_operations` : Opérations cache
- `business.user_interactions` : Interactions utilisateur

## Intégration avec Prometheus

Pour intégrer avec Prometheus, ajoutez cette configuration à votre `prometheus.yml` :

```yaml
scrape_configs:
  - job_name: 'ai-css-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 30s
```

## Intégration avec Grafana

### Dashboard Grafana

1. Importez les métriques depuis Prometheus
2. Créez des graphiques pour :
   - Utilisation des ressources système
   - Performances API (temps de réponse, taux d'erreur)
   - Métriques RAG (temps de traitement)
   - Statistiques cache

### Exemples de Requêtes PromQL

```promql
# Utilisation CPU moyenne sur 5 minutes
rate(system_cpu_percent[5m])

# Temps de réponse API P95
histogram_quantile(0.95, rate(api_response_time_bucket[5m]))

# Taux d'erreur API
rate(api_error_count[5m]) / rate(api_total_requests[5m]) * 100

# Taux de hit cache
rate(cache_hits[5m]) / (rate(cache_hits[5m]) + rate(cache_misses[5m])) * 100
```

## Démarrage du Système de Monitoring

Le système de monitoring se démarre automatiquement avec l'application. Pour un contrôle manuel :

```python
from app.core.alert_system import alert_system
import asyncio

# Démarrer le monitoring des alertes
asyncio.create_task(alert_system.start_monitoring(check_interval=60))
```

## Bonnes Pratiques

### 1. Configuration des Seuils
- Ajustez les seuils selon votre environnement
- Utilisez des seuils différents pour dev/staging/prod
- Surveillez les faux positifs et ajustez

### 2. Gestion des Alertes
- Configurez des canaux appropriés (email, Slack, PagerDuty)
- Implémentez une escalade pour les alertes critiques
- Documentez les procédures de résolution

### 3. Performance
- Le monitoring ajoute une surcharge minimale (<1ms par requête)
- Les métriques sont collectées de manière asynchrone
- L'historique est limité pour éviter la consommation mémoire

### 4. Sécurité
- Protégez les endpoints de monitoring si nécessaire
- Chiffrez les communications webhook
- Utilisez des credentials sécurisés pour les notifications

## Dépannage

### Problèmes Courants

#### Les métriques ne s'affichent pas
1. Vérifiez que les middlewares sont bien ajoutés
2. Contrôlez les logs pour les erreurs
3. Testez les endpoints manuellement

#### Les alertes ne se déclenchent pas
1. Vérifiez la configuration des règles
2. Contrôlez les seuils et conditions
3. Vérifiez les logs du système d'alertes

#### Dashboard inaccessible
1. Vérifiez que le routeur dashboard est inclus
2. Contrôlez les permissions et CORS
3. Vérifiez les logs du serveur web

### Logs de Debug

Pour activer les logs de debug du monitoring :

```python
import logging
logging.getLogger('app.core.metrics').setLevel(logging.DEBUG)
logging.getLogger('app.core.alert_system').setLevel(logging.DEBUG)
```

## Support et Maintenance

- **Logs** : Consultez les logs de l'application pour les erreurs
- **Métriques** : Surveillez les métriques de performance du monitoring lui-même
- **Mise à jour** : Mettez à jour régulièrement les seuils et règles
- **Sauvegarde** : Sauvegardez la configuration des alertes

---

**Développé avec ❤️ par la CSS**