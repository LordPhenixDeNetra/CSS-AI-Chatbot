import os
# from pydantic import BaseSettings
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "CSS RAG Multimodal API"
    APP_DESCRIPTION: str = "API RAG multimodale avec recherche hybride, re-ranking et optimisations avancées"
    APP_VERSION: str = "2005.0.3"

    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))

    # API Keys
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # ChromaDB path
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./ultra_rag_db")
    MULTIMODAL_CHROMA_DB_PATH: str = os.getenv("MULTIMODAL_CHROMA_DB_PATH", "./multimodal_ultra_rag_db")

    # Model paths
    MULTIMODAL_MODELS: dict = {
        "clip": "openai/clip-vit-base-patch32",
        "blip": "Salesforce/blip-image-captioning-base",
        "text_embedding": "sentence-transformers/clip-ViT-B-32-multilingual-v1"
    }


settings = Settings()
