#!/usr/bin/env python3

import requests
import json


def test_delete_document():
    """Test de l'endpoint DELETE pour supprimer un document"""

    # D'abord, lister les documents disponibles
    list_url = "http://localhost:8000/documents-advanced"

    try:
        print("Récupération de la liste des documents...")
        list_response = requests.get(list_url)

        if list_response.status_code == 200:
            documents = list_response.json()
            print(f"Documents disponibles: {len(documents.get('documents', []))}")

            if documents.get('documents'):
                # Prendre le premier document pour le test
                first_doc = documents['documents'][0]
                document_id = first_doc['document_id']

                print(f"Test de suppression du document: {document_id}")

                # Test de suppression
                delete_url = f"http://localhost:8000/documents/{document_id}"

                headers = {
                    "accept": "application/json"
                }

                delete_response = requests.delete(delete_url, headers=headers)

                print(f"Status Code: {delete_response.status_code}")

                if delete_response.status_code == 200:
                    result = delete_response.json()
                    print("✅ Suppression réussie!")
                    print(f"Message: {result.get('message')}")
                    print(f"Actions effectuées: {result.get('actions', [])}")
                    print(f"Détails complets: {json.dumps(result, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ Erreur {delete_response.status_code}")
                    try:
                        error_detail = delete_response.json()
                        print(f"Détail de l'erreur: {error_detail}")
                    except:
                        print(f"Réponse brute: {delete_response.text}")
            else:
                print("❌ Aucun document disponible pour le test de suppression")
        else:
            print(f"❌ Erreur lors de la récupération des documents: {list_response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur. Vérifiez que le serveur est démarré.")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


if __name__ == "__main__":
    test_delete_document()
