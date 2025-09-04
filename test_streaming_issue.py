#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pour reproduire le problème de streaming Unicode visible dans la capture d'écran
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_advanced import TelegramCSSBotAdvanced

def test_streaming_chunks():
    """Test pour reproduire le problème de chunks streaming"""
    
    # Créer une instance du bot
    bot = TelegramCSSBotAdvanced()
    
    print("=== Test des chunks de streaming ===\n")
    
    # Simuler les chunks comme ils arrivent de l'API de streaming
    # D'après la capture d'écran, le texte contient des \u00e9 et \u00e8
    chunks = [
        '"Les allocations familiales de la CSS sont vers\u00e9es mensuellement. Le montant varie selon le nombre d\'enfants \u00e0 charge et leur \u00e2ge. Pour conna\u00eetre le montant exact applicable \u00e0 votre situation, veuillez consulter le bar\u00e8me en vigueur aupr\u00e8s de votre agence CSS."',
        '"Bonjour,\\n\\nEn me basant sur les informations fournies, je peux vous informer sur l\'objectif g\u00e9n\u00e9ral des prestations en nature de l\'Action Sanitaire, Sociale et Familiale (A.S.S.F).\\n\\nL\'objectif principal de ces prestations est de compl\u00e9ter les prestations en esp\u00e8ces pour prot\u00e9ger la m\u00e8re et l\'enfant en palliant les insuffisances du syst\u00e8me national de sant\u00e9."'
    ]
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i} original:")
        print(repr(chunk))
        print()
        
        # Appliquer fix_unicode_encoding comme dans le code de streaming
        decoded_chunk = bot.fix_unicode_encoding(chunk)
        
        print(f"Chunk {i} après fix_unicode_encoding:")
        print(repr(decoded_chunk))
        print()
        
        print(f"Chunk {i} affichage final:")
        print(decoded_chunk)
        print()
        print("=" * 60)
        print()
    
    # Test avec un chunk qui ne commence/finit pas par des guillemets
    print("Test avec chunk sans guillemets externes:")
    chunk_no_quotes = "Les allocations familiales de la CSS sont vers\u00e9es mensuellement. Le montant varie selon le nombre d'enfants \u00e0 charge et leur \u00e2ge."
    
    print("Original:")
    print(repr(chunk_no_quotes))
    print()
    
    decoded_no_quotes = bot.fix_unicode_encoding(chunk_no_quotes)
    
    print("Après décodage:")
    print(repr(decoded_no_quotes))
    print()
    
    print("Affichage:")
    print(decoded_no_quotes)
    print()
    
    # Vérifications
    print("=== Vérifications ===")
    for i, chunk in enumerate(chunks, 1):
        decoded = bot.fix_unicode_encoding(chunk)
        print(f"Chunk {i}:")
        print(f"  - Contient encore \\u00e9 ? {('\\u00e9' in decoded)}")
        print(f"  - Contient encore \\u00e8 ? {('\\u00e8' in decoded)}")
        print(f"  - Contient encore \\u00e0 ? {('\\u00e0' in decoded)}")
        print(f"  - Contient é correctement ? {('é' in decoded)}")
        print(f"  - Contient è correctement ? {('è' in decoded)}")
        print(f"  - Contient à correctement ? {('à' in decoded)}")
        print(f"  - Contient des retours à la ligne ? {chr(10) in decoded}")
        print()

if __name__ == "__main__":
    test_streaming_chunks()