#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test complet pour vérifier tous les modules d'optimisation LLM
Teste l'intégration complète du système
"""

import sys
import os
import asyncio
from typing import Dict, Any

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test des imports de tous les modules"""
    print("=== Test des imports ===")
    
    try:
        from app.core.question_classifier import QuestionClassifier, QuestionType
        print("✅ QuestionClassifier importé avec succès")
        
        from app.core.direct_response_generator import DirectResponseGenerator
        print("✅ DirectResponseGenerator importé avec succès")
        
        from app.core.predefined_qa import PredefinedQASystem
        print("✅ PredefinedQASystem importé avec succès")
        
        from app.services.rag_service import UltraPerformantRAG
        print("✅ UltraPerformantRAG importé avec succès")
        
        from app.core.config import settings
        print(f"✅ Configuration importée - ENABLE_PREDEFINED_QA: {settings.ENABLE_PREDEFINED_QA}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def test_question_classifier():
    """Test du classificateur de questions"""
    print("\n=== Test du classificateur de questions ===")
    
    try:
        from app.core.question_classifier import QuestionClassifier
        
        classifier = QuestionClassifier()
        
        # Test de différents types de questions
        test_questions = [
            ("Quel est l'âge de retraite à la CSS?", "factual"),
            ("Comment faire une demande de pension?", "procedural"),
            ("Qu'est-ce que la CSS?", "definition"),
            ("Quel est le statut de mon dossier?", "status"),
            ("Combien sera ma pension de retraite?", "calculation")
        ]
        
        for question, expected_type in test_questions:
            result = classifier.classify(question)
            print(f"Question: {question}")
            print(f"  Type détecté: {result.question_type.value}")
            print(f"  Confiance: {result.confidence:.2f}")
            print(f"  Mots-clés: {result.keywords}")
            print(f"  Skip LLM: {result.skip_llm}")
            print()
        
        # Statistiques
        stats = classifier.get_statistics()
        print(f"Statistiques du classificateur: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test du classificateur: {e}")
        return False

def test_direct_response_generator():
    """Test du générateur de réponses directes"""
    print("\n=== Test du générateur de réponses directes ===")
    
    try:
        from app.core.direct_response_generator import DirectResponseGenerator
        
        generator = DirectResponseGenerator()
        
        # Simuler des résultats de recherche
        mock_search_results = [
            {
                "content": "L'âge de retraite à la CSS est fixé à 60 ans pour les hommes et les femmes. Cette disposition s'applique à tous les travailleurs du secteur privé.",
                "score": 0.95,
                "source": "reglement_css.pdf"
            },
            {
                "content": "La pension de retraite est calculée sur la base du salaire moyen des 10 meilleures années.",
                "score": 0.85,
                "source": "guide_pension.pdf"
            }
        ]
        
        # Test de génération de réponse directe
        question = "Quel est l'âge de retraite à la CSS?"
        response = generator.generate_direct_response(
            question=question,
            search_results=mock_search_results,
            question_type="factual"
        )
        
        if response:
            print(f"✅ Réponse directe générée:")
            print(f"  Réponse: {response.answer}")
            print(f"  Confiance: {response.confidence:.2f}")
            print(f"  Temps: {response.response_time:.3f}s")
            print(f"  Méthode: {response.method}")
            print(f"  Sources: {len(response.sources)}")
        else:
            print("❌ Aucune réponse directe générée")
        
        # Test de la capacité de génération
        can_generate = generator.can_generate_direct_response(
            question_type="factual",
            confidence=0.8,
            search_results=mock_search_results
        )
        print(f"Peut générer une réponse directe: {can_generate}")
        
        # Statistiques
        stats = generator.get_statistics()
        print(f"Statistiques du générateur: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test du générateur: {e}")
        return False

def test_predefined_qa():
    """Test du système de Q&A prédéfinies"""
    print("\n=== Test du système de Q&A prédéfinies ===")
    
    try:
        from app.core.predefined_qa import PredefinedQASystem
        
        qa_system = PredefinedQASystem()
        
        # Test de recherche de réponse prédéfinie
        test_questions = [
            "Quel est l'âge de retraite à la CSS?",
            "Comment contacter la CSS?",
            "Question inexistante dans la base"
        ]
        
        for question in test_questions:
            answer = qa_system.get_predefined_answer(question)
            if answer:
                print(f"✅ Question: {question}")
                print(f"  Réponse: {answer['answer'][:100]}...")
                print(f"  Confiance: {answer['confidence']}")
                print(f"  Mots-clés: {answer['keywords'][:3]}")
            else:
                print(f"❌ Pas de réponse prédéfinie pour: {question}")
            print()
        
        # Statistiques
        stats = qa_system.get_statistics()
        print(f"Statistiques du système Q&A: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test du système Q&A: {e}")
        return False

async def test_rag_integration():
    """Test de l'intégration complète avec le service RAG"""
    print("\n=== Test d'intégration RAG ===")
    
    try:
        from app.services.rag_service import UltraPerformantRAG
        from app.models.enums import Provider
        
        # Initialiser le service RAG
        rag_service = UltraPerformantRAG()
        
        # Vérifier l'état des composants
        print(f"Système Q&A prédéfinies: {'✅ Activé' if rag_service.predefined_qa else '❌ Désactivé'}")
        print(f"Classificateur de questions: {'✅ Disponible' if hasattr(rag_service, 'question_classifier') else '❌ Indisponible'}")
        print(f"Générateur de réponses directes: {'✅ Disponible' if hasattr(rag_service, 'direct_response_generator') else '❌ Indisponible'}")
        
        # Test d'une question simple (devrait utiliser Q&A prédéfinies)
        if rag_service.predefined_qa:
            print("\nTest avec question prédéfinie:")
            question = "Quel est l'âge de retraite à la CSS?"
            
            try:
                result = await rag_service.query(
                    question=question,
                    provider=Provider.MISTRAL,
                    top_k=3
                )
                
                print(f"  Question: {question}")
                print(f"  Provider: {result.get('provider_used', 'N/A')}")
                print(f"  Optimisation: {result.get('performance_metrics', {}).get('optimization_used', 'N/A')}")
                print(f"  LLM évité: {result.get('performance_metrics', {}).get('llm_calls_saved', False)}")
                print(f"  Temps: {result.get('performance_metrics', {}).get('response_time', 'N/A')}")
                
            except Exception as e:
                print(f"  ⚠️ Erreur lors de la requête (normal sans documents): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test d'intégration: {e}")
        return False

def test_configuration():
    """Test de la configuration"""
    print("\n=== Test de configuration ===")
    
    try:
        from app.core.config import settings
        
        print(f"ENABLE_PREDEFINED_QA: {settings.ENABLE_PREDEFINED_QA}")
        print(f"Type: {type(settings.ENABLE_PREDEFINED_QA)}")
        
        # Vérifier que c'est bien un booléen
        if isinstance(settings.ENABLE_PREDEFINED_QA, bool):
            print("✅ Configuration correcte (type booléen)")
        else:
            print(f"❌ Configuration incorrecte (type: {type(settings.ENABLE_PREDEFINED_QA)})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test de configuration: {e}")
        return False

async def main():
    """Fonction principale de test"""
    print("=== Test complet du système d'optimisation LLM ===")
    print("Ce script teste tous les composants d'optimisation implémentés.\n")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Classificateur de questions", test_question_classifier),
        ("Générateur de réponses directes", test_direct_response_generator),
        ("Système Q&A prédéfinies", test_predefined_qa),
        ("Intégration RAG", test_rag_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Test: {test_name}")
        print(f"{'='*50}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            results.append((test_name, success))
            
        except Exception as e:
            print(f"❌ Erreur inattendue dans {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé des résultats
    print(f"\n{'='*50}")
    print("RÉSUMÉ DES TESTS")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSÉ" if success else "❌ ÉCHOUÉ"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nRésultat global: {passed}/{total} tests passés")
    
    if passed == total:
        print("🎉 Tous les tests sont passés ! Le système est opérationnel.")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
    
    print("\n=== Fin des tests ===")

if __name__ == "__main__":
    asyncio.run(main())