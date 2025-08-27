#!/bin/bash

# Script de sauvegarde pour RAG Ultra Performant Multimodal API
# Auteur: RAG Multimodal Team
# Version: 1.0

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="rag_backup_${DATE}"
RETENTION_DAYS=30
LOG_FILE="${BACKUP_DIR}/backup.log"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[${timestamp}] INFO: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[${timestamp}] WARN: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[${timestamp}] SUCCESS: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Fonction de nettoyage en cas d'erreur
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log "ERROR" "Sauvegarde échouée avec le code $exit_code"
        # Nettoyer les fichiers partiels
        rm -rf "${BACKUP_DIR}/${BACKUP_NAME}"* 2>/dev/null || true
    fi
    exit $exit_code
}

# Piège pour le nettoyage
trap cleanup EXIT

# Vérification des prérequis
check_prerequisites() {
    log "INFO" "Vérification des prérequis..."
    
    # Vérifier que le répertoire de sauvegarde existe
    if [ ! -d "$BACKUP_DIR" ]; then
        log "ERROR" "Répertoire de sauvegarde $BACKUP_DIR n'existe pas"
        exit 1
    fi
    
    # Vérifier l'espace disque disponible (minimum 5GB)
    local available_space=$(df "$BACKUP_DIR" | awk 'NR==2 {print $4}')
    local min_space=5242880  # 5GB en KB
    
    if [ "$available_space" -lt "$min_space" ]; then
        log "ERROR" "Espace disque insuffisant. Disponible: ${available_space}KB, Requis: ${min_space}KB"
        exit 1
    fi
    
    log "SUCCESS" "Prérequis vérifiés"
}

# Sauvegarde des données de l'application
backup_app_data() {
    log "INFO" "Sauvegarde des données de l'application..."
    
    local app_backup_dir="${BACKUP_DIR}/${BACKUP_NAME}/app_data"
    mkdir -p "$app_backup_dir"
    
    # Sauvegarder les données utilisateur
    if [ -d "/backup/data" ]; then
        tar -czf "${app_backup_dir}/data.tar.gz" -C "/backup" data
        log "SUCCESS" "Données utilisateur sauvegardées"
    else
        log "WARN" "Répertoire /backup/data non trouvé"
    fi
    
    # Sauvegarder la base de données RAG
    if [ -d "/backup/ultra_rag_db" ]; then
        tar -czf "${app_backup_dir}/ultra_rag_db.tar.gz" -C "/backup" ultra_rag_db
        log "SUCCESS" "Base de données RAG sauvegardée"
    else
        log "WARN" "Répertoire /backup/ultra_rag_db non trouvé"
    fi
}

# Sauvegarde de Redis
backup_redis() {
    log "INFO" "Sauvegarde de Redis..."
    
    local redis_backup_dir="${BACKUP_DIR}/${BACKUP_NAME}/redis"
    mkdir -p "$redis_backup_dir"
    
    if [ -d "/backup/redis" ]; then
        # Copier le dump Redis
        cp -r /backup/redis/* "$redis_backup_dir/" 2>/dev/null || true
        
        # Créer une archive
        tar -czf "${redis_backup_dir}.tar.gz" -C "${BACKUP_DIR}/${BACKUP_NAME}" redis
        rm -rf "$redis_backup_dir"
        
        log "SUCCESS" "Redis sauvegardé"
    else
        log "WARN" "Données Redis non trouvées"
    fi
}

# Sauvegarde de ChromaDB
backup_chromadb() {
    log "INFO" "Sauvegarde de ChromaDB..."
    
    local chromadb_backup_dir="${BACKUP_DIR}/${BACKUP_NAME}/chromadb"
    mkdir -p "$chromadb_backup_dir"
    
    if [ -d "/backup/chromadb" ]; then
        tar -czf "${chromadb_backup_dir}.tar.gz" -C "/backup" chromadb
        log "SUCCESS" "ChromaDB sauvegardé"
    else
        log "WARN" "Données ChromaDB non trouvées"
    fi
}

# Création du manifeste de sauvegarde
create_manifest() {
    log "INFO" "Création du manifeste de sauvegarde..."
    
    local manifest_file="${BACKUP_DIR}/${BACKUP_NAME}/manifest.json"
    
    cat > "$manifest_file" << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "timestamp": "$(date -Iseconds)",
    "version": "3.1.0",
    "components": {
        "app_data": $([ -f "${BACKUP_DIR}/${BACKUP_NAME}/app_data/data.tar.gz" ] && echo "true" || echo "false"),
        "ultra_rag_db": $([ -f "${BACKUP_DIR}/${BACKUP_NAME}/app_data/ultra_rag_db.tar.gz" ] && echo "true" || echo "false"),
        "redis": $([ -f "${BACKUP_DIR}/${BACKUP_NAME}/redis.tar.gz" ] && echo "true" || echo "false"),
        "chromadb": $([ -f "${BACKUP_DIR}/${BACKUP_NAME}/chromadb.tar.gz" ] && echo "true" || echo "false")
    },
    "checksums": {
EOF
    
    # Ajouter les checksums
    for file in $(find "${BACKUP_DIR}/${BACKUP_NAME}" -name "*.tar.gz"); do
        local filename=$(basename "$file")
        local checksum=$(sha256sum "$file" | cut -d' ' -f1)
        echo "        \"$filename\": \"$checksum\"," >> "$manifest_file"
    done
    
    # Fermer le JSON (supprimer la dernière virgule)
    sed -i '$ s/,$//' "$manifest_file"
    echo "    }" >> "$manifest_file"
    echo "}" >> "$manifest_file"
    
    log "SUCCESS" "Manifeste créé"
}

# Compression finale
compress_backup() {
    log "INFO" "Compression finale de la sauvegarde..."
    
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    
    # Vérifier la compression
    if [ -f "${BACKUP_NAME}.tar.gz" ]; then
        local size=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
        log "SUCCESS" "Sauvegarde compressée: ${BACKUP_NAME}.tar.gz (${size})"
        
        # Supprimer le répertoire temporaire
        rm -rf "$BACKUP_NAME"
    else
        log "ERROR" "Échec de la compression"
        exit 1
    fi
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log "INFO" "Nettoyage des anciennes sauvegardes (> ${RETENTION_DAYS} jours)..."
    
    local deleted_count=0
    
    # Supprimer les sauvegardes anciennes
    find "$BACKUP_DIR" -name "rag_backup_*.tar.gz" -type f -mtime +"$RETENTION_DAYS" -print0 | 
    while IFS= read -r -d '' file; do
        log "INFO" "Suppression de $(basename "$file")"
        rm -f "$file"
        ((deleted_count++))
    done
    
    if [ "$deleted_count" -gt 0 ]; then
        log "SUCCESS" "$deleted_count anciennes sauvegardes supprimées"
    else
        log "INFO" "Aucune ancienne sauvegarde à supprimer"
    fi
}

# Envoi de notification (optionnel)
send_notification() {
    local status=$1
    local message=$2
    
    # Webhook Slack/Discord (à configurer)
    if [ -n "${WEBHOOK_URL:-}" ]; then
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"🔄 Sauvegarde RAG API\",
                \"attachments\": [{
                    \"color\": \"$([ \"$status\" = \"success\" ] && echo \"good\" || echo \"danger\")\",
                    \"fields\": [{
                        \"title\": \"Status\",
                        \"value\": \"$status\",
                        \"short\": true
                    }, {
                        \"title\": \"Message\",
                        \"value\": \"$message\",
                        \"short\": false
                    }]
                }]
            }" 2>/dev/null || true
    fi
}

# Fonction principale
main() {
    log "INFO" "=== Début de la sauvegarde RAG Ultra Performant ==="
    
    local start_time=$(date +%s)
    
    # Exécuter les étapes de sauvegarde
    check_prerequisites
    backup_app_data
    backup_redis
    backup_chromadb
    create_manifest
    compress_backup
    cleanup_old_backups
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "SUCCESS" "=== Sauvegarde terminée en ${duration}s ==="
    
    # Statistiques finales
    local backup_size=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
    local total_backups=$(ls -1 "${BACKUP_DIR}"/rag_backup_*.tar.gz 2>/dev/null | wc -l)
    
    log "INFO" "Taille de la sauvegarde: $backup_size"
    log "INFO" "Nombre total de sauvegardes: $total_backups"
    
    # Envoyer notification de succès
    send_notification "success" "Sauvegarde ${BACKUP_NAME} terminée avec succès (${backup_size})"
}

# Point d'entrée
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi