#!/usr/bin/env python3
"""
Script de test pour l'endpoint /multimodal-capabilities
"""

import requests
import json


def test_multimodal_capabilities():
    """Teste l'endpoint /multimodal-capabilities"""

    url = "http://localhost:8000/multimodal-capabilities"

    try:
        print("Test de l'endpoint /multimodal-capabilities...")
        print(f"URL: {url}")
        print("-" * 50)

        response = requests.get(url)

        print(f"Code de statut: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ Succès ! Réponse:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Vérifications spécifiques
            print("\n📊 Résumé des capacités:")
            print(f"- Multimodal activé: {data.get('multimodal_enabled', False)}")
            print(f"- Modalités supportées: {', '.join(data.get('supported_modalities', []))}")
            print(f"- Types de contenu: {', '.join(data.get('supported_content_types', []))}")
            print(f"- Formats d'image: {', '.join(data.get('supported_image_formats', []))}")
            print(f"- Device utilisé: {data.get('device', 'N/A')}")

            # Statut des modèles
            models_status = data.get('models_status', {})
            print("\n🤖 Statut des modèles:")
            for model, status in models_status.items():
                emoji = "✅" if status == "loaded" or status == "available" else "❌"
                print(f"  {emoji} {model}: {status}")

        else:
            print(f"\n❌ Erreur {response.status_code}:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Erreur: Impossible de se connecter au serveur. Vérifiez qu'il est démarré.")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


if __name__ == "__main__":
    test_multimodal_capabilities()
