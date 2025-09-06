from PIL import Image
import numpy as np

# Créer une image simple
img = Image.new('RGB', (100, 100), color = (73, 109, 137))

# Sauvegarder l'image
img.save('valid_image.jpg')
print('Image valide créée: valid_image.jpg')
