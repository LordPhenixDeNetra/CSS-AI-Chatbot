from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Callable
from app.core.metrics import metrics_collector

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour collecter automatiquement les métriques sur chaque requête API
    """
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ignorer certains endpoints pour éviter la pollution des métriques
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Enregistrer le début de la requête
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        # Incrémenter le compteur de requêtes
        metrics_collector.increment_counter("api_requests_total", 1.0, {
            "method": method,
            "endpoint": path
        })
        
        # Traiter la requête
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculer le temps de réponse
            response_time = time.time() - start_time
            
            # Enregistrer les métriques de succès
            metrics_collector.record_histogram("api_response_time_seconds", response_time, {
                "method": method,
                "endpoint": path,
                "status_code": str(status_code)
            })
            
            # Incrémenter le compteur de réponses par statut
            metrics_collector.increment_counter("api_responses_total", 1.0, {
                "method": method,
                "endpoint": path,
                "status_code": str(status_code)
            })
            
            # Enregistrer la requête API dans les métriques spécialisées
            success = status_code < 400
            metrics_collector.record_api_request(success, response_time)
            
            # Métriques spécifiques pour les erreurs
            if status_code >= 400:
                metrics_collector.increment_counter("api_errors_total", 1.0, {
                    "method": method,
                    "endpoint": path,
                    "status_code": str(status_code)
                })
            
            # Log pour les requêtes lentes
            if response_time > 5.0:
                logger.warning(f"Slow request: {method} {path} took {response_time:.2f}s")
                metrics_collector.increment_counter("api_slow_requests_total", 1.0, {
                    "method": method,
                    "endpoint": path
                })
            
            return response
            
        except Exception as e:
            # Calculer le temps même en cas d'erreur
            response_time = time.time() - start_time
            
            # Enregistrer les métriques d'erreur
            metrics_collector.increment_counter("api_errors_total", 1.0, {
                "method": method,
                "endpoint": path,
                "status_code": "500",
                "error_type": type(e).__name__
            })
            
            metrics_collector.record_histogram("api_response_time_seconds", response_time, {
                "method": method,
                "endpoint": path,
                "status_code": "500"
            })
            
            # Enregistrer la requête API échouée dans les métriques spécialisées
            metrics_collector.record_api_request(False, response_time)
            
            logger.error(f"Request error: {method} {path} - {str(e)}")
            
            # Re-lever l'exception
            raise e

class RAGMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware spécialisé pour collecter les métriques des opérations RAG
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rag_endpoints = ["/ask-question", "/ask-question-stream", "/ask-question-stream-ultra"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Vérifier si c'est un endpoint RAG
        is_rag_endpoint = any(request.url.path.startswith(endpoint) for endpoint in self.rag_endpoints)
        
        if not is_rag_endpoint:
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculer le temps de traitement RAG
            processing_time = time.time() - start_time
            
            # Métriques spécifiques RAG
            metrics_collector.record_histogram("rag_processing_time_seconds", processing_time, {
                "endpoint": request.url.path,
                "status": "success"
            })
            
            metrics_collector.increment_counter("rag_queries_total", 1.0, {
                "endpoint": request.url.path,
                "status": "success"
            })
            
            # Enregistrer la requête RAG dans les métriques spécialisées
            metrics_collector.record_rag_query("rag", total_time=processing_time)
            
            # Métriques de performance RAG
            if processing_time > 10.0:
                metrics_collector.increment_counter("rag_slow_queries_total", 1.0, {
                    "endpoint": request.url.path
                })
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Métriques d'erreur RAG
            metrics_collector.record_histogram("rag_processing_time_seconds", processing_time, {
                "endpoint": request.url.path,
                "status": "error"
            })
            
            metrics_collector.increment_counter("rag_queries_total", 1.0, {
                "endpoint": request.url.path,
                "status": "error"
            })
            
            metrics_collector.increment_counter("rag_errors_total", 1.0, {
                "endpoint": request.url.path,
                "error_type": type(e).__name__
            })
            
            # Enregistrer la requête RAG échouée dans les métriques spécialisées
            metrics_collector.record_rag_query("rag", total_time=processing_time)
            
            raise e

class CacheMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour collecter les métriques de cache
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ajouter un header pour tracker les hits/miss de cache
        response = await call_next(request)
        
        # Vérifier si la réponse vient du cache
        cache_status = response.headers.get("X-Cache-Status", "unknown")
        
        if cache_status in ["hit", "miss"]:
            metrics_collector.increment_counter("cache_operations_total", 1.0, {
                "status": cache_status,
                "endpoint": request.url.path
            })
            
            if cache_status == "hit":
                metrics_collector.increment_counter("cache_hits_total", 1.0, {
                    "endpoint": request.url.path
                })
            else:
                metrics_collector.increment_counter("cache_misses_total", 1.0, {
                    "endpoint": request.url.path
                })
        
        return response