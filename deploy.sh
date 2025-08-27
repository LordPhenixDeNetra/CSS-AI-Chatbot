#!/bin/bash

# Script de déploiement automatisé pour RAG Ultra Performant Multimodal API
# Auteur: RAG Multimodal Team
# Version: 1.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="rag-ultra-performant"
VERSION="3.1.0"
ENVIRONMENT="${ENVIRONMENT:-production}"
DOMAIN="${DOMAIN:-localhost}"
EMAIL="${EMAIL:-admin@example.com}"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[${timestamp}] INFO: ${message}${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}[${timestamp}] WARN: ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR: ${message}${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[${timestamp}] SUCCESS: ${message}${NC}"
            ;;
        "STEP")
            echo -e "${PURPLE}[${timestamp}] STEP: ${message}${NC}"
            ;;
    esac
}

# Affichage de l'aide
show_help() {
    cat << EOF
🚀 Script de déploiement RAG Ultra Performant Multimodal API

Usage: $0 [OPTIONS] [COMMAND]

Commandes:
    install         Installation complète (défaut)
    update          Mise à jour de l'application
    backup          Sauvegarde avant déploiement
    rollback        Retour à la version précédente
    status          Vérifier l'état du déploiement
    logs            Afficher les logs
    cleanup         Nettoyer les ressources inutilisées
    ssl             Configurer SSL avec Let's Encrypt
    monitoring      Déployer le monitoring
    help            Afficher cette aide

Options:
    -e, --env ENV           Environnement (production, staging, dev)
    -d, --domain DOMAIN     Nom de domaine
    -m, --email EMAIL       Email pour SSL
    -b, --backup            Créer une sauvegarde avant déploiement
    -s, --ssl               Activer SSL automatiquement
    -M, --monitoring        Déployer avec monitoring
    -f, --force             Forcer le déploiement
    -v, --verbose           Mode verbeux
    -h, --help              Afficher cette aide

Variables d'environnement:
    ENVIRONMENT             Environnement de déploiement
    DOMAIN                  Nom de domaine
    EMAIL                   Email pour SSL
    BACKUP_ENABLED          Activer les sauvegardes (true/false)
    SSL_ENABLED             Activer SSL (true/false)
    MONITORING_ENABLED      Activer le monitoring (true/false)

Exemples:
    $0 install
    $0 --env production --domain api.example.com --ssl install
    $0 --backup update
    $0 monitoring
    $0 status

EOF
}

# Vérification des prérequis
check_prerequisites() {
    log "STEP" "Vérification des prérequis..."
    
    local missing_tools=()
    
    # Vérifier Docker
    if ! command -v docker >/dev/null 2>&1; then
        missing_tools+=("docker")
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        missing_tools+=("docker-compose")
    fi
    
    # Vérifier curl
    if ! command -v curl >/dev/null 2>&1; then
        missing_tools+=("curl")
    fi
    
    # Vérifier jq
    if ! command -v jq >/dev/null 2>&1; then
        missing_tools+=("jq")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log "ERROR" "Outils manquants: ${missing_tools[*]}"
        log "INFO" "Installation sur Ubuntu/Debian:"
        echo "sudo apt update && sudo apt install -y docker.io docker-compose curl jq"
        log "INFO" "Installation sur CentOS/RHEL:"
        echo "sudo yum install -y docker docker-compose curl jq"
        exit 1
    fi
    
    # Vérifier que Docker fonctionne
    if ! docker info >/dev/null 2>&1; then
        log "ERROR" "Docker n'est pas démarré ou accessible"
        log "INFO" "Démarrer Docker: sudo systemctl start docker"
        exit 1
    fi
    
    # Vérifier l'espace disque (minimum 10GB)
    local available_space=$(df "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
    local min_space=10485760  # 10GB en KB
    
    if [ "$available_space" -lt "$min_space" ]; then
        log "WARN" "Espace disque faible: $(($available_space / 1024 / 1024))GB disponible, 10GB recommandé"
    fi
    
    log "SUCCESS" "Prérequis vérifiés"
}

# Configuration de l'environnement
setup_environment() {
    log "STEP" "Configuration de l'environnement..."
    
    cd "$SCRIPT_DIR"
    
    # Créer les répertoires nécessaires
    mkdir -p data logs ultra_rag_db .cache backups ssl monitoring/grafana/dashboards
    
    # Copier .env.example vers .env si nécessaire
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log "INFO" "Fichier .env créé à partir de .env.example"
            log "WARN" "⚠️  Veuillez éditer .env avec vos clés API avant de continuer"
            
            if [ "$ENVIRONMENT" = "production" ]; then
                # Configurer pour la production
                sed -i 's/DEBUG=true/DEBUG=false/' .env
                sed -i 's/ENVIRONMENT="development"/ENVIRONMENT="production"/' .env
                sed -i 's/LOG_LEVEL="DEBUG"/LOG_LEVEL="INFO"/' .env
            fi
        else
            log "ERROR" "Fichier .env.example non trouvé"
            exit 1
        fi
    fi
    
    # Configurer les permissions
    chmod +x scripts/*.sh 2>/dev/null || true
    
    # Configurer le domaine dans nginx.conf si spécifié
    if [ "$DOMAIN" != "localhost" ] && [ -f "nginx.conf" ]; then
        sed -i "s/server_name localhost;/server_name $DOMAIN;/g" nginx.conf
        log "INFO" "Domaine configuré: $DOMAIN"
    fi
    
    log "SUCCESS" "Environnement configuré"
}

# Sauvegarde avant déploiement
create_backup() {
    log "STEP" "Création d'une sauvegarde..."
    
    if [ -f "scripts/backup.sh" ]; then
        ./scripts/backup.sh
        log "SUCCESS" "Sauvegarde créée"
    else
        log "WARN" "Script de sauvegarde non trouvé"
    fi
}

# Construction des images Docker
build_images() {
    log "STEP" "Construction des images Docker..."
    
    local compose_file="docker-compose.yml"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        compose_file="docker-compose.prod.yml"
    elif [ "$ENVIRONMENT" = "development" ]; then
        compose_file="docker-compose.dev.yml"
    fi
    
    if [ ! -f "$compose_file" ]; then
        log "ERROR" "Fichier $compose_file non trouvé"
        exit 1
    fi
    
    # Construire les images
    docker-compose -f "$compose_file" build --no-cache
    
    log "SUCCESS" "Images construites"
}

# Déploiement des services
deploy_services() {
    log "STEP" "Déploiement des services..."
    
    local compose_file="docker-compose.yml"
    local compose_args=""
    
    if [ "$ENVIRONMENT" = "production" ]; then
        compose_file="docker-compose.prod.yml"
    elif [ "$ENVIRONMENT" = "development" ]; then
        compose_file="docker-compose.dev.yml"
    fi
    
    # Ajouter le monitoring si demandé
    if [ "${MONITORING_ENABLED:-false}" = "true" ]; then
        compose_args="--profile monitoring"
    fi
    
    # Arrêter les services existants
    docker-compose -f "$compose_file" down 2>/dev/null || true
    
    # Démarrer les services
    docker-compose -f "$compose_file" $compose_args up -d
    
    # Attendre que les services soient prêts
    log "INFO" "Attente du démarrage des services..."
    sleep 30
    
    # Vérifier l'état des services
    if docker-compose -f "$compose_file" ps | grep -q "Up"; then
        log "SUCCESS" "Services déployés avec succès"
    else
        log "ERROR" "Échec du déploiement des services"
        docker-compose -f "$compose_file" logs
        exit 1
    fi
}

# Configuration SSL avec Let's Encrypt
setup_ssl() {
    log "STEP" "Configuration SSL avec Let's Encrypt..."
    
    if [ "$DOMAIN" = "localhost" ]; then
        log "WARN" "SSL ignoré pour localhost"
        return 0
    fi
    
    # Installer certbot si nécessaire
    if ! command -v certbot >/dev/null 2>&1; then
        log "INFO" "Installation de certbot..."
        if command -v apt >/dev/null 2>&1; then
            sudo apt update && sudo apt install -y certbot python3-certbot-nginx
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y certbot python3-certbot-nginx
        else
            log "ERROR" "Impossible d'installer certbot automatiquement"
            return 1
        fi
    fi
    
    # Obtenir le certificat SSL
    sudo certbot --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "SSL configuré pour $DOMAIN"
        
        # Copier les certificats dans le répertoire ssl
        sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ssl/cert.pem
        sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" ssl/key.pem
        sudo chown $USER:$USER ssl/*.pem
        
        # Activer HTTPS dans nginx.conf
        sed -i 's/# return 301 https/return 301 https/' nginx.conf
        sed -i 's/# server {/server {/' nginx.conf
        sed -i 's/# }/}/' nginx.conf
        
        # Redémarrer nginx
        docker-compose restart nginx 2>/dev/null || true
    else
        log "ERROR" "Échec de la configuration SSL"
        return 1
    fi
}

# Vérification de l'état du déploiement
check_deployment_status() {
    log "STEP" "Vérification de l'état du déploiement..."
    
    local base_url="http://localhost:8000"
    if [ "$DOMAIN" != "localhost" ]; then
        base_url="http://$DOMAIN"
    fi
    
    # Vérifier l'API
    log "INFO" "Test de l'API..."
    if curl -f "$base_url/health" >/dev/null 2>&1; then
        log "SUCCESS" "✓ API accessible"
    else
        log "ERROR" "✗ API non accessible"
        return 1
    fi
    
    # Vérifier les capacités multimodales
    log "INFO" "Test des capacités multimodales..."
    if curl -f "$base_url/multimodal-capabilities" >/dev/null 2>&1; then
        log "SUCCESS" "✓ Capacités multimodales actives"
    else
        log "WARN" "⚠ Capacités multimodales non disponibles"
    fi
    
    # Vérifier Redis
    log "INFO" "Test de Redis..."
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        log "SUCCESS" "✓ Redis opérationnel"
    else
        log "WARN" "⚠ Redis non accessible"
    fi
    
    # Vérifier ChromaDB
    log "INFO" "Test de ChromaDB..."
    if curl -f "http://localhost:8001/api/v1/heartbeat" >/dev/null 2>&1; then
        log "SUCCESS" "✓ ChromaDB opérationnel"
    else
        log "WARN" "⚠ ChromaDB non accessible"
    fi
    
    # Afficher les informations de déploiement
    echo
    log "INFO" "=== INFORMATIONS DE DÉPLOIEMENT ==="
    echo "🌐 API URL: $base_url"
    echo "📚 Documentation: $base_url/docs"
    echo "❤️ Health Check: $base_url/health"
    echo "🔍 ChromaDB: http://localhost:8001"
    
    if [ "${MONITORING_ENABLED:-false}" = "true" ]; then
        echo "📊 Prometheus: http://localhost:9090"
        echo "📈 Grafana: http://localhost:3000 (admin/admin123)"
    fi
    
    echo
    log "SUCCESS" "Déploiement vérifié"
}

# Affichage des logs
show_logs() {
    local service="${1:-}"
    
    if [ -n "$service" ]; then
        docker-compose logs -f "$service"
    else
        docker-compose logs -f
    fi
}

# Nettoyage des ressources
cleanup() {
    log "STEP" "Nettoyage des ressources..."
    
    # Supprimer les images inutilisées
    docker image prune -f
    
    # Supprimer les volumes orphelins
    docker volume prune -f
    
    # Supprimer les réseaux inutilisés
    docker network prune -f
    
    log "SUCCESS" "Nettoyage terminé"
}

# Rollback vers la version précédente
rollback() {
    log "STEP" "Rollback vers la version précédente..."
    
    # Arrêter les services actuels
    docker-compose down
    
    # Restaurer la dernière sauvegarde
    if [ -f "scripts/restore.sh" ]; then
        local latest_backup=$(ls -t backups/rag_backup_*.tar.gz 2>/dev/null | head -1)
        if [ -n "$latest_backup" ]; then
            ./scripts/restore.sh "$latest_backup"
            log "SUCCESS" "Rollback terminé"
        else
            log "ERROR" "Aucune sauvegarde trouvée pour le rollback"
            exit 1
        fi
    else
        log "ERROR" "Script de restauration non trouvé"
        exit 1
    fi
}

# Fonction principale
main() {
    local command="install"
    local backup_before="false"
    local ssl_enabled="false"
    local monitoring_enabled="false"
    local force="false"
    local verbose="false"
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -m|--email)
                EMAIL="$2"
                shift 2
                ;;
            -b|--backup)
                backup_before="true"
                shift
                ;;
            -s|--ssl)
                ssl_enabled="true"
                shift
                ;;
            -M|--monitoring)
                monitoring_enabled="true"
                shift
                ;;
            -f|--force)
                force="true"
                shift
                ;;
            -v|--verbose)
                verbose="true"
                set -x
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            install|update|backup|rollback|status|logs|cleanup|ssl|monitoring|help)
                command="$1"
                shift
                ;;
            *)
                log "ERROR" "Option inconnue: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Exporter les variables d'environnement
    export ENVIRONMENT DOMAIN EMAIL
    export BACKUP_ENABLED="$backup_before"
    export SSL_ENABLED="$ssl_enabled"
    export MONITORING_ENABLED="$monitoring_enabled"
    
    # Afficher la bannière
    echo
    echo "🚀 RAG Ultra Performant Multimodal API - Déploiement v$VERSION"
    echo "📦 Environnement: $ENVIRONMENT"
    echo "🌐 Domaine: $DOMAIN"
    echo "📧 Email: $EMAIL"
    echo
    
    # Exécuter la commande
    case $command in
        "install")
            check_prerequisites
            setup_environment
            
            if [ "$backup_before" = "true" ]; then
                create_backup
            fi
            
            build_images
            deploy_services
            
            if [ "$ssl_enabled" = "true" ]; then
                setup_ssl
            fi
            
            check_deployment_status
            ;;
        "update")
            if [ "$backup_before" = "true" ]; then
                create_backup
            fi
            
            build_images
            deploy_services
            check_deployment_status
            ;;
        "backup")
            create_backup
            ;;
        "rollback")
            rollback
            ;;
        "status")
            check_deployment_status
            ;;
        "logs")
            show_logs "${2:-}"
            ;;
        "cleanup")
            cleanup
            ;;
        "ssl")
            setup_ssl
            ;;
        "monitoring")
            MONITORING_ENABLED="true"
            deploy_services
            ;;
        "help")
            show_help
            ;;
        *)
            log "ERROR" "Commande inconnue: $command"
            show_help
            exit 1
            ;;
    esac
    
    log "SUCCESS" "🎉 Déploiement terminé avec succès!"
}

# Point d'entrée
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi