#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test en temps réel de l'API streaming pour diagnostiquer le problème d'encodage
"""

import aiohttp
import asyncio
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

async def test_real_streaming():
    """Test l'API streaming en temps réel"""
    print("=== Test API streaming en temps réel ===")
    
    api_url = "http://localhost:8000"
    endpoint = f"{api_url}/ask-question-stream-ultra"
    
    # Question qui devrait contenir des caractères accentués
    question = "quel est le montant des allocations familiales"
    
    payload = {
        "question": question,
        "provider": "mistral",
        "temperature": 0.3,
        "max_tokens": 512,
        "top_k": 3
    }
    
    print(f"Question: {question}")
    print(f"Endpoint: {endpoint}")
    print()
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print("✅ Connexion streaming établie")
                    print()
                    
                    chunk_count = 0
                    response_text = ""
                    
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if line_text.startswith("data: "):
                            try:
                                data = json.loads(line_text[6:])
                                
                                if data.get('type') == 'chunk' and 'content' in data:
                                    chunk_count += 1
                                    chunk_content = data['content']
                                    
                                    print(f"Chunk {chunk_count}:")
                                    print(f"  Brut: {repr(chunk_content)}")
                                    
                                    # Appliquer fix_unicode_encoding
                                    fixed_content = fix_unicode_encoding(chunk_content)
                                    print(f"  Fixé: {repr(fixed_content)}")
                                    print(f"  Affiché: {fixed_content}")
                                    print()
                                    
                                    response_text += fixed_content
                                    
                                    # Arrêter après quelques chunks pour le test
                                    if chunk_count >= 10:
                                        break
                                        
                                elif data.get('type') == 'final':
                                    print("🏁 Streaming terminé")
                                    break
                                    
                                elif data.get('type') == 'error':
                                    print(f"❌ Erreur: {data.get('error')}")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"❌ Erreur JSON: {e}")
                                print(f"   Ligne: {line_text}")
                    
                    print(f"\n=== Résumé ===")
                    print(f"Chunks reçus: {chunk_count}")
                    print(f"Texte final: {response_text[:200]}...")
                    
                    # Vérifier les caractères accentués
                    accented_chars = ['é', 'è', 'à', 'ç', 'ù', 'â', 'ê', 'î', 'ô', 'û']
                    found_chars = []
                    for char in accented_chars:
                        if char in response_text:
                            found_chars.append(char)
                    
                    if found_chars:
                        print(f"✅ Caractères accentués trouvés: {found_chars}")
                    else:
                        print("❌ Aucun caractère accentué trouvé")
                        
                else:
                    print(f"❌ Erreur HTTP: {response.status}")
                    error_text = await response.text()
                    print(f"   Détails: {error_text}")
                    
    except aiohttp.ClientConnectorError:
        print("❌ Impossible de se connecter à l'API")
        print("   Assurez-vous que l'API est démarrée sur http://localhost:8000")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_streaming())