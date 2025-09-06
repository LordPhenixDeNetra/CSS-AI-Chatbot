import os
import requests
from PIL import Image

# Chemin vers l'image à tester
image_path = os.path.join(os.getcwd(), "multimodal-documents", "new_valid_image.jpg")

# Vérifier si le fichier existe
if not os.path.exists(image_path):
    print(f"Erreur: Le fichier {image_path} n'existe pas.")
    exit(1)

# Vérifier si l'image est valide avec PIL
try:
    with Image.open(image_path) as img:
        print(f"Image ouverte avec succès: {img.format}, {img.size}, {img.mode}")
        
    # Préparer le fichier pour l'upload
    files = {
        "file": ("new_valid_image.jpg", open(image_path, "rb"), "image/jpeg")
    }
    
    # Envoyer la requête à l'API
    response = requests.post("http://localhost:8000/upload-multimodal", files=files)
    
    # Afficher la réponse
    print(f"Statut: {response.status_code}")
    print(f"Réponse: {response.text}")
    
    # Vérifier les documents multimodaux
    docs_response = requests.get("http://localhost:8000/multimodal-documents")
    print(f"Documents multimodaux: {docs_response.status_code}")
    print(f"Réponse: {docs_response.text[:500]}...")
    
except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
