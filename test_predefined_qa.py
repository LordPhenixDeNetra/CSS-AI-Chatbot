#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour le système de Q&A prédéfinies
Permet de tester les réponses prédéfinies sans utiliser le LLM
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.predefined_qa import PredefinedQASystem
from app.models.enums import Provider

async def test_predefined_qa():
    """Test du système de Q&A prédéfinies"""
    print("=== Test du système de Q&A prédéfinies ===")
    
    # Initialisation du système
    qa_system = PredefinedQASystem()
    
    # Questions de test
    test_questions = [
        "Quel est l'âge de retraite à la CSS?",
        "Comment calculer ma pension de retraite?",
        "Quels sont les taux de cotisation?",
        "Comment bénéficier des allocations familiales?",
        "Quels documents pour une demande de pension?",
        "Où se trouve le siège de la CSS?",
        "Comment contacter la CSS?",
        "Qu'est-ce que la CSS?",
        "Question non prédéfinie qui devrait retourner None"
    ]
    
    print(f"\nTest de {len(test_questions)} questions:\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"{i}. Question: {question}")
        
        # Test de la réponse prédéfinie
        response = qa_system.get_predefined_answer(question)
        
        if response:
            print(f"   ✅ Réponse prédéfinie trouvée:")
            print(f"   {response[:100]}..." if len(response) > 100 else f"   {response}")
        else:
            print(f"   ❌ Aucune réponse prédéfinie trouvée")
        
        print()
    
    # Test des statistiques
    print("=== Statistiques du système ===")
    stats = qa_system.get_statistics()
    print(f"Nombre total de questions: {stats['total_questions']}")
    print(f"Confiance moyenne: {stats['average_confidence']:.2f}")
    print(f"Total des mots-clés: {stats['total_keywords']}")
    
    # Test de recherche par mot-clé
    print("\n=== Test de recherche par mot-clé ===")
    keyword_results = qa_system.search_by_keyword("retraite")
    print(f"Résultats pour 'retraite': {len(keyword_results)} trouvé(s)")
    for question, data in keyword_results[:2]:  # Afficher les 2 premiers
        print(f"  - {question[:50]}...")

async def test_integration_with_rag():
    """Test d'intégration avec le service RAG"""
    print("\n=== Test d'intégration avec le service RAG ===")
    
    try:
        from app.services.rag_service import UltraPerformantRAG
        
        # Initialisation du service RAG
        rag_service = UltraPerformantRAG()
        
        # Test avec une question prédéfinie
        test_question = "Quel est l'âge de retraite à la CSS?"
        print(f"Question de test: {test_question}")
        
        # Appel du service RAG
        result = await rag_service.query(
            question=test_question,
            provider=Provider.MISTRAL,
            top_k=3
        )
        
        print(f"\nRésultat:")
        print(f"Provider utilisé: {result['provider_used']}")
        print(f"Modèle utilisé: {result['model_used']}")
        print(f"Temps de réponse: {result['response_time_ms']}ms")
        print(f"Optimisation utilisée: {result.get('performance_metrics', {}).get('optimization_used', 'N/A')}")
        print(f"LLM évité: {result.get('performance_metrics', {}).get('llm_calls_saved', False)}")
        print(f"\nRéponse: {result['answer'][:200]}...")
        
    except Exception as e:
        print(f"Erreur lors du test d'intégration: {e}")
        print("Note: Assurez-vous que ChromaDB et les autres dépendances sont configurées")

if __name__ == "__main__":
    # Test du système de Q&A prédéfinies
    asyncio.run(test_predefined_qa())
    
    # Test d'intégration (optionnel)
    try:
        asyncio.run(test_integration_with_rag())
    except Exception as e:
        print(f"\nTest d'intégration ignoré: {e}")
    
    print("\n=== Tests terminés ===")