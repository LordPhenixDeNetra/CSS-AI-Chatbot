# 🚀 CSS RAG Multimodal API

Une API RAG (Retrieval Augmented Generation) ultra performante avec support multimodal complet (texte + images) utilisant les dernières technologies d'IA.

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Endpoints API](#-endpoints-api)
- [Exemples](#-exemples)
- [Performance](#-performance)
- [Monitoring](#-monitoring)
- [Développement](#-développement)
- [Contribution](#-contribution)

## ✨ Fonctionnalités

### 🔍 Recherche Avancée
- **Recherche hybride Dense+Sparse** : Combinaison optimale de recherche sémantique et par mots-clés
- **Re-ranking intelligent** : Cross-Encoder pour améliorer la pertinence des résultats
- **Query Enhancement** : Amélioration automatique des requêtes utilisateur
- **Cache multicouche** : Redis + mémoire pour des performances optimales

### 🖼️ Support Multimodal
- **Images supportées** : JPEG, PNG, GIF, BMP, TIFF, WebP
- **OCR avancé** : Extraction de texte des images avec Tesseract
- **Génération de légendes** : Descriptions automatiques d'images avec BLIP
- **Recherche par similarité d'image** : Utilisation de CLIP pour la recherche visuelle
- **Recherche croisée texte-image** : Requêtes multimodales sophistiquées

### 🤖 IA et Modèles
- **Support multi-provider LLM** : Mistral, OpenAI, Anthropic, Groq
- **Embeddings multimodaux** : CLIP + Sentence Transformers
- **Chunking sémantique adaptatif** : Découpage intelligent des documents
- **Streaming des réponses** : Réponses en temps réel

### 📊 Monitoring et Performance
- **Métriques Prometheus** : Monitoring complet des performances
- **Logging avancé** : Traçabilité complète des opérations
- **Health checks** : Surveillance de l'état du système
- **Optimisations avancées** : Pool de threads, lazy loading, cache intelligent

## 🏗️ Architecture

### Vue d'ensemble du système

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  RAG Engine     │    │   ChromaDB      │
│   Endpoints     │◄──►│  Multimodal     │◄──►│   Vector Store  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cache Layer   │    │  AI Models      │    │   Document      │
│   Redis+Memory  │    │  CLIP+BLIP+LLM  │    │   Processing    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Diagrammes détaillés

#### Architecture générale

```mermaid
graph TB
    %% Style definitions
    classDef apiLayer fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef cacheLayer fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef processingLayer fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef searchLayer fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef llmLayer fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef storageLayer fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef monitoringLayer fill:#e3f2fd,stroke:#1976d2,stroke-width:2px

    %% API Layer
    subgraph API["COUCHE API ET INTERFACE"]
        FastAPI[FastAPI Server\n- CORS Middleware\n- Upload Handler\n- Streaming Support]
        Endpoints[Endpoints\n- /upload-document\n- /ask-question-ultra\n- /ask-question-stream\n- /health\n- /metrics]
    end

    %% Cache Layer
    subgraph CACHE["COUCHE CACHE MULTICOUCHE"]
        MCL[MultiLayerCache]
        Redis[(Redis Cache\nPrioritaire)]
        MemCache[(Cache Memoire\nFallback)]
        CacheTypes[Types de Cache\n- embeddings\n- rerank\n- full_response\n- query_enhancement]
    end

    %% Document Processing Layer
    subgraph PROCESSING["COUCHE TRAITEMENT DOCUMENTS"]
        DocLoaders[Document Loaders\n- PyPDFLoader\n- Docx2txtLoader]
        AdvChunker[AdvancedChunker\n- Chunking semantique\n- Metadonnees enrichies\n- Classification chunks]
        TextProcess[Traitement Texte\n- Nettoyage\n- Normalisation\n- Extraction metadonnees]
    end

    %% Embeddings Layer
    subgraph EMBEDDINGS["COUCHE EMBEDDINGS"]
        AdvEmbed[AdvancedEmbeddings]
        PrimaryModel[all-mpnet-base-v2\nModele Principal]
        MultiModel[paraphrase-multilingual\nLazy Loading]
        EmbedCache[Cache LRU\n5000 items]
    end

    %% Search Layer
    subgraph SEARCH["COUCHE RECHERCHE HYBRIDE"]
        HybridSearch[HybridSearch Engine]
        
        subgraph DENSE["Recherche Dense"]
            ChromaQuery[ChromaDB Query\nRecherche Vectorielle]
        end
        
        subgraph SPARSE["Recherche Sparse"]
            BM25[BM25 Index\nRecherche Lexicale]
        end
        
        Fusion[Fusion Scores\nalpha=0.7 dense + 0.3 sparse]
        Dedup[Deduplication\n+ Boost Hybride]
    end

    %% Re-ranking Layer
    subgraph RERANK["COUCHE RE-RANKING"]
        AdvReranker[AdvancedReranker]
        CrossEncoder[CrossEncoder\nms-marco-MiniLM-L-12-v2]
        ScoreCombine[Score Combine\n30% retrieval + 70% rerank]
    end

    %% Query Enhancement
    subgraph ENHANCE["ENHANCEMENT REQUETES"]
        QueryEnh[QueryEnhancer]
        VariantGen[Generation Variantes\n- Synonymes\n- Reformulations\n- Angles differents]
    end

    %% LLM Layer
    subgraph LLM["COUCHE LLM MULTI-PROVIDER"]
        OptLLM[OptimizedLLMProvider]
        
        subgraph PROVIDERS["Providers Supportes"]
            Mistral[Mistral AI]
            OpenAI[OpenAI GPT]
            Anthropic[Claude]
            DeepSeek[DeepSeek]
            Groq[Groq]
        end
        
        ProviderConfig[Configuration\n- Headers\n- Models\n- API Keys]
    end

    %% Storage Layer
    subgraph STORAGE["COUCHE STOCKAGE"]
        ChromaDB[(ChromaDB\nVector Database)]
        EmbedFunc[Custom Embedding\nFunction]
        Collection[ultra_documents\nCollection]
    end

    %% Monitoring Layer
    subgraph MONITORING["COUCHE MONITORING"]
        Prometheus[Metriques Prometheus\n- query_counter\n- response_time_histogram\n- cache_hit_counter]
        HealthCheck[Health Checks\n- Components Status\n- Provider Status]
        Logging[Logging Structure]
    end

    %% Main RAG Orchestrator
    RAGSystem[UltraPerformantRAG\nOrchestrateur Principal]

    %% Data Flows - Document Processing
    FastAPI --> DocLoaders
    DocLoaders --> TextProcess
    TextProcess --> AdvChunker
    AdvChunker --> AdvEmbed
    AdvEmbed --> EmbedFunc
    EmbedFunc --> Collection
    Collection --> ChromaDB
    AdvChunker --> BM25

    %% Data Flows - Query Processing
    FastAPI --> RAGSystem
    RAGSystem --> QueryEnh
    QueryEnh --> OptLLM
    RAGSystem --> HybridSearch
    HybridSearch --> ChromaQuery
    HybridSearch --> BM25
    ChromaQuery --> ChromaDB
    ChromaQuery --> Fusion
    BM25 --> Fusion
    Fusion --> Dedup
    Dedup --> AdvReranker
    AdvReranker --> CrossEncoder
    CrossEncoder --> ScoreCombine
    ScoreCombine --> OptLLM
    OptLLM --> PROVIDERS

    %% Cache Interactions
    MCL --> Redis
    MCL --> MemCache
    RAGSystem <--> MCL
    AdvEmbed <--> EmbedCache
    QueryEnh <--> MCL
    AdvReranker <--> MCL

    %% Monitoring Flows
    RAGSystem --> Prometheus
    RAGSystem --> HealthCheck
    RAGSystem --> Logging

    %% Apply styles
    class FastAPI,Endpoints apiLayer
    class MCL,Redis,MemCache,CacheTypes cacheLayer
    class DocLoaders,AdvChunker,TextProcess processingLayer
    class HybridSearch,DENSE,SPARSE,ChromaQuery,BM25,Fusion,Dedup searchLayer
    class OptLLM,PROVIDERS,Mistral,OpenAI,Anthropic,DeepSeek,Groq,ProviderConfig llmLayer
    class ChromaDB,EmbedFunc,Collection storageLayer
    class Prometheus,HealthCheck,Logging monitoringLayer

```

#### Diagramme de Sequence - Pipeline des requêtes

```mermaid
sequenceDiagram
    participant User as Utilisateur
    participant API as FastAPI
    participant RAG as RAG System
    participant Cache as Cache
    participant QE as Query Enhancer
    participant LLM as LLM Provider
    participant HS as Hybrid Search
    participant Dense as ChromaDB
    participant Sparse as BM25
    participant Rerank as Re-ranker
    participant Monitor as Monitoring

    Note over User,Monitor: PIPELINE ULTRA-OPTIMISE DE REQUETE

    %% 1. Requete initiale
    User->>API: POST /ask-question-ultra
    API->>Monitor: Increment query_counter
    API->>RAG: process_query(question, provider)
    
    %% 2. Verification cache complet
    RAG->>Cache: get(full_response_cache_key)
    alt Cache Hit
        Cache-->>RAG: Reponse complete en cache
        RAG-->>API: Reponse immediate
        API-->>User: Reponse (cache hit)
        Monitor->>Monitor: cache_hit_counter++
    else Cache Miss
        Cache-->>RAG: Cache miss
        
        %% 3. Enhancement de requete
        RAG->>QE: enhance_query(question)
        QE->>Cache: get(query_enhancement_cache)
        alt Enhancement cached
            Cache-->>QE: Variantes en cache
        else Generate variants
            QE->>LLM: generate_variants(question)
            LLM-->>QE: Variantes generees
            QE->>Cache: set(variants, ttl=3600)
        end
        QE-->>RAG: [query_original, variant1, variant2]
        
        %% 4. Recherche hybride pour chaque variante
        loop Pour chaque variante
            RAG->>HS: hybrid_search(query_variant)
            
            %% 4a. Recherche Dense
            par Recherche Dense
                HS->>Dense: query(embedding)
                Dense-->>HS: Resultats vectoriels + scores
            
            %% 4b. Recherche Sparse
            and Recherche Sparse
                HS->>Sparse: bm25_query(tokens)
                Sparse-->>HS: Resultats BM25 + scores
            end
            
            %% 4c. Fusion des resultats
            HS->>HS: fusion_scores(dense, sparse, alpha=0.7)
            HS->>HS: deduplicate_and_boost()
            HS-->>RAG: Resultats hybrides
        end
        
        %% 5. Re-ranking avec Cross-Encoder
        RAG->>Rerank: rerank(question, all_results)
        Rerank->>Cache: get(rerank_cache_key)
        alt Rerank cached
            Cache-->>Rerank: Re-ranking en cache
        else Perform reranking
            Rerank->>Rerank: cross_encoder_predict(pairs)
            Rerank->>Rerank: combine_scores(0.3*retrieval + 0.7*rerank)
            Rerank->>Cache: set(rerank_results, ttl=1800)
        end
        Rerank-->>RAG: Top-K resultats classes
        
        %% 6. Construction du contexte optimise
        RAG->>RAG: build_context(ranked_results)
        RAG->>RAG: create_optimized_prompt(context, question)
        
        %% 7. Generation de la reponse
        RAG->>LLM: generate_response(optimized_prompt)
        LLM-->>RAG: Reponse generee
        
        %% 8. Construction reponse finale avec metriques
        RAG->>RAG: build_final_response(answer, metadata)
        
        %% 9. Cache de la reponse complete
        RAG->>Cache: set(full_response, ttl=1800)
        
        %% 10. Mise a jour des metriques
        RAG->>Monitor: update_metrics(response_time, accuracy)
        
        RAG-->>API: Reponse complete + metadonnees
    end
    
    API-->>User: Reponse finale JSON
    
    Note over User,Monitor: Temps total ~500-2000ms selon cache
    
    %% Metriques finales
    rect rgb(240, 248, 255)
        Note over Monitor: METRIQUES CAPTUREES\n- Temps de reponse total\n- Cache hit rates par type\n- Nombre de resultats trouves\n- Performance par provider\n- Erreurs et fallbacks
    end

```

#### Diagramme des flux de donnees

```mermaid
flowchart TD
    %% Style definitions
    classDef inputFlow fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef processingFlow fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef searchFlow fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef cacheFlow fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef outputFlow fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    classDef storageFlow fill:#f1f8e9,stroke:#558b2f,stroke-width:2px

    %% Input Sources
    subgraph INPUT["SOURCES D ENTREE"]
        PDFDoc[Documents PDF]
        WordDoc[Documents Word]
        UserQuery[Requete Utilisateur]
    end

    %% Document Processing Pipeline
    subgraph DOC_PIPELINE["PIPELINE DOCUMENTS"]
        direction TB
        Extract[Extraction Texte\nPyPDF / Docx2txt]
        Clean[Nettoyage Texte\n- Normalisation\n- Suppression caracteres nuls]
        Chunk[Chunking Semantique\n- Taille: 1000 chars\n- Overlap: 200 chars\n- Metadonnees]
        Embed[Generation Embeddings\nall-mpnet-base-v2]
    end

    %% Query Processing Pipeline  
    subgraph QUERY_PIPELINE["PIPELINE REQUETES"]
        direction TB
        QueryEnhance[Amelioration Requete\n- Variantes\n- Reformulations LLM]
        MultiSearch[Recherche Multiple\nPour chaque variante]
        
        subgraph HYBRID["RECHERCHE HYBRIDE"]
            DenseSearch[Dense Search\nChromaDB Vectoriel]
            SparseSearch[Sparse Search\nBM25 Lexical]
            ScoreFusion["Fusion Scores\nalpha × dense + (1 - alpha) × sparse"]
        end
        
        Reranking[Re-ranking\nCross-Encoder\nms-marco-MiniLM]
        ContextBuild[Construction Contexte\nTop-K resultats]
    end

    %% Storage Systems
    subgraph STORAGE["SYSTEMES DE STOCKAGE"]
        direction TB
        ChromaDB[(ChromaDB\nVector Database\n- Collections\n- Embeddings\n- Metadonnees)]
        BM25Index[(Index BM25\nIn-Memory\n- Tokenisation\n- Scores TF-IDF)]
    end

    %% Cache Systems
    subgraph CACHE_SYS["SYSTEMES DE CACHE"]
        direction TB
        Redis[(Redis Cache\nDistribue\nTTL: 30min-1h)]
        MemCache[(Cache Memoire\nLocal LRU\nMax: 1000 items)]
        
        subgraph CACHE_TYPES["Types de Cache"]
            EmbedCache[Embeddings]
            QueryCache[Query Enhancement]  
            RerankCache[Re-ranking]
            ResponseCache[Reponses Completes]
        end
    end

    %% LLM Generation
    subgraph LLM_GEN["GENERATION LLM"]
        direction TB
        ProviderSelect[Selection Provider\nMistral / OpenAI / Claude]
        PromptOpt[Prompt Optimise\nContexte + Instructions]
        ResponseGen[Generation Reponse\nStream / Sync]
    end

    %% Output and Monitoring
    subgraph OUTPUT["SORTIES ET MONITORING"]
        direction TB
        JSONResponse[Reponse JSON\n- Answer\n- Sources\n- Metadonnees\n- Metriques]
        StreamResponse[Reponse Stream\n- Chunks temps reel\n- Metadonnees finales]
        Metrics[Metriques Prometheus\n- Latence\n- Throughput\n- Cache hits\n- Erreurs]
    end

    %% Data Flows
    PDFDoc --> Extract
    WordDoc --> Extract
    Extract --> Clean
    Clean --> Chunk
    Chunk --> Embed
    Embed --> ChromaDB
    Chunk --> BM25Index

    UserQuery --> QueryEnhance
    QueryEnhance --> MultiSearch
    MultiSearch --> DenseSearch
    MultiSearch --> SparseSearch
    DenseSearch --> ChromaDB
    SparseSearch --> BM25Index
    ChromaDB --> ScoreFusion
    BM25Index --> ScoreFusion
    ScoreFusion --> Reranking
    Reranking --> ContextBuild
    ContextBuild --> ProviderSelect

    ProviderSelect --> PromptOpt
    PromptOpt --> ResponseGen
    ResponseGen --> JSONResponse
    ResponseGen --> StreamResponse

    QueryEnhance <--> QueryCache
    Embed <--> EmbedCache  
    Reranking <--> RerankCache
    JSONResponse --> ResponseCache

    QueryCache --> Redis
    EmbedCache --> Redis
    RerankCache --> Redis
    ResponseCache --> Redis
    Redis -.-> MemCache
    MemCache --> CACHE_TYPES

    JSONResponse --> Metrics
    StreamResponse --> Metrics
    ChromaDB --> Metrics
    Redis --> Metrics

    %% Apply styles
    class PDFDoc,WordDoc,UserQuery inputFlow
    class Extract,Clean,Chunk,Embed,QueryEnhance,MultiSearch processingFlow
    class DenseSearch,SparseSearch,ScoreFusion,Reranking,ContextBuild searchFlow
    class Redis,MemCache,EmbedCache,QueryCache,RerankCache,ResponseCache cacheFlow
    class ProviderSelect,PromptOpt,ResponseGen,JSONResponse,StreamResponse outputFlow
    class ChromaDB,BM25Index storageFlow

    %% Performance annotations
    ChromaDB -.->|"50-200 ms"| DenseSearch
    BM25Index -.->|"10-50 ms"| SparseSearch
    Redis -.->|"1-5 ms"| QueryCache
    MemCache -.->|"0.1-1 ms"| EmbedCache



```

### Composants Principaux

- **UltraPerformantRAG** : Moteur RAG principal avec support multimodal
- **MultimodalEmbeddings** : Gestion des embeddings texte et image
- **MultimodalProcessor** : Traitement des documents multimodaux
- **HybridSearch** : Recherche hybride dense/sparse optimisée
- **AdvancedReranker** : Re-ranking avec Cross-Encoder
- **QueryEnhancer** : Amélioration intelligente des requêtes

## 🛠️ Installation

### Prérequis

- Python 3.8+
- CUDA (optionnel, pour GPU)
- Redis (optionnel, pour le cache)
- Tesseract OCR

### Installation rapide

```bash
# Cloner le repository
git clone <repository-url>
cd AI_CSS_Backend

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Installer Tesseract OCR
# Windows: Télécharger depuis https://github.com/UB-Mannheim/tesseract/wiki
# Ubuntu: sudo apt install tesseract-ocr
# macOS: brew install tesseract
```

### Installation avec Docker (Recommandé)

```bash
# Construire l'image
docker build -t rag-multimodal .

# Lancer le conteneur
docker run -p 8000:8000 -v ./data:/app/data rag-multimodal
```

## ⚙️ Configuration

### Variables d'environnement

Créer un fichier `.env` :

```env
# Configuration de base
APP_NAME="RAG Ultra Performant Multimodal"
APP_VERSION="3.1.0"
DEBUG=false

# Providers LLM
MISTRAL_API_KEY=your_mistral_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key

# Redis (optionnel)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Modèles multimodaux
CLIP_MODEL=openai/clip-vit-base-patch32
BLIP_MODEL=Salesforce/blip-image-captioning-base
EMBEDDING_MODEL=sentence-transformers/clip-ViT-B-32-multilingual-v1

# Performance
MAX_WORKERS=4
CACHE_TTL=3600
MAX_CHUNK_SIZE=1000
```

### Configuration avancée

Modifier `app/core/config.py` pour personnaliser :

- Paramètres des modèles
- Seuils de similarité
- Tailles de chunks
- Paramètres de cache

## 🚀 Utilisation

### Démarrage du serveur

```bash
# Développement
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Interface de documentation

Accéder à la documentation interactive :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## 📡 Endpoints API

### 📄 Gestion des documents

#### Upload de document multimodal
```http
POST /upload-multimodal-document
Content-Type: multipart/form-data

file: [fichier PDF/image]
extract_text: true
generate_captions: true
```

#### Upload de document standard
```http
POST /upload-document
Content-Type: multipart/form-data

file: [fichier]
```

#### Liste des documents
```http
GET /multimodal-documents
```

#### Suppression de document
```http
DELETE /documents/{document_id}
```

### 🔍 Recherche et Questions

#### Question multimodale
```http
POST /ask-multimodal-question
Content-Type: application/json

{
  "question": "Votre question",
  "provider": "mistral",
  "content_types": ["document", "image"],
  "top_k": 5,
  "temperature": 0.3,
  "max_tokens": 512
}
```

#### Question avec image
```http
POST /ask-multimodal-with-image
Content-Type: multipart/form-data

question: "Votre question"
query_image: [fichier image]
provider: "mistral"
top_k: 3
```

#### Question streaming
```http
POST /ask-question-stream-ultra
Content-Type: application/json

{
  "question": "Votre question",
  "provider": "mistral"
}
```

### 🖼️ Analyse d'images

#### Analyse d'image standalone
```http
POST /analyze-image
Content-Type: multipart/form-data

file: [fichier image]
```

#### Recherche par similarité d'image
```http
POST /search-by-image
Content-Type: multipart/form-data

file: [fichier image]
top_k: 5
```

### 📊 Monitoring

#### Health check
```http
GET /health
GET /health-multimodal
```

#### Métriques
```http
GET /metrics
GET /performance-metrics
```

#### Capacités multimodales
```http
GET /multimodal-capabilities
```

## 💡 Exemples

### Python Client

```python
import requests
import json

# Upload d'un document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload-multimodal-document',
        files={'file': f},
        data={'extract_text': True, 'generate_captions': True}
    )
    print(response.json())

# Question multimodale
response = requests.post(
    'http://localhost:8000/ask-multimodal-question',
    json={
        'question': 'Quels sont les points clés du document ?',
        'provider': 'mistral',
        'content_types': ['document', 'image'],
        'top_k': 5
    }
)
print(response.json())
```

### JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

// Upload d'un document
const form = new FormData();
form.append('file', fs.createReadStream('document.pdf'));
form.append('extract_text', 'true');

const uploadResponse = await axios.post(
    'http://localhost:8000/upload-multimodal-document',
    form,
    { headers: form.getHeaders() }
);

// Question
const questionResponse = await axios.post(
    'http://localhost:8000/ask-multimodal-question',
    {
        question: 'Résumez le contenu du document',
        provider: 'mistral',
        top_k: 3
    }
);
```

### cURL

```bash
# Upload de document
curl -X POST "http://localhost:8000/upload-multimodal-document" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "extract_text=true" \
  -F "generate_captions=true"

# Question multimodale
curl -X POST "http://localhost:8000/ask-multimodal-question" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quels sont les éléments importants ?",
    "provider": "mistral",
    "top_k": 5
  }'
```

## ⚡ Performance

### Optimisations implémentées

- **Lazy Loading** : Chargement des modèles à la demande
- **Cache intelligent** : Mise en cache des embeddings et résultats
- **Pool de threads** : Traitement parallèle des documents
- **Chunking adaptatif** : Découpage optimisé selon le contenu
- **Compression des embeddings** : Réduction de l'empreinte mémoire

### Benchmarks

| Opération | Temps moyen | Throughput |
|-----------|-------------|------------|
| Upload PDF (10MB) | 2.3s | 4.3 MB/s |
| Question simple | 0.8s | 1.25 req/s |
| Question multimodale | 1.5s | 0.67 req/s |
| Recherche d'image | 0.6s | 1.67 req/s |

### Recommandations de déploiement

- **CPU** : 4+ cores recommandés
- **RAM** : 8GB minimum, 16GB recommandé
- **GPU** : NVIDIA avec 6GB+ VRAM pour de meilleures performances
- **Stockage** : SSD recommandé pour ChromaDB

## 📊 Monitoring

### Métriques Prometheus

Métriques exposées sur `/metrics` :

- `rag_requests_total` : Nombre total de requêtes
- `rag_request_duration_seconds` : Durée des requêtes
- `rag_cache_hits_total` : Hits du cache
- `rag_model_load_duration_seconds` : Temps de chargement des modèles
- `rag_document_processing_duration_seconds` : Temps de traitement des documents

### Logs structurés

Logs au format JSON avec niveaux :
- `INFO` : Opérations normales
- `WARNING` : Situations à surveiller
- `ERROR` : Erreurs nécessitant une attention
- `DEBUG` : Informations de débogage détaillées

### Health Checks

- `/health` : État général du système
- `/health-multimodal` : État des composants multimodaux
- Vérification automatique des modèles et de la base de données

## 🔧 Développement

### Structure du projet

```
app/
├── api/
│   └── endpoints.py          # Endpoints FastAPI
├── core/
│   ├── config.py            # Configuration
│   ├── embeddings.py        # Embeddings texte
│   ├── multimodal_embeddings.py  # Embeddings multimodaux
│   ├── multimodal_processor.py   # Traitement multimodal
│   ├── multimodal_models.py      # Modèles IA
│   ├── search.py            # Recherche hybride
│   ├── reranker.py          # Re-ranking
│   ├── chunker.py           # Découpage de documents
│   ├── query_enhancer.py    # Amélioration de requêtes
│   ├── llm_provider.py      # Providers LLM
│   └── cache.py             # Système de cache
├── models/
│   ├── schemas.py           # Schémas Pydantic
│   └── enums.py             # Énumérations
├── services/
│   ├── rag_service.py       # Service RAG principal
│   └── document_service.py  # Service de documents
├── utils/
│   ├── logging.py           # Configuration des logs
│   └── helpers.py           # Fonctions utilitaires
└── main.py                  # Point d'entrée FastAPI
```

### Tests

```bash
# Lancer tous les tests
pytest

# Tests avec couverture
pytest --cov=app

# Tests spécifiques
pytest tests/test_multimodal.py
```

### Scripts de test

Plusieurs scripts de test sont disponibles :

- `test_multimodal_upload.py` : Test d'upload multimodal
- `test_multimodal_question.py` : Test de questions multimodales
- `test_multimodal_capabilities.py` : Test des capacités
- `test_standard_upload_delete.py` : Test CRUD documents

### Linting et formatage

```bash
# Black pour le formatage
black app/

# isort pour les imports
isort app/

# flake8 pour le linting
flake8 app/
```

## 🤝 Contribution

### Guidelines

1. **Fork** le repository
2. **Créer** une branche feature (`git checkout -b feature/amazing-feature`)
3. **Commiter** les changements (`git commit -m 'Add amazing feature'`)
4. **Pousser** vers la branche (`git push origin feature/amazing-feature`)
5. **Ouvrir** une Pull Request

### Standards de code

- Suivre PEP 8
- Documenter les fonctions avec docstrings
- Ajouter des tests pour les nouvelles fonctionnalités
- Maintenir une couverture de tests > 80%

### Roadmap

- [ ] Support vidéo et audio
- [ ] Interface web React
- [ ] API GraphQL
- [ ] Support de bases de données vectorielles additionnelles
- [ ] Intégration Kubernetes
- [ ] Support multi-tenant

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🆘 Support

- **Documentation** : Consultez la documentation interactive sur `/docs`
- **Issues** : Ouvrez une issue sur GitHub pour les bugs
- **Discussions** : Utilisez les discussions GitHub pour les questions

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) pour le framework web
- [ChromaDB](https://www.trychroma.com/) pour la base de données vectorielle
- [Sentence Transformers](https://www.sbert.net/) pour les embeddings
- [Hugging Face](https://huggingface.co/) pour les modèles pré-entraînés
- [OpenAI CLIP](https://openai.com/blog/clip/) pour la vision par ordinateur

---

**Développé avec ❤️ pour la communauté IA**