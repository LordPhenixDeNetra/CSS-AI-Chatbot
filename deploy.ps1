# Script de déploiement automatisé pour RAG Ultra Performant Multimodal API
# Auteur: RAG Multimodal Team
# Version: 1.0
# Compatible: Windows PowerShell 5.1+

param(
    [string]$Environment = "production",
    [string]$Domain = "localhost",
    [string]$Email = "admin@example.com",
    [switch]$Backup,
    [switch]$SSL,
    [switch]$Monitoring,
    [switch]$Force,
    [switch]$Verbose,
    [string]$Command = "install",
    [switch]$Help
)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectName = "rag-ultra-performant"
$Version = "3.1.0"

# Couleurs pour les logs
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Purple = "Magenta"
    Cyan = "Cyan"
}

# Fonction de logging
function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    switch ($Level) {
        "INFO" {
            Write-Host "[$Timestamp] INFO: $Message" -ForegroundColor $Colors.Blue
        }
        "WARN" {
            Write-Host "[$Timestamp] WARN: $Message" -ForegroundColor $Colors.Yellow
        }
        "ERROR" {
            Write-Host "[$Timestamp] ERROR: $Message" -ForegroundColor $Colors.Red
        }
        "SUCCESS" {
            Write-Host "[$Timestamp] SUCCESS: $Message" -ForegroundColor $Colors.Green
        }
        "STEP" {
            Write-Host "[$Timestamp] STEP: $Message" -ForegroundColor $Colors.Purple
        }
    }
}

# Affichage de l'aide
function Show-Help {
    Write-Host @"
🚀 Script de déploiement RAG Ultra Performant Multimodal API

Usage: .\deploy.ps1 [OPTIONS] [-Command COMMAND]

Commandes:
    install         Installation complète (défaut)
    update          Mise à jour de l'application
    backup          Sauvegarde avant déploiement
    rollback        Retour à la version précédente
    status          Vérifier l'état du déploiement
    logs            Afficher les logs
    cleanup         Nettoyer les ressources inutilisées
    ssl             Configurer SSL
    monitoring      Déployer le monitoring
    help            Afficher cette aide

Options:
    -Environment ENV        Environnement (production, staging, dev)
    -Domain DOMAIN          Nom de domaine
    -Email EMAIL            Email pour SSL
    -Backup                 Créer une sauvegarde avant déploiement
    -SSL                    Activer SSL automatiquement
    -Monitoring             Déployer avec monitoring
    -Force                  Forcer le déploiement
    -Verbose                Mode verbeux
    -Help                   Afficher cette aide

Exemples:
    .\deploy.ps1
    .\deploy.ps1 -Environment production -Domain api.example.com -SSL
    .\deploy.ps1 -Backup -Command update
    .\deploy.ps1 -Command monitoring
    .\deploy.ps1 -Command status

"@
}

# Vérification des prérequis
function Test-Prerequisites {
    Write-Log "STEP" "Vérification des prérequis..."
    
    $MissingTools = @()
    
    # Vérifier Docker
    try {
        $null = docker --version
    } catch {
        $MissingTools += "docker"
    }
    
    # Vérifier Docker Compose
    try {
        $null = docker-compose --version
    } catch {
        $MissingTools += "docker-compose"
    }
    
    if ($MissingTools.Count -gt 0) {
        Write-Log "ERROR" "Outils manquants: $($MissingTools -join ', ')"
        Write-Log "INFO" "Veuillez installer Docker Desktop pour Windows"
        Write-Log "INFO" "Téléchargement: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    # Vérifier que Docker fonctionne
    try {
        $null = docker info 2>$null
    } catch {
        Write-Log "ERROR" "Docker n'est pas démarré ou accessible"
        Write-Log "INFO" "Veuillez démarrer Docker Desktop"
        exit 1
    }
    
    # Vérifier l'espace disque (minimum 10GB)
    $Drive = (Get-Location).Drive
    $FreeSpace = (Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$($Drive.Name)'").FreeSpace
    $MinSpace = 10GB
    
    if ($FreeSpace -lt $MinSpace) {
        $FreeSpaceGB = [math]::Round($FreeSpace / 1GB, 2)
        Write-Log "WARN" "Espace disque faible: ${FreeSpaceGB}GB disponible, 10GB recommandé"
    }
    
    Write-Log "SUCCESS" "Prérequis vérifiés"
}

# Configuration de l'environnement
function Initialize-Environment {
    Write-Log "STEP" "Configuration de l'environnement..."
    
    Set-Location $ScriptDir
    
    # Créer les répertoires nécessaires
    $Directories = @(
        "data", "logs", "ultra_rag_db", ".cache", "backups", 
        "ssl", "monitoring\grafana\dashboards"
    )
    
    foreach ($Dir in $Directories) {
        if (!(Test-Path $Dir)) {
            New-Item -ItemType Directory -Path $Dir -Force | Out-Null
        }
    }
    
    # Copier .env.example vers .env si nécessaire
    if (!(Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Log "INFO" "Fichier .env créé à partir de .env.example"
            Write-Log "WARN" "⚠️  Veuillez éditer .env avec vos clés API avant de continuer"
            
            if ($Environment -eq "production") {
                # Configurer pour la production
                (Get-Content ".env") -replace 'DEBUG=true', 'DEBUG=false' | Set-Content ".env"
                (Get-Content ".env") -replace 'ENVIRONMENT="development"', 'ENVIRONMENT="production"' | Set-Content ".env"
                (Get-Content ".env") -replace 'LOG_LEVEL="DEBUG"', 'LOG_LEVEL="INFO"' | Set-Content ".env"
            }
        } else {
            Write-Log "ERROR" "Fichier .env.example non trouvé"
            exit 1
        }
    }
    
    # Configurer le domaine dans nginx.conf si spécifié
    if ($Domain -ne "localhost" -and (Test-Path "nginx.conf")) {
        (Get-Content "nginx.conf") -replace 'server_name localhost;', "server_name $Domain;" | Set-Content "nginx.conf"
        Write-Log "INFO" "Domaine configuré: $Domain"
    }
    
    Write-Log "SUCCESS" "Environnement configuré"
}

# Sauvegarde avant déploiement
function New-Backup {
    Write-Log "STEP" "Création d'une sauvegarde..."
    
    if (Test-Path "scripts\backup.sh") {
        # Exécuter le script de sauvegarde via WSL ou Git Bash si disponible
        try {
            if (Get-Command wsl -ErrorAction SilentlyContinue) {
                wsl ./scripts/backup.sh
            } elseif (Get-Command bash -ErrorAction SilentlyContinue) {
                bash ./scripts/backup.sh
            } else {
                Write-Log "WARN" "WSL ou Git Bash requis pour exécuter le script de sauvegarde"
                return
            }
            Write-Log "SUCCESS" "Sauvegarde créée"
        } catch {
            Write-Log "WARN" "Erreur lors de la sauvegarde: $($_.Exception.Message)"
        }
    } else {
        Write-Log "WARN" "Script de sauvegarde non trouvé"
    }
}

# Construction des images Docker
function Build-Images {
    Write-Log "STEP" "Construction des images Docker..."
    
    $ComposeFile = "docker-compose.yml"
    
    switch ($Environment) {
        "production" { $ComposeFile = "docker-compose.prod.yml" }
        "development" { $ComposeFile = "docker-compose.dev.yml" }
    }
    
    if (!(Test-Path $ComposeFile)) {
        Write-Log "ERROR" "Fichier $ComposeFile non trouvé"
        exit 1
    }
    
    # Construire les images
    try {
        docker-compose -f $ComposeFile build --no-cache
        Write-Log "SUCCESS" "Images construites"
    } catch {
        Write-Log "ERROR" "Erreur lors de la construction: $($_.Exception.Message)"
        exit 1
    }
}

# Déploiement des services
function Deploy-Services {
    Write-Log "STEP" "Déploiement des services..."
    
    $ComposeFile = "docker-compose.yml"
    $ComposeArgs = @()
    
    switch ($Environment) {
        "production" { $ComposeFile = "docker-compose.prod.yml" }
        "development" { $ComposeFile = "docker-compose.dev.yml" }
    }
    
    # Ajouter le monitoring si demandé
    if ($Monitoring) {
        $ComposeArgs += "--profile", "monitoring"
    }
    
    try {
        # Arrêter les services existants
        docker-compose -f $ComposeFile down 2>$null
        
        # Démarrer les services
        if ($ComposeArgs.Count -gt 0) {
            docker-compose -f $ComposeFile @ComposeArgs up -d
        } else {
            docker-compose -f $ComposeFile up -d
        }
        
        # Attendre que les services soient prêts
        Write-Log "INFO" "Attente du démarrage des services..."
        Start-Sleep -Seconds 30
        
        # Vérifier l'état des services
        $Services = docker-compose -f $ComposeFile ps
        if ($Services -match "Up") {
            Write-Log "SUCCESS" "Services déployés avec succès"
        } else {
            Write-Log "ERROR" "Échec du déploiement des services"
            docker-compose -f $ComposeFile logs
            exit 1
        }
    } catch {
        Write-Log "ERROR" "Erreur lors du déploiement: $($_.Exception.Message)"
        exit 1
    }
}

# Configuration SSL
function Set-SSL {
    Write-Log "STEP" "Configuration SSL..."
    
    if ($Domain -eq "localhost") {
        Write-Log "WARN" "SSL ignoré pour localhost"
        return
    }
    
    Write-Log "INFO" "Configuration SSL manuelle requise sur Windows"
    Write-Log "INFO" "Veuillez configurer vos certificats SSL dans le répertoire ssl/"
    Write-Log "INFO" "Fichiers requis: ssl/cert.pem et ssl/key.pem"
}

# Vérification de l'état du déploiement
function Test-DeploymentStatus {
    Write-Log "STEP" "Vérification de l'état du déploiement..."
    
    $BaseUrl = "http://localhost:8000"
    if ($Domain -ne "localhost") {
        $BaseUrl = "http://$Domain"
    }
    
    # Vérifier l'API
    Write-Log "INFO" "Test de l'API..."
    try {
        $Response = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing -TimeoutSec 10
        if ($Response.StatusCode -eq 200) {
            Write-Log "SUCCESS" "✓ API accessible"
        } else {
            Write-Log "ERROR" "✗ API non accessible (Status: $($Response.StatusCode))"
            return $false
        }
    } catch {
        Write-Log "ERROR" "✗ API non accessible: $($_.Exception.Message)"
        return $false
    }
    
    # Vérifier les capacités multimodales
    Write-Log "INFO" "Test des capacités multimodales..."
    try {
        $Response = Invoke-WebRequest -Uri "$BaseUrl/multimodal-capabilities" -UseBasicParsing -TimeoutSec 10
        if ($Response.StatusCode -eq 200) {
            Write-Log "SUCCESS" "✓ Capacités multimodales actives"
        } else {
            Write-Log "WARN" "⚠ Capacités multimodales non disponibles"
        }
    } catch {
        Write-Log "WARN" "⚠ Capacités multimodales non disponibles"
    }
    
    # Vérifier Redis
    Write-Log "INFO" "Test de Redis..."
    try {
        $RedisTest = docker-compose exec -T redis redis-cli ping 2>$null
        if ($RedisTest -match "PONG") {
            Write-Log "SUCCESS" "✓ Redis opérationnel"
        } else {
            Write-Log "WARN" "⚠ Redis non accessible"
        }
    } catch {
        Write-Log "WARN" "⚠ Redis non accessible"
    }
    
    # Vérifier ChromaDB
    Write-Log "INFO" "Test de ChromaDB..."
    try {
        $Response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -UseBasicParsing -TimeoutSec 10
        if ($Response.StatusCode -eq 200) {
            Write-Log "SUCCESS" "✓ ChromaDB opérationnel"
        } else {
            Write-Log "WARN" "⚠ ChromaDB non accessible"
        }
    } catch {
        Write-Log "WARN" "⚠ ChromaDB non accessible"
    }
    
    # Afficher les informations de déploiement
    Write-Host ""
    Write-Log "INFO" "=== INFORMATIONS DE DÉPLOIEMENT ==="
    Write-Host "🌐 API URL: $BaseUrl" -ForegroundColor Cyan
    Write-Host "📚 Documentation: $BaseUrl/docs" -ForegroundColor Cyan
    Write-Host "❤️ Health Check: $BaseUrl/health" -ForegroundColor Cyan
    Write-Host "🔍 ChromaDB: http://localhost:8001" -ForegroundColor Cyan
    
    if ($Monitoring) {
        Write-Host "📊 Prometheus: http://localhost:9090" -ForegroundColor Cyan
        Write-Host "📈 Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Log "SUCCESS" "Déploiement vérifié"
    return $true
}

# Affichage des logs
function Show-Logs {
    param([string]$Service = "")
    
    if ($Service) {
        docker-compose logs -f $Service
    } else {
        docker-compose logs -f
    }
}

# Nettoyage des ressources
function Clear-Resources {
    Write-Log "STEP" "Nettoyage des ressources..."
    
    try {
        # Supprimer les images inutilisées
        docker image prune -f
        
        # Supprimer les volumes orphelins
        docker volume prune -f
        
        # Supprimer les réseaux inutilisés
        docker network prune -f
        
        Write-Log "SUCCESS" "Nettoyage terminé"
    } catch {
        Write-Log "ERROR" "Erreur lors du nettoyage: $($_.Exception.Message)"
    }
}

# Rollback vers la version précédente
function Invoke-Rollback {
    Write-Log "STEP" "Rollback vers la version précédente..."
    
    try {
        # Arrêter les services actuels
        docker-compose down
        
        # Restaurer la dernière sauvegarde
        if (Test-Path "scripts\restore.sh") {
            $LatestBackup = Get-ChildItem "backups\rag_backup_*.tar.gz" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($LatestBackup) {
                if (Get-Command wsl -ErrorAction SilentlyContinue) {
                    wsl ./scripts/restore.sh $LatestBackup.Name
                } elseif (Get-Command bash -ErrorAction SilentlyContinue) {
                    bash ./scripts/restore.sh $LatestBackup.Name
                } else {
                    Write-Log "ERROR" "WSL ou Git Bash requis pour le rollback"
                    exit 1
                }
                Write-Log "SUCCESS" "Rollback terminé"
            } else {
                Write-Log "ERROR" "Aucune sauvegarde trouvée pour le rollback"
                exit 1
            }
        } else {
            Write-Log "ERROR" "Script de restauration non trouvé"
            exit 1
        }
    } catch {
        Write-Log "ERROR" "Erreur lors du rollback: $($_.Exception.Message)"
        exit 1
    }
}

# Fonction principale
function Main {
    # Afficher l'aide si demandé
    if ($Help) {
        Show-Help
        return
    }
    
    # Activer le mode verbeux si demandé
    if ($Verbose) {
        $VerbosePreference = "Continue"
    }
    
    # Afficher la bannière
    Write-Host ""
    Write-Host "🚀 RAG Ultra Performant Multimodal API - Déploiement v$Version" -ForegroundColor Green
    Write-Host "📦 Environnement: $Environment" -ForegroundColor Cyan
    Write-Host "🌐 Domaine: $Domain" -ForegroundColor Cyan
    Write-Host "📧 Email: $Email" -ForegroundColor Cyan
    Write-Host ""
    
    # Exécuter la commande
    switch ($Command.ToLower()) {
        "install" {
            Test-Prerequisites
            Initialize-Environment
            
            if ($Backup) {
                New-Backup
            }
            
            Build-Images
            Deploy-Services
            
            if ($SSL) {
                Set-SSL
            }
            
            Test-DeploymentStatus
        }
        "update" {
            if ($Backup) {
                New-Backup
            }
            
            Build-Images
            Deploy-Services
            Test-DeploymentStatus
        }
        "backup" {
            New-Backup
        }
        "rollback" {
            Invoke-Rollback
        }
        "status" {
            Test-DeploymentStatus
        }
        "logs" {
            Show-Logs
        }
        "cleanup" {
            Clear-Resources
        }
        "ssl" {
            Set-SSL
        }
        "monitoring" {
            $script:Monitoring = $true
            Deploy-Services
        }
        "help" {
            Show-Help
        }
        default {
            Write-Log "ERROR" "Commande inconnue: $Command"
            Show-Help
            exit 1
        }
    }
    
    Write-Log "SUCCESS" "🎉 Déploiement terminé avec succès!"
}

# Point d'entrée
if ($MyInvocation.InvocationName -ne '.') {
    Main
}