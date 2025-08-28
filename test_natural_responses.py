#!/usr/bin/env python3
"""
Script de test pour vérifier que les réponses sont naturelles
et ne révèlent pas l'architecture RAG du système.
"""

import requests
import json
import time

def test_server_availability():
    """Test si le serveur est disponible"""
    try:
        response = requests.get("http://localhost:8000/health")
        return response.status_code == 200
    except:
        return False

def test_natural_responses():
    """Test que les réponses sont naturelles et ne révèlent pas l'architecture"""
    
    # Questions de test
    test_questions = [
        "Qu'est-ce que la CSS?",
        "Comment faire une demande de pension?",
        "Quels sont les documents requis pour l'inscription?",
        "Question inexistante sur un sujet non documenté",
        "Quel est le montant des cotisations?"
    ]
    
    # Phrases à éviter (qui révèlent l'architecture)
    forbidden_phrases = [
        "d'après les sources fournies",
        "selon les documents",
        "aucun document pertinent trouvé",
        "dans le contexte fourni",
        "source x",
        "d'après les informations disponibles",
        "selon les documents de la css"
    ]
    
    print("🧪 Test des réponses naturelles...\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"Test {i}: {question}")
        
        try:
            response = requests.post(
                "http://localhost:8000/ask-question-ultra",
                json={"question": question},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "").lower()
                
                print(f"✅ Réponse reçue: {data.get('answer', '')[:100]}...")
                
                # Vérifier qu'aucune phrase interdite n'est présente
                found_forbidden = []
                for phrase in forbidden_phrases:
                    if phrase in answer:
                        found_forbidden.append(phrase)
                
                if found_forbidden:
                    print(f"❌ Phrases révélant l'architecture trouvées: {found_forbidden}")
                else:
                    print("✅ Réponse naturelle - aucune phrase révélant l'architecture")
                    
            else:
                print(f"❌ Erreur HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
            
        print("-" * 50)
        time.sleep(1)

def main():
    print("🚀 Test des réponses naturelles du système CSS\n")
    
    # Vérifier la disponibilité du serveur
    if not test_server_availability():
        print("❌ Serveur non disponible sur http://localhost:8000")
        print("Assurez-vous que le serveur est démarré avec: uvicorn app.main:app --reload")
        return
    
    print("✅ Serveur disponible\n")
    
    # Tester les réponses naturelles
    test_natural_responses()
    
    print("\n🎉 Tests terminés!")
    print("\n📝 Résumé:")
    print("- Les réponses doivent être naturelles et professionnelles")
    print("- Aucune phrase ne doit révéler l'architecture RAG")
    print("- Le système doit se présenter comme un assistant CSS")

if __name__ == "__main__":
    main()