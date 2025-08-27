import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Union
from PIL import Image

from app.core.multimodal_models import MultimodalModels
from app.core.config import settings
from app.utils.logging import logger
from app.core.cache import cache


class MultimodalEmbeddings:
    """Classe pour gérer les embeddings multimodaux (texte + images)"""
    
    def __init__(self):
        # Modèle d'embeddings textuels multimodaux
        try:
            self.text_model = SentenceTransformer(
                settings.MULTIMODAL_MODELS["text_embedding"],
                device='cpu',
                cache_folder='./.cache/sentence_transformers'
            )
            logger.info(f"Modèle d'embeddings multimodaux chargé: {settings.MULTIMODAL_MODELS['text_embedding']}")
        except Exception as e:
            logger.error(f"Erreur chargement modèle embeddings multimodaux: {e}")
            # Fallback sur un modèle standard
            self.text_model = SentenceTransformer('all-mpnet-base-v2')
        
        # Modèles multimodaux (CLIP, BLIP, OCR)
        self.multimodal_models = MultimodalModels()
        
    def embed_multimodal_text(self, text: str) -> np.ndarray:
        """Embedding de texte avec le modèle multimodal"""
        try:
            return self.text_model.encode([text])[0]
        except Exception as e:
            logger.error(f"Erreur embedding texte multimodal: {e}")
            raise
    
    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Embedding d'image avec CLIP"""
        try:
            return self.multimodal_models.encode_image(image)
        except Exception as e:
            logger.error(f"Erreur embedding image: {e}")
            raise
    
    def embed_text_for_image_search(self, text: str) -> np.ndarray:
        """Embedding de texte pour recherche d'images avec CLIP"""
        try:
            return self.multimodal_models.encode_text_for_image(text)
        except Exception as e:
            logger.error(f"Erreur embedding texte pour recherche image: {e}")
            raise
    
    def embed_documents_multimodal(self, texts: List[str], use_cache: bool = True) -> List[np.ndarray]:
        """Embedding de documents avec cache intelligent"""
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if use_cache:
                cached = cache.get(text, "multimodal_embeddings")
                if cached is not None:
                    embeddings.append(cached)
                    continue
            
            uncached_texts.append(text)
            uncached_indices.append(i)
            embeddings.append(None)  # Placeholder
        
        # Traitement par batch des textes non cachés
        if uncached_texts:
            new_embeddings = self.text_model.encode(uncached_texts)
            
            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding
                if use_cache:
                    cache.set(uncached_texts[uncached_indices.index(idx)],
                              embedding, cache_type="multimodal_embeddings")
        
        return embeddings
    
    def generate_image_caption(self, image: Image.Image) -> str:
        """Génération de description d'image avec BLIP"""
        try:
            return self.multimodal_models.generate_image_caption(image)
        except Exception as e:
            logger.error(f"Erreur génération caption: {e}")
            return ""
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extraction de texte d'image avec OCR"""
        try:
            return self.multimodal_models.extract_text_from_image(image)
        except Exception as e:
            logger.error(f"Erreur extraction texte OCR: {e}")
            return ""