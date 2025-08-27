import chromadb
import uuid
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from app.core.embeddings import AdvancedEmbeddings
from app.core.chunker import AdvancedChunker
from app.core.search import HybridSearch, SearchResult
from app.core.reranker import AdvancedReranker, RankedResult
from app.core.query_enhancer import QueryEnhancer
from app.core.llm_provider import OptimizedLLMProvider, PROVIDER_CONFIGS
from app.core.multimodal_models import MultimodalModels
from app.core.multimodal_embeddings import MultimodalEmbeddings
from app.core.multimodal_processor import MultimodalProcessor
from app.models.enums import Provider, ContentType, ModalityType
from app.utils.logging import logger
from app.core.cache import cache


# RAG Ultra Performant - Classe principale
class UltraPerformantRAG:
    def __init__(self):
        # Initialisation des composants
        self.embeddings = AdvancedEmbeddings()
        self.chunker = AdvancedChunker(self.embeddings)
        self.reranker = AdvancedReranker()
        self.query_enhancer = QueryEnhancer()
        
        # Composants multimodaux (chargement différé)
        self.multimodal_embeddings = None
        self.multimodal_processor = None

        # ChromaDB avec gestion d'erreurs
        try:
            self.chroma_client = chromadb.PersistentClient(
                path="./ultra_rag_db",
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Fonction d'embedding custom pour ChromaDB
            class CustomEmbeddingFunction(chromadb.EmbeddingFunction):
                def __init__(self, embeddings_model):
                    self.embeddings_model = embeddings_model

                def __call__(self, texts):
                    return self.embeddings_model.embed_documents(texts)

            self.embedding_function = CustomEmbeddingFunction(self.embeddings)

            self.collection = self.chroma_client.get_or_create_collection(
                name="ultra_documents",
                embedding_function=self.embedding_function,
            )

            logger.info("ChromaDB initialisé avec succès")

        except Exception as e:
            logger.error(f"Erreur initialisation ChromaDB: {e}")
            raise

        # Recherche hybride
        self.hybrid_search = HybridSearch(self.collection, self.embeddings)

        # Pool de threads pour opérations parallèles
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info("UltraPerformantRAG initialisé avec support multimodal")

    async def add_document(self, text: str, document_id: str) -> Dict[str, Any]:
        """Ajout optimisé d'un document avec chunking intelligent"""
        start_time = time.time()

        try:
            # Chunking sémantique
            chunks_data = self.chunker.chunk_document(text, document_id)

            # Suppression des anciens chunks du même document
            try:
                self.collection.delete(where={"document_id": document_id})
            except:
                pass

            # Préparation des données pour l'insertion
            documents = [chunk["content"] for chunk in chunks_data]
            metadatas = [chunk["metadata"] for chunk in chunks_data]
            ids = [metadata["chunk_id"] for metadata in metadatas]

            # Insertion par batch
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                self.collection.add(
                    documents=documents[i:end_idx],
                    metadatas=metadatas[i:end_idx],
                    ids=ids[i:end_idx]
                )

            # Reconstruction de l'index BM25
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.hybrid_search.rebuild_index
            )

            processing_time = time.time() - start_time

            return {
                "document_id": document_id,
                "chunks_created": len(chunks_data),
                "processing_time_ms": round(processing_time * 1000, 2),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Erreur ajout document: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur traitement document: {str(e)}")

    async def add_multimodal_document(self, file_content: bytes, filename: str, 
                                    extract_text: bool = True, 
                                    generate_captions: bool = True) -> Dict[str, Any]:
        """
        Ajoute un document multimodal (image ou PDF) au système RAG.
        
        Args:
            file_content: Contenu du fichier en bytes
            filename: Nom du fichier
            extract_text: Si True, extrait le texte des images via OCR
            generate_captions: Si True, génère des légendes pour les images
            
        Returns:
            Dict contenant les informations sur le document ajouté
        """
        try:
            logger.info(f"Ajout du document multimodal: {filename}")
            
            # Traitement du document multimodal
            processed_data = await self.multimodal_processor.process_document(
                file_content, filename, extract_text, generate_captions
            )
            
            # Génération d'un ID unique pour le document
            document_id = f"multimodal_{filename}_{hash(file_content) % 1000000}"
            
            # Ajout des chunks au système RAG
            added_chunks = []
            for i, chunk in enumerate(processed_data['chunks']):
                chunk_id = f"{document_id}_chunk_{i}"
                
                # Création des métadonnées enrichies
                metadata = {
                    'document_id': document_id,
                    'chunk_id': chunk_id,
                    'filename': filename,
                    'chunk_index': i,
                    'content_type': chunk.get('type', 'text'),
                    'modality': chunk.get('modality', 'text'),
                    'has_image': chunk.get('has_image', False),
                    'has_text': chunk.get('has_text', True),
                    'ocr_confidence': chunk.get('ocr_confidence'),
                    'caption_confidence': chunk.get('caption_confidence')
                }
                
                # Génération des embeddings multimodaux
                if chunk.get('has_image') and chunk.get('image_data'):
                    # Embedding d'image
                    image_embedding = await self.multimodal_embeddings.encode_image(chunk['image_data'])
                    embedding = image_embedding
                else:
                    # Embedding de texte
                    text_content = chunk.get('text', '')
                    if text_content:
                        embedding = await self.multimodal_embeddings.encode_text(text_content)
                    else:
                        continue  # Skip chunks without content
                
                # Ajout à ChromaDB
                self.collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[chunk.get('text', '')],
                    metadatas=[metadata],
                    ids=[chunk_id]
                )
                
                added_chunks.append({
                    'chunk_id': chunk_id,
                    'content_type': metadata['content_type'],
                    'modality': metadata['modality'],
                    'text_length': len(chunk.get('text', '')),
                    'has_image': metadata['has_image']
                })
            
            result = {
                'document_id': document_id,
                'filename': filename,
                'chunks_added': len(added_chunks),
                'chunks_details': added_chunks,
                'processing_info': {
                    'file_type': processed_data.get('file_type'),
                    'total_images': processed_data.get('total_images', 0),
                    'total_text_chunks': processed_data.get('total_text_chunks', 0),
                    'ocr_used': extract_text,
                    'captions_generated': generate_captions
                }
            }
            
            logger.info(f"Document multimodal {filename} ajouté avec succès: {len(added_chunks)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du document multimodal {filename}: {e}")
            raise

    async def multimodal_query(self, query: str, query_image: bytes = None, 
                             k: int = 5, rerank: bool = True, 
                             modality_filter: str = None) -> List[RankedResult]:
        """
        Effectue une requête multimodale sur le système RAG.
        
        Args:
            query: Requête textuelle
            query_image: Image de requête optionnelle (bytes)
            k: Nombre de résultats à retourner
            rerank: Si True, applique le reranking
            modality_filter: Filtre par modalité ('text', 'image', 'multimodal')
            
        Returns:
            Liste des résultats classés
        """
        try:
            logger.info(f"Requête multimodale: {query[:100]}...")
            
            # Génération de l'embedding de requête
            if query_image:
                # Requête avec image
                query_embedding = await self.multimodal_embeddings.encode_image(query_image)
                logger.info("Embedding d'image généré pour la requête")
            else:
                # Requête textuelle uniquement
                query_embedding = await self.multimodal_embeddings.encode_text(query)
                logger.info("Embedding textuel généré pour la requête")
            
            # Préparation des filtres de métadonnées
            where_filter = {}
            if modality_filter:
                where_filter['modality'] = modality_filter
            
            # Recherche dans ChromaDB
            search_results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(k * 2, 20),  # Récupère plus de résultats pour le reranking
                where=where_filter if where_filter else None,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Conversion en format SearchResult
            search_results_formatted = []
            for i, (doc, metadata, distance) in enumerate(zip(
                search_results['documents'][0],
                search_results['metadatas'][0], 
                search_results['distances'][0]
            )):
                search_results_formatted.append(SearchResult(
                    content=doc,
                    metadata=metadata,
                    score=1.0 - distance,  # Conversion distance -> score
                    source=metadata.get('filename', 'unknown')
                ))
            
            # Application du reranking si demandé
            if rerank and len(search_results_formatted) > 1:
                logger.info(f"Application du reranking sur {len(search_results_formatted)} résultats")
                ranked_results = await self.reranker.rerank(
                    query=query,
                    results=search_results_formatted,
                    top_k=k
                )
            else:
                # Conversion directe en RankedResult
                ranked_results = [
                    RankedResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=result.score,
                        source=result.source,
                        rank=i+1
                    )
                    for i, result in enumerate(search_results_formatted[:k])
                ]
            
            logger.info(f"Requête multimodale terminée: {len(ranked_results)} résultats")
            return ranked_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la requête multimodale: {e}")
            raise

    async def query(self, question: str, provider: Provider, top_k: int = 3, **kwargs) -> Dict[str, Any]:
        """Query ultra optimisé avec toutes les améliorations"""
        start_time = time.time()
        query_id = str(uuid.uuid4())

        try:
            # Vérification du cache complet
            cache_key = f"{question}_{provider.value}_{top_k}"
            cached_response = cache.get(cache_key, "full_response")
            if cached_response:
                return cached_response

            # 1. Provider LLM
            llm_provider = OptimizedLLMProvider(provider)

            # 2. Enhancement de la requête
            enhanced_queries = await self.query_enhancer.enhance_query(question, llm_provider)
            logger.info(f"Requêtes générées: {enhanced_queries}")

            # 3. Recherche hybride pour toutes les variantes
            all_results = []
            for query_variant in enhanced_queries:
                variant_results = await self.hybrid_search.search(
                    query_variant,
                    n_results=15
                )
                all_results.extend(variant_results)

            if not all_results:
                no_context_response = {
                    "id": query_id,
                    "answer": "Aucun document pertinent trouvé pour votre question.",
                    "context_found": False,
                    "provider_used": provider.value,
                    "model_used": PROVIDER_CONFIGS[provider]["model"],
                    "response_time_ms": round((time.time() - start_time) * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "search_results": 0,
                    "ranked_results": 0,
                    "enhanced_queries": enhanced_queries,
                    "sources": [],
                    "performance_metrics": {
                        "search_time_ms": round((time.time() - start_time) * 1000, 2),
                        "generation_time_ms": 0,
                        "cache_hits": "no_context_found"
                    }
                }
                return no_context_response

            # 4. Re-ranking avec cross-encoder
            ranked_results = self.reranker.rerank(question, all_results, top_k=top_k)

            # 5. Préparation du contexte optimisé
            context_parts = []
            sources = []

            for i, result in enumerate(ranked_results):
                context_parts.append(f"Source {i + 1}: {result.content}")
                sources.append({
                    "source_id": i + 1,
                    "score": float(result.score),
                    "original_rank": result.original_rank,
                    "metadata": result.metadata
                })

            context = "\n\n".join(context_parts)

            # 6. Prompt optimisé avec instructions spécifiques
            optimized_prompt = f"""Vous êtes un assistant expert qui répond aux questions en utilisant uniquement le contexte fourni.

CONTEXTE:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Répondez uniquement en utilisant les informations du contexte fourni
2. Si vous ne trouvez pas d'informations pertinentes, dites-le clairement
3. Citez les sources en utilisant "Source X" quand approprié
4. Soyez précis et concis
5. Si plusieurs sources contiennent des informations complémentaires, synthétisez-les

RÉPONSE:"""

            # 7. Génération de la réponse
            response_text = await llm_provider.generate_response(
                optimized_prompt,
                temperature=kwargs.get('temperature', 0.3),
                max_tokens=kwargs.get('max_tokens', 512)
            )

            # 8. Construction de la réponse finale
            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000, 2)

            final_response = {
                "id": query_id,
                "answer": response_text,
                "context_found": True,
                "provider_used": provider.value,
                "model_used": PROVIDER_CONFIGS[provider]["model"],
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat(),
                "search_results": len(all_results),
                "ranked_results": len(ranked_results),
                "enhanced_queries": enhanced_queries,
                "sources": sources,
                "performance_metrics": {
                    "search_time_ms": round((time.time() - start_time - (end_time - time.time())) * 1000, 2),
                    "generation_time_ms": round((end_time - start_time) * 1000, 2),
                    "cache_hits": "metrics_available_via_prometheus"
                }
            }

            # 9. Cache de la réponse complète
            cache.set(cache_key, final_response, ttl=1800, cache_type="full_response")

            return final_response

        except Exception as e:
            logger.error(f"Erreur query complète: {e}")
            error_response = {
                "id": query_id,
                "answer": f"Erreur lors du traitement: {str(e)}",
                "context_found": False,
                "provider_used": provider.value,
                "model_used": PROVIDER_CONFIGS.get(provider, {}).get("model", "unknown"),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now().isoformat(),
                "search_results": 0,
                "ranked_results": 0,
                "enhanced_queries": [],
                "sources": [],
                "performance_metrics": {
                    "search_time_ms": 0,
                    "generation_time_ms": round((time.time() - start_time) * 1000, 2),
                    "cache_hits": "error_occurred"
                }
            }
            return error_response

    def _ensure_multimodal_components(self):
        """Initialise les composants multimodaux si nécessaire"""
        if self.multimodal_embeddings is None:
            logger.info("Initialisation des composants multimodaux...")
            self.multimodal_embeddings = MultimodalEmbeddings()
            self.multimodal_processor = MultimodalProcessor(self.multimodal_embeddings)
            logger.info("Composants multimodaux initialisés")

    async def add_multimodal_document(self, file_content: bytes, filename: str, 
                               extract_text: bool = True, generate_captions: bool = True) -> Dict[str, Any]:
        """Ajoute un document multimodal au système RAG"""
        self._ensure_multimodal_components()
        return await self.multimodal_processor.process_multimodal_document(
            file_content, filename, extract_text, generate_captions
        )

    async def multimodal_query(self, query: str, modality: str = "text", 
                        provider: Provider = Provider.MISTRAL, **kwargs) -> Dict[str, Any]:
        """Effectue une requête multimodale"""
        self._ensure_multimodal_components()
        # Pour l'instant, on utilise la requête standard
        return await self.query(query, provider, **kwargs)


# Instance globale du RAG multimodal
multimodal_rag_system = UltraPerformantRAG()
