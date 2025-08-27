#!/bin/bash

# Script de restauration pour RAG Ultra Performant Multimodal API
# Auteur: RAG Multimodal Team
# Version: 1.0

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
RESTORE_DIR="/restore"
LOG_FILE="${BACKUP_DIR}/restore.log"

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

# Affichage de l'aide
show_help() {
    cat << EOF
Script de restauration RAG Ultra Performant Multimodal API

Usage: $0 [OPTIONS] <backup_file>

Options:
    -h, --help              Afficher cette aide
    -l, --list              Lister les sauvegardes disponibles
    -i, --info <backup>     Afficher les informations d'une sauvegarde
    -c, --components <list> Restaurer seulement certains composants
                           (app_data,redis,chromadb,ultra_rag_db)
    -f, --force             Forcer la restauration sans confirmation
    -d, --dry-run           Simulation sans restauration réelle
    -v, --verify            Vérifier l'intégrité avant restauration

Exemples:
    $0 rag_backup_20240115_143022.tar.gz
    $0 -c app_data,redis rag_backup_20240115_143022.tar.gz
    $0 -l
    $0 -i rag_backup_20240115_143022.tar.gz
    $0 --dry-run rag_backup_20240115_143022.tar.gz

EOF
}

# Lister les sauvegardes disponibles
list_backups() {
    log "INFO" "Sauvegardes disponibles:"
    echo
    
    if ! ls "${BACKUP_DIR}"/rag_backup_*.tar.gz >/dev/null 2>&1; then
        log "WARN" "Aucune sauvegarde trouvée dans $BACKUP_DIR"
        return 1
    fi
    
    printf "%-30s %-15s %-10s\n" "Nom" "Date" "Taille"
    printf "%-30s %-15s %-10s\n" "---" "----" "------"
    
    for backup in "${BACKUP_DIR}"/rag_backup_*.tar.gz; do
        local name=$(basename "$backup")
        local date=$(stat -c %y "$backup" | cut -d' ' -f1)
        local size=$(du -h "$backup" | cut -f1)
        printf "%-30s %-15s %-10s\n" "$name" "$date" "$size"
    done
    echo
}

# Afficher les informations d'une sauvegarde
show_backup_info() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR" "Fichier de sauvegarde non trouvé: $backup_file"
        return 1
    fi
    
    log "INFO" "Informations de la sauvegarde: $(basename "$backup_file")"
    echo
    
    # Extraire temporairement le manifeste
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir" --wildcards "*/manifest.json" 2>/dev/null || {
        log "WARN" "Manifeste non trouvé dans la sauvegarde"
        rm -rf "$temp_dir"
        return 1
    }
    
    local manifest_file=$(find "$temp_dir" -name "manifest.json")
    
    if [ -f "$manifest_file" ]; then
        echo "📋 Manifeste de sauvegarde:"
        cat "$manifest_file" | jq . 2>/dev/null || cat "$manifest_file"
        echo
    fi
    
    # Afficher le contenu de l'archive
    echo "📦 Contenu de l'archive:"
    tar -tzf "$backup_file" | head -20
    
    local total_files=$(tar -tzf "$backup_file" | wc -l)
    if [ "$total_files" -gt 20 ]; then
        echo "... et $((total_files - 20)) autres fichiers"
    fi
    
    rm -rf "$temp_dir"
    echo
}

# Vérifier l'intégrité d'une sauvegarde
verify_backup() {
    local backup_file="$1"
    
    log "INFO" "Vérification de l'intégrité de $(basename "$backup_file")..."
    
    # Vérifier que l'archive n'est pas corrompue
    if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
        log "ERROR" "Archive corrompue ou invalide"
        return 1
    fi
    
    # Extraire temporairement pour vérifier les checksums
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir" 2>/dev/null || {
        log "ERROR" "Impossible d'extraire l'archive"
        rm -rf "$temp_dir"
        return 1
    }
    
    local manifest_file=$(find "$temp_dir" -name "manifest.json")
    
    if [ -f "$manifest_file" ]; then
        log "INFO" "Vérification des checksums..."
        
        # Vérifier chaque checksum
        local backup_dir=$(dirname "$manifest_file")
        local errors=0
        
        while IFS= read -r line; do
            if [[ $line =~ \"([^\"]+)\":[[:space:]]*\"([^\"]+)\" ]]; then
                local filename="${BASH_REMATCH[1]}"
                local expected_checksum="${BASH_REMATCH[2]}"
                
                local file_path=$(find "$backup_dir" -name "$filename")
                if [ -f "$file_path" ]; then
                    local actual_checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
                    if [ "$actual_checksum" = "$expected_checksum" ]; then
                        log "SUCCESS" "✓ $filename"
                    else
                        log "ERROR" "✗ $filename (checksum invalide)"
                        ((errors++))
                    fi
                else
                    log "ERROR" "✗ $filename (fichier manquant)"
                    ((errors++))
                fi
            fi
        done < <(grep -E '"[^"]+":[[:space:]]*"[^"]+"' "$manifest_file" | grep -v '"components"\|"backup_name"\|"timestamp"\|"version"')
        
        if [ "$errors" -eq 0 ]; then
            log "SUCCESS" "Intégrité vérifiée avec succès"
        else
            log "ERROR" "$errors erreur(s) d'intégrité détectée(s)"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log "WARN" "Pas de manifeste trouvé, vérification limitée"
    fi
    
    rm -rf "$temp_dir"
    return 0
}

# Demander confirmation
confirm_restore() {
    local backup_file="$1"
    local components="$2"
    
    echo
    log "WARN" "⚠️  ATTENTION: Cette opération va remplacer les données existantes!"
    echo
    echo "Sauvegarde: $(basename "$backup_file")"
    echo "Composants: $components"
    echo
    
    read -p "Êtes-vous sûr de vouloir continuer? (oui/non): " -r
    if [[ ! $REPLY =~ ^(oui|yes|y|o)$ ]]; then
        log "INFO" "Restauration annulée par l'utilisateur"
        exit 0
    fi
}

# Arrêter les services Docker
stop_services() {
    log "INFO" "Arrêt des services Docker..."
    
    # Essayer d'arrêter avec docker-compose
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose down 2>/dev/null || true
    fi
    
    # Arrêter les conteneurs individuellement si nécessaire
    for container in rag-api redis chromadb; do
        if docker ps -q -f name="$container" >/dev/null 2>&1; then
            docker stop "$container" 2>/dev/null || true
        fi
    done
    
    log "SUCCESS" "Services arrêtés"
}

# Restaurer les données de l'application
restore_app_data() {
    local backup_dir="$1"
    
    log "INFO" "Restauration des données de l'application..."
    
    if [ -f "${backup_dir}/app_data/data.tar.gz" ]; then
        mkdir -p "/app/data"
        tar -xzf "${backup_dir}/app_data/data.tar.gz" -C "/app"
        log "SUCCESS" "Données utilisateur restaurées"
    else
        log "WARN" "Données utilisateur non trouvées dans la sauvegarde"
    fi
}

# Restaurer la base de données RAG
restore_ultra_rag_db() {
    local backup_dir="$1"
    
    log "INFO" "Restauration de la base de données RAG..."
    
    if [ -f "${backup_dir}/app_data/ultra_rag_db.tar.gz" ]; then
        mkdir -p "/app/ultra_rag_db"
        tar -xzf "${backup_dir}/app_data/ultra_rag_db.tar.gz" -C "/app"
        log "SUCCESS" "Base de données RAG restaurée"
    else
        log "WARN" "Base de données RAG non trouvée dans la sauvegarde"
    fi
}

# Restaurer Redis
restore_redis() {
    local backup_dir="$1"
    
    log "INFO" "Restauration de Redis..."
    
    if [ -f "${backup_dir}/redis.tar.gz" ]; then
        # Créer le répertoire de données Redis
        mkdir -p "/var/lib/redis"
        
        # Extraire les données Redis
        tar -xzf "${backup_dir}/redis.tar.gz" -C "$backup_dir"
        
        # Copier les fichiers
        if [ -d "${backup_dir}/redis" ]; then
            cp -r "${backup_dir}/redis"/* "/var/lib/redis/" 2>/dev/null || true
            chown -R redis:redis "/var/lib/redis" 2>/dev/null || true
        fi
        
        log "SUCCESS" "Redis restauré"
    else
        log "WARN" "Données Redis non trouvées dans la sauvegarde"
    fi
}

# Restaurer ChromaDB
restore_chromadb() {
    local backup_dir="$1"
    
    log "INFO" "Restauration de ChromaDB..."
    
    if [ -f "${backup_dir}/chromadb.tar.gz" ]; then
        mkdir -p "/chroma/chroma"
        tar -xzf "${backup_dir}/chromadb.tar.gz" -C "/"
        log "SUCCESS" "ChromaDB restauré"
    else
        log "WARN" "Données ChromaDB non trouvées dans la sauvegarde"
    fi
}

# Redémarrer les services
restart_services() {
    log "INFO" "Redémarrage des services..."
    
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose up -d 2>/dev/null || {
            log "WARN" "Impossible de redémarrer avec docker-compose"
        }
    fi
    
    log "SUCCESS" "Services redémarrés"
}

# Fonction principale de restauration
restore_backup() {
    local backup_file="$1"
    local components="$2"
    local dry_run="$3"
    local force="$4"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR" "Fichier de sauvegarde non trouvé: $backup_file"
        return 1
    fi
    
    # Vérifier l'intégrité
    if ! verify_backup "$backup_file"; then
        log "ERROR" "Échec de la vérification d'intégrité"
        return 1
    fi
    
    # Demander confirmation si pas en mode force
    if [ "$force" = "false" ] && [ "$dry_run" = "false" ]; then
        confirm_restore "$backup_file" "$components"
    fi
    
    if [ "$dry_run" = "true" ]; then
        log "INFO" "=== MODE SIMULATION - Aucune modification réelle ==="
    fi
    
    # Extraire la sauvegarde
    local temp_dir=$(mktemp -d)
    log "INFO" "Extraction de la sauvegarde..."
    tar -xzf "$backup_file" -C "$temp_dir"
    
    local backup_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "rag_backup_*")
    
    if [ -z "$backup_dir" ]; then
        log "ERROR" "Structure de sauvegarde invalide"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Arrêter les services si pas en mode simulation
    if [ "$dry_run" = "false" ]; then
        stop_services
    fi
    
    # Restaurer les composants demandés
    IFS=',' read -ra COMPONENTS <<< "$components"
    for component in "${COMPONENTS[@]}"; do
        case "$component" in
            "app_data")
                if [ "$dry_run" = "false" ]; then
                    restore_app_data "$backup_dir"
                else
                    log "INFO" "[SIMULATION] Restauration des données de l'application"
                fi
                ;;
            "ultra_rag_db")
                if [ "$dry_run" = "false" ]; then
                    restore_ultra_rag_db "$backup_dir"
                else
                    log "INFO" "[SIMULATION] Restauration de la base de données RAG"
                fi
                ;;
            "redis")
                if [ "$dry_run" = "false" ]; then
                    restore_redis "$backup_dir"
                else
                    log "INFO" "[SIMULATION] Restauration de Redis"
                fi
                ;;
            "chromadb")
                if [ "$dry_run" = "false" ]; then
                    restore_chromadb "$backup_dir"
                else
                    log "INFO" "[SIMULATION] Restauration de ChromaDB"
                fi
                ;;
            *)
                log "WARN" "Composant inconnu: $component"
                ;;
        esac
    done
    
    # Redémarrer les services si pas en mode simulation
    if [ "$dry_run" = "false" ]; then
        restart_services
    fi
    
    # Nettoyer
    rm -rf "$temp_dir"
    
    if [ "$dry_run" = "false" ]; then
        log "SUCCESS" "Restauration terminée avec succès"
    else
        log "INFO" "Simulation terminée"
    fi
}

# Fonction principale
main() {
    local backup_file=""
    local components="app_data,ultra_rag_db,redis,chromadb"
    local dry_run="false"
    local force="false"
    local verify_only="false"
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -l|--list)
                list_backups
                exit 0
                ;;
            -i|--info)
                if [ -n "${2:-}" ]; then
                    show_backup_info "$2"
                    exit 0
                else
                    log "ERROR" "Option --info nécessite un fichier de sauvegarde"
                    exit 1
                fi
                ;;
            -c|--components)
                components="$2"
                shift
                ;;
            -f|--force)
                force="true"
                ;;
            -d|--dry-run)
                dry_run="true"
                ;;
            -v|--verify)
                verify_only="true"
                ;;
            -*)
                log "ERROR" "Option inconnue: $1"
                show_help
                exit 1
                ;;
            *)
                backup_file="$1"
                ;;
        esac
        shift
    done
    
    # Vérifier qu'un fichier de sauvegarde est spécifié
    if [ -z "$backup_file" ] && [ "$verify_only" = "false" ]; then
        log "ERROR" "Fichier de sauvegarde requis"
        show_help
        exit 1
    fi
    
    # Ajouter le chemin complet si nécessaire
    if [[ "$backup_file" != /* ]]; then
        backup_file="${BACKUP_DIR}/${backup_file}"
    fi
    
    # Mode vérification seulement
    if [ "$verify_only" = "true" ]; then
        verify_backup "$backup_file"
        exit $?
    fi
    
    # Lancer la restauration
    log "INFO" "=== Début de la restauration ==="
    restore_backup "$backup_file" "$components" "$dry_run" "$force"
}

# Point d'entrée
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi