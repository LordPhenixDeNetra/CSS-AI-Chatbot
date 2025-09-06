from pathlib import Path
from PIL import Image
import io
import sys

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
sys.path.append('.')

from app.core.multimodal_processor import MultimodalProcessor
from app.core.multimodal_embeddings import MultimodalEmbeddings

# Créer une instance de MultimodalEmbeddings et MultimodalProcessor
multimodal_embeddings = MultimodalEmbeddings()
multimodal_processor = MultimodalProcessor(multimodal_embeddings)

# Tester avec valid_image.jpg
image_path = Path('multimodal-documents/valid_image.jpg')
with open(image_path, 'rb') as f:
    image_content = f.read()

try:
    # Tester si l'image peut être ouverte avec PIL
    print(f'Tentative d\'ouverture de l\'image avec PIL...')
    image = Image.open(io.BytesIO(image_content))
    print(f'Image ouverte avec succès: {image.format}, {image.size}, {image.mode}')
    
    # Tester la fonction process_image_document
    print(f'Tentative de traitement avec process_image_document...')
    result = multimodal_processor.process_image_document(
        image_content, 
        'valid_image.jpg', 
        extract_text=False, 
        generate_captions=False
    )
    print(f'Traitement réussi!')
    print(f'Métadonnées: {result["metadata"]}')
    
except Exception as e:
    print(f'Erreur: {e}')
