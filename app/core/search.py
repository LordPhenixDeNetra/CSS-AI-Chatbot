import numpy as np
from rank_bm25 import BM25Okapi
from typing import List, Optional
import hashlib
from dataclasses import dataclass

from app.utils.logging import logger


@dataclass
class SearchResult:
    content: str
    score: float
    metadata: dict
    source_type: str  # "dense", "sparse", "hybrid"


# Recherche hybride Dense + Sparse
class HybridSearch:
    def __init__(self, chroma_db, embeddings_model):
        self.chroma_db = chroma_db
        self.embeddings = embeddings_model
        self.bm25_index = None
        self.documents = []
        self.document_ids = []
        self._build_bm25_index()

    def _build_bm25_index(self):
        """Construction de l'index BM25"""
        try:
            # Récupération de tous les documents
            results = self.chroma_db.get()
            if results and results.get("documents"):
                self.documents = results["documents"]
                self.document_ids = results["ids"]

                # Tokenisation pour BM25
                tokenized_docs = [doc.lower().split() for doc in self.documents]
                self.bm25_index = BM25Okapi(tokenized_docs)

                logger.info(f"Index BM25 construit avec {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Erreur construction index BM25: {e}")

    def rebuild_index(self):
        """Reconstruction de l'index BM25"""
        self._build_bm25_index()

    async def search(self, query: str, n_results: int = 10, alpha: float = 0.7) -> List[SearchResult]:
        """Recherche hybride avec pondération dense/sparse"""
        results = []

        # 1. Recherche dense (vectorielle)
        try:
            dense_results = self.chroma_db.query(
                query_texts=[query],
                n_results=min(n_results * 2, 20)
            )

            if dense_results and dense_results.get("documents") and dense_results["documents"][0]:
                for i, (doc, distance) in enumerate(zip(
                        dense_results["documents"][0],
                        dense_results["distances"][0]
                )):
                    # Conversion distance en score
                    dense_score = 1 / (1 + distance)

                    metadata = dense_results["metadatas"][0][i] if dense_results.get("metadatas") else {}

                    results.append(SearchResult(
                        content=doc,
                        score=dense_score * alpha,
                        metadata=metadata,
                        source_type="dense"
                    ))
        except Exception as e:
            logger.error(f"Erreur recherche dense: {e}")

        # 2. Recherche sparse (BM25)
        if self.bm25_index and self.documents:
            try:
                query_tokens = query.lower().split()
                bm25_scores = self.bm25_index.get_scores(query_tokens)

                # Top résultats BM25
                top_indices = np.argsort(bm25_scores)[::-1][:n_results]

                for idx in top_indices:
                    if bm25_scores[idx] > 0:
                        sparse_score = bm25_scores[idx] * (1 - alpha)

                        results.append(SearchResult(
                            content=self.documents[idx],
                            score=sparse_score,
                            metadata={"document_id": self.document_ids[idx] if idx < len(
                                self.document_ids) else f"doc_{idx}"},
                            source_type="sparse"
                        ))
            except Exception as e:
                logger.error(f"Erreur recherche BM25: {e}")

        # 3. Combinaison et déduplication
        return self._combine_and_deduplicate(results, n_results)

    def _combine_and_deduplicate(self, results: List[SearchResult], n_results: int) -> List[SearchResult]:
        """Combinaison et déduplication des résultats"""
        # Groupement par contenu similaire
        unique_results = {}
        for result in results:
            content_hash = hashlib.md5(result.content.encode()).hexdigest()[:16]
            if content_hash not in unique_results or result.score > unique_results[content_hash].score:
                unique_results[content_hash] = result

        # Tri par score et limitation
        final_results = sorted(unique_results.values(), key=lambda x: x.score, reverse=True)
        return final_results[:n_results]
