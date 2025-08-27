import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from app.utils.logging import logger


async def process_document_advanced(file_content: bytes, filename: str) -> str:
    """Traitement avancé de document avec extraction améliorée"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
        temp_file.write(file_content)
        file_path = temp_file.name

    try:
        if filename.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
            pages = loader.load()

            # Extraction avec métadonnées de page
            text_parts = []
            for page_num, page in enumerate(pages):
                page_text = page.page_content.strip()
                if page_text:
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")

            text = '\n\n'.join(text_parts)

        elif filename.lower().endswith(('.docx', '.doc')):
            loader = Docx2txtLoader(file_path)
            document = loader.load()[0]
            text = document.page_content

        else:
            raise ValueError("Format non supporté. Formats acceptés: PDF, DOC, DOCX")

        # Nettoyage et normalisation du texte
        text = text.replace('\x00', '')  # Suppression caractères null
        text = ' '.join(text.split())  # Normalisation espaces

        return text

    finally:
        os.unlink(file_path)
