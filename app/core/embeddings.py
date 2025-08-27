import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
from functools import lru_cache

from app.core.cache import cache
from app.utils.logging import logger


# Modèles d'embeddings avancés
class AdvancedEmbeddings:
    def __init__(self):
        try:
            # Modèle principal optimisé
            self.primary_model = SentenceTransformer(
                'all-mpnet-base-v2',
                device='cpu',
                cache_folder='./.cache/sentence_transformers'
            )
            logger.info("Modèle principal all-mpnet-base-v2 chargé")

            # Modèle multilingue en lazy loading (chargé seulement si nécessaire)
            self.multilingual_model = None
            self._multilingual_loaded = False

        except Exception as e:
            logger.error(f"Erreur chargement modèles: {e}")
            # Fallback sur un modèle plus léger
            self.primary_model = SentenceTransformer('all-MiniLM-L6-v2')

    def _load_multilingual_if_needed(self):
        """Chargement lazy du modèle multilingue"""
        if not self._multilingual_loaded:
            try:
                self.multilingual_model = SentenceTransformer(
                    'paraphrase-multilingual-mpnet-base-v2',
                    device='cpu',
                    cache_folder='./.cache/sentence_transformers'
                )
                self._multilingual_loaded = True
                logger.info("Modèle multilingue chargé")
            except Exception as e:
                logger.error(f"Erreur chargement modèle multilingue: {e}")
                self.multilingual_model = None

    @lru_cache(maxsize=5000)
    def embed_query(self, text: str) -> np.ndarray:
        """Cache des embeddings de requêtes avec LRU"""
        return self.primary_model.encode([text])[0]

    def embed_documents(self, texts: List[str], use_cache: bool = True) -> List[np.ndarray]:
        """Embedding de documents avec cache intelligent"""
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if use_cache:
                cached = cache.get(text, "embeddings")
                if cached is not None:
                    embeddings.append(cached)
                    continue

            uncached_texts.append(text)
            uncached_indices.append(i)
            embeddings.append(None)  # Placeholder

        # Traitement par batch des textes non cachés
        if uncached_texts:
            new_embeddings = self.primary_model.encode(uncached_texts)

            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding
                if use_cache:
                    cache.set(uncached_texts[uncached_indices.index(idx)],
                              embedding, cache_type="embeddings")

        return embeddings
