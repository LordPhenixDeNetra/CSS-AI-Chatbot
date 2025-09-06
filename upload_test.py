import os
import requests
from pathlib import Path

# Chemin du fichier à uploader
file_path = Path('valid_image.jpg')

# URL de l'endpoint
url = 'http://localhost:8000/upload-multimodal-document'

# Paramètres de la requête
params = {
    'extract_text': 'true',
    'generate_captions': 'false'
}

# Vérifier si le fichier existe
if not file_path.exists():
    print(f'Le fichier {file_path} n\'existe pas')
    exit(1)

# Préparer les fichiers pour l'upload
files = {
    'file': (file_path.name, open(file_path, 'rb'), 'image/jpeg')
}

try:
    # Envoyer la requête
    response = requests.post(url, files=files, params=params)
    
    # Afficher le résultat
    print(f'Status code: {response.status_code}')
    print(f'Response: {response.text}')
    
    # Vérifier si le répertoire multimodal-documents existe
    multimodal_dir = Path('multimodal-documents')
    if multimodal_dir.exists():
        print(f'\nContenu du répertoire {multimodal_dir}:')
        for file in multimodal_dir.iterdir():
            print(f'- {file.name}')
    else:
        print(f'\nLe répertoire {multimodal_dir} n\'existe pas')
        
except Exception as e:
    print(f'Erreur: {e}')
finally:
    # Fermer le fichier
    files['file'][1].close()
