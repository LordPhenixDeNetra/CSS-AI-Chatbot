from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
import hashlib

from app.utils.logging import logger


# Chunking sémantique avancé
class AdvancedChunker:
    def __init__(self, embeddings_model):
        self.embeddings = embeddings_model
        self.base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )

    def chunk_document(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """Chunking intelligent avec contexte sémantique"""
        # Chunking de base
        base_chunks = self.base_splitter.split_text(text)

        # Enrichissement des chunks
        enriched_chunks = []
        for i, chunk in enumerate(base_chunks):
            # Contexte des chunks adjacents
            context_before = base_chunks[i - 1] if i > 0 else ""
            context_after = base_chunks[i + 1] if i < len(base_chunks) - 1 else ""

            # Métadonnées enrichies
            metadata = {
                "document_id": document_id,
                "chunk_id": f"{document_id}_chunk_{i}",
                "chunk_index": i,
                "total_chunks": len(base_chunks),
                "context_before": context_before[:200],
                "context_after": context_after[:200],
                "chunk_length": len(chunk),
                "chunk_type": self._classify_chunk(chunk)
            }

            enriched_chunks.append({
                "content": chunk,
                "metadata": metadata
            })

        return enriched_chunks

    def _classify_chunk(self, chunk: str) -> str:
        """Classification basique du type de contenu"""
        if len(chunk.split()) < 10:
            return "short"
        elif ":" in chunk and len(chunk.split(":")) > 1:
            return "structured"
        elif chunk.count(".") > 3:
            return "paragraph"
        else:
            return "fragment"
