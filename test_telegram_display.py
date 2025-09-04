import json
import re
from datetime import datetime

def fix_unicode_encoding(text: str) -> str:
    """Version corrigée pour corriger l'encodage Unicode échappé"""
    if not text or not isinstance(text, str):
        return text
    
    # Étape 1: Tenter de décoder avec json.loads si le texte contient des séquences \uXXXX
    if '\\u' in text:
        try:
            # Entourer le texte de guillemets pour json.loads
            decoded = json.loads(f'"{text}"')
            text = decoded
        except (json.JSONDecodeError, ValueError):
            # Fallback: utiliser regex pour remplacer les séquences \uXXXX
            def replace_unicode(match):
                code = match.group(1)
                try:
                    return chr(int(code, 16))
                except ValueError:
                    return match.group(0)
            
            text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
    
    # Étape 2: Remplacer les séquences d'échappement courantes
    replacements = {
        '\\n': '\n',
        '\\t': '\t',
        '\\r': '\r',
        '\\"': '"',
        "\\\'": "'"
    }
    
    for escaped, unescaped in replacements.items():
        if escaped in text:
            text = text.replace(escaped, unescaped)
    
    return text

def test_user_exact_case():
    """Test avec exactement ce que l'utilisateur voit"""
    print("=== Test avec le cas exact de l'utilisateur ===")
    
    # Exactement ce que l'utilisateur voit sur Telegram
    user_text = '"Bonjour,\\n\\nEn tant qu\'assistant de la Caisse de S\\u00e9curit\\u00e9 Sociale du S\\u00e9n\\u00e9gal, je me base strictement sur la documentation officielle fournie pour vous r\\u00e9pondre.\\n\\nMalheureusement, les documents \\u00e0 ma disposition ne contiennent pas d\'information sp\\u00e9cifique sur les modalit\\u00e9s de retrait d\'une carte d\'assur\\u00e9 social.\\n\\nPour obtenir une r\\u00e9ponse pr\\u00e9cise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de S\\u00e9curit\\u00e9 Sociale ou de consulter son site internet officiel.\\n\\nJe reste \\u00e0 votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d\'un dossier, pour lesquelles les informations sont disponibles.", ""'
    
    print("Texte original (ce que voit l'utilisateur):")
    print(repr(user_text))
    print("\n" + "="*50 + "\n")
    
    # Test 1: Appliquer fix_unicode_encoding directement
    print("Test 1: Application directe de fix_unicode_encoding")
    result1 = fix_unicode_encoding(user_text)
    print("Résultat:")
    print(repr(result1))
    print("\nAffichage:")
    print(result1)
    print("\n" + "="*50 + "\n")
    
    # Test 2: Traiter comme JSON d'abord
    print("Test 2: Traitement comme JSON d'abord")
    try:
        # Enlever les guillemets externes et la virgule finale
        clean_text = user_text.strip().rstrip(',').strip('"')
        print(f"Texte nettoyé: {repr(clean_text)}")
        
        # Appliquer fix_unicode_encoding
        result2 = fix_unicode_encoding(clean_text)
        print("Résultat:")
        print(repr(result2))
        print("\nAffichage:")
        print(result2)
    except Exception as e:
        print(f"Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Utiliser json.loads directement
    print("Test 3: Utilisation de json.loads directement")
    try:
        # Extraire juste la partie entre guillemets
        json_part = user_text.split('", "')[0] + '"'
        print(f"Partie JSON: {repr(json_part)}")
        
        result3 = json.loads(json_part)
        print("Résultat:")
        print(repr(result3))
        print("\nAffichage:")
        print(result3)
    except Exception as e:
        print(f"Erreur: {e}")

def test_potential_source():
    """Test pour identifier la source potentielle du problème"""
    print("\n=== Test pour identifier la source du problème ===")
    
    # Simuler une réponse normale
    normal_response = "Bonjour,\n\nEn tant qu'assistant de la Caisse de Sécurité Sociale du Sénégal, je me base strictement sur la documentation officielle fournie pour vous répondre.\n\nMalheureusement, les documents à ma disposition ne contiennent pas d'information spécifique sur les modalités de retrait d'une carte d'assuré social.\n\nPour obtenir une réponse précise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de Sécurité Sociale ou de consulter son site internet officiel.\n\nJe reste à votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d'un dossier, pour lesquelles les informations sont disponibles."
    
    print("Réponse normale:")
    print(repr(normal_response))
    print("\nAffichage:")
    print(normal_response)
    print("\n" + "-"*30 + "\n")
    
    # Simuler une sérialisation JSON accidentelle
    json_serialized = json.dumps(normal_response)
    print("Après sérialisation JSON:")
    print(repr(json_serialized))
    print("\nAffichage:")
    print(json_serialized)
    print("\n" + "-"*30 + "\n")
    
    # Simuler une double sérialisation
    double_serialized = json.dumps(json_serialized)
    print("Après double sérialisation JSON:")
    print(repr(double_serialized))
    print("\nAffichage:")
    print(double_serialized)
    print("\n" + "-"*30 + "\n")
    
    # Test de correction
    print("Correction avec fix_unicode_encoding:")
    corrected = fix_unicode_encoding(json_serialized)
    print(repr(corrected))
    print("\nAffichage:")
    print(corrected)

if __name__ == "__main__":
    test_user_exact_case()
    test_potential_source()