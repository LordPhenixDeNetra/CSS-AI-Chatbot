#!/usr/bin/env python3
"""
Exemple simple d'intégration WhatsApp Business API avec l'API CSS
Ce script montre comment créer un bot WhatsApp basique.
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Configuration - À adapter selon votre environnement
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN', 'votre_token_ici')
WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_ID', 'votre_phone_id_ici')
WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN', 'votre_verify_token')
CSS_API_URL = os.getenv('CSS_API_URL', 'http://localhost:8000')

class SimpleWhatsAppBot:
    def __init__(self):
        self.css_api_url = CSS_API_URL
        self.whatsapp_token = WHATSAPP_TOKEN
        self.phone_id = WHATSAPP_PHONE_ID
    
    def process_message(self, from_number, message_text, message_type='text'):
        """
        Traite un message WhatsApp entrant
        
        Args:
            from_number (str): Numéro de l'expéditeur
            message_text (str): Contenu du message
            message_type (str): Type de message (text, image, etc.)
        
        Returns:
            str: Réponse à envoyer
        """
        try:
            # Log de l'interaction
            print(f"[{datetime.now()}] Message de {from_number}: {message_text}")
            
            # Traitement selon le type de message
            if message_type == 'text':
                return self._handle_text_message(message_text)
            else:
                return "Désolé, je ne peux traiter que les messages texte pour le moment."
                
        except Exception as e:
            print(f"Erreur lors du traitement du message: {e}")
            return "Désolé, une erreur s'est produite. Veuillez réessayer."
    
    def _handle_text_message(self, message_text):
        """
        Traite un message texte
        
        Args:
            message_text (str): Contenu du message
        
        Returns:
            str: Réponse générée
        """
        # Commandes spéciales
        message_lower = message_text.lower().strip()
        
        if message_lower in ['bonjour', 'salut', 'hello', 'hi']:
            return self._get_welcome_message()
        elif message_lower in ['aide', 'help', '/aide', '/help']:
            return self._get_help_message()
        elif message_lower in ['menu', '/menu']:
            return self._get_menu_message()
        elif message_lower in ['contact', '/contact']:
            return self._get_contact_message()
        elif message_lower in ['merci', 'au revoir', 'bye']:
            return "Merci d'avoir utilisé le service CSS ! N'hésitez pas à revenir si vous avez d'autres questions. 😊"
        
        # Question normale - interroger l'API CSS
        return self._query_css_api(message_text)
    
    def _query_css_api(self, question):
        """
        Interroge l'API CSS avec la question de l'utilisateur
        
        Args:
            question (str): Question de l'utilisateur
        
        Returns:
            str: Réponse de l'API CSS ou message d'erreur
        """
        try:
            # Appel à l'API CSS
            response = requests.post(
                f"{self.css_api_url}/ask-question-ultra",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                
                # Ajouter des informations contextuelles si disponibles
                context_info = ""
                if data.get('sources'):
                    context_info = "\n\n📚 Cette réponse est basée sur la documentation officielle CSS."
                
                return f"{answer}{context_info}"
            
            elif response.status_code == 404:
                return "Désolé, je n'ai pas trouvé d'informations spécifiques à votre question. Pourriez-vous la reformuler ?"
            
            else:
                return "Le service est temporairement indisponible. Veuillez réessayer dans quelques instants."
                
        except requests.exceptions.Timeout:
            return "La requête a pris trop de temps. Veuillez réessayer avec une question plus simple."
        
        except requests.exceptions.ConnectionError:
            return "Impossible de se connecter au service CSS. Veuillez réessayer plus tard."
        
        except Exception as e:
            print(f"Erreur API CSS: {e}")
            return "Une erreur s'est produite lors du traitement de votre question. Veuillez réessayer."
    
    def _get_welcome_message(self):
        """Message de bienvenue"""
        return """🏛️ **Bienvenue sur le service d'assistance CSS !**

Je suis votre assistant virtuel pour toutes vos questions concernant la Caisse de Sécurité Sociale du Sénégal.

💬 **Posez-moi directement vos questions**, par exemple :
• "Comment faire une demande de pension ?"
• "Quels sont les taux de cotisation ?"
• "Où puis-je retirer ma carte CSS ?"

📋 Tapez "menu" pour voir les catégories
🆘 Tapez "aide" pour obtenir de l'aide

Comment puis-je vous aider aujourd'hui ?"""
    
    def _get_help_message(self):
        """Message d'aide"""
        return """🆘 **Aide - Comment utiliser ce service**

💬 **Posez vos questions directement** :
Écrivez votre question en français, je vous donnerai une réponse basée sur la documentation officielle CSS.

📝 **Exemples de questions** :
• "Comment s'inscrire à la CSS ?"
• "Quel est le montant des cotisations ?"
• "Comment faire une réclamation ?"
• "Quels documents pour la retraite ?"

🔧 **Commandes utiles** :
• "menu" - Voir les catégories
• "contact" - Informations de contact
• "aide" - Afficher cette aide

⏰ **Disponible 24h/24, 7j/7**"""
    
    def _get_menu_message(self):
        """Menu des catégories"""
        return """📋 **Catégories de questions CSS**

1️⃣ **Cotisations et Paiements**
   • Taux de cotisation
   • Modalités de paiement
   • Échéances et délais

2️⃣ **Prestations et Allocations**
   • Pension de retraite
   • Prestations familiales
   • Indemnités journalières

3️⃣ **Procédures Administratives**
   • Inscription employeur/travailleur
   • Demandes de prestations
   • Réclamations et recours

4️⃣ **Documents et Formulaires**
   • Pièces justificatives
   • Attestations
   • Certificats

💬 **Choisissez une catégorie ou posez directement votre question !**"""
    
    def _get_contact_message(self):
        """Informations de contact"""
        return """📞 **Contacts CSS - Caisse de Sécurité Sociale**

🏢 **Siège Social**
Adresse : Dakar, Sénégal
Téléphone : +221 33 XXX XX XX
Email : contact@css.sn

🕒 **Horaires d'ouverture**
Lundi - Vendredi : 8h00 - 17h00
Samedi : 8h00 - 12h00
Dimanche : Fermé

🌐 **Services en ligne**
• Site web officiel CSS
• Portail des assurés
• Application mobile

📱 **Autres moyens de contact**
• Service client téléphonique
• Accueil physique dans nos agences
• Courrier postal

💬 **Ce chatbot WhatsApp est disponible 24h/24 pour vos questions courantes !**"""
    
    def send_message(self, to_number, message_text):
        """
        Envoie un message via WhatsApp Business API
        
        Args:
            to_number (str): Numéro du destinataire
            message_text (str): Message à envoyer
        
        Returns:
            bool: True si envoyé avec succès, False sinon
        """
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            # WhatsApp limite les messages à 4096 caractères
            max_length = 4000
            
            if len(message_text) <= max_length:
                # Message simple
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_number,
                    "type": "text",
                    "text": {"body": message_text}
                }
                
                response = requests.post(url, headers=headers, json=payload)
                return response.status_code == 200
            
            else:
                # Message long - diviser en parties
                parts = [message_text[i:i+max_length] for i in range(0, len(message_text), max_length)]
                
                for i, part in enumerate(parts):
                    if i > 0:
                        part = f"(Suite {i+1}/{len(parts)})\n\n{part}"
                    
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": to_number,
                        "type": "text",
                        "text": {"body": part}
                    }
                    
                    response = requests.post(url, headers=headers, json=payload)
                    if response.status_code != 200:
                        print(f"Erreur envoi partie {i+1}: {response.text}")
                        return False
                
                return True
                
        except Exception as e:
            print(f"Erreur lors de l'envoi du message: {e}")
            return False

# Instance globale du bot
bot = SimpleWhatsAppBot()

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Endpoint webhook pour recevoir les messages WhatsApp
    """
    if request.method == 'GET':
        # Vérification du webhook par WhatsApp
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if verify_token == WEBHOOK_VERIFY_TOKEN:
            print("Webhook vérifié avec succès")
            return challenge
        else:
            print("Échec de la vérification du webhook")
            return 'Erreur de vérification', 403
    
    elif request.method == 'POST':
        # Traitement des messages entrants
        try:
            data = request.get_json()
            
            # Vérifier si c'est un message entrant
            if 'entry' in data:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        
                        if 'messages' in value:
                            for message in value['messages']:
                                from_number = message['from']
                                
                                # Traiter selon le type de message
                                if message['type'] == 'text':
                                    message_text = message['text']['body']
                                    
                                    # Générer la réponse
                                    response_text = bot.process_message(
                                        from_number, 
                                        message_text, 
                                        'text'
                                    )
                                    
                                    # Envoyer la réponse
                                    success = bot.send_message(from_number, response_text)
                                    
                                    if success:
                                        print(f"Réponse envoyée à {from_number}")
                                    else:
                                        print(f"Échec envoi à {from_number}")
                                
                                else:
                                    # Type de message non supporté
                                    response_text = "Désolé, je ne peux traiter que les messages texte pour le moment."
                                    bot.send_message(from_number, response_text)
            
            return jsonify({'status': 'success'})
            
        except Exception as e:
            print(f"Erreur lors du traitement du webhook: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'css_api_url': CSS_API_URL
    })

@app.route('/test-message', methods=['POST'])
def test_message():
    """Endpoint pour tester l'envoi de messages (développement uniquement)"""
    try:
        data = request.get_json()
        to_number = data.get('to')
        message = data.get('message')
        
        if not to_number or not message:
            return jsonify({'error': 'Paramètres to et message requis'}), 400
        
        success = bot.send_message(to_number, message)
        
        return jsonify({
            'success': success,
            'message': 'Message envoyé' if success else 'Échec envoi'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Démarrage du bot WhatsApp CSS...")
    print(f"📡 CSS API URL: {CSS_API_URL}")
    print(f"📱 WhatsApp Phone ID: {WHATSAPP_PHONE_ID}")
    print("🌐 Webhook disponible sur /webhook")
    
    # Démarrage du serveur Flask
    app.run(
        host='0.0.0.0', 
        port=int(os.getenv('PORT', 5000)), 
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )