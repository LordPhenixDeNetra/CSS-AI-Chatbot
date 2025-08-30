from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.api.monitoring_dashboard import router as dashboard_router
from app.core.config import settings
from app.utils.logging import setup_logging
from app.services.rag_service import multimodal_rag_system
from app.core.search import SearchResult
from app.middleware.metrics_middleware import MetricsMiddleware, RAGMetricsMiddleware, CacheMetricsMiddleware
from app.core.metrics import metrics_collector
from app.core.business_metrics import business_metrics_collector

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION
)

# Ajout du middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Ajout des middlewares de métriques
app.add_middleware(MetricsMiddleware)
app.add_middleware(RAGMetricsMiddleware)
app.add_middleware(CacheMetricsMiddleware)

# Inclusion des routeurs
app.include_router(router)
app.include_router(dashboard_router)


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
