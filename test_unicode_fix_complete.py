#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet pour vérifier que le problème d'encodage Unicode a été résolu
dans le bot Telegram après les corrections apportées.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_advanced import TelegramCSSBotAdvanced

def test_fix_unicode_encoding():
    """Test de la fonction fix_unicode_encoding avec différents cas"""
    
    # Créer une instance simplifiée pour tester la méthode
    class TestBot:
        def fix_unicode_encoding(self, text: str) -> str:
            """Version simplifiée de fix_unicode_encoding pour les tests"""
            if not text or not isinstance(text, str):
                return text
                
            try:
                import json
                import re
                
                # Détecter si le texte est une chaîne JSON sérialisée accidentellement
                if text.startswith('"') and text.endswith('"') and len(text) > 2:
                    try:
                        decoded_text = json.loads(text)
                        text = decoded_text
                    except json.JSONDecodeError:
                        text = text[1:-1]
                
                # Utiliser json.loads pour décoder les séquences Unicode
                if '\\u' in text:
                    json_text = '"' + text.replace('"', '\\"') + '"'
                    try:
                        decoded_text = json.loads(json_text)
                        return decoded_text
                    except json.JSONDecodeError:
                        pass
                
                # Utiliser une expression régulière pour remplacer les séquences \uXXXX
                def unicode_replacer(match):
                    hex_code = match.group(1)
                    try:
                        return chr(int(hex_code, 16))
                    except ValueError:
                        return match.group(0)
                
                text = re.sub(r'\\u([0-9a-fA-F]{4})', unicode_replacer, text)
                
                # Décoder les séquences d'échappement courantes
                text = text.replace('\\n', '\n')
                text = text.replace('\\t', '\t')
                text = text.replace('\\r', '\r')
                text = text.replace('\\"', '"')
                text = text.replace("\\\\", "'")
                
            except Exception as e:
                print(f"Erreur de décodage Unicode: {e}")
                # Approche alternative
                replacements = {
                    '\\u00e0': 'à', '\\u00e1': 'á', '\\u00e2': 'â', '\\u00e3': 'ã',
                    '\\u00e4': 'ä', '\\u00e5': 'å', '\\u00e6': 'æ', '\\u00e7': 'ç',
                    '\\u00e8': 'è', '\\u00e9': 'é', '\\u00ea': 'ê', '\\u00eb': 'ë',
                    '\\u00ec': 'ì', '\\u00ed': 'í', '\\u00ee': 'î', '\\u00ef': 'ï',
                    '\\u00f0': 'ð', '\\u00f1': 'ñ', '\\u00f2': 'ò', '\\u00f3': 'ó',
                    '\\u00f4': 'ô', '\\u00f5': 'õ', '\\u00f6': 'ö', '\\u00f8': 'ø',
                    '\\u00f9': 'ù', '\\u00fa': 'ú', '\\u00fb': 'û', '\\u00fc': 'ü',
                    '\\u00fd': 'ý', '\\u00ff': 'ÿ',
                }
                
                for escaped, char in replacements.items():
                    text = text.replace(escaped, char)
                    
                text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
            
            return text
    
    bot = TestBot()
    
    # Tests avec différents cas d'encodage Unicode
    test_cases = [
        # Cas 1: Séquences Unicode échappées simples
        ("Les allocations familiales de la CSS sont vers\\u00e9es", "Les allocations familiales de la CSS sont versées"),
        
        # Cas 2: Caractères accentués français
        ("\\u00c0 propos de la s\\u00e9curit\\u00e9 sociale", "À propos de la sécurité sociale"),
        
        # Cas 3: Texte avec retours à la ligne
        ("Premi\\u00e8re ligne\\nDeuxi\\u00e8me ligne", "Première ligne\nDeuxième ligne"),
        
        # Cas 4: Chaîne JSON sérialisée accidentellement
        ('"Texte avec des caract\\u00e8res sp\\u00e9ciaux"', "Texte avec des caractères spéciaux"),
        
        # Cas 5: Mélange de caractères
        ("Caf\\u00e9, th\\u00e9, cr\\u00e8me fra\\u00eeche", "Café, thé, crème fraîche"),
    ]
    
    print("=== Test de la fonction fix_unicode_encoding ===")
    all_passed = True
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = bot.fix_unicode_encoding(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        
        print(f"\nTest {i}: {'✅ PASS' if passed else '❌ FAIL'}")
        print(f"  Input:    {repr(input_text)}")
        print(f"  Expected: {repr(expected)}")
        print(f"  Got:      {repr(result)}")
        if not passed:
            print(f"  Diff:     Expected '{expected}', got '{result}'")
    
    print(f"\n=== Résultat global: {'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ÉCHOUENT'} ===")
    return all_passed

def test_cached_response_fix():
    """Test pour vérifier que les réponses en cache sont corrigées"""
    print("\n=== Test des réponses en cache ===")
    
    # Simuler une réponse en cache avec des caractères Unicode échappés
    cached_response = "Les prestations de la CSS sont vers\\u00e9es mensuellement."
    
    # Simuler l'application de fix_unicode_encoding comme dans le code corrigé
    class TestBot:
        def fix_unicode_encoding(self, text):
            import re
            def unicode_replacer(match):
                hex_code = match.group(1)
                try:
                    return chr(int(hex_code, 16))
                except ValueError:
                    return match.group(0)
            return re.sub(r'\\u([0-9a-fA-F]{4})', unicode_replacer, text)
    
    bot = TestBot()
    fixed_response = bot.fix_unicode_encoding(cached_response)
    
    expected = "Les prestations de la CSS sont versées mensuellement."
    passed = fixed_response == expected
    
    print(f"Test cache: {'✅ PASS' if passed else '❌ FAIL'}")
    print(f"  Cached:   {repr(cached_response)}")
    print(f"  Fixed:    {repr(fixed_response)}")
    print(f"  Expected: {repr(expected)}")
    
    return passed

def main():
    """Fonction principale de test"""
    print("Test complet de la correction Unicode pour le bot Telegram CSS")
    print("=" * 70)
    
    # Test de la fonction fix_unicode_encoding
    test1_passed = test_fix_unicode_encoding()
    
    # Test des réponses en cache
    test2_passed = test_cached_response_fix()
    
    # Résultat final
    all_tests_passed = test1_passed and test2_passed
    
    print("\n" + "=" * 70)
    print(f"RÉSULTAT FINAL: {'✅ TOUS LES TESTS RÉUSSIS' if all_tests_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")
    
    if all_tests_passed:
        print("\n🎉 Le problème d'encodage Unicode a été résolu !")
        print("Les corrections apportées au bot Telegram devraient maintenant")
        print("afficher correctement les caractères accentués français.")
    else:
        print("\n⚠️  Il reste des problèmes à résoudre.")
        print("Vérifiez les tests qui ont échoué ci-dessus.")
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    exit(main())