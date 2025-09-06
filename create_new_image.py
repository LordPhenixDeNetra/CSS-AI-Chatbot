from PIL import Image
import numpy as np

# Créer une image RGB de 100x100 pixels
img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
img = Image.fromarray(img_array, 'RGB')

# Sauvegarder l'image
img.save('new_valid_image.jpg', format='JPEG')
print('Image créée avec succès: new_valid_image.jpg')

# Copier l'image dans le répertoire multimodal-documents
import shutil
shutil.copy('new_valid_image.jpg', 'multimodal-documents/new_valid_image.jpg')
print('Image copiée dans multimodal-documents/')
