#!/usr/bin/env python3
"""
Script de débogage pour identifier l'origine de l'erreur logger
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.reranker import AdvancedReranker
from app.core.search import SearchResult
from app.utils.logging import logger


def test_reranker():
    """Test du reranker pour reproduire l'erreur logger"""
    print("Test du reranker...")

    try:
        reranker = AdvancedReranker()

        # Créer des résultats de test
        test_results = [
            SearchResult(
                content="Test document 1",
                score=0.8,
                metadata={"id": "1"},
                source_type="dense"
            ),
            SearchResult(
                content="Test document 2",
                score=0.6,
                metadata={"id": "2"},
                source_type="sparse"
            )
        ]

        # Tester le reranking
        query = "test query"
        ranked_results = reranker.rerank(query, test_results, top_k=2)

        print(f"Reranking réussi: {len(ranked_results)} résultats")

    except Exception as e:
        print(f"Erreur dans test_reranker: {e}")
        import traceback
        traceback.print_exc()


def test_cache():
    """Test du cache pour reproduire l'erreur logger"""
    print("Test du cache...")

    try:
        from app.core.cache import cache

        # Test get/set
        cache.set("test_key", "test_value", cache_type="test")
        result = cache.get("test_key", cache_type="test")

        print(f"Cache test réussi: {result}")

    except Exception as e:
        print(f"Erreur dans test_cache: {e}")
        import traceback
        traceback.print_exc()


def test_query_enhancer():
    """Test du query enhancer pour reproduire l'erreur logger"""
    print("Test du query enhancer...")

    try:
        from app.core.query_enhancer import QueryEnhancer
        from app.core.llm_provider import OptimizedLLMProvider
        from app.models.enums import Provider

        enhancer = QueryEnhancer()
        provider_instance = OptimizedLLMProvider(Provider.DEEPSEEK)

        # Simuler une erreur dans enhance_query
        import asyncio

        async def test_enhance():
            try:
                result = await enhancer.enhance_query("test query", provider_instance)
                print(f"Query enhancement réussi: {result}")
            except Exception as e:
                print(f"Erreur dans enhance_query: {e}")
                import traceback
                traceback.print_exc()

        asyncio.run(test_enhance())

    except Exception as e:
        print(f"Erreur dans test_query_enhancer: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=== Test de débogage logger ===")

    # Test 1: Reranker
    test_reranker()
    print()

    # Test 2: Cache
    test_cache()
    print()

    # Test 3: Query Enhancer
    test_query_enhancer()
    print()

    print("=== Fin des tests ===")
