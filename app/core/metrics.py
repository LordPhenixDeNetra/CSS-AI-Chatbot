#!/usr/bin/env python3
"""
Service de métriques centralisé pour le monitoring de l'API AI CSS
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum
import json
import asyncio
from contextlib import asynccontextmanager

class MetricType(Enum):
    """Types de métriques disponibles"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class MetricData:
    """Structure de données pour une métrique"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metric_type: MetricType

@dataclass
class PerformanceMetrics:
    """Métriques de performance système"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime

@dataclass
class APIMetrics:
    """Métriques spécifiques à l'API"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    requests_per_minute: float
    active_connections: int
    timestamp: datetime

@dataclass
class RAGMetrics:
    """Métriques spécifiques au système RAG"""
    total_queries: int
    predefined_qa_hits: int
    rag_queries: int
    cache_hits: int
    cache_misses: int
    avg_embedding_time: float
    avg_llm_time: float
    avg_total_time: float
    timestamp: datetime

class MetricsCollector:
    """Collecteur de métriques centralisé"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Métriques spécialisées
        self.api_metrics = APIMetrics(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            requests_per_minute=0.0,
            active_connections=0,
            timestamp=datetime.now()
        )
        
        self.rag_metrics = RAGMetrics(
            total_queries=0,
            predefined_qa_hits=0,
            rag_queries=0,
            cache_hits=0,
            cache_misses=0,
            avg_embedding_time=0.0,
            avg_llm_time=0.0,
            avg_total_time=0.0,
            timestamp=datetime.now()
        )
        
        # Historique des temps de réponse
        self.response_times: deque = deque(maxlen=1000)
        self.request_timestamps: deque = deque(maxlen=1000)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Démarrage de la collecte automatique
        self._start_background_collection()
    
    def _start_background_collection(self):
        """Démarre la collecte automatique des métriques système"""
        def collect_system_metrics():
            while True:
                try:
                    self._collect_system_metrics()
                    time.sleep(30)  # Collecte toutes les 30 secondes
                except Exception as e:
                    print(f"Erreur lors de la collecte des métriques système: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
    
    def _collect_system_metrics(self):
        """Collecte les métriques système"""
        try:
            # Métriques CPU et mémoire
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            perf_metrics = PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                timestamp=datetime.now()
            )
            
            with self._lock:
                self.metrics_history['system_performance'].append(perf_metrics)
                
                # Mise à jour des gauges
                self.gauges['cpu_percent'] = cpu_percent
                self.gauges['memory_percent'] = memory.percent
                self.gauges['disk_usage_percent'] = disk.percent
                
        except Exception as e:
            print(f"Erreur lors de la collecte des métriques système: {e}")
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Incrémente un compteur"""
        with self._lock:
            self.counters[name] += value
            metric = MetricData(
                name=name,
                value=self.counters[name],
                timestamp=datetime.now(),
                labels=labels or {},
                metric_type=MetricType.COUNTER
            )
            self.metrics_history[name].append(metric)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Définit la valeur d'une jauge"""
        with self._lock:
            self.gauges[name] = value
            metric = MetricData(
                name=name,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {},
                metric_type=MetricType.GAUGE
            )
            self.metrics_history[name].append(metric)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Enregistre une valeur dans un histogramme"""
        with self._lock:
            self.histograms[name].append(value)
            # Garde seulement les 1000 dernières valeurs
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            metric = MetricData(
                name=name,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {},
                metric_type=MetricType.HISTOGRAM
            )
            self.metrics_history[name].append(metric)
    
    @asynccontextmanager
    async def timer(self, name: str, labels: Dict[str, str] = None):
        """Context manager pour mesurer le temps d'exécution"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_timer(name, duration, labels)
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Enregistre une durée"""
        with self._lock:
            self.timers[name].append(duration)
            # Garde seulement les 1000 dernières valeurs
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
            
            metric = MetricData(
                name=name,
                value=duration,
                timestamp=datetime.now(),
                labels=labels or {},
                metric_type=MetricType.TIMER
            )
            self.metrics_history[name].append(metric)
    
    def record_api_request(self, success: bool, response_time: float):
        """Enregistre une requête API"""
        with self._lock:
            self.api_metrics.total_requests += 1
            if success:
                self.api_metrics.successful_requests += 1
            else:
                self.api_metrics.failed_requests += 1
            
            # Mise à jour du temps de réponse moyen
            self.response_times.append(response_time)
            if self.response_times:
                self.api_metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
            
            # Calcul des requêtes par minute
            now = datetime.now()
            self.request_timestamps.append(now)
            
            # Compte les requêtes de la dernière minute
            one_minute_ago = now - timedelta(minutes=1)
            recent_requests = [ts for ts in self.request_timestamps if ts > one_minute_ago]
            self.api_metrics.requests_per_minute = len(recent_requests)
            
            self.api_metrics.timestamp = now
    
    def record_rag_query(self, query_type: str, embedding_time: float = 0, llm_time: float = 0, total_time: float = 0):
        """Enregistre une requête RAG"""
        with self._lock:
            self.rag_metrics.total_queries += 1
            
            if query_type == "predefined_qa":
                self.rag_metrics.predefined_qa_hits += 1
            elif query_type == "rag":
                self.rag_metrics.rag_queries += 1
            
            # Mise à jour des temps moyens
            if embedding_time > 0:
                self.rag_metrics.avg_embedding_time = (
                    (self.rag_metrics.avg_embedding_time * (self.rag_metrics.total_queries - 1) + embedding_time) /
                    self.rag_metrics.total_queries
                )
            
            if llm_time > 0:
                self.rag_metrics.avg_llm_time = (
                    (self.rag_metrics.avg_llm_time * (self.rag_metrics.total_queries - 1) + llm_time) /
                    self.rag_metrics.total_queries
                )
            
            if total_time > 0:
                self.rag_metrics.avg_total_time = (
                    (self.rag_metrics.avg_total_time * (self.rag_metrics.total_queries - 1) + total_time) /
                    self.rag_metrics.total_queries
                )
            
            self.rag_metrics.timestamp = datetime.now()
    
    def record_cache_hit(self, hit: bool):
        """Enregistre un hit/miss de cache"""
        with self._lock:
            if hit:
                self.rag_metrics.cache_hits += 1
            else:
                self.rag_metrics.cache_misses += 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de toutes les métriques"""
        with self._lock:
            # Calcul des statistiques pour les histogrammes et timers
            histogram_stats = {}
            for name, values in self.histograms.items():
                if values:
                    histogram_stats[name] = {
                        'count': len(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'p50': sorted(values)[len(values) // 2] if values else 0,
                        'p95': sorted(values)[int(len(values) * 0.95)] if values else 0,
                        'p99': sorted(values)[int(len(values) * 0.99)] if values else 0
                    }
            
            timer_stats = {}
            for name, values in self.timers.items():
                if values:
                    timer_stats[name] = {
                        'count': len(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'p50': sorted(values)[len(values) // 2] if values else 0,
                        'p95': sorted(values)[int(len(values) * 0.95)] if values else 0,
                        'p99': sorted(values)[int(len(values) * 0.99)] if values else 0
                    }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': histogram_stats,
                'timers': timer_stats,
                'api_metrics': asdict(self.api_metrics),
                'rag_metrics': asdict(self.rag_metrics),
                'system_performance': asdict(self.metrics_history['system_performance'][-1]) if self.metrics_history['system_performance'] else None
            }
    
    def get_metric_history(self, name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retourne l'historique d'une métrique"""
        with self._lock:
            history = list(self.metrics_history[name])[-limit:]
            return [asdict(metric) if hasattr(metric, '__dict__') else metric for metric in history]
    
    def export_prometheus_format(self) -> str:
        """Exporte les métriques au format Prometheus"""
        lines = []
        
        # Compteurs
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Jauges
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Métriques API
        lines.extend([
            "# TYPE api_requests_total counter",
            f"api_requests_total {self.api_metrics.total_requests}",
            "# TYPE api_requests_successful_total counter",
            f"api_requests_successful_total {self.api_metrics.successful_requests}",
            "# TYPE api_requests_failed_total counter",
            f"api_requests_failed_total {self.api_metrics.failed_requests}",
            "# TYPE api_response_time_avg gauge",
            f"api_response_time_avg {self.api_metrics.avg_response_time}",
            "# TYPE api_requests_per_minute gauge",
            f"api_requests_per_minute {self.api_metrics.requests_per_minute}"
        ])
        
        # Métriques RAG
        lines.extend([
            "# TYPE rag_queries_total counter",
            f"rag_queries_total {self.rag_metrics.total_queries}",
            "# TYPE rag_predefined_qa_hits counter",
            f"rag_predefined_qa_hits {self.rag_metrics.predefined_qa_hits}",
            "# TYPE rag_cache_hits counter",
            f"rag_cache_hits {self.rag_metrics.cache_hits}",
            "# TYPE rag_cache_misses counter",
            f"rag_cache_misses {self.rag_metrics.cache_misses}"
        ])
        
        return "\n".join(lines)

# Instance globale du collecteur de métriques
metrics_collector = MetricsCollector()