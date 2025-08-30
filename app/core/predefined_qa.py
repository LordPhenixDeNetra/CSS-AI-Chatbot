from typing import Dict, List, Optional, Tuple
import re
from difflib import SequenceMatcher
from app.utils.logging import logger

class PredefinedQASystem:
    """Système de questions-réponses prédéfinies pour éviter les appels LLM inutiles"""
    
    def __init__(self):
        self.qa_database = {
            "Bonjour": {
                "answer": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Bonjour", "salutation"],
                "confidence": 0.95
            },

            "Salut": {
                "answer": "Salut ! Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Salut", "salutation"],
                "confidence": 0.95
            },

            "Comment ça va": {
                "answer": "Bien, merci ! Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Comment", "ça", "va"],
                "confidence": 0.95
            },

            "Comment vous appelez-vous": {
                "answer": "Je m'appelle CSS AI. Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Comment", "vous", "appelez-vous"],
                "confidence": 0.95
            },

            "Comment vous présentez-vous": {
                "answer": "Je suis une intelligence artificielle spécialisée dans la fourniture d'assistance aux citoyens en sénégal. Je suis capable de répondre à vos questions sur la retraite, les cotisations, les allocations familiales et bien plus encore. Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Comment", "vous", "présentez-vous"],
                "confidence": 0.95
            },

            "Comment vous pouvez vous aider": {
                "answer": "Je suis là pour vous aider. Que souhaitez-vous savoir ?",
                "keywords": ["Comment", "vous", "pouvez", "vous", "aider"],
                "confidence": 0.95
            },

            "Quel est votre nom": {
                "answer": "Je m'appelle CSS AI. Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Quel", "est", "votre", "nom"],
                "confidence": 0.95
            },

            "Quel est votre rôle": {
                "answer": "Je suis une intelligence artificielle spécialisée dans la fourniture d'assistance aux citoyens en sénégal. Je suis capable de répondre à vos questions sur la retraite, les cotisations, les allocations familiales et bien plus encore. Comment puis-je vous aider aujourd'hui ?",
                "keywords": ["Quel", "est", "votre", "rôle"],
                "confidence": 0.95
            },

            "Qu'est-ce que la retraite": {
                "answer": "La retraite est une pension sociale offerte aux travailleurs salariés affiliés à la CSS. Elle permet de couvrir les coûts de santé et de retraite des travailleurs en sénégal.",
                "keywords": ["retraite", "pension", "sociale", "affilié"],
                "confidence": 0.95
            },

            "Merci": {
                "answer": "De rien ! N'hésitez pas à me poser d'autres questions.",
                "keywords": ["Merci", "merci"],
                "confidence": 0.95
            },

            "Ok": {
                "answer": "Ok ! N'hésitez pas à me poser d'autres questions.",
                "keywords": ["Ok", "ok"],
                "confidence": 0.95
            },

            # Questions sur l'âge de retraite
            "quel est l'âge de la retraite": {
                "answer": "L'âge légal de départ à la retraite au Sénégal est de 60 ans pour les salariés du secteur privé affiliés à la CSS. Cependant, il est possible de partir en retraite anticipée sous certaines conditions ou de prolonger l'activité jusqu'à 65 ans.",
                "keywords": ["âge", "retraite", "60 ans", "départ", "légal"],
                "confidence": 0.95
            },
            
            "à quel âge peut-on prendre sa retraite": {
                "answer": "Vous pouvez prendre votre retraite à partir de 60 ans si vous êtes affilié à la CSS. L'âge normal de la retraite est fixé à 60 ans, avec possibilité de prolongation jusqu'à 65 ans selon votre situation.",
                "keywords": ["âge", "prendre", "retraite", "60"],
                "confidence": 0.95
            },
            
            # Questions sur les cotisations
            "quel est le taux de cotisation css": {
                "answer": "Le taux de cotisation à la CSS est de 24% du salaire brut, réparti comme suit : 16% à la charge de l'employeur et 8% à la charge du salarié. Ce taux couvre les prestations familiales, la pension de retraite et les risques professionnels.",
                "keywords": ["taux", "cotisation", "24%", "employeur", "salarié"],
                "confidence": 0.9
            },
            
            "combien cotise-t-on à la css": {
                "answer": "Les cotisations à la CSS représentent 24% du salaire brut : 8% sont prélevés sur le salaire du salarié et 16% sont payés par l'employeur. Ces cotisations donnent droit aux prestations sociales.",
                "keywords": ["cotise", "cotisation", "24%", "8%", "16%"],
                "confidence": 0.9
            },
            
            # Questions sur les allocations familiales
            "montant des allocations familiales": {
                "answer": "Les allocations familiales de la CSS sont versées mensuellement. Le montant varie selon le nombre d'enfants à charge et leur âge. Pour connaître le montant exact applicable à votre situation, veuillez consulter le barème en vigueur auprès de votre agence CSS.",
                "keywords": ["montant", "allocations", "familiales", "enfants"],
                "confidence": 0.85
            },
            
            "qui a droit aux allocations familiales": {
                "answer": "Ont droit aux allocations familiales tous les salariés affiliés à la CSS ayant des enfants à charge âgés de moins de 21 ans (ou 25 ans s'ils poursuivent des études). L'enfant doit résider au Sénégal et être déclaré à la CSS.",
                "keywords": ["droit", "allocations", "familiales", "enfants", "21 ans"],
                "confidence": 0.9
            },
            
            # Questions sur les prestations maladie
            "comment être remboursé par la css": {
                "answer": "Pour être remboursé par la CSS, vous devez : 1) Présenter votre carte CSS lors des soins, 2) Conserver tous les justificatifs (ordonnances, factures), 3) Déposer votre dossier de remboursement dans les délais, 4) Attendre le traitement de votre dossier.",
                "keywords": ["remboursé", "remboursement", "carte", "justificatifs"],
                "confidence": 0.85
            },
            
            "quels soins sont couverts par la css": {
                "answer": "La CSS couvre les consultations médicales, les hospitalisations, les médicaments prescrits, les examens de laboratoire, la radiologie, et certains soins dentaires. Le taux de remboursement varie selon le type de soins et le statut de l'établissement.",
                "keywords": ["soins", "couverts", "consultations", "médicaments"],
                "confidence": 0.85
            },
            
            # Questions sur les documents
            "quels documents pour s'inscrire à la css": {
                "answer": "Pour s'inscrire à la CSS, vous devez fournir : une copie de votre pièce d'identité, un certificat de travail, les bulletins de salaire des 3 derniers mois, une fiche d'état civil, et le formulaire d'immatriculation dûment rempli.",
                "keywords": ["documents", "inscrire", "pièce", "identité", "certificat"],
                "confidence": 0.9
            },
            
            "comment obtenir une attestation css": {
                "answer": "Pour obtenir une attestation CSS, rendez-vous dans votre agence CSS avec votre pièce d'identité et votre numéro d'immatriculation. L'attestation peut aussi être demandée en ligne sur le site officiel de la CSS ou par courrier.",
                "keywords": ["attestation", "obtenir", "agence", "identité"],
                "confidence": 0.9
            },
            
            # Questions sur les délais
            "délai de traitement css": {
                "answer": "Les délais de traitement à la CSS varient selon le type de dossier : remboursements maladie (15-30 jours), prestations familiales (7-15 jours), pension de retraite (1-3 mois). Ces délais peuvent être prolongés en cas de dossier incomplet.",
                "keywords": ["délai", "traitement", "remboursement", "pension"],
                "confidence": 0.8
            },
            
            # Questions sur les contacts
            "numéro de téléphone css": {
                "answer": "Pour contacter la CSS, vous pouvez appeler le numéro vert gratuit ou vous rendre dans l'une des agences régionales. Les coordonnées complètes sont disponibles sur le site officiel de la CSS ou dans vos documents d'affiliation.",
                "keywords": ["numéro", "téléphone", "contact", "agence"],
                "confidence": 0.85
            },
            
            "où se trouve l'agence css": {
                "answer": "La CSS dispose d'agences dans toutes les régions du Sénégal. L'agence principale se trouve à Dakar. Pour connaître l'adresse de l'agence la plus proche de chez vous, consultez le site web de la CSS ou appelez le numéro d'information.",
                "keywords": ["agence", "adresse", "dakar", "région"],
                "confidence": 0.85
            },
            
            # Questions générales
            "qu'est-ce que la css": {
                "answer": "La CSS (Caisse de Sécurité Sociale) est l'organisme public chargé de la gestion de la sécurité sociale au Sénégal. Elle gère les prestations familiales, les pensions de retraite, les accidents du travail et les prestations maladie pour les salariés du secteur privé.",
                "keywords": ["css", "caisse", "sécurité sociale", "organisme"],
                "confidence": 0.95
            },
            
            "comment fonctionne la css": {
                "answer": "La CSS fonctionne sur le principe de la répartition : les cotisations des actifs financent les prestations des bénéficiaires. Elle collecte les cotisations des employeurs et salariés, puis verse les prestations (retraites, allocations familiales, remboursements maladie) selon les droits acquis.",
                "keywords": ["fonctionne", "répartition", "cotisations", "prestations"],
                "confidence": 0.9
            }
        }
        
        # Variations et synonymes pour améliorer la détection
        self.synonyms = {
            "css": ["caisse de sécurité sociale", "sécurité sociale", "caisse"],
            "retraite": ["pension", "retirement", "cessation d'activité"],
            "cotisation": ["contribution", "versement", "prélèvement"],
            "allocations": ["prestations", "indemnités", "aides"],
            "remboursement": ["remboursé", "rembourser", "prise en charge"]
        }
    
    def normalize_question(self, question: str) -> str:
        """Normalise une question pour améliorer la correspondance"""
        # Convertir en minuscules
        question = question.lower().strip()
        
        # Supprimer la ponctuation
        question = re.sub(r'[?!.,;:]', '', question)
        
        # Remplacer les synonymes
        for key, synonyms in self.synonyms.items():
            for synonym in synonyms:
                question = question.replace(synonym, key)
        
        return question
    
    def calculate_similarity(self, question1: str, question2: str) -> float:
        """Calcule la similarité entre deux questions"""
        return SequenceMatcher(None, question1, question2).ratio()
    
    def find_best_match(self, user_question: str, threshold: float = 0.7) -> Optional[Tuple[str, Dict]]:
        """Trouve la meilleure correspondance pour une question utilisateur"""
        normalized_question = self.normalize_question(user_question)
        
        best_match = None
        best_score = 0.0
        
        for predefined_question, qa_data in self.qa_database.items():
            # Similarité directe avec la question prédéfinie
            similarity = self.calculate_similarity(normalized_question, predefined_question)
            
            # Bonus si des mots-clés sont présents
            keyword_bonus = 0.0
            for keyword in qa_data["keywords"]:
                if keyword.lower() in normalized_question:
                    keyword_bonus += 0.1
            
            total_score = similarity + min(keyword_bonus, 0.3)  # Limiter le bonus à 0.3
            
            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = (predefined_question, qa_data)
        
        return best_match if best_match else None
    
    def get_predefined_answer(self, user_question: str, threshold: float = 0.7) -> Optional[Dict]:
        """Récupère une réponse prédéfinie si elle existe"""
        match = self.find_best_match(user_question, threshold)
        
        if match:
            predefined_question, qa_data = match
            logger.info(f"Réponse prédéfinie trouvée pour: '{user_question}' -> '{predefined_question}'")
            
            return {
                "answer": qa_data["answer"],
                "confidence": qa_data["confidence"],
                "matched_question": predefined_question,
                "source": "predefined_qa",
                "keywords_matched": qa_data["keywords"]
            }
        
        return None
    
    def add_qa_pair(self, question: str, answer: str, keywords: List[str], confidence: float = 0.8):
        """Ajoute une nouvelle paire question-réponse"""
        normalized_question = self.normalize_question(question)
        self.qa_database[normalized_question] = {
            "answer": answer,
            "keywords": keywords,
            "confidence": confidence
        }
        logger.info(f"Nouvelle Q&A ajoutée: {question}")
    
    def get_all_questions(self) -> List[str]:
        """Retourne toutes les questions prédéfinies"""
        return list(self.qa_database.keys())
    
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur la base de Q&A"""
        return {
            "total_questions": len(self.qa_database),
            "average_confidence": sum(qa["confidence"] for qa in self.qa_database.values()) / len(self.qa_database),
            "total_keywords": sum(len(qa["keywords"]) for qa in self.qa_database.values())
        }
    
    def search_by_keyword(self, keyword: str) -> List[Tuple[str, Dict]]:
        """Recherche des Q&A par mot-clé"""
        results = []
        keyword_lower = keyword.lower()
        
        for question, qa_data in self.qa_database.items():
            if any(keyword_lower in kw.lower() for kw in qa_data["keywords"]) or keyword_lower in question:
                results.append((question, qa_data))
        
        return results