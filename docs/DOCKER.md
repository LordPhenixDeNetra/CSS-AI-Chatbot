# 🐳 Guide Docker - RAG Ultra Performant Multimodal API

Ce guide vous explique comment utiliser Docker pour déployer et développer l'API RAG multimodale.

## 📋 Table des matières

- [Prérequis](#-prérequis)
- [Démarrage rapide](#-démarrage-rapide)
- [Modes de déploiement](#-modes-de-déploiement)
- [Configuration](#-configuration)
- [Monitoring](#-monitoring)
- [Développement](#-développement)
- [Commandes utiles](#-commandes-utiles)
- [Dépannage](#-dépannage)

## 🛠️ Prérequis

- **Docker** 20.10+ ([Installation](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ ([Installation](https://docs.docker.com/compose/install/))
- **8GB RAM minimum** (16GB recommandé)
- **10GB d'espace disque libre**

### Vérification de l'installation

```bash
# Vérifier Docker
docker --version

# Vérifier Docker Compose
docker-compose --version
```

## 🚀 Démarrage rapide

### Option 1: Script automatique (Recommandé)

**Linux/macOS:**
```bash
# Rendre le script exécutable
chmod +x docker-start.sh

# Démarrage basique
./docker-start.sh basic
```

**Windows (PowerShell):**
```powershell
# Démarrage basique
.\docker-start.ps1 basic
```

### Option 2: Commandes manuelles

```bash
# 1. Créer les répertoires nécessaires
mkdir -p data logs ultra_rag_db .cache

# 2. Configurer l'environnement (voir section Configuration)
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Démarrer les services
docker-compose up -d rag-api redis chromadb

# 4. Vérifier l'état
docker-compose ps
```

### Accès aux services

Après le démarrage, les services sont disponibles :

- **🔗 API RAG**: http://localhost:8000
- **📚 Documentation**: http://localhost:8000/docs
- **❤️ Health Check**: http://localhost:8000/health
- **🗄️ Redis**: localhost:6379
- **🔍 ChromaDB**: http://localhost:8001

## 🎯 Modes de déploiement

### Mode Basique
```bash
# Services essentiels : API + Redis + ChromaDB
./docker-start.sh basic
```

### Mode avec Monitoring
```bash
# Ajoute Prometheus + Grafana
./docker-start.sh monitoring
```
Services supplémentaires :
- **📊 Prometheus**: http://localhost:9090
- **📈 Grafana**: http://localhost:3000 (admin/admin123)

### Mode Build
```bash
# Reconstruction complète des images
./docker-start.sh build
```

### Mode Développement
```bash
# Hot reload + outils de debug
./docker-start.sh dev
```

## ⚙️ Configuration

### Fichier .env

Créez un fichier `.env` à la racine du projet :

```env
# Configuration de base
APP_NAME="RAG Ultra Performant Multimodal"
APP_VERSION="3.1.0"
DEBUG=false

# Providers LLM (OBLIGATOIRE)
MISTRAL_API_KEY=your_mistral_key_here
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GROQ_API_KEY=your_groq_key_here

# Services internes
REDIS_URL=redis://redis:6379
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# Performance
MAX_WORKERS=4
CACHE_TTL=3600
MAX_CHUNK_SIZE=1000

# Modèles (optionnel)
CLIP_MODEL=openai/clip-vit-base-patch32
BLIP_MODEL=Salesforce/blip-image-captioning-base
EMBEDDING_MODEL=sentence-transformers/clip-ViT-B-32-multilingual-v1
```

### Configuration Redis

Le fichier `redis.conf` est automatiquement utilisé. Personnalisations possibles :

```conf
# Mémoire maximum
maxmemory 1gb

# Politique d'éviction
maxmemory-policy allkeys-lru

# Mot de passe (décommentez pour activer)
# requirepass your_secure_password
```

## 📊 Monitoring

### Activation du monitoring

```bash
# Démarrer avec monitoring
docker-compose --profile monitoring up -d
```

### Métriques disponibles

**Prometheus** (http://localhost:9090) :
- Métriques de l'API RAG
- Métriques Redis
- Métriques ChromaDB
- Métriques système

**Grafana** (http://localhost:3000) :
- Dashboards pré-configurés
- Alertes personnalisables
- Visualisations en temps réel

### Configuration des alertes

Éditez `monitoring/prometheus.yml` pour ajouter des règles d'alerte :

```yaml
rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

## 🔧 Développement

### Mode développement

```bash
# Démarrage avec hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Ou avec le script
./docker-start.sh dev
```

### Fonctionnalités de développement

- **Hot reload** : Rechargement automatique du code
- **Debug port** : Port 5678 pour le debugging
- **Outils inclus** : pytest, black, isort, flake8
- **Logs détaillés** : Mode debug activé

### Tests avec Docker

```bash
# Lancer les tests
docker-compose exec rag-api pytest

# Tests avec couverture
docker-compose exec rag-api pytest --cov=app

# Tests spécifiques
docker-compose exec rag-api pytest tests/test_multimodal.py
```

### Accès au conteneur

```bash
# Shell interactif
docker-compose exec rag-api bash

# Exécuter des commandes
docker-compose exec rag-api python -c "import app; print('OK')"
```

## 🛠️ Commandes utiles

### Gestion des services

```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Redémarrer un service
docker-compose restart rag-api

# Voir l'état des services
docker-compose ps

# Voir les logs
docker-compose logs -f rag-api
```

### Gestion des données

```bash
# Sauvegarder les données
docker-compose exec rag-api tar -czf /app/backup.tar.gz /app/ultra_rag_db
docker cp $(docker-compose ps -q rag-api):/app/backup.tar.gz ./backup.tar.gz

# Restaurer les données
docker cp ./backup.tar.gz $(docker-compose ps -q rag-api):/app/backup.tar.gz
docker-compose exec rag-api tar -xzf /app/backup.tar.gz -C /
```

### Nettoyage

```bash
# Arrêter et supprimer les conteneurs
docker-compose down

# Supprimer les volumes (ATTENTION: perte de données)
docker-compose down -v

# Nettoyer les images inutilisées
docker system prune -a
```

### Mise à jour

```bash
# Reconstruire les images
docker-compose build --no-cache

# Redémarrer avec les nouvelles images
docker-compose up -d
```

## 🔍 Dépannage

### Problèmes courants

#### Service ne démarre pas
```bash
# Vérifier les logs
docker-compose logs rag-api

# Vérifier la configuration
docker-compose config
```

#### Erreur de mémoire
```bash
# Augmenter la mémoire Docker (Docker Desktop)
# Ou réduire le nombre de workers
echo "MAX_WORKERS=2" >> .env
docker-compose restart rag-api
```

#### Problème de permissions
```bash
# Linux/macOS : Corriger les permissions
sudo chown -R $USER:$USER data logs ultra_rag_db .cache
```

#### Port déjà utilisé
```bash
# Changer les ports dans docker-compose.yml
ports:
  - "8001:8000"  # Au lieu de 8000:8000
```

### Vérification de l'état

```bash
# Health check de l'API
curl http://localhost:8000/health

# Test des capacités multimodales
curl http://localhost:8000/multimodal-capabilities

# Vérifier Redis
docker-compose exec redis redis-cli ping

# Vérifier ChromaDB
curl http://localhost:8001/api/v1/heartbeat
```

### Logs et debugging

```bash
# Logs en temps réel
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f rag-api

# Logs avec timestamps
docker-compose logs -f -t rag-api

# Dernières 100 lignes
docker-compose logs --tail=100 rag-api
```

## 📈 Performance et optimisation

### Optimisations de production

```yaml
# docker-compose.override.yml pour la production
version: '3.8'
services:
  rag-api:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
    restart: always
```

### Monitoring des ressources

```bash
# Utilisation des ressources
docker stats

# Espace disque des volumes
docker system df

# Informations détaillées
docker-compose exec rag-api htop
```

## 🔒 Sécurité

### Bonnes pratiques

1. **Variables d'environnement** : Ne jamais commiter les clés API
2. **Réseau** : Utiliser des réseaux Docker isolés
3. **Utilisateur non-root** : Les conteneurs s'exécutent avec un utilisateur dédié
4. **Volumes** : Permissions appropriées sur les volumes

### Configuration sécurisée

```bash
# Générer un mot de passe Redis sécurisé
echo "REDIS_PASSWORD=$(openssl rand -base64 32)" >> .env

# Activer l'authentification Redis
echo "requirepass $(grep REDIS_PASSWORD .env | cut -d= -f2)" >> redis.conf
```

---

**🎉 Votre API RAG multimodale est maintenant prête à l'emploi avec Docker !**

Pour plus d'informations, consultez la [documentation principale](README.md).