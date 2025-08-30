from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from app.core.metrics import metrics_collector

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types de requêtes pour les métriques métier"""
    PREDEFINED_QA = "predefined_qa"
    RAG_SEARCH = "rag_search"
    HYBRID = "hybrid"
    FALLBACK = "fallback"

class ResponseSource(Enum):
    """Sources des réponses"""
    PREDEFINED = "predefined"
    RAG_RETRIEVAL = "rag_retrieval"
    AI_GENERATION = "ai_generation"
    CACHE = "cache"
    ERROR = "error"

@dataclass
class BusinessMetric:
    """Métrique métier avec contexte"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BusinessMetricsCollector:
    """Collecteur de métriques métier spécifiques à l'application AI CSS"""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.predefined_qa_stats = {
            "total_queries": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "categories": {},
            "response_times": []
        }
        self.rag_stats = {
            "total_queries": 0,
            "successful_retrievals": 0,
            "failed_retrievals": 0,
            "avg_relevance_score": 0.0,
            "document_hits": {},
            "embedding_times": [],
            "retrieval_times": []
        }
        self.cache_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "cache_invalidations": 0,
            "hit_rate_by_endpoint": {}
        }
        self.user_interaction_stats = {
            "unique_sessions": set(),
            "total_interactions": 0,
            "avg_session_duration": 0.0,
            "popular_queries": {},
            "user_satisfaction_scores": []
        }
    
    def record_predefined_qa_query(self, 
                                   question: str, 
                                   matched: bool, 
                                   category: str = None,
                                   response_time: float = 0.0,
                                   confidence_score: float = 0.0):
        """Enregistre une requête Q&A prédéfinie"""
        try:
            self.predefined_qa_stats["total_queries"] += 1
            
            if matched:
                self.predefined_qa_stats["successful_matches"] += 1
                metrics_collector.increment_counter("predefined_qa_matches_total", {
                    "category": category or "unknown",
                    "status": "success"
                })
            else:
                self.predefined_qa_stats["failed_matches"] += 1
                metrics_collector.increment_counter("predefined_qa_matches_total", {
                    "category": category or "unknown",
                    "status": "failed"
                })
            
            # Statistiques par catégorie
            if category:
                if category not in self.predefined_qa_stats["categories"]:
                    self.predefined_qa_stats["categories"][category] = {
                        "total": 0, "matches": 0
                    }
                self.predefined_qa_stats["categories"][category]["total"] += 1
                if matched:
                    self.predefined_qa_stats["categories"][category]["matches"] += 1
            
            # Temps de réponse
            if response_time > 0:
                self.predefined_qa_stats["response_times"].append(response_time)
                metrics_collector.record_histogram("predefined_qa_response_time_seconds", 
                                                  response_time, {
                    "category": category or "unknown",
                    "matched": str(matched)
                })
            
            # Score de confiance
            if confidence_score > 0:
                metrics_collector.record_histogram("predefined_qa_confidence_score", 
                                                  confidence_score, {
                    "category": category or "unknown"
                })
            
            logger.info(f"Recorded predefined Q&A: matched={matched}, category={category}, time={response_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error recording predefined Q&A metric: {e}")
    
    def record_rag_query(self, 
                        question: str,
                        success: bool,
                        relevance_score: float = 0.0,
                        num_documents_retrieved: int = 0,
                        embedding_time: float = 0.0,
                        retrieval_time: float = 0.0,
                        reranking_time: float = 0.0,
                        documents_used: List[str] = None):
        """Enregistre une requête RAG"""
        try:
            self.rag_stats["total_queries"] += 1
            
            if success:
                self.rag_stats["successful_retrievals"] += 1
                metrics_collector.increment_counter("rag_queries_total", {
                    "status": "success",
                    "num_docs": str(min(num_documents_retrieved, 10))  # Grouper par tranches
                })
            else:
                self.rag_stats["failed_retrievals"] += 1
                metrics_collector.increment_counter("rag_queries_total", {
                    "status": "failed",
                    "num_docs": "0"
                })
            
            # Score de pertinence
            if relevance_score > 0:
                # Mise à jour de la moyenne mobile
                current_avg = self.rag_stats["avg_relevance_score"]
                total_queries = self.rag_stats["total_queries"]
                self.rag_stats["avg_relevance_score"] = (
                    (current_avg * (total_queries - 1) + relevance_score) / total_queries
                )
                
                metrics_collector.record_histogram("rag_relevance_score", relevance_score, {
                    "success": str(success)
                })
            
            # Temps d'embedding
            if embedding_time > 0:
                self.rag_stats["embedding_times"].append(embedding_time)
                metrics_collector.record_histogram("rag_embedding_time_seconds", embedding_time)
            
            # Temps de récupération
            if retrieval_time > 0:
                self.rag_stats["retrieval_times"].append(retrieval_time)
                metrics_collector.record_histogram("rag_retrieval_time_seconds", retrieval_time, {
                    "num_docs": str(num_documents_retrieved)
                })
            
            # Temps de reranking
            if reranking_time > 0:
                metrics_collector.record_histogram("rag_reranking_time_seconds", reranking_time)
            
            # Documents utilisés
            if documents_used:
                for doc_id in documents_used:
                    if doc_id not in self.rag_stats["document_hits"]:
                        self.rag_stats["document_hits"][doc_id] = 0
                    self.rag_stats["document_hits"][doc_id] += 1
                    
                    metrics_collector.increment_counter("rag_document_usage_total", {
                        "document_id": doc_id[:50]  # Limiter la longueur pour éviter la cardinalité élevée
                    })
            
            logger.info(f"Recorded RAG query: success={success}, relevance={relevance_score:.3f}, docs={num_documents_retrieved}")
            
        except Exception as e:
            logger.error(f"Error recording RAG metric: {e}")
    
    def record_cache_operation(self, 
                              operation: str,  # 'hit', 'miss', 'write', 'invalidate'
                              endpoint: str,
                              cache_key: str = None,
                              response_time_saved: float = 0.0):
        """Enregistre une opération de cache"""
        try:
            self.cache_stats["total_requests"] += 1
            
            if operation == "hit":
                self.cache_stats["cache_hits"] += 1
                metrics_collector.increment_counter("cache_operations_total", {
                    "operation": "hit",
                    "endpoint": endpoint
                })
                
                if response_time_saved > 0:
                    metrics_collector.record_histogram("cache_time_saved_seconds", 
                                                      response_time_saved, {
                        "endpoint": endpoint
                    })
                
            elif operation == "miss":
                self.cache_stats["cache_misses"] += 1
                metrics_collector.increment_counter("cache_operations_total", {
                    "operation": "miss",
                    "endpoint": endpoint
                })
                
            elif operation == "write":
                self.cache_stats["cache_writes"] += 1
                metrics_collector.increment_counter("cache_operations_total", {
                    "operation": "write",
                    "endpoint": endpoint
                })
                
            elif operation == "invalidate":
                self.cache_stats["cache_invalidations"] += 1
                metrics_collector.increment_counter("cache_operations_total", {
                    "operation": "invalidate",
                    "endpoint": endpoint
                })
            
            # Calcul du taux de hit par endpoint
            if endpoint not in self.cache_stats["hit_rate_by_endpoint"]:
                self.cache_stats["hit_rate_by_endpoint"][endpoint] = {
                    "hits": 0, "total": 0
                }
            
            endpoint_stats = self.cache_stats["hit_rate_by_endpoint"][endpoint]
            endpoint_stats["total"] += 1
            if operation == "hit":
                endpoint_stats["hits"] += 1
            
            # Calculer et enregistrer le taux de hit
            hit_rate = endpoint_stats["hits"] / endpoint_stats["total"] * 100
            metrics_collector.set_gauge("cache_hit_rate_percent", hit_rate, {
                "endpoint": endpoint
            })
            
            logger.debug(f"Recorded cache operation: {operation} for {endpoint}")
            
        except Exception as e:
            logger.error(f"Error recording cache metric: {e}")
    
    def record_user_interaction(self, 
                               session_id: str,
                               interaction_type: str,
                               query: str = None,
                               satisfaction_score: float = None,
                               session_duration: float = None):
        """Enregistre une interaction utilisateur"""
        try:
            self.user_interaction_stats["unique_sessions"].add(session_id)
            self.user_interaction_stats["total_interactions"] += 1
            
            metrics_collector.increment_counter("user_interactions_total", {
                "type": interaction_type,
                "session_id": session_id[:8]  # Anonymiser partiellement
            })
            
            # Requêtes populaires
            if query:
                query_normalized = query.lower().strip()[:100]  # Normaliser et limiter
                if query_normalized not in self.user_interaction_stats["popular_queries"]:
                    self.user_interaction_stats["popular_queries"][query_normalized] = 0
                self.user_interaction_stats["popular_queries"][query_normalized] += 1
            
            # Score de satisfaction
            if satisfaction_score is not None:
                self.user_interaction_stats["user_satisfaction_scores"].append(satisfaction_score)
                metrics_collector.record_histogram("user_satisfaction_score", satisfaction_score, {
                    "interaction_type": interaction_type
                })
            
            # Durée de session
            if session_duration is not None:
                metrics_collector.record_histogram("user_session_duration_seconds", session_duration)
            
            logger.debug(f"Recorded user interaction: {interaction_type} for session {session_id[:8]}")
            
        except Exception as e:
            logger.error(f"Error recording user interaction metric: {e}")
    
    def get_business_metrics_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des métriques métier"""
        try:
            # Calculs dérivés
            predefined_success_rate = (
                self.predefined_qa_stats["successful_matches"] / 
                max(self.predefined_qa_stats["total_queries"], 1) * 100
            )
            
            rag_success_rate = (
                self.rag_stats["successful_retrievals"] / 
                max(self.rag_stats["total_queries"], 1) * 100
            )
            
            cache_hit_rate = (
                self.cache_stats["cache_hits"] / 
                max(self.cache_stats["total_requests"], 1) * 100
            )
            
            avg_predefined_response_time = (
                sum(self.predefined_qa_stats["response_times"]) / 
                max(len(self.predefined_qa_stats["response_times"]), 1)
            )
            
            avg_rag_embedding_time = (
                sum(self.rag_stats["embedding_times"]) / 
                max(len(self.rag_stats["embedding_times"]), 1)
            )
            
            avg_rag_retrieval_time = (
                sum(self.rag_stats["retrieval_times"]) / 
                max(len(self.rag_stats["retrieval_times"]), 1)
            )
            
            avg_satisfaction = (
                sum(self.user_interaction_stats["user_satisfaction_scores"]) / 
                max(len(self.user_interaction_stats["user_satisfaction_scores"]), 1)
            )
            
            # Top 5 des requêtes populaires
            top_queries = sorted(
                self.user_interaction_stats["popular_queries"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Top 5 des documents les plus utilisés
            top_documents = sorted(
                self.rag_stats["document_hits"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                "timestamp": datetime.now().isoformat(),
                "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
                "predefined_qa": {
                    "total_queries": self.predefined_qa_stats["total_queries"],
                    "success_rate_percent": round(predefined_success_rate, 2),
                    "avg_response_time_ms": round(avg_predefined_response_time * 1000, 2),
                    "categories_stats": self.predefined_qa_stats["categories"]
                },
                "rag_system": {
                    "total_queries": self.rag_stats["total_queries"],
                    "success_rate_percent": round(rag_success_rate, 2),
                    "avg_relevance_score": round(self.rag_stats["avg_relevance_score"], 3),
                    "avg_embedding_time_ms": round(avg_rag_embedding_time * 1000, 2),
                    "avg_retrieval_time_ms": round(avg_rag_retrieval_time * 1000, 2),
                    "top_documents": top_documents
                },
                "cache_performance": {
                    "total_requests": self.cache_stats["total_requests"],
                    "hit_rate_percent": round(cache_hit_rate, 2),
                    "total_hits": self.cache_stats["cache_hits"],
                    "total_misses": self.cache_stats["cache_misses"],
                    "hit_rate_by_endpoint": {
                        endpoint: round(stats["hits"] / max(stats["total"], 1) * 100, 2)
                        for endpoint, stats in self.cache_stats["hit_rate_by_endpoint"].items()
                    }
                },
                "user_engagement": {
                    "unique_sessions": len(self.user_interaction_stats["unique_sessions"]),
                    "total_interactions": self.user_interaction_stats["total_interactions"],
                    "avg_satisfaction_score": round(avg_satisfaction, 2),
                    "top_queries": top_queries
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating business metrics summary: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def reset_session_metrics(self):
        """Remet à zéro les métriques de session"""
        self.session_start = datetime.now()
        self.predefined_qa_stats["response_times"].clear()
        self.rag_stats["embedding_times"].clear()
        self.rag_stats["retrieval_times"].clear()
        self.user_interaction_stats["user_satisfaction_scores"].clear()
        logger.info("Session metrics reset")

# Instance globale du collecteur de métriques métier
business_metrics_collector = BusinessMetricsCollector()