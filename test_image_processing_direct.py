import os
import sys
from PIL import Image
from app.core.multimodal_processor import MultimodalProcessor
from app.core.multimodal_embeddings import MultimodalEmbeddings

# Chemin vers l'image à tester
image_path = os.path.join(os.getcwd(), "multimodal-documents", "new_valid_image.jpg")

# Vérifier si le fichier existe
if not os.path.exists(image_path):
    print(f"Erreur: Le fichier {image_path} n'existe pas.")
    sys.exit(1)

# Créer une instance des embeddings multimodaux
multimodal_embeddings = MultimodalEmbeddings()

# Créer une instance du processeur multimodal
processor = MultimodalProcessor(multimodal_embeddings)

# Vérifier si le fichier est une image valide avec PIL
try:
    with Image.open(image_path) as img:
        print(f"Image ouverte avec succès: {img.format}, {img.size}, {img.mode}")
        # Tester la fonction process_image_document
        result = processor.process_image_document(image_path)
        print("\nRésultat du traitement:")
        print(f"Métadonnées: {result.get('metadata', {})}")
        print(f"Texte OCR: {result.get('text', '')}")
        print(f"Description: {result.get('description', '')}")
        print(f"Modalités: {result.get('modalities', [])}")
        print("\nTraitement réussi!")
except Exception as e:
    print(f"Erreur lors du traitement de l'image: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
