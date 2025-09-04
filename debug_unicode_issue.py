#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug du problème Unicode dans les réponses Telegram
"""

import json
import re

def fix_unicode_encoding_new(text: str) -> str:
    """Version corrigée de la méthode fix_unicode_encoding"""
    if not text or not isinstance(text, str):
        return text
        
    try:
        # Méthode 1: Utiliser json.loads pour décoder les séquences Unicode
        # Entourer le texte de guillemets pour en faire un JSON valide
        json_text = '"' + text.replace('"', '\\"') + '"'
        try:
            decoded_text = json.loads(json_text)
            return decoded_text
        except json.JSONDecodeError:
            pass
        
        # Méthode 2: Utiliser une expression régulière pour remplacer les séquences \uXXXX
        def unicode_replacer(match):
            hex_code = match.group(1)
            try:
                return chr(int(hex_code, 16))
            except ValueError:
                return match.group(0)  # Retourner la séquence originale si erreur
        
        # Remplacer toutes les séquences \uXXXX
        text = re.sub(r'\\u([0-9a-fA-F]{4})', unicode_replacer, text)
        
        # Décoder les séquences d'échappement courantes
        text = text.replace('\\n', '\n')
        text = text.replace('\\t', '\t')
        text = text.replace('\\r', '\r')
        text = text.replace('\\"', '"')
        text = text.replace("\\\'", "'")
            
    except Exception as e:
        print(f"Erreur de décodage Unicode: {e}")
        # En cas d'erreur, essayer une approche alternative
        try:
            # Approche alternative : remplacer manuellement les séquences courantes
            replacements = {
                '\\u00e0': 'à', '\\u00e1': 'á', '\\u00e2': 'â', '\\u00e3': 'ã',
                '\\u00e4': 'ä', '\\u00e5': 'å', '\\u00e6': 'æ', '\\u00e7': 'ç',
                '\\u00e8': 'è', '\\u00e9': 'é', '\\u00ea': 'ê', '\\u00eb': 'ë',
                '\\u00ec': 'ì', '\\u00ed': 'í', '\\u00ee': 'î', '\\u00ef': 'ï',
                '\\u00f0': 'ð', '\\u00f1': 'ñ', '\\u00f2': 'ò', '\\u00f3': 'ó',
                '\\u00f4': 'ô', '\\u00f5': 'õ', '\\u00f6': 'ö', '\\u00f8': 'ø',
                '\\u00f9': 'ù', '\\u00fa': 'ú', '\\u00fb': 'û', '\\u00fc': 'ü',
                '\\u00fd': 'ý', '\\u00ff': 'ÿ',
                # Majuscules
                '\\u00c0': 'À', '\\u00c1': 'Á', '\\u00c2': 'Â', '\\u00c3': 'Ã',
                '\\u00c4': 'Ä', '\\u00c5': 'Å', '\\u00c6': 'Æ', '\\u00c7': 'Ç',
                '\\u00c8': 'È', '\\u00c9': 'É', '\\u00ca': 'Ê', '\\u00cb': 'Ë',
                '\\u00cc': 'Ì', '\\u00cd': 'Í', '\\u00ce': 'Î', '\\u00cf': 'Ï',
                '\\u00d1': 'Ñ', '\\u00d2': 'Ò', '\\u00d3': 'Ó', '\\u00d4': 'Ô',
                '\\u00d5': 'Õ', '\\u00d6': 'Ö', '\\u00d8': 'Ø', '\\u00d9': 'Ù',
                '\\u00da': 'Ú', '\\u00db': 'Û', '\\u00dc': 'Ü', '\\u00dd': 'Ý',
            }
            
            for escaped, char in replacements.items():
                text = text.replace(escaped, char)
                
            # Nettoyer les séquences d'échappement restantes
            text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
            
        except Exception as e2:
            print(f"Échec de l'approche alternative pour l'Unicode: {e2}")
    
    return text

def test_user_example():
    """Test avec l'exemple exact de l'utilisateur"""
    
    # Texte exact fourni par l'utilisateur
    user_text = '"Bonjour,\\n\\nEn tant qu\'assistant de la Caisse de S\\u00e9curit\\u00e9 Sociale du S\\u00e9n\\u00e9gal, je me base strictement sur la documentation officielle fournie pour vous r\\u00e9pondre.\\n\\nMalheureusement, les documents \\u00e0 ma disposition ne contiennent pas d\'information sp\\u00e9cifique sur les modalit\\u00e9s de retrait d\'une carte d\'assur\\u00e9 social.\\n\\nPour obtenir une r\\u00e9ponse pr\\u00e9cise et officielle, je vous recommande de vous rapprocher directement de votre agence locale de la Caisse de S\\u00e9curit\\u00e9 Sociale ou de consulter son site internet officiel.\\n\\nJe reste \\u00e0 votre disposition pour toute autre question concernant les prestations, les conditions ou la constitution d\'un dossier, pour lesquelles les informations sont disponibles.", ""'
    
    print("=== TEXTE ORIGINAL DE L'UTILISATEUR ===")
    print(repr(user_text))
    print("\n=== AFFICHAGE BRUT ===")
    print(user_text)
    
    print("\n=== APRÈS CORRECTION ===")
    corrected_text = fix_unicode_encoding_new(user_text)
    print(corrected_text)
    
    print("\n=== VÉRIFICATION ===")
    print(f"Contient encore \\u: {'\\u' in corrected_text}")
    
    # Test avec juste la partie problématique
    print("\n=== TEST PARTIE PROBLÉMATIQUE ===")
    problematic_part = "S\\u00e9curit\\u00e9 Sociale du S\\u00e9n\\u00e9gal"
    print(f"Avant: {problematic_part}")
    corrected_part = fix_unicode_encoding_new(problematic_part)
    print(f"Après: {corrected_part}")
    
    # Test avec différents formats
    print("\n=== TESTS DIFFÉRENTS FORMATS ===")
    test_cases = [
        "\\u00e9",  # Simple
        "S\\u00e9curit\\u00e9",  # Dans un mot
        '"S\\u00e9curit\\u00e9"',  # Avec guillemets
        "Bonjour,\\n\\nS\\u00e9curit\\u00e9",  # Avec \n
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case} -> {fix_unicode_encoding_new(test_case)}")

if __name__ == "__main__":
    test_user_example()