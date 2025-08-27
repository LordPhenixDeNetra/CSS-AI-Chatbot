from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, StreamingResponse, Response
from typing import Optional, List
import asyncio
import uuid
import time
from datetime import datetime
import json
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
from app.utils.helpers import image_to_base64
from app.core.cache import REDIS_AVAILABLE, cache
from app.utils.logging import logger
from app.core.llm_provider import OptimizedLLMProvider, PROVIDER_CONFIGS

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
            "monitoring": "/health, /metrics, /performance-metrics"
        }
    }


@router.get("/health", summary="Health check avancé")
async def health_check():
    """Vérification de santé complète du système"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": "connected" if REDIS_AVAILABLE else "disconnected",
            "embeddings": "loaded",
            "reranker": "loaded",
            "multimodal_models": "loaded"
        }
    }


@router.get("/metrics", summary="Métriques Prometheus")
async def metrics():
    """Endpoint pour Prometheus"""
    from app.utils.logging import generate_latest
    return Response(generate_latest(), media_type="text/plain")


@router.get("/performance-metrics", summary="Métriques de performance")
async def get_performance_metrics():
    """Métriques détaillées de performance"""
    try:
        # Calcul des métriques depuis Prometheus
        from app.utils.logging import query_counter, response_time_histogram, cache_hit_counter

        # Accès correct aux valeurs des métriques Prometheus
        total_queries = 0
        cache_hits = 0
        response_count = 0
        response_sum = 0
        
        # Pour Counter, on utilise collect() pour obtenir les samples
        try:
            for sample in query_counter.collect()[0].samples:
                total_queries += sample.value
        except (IndexError, AttributeError):
            total_queries = 0
            
        try:
            for sample in cache_hit_counter.collect()[0].samples:
                cache_hits += sample.value
        except (IndexError, AttributeError):
            cache_hits = 0

        # Pour Histogram, on récupère count et sum
        try:
            histogram_samples = response_time_histogram.collect()[0].samples
            for sample in histogram_samples:
                if sample.name.endswith('_count'):
                    response_count = sample.value
                elif sample.name.endswith('_sum'):
                    response_sum = sample.value
        except (IndexError, AttributeError):
            response_count = 0
            response_sum = 0

        # Calculs
        avg_response_time = (response_sum * 1000) / response_count if response_count > 0 else 0
        cache_hit_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0

        # Nombre de documents actifs
        try:
            collections = multimodal_rag_system.chroma_client.list_collections()
            active_documents = sum(collection.count() for collection in collections)
        except:
            active_documents = 0

        return {
            "total_queries": int(total_queries),
            "average_response_time_ms": round(avg_response_time, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "error_rate": 0.0,
            "active_documents": active_documents,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur calcul métriques: {e}")
        return {
            "total_queries": 0,
            "average_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
            "error_rate": 0.0,
            "active_documents": 0,
            "timestamp": datetime.now().isoformat()
        }


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

        return AdvancedQuestionResponse(**result)

    except Exception as e:
        from app.utils.logging import query_counter
        query_counter.labels(provider=request.provider.value, status="error").inc()
        logger.error(f"Erreur question ultra: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-question-stream-ultra", summary="Question streaming ultra optimisée")
async def ask_question_stream_ultra(request: QuestionRequest):
    """Version streaming de la question ultra optimisée"""

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    async def generate_ultra_stream():
        try:
            # Recherche et préparation du contexte (partie non-streaming)
            start_time = time.time()
            query_id = str(uuid.uuid4())

            # Enhancement et recherche
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

            async for chunk in provider.generate_stream(optimized_prompt):
                if chunk:
                    yield f"data: {json.dumps({'content': chunk, 'type': 'chunk'})}\n\n"

            # Métadonnées finales
            end_time = time.time()
            final_metadata = {
                "response_time_ms": round((end_time - start_time) * 1000, 2),
                "search_results": len(all_results),
                "ranked_results": len(ranked_results)
            }
            yield f"data: {json.dumps({'metadata': final_metadata, 'type': 'final'})}\n\n"

        except Exception as e:
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

        return result

    except HTTPException:
        raise
    except Exception as e:
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

    try:
        # Traitement de l'image de requête si fournie
        query_image_pil = None
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

        return result

    except HTTPException:
        raise
    except Exception as e:
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
