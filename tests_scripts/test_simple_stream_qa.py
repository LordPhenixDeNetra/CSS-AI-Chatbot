#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple pour vérifier l'intégration Q&A prédéfinies avec streaming
"""

import requests
import json
import time

def test_simple_predefined_streaming():
    """Test simple de l'endpoint streaming avec une question prédéfinie"""
    print("=== Test simple streaming Q&A prédéfinies ===")
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/ask-question-stream-ultra"
    
    # Test avec une question prédéfinie simple
    question = "Bonjour"
    print(f"Test de la question: '{question}'")
    
    payload = {
        "question": question,
        "provider": "mistral",
        "temperature": 0.3,
        "max_tokens": 512,
        "top_k": 3
    }
    
    try:
        print("Envoi de la requête...")
        response = requests.post(
            endpoint,
            headers={
                "accept": "text/plain",
                "Content-Type": "application/json"
            },
            json=payload,
            stream=True,
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Connexion streaming établie")
            
            chunks_count = 0
            content = ""
            is_predefined = False
            
            print("Lecture du stream...")
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        print(f"Chunk reçu: {data}")
                        
                        if data.get('type') == 'init':
                            metadata = data.get('metadata', {})
                            if metadata.get('provider') == 'predefined_qa':
                                is_predefined = True
                                print("🎯 RÉPONSE PRÉDÉFINIE DÉTECTÉE !")
                        
                        elif data.get('type') == 'chunk':
                            content += data.get('content', '')
                            chunks_count += 1
                        
                        elif data.get('type') == 'final':
                            print(f"Stream terminé. Métadonnées finales: {data.get('metadata', {})}")
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"Erreur JSON: {e}")
                        continue
            
            print(f"\nRésultats:")
            print(f"  Chunks reçus: {chunks_count}")
            print(f"  Contenu: {content}")
            print(f"  Réponse prédéfinie utilisée: {is_predefined}")
            
            if is_predefined:
                print("✅ SUCCESS: L'intégration Q&A prédéfinies fonctionne !")
                return True
            else:
                print("❌ ÉCHEC: Réponse prédéfinie non utilisée")
                return False
        
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_health_check():
    """Vérifie que l'API est accessible"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API accessible")
            return True
        else:
            print(f"❌ API non accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Impossible de contacter l'API: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test simple de l'intégration Q&A prédéfinies avec streaming")
    print("=" * 70)
    
    # Vérification de l'API
    if not test_health_check():
        print("\n❌ L'API n'est pas accessible. Assurez-vous qu'elle est démarrée.")
        exit(1)
    
    # Test principal
    success = test_simple_predefined_streaming()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 SUCCÈS: L'intégration Q&A prédéfinies avec streaming fonctionne !")
    else:
        print("💥 ÉCHEC: L'intégration ne fonctionne pas comme attendu")