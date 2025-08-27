import io
import uuid
from typing import Dict, Any, List, Optional
from PIL import Image
from pathlib import Path

from app.services.document_service import process_document_advanced
from app.core.multimodal_embeddings import MultimodalEmbeddings
from app.models.enums import ContentType, ModalityType
from app.utils.logging import logger


class MultimodalProcessor:
    """Classe pour traiter les documents multimodaux"""
    
    def __init__(self, multimodal_embeddings: MultimodalEmbeddings):
        self.multimodal_embeddings = multimodal_embeddings
        self.supported_image_types = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        self.supported_document_types = {'.pdf', '.doc', '.docx', '.txt'}
    
    def is_image_file(self, filename: str) -> bool:
        """Vérifie si le fichier est une image supportée"""
        return Path(filename).suffix.lower() in self.supported_image_types
    
    def is_document_file(self, filename: str) -> bool:
        """Vérifie si le fichier est un document supporté"""
        return Path(filename).suffix.lower() in self.supported_document_types
    
    async def process_multimodal_document(self, file_content: bytes, filename: str, 
                                         extract_text: bool = True, 
                                         generate_captions: bool = True) -> Dict[str, Any]:
        """Traite un document multimodal (image ou document)"""
        
        if self.is_image_file(filename):
            return self.process_image_document(file_content, filename, extract_text, generate_captions)
        elif self.is_document_file(filename):
            return await self.process_text_document(file_content, filename)
        else:
            raise ValueError(f"Type de fichier non supporté: {filename}")
    
    def process_image_document(self, image_content: bytes, filename: str, 
                              extract_text: bool = True, 
                              generate_captions: bool = True) -> Dict[str, Any]:
        """Traite un document image"""
        try:
            # Chargement de l'image
            image = Image.open(io.BytesIO(image_content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Métadonnées de base
            metadata = {
                "filename": filename,
                "content_type": ContentType.IMAGE.value,
                "modality": ModalityType.IMAGE.value,
                "image_size": image.size,
                "image_mode": image.mode,
                "file_size": len(image_content)
            }
            
            # Extraction de texte avec OCR
            ocr_text = ""
            if extract_text:
                ocr_text = self.multimodal_embeddings.extract_text_from_image(image)
                metadata["has_ocr_text"] = len(ocr_text.strip()) > 0
            
            # Génération de description
            caption = ""
            if generate_captions:
                caption = self.multimodal_embeddings.generate_image_caption(image)
                metadata["has_caption"] = len(caption.strip()) > 0
            
            # Contenu combiné pour la recherche
            searchable_content = f"Image: {filename}"
            if caption:
                searchable_content += f"\nDescription: {caption}"
            if ocr_text:
                searchable_content += f"\nTexte extrait: {ocr_text}"
            
            return {
                "content": searchable_content,
                "caption": caption,
                "ocr_text": ocr_text,
                "image": image,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement image {filename}: {e}")
            raise
    
    async def process_text_document(self, document_content: bytes, filename: str) -> Dict[str, Any]:
        """Traite un document texte"""
        try:
            # Extraction du texte du document
            text_content = await process_document_advanced(document_content, filename)
            
            # Métadonnées
            metadata = {
                "filename": filename,
                "content_type": ContentType.DOCUMENT.value,
                "modality": ModalityType.TEXT.value,
                "file_size": len(document_content),
                "text_length": len(text_content)
            }
            
            return {
                "content": text_content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement document {filename}: {e}")
            raise
    
    def create_multimodal_chunks(self, processed_data: Dict[str, Any], 
                                document_id: str) -> List[Dict[str, Any]]:
        """Crée des chunks pour les données multimodales"""
        chunks = []
        
        content_type = processed_data["metadata"]["content_type"]
        
        if content_type == ContentType.IMAGE.value:
            # Pour les images, on crée un chunk principal avec toutes les informations
            chunk_data = {
                "id": f"{document_id}_image_main",
                "content": processed_data["content"],
                "metadata": {
                    **processed_data["metadata"],
                    "document_id": document_id,
                    "chunk_type": "image_main",
                    "chunk_length": len(processed_data["content"]),
                    "caption": processed_data.get("caption", ""),
                    "ocr_text": processed_data.get("ocr_text", "")
                }
            }
            chunks.append(chunk_data)
            
            # Chunk séparé pour la description si elle existe
            if processed_data.get("caption"):
                caption_chunk = {
                    "id": f"{document_id}_caption",
                    "content": f"Description de l'image: {processed_data['caption']}",
                    "metadata": {
                        **processed_data["metadata"],
                        "document_id": document_id,
                        "chunk_type": "image_caption",
                        "chunk_length": len(processed_data['caption']),
                        "modality": ModalityType.TEXT.value
                    }
                }
                chunks.append(caption_chunk)
            
            # Chunk séparé pour le texte OCR si il existe
            if processed_data.get("ocr_text") and len(processed_data["ocr_text"].strip()) > 10:
                ocr_chunk = {
                    "id": f"{document_id}_ocr",
                    "content": f"Texte extrait de l'image: {processed_data['ocr_text']}",
                    "metadata": {
                        **processed_data["metadata"],
                        "document_id": document_id,
                        "chunk_type": "image_ocr",
                        "chunk_length": len(processed_data['ocr_text']),
                        "modality": ModalityType.TEXT.value
                    }
                }
                chunks.append(ocr_chunk)
        
        elif content_type == ContentType.DOCUMENT.value:
            # Pour les documents texte, on utilise le chunking standard
            # mais on adapte les métadonnées pour le multimodal
            text_content = processed_data["content"]
            
            # Chunking simple pour les documents texte
            chunk_size = 1000
            overlap = 200
            
            for i in range(0, len(text_content), chunk_size - overlap):
                chunk_text = text_content[i:i + chunk_size]
                if len(chunk_text.strip()) < 50:  # Skip très petits chunks
                    continue
                
                chunk_data = {
                    "id": f"{document_id}_text_{i}",
                    "content": chunk_text,
                    "metadata": {
                        **processed_data["metadata"],
                        "document_id": document_id,
                        "chunk_type": "text_chunk",
                        "chunk_index": i // (chunk_size - overlap),
                        "chunk_length": len(chunk_text)
                    }
                }
                chunks.append(chunk_data)
        
        return chunks