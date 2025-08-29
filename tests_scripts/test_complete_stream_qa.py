#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet de l'intégration Q&A prédéfinies avec l'endpoint streaming
"""

import requests
import json
import time
from typing import Dict, Any, List

def test_streaming_endpoint(question: str, expected_predefined: bool = False) -> Dict[str, Any]:
    """Test une question sur l'endpoint streaming"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/ask-question-stream-ultra"
    
    payload = {
        "question": question,
        "provider": "mistral",
        "temperature": 0.3,
        "max_tokens": 512,
        "top_k": 3
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            endpoint,
            headers={
                "accept": "text/plain",
                "Content-Type": "application/json"
            },
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "question": question
            }
        
        chunks_count = 0
        content = ""
        is_predefined = False
        metadata = {}
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    
                    if data.get('type') == 'init':
                        init_metadata = data.get('metadata', {})
                        if init_metadata.get('provider') == 'predefined_qa':
                            is_predefined = True
                    
                    elif data.get('type') == 'chunk':
                        content += data.get('content', '')
                        chunks_count += 1
                    
                    elif data.get('type') == 'final':
                        metadata = data.get('metadata', {})
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        return {
            "success": True,
            "question": question,
            "content": content,
            "chunks_count": chunks_count,
            "is_predefined": is_predefined,
            "expected_predefined": expected_predefined,
            "predefined_match": is_predefined == expected_predefined,
            "response_time_ms": response_time,
            "metadata": metadata
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "question": question
        }

def run_comprehensive_tests():
    """Exécute une série de tests complets"""
    print("🧪 Test complet de l'intégration Q&A prédéfinies avec streaming")
    print("=" * 80)
    
    # Questions prédéfinies (doivent utiliser le système Q&A)
    predefined_questions = [
        "Bonjour",
        "Salut",
        "Bonsoir",
        "quel est l'âge de la retraite",
        "âge de la retraite",
        "retraite",
        "comment faire une demande de pension",
        "pension",
        "quels sont les documents requis",
        "documents"
    ]
    
    # Questions non prédéfinies (doivent utiliser le RAG normal)
    non_predefined_questions = [
        "Quelle est la capitale du Sénégal?",
        "Comment calculer une intégrale?",
        "Expliquez-moi la théorie de la relativité",
        "Qu'est-ce que l'intelligence artificielle?"
    ]
    
    results = []
    
    print("\n📋 Test des questions prédéfinies:")
    print("-" * 50)
    
    for i, question in enumerate(predefined_questions, 1):
        print(f"\n{i:2d}. Test: '{question}'")
        result = test_streaming_endpoint(question, expected_predefined=True)
        results.append(result)
        
        if result["success"]:
            status = "✅" if result["predefined_match"] else "❌"
            predefined_status = "PRÉDÉFINIE" if result["is_predefined"] else "RAG NORMAL"
            print(f"    {status} {predefined_status} | Chunks: {result['chunks_count']} | Temps: {result['response_time_ms']:.1f}ms")
            print(f"    📝 Réponse: {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}")
        else:
            print(f"    ❌ ERREUR: {result['error']}")
    
    print("\n\n📋 Test des questions non prédéfinies:")
    print("-" * 50)
    
    for i, question in enumerate(non_predefined_questions, 1):
        print(f"\n{i:2d}. Test: '{question}'")
        result = test_streaming_endpoint(question, expected_predefined=False)
        results.append(result)
        
        if result["success"]:
            status = "✅" if result["predefined_match"] else "❌"
            predefined_status = "PRÉDÉFINIE" if result["is_predefined"] else "RAG NORMAL"
            print(f"    {status} {predefined_status} | Chunks: {result['chunks_count']} | Temps: {result['response_time_ms']:.1f}ms")
            print(f"    📝 Réponse: {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}")
        else:
            print(f"    ❌ ERREUR: {result['error']}")
    
    # Analyse des résultats
    print("\n\n📊 ANALYSE DES RÉSULTATS")
    print("=" * 80)
    
    successful_tests = [r for r in results if r["success"]]
    predefined_correct = [r for r in successful_tests if r["predefined_match"] and r["expected_predefined"]]
    non_predefined_correct = [r for r in successful_tests if r["predefined_match"] and not r["expected_predefined"]]
    
    total_tests = len(results)
    successful_count = len(successful_tests)
    predefined_accuracy = len(predefined_correct) / len([r for r in results if r["expected_predefined"]]) * 100
    non_predefined_accuracy = len(non_predefined_correct) / len([r for r in results if not r["expected_predefined"]]) * 100
    
    print(f"📈 Tests réussis: {successful_count}/{total_tests} ({successful_count/total_tests*100:.1f}%)")
    print(f"🎯 Précision questions prédéfinies: {predefined_accuracy:.1f}%")
    print(f"🎯 Précision questions non prédéfinies: {non_predefined_accuracy:.1f}%")
    
    if successful_tests:
        avg_predefined_time = sum(r["response_time_ms"] for r in successful_tests if r["is_predefined"]) / max(1, len([r for r in successful_tests if r["is_predefined"]]))
        avg_rag_time = sum(r["response_time_ms"] for r in successful_tests if not r["is_predefined"]) / max(1, len([r for r in successful_tests if not r["is_predefined"]]))
        
        print(f"⚡ Temps moyen réponses prédéfinies: {avg_predefined_time:.1f}ms")
        print(f"⚡ Temps moyen réponses RAG: {avg_rag_time:.1f}ms")
        
        if avg_predefined_time > 0 and avg_rag_time > 0:
            speedup = avg_rag_time / avg_predefined_time
            print(f"🚀 Accélération: {speedup:.1f}x plus rapide avec Q&A prédéfinies")
    
    # Verdict final
    print("\n" + "=" * 80)
    overall_accuracy = (len(predefined_correct) + len(non_predefined_correct)) / total_tests * 100
    
    if overall_accuracy >= 90:
        print("🎉 SUCCÈS COMPLET: L'intégration Q&A prédéfinies fonctionne parfaitement !")
    elif overall_accuracy >= 70:
        print("✅ SUCCÈS PARTIEL: L'intégration fonctionne bien avec quelques améliorations possibles.")
    else:
        print("❌ ÉCHEC: L'intégration nécessite des corrections importantes.")
    
    print(f"📊 Score global: {overall_accuracy:.1f}%")
    
    return results

if __name__ == "__main__":
    # Vérification de l'API
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ L'API n'est pas accessible. Assurez-vous qu'elle est démarrée.")
            exit(1)
    except Exception as e:
        print(f"❌ Impossible de contacter l'API: {e}")
        exit(1)
    
    # Exécution des tests
    results = run_comprehensive_tests()