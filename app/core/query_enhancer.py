from typing import List
from app.core.cache import cache
from app.utils.logging import logger


# Query Enhancement
class QueryEnhancer:
    def __init__(self):
        self.enhancement_cache = {}

    async def enhance_query(self, query: str, provider_instance) -> List[str]:
        """Génération de variantes de requête pour améliorer la recherche"""
        # Vérification du cache
        cached = cache.get(query, "query_enhancement")
        if cached:
            return cached

        try:
            enhancement_prompt = f"""Vous êtes un expert en reformulation de requêtes pour améliorer la recherche documentaire.

Requête originale: "{query}"

Générez 2 variantes de cette requête qui:
1. Utilisent des synonymes et termes alternatifs
2. Reformulent la question sous un angle différent
3. Sont plus spécifiques ou plus générales selon le contexte

Répondez uniquement avec les 2 variantes, une par ligne, sans numérotation ni formatage:"""

            enhanced_text = await provider_instance.generate_response(enhancement_prompt)

            # Parsing des variantes
            variants = [line.strip() for line in enhanced_text.split('\n') if line.strip()]
            variants = [v for v in variants if len(v) > 10]  # Filtrage des variantes trop courtes

            # Inclure la requête originale
            all_queries = [query] + variants[:2]  # Maximum 3 requêtes au total

            # Cache du résultat
            cache.set(query, all_queries, ttl=3600, cache_type="query_enhancement")

            return all_queries

        except Exception as e:
            logger.error(f"Erreur query enhancement: {e}")
            return [query]  # Fallback sur la requête originale
