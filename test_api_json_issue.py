#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pour reproduire le problème d'encodage Unicode avec les données JSON de l'API
"""

import json
import sys
import os

# Ajouter le répertoire parent au path pour importer telegram_advanced
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import re

def fix_unicode_encoding(text: str) -> str:
    """Version de la méthode fix_unicode_encoding pour test"""
    if not text or not isinstance(text, str):
        return text
    
    # Étape 1: Détecter et désérialiser les chaînes JSON accidentellement sérialisées
    if text.startswith('"') and text.endswith('"') and ('\\u' in text or '\\n' in text):
        try:
            text = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass
    
    # Étape 2: Tenter de décoder avec json.loads si le texte contient des séquences \uXXXX
    if '\\u' in text:
        try:
            decoded = json.loads(f'"{text}"')
            text = decoded
        except (json.JSONDecodeError, ValueError):
            def replace_unicode(match):
                code = match.group(1)
                try:
                    return chr(int(code, 16))
                except ValueError:
                    return match.group(0)
            
            text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
    
    # Étape 3: Remplacer les séquences d'échappement courantes
    replacements = {
        '\\n': '\n',
        '\\t': '\t',
        '\\r': '\r',
        '\\"': '"',
        "\\'": "'"
    }
    
    for escaped, unescaped in replacements.items():
        if escaped in text:
            text = text.replace(escaped, unescaped)
    
    return text

def test_api_json_encoding():
    """Test l'encodage des données JSON comme elles arrivent de l'API"""
    print("=== Test encodage JSON API ===")
    
    # Simuler exactement ce qui arrive de l'API streaming
    # Cas 1: Chunk avec caractères accentués (comme dans l'API)
    api_chunk_1 = {
        "content": "Les allocations familiales de la CSS sont versées mensuellement. Le montant varie selon le nombre d'enfants à charge et leur âge. Pour un enfant de moins de 14 ans, le montant est de 2 500 FCFA par mois.",
        "type": "chunk"
    }
    
    # Sérialiser comme le fait l'API
    serialized_chunk_1 = json.dumps(api_chunk_1)
    print(f"Chunk sérialisé par l'API: {serialized_chunk_1}")
    
    # Désérialiser comme le fait le bot Telegram
    deserialized_chunk_1 = json.loads(serialized_chunk_1)
    chunk_content_1 = deserialized_chunk_1['content']
    print(f"Contenu après désérialisation: {chunk_content_1}")
    
    # Appliquer fix_unicode_encoding
    fixed_content_1 = fix_unicode_encoding(chunk_content_1)
    print(f"Contenu après fix_unicode_encoding: {fixed_content_1}")
    print()
    
    # Cas 2: Chunk avec caractères Unicode échappés (problème potentiel)
    api_chunk_2 = {
        "content": "Bonjour,\n\nJe peux vous informer sur l'objectif g\u00e9n\u00e9ral des prestations en nature de l'Action Sanitaire et Sociale de la CSS.\n\n**Objectif g\u00e9n\u00e9ral :**\n\nL'objectif principal est de compl\u00e9ter les prestations en esp\u00e8ces pour permettre aux b\u00e9n\u00e9ficiaires d'am\u00e9liorer leurs conditions de vie et leurs modalit\u00e9s d'acc\u00e8s aux soins.",
        "type": "chunk"
    }
    
    # Sérialiser comme le fait l'API
    serialized_chunk_2 = json.dumps(api_chunk_2)
    print(f"Chunk 2 sérialisé par l'API: {serialized_chunk_2}")
    
    # Désérialiser comme le fait le bot Telegram
    deserialized_chunk_2 = json.loads(serialized_chunk_2)
    chunk_content_2 = deserialized_chunk_2['content']
    print(f"Contenu 2 après désérialisation: {chunk_content_2}")
    
    # Appliquer fix_unicode_encoding
    fixed_content_2 = fix_unicode_encoding(chunk_content_2)
    print(f"Contenu 2 après fix_unicode_encoding: {fixed_content_2}")
    print()
    
    # Cas 3: Double sérialisation (problème potentiel)
    # Simuler une double sérialisation accidentelle
    double_serialized = json.dumps(serialized_chunk_2)
    print(f"Double sérialisation: {double_serialized}")
    
    # Première désérialisation
    first_deser = json.loads(double_serialized)
    print(f"Première désérialisation: {first_deser}")
    
    # Deuxième désérialisation
    second_deser = json.loads(first_deser)
    chunk_content_3 = second_deser['content']
    print(f"Contenu après double désérialisation: {chunk_content_3}")
    
    # Appliquer fix_unicode_encoding
    fixed_content_3 = fix_unicode_encoding(chunk_content_3)
    print(f"Contenu après fix_unicode_encoding (double): {fixed_content_3}")
    print()
    
    # Vérifier si les caractères sont correctement décodés
    print("=== Vérification des caractères ===")
    test_chars = ['é', 'è', 'à', 'ç', 'ù']
    for char in test_chars:
        if char in fixed_content_2:
            print(f"✅ Caractère '{char}' trouvé dans le contenu fixé")
        else:
            print(f"❌ Caractère '{char}' manquant dans le contenu fixé")
    
    # Vérifier les retours à la ligne
    if '\n' in fixed_content_2:
        print("✅ Retours à la ligne préservés")
    else:
        print("❌ Retours à la ligne perdus")

if __name__ == "__main__":
    test_api_json_encoding()