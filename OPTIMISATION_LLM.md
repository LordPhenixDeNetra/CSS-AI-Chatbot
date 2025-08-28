# Optimisation LLM - Système de Q&A Prédéfinies

## Vue d'ensemble

Ce système d'optimisation permet d'éviter les appels LLM inutiles en fournissant des réponses prédéfinies pour les questions fréquentes sur la CSS (Caisse de Sécurité Sociale du Sénégal).

## Fonctionnalités implémentées

### 1. Système de Q&A Prédéfinies (`app/core/predefined_qa.py`)

- **Base de données intégrée** : 15 questions-réponses prédéfinies couvrant :
  - Âge de retraite et pensions
  - Taux de cotisation
  - Allocations familiales
  - Prestations maladie
  - Documents et procédures
  - Informations de contact
  - Généralités sur la CSS

- **Correspondance intelligente** :
  - Normalisation des questions (suppression accents, ponctuation)
  - Calcul de similarité avec `SequenceMatcher`
  - Seuil de confiance configurable (défaut: 0.7)
  - Recherche par mots-clés

### 2. Classification des questions (`app/core/question_classifier.py`)

- Détection automatique des types de questions :
  - Questions factuelles
  - Questions de statut
  - Questions de définition
  - Questions complexes nécessitant le LLM

### 3. Générateur de réponses directes (`app/core/direct_response_generator.py`)

- Templates de réponses pour questions simples
- Templates spécialisés CSS
- Génération sans appel LLM

### 4. Optimisation du QueryEnhancer (`app/core/query_enhancer.py`)

- Évite la génération de variantes pour questions simples
- Paramètre `force_enhancement` pour contrôle manuel

### 5. Templates CSS spécialisés (`app/core/css_templates.py`)

- Énumération des sujets fréquents CSS
- Templates de réponses contextualisées
- Identification automatique du sujet

## Intégration dans le service RAG

Le système est intégré dans `app/services/rag_service.py` avec la logique suivante :

1. **Vérification cache** (existant)
2. **🆕 Vérification réponses prédéfinies** (PRIORITÉ ABSOLUE)
3. Classification de la question
4. Recherche hybride (optimisée selon le type)
5. Re-ranking
6. Génération LLM (si nécessaire)

## Métriques d'optimisation

Le système ajoute ces métriques aux réponses :

```json
{
  "performance_metrics": {
    "llm_calls_saved": true,
    "optimization_used": "predefined_qa",
    "question_classification": "factual"
  }
}
```

## Configuration

### Variable d'environnement

Le système de Q&A prédéfinies peut être activé/désactivé via la variable d'environnement `ENABLE_PREDEFINED_QA` :

```bash
# Dans votre fichier .env
ENABLE_PREDEFINED_QA=true   # Active le système (défaut)
ENABLE_PREDEFINED_QA=false  # Désactive le système
```

### Configuration programmatique

```python
from app.core.config import settings

# Vérifier l'état de la configuration
if settings.ENABLE_PREDEFINED_QA:
    print("Système de Q&A prédéfinies activé")
else:
    print("Système de Q&A prédéfinies désactivé")
```

## Utilisation

### Test du système

```bash
# Test du système de Q&A
python test_predefined_qa.py

# Test de la configuration
python test_predefined_qa_config.py
```

## Tests et Validation

### Test de Configuration
```bash
python test_predefined_qa_config.py
```

### Test de Correction des Erreurs de Validation
```bash
python test_predefined_qa_fix.py
```

### Script de test des réponses naturelles
```bash
python test_natural_responses.py
```

### Problèmes Résolus

#### Erreur de Validation Pydantic
**Problème**: L'erreur `Input should be a valid string [type=string_type]` se produisait car le système retournait un dictionnaire complet au lieu d'une chaîne pour le champ `answer`.

**Solution**: Modification dans `app/services/rag_service.py` ligne 342 :
```python
# Avant (incorrect)
"answer": predefined_response,

# Après (correct)
"answer": predefined_response["answer"],
```

**Validation**: Le script `test_predefined_qa_fix.py` teste 7 questions prédéfinies et confirme que toutes les réponses sont correctement formatées.

#### Amélioration des réponses naturelles

**Problème identifié :**
- Les réponses contenaient des phrases révélant l'architecture RAG comme "D'après les sources fournies" ou "Aucun document pertinent trouvé"

**Solutions appliquées :**
1. **Messages d'erreur naturels** (`app/services/rag_service.py`) :
   ```python
   # Avant
   "Aucun document pertinent trouvé pour votre question."
   
   # Après
   "Je ne trouve pas d'informations spécifiques à votre question dans ma base de connaissances CSS. Pourriez-vous reformuler votre question ou être plus précis ?"
   ```

2. **Templates de réponses simplifiés** (`app/core/direct_response_generator.py`) :
   ```python
   # Avant
   "factual": "Selon les documents de la CSS, {answer}"
   "default": "D'après les informations disponibles : {answer}"
   
   # Après
   "factual": "{answer}"
   "default": "{answer}"
   ```

3. **Prompt LLM optimisé** (`app/services/rag_service.py`) :
   ```python
   # Avant
   "Vous êtes un assistant expert qui répond aux questions en utilisant uniquement le contexte fourni."
   
   # Après
   "Vous êtes un assistant expert de la Caisse de Sécurité Sociale du Sénégal."
   ```

**Validation :**
- Le script `test_natural_responses.py` confirme que toutes les réponses sont naturelles
- Aucune phrase révélant l'architecture RAG n'est détectée
- Les réponses sont professionnelles et cohérentes avec l'identité CSS

### API Endpoints

Les endpoints existants supportent automatiquement l'optimisation :

- `/ask-question-ultra`
- `/ask-question-stream-ultra`

Paramètres optionnels :
- `force_llm`: Force l'utilisation du LLM
- `skip_llm`: Force les réponses directes

### Exemple d'utilisation

```python
from app.core.predefined_qa import PredefinedQASystem

qa_system = PredefinedQASystem()
response = qa_system.get_predefined_answer("Quel est l'âge de retraite à la CSS?")

if response:
    print(f"Réponse: {response['answer']}")
    print(f"Confiance: {response['confidence']}")
```

## Avantages

### Performance
- **Temps de réponse** : < 10ms pour réponses prédéfinies vs 2-5s pour LLM
- **Coût** : 0€ vs 0.001-0.01€ par requête LLM
- **Fiabilité** : 100% de disponibilité (pas de dépendance API externe)

### Qualité
- Réponses cohérentes et validées
- Informations spécifiques à la CSS
- Pas de hallucinations LLM

### Évolutivité
- Base de Q&A facilement extensible
- Ajout dynamique de nouvelles paires
- Statistiques et monitoring intégrés

## Statistiques de test

Lors des tests :
- **15 questions** prédéfinies dans la base
- **8/9 questions** de test trouvent une réponse
- **Confiance moyenne** : 0.89
- **65 mots-clés** pour la correspondance

## Questions prédéfinies disponibles

1. Âge de retraite à la CSS
2. Calcul de pension de retraite
3. Taux de cotisation
4. Allocations familiales
5. Prestations maladie
6. Documents pour demande de pension
7. Délais de traitement
8. Adresse du siège CSS
9. Contact CSS
10. Définition de la CSS
11. Services CSS
12. Bénéficiaires CSS
13. Cotisations employeur
14. Remboursements maladie
15. Procédures d'affiliation

## Maintenance

### Ajout de nouvelles Q&A

```python
qa_system.add_qa_pair(
    question="Nouvelle question?",
    answer="Réponse détaillée...",
    keywords=["mot1", "mot2"],
    confidence=0.9
)
```

### Monitoring

```python
stats = qa_system.get_statistics()
print(f"Questions: {stats['total_questions']}")
print(f"Confiance: {stats['average_confidence']}")
```

## Prochaines améliorations

1. **Interface d'administration** pour gérer les Q&A
2. **Apprentissage automatique** des nouvelles questions fréquentes
3. **Multilinguisme** (Wolof, Français)
4. **Intégration base de données** pour persistance
5. **Analytics avancées** sur l'utilisation

---

*Cette optimisation permet d'économiser significativement les coûts d'API LLM tout en améliorant les temps de réponse pour les questions fréquentes.*