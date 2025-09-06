#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de la correction Unicode pour le problème Telegram
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_advanced import TelegramCSSBotAdvanced

def test_unicode_fix():
    """Test de la méthode fix_unicode_encoding corrigée"""
    
    # Créer une instance du bot pour accéder à la méthode
    bot = TelegramCSSBotAdvanced()
    
    print("=== Test de correction Unicode ===")
    print()
    
    # Cas 1: Texte avec guillemets (sérialisation JSON accidentelle)
    problematic_text = '"Bonjour,\\n\\nLa s\\u00e9curit\\u00e9 informatique est un domaine crucial qui englobe la protection des syst\\u00e8mes, des r\\u00e9seaux et des donn\\u00e9es contre les menaces num\\u00e9riques. Voici les aspects essentiels :\\n\\n## 1. **Authentification et Contr\\u00f4le d\'Acc\\u00e8s**\\n\\n### Authentification Multi-Facteurs (MFA)\\n- **Quelque chose que vous savez** : mot de passe, PIN\\n- **Quelque chose que vous avez** : t\\u00e9l\\u00e9phone, token, carte \\u00e0 puce\\n- **Quelque chose que vous \\u00eates** : biom\\u00e9trie (empreinte, reconnaissance faciale)"'
    
    print("Texte problématique (avec guillemets):")
    print(repr(problematic_text))
    print()
    
    # Appliquer la correction
    corrected_text = bot.fix_unicode_encoding(problematic_text)
    
    print("Texte corrigé:")
    print(repr(corrected_text))
    print()
    print("Affichage final:")
    print(corrected_text)
    print()
    print("=" * 50)
    print()
    
    # Cas 2: Texte sans guillemets (cas normal)
    normal_text = "S\\u00e9curit\\u00e9 informatique\\nAvec des caract\\u00e8res sp\\u00e9ciaux"
    
    print("Texte normal (sans guillemets):")
    print(repr(normal_text))
    print()
    
    corrected_normal = bot.fix_unicode_encoding(normal_text)
    
    print("Texte normal corrigé:")
    print(repr(corrected_normal))
    print()
    print("Affichage normal:")
    print(corrected_normal)
    print()
    print("=" * 50)
    print()
    
    # Cas 3: Vérification que le problème est résolu
    print("Vérification:")
    print(f"- Contient encore \\u00e9 ? {('\\u00e9' in corrected_text)}")
    print(f"- Contient encore \\n ? {('\\n' in corrected_text)}")
    print(f"- Contient é correctement ? {('é' in corrected_text)}")
    print(f"- Contient des retours à la ligne ? {chr(10) in corrected_text}")
    
if __name__ == "__main__":
    test_unicode_fix()