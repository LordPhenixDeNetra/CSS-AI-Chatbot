#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram Simple pour l'API CSS

Ce bot permet aux utilisateurs de poser des questions sur la CSS
directement via Telegram en utilisant l'API CSS Backend.

Auteur: Assistant IA
Date: 2024
"""

import os
import json
import requests
import logging
import asyncio
from datetime import datetime
from typing import Optional

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        CallbackQueryHandler, ContextTypes, filters
    )
except ImportError:
    print("❌ Erreur: python-telegram-bot n'est pas installé")
    print("📦 Installation: pip install python-telegram-bot")
    exit(1)

# Configuration depuis les variables d'environnement
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CSS_API_URL = os.getenv('CSS_API_URL', 'http://localhost:8000')
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG_MODE else logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramCSSBot:
    """Bot Telegram pour l'API CSS"""
    
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("❌ TELEGRAM_TOKEN non configuré")
        
        self.css_api_url = CSS_API_URL.rstrip('/')
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        
        logger.info(f"🤖 Bot initialisé avec API CSS: {self.css_api_url}")
    
    def setup_handlers(self):
        """Configure les gestionnaires de commandes et messages"""
        # Commandes principales
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("aide", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("contact", self.contact_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Messages texte (questions)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Boutons inline
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        logger.info("✅ Gestionnaires configurés")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /start - Message de bienvenue"""
        user = update.effective_user
        user_name = user.first_name or "Utilisateur"
        
        welcome_text = f"""🏛️ **Bienvenue {user_name} !**

Je suis l'assistant virtuel de la **Caisse de Sécurité Sociale du Sénégal**.

💬 **Posez-moi vos questions directement**, par exemple :
• "Comment faire une demande de pension ?"
• "Quels sont les taux de cotisation ?"
• "Où puis-je retirer ma carte CSS ?"
• "Comment s'inscrire à la CSS ?"

📋 Utilisez /menu pour voir les catégories
🆘 Utilisez /aide pour obtenir de l'aide
📞 Utilisez /contact pour les informations de contact

**Comment puis-je vous aider aujourd'hui ?**"""
        
        # Clavier inline avec options rapides
        keyboard = [
            [InlineKeyboardButton("📋 Menu des catégories", callback_data="menu")],
            [InlineKeyboardButton("🆘 Aide", callback_data="aide"),
             InlineKeyboardButton("📞 Contact", callback_data="contact")],
            [InlineKeyboardButton("📊 Statut du service", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"👋 Nouvel utilisateur: {user_name} (ID: {user.id})")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /aide - Instructions d'utilisation"""
        help_text = """🆘 **Guide d'utilisation**

💬 **Comment poser une question :**
Écrivez simplement votre question en français. Je vous donnerai une réponse basée sur la documentation officielle de la CSS.

📝 **Exemples de questions :**
• "Comment s'inscrire à la CSS ?"
• "Quel est le montant des cotisations ?"
• "Comment faire une réclamation ?"
• "Quels documents pour la retraite ?"
• "Où se trouvent les bureaux CSS ?"
• "Comment obtenir une attestation ?"

🔧 **Commandes disponibles :**
• `/start` - Redémarrer le bot
• `/menu` - Voir les catégories de questions
• `/contact` - Informations de contact CSS
• `/status` - Vérifier le statut du service
• `/aide` - Afficher cette aide

⏰ **Disponibilité :** 24h/24, 7j/7
🤖 **Réponses :** Basées sur la documentation officielle CSS"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /menu - Affiche le menu des catégories"""
        await self.show_menu(update)
    
    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /contact - Informations de contact"""
        contact_text = """📞 **Contacts CSS Sénégal**

🏢 **Siège Social**
📍 Adresse : Dakar, Sénégal
☎️ Téléphone : +221 33 XXX XX XX
📧 Email : contact@css.sn
🌐 Site web : www.css.sn

🕒 **Horaires d'ouverture**
📅 Lundi - Vendredi : 8h00 - 17h00
📅 Samedi : 8h00 - 12h00
📅 Dimanche : Fermé

🏪 **Agences régionales**
• Dakar Centre
• Pikine
• Thiès
• Saint-Louis
• Kaolack
• Ziguinchor

🌐 **Services en ligne**
• Portail des assurés
• Application mobile CSS
• Télé-déclaration

🤖 **Ce bot Telegram est disponible 24h/24 !**
Pour toute question urgente, contactez directement nos services."""
        
        await update.message.reply_text(contact_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /status - Vérifie le statut du service"""
        status_message = await update.message.reply_text(
            "🔄 Vérification du statut du service..."
        )
        
        try:
            # Vérifier l'API CSS
            response = requests.get(f"{self.css_api_url}/health", timeout=10)
            
            if response.status_code == 200:
                status_text = """✅ **Service CSS opérationnel**

🤖 Bot Telegram : ✅ Actif
🔗 API CSS : ✅ Connectée
📡 Connexion : ✅ Stable
⏰ Dernière vérification : {}

💬 Vous pouvez poser vos questions normalement !""".format(
                    datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
                )
                status_emoji = "✅"
            else:
                status_text = """⚠️ **Service partiellement disponible**

🤖 Bot Telegram : ✅ Actif
🔗 API CSS : ❌ Problème de connexion
📡 Statut HTTP : {}
⏰ Vérification : {}

🔄 Veuillez réessayer dans quelques instants.""".format(
                    response.status_code,
                    datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
                )
                status_emoji = "⚠️"
                
        except requests.exceptions.Timeout:
            status_text = """⏳ **Service lent**

🤖 Bot Telegram : ✅ Actif
🔗 API CSS : ⏳ Réponse lente
📡 Connexion : ⚠️ Timeout
⏰ Vérification : {}

⏱️ Le service répond lentement, patience recommandée.""".format(
                datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
            )
            status_emoji = "⏳"
            
        except requests.exceptions.ConnectionError:
            status_text = """❌ **Service temporairement indisponible**

🤖 Bot Telegram : ✅ Actif
🔗 API CSS : ❌ Hors ligne
📡 Connexion : ❌ Impossible
⏰ Vérification : {}

🔧 Maintenance en cours ou problème technique.""".format(
                datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
            )
            status_emoji = "❌"
            
        except Exception as e:
            status_text = f"""❌ **Erreur de vérification**

🤖 Bot Telegram : ✅ Actif
🔗 API CSS : ❓ Statut inconnu
⚠️ Erreur : {str(e)[:50]}...
⏰ Vérification : {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}"""
            status_emoji = "❌"
        
        await status_message.edit_text(status_text, parse_mode='Markdown')
        logger.info(f"📊 Vérification statut: {status_emoji}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les messages texte (questions des utilisateurs)"""
        user_message = update.message.text.strip()
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "Utilisateur"
        
        # Ignorer les messages vides
        if not user_message:
            await update.message.reply_text(
                "Veuillez poser une question sur la CSS. 🤔"
            )
            return
        
        logger.info(f"💬 Question de {user_name} (ID: {user_id}): {user_message[:100]}...")
        
        # Afficher l'indicateur de frappe
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action='typing'
        )
        
        try:
            # Mesurer le temps de réponse
            start_time = datetime.now()
            
            # Interroger l'API CSS
            response_text = await self.query_css_api(user_message)
            
            # Calculer le temps de réponse
            response_time = (datetime.now() - start_time).total_seconds()
            
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
            
            logger.info(f"✅ Réponse envoyée en {response_time:.2f}s ({len(response_text)} caractères)")
        
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement: {e}")
            await update.message.reply_text(
                "😔 Désolé, une erreur s'est produite lors du traitement de votre question.\n\n"
                "🔄 Veuillez réessayer dans quelques instants.\n"
                "📞 Si le problème persiste, contactez le support CSS."
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les callbacks des boutons inline"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        logger.info(f"🔘 Callback: {data}")
        
        if data == "menu":
            await self.show_menu_inline(query)
        elif data == "aide":
            await self.show_help_inline(query)
        elif data == "contact":
            await self.show_contact_inline(query)
        elif data == "status":
            await self.show_status_inline(query)
        elif data == "start":
            await self.show_start_inline(query)
        elif data.startswith("cat_"):
            category = data.replace("cat_", "")
            await self.show_category_info(query, category)
    
    async def show_menu(self, update):
        """Affiche le menu des catégories"""
        keyboard = [
            [InlineKeyboardButton("💰 Cotisations et Paiements", callback_data="cat_cotisations")],
            [InlineKeyboardButton("🎯 Prestations et Allocations", callback_data="cat_prestations")],
            [InlineKeyboardButton("📋 Procédures Administratives", callback_data="cat_procedures")],
            [InlineKeyboardButton("📄 Documents et Formulaires", callback_data="cat_documents")],
            [InlineKeyboardButton("🏢 Agences et Services", callback_data="cat_agences")],
            [InlineKeyboardButton("🔙 Retour à l'accueil", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = """📋 **Menu des catégories CSS**

Choisissez une catégorie pour voir des exemples de questions, ou posez directement votre question :

💡 **Astuce :** Vous pouvez toujours taper votre question directement, sans passer par le menu !"""
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                menu_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # C'est un callback
            await update.callback_query.edit_message_text(
                menu_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def show_menu_inline(self, query):
        """Affiche le menu via callback"""
        await self.show_menu(query)
    
    async def show_help_inline(self, query):
        """Affiche l'aide via callback"""
        help_text = """🆘 **Aide rapide**

💬 **Comment utiliser ce bot :**
• Tapez votre question directement
• Utilisez le menu pour naviguer par catégories
• Les réponses sont basées sur la documentation officielle CSS

📝 **Exemples de questions :**
• "Comment s'inscrire ?"
• "Taux de cotisation ?"
• "Demande de pension ?"

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

🏢 **Siège Social**
📍 Dakar, Sénégal
☎️ +221 33 XXX XX XX
📧 contact@css.sn

🕒 **Horaires**
📅 Lun-Ven : 8h-17h
📅 Sam : 8h-12h

🌐 **En ligne**
• Site web officiel
• Portail des assurés
• Application mobile"""
        
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            contact_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_status_inline(self, query):
        """Affiche le statut via callback"""
        await query.edit_message_text(
            "🔄 Vérification du statut...",
            parse_mode='Markdown'
        )
        
        try:
            response = requests.get(f"{self.css_api_url}/health", timeout=5)
            if response.status_code == 200:
                status_text = "✅ **Service opérationnel**\n\n🤖 Bot : Actif\n🔗 API : Connectée"
            else:
                status_text = "⚠️ **Service partiellement disponible**\n\n🤖 Bot : Actif\n❌ API : Problème"
        except:
            status_text = "❌ **Service temporairement indisponible**\n\n🤖 Bot : Actif\n❌ API : Hors ligne"
        
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            status_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_start_inline(self, query):
        """Retour à l'accueil via callback"""
        welcome_text = """🏛️ **Assistant CSS Sénégal**

💬 Posez-moi vos questions sur la Caisse de Sécurité Sociale
📋 Utilisez le menu pour naviguer par catégories
🆘 Cliquez sur Aide pour plus d'informations

**Que souhaitez-vous savoir ?**"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Menu", callback_data="menu")],
            [InlineKeyboardButton("🆘 Aide", callback_data="aide"),
             InlineKeyboardButton("📞 Contact", callback_data="contact")],
            [InlineKeyboardButton("📊 Statut", callback_data="status")]
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
                "content": """**Informations sur les cotisations CSS :**

• Taux de cotisation : 24% du salaire
• Répartition employeur/employé
• Modalités de paiement
• Échéances et délais
• Pénalités de retard
• Calcul des cotisations""",
                "examples": [
                    "Quel est le taux de cotisation CSS ?",
                    "Comment payer mes cotisations ?",
                    "Quand payer les cotisations ?"
                ]
            },
            "prestations": {
                "title": "🎯 Prestations et Allocations",
                "content": """**Prestations disponibles :**

• Pension de retraite
• Prestations familiales
• Indemnités journalières
• Allocations diverses
• Conditions d'attribution
• Montants et calculs""",
                "examples": [
                    "Comment demander ma pension de retraite ?",
                    "Quelles sont les prestations familiales ?",
                    "Montant des allocations ?"
                ]
            },
            "procedures": {
                "title": "📋 Procédures Administratives",
                "content": """**Démarches administratives :**

• Inscription employeur
• Inscription travailleur
• Demandes de prestations
• Réclamations et recours
• Modifications de dossier
• Certificats et attestations""",
                "examples": [
                    "Comment s'inscrire à la CSS ?",
                    "Comment faire une réclamation ?",
                    "Modifier mes informations ?"
                ]
            },
            "documents": {
                "title": "📄 Documents et Formulaires",
                "content": """**Documents nécessaires :**

• Pièces justificatives
• Formulaires de demande
• Attestations diverses
• Certificats médicaux
• Documents d'état civil
• Justificatifs de revenus""",
                "examples": [
                    "Quels documents pour la retraite ?",
                    "Comment obtenir une attestation ?",
                    "Formulaires à remplir ?"
                ]
            },
            "agences": {
                "title": "🏢 Agences et Services",
                "content": """**Réseau d'agences CSS :**

• Agences régionales
• Horaires d'ouverture
• Services disponibles
• Contacts locaux
• Accès et localisation
• Services en ligne""",
                "examples": [
                    "Où se trouve l'agence CSS de Dakar ?",
                    "Horaires d'ouverture des agences ?",
                    "Services disponibles en ligne ?"
                ]
            }
        }
        
        if category in category_info:
            info = category_info[category]
            text = f"""**{info['title']}**

{info['content']}

💡 **Exemples de questions :**
• {info['examples'][0]}
• {info['examples'][1]}
• {info['examples'][2]}

💬 **Posez votre question directement !**"""
        else:
            text = "❌ Catégorie non trouvée."
        
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
    
    async def query_css_api(self, question: str) -> str:
        """Interroge l'API CSS et retourne la réponse formatée"""
        try:
            logger.info(f"🔍 Interrogation API CSS: {question[:50]}...")
            
            # Préparer la requête
            payload = {"question": question}
            headers = {"Content-Type": "application/json"}
            
            # Faire la requête à l'API CSS
            response = requests.post(
                f"{self.css_api_url}/ask-question-ultra",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"📡 Réponse API: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '').strip()
                
                if not answer:
                    return "❌ Réponse vide reçue de l'API CSS."
                
                # Ajouter des informations contextuelles
                context_info = ""
                if data.get('sources'):
                    context_info = "\n\n📚 *Réponse basée sur la documentation officielle CSS*"
                elif data.get('confidence'):
                    confidence = data.get('confidence', 0)
                    if confidence > 0.8:
                        context_info = "\n\n✅ *Réponse de haute confiance*"
                    elif confidence > 0.6:
                        context_info = "\n\n⚠️ *Réponse de confiance moyenne*"
                
                return f"{answer}{context_info}"
            
            elif response.status_code == 404:
                return """🤔 Je n'ai pas trouvé d'informations spécifiques à votre question dans ma base de connaissances CSS.

💡 **Suggestions :**
• Reformulez votre question
• Soyez plus précis
• Utilisez des mots-clés CSS
• Consultez le /menu pour voir les catégories

📞 Pour des questions très spécifiques, contactez directement la CSS."""
            
            elif response.status_code == 422:
                return "❌ Format de question non valide. Veuillez reformuler votre question."
            
            elif response.status_code == 500:
                return "⚠️ Erreur interne du service CSS. Veuillez réessayer dans quelques instants."
            
            else:
                return f"❌ Erreur du service CSS (Code: {response.status_code}). Veuillez réessayer."
                
        except requests.exceptions.Timeout:
            logger.warning("⏰ Timeout API CSS")
            return """⏰ **Délai d'attente dépassé**

La requête a pris trop de temps à traiter.

🔄 **Solutions :**
• Réessayez avec une question plus simple
• Vérifiez votre connexion internet
• Attendez quelques instants avant de réessayer"""
        
        except requests.exceptions.ConnectionError:
            logger.error("🔌 Erreur de connexion API CSS")
            return """🔌 **Problème de connexion**

Impossible de se connecter au service CSS.

🔧 **Causes possibles :**
• Maintenance en cours
• Problème de réseau
• Service temporairement indisponible

⏰ Veuillez réessayer plus tard."""
        
        except json.JSONDecodeError:
            logger.error("📄 Erreur de format JSON")
            return "❌ Erreur de format de réponse du service CSS."
        
        except Exception as e:
            logger.error(f"💥 Erreur inattendue API CSS: {e}")
            return """💥 **Erreur inattendue**

Une erreur s'est produite lors du traitement de votre question.

🔄 Veuillez réessayer.
📞 Si le problème persiste, contactez le support CSS."""
    
    def split_long_message(self, text: str, max_length: int = 4000) -> list:
        """Divise un message long en plusieurs parties"""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Diviser par paragraphes d'abord
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_part + paragraph + "\n\n") <= max_length:
                current_part += paragraph + "\n\n"
            else:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = paragraph + "\n\n"
                else:
                    # Paragraphe trop long, diviser par phrases
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_part + sentence + ". ") <= max_length:
                            current_part += sentence + ". "
                        else:
                            if current_part:
                                parts.append(current_part.strip())
                            current_part = sentence + ". "
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def run(self):
        """Démarre le bot en mode polling"""
        logger.info("🚀 Démarrage du bot Telegram CSS...")
        
        try:
            # Vérifier la connexion à l'API CSS
            logger.info("🔍 Vérification de l'API CSS...")
            response = requests.get(f"{self.css_api_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ API CSS accessible")
            else:
                logger.warning(f"⚠️ API CSS répond avec le code {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Impossible de vérifier l'API CSS: {e}")
        
        # Démarrer le bot
        logger.info("🤖 Bot Telegram CSS démarré avec succès !")
        logger.info("📱 Les utilisateurs peuvent maintenant poser leurs questions")
        logger.info("🛑 Appuyez sur Ctrl+C pour arrêter le bot")
        
        self.application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )

def main():
    """Point d'entrée principal"""
    print("🤖 Bot Telegram CSS - Démarrage...")
    
    # Vérifier la configuration
    if not TELEGRAM_TOKEN:
        print("❌ Erreur: Variable TELEGRAM_TOKEN non configurée")
        print("💡 Solution: export TELEGRAM_TOKEN='votre_token_ici'")
        return
    
    if not CSS_API_URL:
        print("❌ Erreur: Variable CSS_API_URL non configurée")
        print("💡 Solution: export CSS_API_URL='http://localhost:8000'")
        return
    
    try:
        # Créer et démarrer le bot
        bot = TelegramCSSBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bot demandé par l'utilisateur")
        logger.info("🛑 Bot arrêté par l'utilisateur")
        
    except Exception as e:
        print(f"💥 Erreur fatale: {e}")
        logger.error(f"💥 Erreur fatale: {e}")
        
    finally:
        print("👋 Bot Telegram CSS arrêté")

if __name__ == '__main__':
    main()