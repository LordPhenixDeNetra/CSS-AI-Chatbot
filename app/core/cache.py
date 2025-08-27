import redis
import hashlib
import pickle
import threading
from typing import Optional, Any
from functools import lru_cache
import os

from app.core.config import settings
from app.utils.logging import logger

# Configuration Redis
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connecté avec succès")
except Exception as e:
    REDIS_AVAILABLE = False
    logger.warning(f"Redis non disponible: {e}")


# Système de cache multi-niveaux
class MultiLayerCache:
    def __init__(self):
        self.memory_cache = {}
        self.memory_cache_lock = threading.Lock()
        self.max_memory_items = 1000

    def _get_cache_key(self, key: str, prefix: str = "") -> str:
        return f"{prefix}:{hashlib.md5(key.encode()).hexdigest()}"

    def get(self, key: str, cache_type: str = "general") -> Optional[Any]:
        cache_key = self._get_cache_key(key, cache_type)

        # Essayer Redis d'abord
        if REDIS_AVAILABLE:
            try:
                result = redis_client.get(cache_key)
                if result:
                    logger.info(f"Cache hit Redis: {cache_key}")
                    return pickle.loads(result.encode('latin1'))
            except Exception as e:
                logger.error(f"Erreur Redis get: {e}")

        # Fallback sur cache mémoire
        with self.memory_cache_lock:
            if cache_key in self.memory_cache:
                logger.info(f"Cache hit mémoire: {cache_key}")
                return self.memory_cache[cache_key]

        return None

    def set(self, key: str, value: Any, ttl: int = 3600, cache_type: str = "general"):
        cache_key = self._get_cache_key(key, cache_type)

        # Redis
        if REDIS_AVAILABLE:
            try:
                serialized = pickle.dumps(value).decode('latin1')
                redis_client.setex(cache_key, ttl, serialized)
            except Exception as e:
                logger.error(f"Erreur Redis set: {e}")

        # Cache mémoire
        with self.memory_cache_lock:
            if len(self.memory_cache) >= self.max_memory_items:
                # Supprimer les entrées les plus anciennes
                oldest_keys = list(self.memory_cache.keys())[:100]
                for old_key in oldest_keys:
                    del self.memory_cache[old_key]

            self.memory_cache[cache_key] = value


# Cache global
cache = MultiLayerCache()
