# Dockerfile multi-stage pour RAG Ultra Performant Multimodal API

# Stage de base avec les dépendances système
FROM python:3.11-slim as base

# Métadonnées
LABEL maintainer="RAG Multimodal Team"
LABEL description="API RAG avec support multimodal"
LABEL version="2005.0.1"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    # Tesseract OCR pour l'extraction de texte des images
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    # Librairies pour le traitement d'images
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Outils de compilation pour certaines dépendances Python
    gcc \
    g++ \
    # Outils réseau
    curl \
    wget \
    # Nettoyage du cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY app/ ./app/
COPY .env* ./

# Création des répertoires nécessaires
RUN mkdir -p /app/data /app/logs /app/cache /app/ultra_rag_db

# Permissions pour l'utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# Changement vers l'utilisateur non-root
USER appuser

# Port exposé
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Stage de développement
FROM base as development

# Installation d'outils de développement
RUN pip install --no-cache-dir debugpy pytest pytest-cov black isort flake8

# Commande de développement avec hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage de production
FROM base as production

# Optimisations pour la production
ENV PYTHONOPTIMIZE=1

# Commande de production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Stage par défaut (production)
FROM production as default