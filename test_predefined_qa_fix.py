#!/usr/bin/env python3
"""
Script de test pour vérifier la correction de l'erreur de validation Pydantic
dans le système de Q&A prédéfinies.
"""

import requests
import json
import time
from typing import Dict, Any

def test_predefined_qa_endpoint():
    """Test l'endpoint avec différentes questions prédéfinies"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/ask-question-ultra"
    
    # Questions de test prédéfinies
    test_questions = [
        "Bonjour",
        "Salut",
        "quel est l'âge de la retraite",
        "quel est le taux de cotisation css",
        "montant des allocations familiales",
        "comment être remboursé par la css",
        "numéro de téléphone css"
    ]
    
    print("=== Test des réponses prédéfinies ===")
    print(f"Endpoint testé: {endpoint}")
    print()
    
    success_count = 0
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
            response = requests.post(
                endpoint,
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Vérifications de validation
                assert "answer" in data, "Champ 'answer' manquant"
                assert isinstance(data["answer"], str), f"Le champ 'answer' doit être une chaîne, reçu: {type(data['answer'])}"
                assert "provider_used" in data, "Champ 'provider_used' manquant"
                assert data["provider_used"] == "predefined_qa", f"Provider attendu: predefined_qa, reçu: {data['provider_used']}"
                
                print(f"  ✅ Succès - Réponse: {data['answer'][:50]}...")
                print(f"  📊 Temps de réponse: {data.get('response_time_ms', 'N/A')} ms")
                
                # Vérification des métadonnées d'optimisation
                if "performance_metrics" in data:
                    metrics = data["performance_metrics"]
                    if "llm_calls_saved" in metrics:
                        print(f"  🚀 Optimisation: Appel LLM évité = {metrics['llm_calls_saved']}")
                
                success_count += 1
                
            else:
                print(f"  ❌ Erreur HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Erreur de connexion: {e}")
        except json.JSONDecodeError as e:
            print(f"  ❌ Erreur de parsing JSON: {e}")
        except AssertionError as e:
            print(f"  ❌ Erreur de validation: {e}")
        except Exception as e:
            print(f"  ❌ Erreur inattendue: {e}")
        
        print()
        time.sleep(0.5)  # Petite pause entre les tests
    
    print("=== Résumé des tests ===")
    print(f"Tests réussis: {success_count}/{total_tests}")
    print(f"Taux de réussite: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 Tous les tests ont réussi ! L'erreur de validation Pydantic est corrigée.")
        return True
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les logs ci-dessus.")
        return False

def test_server_availability():
    """Vérifie que le serveur est disponible"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Serveur disponible")
            return True
        else:
            print(f"❌ Serveur répond avec le code {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ Serveur non disponible. Assurez-vous que l'application est démarrée.")
        return False

if __name__ == "__main__":
    print("Test de correction de l'erreur de validation Pydantic")
    print("=" * 60)
    
    # Vérification de la disponibilité du serveur
    if not test_server_availability():
        print("\n❌ Impossible de continuer les tests sans serveur.")
        exit(1)
    
    print()
    
    # Test des réponses prédéfinies
    success = test_predefined_qa_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCÈS: L'erreur de validation Pydantic a été corrigée !")
        exit(0)
    else:
        print("❌ ÉCHEC: Des problèmes persistent.")
        exit(1)