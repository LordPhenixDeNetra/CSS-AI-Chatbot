#!/usr/bin/env python3

import asyncio
import json
from app.models.schemas import QuestionRequest
from app.models.enums import Provider
from app.core.llm_provider import OptimizedLLMProvider
from app.services.rag_service import multimodal_rag_system


async def test_stream_debug():
    """Test pour reproduire l'erreur logger dans le streaming"""

    # Créer une requête similaire à celle qui cause l'erreur
    request = QuestionRequest(
        question="Parlez moi des prestations",
        provider=Provider.DEEPSEEK,
        temperature=0.3,
        max_tokens=512,
        top_k=3
    )

    print("=== Test de reproduction de l'erreur logger ===")
    print(f"Question: {request.question}")
    print(f"Provider: {request.provider}")

    try:
        # Reproduire exactement le même code que dans l'endpoint
        llm_provider = OptimizedLLMProvider(request.provider)
        print("✓ LLM Provider créé")

        # Enhancement et recherche
        enhanced_queries = await multimodal_rag_system.query_enhancer.enhance_query(request.question, llm_provider)
        print(f"✓ Enhanced queries: {enhanced_queries}")

        # Recherche hybride
        all_results = []
        for query_variant in enhanced_queries:
            results = await multimodal_rag_system.hybrid_search.search(query_variant, n_results=15)
            all_results.extend(results)
        print(f"✓ Recherche terminée: {len(all_results)} résultats")

        if not all_results:
            print("⚠️ Aucun résultat trouvé")
            return

        # Re-ranking
        ranked_results = multimodal_rag_system.reranker.rerank(request.question, all_results, top_k=request.top_k)
        print(f"✓ Re-ranking terminé: {len(ranked_results)} résultats")

        # Préparation contexte
        context_parts = [f"Source {i + 1}: {result.content}" for i, result in enumerate(ranked_results)]
        context = "\n\n".join(context_parts)

        # Prompt optimisé
        optimized_prompt = f"""Contexte: {context}

Question: {request.question}

Répondez en utilisant uniquement le contexte fourni. Citez les sources quand approprié.

Réponse:"""

        print("✓ Prompt préparé")

        # Test du streaming - c'est ici que l'erreur devrait se produire
        provider = OptimizedLLMProvider(request.provider)
        print("🔄 Début du streaming...")

        chunk_count = 0
        async for chunk in provider.generate_stream(optimized_prompt):
            if chunk:
                chunk_count += 1
                print(f"Chunk {chunk_count}: {chunk[:50]}...")
                if chunk_count >= 3:  # Limiter pour le test
                    break

        print("✅ Test terminé avec succès")

    except Exception as e:
        print(f"❌ Erreur détectée: {e}")
        print(f"Type d'erreur: {type(e).__name__}")
        import traceback
        print("Traceback complet:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stream_debug())
