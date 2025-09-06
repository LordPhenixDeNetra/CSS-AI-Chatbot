from PIL import Image
import io

# Tester avec valid_image.jpg
with open('multimodal-documents/valid_image.jpg', 'rb') as f:
    image_content = f.read()

try:
    # Tester si l'image peut être ouverte avec PIL
    print(f'Tentative d\'ouverture de l\'image avec PIL...')
    image = Image.open(io.BytesIO(image_content))
    print(f'Image ouverte avec succès: {image.format}, {image.size}, {image.mode}')
except Exception as e:
    print(f'Erreur: {e}')
