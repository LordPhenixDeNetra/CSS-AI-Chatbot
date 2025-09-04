import os
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
    import subprocess
    import sys
    from pathlib import Path
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

    def start_telegram_bot():
        """Démarre le bot Telegram automatiquement"""
        try:
            # Vérifier si le bot doit être démarré automatiquement
            auto_start_bot = os.getenv('AUTO_START_TELEGRAM_BOT', 'false').lower() == 'true'
            
            if not auto_start_bot:
                logger.info("Démarrage automatique du bot Telegram désactivé")
                return
                
            # Chemin vers le script du bot avancé
            bot_script = Path(__file__).parent.parent / "telegram_advanced.py"
            
            if not bot_script.exists():
                logger.warning(f"Script du bot Telegram non trouvé: {bot_script}")
                return
                
            # Vérifier les variables d'environnement nécessaires
            telegram_token = os.getenv('TELEGRAM_TOKEN')
            css_api_url = os.getenv('CSS_API_URL', 'http://localhost:8000')
            
            if not telegram_token:
                logger.warning("TELEGRAM_TOKEN non défini - bot Telegram non démarré")
                return
                
            logger.info("🤖 Démarrage automatique du bot Telegram avancé...")
            
            # Définir les variables d'environnement pour le bot
            env = os.environ.copy()
            env['TELEGRAM_TOKEN'] = telegram_token
            env['CSS_API_URL'] = css_api_url
            
            # Démarrer le bot avancé en arrière-plan
            bot_cwd = Path(__file__).parent.parent
            subprocess.Popen(
                [sys.executable, str(bot_script)],
                cwd=str(bot_cwd),
                env=env,
                start_new_session=True
            )
            
            logger.info("✅ Bot Telegram démarré automatiquement")
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage automatique du bot Telegram: {e}")

    # Démarrage des tâches en arrière-plan
    threading.Thread(target=preload_reranker, daemon=True).start()
    threading.Thread(target=start_telegram_bot, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
