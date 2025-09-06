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
        "\\\'" : "'"
    }
    
    for escaped, unescaped in replacements.items():
        if escaped in text:
            text = text.replace(escaped, unescaped)
    
    return text

def simulate_telegram_flow():
    """Simule le flux complet du bot Telegram"""
    print("=== Simulation du flux Telegram ===")
    
    # 1. Réponse de l'API (comme elle arrive)
    api_response = {
        "response": "Bonjour,\n\nEn tant qu'assistant de la Caisse de S\u00e9curit\u00e9 Sociale du S\u00e9n\u00e9gal, je me base strictement sur la documentation officielle fournie pour vous r\u00e9pondre.\n\nMalheureusement, les documents \u00e0 ma disposition ne contiennent pas d'information sp\u00e9cifique sur les modalit\u00e9s de retrait d'une carte d'assur\u00e9 social.\n\nPour obtenir une r\u00e9ponse pr\u00e9cise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de S\u00e9curit\u00e9 Sociale ou de consulter son site internet officiel.\n\nJe reste \u00e0 votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d'un dossier, pour lesquelles les informations sont disponibles.",
        "response_id": "test123"
    }
    
    print(f"1. Réponse API brute: {repr(api_response['response'])}")
    
    # 2. Extraction du texte (format_response)
    response_text = api_response.get('response', '')
    print(f"\n2. Texte extrait: {repr(response_text)}")
    
    # 3. Application de fix_unicode_encoding
    fixed_text = fix_unicode_encoding(response_text)
    print(f"\n3. Texte après fix_unicode_encoding: {repr(fixed_text)}")
    
    # 4. Stockage dans l'historique (add_to_history)
    history_entry = {
        'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'question': "Comment retirer ma carte d'assuré social ?",
        'response': fixed_text,  # Le texte corrigé est stocké
        'success': True,
        'query_type': 'standard',
        'response_id': 'test123'
    }
    
    print(f"\n4. Entrée d'historique: {repr(history_entry['response'])}")
    
    # 5. Sérialisation JSON (comme si on sauvegardait en base)
    serialized = json.dumps(history_entry, ensure_ascii=False)
    print(f"\n5. Sérialisé JSON: {repr(serialized)}")
    
    # 6. Désérialisation JSON (comme si on récupérait de la base)
    deserialized = json.loads(serialized)
    print(f"\n6. Désérialisé JSON: {repr(deserialized['response'])}")
    
    # 7. Affichage dans l'historique (show_history_inline)
    displayed_text = deserialized['response']
    print(f"\n7. Texte affiché: {repr(displayed_text)}")
    
    # 8. Vérification finale
    has_escaped_unicode = '\\u' in displayed_text
    has_escaped_newlines = '\\n' in displayed_text
    
    print(f"\n=== RÉSULTATS ===")
    print(f"Contient des \\u échappés: {has_escaped_unicode}")
    print(f"Contient des \\n échappés: {has_escaped_newlines}")
    
    if has_escaped_unicode or has_escaped_newlines:
        print("\n❌ PROBLÈME DÉTECTÉ: Le texte contient encore des séquences échappées")
        print("\nTexte problématique:")
        print(displayed_text)
        
        print("\nTexte après correction supplémentaire:")
        final_fixed = fix_unicode_encoding(displayed_text)
        print(final_fixed)
    else:
        print("\n✅ SUCCÈS: Le texte ne contient plus de séquences échappées")
        print("\nTexte final:")
        print(displayed_text)

def test_double_escaping():
    """Test pour vérifier si le problème vient d'un double échappement"""
    print("\n\n=== Test de double échappement ===")
    
    # Texte comme il apparaît dans le message de l'utilisateur
    user_reported_text = '"Bonjour,\\n\\nEn tant qu\'assistant de la Caisse de S\\u00e9curit\\u00e9 Sociale du S\\u00e9n\\u00e9gal, je me base strictement sur la documentation officielle fournie pour vous r\\u00e9pondre.\\n\\nMalheureusement, les documents \\u00e0 ma disposition ne contiennent pas d\'information sp\\u00e9cifique sur les modalit\\u00e9s de retrait d\'une carte d\'assur\\u00e9 social.\\n\\nPour obtenir une r\\u00e9ponse pr\\u00e9cise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de S\\u00e9curit\\u00e9 Sociale ou de consulter son site internet officiel.\\n\\nJe reste \\u00e0 votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d\'un dossier, pour lesquelles les informations sont disponibles."'
    
    print(f"Texte rapporté par l'utilisateur: {repr(user_reported_text)}")
    
    # Essayer de décoder
    try:
        # Première tentative: json.loads direct
        decoded1 = json.loads(user_reported_text)
        print(f"\nAprès json.loads: {repr(decoded1)}")
        
        # Deuxième correction
        final_text = fix_unicode_encoding(decoded1)
        print(f"\nAprès fix_unicode_encoding: {repr(final_text)}")
        
        print(f"\nTexte final lisible:")
        print(final_text)
        
    except json.JSONDecodeError as e:
        print(f"\nErreur json.loads: {e}")
        
        # Fallback: correction directe
        fixed_text = fix_unicode_encoding(user_reported_text)
        print(f"\nAprès correction directe: {repr(fixed_text)}")
        print(f"\nTexte final:")
        print(fixed_text)

if __name__ == "__main__":
    simulate_telegram_flow()
    test_double_escaping()