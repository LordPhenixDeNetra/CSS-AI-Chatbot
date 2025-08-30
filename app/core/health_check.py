#!/usr/bin/env python3
"""
Service de health check pour le monitoring des composants critiques
"""

import asyncio
import time
import redis
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import httpx
import os
from pathlib import Path

class HealthStatus(Enum):
    """États de santé possibles"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ComponentHealth:
    """État de santé d'un composant"""
    name: str
    status: HealthStatus
    message: str
    response_time: float
    timestamp: datetime
    details: Dict[str, Any] = None

@dataclass
class SystemHealth:
    """État de santé global du système"""
    overall_status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime
    uptime: float
    version: str

class HealthChecker:
    """Vérificateur de santé des composants"""
    
    def __init__(self):
        self.start_time = time.time()
        self.version = "1.0.0"
        self.redis_client = None
        self.last_check_cache = {}
        self.check_interval = 30  # secondes
        
        # Initialisation des clients
        self._init_redis_client()
    
    def _init_redis_client(self):
        """Initialise le client Redis"""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
        except Exception as e:
            print(f"Erreur lors de l'initialisation du client Redis: {e}")
    
    async def check_system_resources(self) -> ComponentHealth:
        """Vérifie les ressources système"""
        start_time = time.time()
        
        try:
            # Vérification CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Vérification mémoire
            memory = psutil.virtual_memory()
            
            # Vérification disque
            disk = psutil.disk_usage('/')
            
            # Détermination du statut
            status = HealthStatus.HEALTHY
            messages = []
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                messages.append(f"CPU usage critical: {cpu_percent}%")
            elif cpu_percent > 70:
                status = HealthStatus.DEGRADED
                messages.append(f"CPU usage high: {cpu_percent}%")
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                messages.append(f"Memory usage critical: {memory.percent}%")
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                messages.append(f"Memory usage high: {memory.percent}%")
            
            if disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                messages.append(f"Disk usage critical: {disk.percent}%")
            elif disk.percent > 85:
                status = HealthStatus.DEGRADED
                messages.append(f"Disk usage high: {disk.percent}%")
            
            message = "; ".join(messages) if messages else "System resources OK"
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2)
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Error checking system resources: {str(e)}"
            details = {"error": str(e)}
        
        response_time = time.time() - start_time
        
        return ComponentHealth(
            name="system_resources",
            status=status,
            message=message,
            response_time=response_time,
            timestamp=datetime.now(),
            details=details
        )
    
    async def check_redis(self) -> ComponentHealth:
        """Vérifie la connexion Redis"""
        start_time = time.time()
        
        try:
            if not self.redis_client:
                raise Exception("Redis client not initialized")
            
            # Test de ping
            ping_result = self.redis_client.ping()
            
            if not ping_result:
                raise Exception("Redis ping failed")
            
            # Test d'écriture/lecture
            test_key = "health_check_test"
            test_value = str(time.time())
            
            self.redis_client.set(test_key, test_value, ex=60)
            retrieved_value = self.redis_client.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception("Redis read/write test failed")
            
            # Informations Redis
            info = self.redis_client.info()
            
            status = HealthStatus.HEALTHY
            message = "Redis connection OK"
            
            details = {
                "version": info.get('redis_version'),
                "connected_clients": info.get('connected_clients'),
                "used_memory_human": info.get('used_memory_human'),
                "uptime_in_seconds": info.get('uptime_in_seconds')
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Redis connection failed: {str(e)}"
            details = {"error": str(e)}
        
        response_time = time.time() - start_time
        
        return ComponentHealth(
            name="redis",
            status=status,
            message=message,
            response_time=response_time,
            timestamp=datetime.now(),
            details=details
        )
    
    async def check_ai_models(self) -> ComponentHealth:
        """Vérifie l'état des modèles IA"""
        start_time = time.time()
        
        try:
            # Vérification des modèles chargés
            models_status = {}
            
            # Vérification du modèle d'embeddings
            try:
                from app.core.embeddings import embedding_model
                if hasattr(embedding_model, 'model') and embedding_model.model is not None:
                    models_status['embedding_model'] = 'loaded'
                else:
                    models_status['embedding_model'] = 'not_loaded'
            except Exception as e:
                models_status['embedding_model'] = f'error: {str(e)}'
            
            # Vérification du reranker
            try:
                from app.core.reranker import reranker
                if hasattr(reranker, 'model') and reranker.model is not None:
                    models_status['reranker'] = 'loaded'
                else:
                    models_status['reranker'] = 'not_loaded'
            except Exception as e:
                models_status['reranker'] = f'error: {str(e)}'
            
            # Vérification du LLM provider
            try:
                from app.core.llm_provider import llm_provider
                if llm_provider and hasattr(llm_provider, 'client'):
                    models_status['llm_provider'] = 'initialized'
                else:
                    models_status['llm_provider'] = 'not_initialized'
            except Exception as e:
                models_status['llm_provider'] = f'error: {str(e)}'
            
            # Détermination du statut global
            loaded_models = sum(1 for status in models_status.values() if 'loaded' in status or 'initialized' in status)
            total_models = len(models_status)
            
            if loaded_models == total_models:
                status = HealthStatus.HEALTHY
                message = "All AI models loaded successfully"
            elif loaded_models > 0:
                status = HealthStatus.DEGRADED
                message = f"Some AI models not loaded ({loaded_models}/{total_models})"
            else:
                status = HealthStatus.UNHEALTHY
                message = "No AI models loaded"
            
            details = {
                "models_status": models_status,
                "loaded_models": loaded_models,
                "total_models": total_models
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Error checking AI models: {str(e)}"
            details = {"error": str(e)}
        
        response_time = time.time() - start_time
        
        return ComponentHealth(
            name="ai_models",
            status=status,
            message=message,
            response_time=response_time,
            timestamp=datetime.now(),
            details=details
        )
    
    async def check_database_connection(self) -> ComponentHealth:
        """Vérifie la connexion à la base de données"""
        start_time = time.time()
        
        try:
            # Vérification de la base de données vectorielle (si utilisée)
            # Pour l'instant, on simule une vérification basique
            
            # Vérification des fichiers de données
            data_dir = Path("data")
            if data_dir.exists():
                file_count = len(list(data_dir.glob("**/*")))
                status = HealthStatus.HEALTHY
                message = f"Data directory accessible with {file_count} files"
                details = {
                    "data_directory": str(data_dir.absolute()),
                    "file_count": file_count,
                    "directory_size_mb": self._get_directory_size(data_dir)
                }
            else:
                status = HealthStatus.DEGRADED
                message = "Data directory not found"
                details = {"data_directory": str(data_dir.absolute())}
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Database connection failed: {str(e)}"
            details = {"error": str(e)}
        
        response_time = time.time() - start_time
        
        return ComponentHealth(
            name="database",
            status=status,
            message=message,
            response_time=response_time,
            timestamp=datetime.now(),
            details=details
        )
    
    def _get_directory_size(self, path: Path) -> float:
        """Calcule la taille d'un répertoire en MB"""
        try:
            total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            return round(total_size / (1024 * 1024), 2)
        except:
            return 0.0
    
    async def check_api_endpoints(self) -> ComponentHealth:
        """Vérifie les endpoints API critiques"""
        start_time = time.time()
        
        try:
            # Test des endpoints internes
            base_url = "http://localhost:8000"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test de l'endpoint de base
                try:
                    response = await client.get(f"{base_url}/")
                    root_status = response.status_code == 200
                except:
                    root_status = False
                
                # Test de l'endpoint de santé (s'il existe)
                try:
                    response = await client.get(f"{base_url}/health")
                    health_status = response.status_code == 200
                except:
                    health_status = False
            
            if root_status:
                status = HealthStatus.HEALTHY
                message = "API endpoints responding"
            else:
                status = HealthStatus.UNHEALTHY
                message = "API endpoints not responding"
            
            details = {
                "root_endpoint": root_status,
                "health_endpoint": health_status,
                "base_url": base_url
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Error checking API endpoints: {str(e)}"
            details = {"error": str(e)}
        
        response_time = time.time() - start_time
        
        return ComponentHealth(
            name="api_endpoints",
            status=status,
            message=message,
            response_time=response_time,
            timestamp=datetime.now(),
            details=details
        )
    
    async def perform_full_health_check(self) -> SystemHealth:
        """Effectue un check complet de tous les composants"""
        components = []
        
        # Exécution parallèle de tous les checks
        checks = [
            self.check_system_resources(),
            self.check_redis(),
            self.check_ai_models(),
            self.check_database_connection(),
            self.check_api_endpoints()
        ]
        
        try:
            results = await asyncio.gather(*checks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, ComponentHealth):
                    components.append(result)
                else:
                    # En cas d'exception
                    components.append(ComponentHealth(
                        name="unknown_component",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed: {str(result)}",
                        response_time=0.0,
                        timestamp=datetime.now()
                    ))
        
        except Exception as e:
            components.append(ComponentHealth(
                name="health_check_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check system error: {str(e)}",
                response_time=0.0,
                timestamp=datetime.now()
            ))
        
        # Détermination du statut global
        overall_status = self._determine_overall_status(components)
        
        # Calcul de l'uptime
        uptime = time.time() - self.start_time
        
        return SystemHealth(
            overall_status=overall_status,
            components=components,
            timestamp=datetime.now(),
            uptime=uptime,
            version=self.version
        )
    
    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Détermine le statut global basé sur les composants"""
        if not components:
            return HealthStatus.UNKNOWN
        
        statuses = [comp.status for comp in components]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    async def check_system_health(self):
        """Check de santé système pour le dashboard"""
        try:
            # Effectuer un check complet
            full_health = await self.perform_full_health_check()
            
            # Convertir au format attendu par le dashboard
            components_dict = {}
            for component in full_health.components:
                components_dict[component.name] = {
                    "status": component.status,
                    "message": component.message,
                    "response_time_ms": component.response_time * 1000  # Conversion en ms
                }
            
            return type('HealthStatus', (), {
                'status': full_health.overall_status,
                'components': components_dict,
                'system_info': {
                    'uptime': full_health.uptime,
                    'version': full_health.version,
                    'timestamp': full_health.timestamp.isoformat()
                }
            })()
            
        except Exception as e:
            # Retour d'urgence en cas d'erreur
            return type('HealthStatus', (), {
                'status': HealthStatus.UNHEALTHY,
                'components': {
                    'system': {
                        'status': HealthStatus.UNHEALTHY,
                        'message': f"Health check error: {str(e)}",
                        'response_time_ms': 0
                    }
                },
                'system_info': {
                    'uptime': time.time() - self.start_time,
                    'version': self.version,
                    'timestamp': datetime.now().isoformat()
                }
            })()
    
    async def quick_health_check(self) -> Dict[str, Any]:
        """Check rapide pour les endpoints de monitoring"""
        # Utilise le cache si disponible et récent
        cache_key = "quick_health_check"
        now = time.time()
        
        if (cache_key in self.last_check_cache and 
            now - self.last_check_cache[cache_key]['timestamp'] < self.check_interval):
            return self.last_check_cache[cache_key]['data']
        
        # Effectue un check rapide
        start_time = time.time()
        
        try:
            # Checks basiques
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # Test Redis rapide
            redis_ok = False
            try:
                if self.redis_client:
                    redis_ok = self.redis_client.ping()
            except:
                pass
            
            status = "healthy"
            if cpu_percent > 90 or memory.percent > 90:
                status = "unhealthy"
            elif cpu_percent > 70 or memory.percent > 80 or not redis_ok:
                status = "degraded"
            
            result = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - self.start_time,
                "version": self.version,
                "response_time": time.time() - start_time,
                "components": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "redis": redis_ok
                }
            }
            
            # Mise en cache
            self.last_check_cache[cache_key] = {
                'timestamp': now,
                'data': result
            }
            
            return result
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "response_time": time.time() - start_time
            }

# Instance globale du health checker
health_checker = HealthChecker()