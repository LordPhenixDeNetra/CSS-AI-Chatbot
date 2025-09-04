from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, StreamingResponse, Response
from typing import Optional, List
import asyncio
import uuid
import time
from datetime import datetime
import json
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image

from app.core.config import settings
from app.models.schemas import (
    QuestionRequest, AdvancedQuestionResponse, DocumentResponse,
    PerformanceMetrics, MultimodalUploadRequest, MultimodalQuestionRequest
)
from app.models.enums import Provider, ContentType, ModalityType
from app.services.rag_service import multimodal_rag_system
from app.services.document_service import process_document_advanced
from app.services.csv_logger import csv_logger
from app.utils.helpers import image_to_base64
from app.core.cache import REDIS_AVAILABLE, cache
from app.utils.logging import logger
from app.core.llm_provider import OptimizedLLMProvider, PROVIDER_CONFIGS
from app.core.metrics import metrics_collector
from app.core.health_check import health_checker

router = APIRouter()


@router.get("/", summary="API RAG Multimodal")
async def root():
    """Point d'entrée principal de l'API"""
    return {
        "message": "CSS ChatBot",
        "version": "2005.0.1",
        "features": [
            "Recherche hybride dense/sparse",
            "Re-ranking avec cross-encoder",
            "Cache multi-niveaux (Redis + mémoire)",
            "Support multimodal (texte + images)",
            "Métriques Prometheus",
            "Streaming des réponses",
            "Optimisations avancées"
        ],
        "endpoints": {
            "upload": "/upload-document, /upload-multimodal-document",
            "query": "/ask-question-ultra, /ask-multimodal-question",
            "monitoring": "/health, /health/detailed, /metrics, /metrics/prometheus, /performance-metrics, /alerts"
        }
    }


@router.get("/health", summary="Health check rapide")
async def health_check():
    """Vérification rapide de l'état de santé du système"""
    try:
        health_data = await health_checker.quick_health_check()
        return health_data
    except Exception as e:
        logger.error(f"Erreur lors du health check: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/health/detailed", summary="Health check détaillé")
async def detailed_health_check():
    """Vérification détaillée de l'état de santé de tous les composants"""
    try:
        system_health = await health_checker.perform_full_health_check()
        
        return {
            "overall_status": system_health.overall_status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "uptime_seconds": system_health.uptime,
            "version": system_health.version,
            "components": [
                {
                    "name": comp.name,
                    "status": comp.status.value,
                    "message": comp.message,
                    "response_time": comp.response_time,
                    "timestamp": comp.timestamp.isoformat(),
                    "details": comp.details
                }
                for comp in system_health.components
            ]
        }
    except Exception as e:
        logger.error(f"Erreur lors du health check détaillé: {e}")
        return {
            "overall_status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/metrics", summary="Métriques JSON")
async def metrics():
    """Endpoint pour les métriques au format JSON"""
    try:
        metrics_summary = metrics_collector.get_metrics_summary()
        return metrics_summary
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/prometheus", summary="Métriques Prometheus")
async def prometheus_metrics():
    """Endpoint pour Prometheus au format texte"""
    try:
        prometheus_data = metrics_collector.export_prometheus_format()
        return Response(content=prometheus_data, media_type="text/plain")
    except Exception as e:
        logger.error(f"Erreur lors de l'export Prometheus: {e}")
        return Response(content=f"# Error: {str(e)}", media_type="text/plain")

@router.get("/metrics/history/{metric_name}", summary="Historique d'une métrique")
async def metric_history(metric_name: str, limit: int = 100):
    """Récupère l'historique d'une métrique spécifique"""
    try:
        history = metrics_collector.get_metric_history(metric_name, limit)
        return {
            "metric_name": metric_name,
            "limit": limit,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance-metrics", summary="Métriques de performance")
async def get_performance_metrics():
    """Métriques de performance détaillées"""
    try:
        # Utilise le collecteur de métriques centralisé
        metrics_summary = metrics_collector.get_metrics_summary()
        
        # Ajoute des métriques spécifiques si nécessaire
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Métriques cache
        cache_stats = {}
        if REDIS_AVAILABLE and cache:
            try:
                cache_info = cache.redis_client.info()
                cache_stats = {
                    "connected_clients": cache_info.get('connected_clients', 0),
                    "used_memory_human": cache_info.get('used_memory_human', '0B'),
                    "keyspace_hits": cache_info.get('keyspace_hits', 0),
                    "keyspace_misses": cache_info.get('keyspace_misses', 0)
                }
            except Exception as e:
                logger.warning(f"Erreur récupération stats Redis: {e}")
                cache_stats = {"error": str(e)}
        
        # Métriques RAG
        rag_stats = {
            "total_documents": multimodal_rag_system.collection.count() if multimodal_rag_system and hasattr(multimodal_rag_system, 'collection') else 0,
            "embedding_model_loaded": hasattr(multimodal_rag_system, 'embeddings') if multimodal_rag_system else False,
            "reranker_loaded": hasattr(multimodal_rag_system, 'reranker') if multimodal_rag_system else False
        }
        
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
            "cache": cache_stats,
            "rag": rag_stats,
            "api": {
                "redis_available": REDIS_AVAILABLE,
                "multimodal_system_loaded": multimodal_rag_system is not None
            },
            "metrics_collector": metrics_summary
        }
    except Exception as e:
        logger.error(f"Erreur métriques performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", summary="Système d'alertes")
async def get_alerts():
    """Récupère les alertes actives du système"""
    try:
        alerts = []
        
        # Vérification des seuils critiques
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Alertes CPU
        if cpu_percent > 90:
            alerts.append({
                "level": "critical",
                "component": "system",
                "metric": "cpu_usage",
                "value": cpu_percent,
                "threshold": 90,
                "message": f"CPU usage critical: {cpu_percent}%",
                "timestamp": datetime.now().isoformat()
            })
        elif cpu_percent > 70:
            alerts.append({
                "level": "warning",
                "component": "system",
                "metric": "cpu_usage",
                "value": cpu_percent,
                "threshold": 70,
                "message": f"CPU usage high: {cpu_percent}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # Alertes mémoire
        if memory.percent > 90:
            alerts.append({
                "level": "critical",
                "component": "system",
                "metric": "memory_usage",
                "value": memory.percent,
                "threshold": 90,
                "message": f"Memory usage critical: {memory.percent}%",
                "timestamp": datetime.now().isoformat()
            })
        elif memory.percent > 80:
            alerts.append({
                "level": "warning",
                "component": "system",
                "metric": "memory_usage",
                "value": memory.percent,
                "threshold": 80,
                "message": f"Memory usage high: {memory.percent}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # Alertes disque
        if disk.percent > 95:
            alerts.append({
                "level": "critical",
                "component": "system",
                "metric": "disk_usage",
                "value": disk.percent,
                "threshold": 95,
                "message": f"Disk usage critical: {disk.percent}%",
                "timestamp": datetime.now().isoformat()
            })
        elif disk.percent > 85:
            alerts.append({
                "level": "warning",
                "component": "system",
                "metric": "disk_usage",
                "value": disk.percent,
                "threshold": 85,
                "message": f"Disk usage high: {disk.percent}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # Alertes Redis
        if not REDIS_AVAILABLE:
            alerts.append({
                "level": "critical",
                "component": "redis",
                "metric": "connection",
                "value": False,
                "threshold": True,
                "message": "Redis connection unavailable",
                "timestamp": datetime.now().isoformat()
            })
        
        # Vérification des métriques de performance
        metrics_summary = metrics_collector.get_metrics_summary()
        api_metrics = metrics_summary.get('api_metrics', {})
        
        # Alerte temps de réponse
        avg_response_time = api_metrics.get('avg_response_time', 0)
        if avg_response_time > 5.0:
            alerts.append({
                "level": "warning",
                "component": "api",
                "metric": "response_time",
                "value": avg_response_time,
                "threshold": 5.0,
                "message": f"Average response time high: {avg_response_time:.2f}s",
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_alerts": len(alerts),
            "critical_count": len([a for a in alerts if a['level'] == 'critical']),
            "warning_count": len([a for a in alerts if a['level'] == 'warning']),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des alertes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-document", response_model=DocumentResponse, summary="Upload document optimisé")
async def upload_document_optimized(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload et traitement optimisé de document"""
    start_time = time.time()

    try:
        # Lecture du contenu
        content = await file.read()

        # Traitement du document
        text = await process_document_advanced(content, file.filename)

        # Ajout au système RAG
        document_id = str(uuid.uuid4())
        result = await multimodal_rag_system.add_document(text, document_id)

        processing_time = (time.time() - start_time) * 1000

        return DocumentResponse(
            document_id=document_id,
            chunks_created=result["chunks_created"],
            processing_time_ms=round(processing_time, 2),
            status="success"
        )

    except Exception as e:
        logger.error(f"Erreur upload document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-question-ultra", response_model=AdvancedQuestionResponse, summary="Question ultra optimisée")
async def ask_question_ultra(request: QuestionRequest):
    """Endpoint de question ultra optimisé avec métriques"""
    start_time = time.time()
    error_message = None

    try:
        result = await multimodal_rag_system.query(
            question=request.question,
            provider=request.provider,
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Métriques
        from app.utils.logging import query_counter
        query_counter.labels(provider=request.provider.value, status="success").inc()
        
        # Enregistrement CSV asynchrone
        processing_time = (time.time() - start_time) * 1000
        csv_logger.log_ask_question_ultra(
            question=request.question,
            response=result.get("answer", ""),
            sources=[source.get("content", "")[:100] + "..." for source in result.get("sources", [])],
            confidence_score=result.get("confidence", None),
            processing_time_ms=processing_time,
            tokens_used=result.get("tokens_used", None),
            model_used=request.provider.value,
            cache_hit=result.get("cache_hit", None)
        )

        return AdvancedQuestionResponse(**result)

    except Exception as e:
        error_message = str(e)
        from app.utils.logging import query_counter
        query_counter.labels(provider=request.provider.value, status="error").inc()
        
        # Enregistrement CSV de l'erreur
        processing_time = (time.time() - start_time) * 1000
        csv_logger.log_ask_question_ultra(
            question=request.question,
            response="",
            processing_time_ms=processing_time,
            model_used=request.provider.value,
            error_message=error_message
        )
        
        logger.error(f"Erreur question ultra: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-question-stream-ultra", summary="Question streaming ultra optimisée")
async def ask_question_stream_ultra(request: QuestionRequest):
    """Version streaming de la question ultra optimisée"""

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    async def generate_ultra_stream():
        # Variables pour le logging CSV
        start_time = time.time()
        response_chunks = []
        final_response = ""
        error_message = None
        sources = []
        confidence_score = None
        cache_hit = None
        
        try:
            # Recherche et préparation du contexte (partie non-streaming)
            query_id = str(uuid.uuid4())

            # 0. Vérification des réponses prédéfinies (priorité absolue)
            if multimodal_rag_system.predefined_qa:
                predefined_response = multimodal_rag_system.predefined_qa.get_predefined_answer(request.question)
                
                if predefined_response:
                    logger.info(f"Réponse prédéfinie trouvée pour streaming: {request.question[:50]}...")
                    
                    # Métadonnées initiales pour réponse prédéfinie
                    initial_metadata = {
                        "id": query_id,
                        "provider": "predefined_qa",
                        "enhanced_queries": [request.question],
                        "timestamp": datetime.now().isoformat(),
                        "optimization_used": "predefined_qa",
                        "matched_question": predefined_response["matched_question"]
                    }
                    yield f"data: {json.dumps({'metadata': initial_metadata, 'type': 'init'})}\n\n"
                    
                    # Streaming simulé de la réponse prédéfinie (pour cohérence UX)
                    answer = predefined_response["answer"]
                    words = answer.split()
                    
                    for i, word in enumerate(words):
                        chunk_content = word if i == 0 else f' {word}'
                        response_chunks.append(chunk_content)
                        yield f"data: {json.dumps({'content': chunk_content, 'type': 'chunk'})}\n\n"
                        # Petit délai pour simuler le streaming naturel
                        await asyncio.sleep(0.05)
                    
                    # Données pour CSV
                    final_response = answer
                    confidence_score = predefined_response["confidence"]
                    cache_hit = True
                    
                    # Métadonnées finales
                    end_time = time.time()
                    processing_time = round((end_time - start_time) * 1000, 2)
                    final_metadata = {
                        "response_time_ms": processing_time,
                        "search_results": 0,
                        "ranked_results": 0,
                        "llm_calls_saved": True,
                        "confidence": predefined_response["confidence"],
                        "source": "predefined_qa"
                    }
                    yield f"data: {json.dumps({'metadata': final_metadata, 'type': 'final'})}\n\n"
                    
                    # Enregistrement CSV asynchrone pour réponse prédéfinie
                    csv_logger.log_ask_question_stream_ultra(
                        question=request.question,
                        response_chunks=response_chunks,
                        final_response=final_response,
                        confidence_score=confidence_score,
                        processing_time_ms=processing_time,
                        model_used="predefined_qa",
                        cache_hit=cache_hit,
                        stream_duration_ms=processing_time,
                        chunk_count=len(response_chunks)
                    )
                    return

            # Enhancement et recherche (si pas de réponse prédéfinie)
            llm_provider = OptimizedLLMProvider(request.provider)
            enhanced_queries = await multimodal_rag_system.query_enhancer.enhance_query(request.question, llm_provider)

            # Métadonnées initiales
            initial_metadata = {
                "id": query_id,
                "provider": request.provider.value,
                "enhanced_queries": enhanced_queries,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps({'metadata': initial_metadata, 'type': 'init'})}\n\n"

            # Recherche hybride
            all_results = []
            for query_variant in enhanced_queries:
                results = await multimodal_rag_system.hybrid_search.search(query_variant, n_results=15)
                all_results.extend(results)

            if not all_results:
                yield f"data: {json.dumps({'content': 'Aucun document pertinent trouvé.', 'type': 'final'})}\n\n"
                return

            # Re-ranking
            ranked_results = multimodal_rag_system.reranker.rerank(request.question, all_results, top_k=request.top_k)

            # Préparation contexte
            context_parts = [f"Source {i + 1}: {result.content}" for i, result in enumerate(ranked_results)]
            context = "\n\n".join(context_parts)

            # Prompt optimisé
            optimized_prompt = f"""Contexte: {context}

Question: {request.question}

Répondez en utilisant uniquement le contexte fourni. Citez les sources quand approprié.

Réponse:"""

            # Streaming de la génération
            provider = OptimizedLLMProvider(request.provider)
            
            # Collecte des chunks pour le CSV
            async for chunk in provider.generate_stream(optimized_prompt):
                if chunk:
                    response_chunks.append(chunk)
                    final_response += chunk
                    yield f"data: {json.dumps({'content': chunk, 'type': 'chunk'})}\n\n"
            
            # Données pour CSV
            sources = [result.content[:100] + "..." for result in ranked_results]
            cache_hit = False  # RAG normal n'utilise pas le cache

            # Métadonnées finales
            end_time = time.time()
            processing_time = round((end_time - start_time) * 1000, 2)
            stream_duration = processing_time
            final_metadata = {
                "response_time_ms": processing_time,
                "search_results": len(all_results),
                "ranked_results": len(ranked_results)
            }
            yield f"data: {json.dumps({'metadata': final_metadata, 'type': 'final'})}\n\n"
            
            # Enregistrement CSV asynchrone pour RAG normal
            csv_logger.log_ask_question_stream_ultra(
                question=request.question,
                response_chunks=response_chunks,
                final_response=final_response,
                sources=sources,
                processing_time_ms=processing_time,
                model_used=request.provider.value,
                cache_hit=cache_hit,
                stream_duration_ms=stream_duration,
                chunk_count=len(response_chunks)
            )

        except Exception as e:
            error_message = str(e)
            processing_time = round((time.time() - start_time) * 1000, 2)
            
            # Enregistrement CSV de l'erreur
            csv_logger.log_ask_question_stream_ultra(
                question=request.question,
                response_chunks=response_chunks,
                final_response=final_response,
                processing_time_ms=processing_time,
                model_used=request.provider.value,
                error_message=error_message,
                chunk_count=len(response_chunks)
            )
            
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"

    return StreamingResponse(
        generate_ultra_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.post("/clear-cache", summary="Vider le cache")
async def clear_cache():
    """Vider tous les caches"""
    try:
        # Vider le cache local
        cache.memory_cache.clear()

        # Vider Redis si disponible
        if REDIS_AVAILABLE:
            from app.core.cache import redis_client
            redis_client.flushdb()

        return {
            "status": "success",
            "message": "Cache vidé avec succès",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur vidage cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-multimodal-document", summary="Upload document multimodal")
async def upload_multimodal_document(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        extract_text: bool = True,
        generate_captions: bool = True
):
    """Upload de document multimodal (texte, image, mixte)"""

    # Vérification du type de fichier
    file_ext = Path(file.filename).suffix.lower()
    supported_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Acceptés: {', '.join(supported_extensions)}"
        )

    try:
        file_content = await file.read()

        result = await multimodal_rag_system.add_multimodal_document(
            file_content,
            file.filename,
            extract_text,
            generate_captions
        )

        return result

    except Exception as e:
        logger.error(f"Erreur upload multimodal: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/ask-multimodal-question", summary="Question multimodale")
async def ask_multimodal_question(request: MultimodalQuestionRequest):
    """Question avec recherche multimodale (texte + images)"""

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    start_time = time.time()
    error_message = None

    try:
        result = await multimodal_rag_system.multimodal_query(
            query=request.question,
            provider=request.provider,
            content_types=request.content_types,
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Enregistrement CSV asynchrone
        processing_time = (time.time() - start_time) * 1000
        csv_logger.log_ask_multimodal_question(
            question=request.question,
            images_count=len([ct for ct in request.content_types if ct == ContentType.IMAGE]),
            response=result.get("answer", ""),
            sources=[source.get("content", "")[:100] + "..." for source in result.get("sources", [])],
            confidence_score=result.get("confidence", None),
            processing_time_ms=processing_time,
            tokens_used=result.get("tokens_used", None),
            model_used=request.provider.value,
            cache_hit=result.get("cache_hit", None),
            multimodal_analysis=result.get("multimodal_analysis", None)
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        
        # Enregistrement CSV de l'erreur
        processing_time = (time.time() - start_time) * 1000
        csv_logger.log_ask_multimodal_question(
            question=request.question,
            images_count=len([ct for ct in request.content_types if ct == ContentType.IMAGE]),
            processing_time_ms=processing_time,
            model_used=request.provider.value,
            error_message=error_message
        )
        
        logger.error(f"Erreur question multimodale: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/ask-multimodal-with-image", summary="Question avec image de requête")
async def ask_multimodal_with_image(
        question: str = Form(...),
        provider: Provider = Form(Provider.MISTRAL),
        top_k: int = Form(3),
        temperature: float = Form(0.3),
        max_tokens: int = Form(512),
        query_image: UploadFile = File(None)
):
    """Question multimodale avec image de requête optionnelle"""

    if not question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    start_time = time.time()
    error_message = None
    query_image_pil = None

    try:
        # Traitement de l'image de requête si fournie
        if query_image and query_image.filename:
            # Vérification du type d'image
            if not multimodal_rag_system.multimodal_processor.is_image_file(query_image.filename):
                raise HTTPException(status_code=400, detail="Format d'image non supporté")

            image_content = await query_image.read()
            query_image_pil = Image.open(BytesIO(image_content))
            if query_image_pil.mode != 'RGB':
                query_image_pil = query_image_pil.convert('RGB')

        result = await multimodal_rag_system.multimodal_query(
            question=question,
            provider=provider,
            content_types=[ContentType.DOCUMENT, ContentType.IMAGE],
            query_image=query_image_pil,
            top_k=top_k,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Ajout d'informations sur l'image de requête
        result["query_had_image"] = query_image_pil is not None
        if query_image_pil:
            result["query_image_info"] = {
                "filename": query_image.filename,
                "size": query_image_pil.size,
                "mode": query_image_pil.mode
            }

        # Enregistrement CSV asynchrone
        processing_time = (time.time() - start_time) * 1000
        csv_logger.log_ask_multimodal_with_image(
            question=question,
            query_image_filename=query_image.filename if query_image and query_image.filename else None,
            query_image_size=f"{query_image_pil.size[0]}x{query_image_pil.size[1]}" if query_image_pil else None,
            query_image_format=query_image_pil.mode if query_image_pil else None,
            image_analysis=result.get("image_analysis", None),
            response=result.get("answer", ""),
            sources=[source.get("content", "")[:100] + "..." for source in result.get("sources", [])],
            confidence_score=result.get("confidence", None),
            processing_time_ms=processing_time,
            tokens_used=result.get("tokens_used", None),
            model_used=provider.value,
            cache_hit=result.get("cache_hit", None),
            ocr_text=result.get("ocr_text", None),
            image_caption=result.get("image_caption", None)
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        
        # Enregistrement CSV de l'erreur
        processing_time = (time.time() - start_time) * 1000
        csv_logger.log_ask_multimodal_with_image(
            question=question,
            query_image_filename=query_image.filename if query_image and query_image.filename else None,
            query_image_size=f"{query_image_pil.size[0]}x{query_image_pil.size[1]}" if query_image_pil else None,
            query_image_format=query_image_pil.mode if query_image_pil else None,
            processing_time_ms=processing_time,
            model_used=provider.value,
            error_message=error_message
        )
        
        logger.error(f"Erreur question avec image: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/documents-advanced", summary="Liste documents avec métadonnées")
async def list_documents_advanced():
    """Liste avancée des documents avec statistiques"""
    try:
        results = multimodal_rag_system.collection.get()

        document_stats = {}
        total_chunks = 0

        for metadata in results.get("metadatas", []):
            if metadata and "document_id" in metadata:
                doc_id = metadata["document_id"]

                if doc_id not in document_stats:
                    document_stats[doc_id] = {
                        "document_id": doc_id,
                        "total_chunks": 0,
                        "chunk_types": {},
                        "total_length": 0
                    }

                document_stats[doc_id]["total_chunks"] += 1
                total_chunks += 1

                chunk_type = metadata.get("chunk_type", "unknown")
                if chunk_type not in document_stats[doc_id]["chunk_types"]:
                    document_stats[doc_id]["chunk_types"][chunk_type] = 0
                document_stats[doc_id]["chunk_types"][chunk_type] += 1

                document_stats[doc_id]["total_length"] += metadata.get("chunk_length", 0)

        return {
            "documents": list(document_stats.values()),
            "summary": {
                "total_documents": len(document_stats),
                "total_chunks": total_chunks,
                "average_chunks_per_doc": round(total_chunks / max(len(document_stats), 1), 2)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/multimodal-documents", summary="Liste documents multimodaux")
async def list_multimodal_documents():
    """Liste des documents avec informations multimodales"""
    try:
        results = multimodal_rag_system.collection.get()

        document_stats = {}
        total_chunks = 0
        image_documents = 0
        text_documents = 0

        for metadata in results.get("metadatas", []):
            if metadata and "document_id" in metadata:
                doc_id = metadata["document_id"]
                content_type = metadata.get("content_type", "text")

                if doc_id not in document_stats:
                    document_stats[doc_id] = {
                        "document_id": doc_id,
                        "content_type": content_type,
                        "total_chunks": 0,
                        "chunk_types": {},
                        "total_length": 0,
                        "has_images": content_type == ContentType.IMAGE.value,
                        "has_captions": False,
                        "has_ocr_text": False,
                        "modalities": set()
                    }

                # Mise à jour des statistiques
                document_stats[doc_id]["total_chunks"] += 1
                total_chunks += 1

                # Informations multimodales
                if content_type == ContentType.IMAGE.value:
                    document_stats[doc_id]["has_captions"] = metadata.get("caption", "") != ""
                    document_stats[doc_id]["has_ocr_text"] = metadata.get("has_ocr_text", False)

                modality = metadata.get("modality", ModalityType.TEXT.value)
                document_stats[doc_id]["modalities"].add(modality)

                chunk_type = metadata.get("chunk_type", "unknown")
                if chunk_type not in document_stats[doc_id]["chunk_types"]:
                    document_stats[doc_id]["chunk_types"][chunk_type] = 0
                document_stats[doc_id]["chunk_types"][chunk_type] += 1

                document_stats[doc_id]["total_length"] += metadata.get("chunk_length", 0)

        # Conversion des sets en listes pour JSON
        for doc_id in document_stats:
            document_stats[doc_id]["modalities"] = list(document_stats[doc_id]["modalities"])
            if document_stats[doc_id]["content_type"] == ContentType.IMAGE.value:
                image_documents += 1
            else:
                text_documents += 1

        return {
            "documents": list(document_stats.values()),
            "summary": {
                "total_documents": len(document_stats),
                "total_chunks": total_chunks,
                "image_documents": image_documents,
                "text_documents": text_documents,
                "average_chunks_per_doc": round(total_chunks / max(len(document_stats), 1), 2),
                "multimodal_capabilities": {
                    "supports_images": True,
                    "supports_ocr": True,
                    "supports_captions": True,
                    "supports_hybrid_search": True
                }
            }
        }

    except Exception as e:
        logger.error(f"Erreur liste documents multimodaux: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.delete("/documents/{document_id}", summary="Suppression avancée document")
async def delete_document_advanced(document_id: str):
    """Suppression avancée avec nettoyage complet"""
    try:
        # Suppression de ChromaDB
        multimodal_rag_system.collection.delete(where={"document_id": document_id})

        # Reconstruction index BM25
        await asyncio.get_event_loop().run_in_executor(
            multimodal_rag_system.executor,
            multimodal_rag_system.hybrid_search.rebuild_index
        )

        return {
            "message": f"Document '{document_id}' supprimé avec succès",
            "actions": [
                "Suppression chunks ChromaDB",
                "Reconstruction index BM25",
                "Nettoyage cache"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression: {str(e)}")


@router.get("/multimodal-capabilities", summary="Capacités multimodales")
async def get_multimodal_capabilities():
    """Information sur les capacités multimodales du système"""

    try:
        # S'assurer que les composants multimodaux sont initialisés
        multimodal_rag_system._ensure_multimodal_components()
        
        # Test des modèles
        models_status = {}

        # Test CLIP
        try:
            multimodal_rag_system.multimodal_embeddings.multimodal_models._load_clip()
            models_status["clip"] = "loaded"
        except Exception as e:
            models_status["clip"] = f"error: {str(e)}"

        # Test BLIP
        try:
            multimodal_rag_system.multimodal_embeddings.multimodal_models._load_blip()
            models_status["blip"] = "loaded"
        except Exception as e:
            models_status["blip"] = f"error: {str(e)}"

        # Test OCR
        try:
            # Test simple d'OCR avec une image factice
            test_image = Image.new('RGB', (100, 50), color='white')
            multimodal_rag_system.multimodal_embeddings.multimodal_models.extract_text_from_image(test_image)
            models_status["ocr"] = "available"
        except Exception as e:
            models_status["ocr"] = f"error: {str(e)}"

        return {
            "multimodal_enabled": True,
            "supported_modalities": [e.value for e in ModalityType],
            "supported_content_types": [e.value for e in ContentType],
            "supported_image_formats": list(multimodal_rag_system.multimodal_processor.supported_image_types),
            "models_status": models_status,
            "features": {
                "image_search": True,
                "text_extraction_ocr": True,
                "image_captioning": True,
                "hybrid_text_image_search": True,
                "cross_modal_retrieval": True,
                "query_with_image": True
            },
            "device": multimodal_rag_system.multimodal_embeddings.multimodal_models.device,
            "models_info": {
                "clip_model": settings.MULTIMODAL_MODELS["clip"],
                "blip_model": settings.MULTIMODAL_MODELS["blip"],
                "embedding_model": settings.MULTIMODAL_MODELS["text_embedding"]
            }
        }

    except Exception as e:
        logger.error(f"Erreur capacités multimodales: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/analyze-image", summary="Analyse d'image standalone")
async def analyze_image(file: UploadFile = File(...)):
    """Analyse complète d'une image sans l'ajouter à la base"""

    if not multimodal_rag_system.multimodal_processor.is_image_file(file.filename):
        raise HTTPException(status_code=400, detail="Format d'image non supporté")

    try:
        image_content = await file.read()

        # Traitement de l'image
        image_data = multimodal_rag_system.multimodal_processor.process_image_document(
            image_content,
            file.filename
        )

        return {
            "filename": file.filename,
            "analysis": {
                "caption": image_data["caption"],
                "ocr_text": image_data["ocr_text"],
                "has_text": len(image_data["ocr_text"].strip()) > 10,
                "image_size": image_data["metadata"]["image_size"],
                "image_mode": image_data["metadata"]["image_mode"]
            },
            "searchable_content": image_data["content"],
            "metadata": image_data["metadata"]
        }

    except Exception as e:
        logger.error(f"Erreur analyse image: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/search-by-image", summary="Recherche par similarité d'image")
async def search_by_image(
        file: UploadFile = File(...),
        top_k: int = Form(5)
):
    """Recherche de documents similaires à une image donnée"""

    if not multimodal_rag_system.multimodal_processor.is_image_file(file.filename):
        raise HTTPException(status_code=400, detail="Format d'image non supporté")

    try:
        image_content = await file.read()
        query_image = Image.open(BytesIO(image_content))
        if query_image.mode != 'RGB':
            query_image = query_image.convert('RGB')

        # Recherche par similarité d'image
        results = await multimodal_rag_system.hybrid_search.multimodal_search(
            query="",  # Pas de requête textuelle
            query_image=query_image,
            content_types=[ContentType.IMAGE],
            n_results=top_k
        )

        # Formatage des résultats
        formatted_results = []
        for i, result in enumerate(results):
            formatted_results.append({
                "rank": i + 1,
                "score": float(result.score),
                "document_id": result.metadata.get("document_id", "unknown"),
                "filename": result.metadata.get("filename", "unknown"),
                "caption": result.metadata.get("caption", ""),
                "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "metadata": result.metadata
            })

        return {
            "query_image": {
                "filename": file.filename,
                "size": query_image.size,
                "mode": query_image.mode
            },
            "results": formatted_results,
            "total_found": len(formatted_results)
        }

    except Exception as e:
        logger.error(f"Erreur recherche par image: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/health-multimodal", summary="Health check multimodal")
async def health_check_multimodal():
    """Health check spécifique aux fonctionnalités multimodales"""

    components_status = {
        "base_system": "healthy",
        "multimodal_embeddings": "checking",
        "clip_model": "checking",
        "blip_model": "checking",
        "ocr_system": "checking"
    }

    try:
        # Test embeddings multimodaux
        test_embedding = multimodal_rag_system.multimodal_embeddings.embed_multimodal_text("test")
        components_status["multimodal_embeddings"] = "healthy"
    except Exception as e:
        components_status["multimodal_embeddings"] = f"error: {str(e)}"

    # Test CLIP (lazy loading)
    try:
        multimodal_rag_system.multimodal_embeddings.multimodal_models._load_clip()
        components_status["clip_model"] = "loaded"
    except Exception as e:
        components_status["clip_model"] = f"error: {str(e)}"

    # Test BLIP (lazy loading)
    try:
        multimodal_rag_system.multimodal_embeddings.multimodal_models._load_blip()
        components_status["blip_model"] = "loaded"
    except Exception as e:
        components_status["blip_model"] = f"error: {str(e)}"

    # Test OCR
    try:
        test_image = Image.new('RGB', (100, 50), color='white')
        multimodal_rag_system.multimodal_embeddings.multimodal_models.extract_text_from_image(test_image)
        components_status["ocr_system"] = "available"
    except Exception as e:
        components_status["ocr_system"] = f"error: {str(e)}"

    # Statut global
    all_healthy = all("error" not in status for status in components_status.values())

    return {
        "status": "healthy" if all_healthy else "partial",
        "service": "Multimodal RAG API",
        "components": components_status,
        "multimodal_features": {
            "image_processing": components_status["clip_model"] == "loaded" and components_status[
                "blip_model"] == "loaded",
            "ocr_available": "error" not in components_status["ocr_system"],
            "hybrid_search": components_status["multimodal_embeddings"] == "healthy"
        },
        "device": multimodal_rag_system.multimodal_embeddings.multimodal_models.device
    }


@router.get("/multimodal", summary="API RAG Multimodal Info")
async def multimodal_info():
    return {
        "message": "CSS ChatBot",
        "version": "2005.0.1",
        "features": [
            "Recherche hybride Dense+Sparse multimodale",
            "Support images (JPEG, PNG, GIF, BMP, TIFF, WebP)",
            "OCR avec extraction de texte des images",
            "Génération de descriptions d'images (BLIP)",
            "Recherche par similarité d'image (CLIP)",
            "Recherche croisée texte-image",
            "Re-ranking avec Cross-Encoder",
            "Query Enhancement intelligent",
            "Cache multicouche Redis+Mémoire",
            "Embeddings multimodaux avancés",
            "Chunking sémantique adaptatif",
            "Monitoring Prometheus",
            "Support multi-provider LLM",
            "Streaming responses"
        ],
        "supported_modalities": [e.value for e in ModalityType],
        "supported_content_types": [e.value for e in ContentType],
        "providers": [p.value for p in Provider],
        "endpoints": {
            "document_upload": "/upload-multimodal-document",
            "text_question": "/ask-multimodal-question",
            "image_question": "/ask-multimodal-with-image",
            "image_analysis": "/analyze-image",
            "image_search": "/search-by-image",
            "document_list": "/multimodal-documents",
            "capabilities": "/multimodal-capabilities",
            "health": "/health-multimodal"
        }
    }
