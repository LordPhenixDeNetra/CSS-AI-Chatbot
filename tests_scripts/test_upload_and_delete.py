#!/usr/bin/env python3

import requests
import json
import time


def test_upload_and_delete():
    """Test complet: upload puis suppression d'un document"""

    # 1. Upload d'un document
    upload_url = "http://localhost:8000/upload-multimodal-document"

    try:
        print("=== ÉTAPE 1: Upload du document ===")

        with open("test_document.pdf", "rb") as f:
            files = {"file": ("test_document.pdf", f, "application/pdf")}
            data = {
                "extract_text": "true",
                "generate_captions": "true"
            }

            upload_response = requests.post(upload_url, files=files, data=data)

        print(f"Upload Status Code: {upload_response.status_code}")

        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            document_id = upload_result.get("document_id")
            print(f"✅ Upload réussi! Document ID: {document_id}")

            # Attendre un peu pour que l'indexation soit terminée
            time.sleep(2)

            # 2. Vérifier que le document existe
            print("\n=== ÉTAPE 2: Vérification de l'existence ===")
            list_url = "http://localhost:8000/multimodal-documents"
            list_response = requests.get(list_url)

            if list_response.status_code == 200:
                documents = list_response.json()
                print(f"Documents trouvés: {len(documents.get('documents', []))}")

                if documents.get('documents'):
                    # Utiliser le document_id du premier document trouvé
                    actual_doc_id = documents['documents'][0]['document_id']
                    print(f"Document ID trouvé: {actual_doc_id}")

                    # 3. Test de suppression
                    print("\n=== ÉTAPE 3: Suppression du document ===")
                    delete_url = f"http://localhost:8000/documents/{actual_doc_id}"

                    headers = {"accept": "application/json"}
                    delete_response = requests.delete(delete_url, headers=headers)

                    print(f"Delete Status Code: {delete_response.status_code}")

                    if delete_response.status_code == 200:
                        delete_result = delete_response.json()
                        print("✅ Suppression réussie!")
                        print(f"Message: {delete_result.get('message')}")
                        print(f"Actions: {delete_result.get('actions', [])}")

                        # 4. Vérifier que le document a été supprimé
                        print("\n=== ÉTAPE 4: Vérification de la suppression ===")
                        time.sleep(1)
                        final_list_response = requests.get(list_url)

                        if final_list_response.status_code == 200:
                            final_documents = final_list_response.json()
                            print(f"Documents restants: {len(final_documents.get('documents', []))}")

                            if len(final_documents.get('documents', [])) == 0:
                                print("✅ Document supprimé avec succès de la base!")
                            else:
                                print("⚠️ Le document semble encore présent dans la base")

                    else:
                        print(f"❌ Erreur suppression: {delete_response.status_code}")
                        try:
                            error_detail = delete_response.json()
                            print(f"Détail: {error_detail}")
                        except:
                            print(f"Réponse brute: {delete_response.text}")
                else:
                    print("❌ Aucun document trouvé après upload")
            else:
                print(f"❌ Erreur liste documents: {list_response.status_code}")
        else:
            print(f"❌ Erreur upload: {upload_response.status_code}")
            try:
                error_detail = upload_response.json()
                print(f"Détail: {error_detail}")
            except:
                print(f"Réponse brute: {upload_response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


if __name__ == "__main__":
    test_upload_and_delete()
