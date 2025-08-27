from sentence_transformers import CrossEncoder
from typing import List
from dataclasses import dataclass

from app.core.cache import cache
from app.utils.logging import logger


@dataclass
class RankedResult:
    content: str
    score: float
    metadata: dict
    original_rank: int


# Re-ranking avancé
class AdvancedReranker:
    def __init__(self):
        # Modèle de re-ranking haute performance
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
        self.rerank_cache = {}

    def rerank(self, query: str, results: List, top_k: int = 5) -> List[RankedResult]:
        """Re-ranking des résultats avec cross-encoder"""
        if not results:
            return []

        # Vérification du cache
        cache_key = f"{query}_{len(results)}_{hash(tuple(r.content[:50] for r in results))}"
        cached = cache.get(cache_key, "rerank")
        if cached:
            return cached[:top_k]

        try:
            # Préparation des paires query-document
            pairs = [(query, result.content) for result in results]

            # Scoring avec cross-encoder
            cross_scores = self.reranker.predict(pairs)

            # Combinaison des scores (retrieval + reranking)
            final_results = []
            for i, (result, cross_score) in enumerate(zip(results, cross_scores)):
                # Score final: pondération retrieval (30%) + cross-encoder (70%)
                final_score = 0.3 * result.score + 0.7 * cross_score

                final_results.append(RankedResult(
                    content=result.content,
                    score=final_score,
                    metadata=result.metadata,
                    original_rank=i
                ))

            # Tri par score final
            ranked_results = sorted(final_results, key=lambda x: x.score, reverse=True)

            # Cache du résultat
            cache.set(cache_key, ranked_results, ttl=1800, cache_type="rerank")

            return ranked_results[:top_k]

        except Exception as e:
            # Import local pour éviter les problèmes de portée
            from app.utils.logging import logger
            logger.error(f"Erreur re-ranking: {e}")
            # Fallback: retour des résultats originaux
            fallback_results = [
                RankedResult(
                    content=result.content,
                    score=result.score,
                    metadata=result.metadata,
                    original_rank=i
                )
                for i, result in enumerate(results)
            ]
            return sorted(fallback_results, key=lambda x: x.score, reverse=True)[:top_k]
