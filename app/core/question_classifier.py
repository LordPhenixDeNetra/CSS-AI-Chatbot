#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classificateur de questions pour optimiser les réponses RAG
Permet de déterminer le type de question et d'adapter la stratégie de réponse
"""

import re
from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass


class QuestionType(Enum):
    """Types de questions identifiées"""
    FACTUAL = "factual"  # Questions factuelles simples
    PROCEDURAL = "procedural"  # Questions sur les procédures
    COMPARATIVE = "comparative"  # Questions de comparaison
    COMPLEX = "complex"  # Questions complexes nécessitant analyse
    PERSONAL = "personal"  # Questions personnalisées
    STATUS = "status"  # Questions sur le statut
    DEFINITION = "definition"  # Questions de définition
    CALCULATION = "calculation"  # Questions de calcul
    UNKNOWN = "unknown"  # Type non déterminé


@dataclass
class ClassificationResult:
    """Résultat de la classification d'une question"""
    question_type: QuestionType
    confidence: float
    keywords: List[str]
    suggested_strategy: str
    skip_llm: bool = False


class QuestionClassifier:
    """Classificateur de questions pour optimiser les réponses"""

    def __init__(self):
        self.patterns = {
            QuestionType.FACTUAL: [
                r"\b(quel|quelle|quels|quelles)\s+(est|sont)\b",
                r"\b(combien)\b",
                r"\b(où|quand|qui)\b",
                r"\b(âge de retraite|montant|taux|pourcentage)\b"
            ],
            QuestionType.PROCEDURAL: [
                r"\b(comment)\b",
                r"\b(procédure|démarche|étapes)\b",
                r"\b(faire pour|obtenir)\b",
                r"\b(demander|constituer|déposer)\b"
            ],
            QuestionType.COMPARATIVE: [
                r"\b(différence|comparaison|versus|vs)\b",
                r"\b(mieux|meilleur|préférable)\b",
                r"\b(plutôt que|au lieu de)\b"
            ],
            QuestionType.STATUS: [
                r"\b(statut|état|situation)\b",
                r"\b(en cours|traité|validé)\b",
                r"\b(dossier|demande)\s+(est|a été)\b"
            ],
            QuestionType.DEFINITION: [
                r"\b(qu'est-ce que|que signifie|définition)\b",
                r"\b(c'est quoi|signification)\b"
            ],
            QuestionType.CALCULATION: [
                r"\b(calculer|calcul|montant)\b",
                r"\b(pension|allocation|indemnité)\s+(de|sera)\b",
                r"\b(cotisation|contribution)\b"
            ]
        }

        self.css_keywords = [
            "css", "caisse", "sécurité sociale", "retraite", "pension",
            "allocation", "cotisation", "prestation", "assurance",
            "maladie", "maternité", "invalidité", "décès", "famille"
        ]

        self.simple_question_indicators = [
            "quel est", "quelle est", "combien", "où", "quand", "qui"
        ]

    def classify(self, question: str) -> ClassificationResult:
        """Classifie une question et détermine la stratégie optimale"""
        question_lower = question.lower().strip()

        # Détection du type de question
        question_type = self._detect_question_type(question_lower)

        # Calcul de la confiance
        confidence = self._calculate_confidence(question_lower, question_type)

        # Extraction des mots-clés
        keywords = self._extract_keywords(question_lower)

        # Stratégie suggérée
        strategy = self._suggest_strategy(question_type, confidence)

        # Décision de skip LLM
        skip_llm = self._should_skip_llm(question_type, confidence, keywords)

        return ClassificationResult(
            question_type=question_type,
            confidence=confidence,
            keywords=keywords,
            suggested_strategy=strategy,
            skip_llm=skip_llm
        )

    def _detect_question_type(self, question: str) -> QuestionType:
        """Détecte le type de question basé sur les patterns"""
        scores = {}

        for q_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, question, re.IGNORECASE))
                score += matches
            scores[q_type] = score

        # Retourner le type avec le score le plus élevé
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return QuestionType.UNKNOWN

    def _calculate_confidence(self, question: str, question_type: QuestionType) -> float:
        """Calcule la confiance de la classification"""
        if question_type == QuestionType.UNKNOWN:
            return 0.1

        # Facteurs de confiance
        confidence = 0.5  # Base

        # Présence de mots-clés CSS
        css_keywords_found = sum(1 for keyword in self.css_keywords if keyword in question)
        confidence += min(css_keywords_found * 0.1, 0.3)

        # Questions simples
        simple_indicators = sum(1 for indicator in self.simple_question_indicators if indicator in question)
        if simple_indicators > 0:
            confidence += 0.2

        # Longueur de la question (questions courtes souvent plus simples)
        if len(question.split()) <= 10:
            confidence += 0.1

        return min(confidence, 1.0)

    def _extract_keywords(self, question: str) -> List[str]:
        """Extrait les mots-clés pertinents de la question"""
        keywords = []

        # Mots-clés CSS trouvés
        for keyword in self.css_keywords:
            if keyword in question:
                keywords.append(keyword)

        # Mots-clés numériques (âges, montants, etc.)
        numbers = re.findall(r'\b\d+\b', question)
        keywords.extend(numbers)

        # Mots importants (noms, verbes d'action)
        important_words = re.findall(r'\b(retraite|pension|allocation|cotisation|prestation|dossier|demande)\b',
                                     question)
        keywords.extend(important_words)

        return list(set(keywords))  # Supprimer les doublons

    def _suggest_strategy(self, question_type: QuestionType, confidence: float) -> str:
        """Suggère une stratégie de réponse basée sur le type et la confiance"""
        strategies = {
            QuestionType.FACTUAL: "direct_search" if confidence > 0.7 else "enhanced_search",
            QuestionType.PROCEDURAL: "structured_response",
            QuestionType.COMPARATIVE: "multi_source_analysis",
            QuestionType.STATUS: "direct_search",
            QuestionType.DEFINITION: "direct_search",
            QuestionType.CALCULATION: "computational_response",
            QuestionType.COMPLEX: "full_rag_pipeline",
            QuestionType.PERSONAL: "contextual_response",
            QuestionType.UNKNOWN: "full_rag_pipeline"
        }

        return strategies.get(question_type, "full_rag_pipeline")

    def _should_skip_llm(self, question_type: QuestionType, confidence: float, keywords: List[str]) -> bool:
        """Détermine si on peut éviter l'appel LLM"""
        # Conditions pour skip LLM
        skip_conditions = [
            # Questions factuelles simples avec haute confiance
            question_type == QuestionType.FACTUAL and confidence > 0.8,

            # Questions de statut
            question_type == QuestionType.STATUS and confidence > 0.7,

            # Questions de définition simples
            question_type == QuestionType.DEFINITION and confidence > 0.7,

            # Questions avec mots-clés CSS spécifiques
            len(keywords) >= 2 and any(kw in ["âge", "retraite", "montant"] for kw in keywords)
        ]

        return any(skip_conditions)

    def get_statistics(self) -> Dict[str, any]:
        """Retourne les statistiques du classificateur"""
        return {
            "total_patterns": sum(len(patterns) for patterns in self.patterns.values()),
            "question_types": len(QuestionType),
            "css_keywords": len(self.css_keywords),
            "simple_indicators": len(self.simple_question_indicators)
        }
