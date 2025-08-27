import torch
from PIL import Image
import pytesseract
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers import CLIPProcessor, CLIPModel
import numpy as np

from app.core.config import settings
from app.utils.logging import logger


# Classe pour gérer les modèles multimodaux
class MultimodalModels:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.models_loaded = {}
        logger.info(f"Utilisation du device: {self.device}")

        # Lazy loading des modèles
        self._clip_model = None
        self._clip_processor = None
        self._blip_model = None
        self._blip_processor = None

    def _load_clip(self):
        """Chargement lazy du modèle CLIP"""
        if self._clip_model is None:
            try:
                self._clip_model = CLIPModel.from_pretrained(settings.MULTIMODAL_MODELS["clip"])
                self._clip_processor = CLIPProcessor.from_pretrained(settings.MULTIMODAL_MODELS["clip"])
                self._clip_model.to(self.device)
                logger.info("Modèle CLIP chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur chargement CLIP: {e}")
                raise

    def _load_blip(self):
        """Chargement lazy du modèle BLIP"""
        if self._blip_model is None:
            try:
                self._blip_processor = BlipProcessor.from_pretrained(settings.MULTIMODAL_MODELS["blip"])
                self._blip_model = BlipForConditionalGeneration.from_pretrained(settings.MULTIMODAL_MODELS["blip"])
                self._blip_model.to(self.device)
                logger.info("Modèle BLIP chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur chargement BLIP: {e}")
                raise

    def encode_image(self, image: Image.Image) -> np.ndarray:
        """Encodage d'image avec CLIP"""
        self._load_clip()
        inputs = self._clip_processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            image_features = self._clip_model.get_image_features(**inputs)
        return image_features.cpu().numpy()[0]

    def _truncate_text_for_clip(self, text: str, max_tokens: int = 77) -> str:
        """Tronque le texte pour respecter la limite de tokens CLIP"""
        # Approximation simple: 1 token ≈ 4 caractères pour la plupart des langues
        # On garde une marge de sécurité
        max_chars = max_tokens * 3
        if len(text) <= max_chars:
            return text

        # Tronquer en gardant les mots entiers
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated + "..."

    def encode_text_for_image(self, text: str) -> np.ndarray:
        """Encodage de texte pour recherche multimodale avec CLIP"""
        self._load_clip()
        # Tronquer le texte pour respecter la limite de 77 tokens
        truncated_text = self._truncate_text_for_clip(text)
        inputs = self._clip_processor(text=[truncated_text], return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            text_features = self._clip_model.get_text_features(**inputs)
        return text_features.cpu().numpy()[0]

    def generate_image_caption(self, image: Image.Image) -> str:
        """Génération de description d'image avec BLIP"""
        self._load_blip()
        inputs = self._blip_processor(image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self._blip_model.generate(**inputs, max_length=100, num_beams=5)
        caption = self._blip_processor.decode(out[0], skip_special_tokens=True)
        return caption

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extraction de texte avec OCR"""
        try:
            # Configuration OCR pour le français
            custom_config = r'--oem 3 --psm 6 -l fra+eng'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text.strip()
        except Exception as e:
            logger.error(f"Erreur OCR: {e}")
            return ""
