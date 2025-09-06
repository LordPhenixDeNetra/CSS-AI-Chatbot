import requests
import json
from PIL import Image
import io

# Configuration
BASE_URL = "http://localhost:8000"

def test_upload_detailed():
    """Test détaillé de l'upload multimodal avec capture d'erreur"""
    
    print("=== Test Upload Multimodal Détaillé ===")
    
    # Créer une image de test simple
    img = Image.new('RGB', (100, 100), color='green')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    # Test d'upload
    files = {'file': ('test_detailed.jpg', img_bytes.getvalue(), 'image/jpeg')}
    params = {
        'extract_text': True,
        'generate_captions': False
    }
    
    try:
        print("Envoi de la requête d'upload...")
        response = requests.post(f"{BASE_URL}/upload-multimodal-document", files=files, params=params)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Upload réussi!")
            print(f"Response complète: {json.dumps(result, indent=2)}")
            return result.get('document_id')
        else:
            print(f"✗ Erreur upload:")
            print(f"Response text: {response.text}")
            try:
                error_json = response.json()
                print(f"Error JSON: {json.dumps(error_json, indent=2)}")
            except:
                print("Pas de JSON dans la réponse d'erreur")
            return None
            
    except Exception as e:
        print(f"✗ Exception lors de la requête: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_simple_endpoints():
    """Test des endpoints simples pour vérifier la connectivité"""
    
    print("\n=== Test Connectivité ===")
    
    # Test endpoint racine
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Root endpoint: {response.status_code}")
    except Exception as e:
        print(f"Erreur root endpoint: {e}")
    
    # Test health check
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"Health data: {response.json()}")
    except Exception as e:
        print(f"Erreur health endpoint: {e}")
    
    # Test multimodal capabilities
    try:
        response = requests.get(f"{BASE_URL}/multimodal-capabilities")
        print(f"Multimodal capabilities: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Multimodal ready: {data.get('multimodal_ready')}")
            print(f"Components: {data.get('components', {})}")
    except Exception as e:
        print(f"Erreur multimodal capabilities: {e}")

if __name__ == "__main__":
    # Test la connectivité d'abord
    test_simple_endpoints()
    
    # Puis test l'upload
    doc_id = test_upload_detailed()
    
    if doc_id:
        print(f"\n✓ Document créé avec ID: {doc_id}")
    else:
        print(f"\n✗ Échec de l'upload")