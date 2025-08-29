#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de réponses directes pour éviter les appels LLM
Permet de générer des réponses basées uniquement sur la recherche vectorielle
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time


@dataclass
class DirectResponse:
    """Réponse directe générée sans LLM"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    response_time: float
    method: str
    metadata: Dict[str, Any]


class DirectResponseGenerator:
    """Générateur de réponses directes basées sur la recherche vectorielle"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.response_templates = {
            "factual": "{answer}",
            "procedural": "Pour {question}, voici la procédure : {answer}",
            "definition": "{term} : {answer}",
            "status": "{answer}",
            "calculation": "{answer}",
            "default": "{answer}"
        }

    def generate_direct_response(
            self,
            question: str,
            search_results: List[Dict[str, Any]],
            question_type: str = "default",
            confidence_threshold: float = 0.7
    ) -> Optional[DirectResponse]:
        """Génère une réponse directe basée sur les résultats de recherche"""
        start_time = time.time()

        try:
            # Vérifier si nous avons des résultats suffisants
            if not search_results or len(search_results) == 0:
                return None

            # Filtrer les résultats par score de confiance
            high_confidence_results = [
                result for result in search_results
                if result.get('score', 0) >= confidence_threshold
            ]

            if not high_confidence_results:
                return None

            # Extraire le contenu le plus pertinent
            best_result = high_confidence_results[0]
            content = best_result.get('content', '')

            # Générer la réponse basée sur le type de question
            answer = self._extract_relevant_answer(content, question, question_type)

            if not answer:
                return None

            # Calculer la confiance globale
            overall_confidence = self._calculate_overall_confidence(
                high_confidence_results, question, answer
            )

            # Formater la réponse
            formatted_answer = self._format_answer(answer, question_type, question)

            response_time = time.time() - start_time

            return DirectResponse(
                answer=formatted_answer,
                confidence=overall_confidence,
                sources=high_confidence_results[:3],  # Top 3 sources
                response_time=response_time,
                method="direct_vectorial_search",
                metadata={
                    "question_type": question_type,
                    "results_count": len(search_results),
                    "high_confidence_count": len(high_confidence_results),
                    "confidence_threshold": confidence_threshold
                }
            )

        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de réponse directe: {e}")
            return None

    def _extract_relevant_answer(self, content: str, question: str, question_type: str) -> str:
        """Extrait la réponse pertinente du contenu"""
        if not content:
            return ""

        # Stratégies d'extraction selon le type de question
        if question_type == "factual":
            return self._extract_factual_answer(content, question)
        elif question_type == "procedural":
            return self._extract_procedural_answer(content)
        elif question_type == "definition":
            return self._extract_definition_answer(content, question)
        elif question_type == "calculation":
            return self._extract_calculation_answer(content)
        else:
            return self._extract_general_answer(content, question)

    def _extract_factual_answer(self, content: str, question: str) -> str:
        """Extrait une réponse factuelle"""
        # Rechercher des phrases contenant des informations factuelles
        sentences = content.split('.')

        # Mots-clés de la question
        question_words = question.lower().split()

        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Ignorer les phrases trop courtes
                continue

            # Calculer le score de pertinence
            score = sum(1 for word in question_words if word in sentence.lower())

            if score > best_score:
                best_score = score
                best_sentence = sentence

        return best_sentence

    def _extract_procedural_answer(self, content: str) -> str:
        """Extrait une réponse procédurale"""
        # Rechercher des listes ou des étapes
        lines = content.split('\n')
        procedural_lines = []

        for line in lines:
            line = line.strip()
            # Détecter les étapes (numérotées ou avec tirets)
            if any(indicator in line.lower() for indicator in ['étape', 'procédure', 'démarche', '1.', '2.', '-', '•']):
                procedural_lines.append(line)

        if procedural_lines:
            return ' '.join(procedural_lines[:3])  # Limiter à 3 étapes

        # Fallback: retourner les premières phrases
        sentences = content.split('.')[:2]
        return '. '.join(sentences) + '.'

    def _extract_definition_answer(self, content: str, question: str) -> str:
        """Extrait une définition"""
        # Rechercher des phrases de définition
        sentences = content.split('.')

        for sentence in sentences:
            sentence = sentence.strip()
            if any(indicator in sentence.lower() for indicator in
                   ['est défini', 'signifie', 'correspond à', 'désigne']):
                return sentence

        # Fallback: première phrase significative
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                return sentence.strip()

        return ""

    def _extract_calculation_answer(self, content: str) -> str:
        """Extrait une réponse de calcul"""
        # Rechercher des montants, pourcentages, etc.
        import re

        # Patterns pour les montants et calculs
        patterns = [
            r'\d+[.,]\d+\s*(?:euros?|€|FCFA|francs?)',
            r'\d+\s*%',
            r'\d+\s*(?:ans?|années?)',
            r'(?:montant|taux|pourcentage)\s*:?\s*\d+'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Retourner le contexte autour du premier match
                match_pos = content.lower().find(matches[0].lower())
                start = max(0, match_pos - 50)
                end = min(len(content), match_pos + 100)
                return content[start:end].strip()

        return self._extract_general_answer(content, "")

    def _extract_general_answer(self, content: str, question: str) -> str:
        """Extrait une réponse générale"""
        # Retourner les premières phrases significatives
        sentences = content.split('.')[:2]
        result = '. '.join(sentence.strip() for sentence in sentences if sentence.strip())

        if result:
            result += '.'

        return result

    def _calculate_overall_confidence(self, results: List[Dict], question: str, answer: str) -> float:
        """Calcule la confiance globale de la réponse"""
        if not results or not answer:
            return 0.0

        # Confiance basée sur les scores des résultats
        avg_score = sum(result.get('score', 0) for result in results) / len(results)

        # Bonus pour la longueur de la réponse (ni trop courte, ni trop longue)
        length_bonus = 0.1 if 20 <= len(answer) <= 200 else 0.0

        # Bonus pour la pertinence (mots de la question dans la réponse)
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        relevance_bonus = len(question_words & answer_words) / max(len(question_words), 1) * 0.2

        total_confidence = min(avg_score + length_bonus + relevance_bonus, 1.0)

        return round(total_confidence, 3)

    def _format_answer(self, answer: str, question_type: str, question: str) -> str:
        """Formate la réponse selon le template approprié"""
        template = self.response_templates.get(question_type, self.response_templates["default"])

        try:
            if question_type == "procedural":
                return template.format(question=question, answer=answer)
            elif question_type == "definition":
                # Extraire le terme à définir
                term = self._extract_term_to_define(question)
                return template.format(term=term, answer=answer)
            else:
                return template.format(answer=answer)
        except KeyError:
            # Fallback si le formatage échoue
            return answer

    def _extract_term_to_define(self, question: str) -> str:
        """Extrait le terme à définir de la question"""
        # Patterns pour extraire le terme
        import re

        patterns = [
            r"qu'est-ce que\s+(.*?)\s*\?",
            r"que signifie\s+(.*?)\s*\?",
            r"définition de\s+(.*?)\s*\?",
            r"c'est quoi\s+(.*?)\s*\?"
        ]

        for pattern in patterns:
            match = re.search(pattern, question.lower())
            if match:
                return match.group(1).strip()

        # Fallback: retourner les derniers mots de la question
        words = question.replace('?', '').split()
        if len(words) >= 2:
            return ' '.join(words[-2:])

        return "le terme"

    def can_generate_direct_response(
            self,
            question_type: str,
            confidence: float,
            search_results: List[Dict]
    ) -> bool:
        """Détermine si une réponse directe peut être générée"""
        # Conditions pour générer une réponse directe
        conditions = [
            confidence >= 0.7,
            len(search_results) > 0,
            question_type in ["factual", "definition", "status", "calculation"],
            any(result.get('score', 0) >= 0.8 for result in search_results)
        ]

        return all(conditions[:2]) and any(conditions[2:])

    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du générateur"""
        return {
            "response_templates": len(self.response_templates),
            "supported_question_types": list(self.response_templates.keys()),
            "extraction_methods": [
                "factual", "procedural", "definition", "calculation", "general"
            ]
        }
