#!/usr/bin/env python3

import requests
import json


def test_multimodal_upload():
    """Test de l'endpoint upload-multimodal-document"""

    url = "http://localhost:8000/upload-multimodal-document"
    params = {
        "extract_text": True,
        "generate_captions": True
    }

    # Test avec le fichier PDF créé
    try:
        with open("test_document.pdf", "rb") as f:
            files = {"file": ("test_document.pdf", f, "application/pdf")}

            print("Test de l'upload multimodal...")
            response = requests.post(url, params=params, files=files)

            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                print("✅ Upload réussi!")
                print(f"Document ID: {result.get('document_id')}")
                print(f"Chunks ajoutés: {result.get('chunks_added')}")
                print(f"Détails: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ Erreur {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"Détail de l'erreur: {error_detail}")
                except:
                    print(f"Réponse brute: {response.text}")

    except FileNotFoundError:
        print("❌ Fichier test_document.pdf non trouvé")
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur. Vérifiez que le serveur est démarré.")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


if __name__ == "__main__":
    test_multimodal_upload()
