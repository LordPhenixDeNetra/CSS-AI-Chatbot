# Script PowerShell de démarrage Docker pour RAG Ultra Performant Multimodal API

param(
    [Parameter(Position=0)]
    [ValidateSet("basic", "monitoring", "build", "dev")]
    [string]$Mode = "basic"
)

# Configuration des couleurs
$Host.UI.RawUI.ForegroundColor = "White"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Print-Status($Message) {
    Write-ColorOutput Blue "[INFO] $Message"
}

function Print-Success($Message) {
    Write-ColorOutput Green "[SUCCESS] $Message"
}

function Print-Warning($Message) {
    Write-ColorOutput Yellow "[WARNING] $Message"
}

function Print-Error($Message) {
    Write-ColorOutput Red "[ERROR] $Message"
}

Write-Host "Démarrage de RAG Multimodal API" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Vérification de Docker
try {
    docker --version | Out-Null
} catch {
    Print-Error "Docker n'est pas installé ou n'est pas accessible. Veuillez installer Docker Desktop."
    exit 1
}

try {
    docker-compose --version | Out-Null
} catch {
    Print-Error "Docker Compose n'est pas installé. Veuillez installer Docker Compose."
    exit 1
}

# Création des répertoires nécessaires
Print-Status "Création des répertoires nécessaires..."
$directories = @("data", "logs", "ultra_rag_db", ".cache")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Vérification du fichier .env
if (!(Test-Path ".env")) {
    Print-Warning "Fichier .env non trouvé. Création d'un fichier .env par défaut..."
    
    $envContent = @"
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
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Print-Warning "Veuillez configurer vos clés API dans le fichier .env"
}

# Démarrage selon le mode
switch ($Mode) {
    "basic" {
        Print-Status "Démarrage en mode basique (API + Redis + ChromaDB)..."
        docker-compose up -d rag-api redis chromadb
    }
    "monitoring" {
        Print-Status "Démarrage avec monitoring (API + Redis + ChromaDB + Prometheus + Grafana)..."
        docker-compose --profile monitoring up -d
    }
    "build" {
        Print-Status "Reconstruction et démarrage..."
        docker-compose build --no-cache
        docker-compose up -d rag-api redis chromadb
    }
    "dev" {
        Print-Status "Démarrage en mode développement..."
        if (Test-Path "docker-compose.dev.yml") {
            docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        } else {
            Print-Warning "Fichier docker-compose.dev.yml non trouvé, démarrage en mode basic"
            docker-compose up -d rag-api redis chromadb
        }
    }
}

if ($LASTEXITCODE -ne 0) {
    Print-Error "Erreur lors du démarrage des services"
    docker-compose logs
    exit 1
}

# Attendre que les services soient prêts
Print-Status "Attente du démarrage des services..."
Start-Sleep -Seconds 10

# Vérification de l'état des services
Print-Status "Vérification de l'état des services..."

$services = docker-compose ps --format "table {{.Name}}\t{{.State}}"
if ($services -match "Up") {
    Print-Success "Services démarrés avec succès!"
    Write-Host ""
    Write-Host "📋 Services disponibles:" -ForegroundColor Yellow
    Write-Host "   🔗 API RAG: http://localhost:8000" -ForegroundColor White
    Write-Host "   📚 Documentation: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "   ❤️  Health Check: http://localhost:8000/health" -ForegroundColor White
    Write-Host "   🗄️  Redis: localhost:6379" -ForegroundColor White
    Write-Host "   🔍 ChromaDB: http://localhost:8001" -ForegroundColor White
    
    if ($Mode -eq "monitoring") {
        Write-Host "   📊 Prometheus: http://localhost:9090" -ForegroundColor White
        Write-Host "   📈 Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "🔧 Commandes utiles:" -ForegroundColor Yellow
    Write-Host "   docker-compose logs -f rag-api    # Voir les logs de l'API" -ForegroundColor Gray
    Write-Host "   docker-compose ps                 # État des services" -ForegroundColor Gray
    Write-Host "   docker-compose down               # Arrêter tous les services" -ForegroundColor Gray
    Write-Host "   docker-compose restart rag-api    # Redémarrer l'API" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "✅ Tous les services sont opérationnels!" -ForegroundColor Green
} else {
    Print-Error "Erreur lors du démarrage des services"
    docker-compose logs
    exit 1
}