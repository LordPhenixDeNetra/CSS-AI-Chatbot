#!/usr/bin/env python3

import requests
import json


def test_multimodal_question():
    """Test de l'endpoint ask-multimodal-question"""

    url = "http://localhost:8000/ask-multimodal-question"

    payload = {
        "question": "Parlez moi des prestations",
        "provider": "deepseek",
        "temperature": 0.3,
        "max_tokens": 512,
        "top_k": 3,
        "content_types": ["document"],
        "include_images": True,
        "multimodal_boost": 0.1
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        print("Test de la question multimodale...")
        response = requests.post(url, json=payload, headers=headers)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Question multimodale réussie!")
            print(f"ID de la réponse: {result.get('id')}")
            print(f"Réponse: {result.get('answer', '')[:200]}...")
            print(f"Sources: {len(result.get('sources', []))} documents trouvés")
            print(f"Détails complets: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ Erreur {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Détail de l'erreur: {error_detail}")
            except:
                print(f"Réponse brute: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur. Vérifiez que le serveur est démarré.")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


if __name__ == "__main__":
    test_multimodal_question()
