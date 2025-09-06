import json
import re

def fix_unicode_encoding_new(text: str) -> str:
    """Version améliorée pour corriger l'encodage Unicode échappé"""
    if not text or not isinstance(text, str):
        return text
    
    print(f"Input text: {repr(text)}")
    
    # Étape 1: Tenter de décoder avec json.loads si le texte contient des séquences \uXXXX
    if '\\u' in text:
        try:
            # Entourer le texte de guillemets pour json.loads
            decoded = json.loads(f'"{text}"')
            print(f"After json.loads: {repr(decoded)}")
            text = decoded
        except (json.JSONDecodeError, ValueError) as e:
            print(f"json.loads failed: {e}")
            # Fallback: utiliser regex pour remplacer les séquences \uXXXX
            def replace_unicode(match):
                code = match.group(1)
                try:
                    return chr(int(code, 16))
                except ValueError:
                    return match.group(0)
            
            text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
            print(f"After regex replacement: {repr(text)}")
    
    # Étape 2: Remplacer les séquences d'échappement courantes
    replacements = {
        '\\n': '\n',
        '\\t': '\t',
        '\\r': '\r',
        '\\"': '"',
        "\\\'" : "'"
    }
    
    for escaped, unescaped in replacements.items():
        if escaped in text:
            text = text.replace(escaped, unescaped)
            print(f"After replacing {escaped}: {repr(text)}")
    
    print(f"Final text: {repr(text)}")
    return text

def test_json_response_simulation():
    """Simule ce qui se passe quand on reçoit une réponse JSON de l'API"""
    print("=== Test de simulation de réponse JSON ===")
    
    # Simuler une réponse JSON brute comme elle pourrait venir de l'API
    raw_json_response = {
        "response": "Bonjour,\n\nEn tant qu'assistant de la Caisse de S\u00e9curit\u00e9 Sociale du S\u00e9n\u00e9gal, je me base strictement sur la documentation officielle fournie pour vous r\u00e9pondre.\n\nMalheureusement, les documents \u00e0 ma disposition ne contiennent pas d'information sp\u00e9cifique sur les modalit\u00e9s de retrait d'une carte d'assur\u00e9 social.\n\nPour obtenir une r\u00e9ponse pr\u00e9cise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de S\u00e9curit\u00e9 Sociale ou de consulter son site internet officiel.\n\nJe reste \u00e0 votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d'un dossier, pour lesquelles les informations sont disponibles.",
        "response_id": "test123"
    }
    
    print(f"Raw JSON response: {raw_json_response}")
    
    # Extraire le texte de réponse
    response_text = raw_json_response.get('response', '')
    print(f"\nExtracted response_text: {repr(response_text)}")
    
    # Appliquer la correction Unicode
    fixed_text = fix_unicode_encoding_new(response_text)
    print(f"\nFixed text: {repr(fixed_text)}")
    
    # Vérifier s'il reste des séquences échappées
    has_escaped_unicode = '\\u' in fixed_text
    has_escaped_newlines = '\\n' in fixed_text
    
    print(f"\nHas escaped unicode: {has_escaped_unicode}")
    print(f"Has escaped newlines: {has_escaped_newlines}")
    
    print(f"\nFinal display text:")
    print(fixed_text)

def test_double_escaped():
    """Test avec du texte doublement échappé"""
    print("\n=== Test de texte doublement échappé ===")
    
    # Texte comme il apparaît dans le message Telegram de l'utilisateur
    telegram_text = '"Bonjour,\\n\\nEn tant qu\'assistant de la Caisse de S\\u00e9curit\\u00e9 Sociale du S\\u00e9n\\u00e9gal, je me base strictement sur la documentation officielle fournie pour vous r\\u00e9pondre.\\n\\nMalheureusement, les documents \\u00e0 ma disposition ne contiennent pas d\'information sp\\u00e9cifique sur les modalit\\u00e9s de retrait d\'une carte d\'assur\\u00e9 social.\\n\\nPour obtenir une r\\u00e9ponse pr\\u00e9cise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de S\\u00e9curit\\u00e9 Sociale ou de consulter son site internet officiel.\\n\\nJe reste \\u00e0 votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d\'un dossier, pour lesquelles les informations sont disponibles."'
    
    print(f"Telegram text: {repr(telegram_text)}")
    
    # Appliquer la correction
    fixed_text = fix_unicode_encoding_new(telegram_text)
    
    print(f"\nFinal display text:")
    print(fixed_text)

if __name__ == "__main__":
    test_json_response_simulation()
    test_double_escaped()