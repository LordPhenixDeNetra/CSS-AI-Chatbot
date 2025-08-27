#!/bin/bash

# Script de démarrage Docker pour RAG Ultra Performant Multimodal API

set -e

echo "Démarrage de RAG Ultra Performant Multimodal API"
echo "================================================="

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages colorés
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification de Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose n'est pas installé. Veuillez installer Docker Compose d'abord."
    exit 1
fi

# Création des répertoires nécessaires
print_status "Création des répertoires nécessaires..."
mkdir -p data logs ultra_rag_db .cache

# Vérification du fichier .env
if [ ! -f ".env" ]; then
    print_warning "Fichier .env non trouvé. Création d'un fichier .env par défaut..."
    cat > .env << EOF
# Configuration de base
APP_NAME="RAG Ultra Performant Multimodal"
APP_VERSION="3.1.0"
DEBUG=false

# Providers LLM (à configurer)
MISTRAL_API_KEY=your_mistral_key_here
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GROQ_API_KEY=your_groq_key_here

# Redis
REDIS_URL=redis://redis:6379

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# Performance
MAX_WORKERS=4
CACHE_TTL=3600
MAX_CHUNK_SIZE=1000
EOF
    print_warning "Veuillez configurer vos clés API dans le fichier .env"
fi

# Options de démarrage
MODE=${1:-"basic"}

case $MODE in
    "basic")
        print_status "Démarrage en mode basique (API + Redis + ChromaDB)..."
        docker-compose up -d rag-api redis chromadb
        ;;
    "monitoring")
        print_status "Démarrage avec monitoring (API + Redis + ChromaDB + Prometheus + Grafana)..."
        docker-compose --profile monitoring up -d
        ;;
    "build")
        print_status "Reconstruction et démarrage..."
        docker-compose build --no-cache
        docker-compose up -d rag-api redis chromadb
        ;;
    "dev")
        print_status "Démarrage en mode développement..."
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        ;;
    *)
        print_error "Mode non reconnu. Modes disponibles: basic, monitoring, build, dev"
        exit 1
        ;;
esac

# Attendre que les services soient prêts
print_status "Attente du démarrage des services..."
sleep 10

# Vérification de l'état des services
print_status "Vérification de l'état des services..."

if docker-compose ps | grep -q "Up"; then
    print_success "Services démarrés avec succès!"
    echo ""
    echo "📋 Services disponibles:"
    echo "   🔗 API RAG: http://localhost:8000"
    echo "   📚 Documentation: http://localhost:8000/docs"
    echo "   ❤️  Health Check: http://localhost:8000/health"
    echo "   🗄️  Redis: localhost:6379"
    echo "   🔍 ChromaDB: http://localhost:8001"
    
    if [ "$MODE" = "monitoring" ]; then
        echo "   📊 Prometheus: http://localhost:9090"
        echo "   📈 Grafana: http://localhost:3000 (admin/admin123)"
    fi
    
    echo ""
    echo "🔧 Commandes utiles:"
    echo "   docker-compose logs -f rag-api    # Voir les logs de l'API"
    echo "   docker-compose ps                 # État des services"
    echo "   docker-compose down               # Arrêter tous les services"
    echo "   docker-compose restart rag-api    # Redémarrer l'API"
else
    print_error "Erreur lors du démarrage des services"
    docker-compose logs
    exit 1
fi