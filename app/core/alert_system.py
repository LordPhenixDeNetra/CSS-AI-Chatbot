#!/usr/bin/env python3
"""
Système d'alertes intelligent pour le monitoring de l'API AI CSS
"""

import time
import asyncio
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
from collections import defaultdict, deque

from app.core.metrics import metrics_collector
from app.core.health_check import health_checker
from app.core.config import settings

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Niveaux de sévérité des alertes"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Statuts des alertes"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"

@dataclass
class AlertRule:
    """Règle d'alerte configurable"""
    name: str
    description: str
    metric_name: str
    condition: str  # ">", "<", ">=", "<=", "==", "!="
    threshold: float
    severity: AlertSeverity
    duration: int = 300  # Durée en secondes avant déclenchement
    cooldown: int = 900  # Période de refroidissement en secondes
    enabled: bool = True
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class Alert:
    """Alerte générée"""
    id: str
    rule_name: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

class AlertChannel:
    """Canal de notification d'alerte"""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Envoie une alerte via ce canal"""
        raise NotImplementedError

class EmailAlertChannel(AlertChannel):
    """Canal d'alerte par email"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, recipients: List[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
    
    async def send_alert(self, alert: Alert) -> bool:
        """Envoie une alerte par email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            body = f"""
            Alerte: {alert.rule_name}
            Sévérité: {alert.severity.value.upper()}
            Message: {alert.message}
            Métrique: {alert.metric_name}
            Valeur actuelle: {alert.current_value}
            Seuil: {alert.threshold}
            Déclenchée à: {alert.triggered_at}
            
            Tags: {json.dumps(alert.tags, indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False

class WebhookAlertChannel(AlertChannel):
    """Canal d'alerte par webhook"""
    
    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    async def send_alert(self, alert: Alert) -> bool:
        """Envoie une alerte via webhook"""
        try:
            import httpx
            
            payload = {
                "alert": asdict(alert),
                "timestamp": alert.triggered_at.isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=10
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Erreur envoi webhook: {e}")
            return False

class LogAlertChannel(AlertChannel):
    """Canal d'alerte par logs"""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Enregistre l'alerte dans les logs"""
        try:
            log_level = {
                AlertSeverity.LOW: logging.INFO,
                AlertSeverity.MEDIUM: logging.WARNING,
                AlertSeverity.HIGH: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL
            }.get(alert.severity, logging.WARNING)
            
            logger.log(log_level, f"ALERTE [{alert.severity.value.upper()}] {alert.rule_name}: {alert.message}")
            return True
        except Exception as e:
            logger.error(f"Erreur log alerte: {e}")
            return False

class IntelligentAlertSystem:
    """Système d'alertes intelligent avec seuils configurables"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.channels: List[AlertChannel] = []
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.rule_states: Dict[str, Dict] = defaultdict(dict)
        self.running = False
        
        # Initialisation des règles par défaut
        self._init_default_rules()
        
        # Initialisation des canaux par défaut
        self._init_default_channels()
    
    def _init_default_rules(self):
        """Initialise les règles d'alerte par défaut"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                description="Utilisation CPU élevée",
                metric_name="system.cpu_percent",
                condition=">",
                threshold=80.0,
                severity=AlertSeverity.HIGH,
                duration=300,
                tags={"component": "system", "type": "resource"}
            ),
            AlertRule(
                name="high_memory_usage",
                description="Utilisation mémoire élevée",
                metric_name="system.memory_percent",
                condition=">",
                threshold=85.0,
                severity=AlertSeverity.HIGH,
                duration=300,
                tags={"component": "system", "type": "resource"}
            ),
            AlertRule(
                name="low_disk_space",
                description="Espace disque faible",
                metric_name="system.disk_percent",
                condition=">",
                threshold=90.0,
                severity=AlertSeverity.CRITICAL,
                duration=60,
                tags={"component": "system", "type": "storage"}
            ),
            AlertRule(
                name="high_api_error_rate",
                description="Taux d'erreur API élevé",
                metric_name="api.error_rate",
                condition=">",
                threshold=5.0,
                severity=AlertSeverity.HIGH,
                duration=180,
                tags={"component": "api", "type": "error"}
            ),
            AlertRule(
                name="slow_api_response",
                description="Temps de réponse API lent",
                metric_name="api.avg_response_time",
                condition=">",
                threshold=2000.0,  # 2 secondes
                severity=AlertSeverity.MEDIUM,
                duration=300,
                tags={"component": "api", "type": "performance"}
            ),
            AlertRule(
                name="redis_connection_failed",
                description="Connexion Redis échouée",
                metric_name="cache.redis_available",
                condition="==",
                threshold=0.0,
                severity=AlertSeverity.CRITICAL,
                duration=30,
                tags={"component": "cache", "type": "connectivity"}
            ),
            AlertRule(
                name="low_cache_hit_rate",
                description="Taux de hit cache faible",
                metric_name="cache.hit_rate",
                condition="<",
                threshold=70.0,
                severity=AlertSeverity.MEDIUM,
                duration=600,
                tags={"component": "cache", "type": "performance"}
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def _init_default_channels(self):
        """Initialise les canaux d'alerte par défaut"""
        # Canal de logs par défaut
        self.channels.append(LogAlertChannel())
    
    def add_rule(self, rule: AlertRule):
        """Ajoute une règle d'alerte"""
        self.rules[rule.name] = rule
        self.rule_states[rule.name] = {
            "breach_start": None,
            "last_alert": None,
            "consecutive_breaches": 0
        }
        logger.info(f"Règle d'alerte ajoutée: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Supprime une règle d'alerte"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            del self.rule_states[rule_name]
            logger.info(f"Règle d'alerte supprimée: {rule_name}")
    
    def add_channel(self, channel: AlertChannel):
        """Ajoute un canal d'alerte"""
        self.channels.append(channel)
        logger.info(f"Canal d'alerte ajouté: {type(channel).__name__}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Évalue une condition d'alerte"""
        conditions = {
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
            "==": lambda v, t: abs(v - t) < 0.001,
            "!=": lambda v, t: abs(v - t) >= 0.001
        }
        
        return conditions.get(condition, lambda v, t: False)(value, threshold)
    
    def _should_trigger_alert(self, rule: AlertRule, current_value: float) -> bool:
        """Détermine si une alerte doit être déclenchée"""
        if not rule.enabled:
            return False
        
        state = self.rule_states[rule.name]
        now = datetime.now()
        
        # Vérifier la condition
        condition_met = self._evaluate_condition(current_value, rule.condition, rule.threshold)
        
        if condition_met:
            if state["breach_start"] is None:
                state["breach_start"] = now
                state["consecutive_breaches"] = 1
            else:
                state["consecutive_breaches"] += 1
                
                # Vérifier si la durée de violation est atteinte
                breach_duration = (now - state["breach_start"]).total_seconds()
                if breach_duration >= rule.duration:
                    # Vérifier le cooldown
                    if state["last_alert"] is None or \
                       (now - state["last_alert"]).total_seconds() >= rule.cooldown:
                        return True
        else:
            # Réinitialiser l'état si la condition n'est plus remplie
            state["breach_start"] = None
            state["consecutive_breaches"] = 0
        
        return False
    
    async def _create_and_send_alert(self, rule: AlertRule, current_value: float):
        """Crée et envoie une alerte"""
        alert_id = f"{rule.name}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            message=f"{rule.description}. Valeur actuelle: {current_value}, Seuil: {rule.threshold}",
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold=rule.threshold,
            triggered_at=datetime.now(),
            tags=rule.tags.copy()
        )
        
        # Stocker l'alerte
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Mettre à jour l'état de la règle
        self.rule_states[rule.name]["last_alert"] = alert.triggered_at
        
        # Envoyer via tous les canaux
        for channel in self.channels:
            try:
                await channel.send_alert(alert)
            except Exception as e:
                logger.error(f"Erreur envoi alerte via {type(channel).__name__}: {e}")
        
        logger.warning(f"Alerte déclenchée: {alert.rule_name} - {alert.message}")
    
    async def check_alerts(self):
        """Vérifie toutes les règles d'alerte"""
        try:
            # Récupérer les métriques actuelles
            current_metrics = metrics_collector.get_all_metrics()
            
            for rule in self.rules.values():
                if not rule.enabled:
                    continue
                
                # Récupérer la valeur de la métrique
                metric_value = self._get_metric_value(current_metrics, rule.metric_name)
                
                if metric_value is not None:
                    # Stocker l'historique
                    self.metric_history[rule.metric_name].append({
                        "timestamp": datetime.now(),
                        "value": metric_value
                    })
                    
                    # Vérifier si une alerte doit être déclenchée
                    if self._should_trigger_alert(rule, metric_value):
                        await self._create_and_send_alert(rule, metric_value)
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes: {e}")
    
    def _get_metric_value(self, metrics: Dict, metric_name: str) -> Optional[float]:
        """Récupère la valeur d'une métrique depuis les données"""
        try:
            # Navigation dans la structure de métriques
            parts = metric_name.split('.')
            value = metrics
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            
            return float(value) if value is not None else None
        except (ValueError, TypeError, KeyError):
            return None
    
    async def resolve_alert(self, alert_id: str):
        """Résout une alerte"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            del self.active_alerts[alert_id]
            logger.info(f"Alerte résolue: {alert.rule_name}")
    
    async def acknowledge_alert(self, alert_id: str):
        """Acquitte une alerte"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            logger.info(f"Alerte acquittée: {alert.rule_name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Retourne les alertes actives"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Retourne l'historique des alertes"""
        return list(self.alert_history)[-limit:]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques des alertes"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        severity_counts = defaultdict(int)
        for alert in self.alert_history:
            severity_counts[alert.severity.value] += 1
        
        rule_counts = defaultdict(int)
        for alert in self.alert_history:
            rule_counts[alert.rule_name] += 1
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "severity_distribution": dict(severity_counts),
            "alerts_by_rule": dict(rule_counts),
            "rules_count": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules.values() if rule.enabled)
        }
    
    async def start_monitoring(self, check_interval: int = 60):
        """Démarre le monitoring des alertes"""
        self.running = True
        logger.info(f"Système d'alertes démarré (intervalle: {check_interval}s)")
        
        while self.running:
            try:
                await self.check_alerts()
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring: {e}")
                await asyncio.sleep(check_interval)
    
    def stop_monitoring(self):
        """Arrête le monitoring des alertes"""
        self.running = False
        logger.info("Système d'alertes arrêté")

# Instance globale du système d'alertes
alert_system = IntelligentAlertSystem()