#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier l'intégration du système de Q&A prédéfinies
avec l'endpoint streaming /ask-question-stream-ultra
"""

import requests
import json
import time
from typing import Dict, Any

def test_stream_predefined_qa():
    """Test l'endpoint streaming avec des questions prédéfinies"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/ask-question-stream-ultra"
    
    # Questions de test prédéfinies
    test_questions = [
        "Bonjour",
        "quel est l'âge de la retraite",
        "quel est le taux de cotisation css",
        "montant des allocations familiales",
        "comment contacter la css",
        "Question non prédéfinie qui devrait utiliser le LLM"
    ]
    
    print("=== Test du streaming avec Q&A prédéfinies ===")
    print(f"Endpoint testé: {endpoint}")
    print()
    
    success_count = 0
    predefined_count = 0
    total_tests = len(test_questions)
    
    for i, question in enumerate(test_questions, 1):
        print(f"Test {i}/{total_tests}: '{question}'")
        
        payload = {
            "question": question,
            "provider": "mistral",
            "temperature": 0.3,
            "max_tokens": 512,
            "top_k": 3
        }
        
        try:
            start_time = time.time()
            
            response = requests.post(
                endpoint,
                headers={
                    "accept": "text/plain",
                    "Content-Type": "application/json"
                },
                json=payload,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                print("  ✅ Connexion streaming établie")
                
                chunks_received = 0
                full_content = ""
                metadata_init = None
                metadata_final = None
                is_predefined = False
                
                # Lecture du stream
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Enlever "data: "
                            
                            if data.get('type') == 'init':
                                metadata_init = data.get('metadata', {})
                                if metadata_init.get('provider') == 'predefined_qa':
                                    is_predefined = True
                                    print(f"  🎯 Réponse prédéfinie détectée")
                                    print(f"     Question correspondante: {metadata_init.get('matched_question', 'N/A')}")
                                
                            elif data.get('type') == 'chunk':
                                content = data.get('content', '')
                                full_content += content
                                chunks_received += 1
                                
                            elif data.get('type') == 'final':
                                metadata_final = data.get('metadata', {})
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)
                
                print(f"  📊 Chunks reçus: {chunks_received}")
                print(f"  ⏱️  Temps de réponse: {response_time}ms")
                print(f"  📝 Contenu (50 premiers caractères): {full_content[:50]}...")
                
                if is_predefined:
                    predefined_count += 1
                    print(f"  🚀 Optimisation: Réponse prédéfinie utilisée")
                    if metadata_final:
                        print(f"     Confiance: {metadata_final.get('confidence', 'N/A')}")
                        print(f"     Appels LLM économisés: {metadata_final.get('llm_calls_saved', False)}")
                else:
                    print(f"  🔍 Recherche hybride utilisée")
                    if metadata_final:
                        print(f"     Résultats de recherche: {metadata_final.get('search_results', 0)}")
                        print(f"     Résultats classés: {metadata_final.get('ranked_results', 0)}")
                
                success_count += 1
                
            else:
                print(f"  ❌ Erreur HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"  ⏰ Timeout après 30 secondes")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
        
        print()
        time.sleep(1)  # Pause entre les tests
    
    # Résumé des tests
    print("=== Résumé des tests ===")
    print(f"Tests réussis: {success_count}/{total_tests}")
    print(f"Réponses prédéfinies utilisées: {predefined_count}/{total_tests}")
    print(f"Taux de réussite: {(success_count/total_tests)*100:.1f}%")
    print(f"Taux d'optimisation: {(predefined_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("\n🎉 Tous les tests ont réussi !")
        if predefined_count > 0:
            print(f"✨ {predefined_count} questions ont bénéficié de l'optimisation prédéfinie")
    else:
        print(f"\n⚠️  {total_tests - success_count} test(s) ont échoué")
    
    return success_count == total_tests

def test_stream_performance_comparison():
    """Compare les performances entre questions prédéfinies et non prédéfinies"""
    print("\n=== Comparaison des performances ===")
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/ask-question-stream-ultra"
    
    # Test avec question prédéfinie
    predefined_question = "quel est l'âge de la retraite"
    print(f"Test question prédéfinie: '{predefined_question}'")
    
    start_time = time.time()
    response = requests.post(
        endpoint,
        json={
            "question": predefined_question,
            "provider": "mistral",
            "temperature": 0.3,
            "max_tokens": 512,
            "top_k": 3
        },
        stream=True,
        timeout=30
    )
    
    predefined_time = None
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get('type') == 'final':
                    predefined_time = data.get('metadata', {}).get('response_time_ms')
                    break
            except:
                continue
    
    # Test avec question non prédéfinie
    complex_question = "Expliquez-moi en détail le processus de calcul des pensions de retraite avec tous les paramètres"
    print(f"Test question complexe: '{complex_question[:50]}...'")
    
    start_time = time.time()
    response = requests.post(
        endpoint,
        json={
            "question": complex_question,
            "provider": "mistral",
            "temperature": 0.3,
            "max_tokens": 512,
            "top_k": 3
        },
        stream=True,
        timeout=30
    )
    
    complex_time = None
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get('type') == 'final':
                    complex_time = data.get('metadata', {}).get('response_time_ms')
                    break
            except:
                continue
    
    # Comparaison
    if predefined_time and complex_time:
        print(f"\n📊 Résultats de performance:")
        print(f"  Question prédéfinie: {predefined_time}ms")
        print(f"  Question complexe: {complex_time}ms")
        print(f"  Gain de performance: {complex_time - predefined_time:.1f}ms ({((complex_time - predefined_time) / complex_time * 100):.1f}%)")
    else:
        print("❌ Impossible de mesurer les performances")

if __name__ == "__main__":
    print("🧪 Test de l'intégration Q&A prédéfinies avec streaming")
    print("=" * 60)
    
    # Test principal
    success = test_stream_predefined_qa()
    
    # Test de performance
    test_stream_performance_comparison()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Intégration Q&A prédéfinies avec streaming: SUCCÈS")
    else:
        print("❌ Intégration Q&A prédéfinies avec streaming: ÉCHEC")