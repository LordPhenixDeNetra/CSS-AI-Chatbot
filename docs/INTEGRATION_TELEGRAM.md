# Intégration Telegram Bot API avec l'API CSS

## Vue d'ensemble

**Les endpoints de l'API CSS peuvent être parfaitement intégrés dans un bot Telegram !** Cette intégration permet aux utilisateurs de poser des questions sur la CSS directement via Telegram.

## Architecture d'intégration

```
Utilisateur Telegram → Telegram Bot API → Webhook/Polling → Bot Python → API CSS → Réponse
```

## Prérequis

1. **Bot Telegram**
   - Créer un bot via @BotFather
   - Obtenir le token du bot
   - Configurer les commandes

2. **Serveur Backend**
   - Python 3.8+
   - Accès à l'API CSS
   - Connexion internet stable

## Configuration du Bot Telegram

### 1. Création du bot

1. Ouvrir Telegram et chercher @BotFather
2. Envoyer `/newbot`
3. Choisir un nom et un username
4. Récupérer le token du bot

### 2. Configuration des commandes

Envoyer à @BotFather :
```
/setcommands

start - Démarrer le bot CSS
aide - Obtenir de l'aide
menu - Voir les catégories
contact - Informations de contact
status - Statut du service
```

## Implémentation du Bot

### 1. Bot Telegram simple

```python
# telegram_bot_css.py
import os
import json
import requests
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'votre_token_ici')
CSS_API_URL = os.getenv('CSS_API_URL', 'http://localhost:8000')

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramCSSBot:
    def __init__(self):
        self.css_api_url = CSS_API_URL
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configure les gestionnaires de commandes et messages"""
        # Commandes
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("aide", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("contact", self.contact_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Messages texte
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Boutons inline
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /start"""
        user = update.effective_user
        welcome_text = f"""🏛️ **Bienvenue {user.first_name} !**

Je suis l'assistant virtuel de la Caisse de Sécurité Sociale du Sénégal.

💬 **Posez-moi vos questions directement**, par exemple :
• "Comment faire une demande de pension ?"
• "Quels sont les taux de cotisation ?"
• "Où puis-je retirer ma carte CSS ?"

📋 Utilisez /menu pour voir les catégories
🆘 Utilisez /aide pour obtenir de l'aide

Comment puis-je vous aider aujourd'hui ?"""
        
        # Clavier inline avec options rapides
        keyboard = [
            [InlineKeyboardButton("📋 Menu", callback_data="menu")],
            [InlineKeyboardButton("🆘 Aide", callback_data="aide")],
            [InlineKeyboardButton("📞 Contact", callback_data="contact")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /aide"""
        help_text = """🆘 **Aide - Comment utiliser ce bot**

💬 **Posez vos questions directement** :
Écrivez votre question en français, je vous donnerai une réponse basée sur la documentation officielle CSS.

📝 **Exemples de questions** :
• "Comment s'inscrire à la CSS ?"
• "Quel est le montant des cotisations ?"
• "Comment faire une réclamation ?"
• "Quels documents pour la retraite ?"

🔧 **Commandes disponibles** :
• /start - Redémarrer le bot
• /menu - Voir les catégories
• /contact - Informations de contact
• /status - Statut du service

⏰ **Disponible 24h/24, 7j/7**"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /menu"""
        keyboard = [
            [InlineKeyboardButton("💰 Cotisations", callback_data="cat_cotisations")],
            [InlineKeyboardButton("🎯 Prestations", callback_data="cat_prestations")],
            [InlineKeyboardButton("📋 Procédures", callback_data="cat_procedures")],
            [InlineKeyboardButton("📄 Documents", callback_data="cat_documents")],
            [InlineKeyboardButton("🔙 Retour", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = """📋 **Menu des catégories CSS**

Choisissez une catégorie ou posez directement votre question :"""
        
        if update.message:
            await update.message.reply_text(
                menu_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.callback_query.edit_message_text(
                menu_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /contact"""
        contact_text = """📞 **Contacts CSS**

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

📱 **Ce bot Telegram est disponible 24h/24 !**"""
        
        await update.message.reply_text(contact_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /status"""
        try:
            # Vérifier l'API CSS
            response = requests.get(f"{self.css_api_url}/health", timeout=5)
            if response.status_code == 200:
                status_text = "✅ **Service CSS opérationnel**\n\n🤖 Bot Telegram : Actif\n🔗 API CSS : Connectée\n⏰ Dernière vérification : " + datetime.now().strftime("%H:%M:%S")
            else:
                status_text = "⚠️ **Service partiellement disponible**\n\n🤖 Bot Telegram : Actif\n❌ API CSS : Problème de connexion"
        except:
            status_text = "❌ **Service temporairement indisponible**\n\n🤖 Bot Telegram : Actif\n❌ API CSS : Hors ligne"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les messages texte"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"Message de {user_id}: {user_message}")
        
        # Afficher l'indicateur de frappe
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action='typing'
        )
        
        try:
            # Interroger l'API CSS
            response_text = await self.query_css_api(user_message)
            
            # Diviser les messages longs (Telegram limite à 4096 caractères)
            if len(response_text) <= 4096:
                await update.message.reply_text(
                    response_text, 
                    parse_mode='Markdown'
                )
            else:
                # Diviser en plusieurs messages
                parts = self.split_long_message(response_text)
                for i, part in enumerate(parts):
                    if i > 0:
                        part = f"*(Suite {i+1}/{len(parts)})*\n\n{part}"
                    await update.message.reply_text(
                        part, 
                        parse_mode='Markdown'
                    )
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement: {e}")
            await update.message.reply_text(
                "Désolé, une erreur s'est produite. Veuillez réessayer."
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les callbacks des boutons inline"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "menu":
            await self.menu_command(update, context)
        elif data == "aide":
            await self.show_help_inline(query)
        elif data == "contact":
            await self.show_contact_inline(query)
        elif data == "start":
            await self.show_start_inline(query)
        elif data.startswith("cat_"):
            category = data.replace("cat_", "")
            await self.show_category_info(query, category)
    
    async def show_help_inline(self, query):
        """Affiche l'aide via callback"""
        help_text = """🆘 **Aide rapide**

💬 Posez vos questions directement
📋 Utilisez le menu pour naviguer
🔄 Tapez /start pour recommencer"""
        
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_contact_inline(self, query):
        """Affiche les contacts via callback"""
        contact_text = """📞 **Contacts CSS**

🏢 Siège : Dakar, Sénégal
📞 Tél : +221 33 XXX XX XX
📧 Email : contact@css.sn

🕒 Lun-Ven : 8h-17h
🕒 Sam : 8h-12h"""
        
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            contact_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_start_inline(self, query):
        """Retour à l'accueil via callback"""
        welcome_text = """🏛️ **Assistant CSS**

💬 Posez-moi vos questions sur la CSS
📋 Utilisez le menu pour naviguer
🆘 Besoin d'aide ? Cliquez sur Aide"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Menu", callback_data="menu")],
            [InlineKeyboardButton("🆘 Aide", callback_data="aide")],
            [InlineKeyboardButton("📞 Contact", callback_data="contact")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_category_info(self, query, category):
        """Affiche les informations d'une catégorie"""
        category_info = {
            "cotisations": {
                "title": "💰 Cotisations et Paiements",
                "content": """• Taux de cotisation : 24% du salaire
• Répartition employeur/employé
• Modalités de paiement
• Échéances et délais
• Pénalités de retard""",
                "examples": ["Quel est le taux de cotisation ?", "Comment payer mes cotisations ?"]
            },
            "prestations": {
                "title": "🎯 Prestations et Allocations",
                "content": """• Pension de retraite
• Prestations familiales
• Indemnités journalières
• Allocations diverses
• Conditions d'attribution""",
                "examples": ["Comment demander ma pension ?", "Quelles sont les prestations familiales ?"]
            },
            "procedures": {
                "title": "📋 Procédures Administratives",
                "content": """• Inscription employeur
• Inscription travailleur
• Demandes de prestations
• Réclamations et recours
• Modifications de dossier""",
                "examples": ["Comment s'inscrire à la CSS ?", "Comment faire une réclamation ?"]
            },
            "documents": {
                "title": "📄 Documents et Formulaires",
                "content": """• Pièces justificatives
• Formulaires de demande
• Attestations diverses
• Certificats médicaux
• Documents d'état civil""",
                "examples": ["Quels documents pour la retraite ?", "Comment obtenir une attestation ?"]
            }
        }
        
        if category in category_info:
            info = category_info[category]
            text = f"""**{info['title']}**

{info['content']}

💡 **Exemples de questions** :
• {info['examples'][0]}
• {info['examples'][1]}"""
        else:
            text = "Catégorie non trouvée."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
            [InlineKeyboardButton("🏠 Accueil", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def query_css_api(self, question):
        """Interroge l'API CSS"""
        try:
            response = requests.post(
                f"{self.css_api_url}/ask-question-ultra",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                
                # Ajouter des informations contextuelles
                context_info = ""
                if data.get('sources'):
                    context_info = "\n\n📚 *Réponse basée sur la documentation officielle CSS*"
                
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
            logger.error(f"Erreur API CSS: {e}")
            return "Une erreur s'est produite lors du traitement de votre question. Veuillez réessayer."
    
    def split_long_message(self, text, max_length=4000):
        """Divise un message long en plusieurs parties"""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Diviser par paragraphes d'abord
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_part + paragraph) <= max_length:
                current_part += paragraph + "\n\n"
            else:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = paragraph + "\n\n"
                else:
                    # Paragraphe trop long, diviser par phrases
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_part + sentence) <= max_length:
                            current_part += sentence + ". "
                        else:
                            if current_part:
                                parts.append(current_part.strip())
                            current_part = sentence + ". "
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def run(self):
        """Démarre le bot"""
        logger.info("Démarrage du bot Telegram CSS...")
        self.application.run_polling()

# Point d'entrée
if __name__ == '__main__':
    bot = TelegramCSSBot()
    bot.run()
```

### 2. Version avec webhook

```python
# telegram_webhook_bot.py
from flask import Flask, request, jsonify
import asyncio
from telegram import Bot, Update
from telegram.ext import Application

app = Flask(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # https://votre-domaine.com/webhook
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'secret_token')

# Instance du bot
telegram_bot = TelegramCSSBot()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint webhook pour Telegram"""
    try:
        # Vérifier le secret token
        secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret_token != WEBHOOK_SECRET:
            return 'Unauthorized', 401
        
        # Traiter la mise à jour
        update_data = request.get_json()
        update = Update.de_json(update_data, telegram_bot.application.bot)
        
        # Traiter de manière asynchrone
        asyncio.run(telegram_bot.application.process_update(update))
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Erreur webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/set-webhook', methods=['POST'])
def set_webhook():
    """Configure le webhook"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        result = asyncio.run(bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook",
            secret_token=WEBHOOK_SECRET
        ))
        return jsonify({'success': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Fonctionnalités avancées

### 1. Gestion des médias

```python
async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite les photos envoyées"""
    photo = update.message.photo[-1]  # Plus haute résolution
    file = await context.bot.get_file(photo.file_id)
    
    # Télécharger l'image
    image_bytes = await file.download_as_bytearray()
    
    # Utiliser l'endpoint multimodal de l'API CSS
    response = await self.query_css_multimodal(image_bytes)
    
    await update.message.reply_text(response)

async def query_css_multimodal(self, image_bytes):
    """Interroge l'API CSS avec une image"""
    try:
        files = {'file': ('image.jpg', image_bytes, 'image/jpeg')}
        response = requests.post(
            f"{self.css_api_url}/upload-multimodal",
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            return "Image traitée avec succès. Posez votre question à propos de ce document."
        else:
            return "Impossible de traiter cette image."
    except Exception as e:
        return "Erreur lors du traitement de l'image."
```

### 2. Commandes administratives

```python
async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistiques d'utilisation (admin uniquement)"""
    user_id = update.effective_user.id
    
    # Vérifier si l'utilisateur est admin
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Accès non autorisé.")
        return
    
    # Récupérer les statistiques
    stats = get_bot_statistics()
    
    stats_text = f"""📊 **Statistiques du bot**

👥 Utilisateurs actifs : {stats['active_users']}
💬 Messages traités : {stats['total_messages']}
⏱️ Temps de réponse moyen : {stats['avg_response_time']}ms
🔄 Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')
```

### 3. Notifications push

```python
async def send_broadcast(self, message, user_ids=None):
    """Envoie un message à plusieurs utilisateurs"""
    if user_ids is None:
        user_ids = get_all_user_ids()  # Récupérer de la base de données
    
    for user_id in user_ids:
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Erreur envoi à {user_id}: {e}")
```

## Déploiement

### 1. Mode Polling (simple)

```bash
# Installation
pip install python-telegram-bot requests python-dotenv

# Configuration
export TELEGRAM_TOKEN="votre_token_bot"
export CSS_API_URL="http://localhost:8000"

# Démarrage
python telegram_bot_css.py
```

### 2. Mode Webhook (production)

```bash
# Configuration HTTPS requise
export WEBHOOK_URL="https://votre-domaine.com"
export WEBHOOK_SECRET="votre_secret"

# Démarrage avec gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 telegram_webhook_bot:app
```

### 3. Docker

```dockerfile
# Dockerfile.telegram
FROM python:3.11-slim

WORKDIR /app

COPY requirements_telegram.txt .
RUN pip install -r requirements_telegram.txt

COPY telegram_bot_css.py .

CMD ["python", "telegram_bot_css.py"]
```

```yaml
# docker-compose.telegram.yml
version: '3.8'

services:
  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile.telegram
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - CSS_API_URL=http://css-api:8000
    depends_on:
      - css-api
    restart: unless-stopped

  css-api:
    # Configuration de votre API CSS existante
    build: .
    ports:
      - "8000:8000"
```

## Monitoring et Analytics

```python
# analytics.py
import sqlite3
from datetime import datetime

class BotAnalytics:
    def __init__(self, db_path="bot_analytics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message TEXT,
                response_length INTEGER,
                response_time_ms INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_interaction(self, user_id, username, message, response_length, response_time):
        """Enregistre une interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interactions 
            (user_id, username, message, response_length, response_time_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, message, response_length, response_time))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self):
        """Récupère les statistiques"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Utilisateurs uniques
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM interactions")
        unique_users = cursor.fetchone()[0]
        
        # Total des messages
        cursor.execute("SELECT COUNT(*) FROM interactions")
        total_messages = cursor.fetchone()[0]
        
        # Temps de réponse moyen
        cursor.execute("SELECT AVG(response_time_ms) FROM interactions")
        avg_response_time = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'unique_users': unique_users,
            'total_messages': total_messages,
            'avg_response_time': round(avg_response_time, 2)
        }
```

## Sécurité et bonnes pratiques

1. **Validation des entrées** : Filtrer et valider tous les messages
2. **Rate limiting** : Limiter le nombre de requêtes par utilisateur
3. **Logging sécurisé** : Ne pas logger les informations sensibles
4. **Gestion d'erreurs** : Prévoir des messages d'erreur conviviaux
5. **Monitoring** : Surveiller les performances et erreurs

## Exemple d'utilisation

```
Utilisateur: /start
Bot: [Message de bienvenue avec boutons]

Utilisateur: "Comment faire une demande de pension ?"
Bot: [Appel API CSS] → "Pour faire une demande de pension..."

Utilisateur: Clique sur "📋 Menu"
Bot: [Affiche le menu avec catégories]

Utilisateur: Clique sur "💰 Cotisations"
Bot: [Informations sur les cotisations]
```

## Conclusion

L'intégration Telegram Bot API avec l'API CSS offre :

- ✅ **Interface intuitive** avec boutons et commandes
- ✅ **Réponses instantanées** 24h/24
- ✅ **Support multimédia** (images, documents)
- ✅ **Notifications push** possibles
- ✅ **Analytics intégrées** pour le suivi
- ✅ **Déploiement flexible** (polling ou webhook)

Cette solution permet aux utilisateurs d'accéder facilement aux services CSS via Telegram, avec une expérience utilisateur riche et interactive.