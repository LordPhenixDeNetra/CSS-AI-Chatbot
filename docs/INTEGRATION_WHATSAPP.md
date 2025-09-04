# Intégration WhatsApp Business API avec l'API CSS

## Vue d'ensemble

Les endpoints de l'API CSS peuvent être facilement intégrés dans un chatbot WhatsApp en utilisant l'API WhatsApp Business. Cette intégration permet aux utilisateurs de poser des questions sur la CSS directement via WhatsApp.

## Architecture d'intégration

```
WhatsApp User → WhatsApp Business API → Webhook → Votre Backend → API CSS → Réponse
```

## Prérequis

1. **Compte WhatsApp Business API**
   - Compte Meta for Developers
   - Application WhatsApp Business approuvée
   - Numéro de téléphone vérifié

2. **Serveur Backend**
   - Serveur avec HTTPS (requis par WhatsApp)
   - Capacité à recevoir des webhooks
   - Accès à l'API CSS (localhost:8000)

## Configuration WhatsApp Business API

### 1. Configuration du Webhook

```python
# webhook_handler.py
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Configuration
WHATSAPP_TOKEN = "votre_token_whatsapp"
WHATSAPP_PHONE_ID = "votre_phone_number_id"
CSS_API_URL = "http://localhost:8000"  # ou votre URL de production
WEBHOOK_VERIFY_TOKEN = "votre_verify_token"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Vérification du webhook
        verify_token = request.args.get('hub.verify_token')
        if verify_token == WEBHOOK_VERIFY_TOKEN:
            return request.args.get('hub.challenge')
        return 'Erreur de vérification', 403
    
    elif request.method == 'POST':
        # Traitement des messages entrants
        data = request.get_json()
        process_whatsapp_message(data)
        return jsonify({'status': 'success'})

def process_whatsapp_message(data):
    """Traite les messages WhatsApp entrants"""
    try:
        # Extraction des données du message
        entry = data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        
        if 'messages' in value:
            message = value['messages'][0]
            from_number = message['from']
            message_text = message['text']['body']
            
            # Appel à l'API CSS
            css_response = query_css_api(message_text)
            
            # Envoi de la réponse via WhatsApp
            send_whatsapp_message(from_number, css_response)
            
    except Exception as e:
        print(f"Erreur lors du traitement: {e}")

def query_css_api(question):
    """Interroge l'API CSS"""
    try:
        response = requests.post(
            f"{CSS_API_URL}/ask-question-ultra",
            json={"question": question},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('answer', 'Désolé, je n\'ai pas pu traiter votre question.')
        else:
            return "Désolé, le service est temporairement indisponible."
            
    except Exception as e:
        print(f"Erreur API CSS: {e}")
        return "Désolé, une erreur s'est produite lors du traitement de votre question."

def send_whatsapp_message(to_number, message_text):
    """Envoie un message via WhatsApp Business API"""
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Diviser les messages longs (WhatsApp limite à 4096 caractères)
    max_length = 4000
    if len(message_text) > max_length:
        # Envoyer en plusieurs parties
        parts = [message_text[i:i+max_length] for i in range(0, len(message_text), max_length)]
        for i, part in enumerate(parts):
            if i > 0:
                part = f"(Suite {i+1}/{len(parts)})\n{part}"
            send_single_message(url, headers, to_number, part)
    else:
        send_single_message(url, headers, to_number, message_text)

def send_single_message(url, headers, to_number, message_text):
    """Envoie un message unique"""
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Erreur envoi WhatsApp: {response.text}")
    except Exception as e:
        print(f"Erreur lors de l'envoi: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### 2. Configuration avancée avec gestion des sessions

```python
# advanced_whatsapp_bot.py
import redis
from datetime import datetime, timedelta

# Configuration Redis pour les sessions
redis_client = redis.Redis(host='localhost', port=6379, db=0)

class WhatsAppCSSBot:
    def __init__(self):
        self.css_api_url = "http://localhost:8000"
        self.session_timeout = 1800  # 30 minutes
    
    def process_message(self, from_number, message_text):
        """Traite un message avec gestion de session"""
        # Vérifier la session utilisateur
        session_key = f"whatsapp_session:{from_number}"
        session_data = redis_client.get(session_key)
        
        if not session_data:
            # Nouvelle session
            self.start_new_session(from_number)
            response = self.get_welcome_message()
        else:
            # Session existante
            response = self.handle_question(message_text)
        
        # Mettre à jour la session
        self.update_session(from_number)
        
        return response
    
    def start_new_session(self, from_number):
        """Démarre une nouvelle session utilisateur"""
        session_data = {
            'start_time': datetime.now().isoformat(),
            'message_count': 0
        }
        session_key = f"whatsapp_session:{from_number}"
        redis_client.setex(
            session_key, 
            self.session_timeout, 
            json.dumps(session_data)
        )
    
    def update_session(self, from_number):
        """Met à jour la session utilisateur"""
        session_key = f"whatsapp_session:{from_number}"
        session_data = redis_client.get(session_key)
        
        if session_data:
            data = json.loads(session_data)
            data['message_count'] += 1
            data['last_activity'] = datetime.now().isoformat()
            
            redis_client.setex(
                session_key, 
                self.session_timeout, 
                json.dumps(data)
            )
    
    def get_welcome_message(self):
        """Message de bienvenue"""
        return """🏛️ Bienvenue sur le service d'assistance CSS!

Je suis votre assistant virtuel pour toutes vos questions concernant la Caisse de Sécurité Sociale du Sénégal.

📝 Vous pouvez me poser des questions sur :
• Les cotisations et prestations
• Les procédures d'inscription
• Les documents requis
• Les montants et calculs
• Et bien plus encore!

💬 Posez-moi votre question directement."""
    
    def handle_question(self, question):
        """Traite une question utilisateur"""
        # Vérifier si c'est une commande spéciale
        if question.lower() in ['/aide', '/help', 'aide']:
            return self.get_help_message()
        elif question.lower() in ['/menu', 'menu']:
            return self.get_menu_message()
        elif question.lower() in ['/contact', 'contact']:
            return self.get_contact_message()
        
        # Question normale - appeler l'API CSS
        return self.query_css_api(question)
    
    def get_help_message(self):
        """Message d'aide"""
        return """🆘 **Aide - Comment utiliser ce service**

📝 **Posez vos questions directement**, par exemple :
• "Comment faire une demande de pension ?"
• "Quels sont les taux de cotisation ?"
• "Où puis-je retirer ma carte CSS ?"

🔧 **Commandes disponibles :**
• `/menu` - Voir les catégories de questions
• `/contact` - Informations de contact CSS
• `/aide` - Afficher cette aide

⏰ **Disponibilité :** 24h/24, 7j/7"""
    
    def get_menu_message(self):
        """Menu des catégories"""
        return """📋 **Menu des catégories**

1️⃣ **Cotisations**
   • Taux de cotisation
   • Modalités de paiement
   • Échéances

2️⃣ **Prestations**
   • Pension de retraite
   • Prestations familiales
   • Indemnités journalières

3️⃣ **Procédures**
   • Inscription employeur/travailleur
   • Demandes de prestations
   • Réclamations

4️⃣ **Documents**
   • Pièces requises
   • Formulaires
   • Attestations

💬 Choisissez une catégorie ou posez directement votre question !"""
    
    def get_contact_message(self):
        """Informations de contact"""
        return """📞 **Contacts CSS**

🏢 **Siège Social**
Adresse : [Adresse du siège]
Téléphone : [Numéro principal]
Email : [Email officiel]

🕒 **Horaires d'ouverture**
Lundi - Vendredi : 8h00 - 17h00
Samedi : 8h00 - 12h00

🌐 **Site Web**
[URL du site officiel]

📱 **Autres services**
• Application mobile CSS
• Portail en ligne
• Service client téléphonique"""
```

## Déploiement

### 1. Déploiement sur serveur

```bash
# Installation des dépendances
pip install flask requests redis

# Démarrage du webhook
python webhook_handler.py
```

### 2. Configuration HTTPS (requis)

```nginx
# nginx.conf pour le webhook
server {
    listen 443 ssl;
    server_name votre-domaine.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location /webhook {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Variables d'environnement

```bash
# .env
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_ID=your_phone_number_id
WEBHOOK_VERIFY_TOKEN=your_verify_token
CSS_API_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
```

## Fonctionnalités avancées

### 1. Gestion des médias

```python
def handle_media_message(message):
    """Traite les messages avec médias (images, documents)"""
    if message['type'] == 'image':
        # Télécharger et traiter l'image
        image_id = message['image']['id']
        # Utiliser l'endpoint multimodal de l'API CSS
        return process_image_question(image_id)
    elif message['type'] == 'document':
        # Traiter les documents PDF
        doc_id = message['document']['id']
        return process_document_upload(doc_id)
```

### 2. Messages interactifs

```python
def send_interactive_menu(to_number):
    """Envoie un menu interactif"""
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Choisissez une catégorie :"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "cotisations", "title": "Cotisations"}},
                    {"type": "reply", "reply": {"id": "prestations", "title": "Prestations"}},
                    {"type": "reply", "reply": {"id": "procedures", "title": "Procédures"}}
                ]
            }
        }
    }
```

## Monitoring et Analytics

```python
# analytics.py
def log_interaction(from_number, question, response, response_time):
    """Enregistre les interactions pour analytics"""
    interaction = {
        'timestamp': datetime.now().isoformat(),
        'user': from_number,
        'question': question,
        'response_length': len(response),
        'response_time_ms': response_time,
        'platform': 'whatsapp'
    }
    
    # Sauvegarder en base de données ou fichier log
    save_interaction(interaction)
```

## Bonnes pratiques

1. **Limitation de débit** : Respecter les limites de l'API WhatsApp
2. **Gestion d'erreurs** : Prévoir des messages d'erreur conviviaux
3. **Sessions utilisateur** : Maintenir le contexte des conversations
4. **Monitoring** : Surveiller les performances et erreurs
5. **Sécurité** : Valider tous les webhooks entrants

## Exemple d'utilisation

```
Utilisateur WhatsApp: "Bonjour"
Bot: [Message de bienvenue avec menu]

Utilisateur: "Comment faire une demande de pension ?"
Bot: [Appel API CSS] → "Pour faire une demande de pension..."

Utilisateur: "Quels documents faut-il ?"
Bot: [Appel API CSS] → "Les documents requis sont..."
```

## Conclusion

L'intégration WhatsApp Business API avec l'API CSS permet de créer un chatbot puissant et accessible. Les utilisateurs peuvent poser leurs questions directement via WhatsApp et recevoir des réponses précises basées sur la base de connaissances CSS.

Cette solution offre :
- ✅ Accessibilité 24h/24
- ✅ Interface familière (WhatsApp)
- ✅ Réponses précises et contextuelles
- ✅ Support multimédia
- ✅ Gestion des sessions utilisateur