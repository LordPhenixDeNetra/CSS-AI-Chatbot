from fastapi import FastAPI
from app.api.endpoints import router
from app.core.config import settings
from app.utils.logging import setup_logging
from app.services.rag_service import multimodal_rag_system
from app.core.search import SearchResult

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """Événements de démarrage pour optimisation"""
    import threading
    from app.utils.logging import logger

    logger.info("Démarrage du RAG Ultra Performant Multimodal...")

    def preload_reranker():
        try:
            multimodal_rag_system.reranker.rerank("test", [
                SearchResult("test content", 0.5, {}, "test")
            ], top_k=1)
            logger.info("Reranker pré-chargé")
        except Exception as e:
            logger.warning(f"Erreur pré-chargement reranker: {e}")

    threading.Thread(target=preload_reranker, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)