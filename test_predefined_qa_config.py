#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour la configuration du système de Q&A prédéfinies
Permet de tester l'activation/désactivation via variable d'environnement
"""

import os
import sys
import asyncio
from unittest.mock import patch

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_predefined_qa_enabled():
    """Test avec le système de Q&A prédéfinies activé"""
    print("=== Test avec ENABLE_PREDEFINED_QA=true ===")
    
    # Forcer la variable d'environnement
    with patch.dict(os.environ, {'ENABLE_PREDEFINED_QA': 'true'}):
        # Recharger les modules pour prendre en compte la nouvelle config
        if 'app.core.config' in sys.modules:
            del sys.modules['app.core.config']
        if 'app.services.rag_service' in sys.modules:
            del sys.modules['app.services.rag_service']
        
        try:
            from app.core.config import settings
            print(f"Configuration ENABLE_PREDEFINED_QA: {settings.ENABLE_PREDEFINED_QA}")
            
            from app.services.rag_service import UltraPerformantRAG
            
            # Initialisation du service RAG
            rag_service = UltraPerformantRAG()
            
            # Vérifier que le système de Q&A est initialisé
            if rag_service.predefined_qa is not None:
                print("✅ Système de Q&A prédéfinies correctement initialisé")
                
                # Test d'une question prédéfinie
                test_question = "Quel est l'âge de retraite à la CSS?"
                print(f"\nTest de la question: {test_question}")
                
                result = await rag_service.query(
                    question=test_question,
                    provider=Provider.MISTRAL,
                    top_k=3
                )
                
                print(f"Provider utilisé: {result['provider_used']}")
                print(f"Optimisation: {result.get('performance_metrics', {}).get('optimization_used', 'N/A')}")
                print(f"LLM évité: {result.get('performance_metrics', {}).get('llm_calls_saved', False)}")
                
            else:
                print("❌ Système de Q&A prédéfinies non initialisé")
                
        except Exception as e:
            print(f"Erreur lors du test activé: {e}")

async def test_predefined_qa_disabled():
    """Test avec le système de Q&A prédéfinies désactivé"""
    print("\n=== Test avec ENABLE_PREDEFINED_QA=false ===")
    
    # Forcer la variable d'environnement
    with patch.dict(os.environ, {'ENABLE_PREDEFINED_QA': 'false'}):
        # Recharger les modules pour prendre en compte la nouvelle config
        if 'app.core.config' in sys.modules:
            del sys.modules['app.core.config']
        if 'app.services.rag_service' in sys.modules:
            del sys.modules['app.services.rag_service']
        
        try:
            from app.core.config import settings
            print(f"Configuration ENABLE_PREDEFINED_QA: {settings.ENABLE_PREDEFINED_QA}")
            
            from app.services.rag_service import UltraPerformantRAG
            from app.models.enums import Provider
            
            # Initialisation du service RAG
            rag_service = UltraPerformantRAG()
            
            # Vérifier que le système de Q&A n'est pas initialisé
            if rag_service.predefined_qa is None:
                print("✅ Système de Q&A prédéfinies correctement désactivé")
                
                # Test d'une question qui aurait été prédéfinie
                test_question = "Quel est l'âge de retraite à la CSS?"
                print(f"\nTest de la question: {test_question}")
                print("Note: Cette question devrait maintenant utiliser le LLM ou la recherche vectorielle")
                
            else:
                print("❌ Système de Q&A prédéfinies encore initialisé")
                
        except Exception as e:
            print(f"Erreur lors du test désactivé: {e}")

def test_config_parsing():
    """Test du parsing de la configuration"""
    print("\n=== Test du parsing de configuration ===")
    
    test_cases = [
        ('true', True),
        ('True', True),
        ('TRUE', True),
        ('false', False),
        ('False', False),
        ('FALSE', False),
        ('1', False),  # Seul 'true' devrait être accepté
        ('0', False),
        ('', False),   # Valeur vide
    ]
    
    for env_value, expected in test_cases:
        with patch.dict(os.environ, {'ENABLE_PREDEFINED_QA': env_value}):
            # Recharger le module config
            if 'app.core.config' in sys.modules:
                del sys.modules['app.core.config']
            
            try:
                from app.core.config import settings
                result = settings.ENABLE_PREDEFINED_QA
                status = "✅" if result == expected else "❌"
                print(f"{status} '{env_value}' -> {result} (attendu: {expected})")
            except Exception as e:
                print(f"❌ Erreur avec '{env_value}': {e}")

if __name__ == "__main__":
    print("=== Test de configuration du système de Q&A prédéfinies ===")
    
    # Test du parsing de configuration
    test_config_parsing()
    
    # Tests avec activation/désactivation
    try:
        asyncio.run(test_predefined_qa_enabled())
        asyncio.run(test_predefined_qa_disabled())
    except Exception as e:
        print(f"\nErreur lors des tests d'intégration: {e}")
        print("Note: Assurez-vous que les dépendances sont installées")
    
    print("\n=== Tests de configuration terminés ===")
    print("\nPour utiliser cette fonctionnalité:")
    print("1. Ajoutez ENABLE_PREDEFINED_QA=true dans votre fichier .env")
    print("2. Ou définissez la variable d'environnement: export ENABLE_PREDEFINED_QA=false")
    print("3. Redémarrez votre application")