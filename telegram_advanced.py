import os
import json
import asyncio
import logging
import aiohttp
import aiofiles
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

# Chargement des variables d'environnement
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv non installé - variables d'environnement système utilisées")

try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup,
        ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
        InputFile, Document, PhotoSize
    )
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, filters,
        ConversationHandler
    )
    from telegram.constants import ParseMode, ChatAction
except ImportError:
    print("❌ Erreur: python-telegram-bot n'est pas installé")
    print("📦 Installation: pip install python-telegram-bot aiohttp aiofiles")
    exit(1)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis non disponible - utilisation du cache en mémoire")

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CSS_API_URL = os.getenv('CSS_API_URL', 'http://localhost:8000')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '20971520'))  # 20MB
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 1 heure

# Configuration du logging avec gestion robuste des erreurs
try:
    # Configuration du logging avec handlers personnalisés pour éviter les erreurs de buffer
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        handlers=[
            logging.StreamHandler(),  # Handler par défaut
        ],
        force=True  # Force la reconfiguration si déjà configuré
    )
except Exception as e:
    # Fallback en cas d'erreur de configuration du logging
    print(f"⚠️ Erreur de configuration du logging: {e}")
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Désactiver les logs verbeux de httpx pour éviter les erreurs de buffer
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# États de conversation
class ConversationState(Enum):
    MAIN_MENU = "main_menu"
    ASKING_QUESTION = "asking_question"
    UPLOADING_DOCUMENT = "uploading_document"
    UPLOADING_IMAGE = "uploading_image"
    WAITING_MULTIMODAL_QUESTION = "waiting_multimodal_question"
    PROVIDING_FEEDBACK = "providing_feedback"

# Types de requêtes
class QueryType(Enum):
    STANDARD = "standard"
    STREAM = "stream"
    MULTIMODAL = "multimodal"
    MULTIMODAL_IMAGE = "multimodal_image"

@dataclass
class UserSession:
    """Gestion des sessions utilisateur"""
    user_id: int
    username: str
    state: ConversationState
    current_query_type: Optional[QueryType] = None
    uploaded_files: List[str] = None
    question_history: List[Dict] = None
    preferences: Dict[str, Any] = None
    created_at: datetime = None
    last_activity: datetime = None
    temp_question: Optional[str] = None  # Pour les questions en attente de traitement
    favorites: List[Dict] = None  # Pour les réponses favorites
    
    def __post_init__(self):
        if self.uploaded_files is None:
            self.uploaded_files = []
        if self.question_history is None:
            self.question_history = []
        if self.preferences is None:
            self.preferences = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
        if self.favorites is None:
            self.favorites = []
        # Ajouter le champ pour les suggestions temporaires
        if not hasattr(self, 'temp_suggestions'):
            self.temp_suggestions = []

class CacheManager:
    """Gestionnaire de cache avec support Redis et fallback mémoire"""
    
    def __init__(self):
        self.memory_cache = {}
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Connexion Redis établie")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de se connecter à Redis: {e}")
                self.redis_client = None
    
    async def get(self, key: str) -> Optional[str]:
        """Récupère une valeur du cache"""
        try:
            if self.redis_client:
                return self.redis_client.get(key)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Erreur lecture cache: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = CACHE_TTL):
        """Stocke une valeur dans le cache"""
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, value)
            else:
                # Nettoyage simple du cache mémoire
                if len(self.memory_cache) > 1000:
                    # Garde seulement les 500 entrées les plus récentes
                    keys = list(self.memory_cache.keys())
                    for k in keys[:500]:
                        del self.memory_cache[k]
                
                self.memory_cache[key] = value
        except Exception as e:
            logger.error(f"Erreur écriture cache: {e}")
    
    def generate_cache_key(self, query_type: str, question: str, files: List[str] = None) -> str:
        """Génère une clé de cache unique"""
        content = f"{query_type}:{question}"
        if files:
            content += f":{':'.join(files)}"
        return f"css_bot:{hashlib.md5(content.encode()).hexdigest()}"

class TelegramCSSBotAdvanced:
    """Bot Telegram avancé pour l'API CSS"""
    
    def __init__(self):
        self.css_api_url = CSS_API_URL
        self.cache_manager = CacheManager()
        self.user_sessions: Dict[int, UserSession] = {}
        self.feedback_data: List[Dict] = []
        
        # Statistiques globales
        self.stats = {
            'total_users': 0,
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'multimodal_queries': 0,
            'stream_queries': 0,
            'start_time': datetime.now()
        }
    
    @staticmethod
    def clean_markdown_text(text: str) -> str:
        """Nettoie le texte pour éviter les erreurs de parsing Markdown et corrige l'encodage"""
        if not text:
            return text
        
        # Décoder les caractères Unicode échappés AVANT le nettoyage
        if '\\u' in text:
            try:
                import codecs
                text = codecs.decode(text, 'unicode_escape')
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
        
        # Remplacer les caractères problématiques pour Markdown
        cleaned = text.replace('`', "'").replace('*', '•').replace('_', '-')
        cleaned = cleaned.replace('[', '(').replace(']', ')')
        cleaned = cleaned.replace('\\', '/')
        
        # Limiter la longueur pour éviter les messages trop longs
        if len(cleaned) > 3000:
            cleaned = cleaned[:3000] + "..."
        
        return cleaned
    
    def get_or_create_session(self, user_id: int, username: str = None) -> UserSession:
        """Récupère ou crée une session utilisateur"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = UserSession(
                user_id=user_id,
                username=username or f"user_{user_id}",
                state=ConversationState.MAIN_MENU
            )
            self.stats['total_users'] += 1
        
        # Met à jour l'activité
        self.user_sessions[user_id].last_activity = datetime.now()
        return self.user_sessions[user_id]
    
    def setup_handlers(self, application: Application):
        """Configure tous les gestionnaires du bot"""
        # Commandes principales
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("menu", self.menu_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("history", self.history_command))
        application.add_handler(CommandHandler("clear", self.clear_session_command))
        
        # Gestionnaires de callbacks
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Gestionnaires de messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Gestionnaire d'erreurs
        application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /start - Accueil du bot"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        session.state = ConversationState.MAIN_MENU
        
        welcome_text = f"""🤖 **Salut {user.first_name} ! Bienvenue sur votre Assistant CSS IA**

🎯 **Je peux vous aider avec :**
• 📚 Questions sur les règlements CSS
• 📋 Procédures administratives
• 🔍 Recherche dans la documentation

💡 **Comment commencer ?**
1️⃣ Cliquez sur "💬 Question Standard" ci-dessous
2️⃣ Tapez votre question (ex: "Comment faire une demande de pension ?")
3️⃣ Recevez une réponse détaillée instantanément !

🌟 **Astuce :** Utilisez "🌊 Streaming" pour des réponses progressives en temps réel

⚡ **Raccourcis rapides :**
• Tapez directement votre question
• `/menu` - Retour au menu
• `/help` - Guide complet
• `/history` - Vos dernières questions

👇 **Choisissez une option pour commencer :**"""
        
        keyboard = self.get_main_menu_keyboard()
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Génère le clavier du menu principal"""
        keyboard = [
            [
                InlineKeyboardButton("💬 Question Standard", callback_data="standard_query"),
                InlineKeyboardButton("🌊 Question Streaming", callback_data="stream_query")
            ],
            # Fonctionnalités temporairement désactivées
            # [
            #     InlineKeyboardButton("📄 Question + Document", callback_data="multimodal_query"),
            #     InlineKeyboardButton("🖼️ Question + Image", callback_data="image_query")
            # ],
            [
                InlineKeyboardButton("📝 Templates", callback_data="show_templates"),
                InlineKeyboardButton("⭐ Favoris", callback_data="show_favorites")
            ],
            [
                # InlineKeyboardButton("📊 Statistiques", callback_data="show_stats"),
                InlineKeyboardButton("📚 Historique", callback_data="show_history")
            ],
            [
                InlineKeyboardButton("⚙️ Paramètres", callback_data="show_settings"),
                InlineKeyboardButton("❓ Aide", callback_data="show_help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /menu - Affiche le menu principal"""
        text = "🏠 **Menu Principal**\n\nChoisissez une option ci-dessous :"
        keyboard = self.get_main_menu_keyboard()
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /help - Aide détaillée"""
        help_text = """📖 **Guide d'utilisation complet**

🚀 **Démarrage rapide :**
1. Tapez directement votre question ou utilisez le menu
2. Choisissez le mode de réponse (Standard ou Streaming)
3. Consultez votre historique avec `/history`

💬 **Exemples de questions :**
• "Quelles sont les conditions pour une pension de retraite ?"
• "Comment faire une demande de pension de retraite ?"
• "Procédure pour obtenir un remboursement de soins"
• "Comment déclarer un accident de travail ?"
• "Calcul des cotisations sociales"

⚡ **Commandes rapides :**
• `/start` - Redémarrer le bot
• `/menu` - Menu principal
• `/history` - Vos 10 dernières questions
• `/settings` - Personnaliser vos préférences
• `/clear` - Nouvelle session

🎯 **Modes de réponse :**
• **💬 Standard** : Réponse complète instantanée
• **🌊 Streaming** : Réponse progressive (idéal pour questions complexes)
• **📄 Document** : Analysez vos fichiers PDF/TXT (max 20MB)
• **🖼️ Image** : Analysez images et documents scannés (max 10MB)

🔧 **Fonctionnalités intelligentes :**
• 🧠 Cache des réponses pour une vitesse optimale
• 📊 Statistiques personnelles d'utilisation
• 💾 Historique automatique des conversations
• ⭐ Système de feedback pour améliorer les réponses
• 🔄 Sessions persistantes entre les utilisations

💡 **Conseils d'utilisation :**
• Soyez précis dans vos questions pour de meilleurs résultats
• Utilisez le streaming pour les questions longues ou complexes
• Consultez régulièrement votre historique
• N'hésitez pas à reformuler si la réponse ne vous satisfait pas

🆘 **Problème ?** Tapez `/clear` pour redémarrer ou contactez l'administrateur."""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu"),
            InlineKeyboardButton("📚 Historique", callback_data="show_history")
        ]])
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /stats - Statistiques utilisateur"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        
        # Statistiques utilisateur
        user_queries = len(session.question_history)
        successful_queries = sum(1 for q in session.question_history if q.get('success', False))
        
        # Statistiques globales
        uptime = datetime.now() - self.stats['start_time']
        success_rate = (self.stats['successful_queries'] / max(self.stats['total_queries'], 1)) * 100
        
        stats_text = f"""📊 **Vos Statistiques**

👤 **Profil :**
• Nom d'utilisateur : @{session.username}
• Membre depuis : {session.created_at.strftime('%d/%m/%Y')}
• Dernière activité : {session.last_activity.strftime('%d/%m/%Y %H:%M')}

📈 **Utilisation personnelle :**
• Questions posées : {user_queries}
• Questions réussies : {successful_queries}
• Taux de succès : {(successful_queries/max(user_queries, 1)*100):.1f}%
• Mode streaming : {'✅ Activé' if session.preferences.get('stream_mode') else '❌ Désactivé'}

🌐 **Statistiques globales :**
• Utilisateurs totaux : {self.stats['total_users']}
• Requêtes totales : {self.stats['total_queries']}
• Taux de succès global : {success_rate:.1f}%
• Temps de fonctionnement : {uptime.days}j {uptime.seconds//3600}h"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
        ]])
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /settings - Paramètres utilisateur"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        
        settings_text = f"""⚙️ **Paramètres**

🔧 **Configuration actuelle :**
• Mode streaming : {'✅ Activé' if session.preferences.get('stream_mode') else '❌ Désactivé'}
• Langue : {session.preferences.get('language', 'fr').upper()}
• Notifications : ✅ Activées

💡 **Personnalisez votre expérience !**"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🌊 Streaming: {'ON' if session.preferences.get('stream_mode') else 'OFF'}",
                    callback_data="toggle_stream"
                )
            ],
            [
                InlineKeyboardButton("🗑️ Effacer le cache", callback_data="clear_cache"),
                InlineKeyboardButton("📊 Reset stats", callback_data="reset_stats")
            ],
            [
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ])
        
        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /history - Historique des questions"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        
        if not session.question_history:
            await update.message.reply_text(
                "📚 **Historique vide**\n\nVous n'avez encore posé aucune question.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Affiche les 5 dernières questions
        recent_questions = session.question_history[-5:]
        history_text = "📚 **Historique récent**\n\n"
        
        for i, entry in enumerate(recent_questions, 1):
            status = "✅" if entry.get('success') else "❌"
            timestamp = entry.get('timestamp', 'N/A')
            question = entry.get('question', 'N/A')[:50] + ('...' if len(entry.get('question', '')) > 50 else '')
            
            history_text += f"{status} **{i}.** {question}\n📅 {timestamp}\n\n"
        
        history_text += f"💡 **Total : {len(session.question_history)} questions**"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Effacer l'historique", callback_data="clear_history"),
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ])
        
        await update.message.reply_text(
            history_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def clear_session_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /clear - Efface la session utilisateur"""
        user = update.effective_user
        if user.id in self.user_sessions:
            del self.user_sessions[user.id]
        
        await update.message.reply_text(
            "🗑️ **Session effacée**\n\nVotre session a été réinitialisée avec succès.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des callbacks des boutons inline"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        
        callback_data = query.data
        
        # Navigation principale
        if callback_data == "main_menu":
            await self.show_main_menu(query)
        elif callback_data == "standard_query":
            await self.start_standard_query(query, session)
        elif callback_data == "stream_query":
            await self.start_stream_query(query, session)
        elif callback_data == "multimodal_query":
            await self.start_multimodal_query(query, session)
        elif callback_data == "image_query":
            await self.start_image_query(query, session)
        elif callback_data == "show_stats":
            await self.show_stats_inline(query, session)
        elif callback_data == "show_history":
            await self.show_history_inline(query, session)
        elif callback_data == "show_settings":
            await self.show_settings_inline(query, session)
        elif callback_data == "show_help":
            await self.show_help_inline(query)
        elif callback_data == "show_templates":
            await self.show_templates_inline(query, session)
        elif callback_data == "show_favorites":
            await self.show_favorites_inline(query, session)
        elif callback_data == "toggle_stream":
            await self.toggle_stream_mode(query, session)
        elif callback_data == "toggle_default_mode":
            await self.toggle_default_mode(query, session)
        elif callback_data == "toggle_suggestions":
            await self.toggle_suggestions(query, session)
        elif callback_data == "toggle_notifications":
            await self.toggle_notifications(query, session)
        elif callback_data == "change_language":
            await self.change_language(query, session)
        elif callback_data == "change_theme":
            await self.change_theme(query, session)
        elif callback_data == "clear_cache":
            await self.clear_user_cache(query, session)
        elif callback_data == "reset_stats":
            await self.reset_user_stats(query, session)
        elif callback_data == "clear_history":
            await self.clear_user_history(query, session)
        elif callback_data.startswith("feedback_"):
            await self.handle_feedback_callback(query, session, callback_data)
        # Raccourcis rapides pour questions
        elif callback_data == "quick_standard":
            await self.handle_quick_question(query, session, QueryType.STANDARD)
        elif callback_data == "quick_stream":
            await self.handle_quick_question(query, session, QueryType.STREAM)
        # Templates et favoris
        elif callback_data.startswith("template_"):
            await self.handle_template_callback(query, session, callback_data)
        elif callback_data.startswith("favorite_"):
            await self.handle_favorite_callback(query, session, callback_data)
        # Gestion des suggestions d'auto-complétion
        elif callback_data.startswith("suggest_"):
            await self.handle_suggestion_callback(query, session, callback_data)
        # Gestion des langues et thèmes
        elif callback_data.startswith("set_lang_"):
            await self.handle_language_callback(query, session, callback_data)
        elif callback_data.startswith("set_theme_"):
            await self.handle_theme_callback(query, session, callback_data)
    
    async def handle_quick_question(self, query, session: UserSession, query_type: QueryType):
        """Traite une question rapide avec le type spécifié"""
        if not session.temp_question:
            await query.edit_message_text(
                "❌ **Erreur** : Aucune question en attente.\n\nVeuillez poser une nouvelle question.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        question = session.temp_question
        session.temp_question = None  # Nettoyer la question temporaire
        session.current_query_type = query_type
        session.state = ConversationState.ASKING_QUESTION
        
        # Afficher un indicateur de progression
        progress_text = f"🔄 **Traitement en cours...**\n\n📝 Question : _{question[:100]}{'...' if len(question) > 100 else ''}_\n\n⏳ Mode : {'🌊 Streaming' if query_type == QueryType.STREAM else '💬 Standard'}"
        
        await query.edit_message_text(
            progress_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Traiter la question selon le type
        if query_type == QueryType.STREAM:
            await self.call_stream_endpoint(query, question)
        else:
            try:
                response = await self.call_standard_endpoint(question, query.message)
                formatted_response = response  # call_standard_endpoint retourne déjà une chaîne formatée
                
                # Ajouter boutons de feedback
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("👍 Utile", callback_data="feedback_positive"),
                        InlineKeyboardButton("👎 Pas utile", callback_data="feedback_negative")
                    ],
                    [
                        InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                    ]
                ])
                
                await self.send_long_message(query, formatted_response, edit=True)
                await query.message.reply_text(
                    "💡 Cette réponse vous a-t-elle été utile ?",
                    reply_markup=keyboard
                )
                
                self.add_to_history(session, question, formatted_response, True)
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la question rapide: {e}")
                try:
                    # Nettoyer le message d'erreur pour éviter les problèmes de parsing Markdown
                    error_msg = self.clean_markdown_text(str(e))
                    await query.edit_message_text(
                        f"❌ **Erreur lors du traitement**\n\nUne erreur s'est produite. Veuillez réessayer.\n\n🔧 **Détails:** {error_msg[:100]}...",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e2:
                    logger.error(f"Erreur lors de l'édition du message d'erreur: {e2}")
                    # Fallback sans markdown
                    try:
                        await query.edit_message_text(
                            f"❌ Erreur lors du traitement\n\nUne erreur s'est produite. Veuillez réessayer."
                        )
                    except Exception as e3:
                        logger.error(f"Impossible d'éditer le message: {e3}")
                self.add_to_history(session, question, f"Erreur: {str(e)}", False)
        
        session.state = ConversationState.MAIN_MENU
    
    def get_smart_suggestions(self, text: str) -> List[str]:
        """Génère des suggestions intelligentes basées sur le contenu du texte"""
        text_lower = text.lower()
        suggestions = []
        
        # Suggestions basées sur les mots-clés CSS/IPRES
        if any(word in text_lower for word in ['pension', 'retraite']):
            suggestions.extend([
                "Précisez votre âge et années de cotisation",
                "Mentionnez votre secteur d'activité (public/privé)"
            ])
        elif any(word in text_lower for word in ['immatriculation', 'inscription']):
            suggestions.extend([
                "Indiquez votre statut (salarié, employeur, indépendant)",
                "Précisez votre secteur d'activité"
            ])
        elif any(word in text_lower for word in ['accident', 'travail', 'maladie']):
            suggestions.extend([
                "Mentionnez la date et les circonstances",
                "Précisez si vous avez consulté un médecin"
            ])
        elif any(word in text_lower for word in ['remboursement', 'soins']):
            suggestions.extend([
                "Indiquez le type de soins reçus",
                "Précisez l'établissement de soins"
            ])
        else:
            suggestions.extend([
                "Soyez plus spécifique dans votre question",
                "Ajoutez des détails sur votre situation"
            ])
        
        return suggestions[:3]
    
    def get_autocomplete_suggestions(self, text: str) -> List[str]:
        """Génère des suggestions d'auto-complétion pour les textes courts"""
        text_lower = text.lower()
        
        # Templates de questions fréquentes
        templates = [
            "Comment faire une demande de pension de retraite ?",
            "Quelles sont les conditions pour bénéficier des prestations familiales ?",
            "Comment déclarer un accident de travail ?",
            "Où puis-je retirer ma carte d'assuré social ?",
            "Quels documents sont nécessaires pour l'immatriculation ?",
            "Comment obtenir un remboursement de soins médicaux ?",
            "Quelles sont les démarches pour une pension d'invalidité ?",
            "Comment calculer mes cotisations sociales ?"
        ]
        
        # Filtrer les suggestions basées sur le texte saisi
        if len(text) >= 2:
            filtered = [t for t in templates if any(word in t.lower() for word in text_lower.split())]
            if filtered:
                return filtered[:4]
        
        # Retourner les suggestions les plus populaires
        return templates[:4]
    
    async def handle_suggestion_callback(self, query, session: UserSession, callback_data: str):
        """Gère les callbacks des suggestions d'auto-complétion"""
        try:
            suggestion_index = int(callback_data.split('_')[1])
            if suggestion_index < len(session.temp_suggestions):
                selected_suggestion = session.temp_suggestions[suggestion_index]
                session.temp_question = selected_suggestion
                session.temp_suggestions = []  # Nettoyer les suggestions
                
                # Proposer les modes de réponse
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("💬 Réponse Standard", callback_data="quick_standard"),
                        InlineKeyboardButton("🌊 Streaming", callback_data="quick_stream")
                    ],
                    [
                        InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                    ]
                ])
                
                await query.edit_message_text(
                    f"✅ **Question sélectionnée :**\n\n_{selected_suggestion}_\n\n🤔 Comment souhaitez-vous recevoir la réponse ?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await query.answer("❌ Suggestion non trouvée")
        except (ValueError, IndexError):
            await query.answer("❌ Erreur lors de la sélection")
    
    async def show_main_menu(self, query):
        """Affiche le menu principal"""
        text = "🏠 **Menu Principal**\n\nChoisissez une option ci-dessous :"
        keyboard = self.get_main_menu_keyboard()
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des messages texte avec raccourcis intelligents"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        text = update.message.text.strip()
        
        # Gestion des états spéciaux
        if session.state == ConversationState.ASKING_QUESTION:
            await self.process_question(update, session, text)
            return
        elif session.state == ConversationState.WAITING_MULTIMODAL_QUESTION:
            await self.process_multimodal_question(update, session, text)
            return
        elif session.state == ConversationState.PROVIDING_FEEDBACK:
            await self.process_feedback(update, session, text)
            return
        
        # Raccourcis rapides (insensibles à la casse)
        text_lower = text.lower()
        
        # Commandes raccourcies
        if text_lower in ['menu', 'm', '🏠']:
            await self.menu_command(update, context)
            return
        elif text_lower in ['aide', 'help', 'h', '❓', '?']:
            await self.help_command(update, context)
            return
        elif text_lower in ['historique', 'history', 'hist', '📚']:
            await self.history_command(update, context)
            return
        elif text_lower in ['parametres', 'settings', 'config', '⚙️']:
            await self.settings_command(update, context)
            return
        elif text_lower in ['stats', 'statistiques', '📊']:
            await self.stats_command(update, context)
            return
        elif text_lower in ['clear', 'reset', 'nouveau', 'effacer']:
            await self.clear_session_command(update, context)
            return
        
        # Détection automatique du type de question
        if len(text) > 10:  # Question probable
            # Si l'utilisateur est dans le menu principal (après /start), traiter automatiquement comme question standard
            if session.state == ConversationState.MAIN_MENU:
                # Traitement automatique en mode question standard
                session.current_query_type = QueryType.STANDARD
                session.state = ConversationState.ASKING_QUESTION
                
                # Afficher un indicateur de progression
                progress_text = f"🔄 **Traitement automatique en cours...**\n\n📝 Question : _{text[:100]}{'...' if len(text) > 100 else ''}_\n\n⏳ Mode : 💬 Question Standard"
                
                progress_message = await update.message.reply_text(
                    progress_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Traiter directement la question
                try:
                    response = await self.call_standard_endpoint(text, progress_message)
                    formatted_response = response  # call_standard_endpoint retourne déjà une chaîne formatée
                    
                    # Ajouter boutons de feedback
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("👍 Utile", callback_data="feedback_positive"),
                            InlineKeyboardButton("👎 Pas utile", callback_data="feedback_negative")
                        ],
                        [
                            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                        ]
                    ])
                    
                    await self.send_long_message(progress_message, formatted_response, edit=True)
                    await update.message.reply_text(
                        "💡 Cette réponse vous a-t-elle été utile ?",
                        reply_markup=keyboard
                    )
                    
                    self.add_to_history(session, text, formatted_response, True)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement automatique de la question: {e}")
                    try:
                        # Nettoyer le message d'erreur pour éviter les problèmes de parsing Markdown
                        error_msg = self.clean_markdown_text(str(e))
                        await progress_message.edit_text(
                            f"❌ **Erreur lors du traitement**\n\nUne erreur s'est produite. Veuillez réessayer.\n\n🔧 **Détails:** {error_msg[:100]}...",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e2:
                        logger.error(f"Erreur lors de l'édition du message d'erreur: {e2}")
                        await update.message.reply_text(
                            "❌ Une erreur s'est produite. Veuillez réessayer avec /start"
                        )
                return
            else:
                # Comportement normal pour les autres états - proposer les modes de réponse
                # Générer des suggestions intelligentes
                smart_suggestions = self.get_smart_suggestions(text)
                suggestion_text = "\n".join(f"💡 {s}" for s in smart_suggestions[:2]) if smart_suggestions else ""
                
                # Proposer les modes de réponse
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("💬 Réponse Standard", callback_data="quick_standard"),
                        InlineKeyboardButton("🌊 Réponse Streaming", callback_data="quick_stream")
                    ],
                    [
                        InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                    ]
                ])
                
                # Stocker la question pour traitement rapide
                session.temp_question = text
                
                message_text = f"🎯 **Question détectée :**\n_{text[:100]}{'...' if len(text) > 100 else ''}_\n\n💡 **Choisissez le mode de réponse :**"
                if suggestion_text:
                    message_text += f"\n\n**Suggestions pour améliorer votre question :**\n{suggestion_text}"
                
                await update.message.reply_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
        else:
            # Auto-complétion pour texte court
            suggestions = self.get_autocomplete_suggestions(text)
            
            keyboard_buttons = []
            for i, suggestion in enumerate(suggestions[:4]):
                keyboard_buttons.append([InlineKeyboardButton(f"📝 {suggestion[:50]}{'...' if len(suggestion) > 50 else ''}", callback_data=f"suggest_{i}")])
            
            keyboard_buttons.append([InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")])
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            # Stocker les suggestions dans la session
            session.temp_suggestions = suggestions[:4]
            
            await update.message.reply_text(
                f"🤔 **Votre message semble court**\n\n_{text}_\n\n💡 **Suggestions d'auto-complétion :**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des documents uploadés"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        
        if session.state != ConversationState.UPLOADING_DOCUMENT:
            await update.message.reply_text(
                "📄 **Document reçu**\n\nPour analyser un document, utilisez l'option 'Question + Document' du menu principal.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        document = update.message.document
        
        # Vérifications
        if document.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ **Fichier trop volumineux**\n\nTaille maximum autorisée : {MAX_FILE_SIZE//1024//1024}MB",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if not document.file_name.lower().endswith(('.pdf', '.txt')):
            await update.message.reply_text(
                "❌ **Format non supporté**\n\nFormats acceptés : PDF, TXT",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            # Téléchargement du fichier
            file = await context.bot.get_file(document.file_id)
            file_path = f"temp_{user.id}_{document.file_name}"
            await file.download_to_drive(file_path)
            
            session.uploaded_files = [file_path]
            session.state = ConversationState.WAITING_MULTIMODAL_QUESTION
            
            await update.message.reply_text(
                f"✅ **Document uploadé avec succès !**\n\n📄 Fichier : {document.file_name}\n📊 Taille : {document.file_size//1024}KB\n\n💬 **Posez maintenant votre question sur ce document :**",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erreur upload document: {e}")
            await update.message.reply_text(
                "❌ **Erreur lors de l'upload**\n\nVeuillez réessayer.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des images uploadées"""
        user = update.effective_user
        session = self.get_or_create_session(user.id, user.username)
        
        if session.state != ConversationState.UPLOADING_IMAGE:
            await update.message.reply_text(
                "🖼️ **Image reçue**\n\nPour analyser une image, utilisez l'option 'Question + Image' du menu principal.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Prend la photo de meilleure qualité
        photo = update.message.photo[-1]
        
        if photo.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ **Image trop volumineuse**\n\nTaille maximum autorisée : {MAX_FILE_SIZE//1024//1024}MB",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            # Téléchargement de l'image
            file = await context.bot.get_file(photo.file_id)
            file_path = f"temp_{user.id}_image.jpg"
            await file.download_to_drive(file_path)
            
            session.uploaded_files = [file_path]
            session.state = ConversationState.WAITING_MULTIMODAL_QUESTION
            
            await update.message.reply_text(
                f"✅ **Image uploadée avec succès !**\n\n🖼️ Taille : {photo.file_size//1024}KB\n📐 Dimensions : {photo.width}x{photo.height}\n\n💬 **Posez maintenant votre question sur cette image :**",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erreur upload image: {e}")
            await update.message.reply_text(
                "❌ **Erreur lors de l'upload**\n\nVeuillez réessayer.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def process_question(self, update: Update, session: UserSession, question: str):
        """Traite une question standard ou streaming"""
        await update.message.reply_chat_action(ChatAction.TYPING)
        
        # Vérification du cache
        cache_key = self.cache_manager.generate_cache_key(
            session.current_query_type.value, question
        )
        cached_response = await self.cache_manager.get(cache_key)
        
        if cached_response:
            # Appliquer la correction Unicode aux réponses en cache
            cached_response = self.fix_unicode_encoding(cached_response)
            await update.message.reply_text(
                f"{cached_response}",
                parse_mode=ParseMode.MARKDOWN
            )
            self.add_to_history(session, question, cached_response, True)
            session.state = ConversationState.MAIN_MENU
            return
        
        try:
            if session.current_query_type == QueryType.STREAM:
                await self.call_stream_endpoint(update, question)
                # Pour le streaming, l'historique est géré dans call_stream_endpoint
                session.state = ConversationState.MAIN_MENU
                return
            else:
                response, response_id = await self.call_standard_endpoint(question)
                
                # La fonction call_standard_endpoint retourne maintenant toujours une réponse (succès ou erreur)
                await self.send_long_message(update.message, response)
                
                # Vérifier si c'est une réponse d'erreur ou de succès
                is_success = not (response.startswith("❌") or response.startswith("🔌") or response.startswith("⚠️"))
                
                if is_success:
                    # Mise en cache seulement pour les réponses réussies
                    await self.cache_manager.set(cache_key, response)
                    
                    # Boutons de feedback pour les réponses réussies
                    feedback_keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("👍 Utile", callback_data=f"feedback_good_{len(session.question_history)}"),
                            InlineKeyboardButton("👎 Pas utile", callback_data=f"feedback_bad_{len(session.question_history)}")
                        ],
                        [
                            InlineKeyboardButton("⭐ Ajouter aux favoris", callback_data=f"favorite_add_{len(session.question_history)}")
                        ],
                        [
                            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                        ]
                    ])
                    
                    await update.message.reply_text(
                        "💡 Cette réponse vous a-t-elle été utile ?",
                        reply_markup=feedback_keyboard
                    )
                
                # Ajout à l'historique (succès ou échec)
                self.add_to_history(session, question, response, is_success, response_id)
        
        except Exception as e:
            logger.error(f"Erreur traitement question: {e}")
            await update.message.reply_text(
                "❌ **Erreur inattendue**\n\nVeuillez réessayer plus tard.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        session.state = ConversationState.MAIN_MENU
    
    async def process_multimodal_question(self, update: Update, session: UserSession, question: str):
        """Traite une question multimodale (avec fichier)"""
        await update.message.reply_chat_action(ChatAction.TYPING)
        
        if not session.uploaded_files:
            await update.message.reply_text(
                "❌ **Aucun fichier uploadé**\n\nVeuillez d'abord uploader un fichier.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            if session.current_query_type == QueryType.MULTIMODAL_IMAGE:
                response = await self.call_multimodal_image_endpoint(question, session.uploaded_files)
            else:
                response = await self.call_multimodal_endpoint(question, session.uploaded_files)
            
            if response:
                # Appliquer la correction Unicode aux réponses multimodales
                response = self.fix_unicode_encoding(response)
                await self.send_long_message(update.message, response)
                self.add_to_history(session, f"[Multimodal] {question}", response, True)
                self.stats['multimodal_queries'] += 1
                
                # Nettoyage des fichiers temporaires
                for file_path in session.uploaded_files:
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                session.uploaded_files = []
                
                # Boutons de feedback
                feedback_keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("👍 Utile", callback_data=f"feedback_good_{len(session.question_history)-1}"),
                        InlineKeyboardButton("👎 Pas utile", callback_data=f"feedback_bad_{len(session.question_history)-1}")
                    ],
                    [
                        InlineKeyboardButton("⭐ Ajouter aux favoris", callback_data=f"favorite_add_{len(session.question_history)-1}")
                    ],
                    [
                        InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                    ]
                ])
                
                await update.message.reply_text(
                    "💡 Cette analyse vous a-t-elle été utile ?",
                    reply_markup=feedback_keyboard
                )
            else:
                await update.message.reply_text(
                    "❌ **Erreur lors de l'analyse**\n\nVeuillez réessayer.",
                    parse_mode=ParseMode.MARKDOWN
                )
                self.add_to_history(session, f"[Multimodal] {question}", "Erreur", False)
        
        except Exception as e:
            logger.error(f"Erreur traitement multimodal: {e}")
            await update.message.reply_text(
                "❌ **Erreur inattendue**\n\nVeuillez réessayer plus tard.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        session.state = ConversationState.MAIN_MENU
    
    async def start_standard_query(self, query, session: UserSession):
        """Démarre une requête standard"""
        session.state = ConversationState.ASKING_QUESTION
        session.current_query_type = QueryType.STANDARD
        
        text = """💬 **Question Standard**

Posez votre question et recevez une réponse complète !

💡 **Avantages :**
• Réponse détaillée et structurée
• Mise en cache pour accès rapide
• Sources et références incluses

✍️ Tapez votre question ci-dessous :"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def start_stream_query(self, query, session: UserSession):
        """Démarre une requête en streaming"""
        session.state = ConversationState.ASKING_QUESTION
        session.current_query_type = QueryType.STREAM
        
        text = """🌊 **Question Streaming**

Posez votre question et recevez la réponse en temps réel !

⚡ **Avantages :**
• Réponse progressive
• Feedback immédiat
• Expérience interactive

✍️ Tapez votre question ci-dessous :"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def start_multimodal_query(self, query, session: UserSession):
        """Démarre une requête multimodale"""
        session.state = ConversationState.UPLOADING_DOCUMENT
        session.current_query_type = QueryType.MULTIMODAL
        
        text = """📄 **Question + Document**

Uploadez un document PDF puis posez votre question.

📋 **Formats supportés :**
• PDF (max 20MB)
• TXT (max 5MB)

💡 **Exemples d'usage :**
• Analyser un formulaire CSS
• Comprendre un document officiel
• Extraire des informations spécifiques

📎 Envoyez votre document maintenant :"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def start_image_query(self, query, session: UserSession):
        """Démarre une requête avec image"""
        session.state = ConversationState.UPLOADING_IMAGE
        session.current_query_type = QueryType.MULTIMODAL_IMAGE
        
        text = """🖼️ **Question + Image**

Envoyez une image puis posez votre question.

🎨 **Formats supportés :**
• JPG, PNG, WEBP
• Max 10MB

💡 **Exemples d'usage :**
• Analyser un formulaire scanné
• Lire un document photographié
• Identifier des éléments visuels

📸 Envoyez votre image maintenant :"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def show_stats_inline(self, query, session: UserSession):
        """Affiche les statistiques en mode inline"""
        user_queries = len(session.question_history)
        successful_queries = sum(1 for q in session.question_history if q.get('success', False))
        
        uptime = datetime.now() - self.stats['start_time']
        success_rate = (self.stats['successful_queries'] / max(self.stats['total_queries'], 1)) * 100
        
        stats_text = f"""📊 **Statistiques**

👤 **Votre profil :**
• Questions posées : {user_queries}
• Questions réussies : {successful_queries}
• Taux de succès : {(successful_queries/max(user_queries, 1)*100):.1f}%

🌐 **Global :**
• Utilisateurs : {self.stats['total_users']}
• Requêtes totales : {self.stats['total_queries']}
• Succès global : {success_rate:.1f}%
• Uptime : {uptime.days}j {uptime.seconds//3600}h"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Actualiser", callback_data="show_stats"),
            InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def show_history_inline(self, query, session: UserSession):
        """Affiche l'historique en mode inline"""
        if not session.question_history:
            text = "📚 **Historique vide**\n\nVous n'avez encore posé aucune question."
        else:
            recent_questions = session.question_history[-3:]
            text = "📚 **Historique récent**\n\n"
            
            for i, entry in enumerate(recent_questions, 1):
                status = "✅" if entry.get('success') else "❌"
                question = entry.get('question', 'N/A')[:30] + ('...' if len(entry.get('question', '')) > 30 else '')
                text += f"{status} **{i}.** {question}\n"
            
            text += f"\n💡 **Total : {len(session.question_history)} questions**"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Effacer", callback_data="clear_history"),
                InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
            ]
        ])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def show_settings_inline(self, query, session: UserSession):
        """Affiche les paramètres en mode inline"""
        default_mode = session.preferences.get('default_query_mode', 'standard')
        auto_suggestions = session.preferences.get('auto_suggestions', True)
        notifications = session.preferences.get('notifications', True)
        
        text = f"""⚙️ **Paramètres**

🔧 **Configuration :**
• Streaming : {'✅ ON' if session.preferences.get('stream_mode') else '❌ OFF'}
• Mode par défaut : {default_mode.title()}
• Suggestions auto : {'✅ ON' if auto_suggestions else '❌ OFF'}
• Notifications : {'✅ ON' if notifications else '❌ OFF'}
• Langue : {session.preferences.get('language', 'fr').upper()}
• Cache : ✅ Activé

💡 **Personnalisez votre expérience !**"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🌊 Streaming: {'ON' if session.preferences.get('stream_mode') else 'OFF'}",
                    callback_data="toggle_stream"
                ),
                InlineKeyboardButton(
                    f"🎯 Mode: {default_mode.title()}",
                    callback_data="toggle_default_mode"
                )
            ],
            [
                InlineKeyboardButton(
                    f"💡 Suggestions: {'ON' if auto_suggestions else 'OFF'}",
                    callback_data="toggle_suggestions"
                ),
                InlineKeyboardButton(
                    f"🔔 Notifications: {'ON' if notifications else 'OFF'}",
                    callback_data="toggle_notifications"
                )
            ],
            [
                InlineKeyboardButton("🌐 Langue", callback_data="change_language"),
                InlineKeyboardButton("🎨 Thème", callback_data="change_theme")
            ],
            [
                InlineKeyboardButton("🗑️ Effacer cache", callback_data="clear_cache"),
                InlineKeyboardButton("📊 Reset stats", callback_data="reset_stats")
            ],
            [
                InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
            ]
        ])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def show_help_inline(self, query):
        """Affiche l'aide en mode inline"""
        help_text = """❓ **Aide rapide**

🤖 **Commandes :**
• `/start` - Démarrer
• `/menu` - Menu principal
• `/help` - Aide complète
• `/stats` - Statistiques
• `/clear` - Reset session

💡 **Types de questions :**
• **Standard** : Réponse complète
• **Streaming** : Réponse progressive
• **Document** : Analyse PDF/TXT
• **Image** : Analyse d'images

📋 **Formats :**
• Documents : PDF, TXT (20MB max)
• Images : JPG, PNG, WEBP (10MB max)

🔧 **Fonctionnalités :**
• Cache intelligent
• Historique des questions
• Statistiques d'usage
• Système de feedback"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def show_templates_inline(self, query, session: UserSession):
        """Affiche les templates de questions prédéfinies"""
        templates = {
            "pension_retraite": "Comment faire une demande de pension de retraite ?",
            "immatriculation": "Quelles sont les démarches pour l'immatriculation à la sécurité sociale ?",
            "accident_travail": "Comment déclarer un accident de travail ?",
            "maladie_professionnelle": "Quelles sont les procédures pour une maladie professionnelle ?",
            "remboursement_soins": "Comment obtenir le remboursement de mes soins médicaux ?",
            "cotisations": "Comment calculer mes cotisations sociales ?",
            "prestations_familiales": "Quelles sont les prestations familiales disponibles ?",
            "invalidite": "Comment faire une demande de pension d'invalidité ?",
            "deces": "Quelles sont les démarches en cas de décès d'un assuré ?",
            "documents_requis": "Quels documents sont nécessaires pour mes démarches ?"
        }
        
        keyboard = []
        for key, template in templates.items():
            # Tronquer le texte pour l'affichage du bouton
            button_text = template[:45] + "..." if len(template) > 45 else template
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"template_{key}")])
        
        keyboard.append([InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")])
        
        await query.edit_message_text(
            "📝 **Templates de Questions**\n\nChoisissez un template pour poser une question prédéfinie :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_favorites_inline(self, query, session: UserSession):
        """Affiche les réponses favorites de l'utilisateur"""
        if not session.favorites:
            keyboard = [[InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")]]
            await query.edit_message_text(
                "⭐ **Favoris**\n\nVous n'avez encore aucune réponse en favoris.\n\nPour ajouter une réponse aux favoris, utilisez le bouton ⭐ qui apparaît après chaque réponse.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        keyboard = []
        for i, favorite in enumerate(session.favorites[-10:]):  # Afficher les 10 derniers favoris
            question_preview = favorite['question'][:40] + "..." if len(favorite['question']) > 40 else favorite['question']
            keyboard.append([InlineKeyboardButton(f"📌 {question_preview}", callback_data=f"favorite_view_{i}")])
        
        keyboard.append([InlineKeyboardButton("🗑️ Vider les favoris", callback_data="favorite_clear")])
        keyboard.append([InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")])
        
        await query.edit_message_text(
            f"⭐ **Favoris** ({len(session.favorites)})\n\nVos réponses favorites :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_template_callback(self, query, session: UserSession, callback_data: str):
        """Gère les callbacks des templates"""
        template_key = callback_data.replace("template_", "")
        
        templates = {
            "pension_retraite": "Comment faire une demande de pension de retraite ?",
            "immatriculation": "Quelles sont les démarches pour l'immatriculation à la sécurité sociale ?",
            "accident_travail": "Comment déclarer un accident de travail ?",
            "maladie_professionnelle": "Quelles sont les procédures pour une maladie professionnelle ?",
            "remboursement_soins": "Comment obtenir le remboursement de mes soins médicaux ?",
            "cotisations": "Comment calculer mes cotisations sociales ?",
            "prestations_familiales": "Quelles sont les prestations familiales disponibles ?",
            "invalidite": "Comment faire une demande de pension d'invalidité ?",
            "deces": "Quelles sont les démarches en cas de décès d'un assuré ?",
            "documents_requis": "Quels documents sont nécessaires pour mes démarches ?"
        }
        
        if template_key in templates:
            question = templates[template_key]
            session.temp_question = question
            
            # Proposer le choix du mode de réponse
            keyboard = [
                [
                    InlineKeyboardButton("💬 Réponse Standard", callback_data="quick_standard"),
                    InlineKeyboardButton("🌊 Réponse Streaming", callback_data="quick_stream")
                ],
                [InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                f"📝 **Question sélectionnée :**\n\n*{question}*\n\nChoisissez le mode de réponse :",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def handle_favorite_callback(self, query, session: UserSession, callback_data: str):
        """Gère les callbacks des favoris"""
        if callback_data.startswith("favorite_add_"):
            try:
                index = int(callback_data.replace("favorite_add_", ""))
                if 0 <= index < len(session.question_history):
                    history_item = session.question_history[index]
                    
                    # Vérifier si déjà en favoris
                    existing = any(fav['question'] == history_item['question'] for fav in session.favorites)
                    if existing:
                        await query.answer("Cette réponse est déjà dans vos favoris !")
                        return
                    
                    # Ajouter aux favoris
                    favorite = {
                        'question': history_item['question'],
                        'response': history_item['response'],
                        'timestamp': datetime.now().isoformat(),
                        'success': history_item.get('success', True)
                    }
                    session.favorites.append(favorite)
                    await query.answer("⭐ Ajouté aux favoris !")
                else:
                    await query.answer("Question introuvable dans l'historique")
            except (ValueError, IndexError):
                await query.answer("Erreur lors de l'ajout aux favoris")
        elif callback_data == "favorite_clear":
            session.favorites = []
            await query.answer("Favoris vidés !")
            await self.show_favorites_inline(query, session)
        elif callback_data.startswith("favorite_view_"):
            try:
                index = int(callback_data.replace("favorite_view_", ""))
                if 0 <= index < len(session.favorites):
                    favorite = session.favorites[index]
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("🗑️ Supprimer", callback_data=f"favorite_delete_{index}"),
                            InlineKeyboardButton("🔄 Reposer la question", callback_data=f"favorite_reask_{index}")
                        ],
                        [InlineKeyboardButton("⬅️ Retour aux favoris", callback_data="show_favorites")]
                    ]
                    
                    text = f"⭐ **Favori**\n\n**Question :** {favorite['question']}\n\n**Réponse :**\n{favorite['response'][:1000]}{'...' if len(favorite['response']) > 1000 else ''}"
                    
                    await query.edit_message_text(
                        text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except (ValueError, IndexError):
                await query.answer("Erreur lors de l'affichage du favori")
        elif callback_data.startswith("favorite_delete_"):
            try:
                index = int(callback_data.replace("favorite_delete_", ""))
                if 0 <= index < len(session.favorites):
                    session.favorites.pop(index)
                    await query.answer("Favori supprimé !")
                    await self.show_favorites_inline(query, session)
            except (ValueError, IndexError):
                await query.answer("Erreur lors de la suppression")
        elif callback_data.startswith("favorite_reask_"):
            try:
                index = int(callback_data.replace("favorite_reask_", ""))
                if 0 <= index < len(session.favorites):
                    favorite = session.favorites[index]
                    session.temp_question = favorite['question']
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("💬 Réponse Standard", callback_data="quick_standard"),
                            InlineKeyboardButton("🌊 Réponse Streaming", callback_data="quick_stream")
                        ],
                        [InlineKeyboardButton("⬅️ Retour aux favoris", callback_data="show_favorites")]
                    ]
                    
                    await query.edit_message_text(
                        f"🔄 **Reposer la question :**\n\n*{favorite['question']}*\n\nChoisissez le mode de réponse :",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except (ValueError, IndexError):
                await query.answer("Erreur lors du rechargement de la question")
    
    async def toggle_stream_mode(self, query, session: UserSession):
        """Bascule le mode streaming"""
        current_mode = session.preferences.get('stream_mode', False)
        session.preferences['stream_mode'] = not current_mode
        
        status = "activé" if session.preferences['stream_mode'] else "désactivé"
        await query.answer(f"Mode streaming {status} !")
        
        # Rafraîchit l'affichage des paramètres
        await self.show_settings_inline(query, session)
    
    async def toggle_default_mode(self, query, session: UserSession):
        """Bascule le mode par défaut entre standard et stream"""
        current_mode = session.preferences.get('default_query_mode', 'standard')
        new_mode = 'stream' if current_mode == 'standard' else 'standard'
        session.preferences['default_query_mode'] = new_mode
        
        await query.answer(f"Mode par défaut: {new_mode.title()} !")
        await self.show_settings_inline(query, session)
    
    async def toggle_suggestions(self, query, session: UserSession):
        """Bascule les suggestions automatiques"""
        current_suggestions = session.preferences.get('auto_suggestions', True)
        session.preferences['auto_suggestions'] = not current_suggestions
        
        status = "activées" if session.preferences['auto_suggestions'] else "désactivées"
        await query.answer(f"Suggestions automatiques {status} !")
        await self.show_settings_inline(query, session)
    
    async def toggle_notifications(self, query, session: UserSession):
        """Bascule les notifications"""
        current_notifications = session.preferences.get('notifications', True)
        session.preferences['notifications'] = not current_notifications
        
        status = "activées" if session.preferences['notifications'] else "désactivées"
        await query.answer(f"Notifications {status} !")
        await self.show_settings_inline(query, session)
    
    async def change_language(self, query, session: UserSession):
        """Change la langue de l'interface"""
        current_lang = session.preferences.get('language', 'fr')
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data="set_lang_fr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
            ],
            [
                InlineKeyboardButton("🇪🇸 Español", callback_data="set_lang_es"),
                InlineKeyboardButton("🇩🇪 Deutsch", callback_data="set_lang_de")
            ],
            [
                InlineKeyboardButton("⬅️ Retour aux paramètres", callback_data="show_settings")
            ]
        ])
        
        await query.edit_message_text(
            f"🌐 **Changer la langue**\n\nLangue actuelle : {current_lang.upper()}\n\nChoisissez votre langue préférée :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def change_theme(self, query, session: UserSession):
        """Change le thème de l'interface"""
        current_theme = session.preferences.get('theme', 'default')
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌟 Par défaut", callback_data="set_theme_default"),
                InlineKeyboardButton("🌙 Sombre", callback_data="set_theme_dark")
            ],
            [
                InlineKeyboardButton("🌈 Coloré", callback_data="set_theme_colorful"),
                InlineKeyboardButton("💼 Professionnel", callback_data="set_theme_professional")
            ],
            [
                InlineKeyboardButton("⬅️ Retour aux paramètres", callback_data="show_settings")
            ]
        ])
        
        await query.edit_message_text(
            f"🎨 **Changer le thème**\n\nThème actuel : {current_theme.title()}\n\nChoisissez votre thème préféré :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
     
    async def handle_language_callback(self, query, session: UserSession, callback_data: str):
        """Gère les callbacks de changement de langue"""
        lang_code = callback_data.replace("set_lang_", "")
        lang_names = {
            'fr': 'Français',
            'en': 'English', 
            'es': 'Español',
            'de': 'Deutsch'
        }
        
        session.preferences['language'] = lang_code
        lang_name = lang_names.get(lang_code, lang_code.upper())
        
        await query.answer(f"Langue changée: {lang_name} !")
        await self.show_settings_inline(query, session)
    
    async def handle_theme_callback(self, query, session: UserSession, callback_data: str):
        """Gère les callbacks de changement de thème"""
        theme_code = callback_data.replace("set_theme_", "")
        theme_names = {
            'default': 'Par défaut',
            'dark': 'Sombre',
            'colorful': 'Coloré',
            'professional': 'Professionnel'
        }
        
        session.preferences['theme'] = theme_code
        theme_name = theme_names.get(theme_code, theme_code.title())
        
        await query.answer(f"Thème changé: {theme_name} !")
        await self.show_settings_inline(query, session)
     
    async def clear_user_cache(self, query, session: UserSession):
        """Efface le cache utilisateur"""
        # Ici on pourrait implémenter un nettoyage spécifique au cache utilisateur
        await query.answer("Cache utilisateur effacé !")
        
        await query.edit_message_text(
            "🗑️ **Cache effacé**\n\nVotre cache personnel a été vidé.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]])
        )
    
    async def reset_user_stats(self, query, session: UserSession):
        """Remet à zéro les statistiques utilisateur"""
        session.question_history = []
        await query.answer("Statistiques réinitialisées !")
        
        await query.edit_message_text(
            "📊 **Statistiques réinitialisées**\n\nVotre historique et vos stats ont été remis à zéro.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]])
        )
    
    async def clear_user_history(self, query, session: UserSession):
        """Efface l'historique utilisateur"""
        session.question_history = []
        await query.answer("Historique effacé !")
        
        await query.edit_message_text(
            "🗑️ **Historique effacé**\n\nVotre historique des questions a été vidé.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]])
        )
    
    async def handle_feedback_callback(self, query, session: UserSession, callback_data: str):
        """Gère les callbacks de feedback"""
        parts = callback_data.split('_')
        if len(parts) >= 3:
            feedback_type = parts[1]  # 'good' ou 'bad'
            question_index = int(parts[2])
            
            if question_index < len(session.question_history):
                question_entry = session.question_history[question_index]
                response_id = question_entry.get('response_id')
                
                if response_id:
                    # Appelle l'endpoint /record-satisfaction
                    satisfaction = feedback_type == 'good'
                    success = await self.call_satisfaction_endpoint(response_id, satisfaction)
                    
                    if success:
                        # Marque le feedback dans l'historique local
                        session.question_history[question_index]['feedback'] = feedback_type
                        
                        feedback_text = "👍 Merci !" if feedback_type == 'good' else "👎 Merci pour votre retour !"
                        await query.answer(feedback_text)
                        
                        # Propose un feedback textuel pour les évaluations négatives
                        if feedback_type == 'bad':
                            session.state = ConversationState.PROVIDING_FEEDBACK
                            session.feedback_data = {'rating': feedback_type, 'question_index': question_index}
                            
                            await query.edit_message_text(
                                "💬 **Aidez-nous à nous améliorer !**\n\nPouvez-vous nous dire ce qui n'a pas fonctionné ?\n\n✍️ Tapez votre commentaire :",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("⏭️ Passer", callback_data="main_menu")
                                ]])
                            )
                        else:
                            await query.edit_message_text(
                                "✅ **Merci pour votre feedback !**\n\nVotre évaluation nous aide à améliorer le service.",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                                ]])
                            )
                    else:
                        # Erreur lors de l'enregistrement
                        await query.answer("❌ Erreur lors de l'enregistrement du feedback")
                        await query.edit_message_text(
                            "❌ **Erreur**\n\nImpossible d'enregistrer votre feedback. Veuillez réessayer plus tard.",
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                            ]])
                        )
                else:
                    # Pas de response_id disponible (ancienne réponse)
                    await query.answer("⚠️ Feedback non disponible pour cette réponse")
                    await query.edit_message_text(
                        "⚠️ **Feedback non disponible**\n\nCette réponse ne supporte pas le feedback.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                        ]])
                    )
    
    async def process_feedback(self, update: Update, session: UserSession, feedback: str):
        """Traite le feedback textuel de l'utilisateur"""
        if hasattr(session, 'feedback_data'):
            session.feedback_data['text_feedback'] = feedback
            session.state = ConversationState.MAIN_MENU
            
            # Sauvegarde du feedback
            feedback_entry = {
                'user_id': session.user_id,
                'timestamp': datetime.now().isoformat(),
                'rating': session.feedback_data.get('rating'),
                'text_feedback': feedback,
                'question_index': session.feedback_data.get('question_index')
            }
            
            self.feedback_data.append(feedback_entry)
            
            await update.message.reply_text(
                "✅ **Merci pour votre feedback détaillé !**\n\nVos commentaires nous aident à améliorer le service.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
                ]])
            )
        else:
            await update.message.reply_text(
                "💡 **Utilisez le menu pour naviguer !**\n\nTapez /menu pour voir les options disponibles.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def call_standard_endpoint(self, question: str, progress_message=None) -> tuple[str, str]:
        """Appelle l'endpoint ask-question-ultra avec indicateur de progression
        Retourne un tuple (response_text, response_id)
        """
        import time
        start_time = time.time()
        
        try:
            # Afficher l'indicateur de progression si fourni
            if progress_message:
                try:
                    await progress_message.edit_text(
                        f"🔄 **Traitement en cours...**\n\n📝 Question : _{question[:100]}{'...' if len(question) > 100 else ''}_\n\n⏳ Connexion à l'API CSS...",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            # Timeout plus long pour les requêtes complexes (60 secondes)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                if progress_message:
                    try:
                        await progress_message.edit_text(
                            f"🔄 **Traitement en cours...**\n\n📝 Question : _{question[:100]}{'...' if len(question) > 100 else ''}_\n\n⏳ Envoi de la requête...",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
                
                async with session.post(
                    f"{self.css_api_url}/ask-question-ultra",
                    json={"question": question}
                ) as response:
                    if progress_message:
                        try:
                            await progress_message.edit_text(
                                f"🔄 **Traitement en cours...**\n\n📝 Question : _{question[:100]}{'...' if len(question) > 100 else ''}_\n\n⏳ Réception de la réponse...",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except:
                            pass
                    
                    if response.status == 200:
                        data = await response.json()
                        response_time = time.time() - start_time
                        logger.info(f"API standard réussie en {response_time:.2f}s - Question: {question[:50]}...")
                        if response_time > 45.0:
                            logger.warning(f"Requête API standard très lente (proche du timeout): {response_time:.2f}s - Question: {question[:50]}...")
                        elif response_time > 30.0:
                            logger.warning(f"Requête API standard lente: {response_time:.2f}s - Question: {question[:50]}...")
                        self.stats['total_queries'] += 1
                        self.stats['successful_queries'] += 1
                        
                        # Extraire le response_id de la réponse
                        response_id = data.get('response_id', '')

                        response_text = self.format_response(data)
                        # Appliquer la correction Unicode
                        response_text = self.fix_unicode_encoding(response_text)
                        return response_text, response_id
                    else:
                        error_text = await response.text()
                        response_time = time.time() - start_time
                        logger.error(f"Erreur API standard: {response.status} - {error_text} - Temps: {response_time:.2f}s")
                        self.stats['total_queries'] += 1
                        self.stats['failed_queries'] += 1
                        error_msg = f"❌ **Erreur API CSS (Code: {response.status})**\n\nL'API CSS a retourné une erreur. Veuillez réessayer plus tard.\n\n🔧 **Détails techniques:** {error_text[:100]}..."
                        # Décoder les caractères Unicode échappés
                        error_msg = self.fix_unicode_encoding(error_msg)
                        return error_msg, ""
        except aiohttp.ClientConnectorError:
            response_time = time.time() - start_time
            logger.error(f"Impossible de se connecter à l'API CSS: {self.css_api_url} - Temps: {response_time:.2f}s")
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
            error_msg = f"🔌 **API CSS non disponible**\n\nImpossible de se connecter à l'API CSS.\n\n🔧 **Solutions possibles:**\n• Vérifiez que l'API CSS est démarrée\n• Vérifiez l'URL: `{self.css_api_url}`\n• Contactez l'administrateur système"
            # Utiliser la méthode de correction d'encodage
            error_msg = self.fix_unicode_encoding(error_msg)
            return error_msg, ""
        except aiohttp.ServerTimeoutError as e:
            response_time = time.time() - start_time
            logger.error(f"Timeout API standard: {e} - URL: {self.css_api_url} - Temps: {response_time:.2f}s")
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
            error_msg = f"⏱️ **Timeout API CSS**\n\nLa requête a pris trop de temps (>30s).\n\n🔧 **Solutions possibles:**\n• Réessayez avec une question plus simple\n• Vérifiez la charge du serveur\n• Contactez l'administrateur si le problème persiste"
            # Décoder les caractères Unicode échappés
            error_msg = self.fix_unicode_encoding(error_msg)
            return error_msg, ""
        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            logger.error(f"Erreur client HTTP API standard: {type(e).__name__}: {e} - URL: {self.css_api_url} - Temps: {response_time:.2f}s")
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
            error_msg = f"🌐 **Erreur de connexion**\n\nProblème de communication avec l'API CSS.\n\n🔧 **Type d'erreur:** {type(e).__name__}\n**Détails:** {str(e)[:100]}..."
            # Décoder les caractères Unicode échappés
            error_msg = self.fix_unicode_encoding(error_msg)
            return error_msg, ""
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Erreur appel API standard: {type(e).__name__}: {e} - URL: {self.css_api_url} - Temps: {response_time:.2f}s")
            logger.exception("Stack trace complète:")
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
            error_msg = f' Erreur technique. Une erreur inattendue s\'est produite. Type: {type(e).__name__} Détails: {str(e)[:100]}...'
            # Décoder les caractères Unicode échappés
            error_msg = self.fix_unicode_encoding(error_msg)
            return error_msg, ""
    
    async def call_satisfaction_endpoint(self, response_id: str, satisfaction: bool) -> bool:
        """Appelle l'endpoint /record-satisfaction pour enregistrer la satisfaction utilisateur"""
        try:
            satisfaction_url = f"{self.css_api_url}/record-satisfaction"
            
            payload = {
                "response_id": response_id,
                "satisfaction": satisfaction
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post(satisfaction_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Satisfaction enregistrée avec succès: response_id={response_id}, satisfaction={satisfaction}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Erreur enregistrement satisfaction: {response.status} - {error_text}")
                        return False
                        
        except aiohttp.ClientConnectorError:
            logger.error(f"Impossible de se connecter à l'API pour enregistrer la satisfaction: {self.css_api_url}")
            return False
        except aiohttp.ServerTimeoutError:
            logger.error(f"Timeout lors de l'enregistrement de la satisfaction")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'enregistrement de la satisfaction: {type(e).__name__}: {e}")
            return False
     
    async def call_stream_endpoint(self, update: Update, question: str):
        """Appelle l'endpoint ask-question-stream-ultra avec streaming"""
        import time
        start_time = time.time()
        
        user_session = self.get_or_create_session(update.effective_user.id, update.effective_user.username)
        try:
            # Message initial
            message = await update.message.reply_text(
                "🔄 **Génération de la réponse en cours...**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            response_text = ""
            last_update_time = 0
            
            payload = {
                "question": question,
                "provider": "deepseek",
                "temperature": 0.3,
                "max_tokens": 512,
                "top_k": 3
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as http_session:
                async with http_session.post(
                    f"{self.css_api_url}/ask-question-stream-ultra",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line_text = line.decode('utf-8').strip()
                            
                            if line_text.startswith("data: "):
                                try:
                                    data = json.loads(line_text[6:])
                                    
                                    # Gestion des chunks de contenu
                                    if data.get('type') == 'chunk' and 'content' in data:
                                        # MODIFICATION CRITIQUE : Décoder chaque chunk
                                        chunk_content = self.fix_unicode_encoding(data['content'])
                                        response_text += chunk_content
                                        
                                        # Mise à jour du message toutes les 2 secondes ou tous les 50 caractères
                                        current_time = asyncio.get_event_loop().time()
                                        if (current_time - last_update_time > 2.0 or 
                                            len(response_text) - len(response_text.split('\n')[-1]) > 50):
                                            
                                            try:
                                                # Le texte est déjà décodé, pas besoin de re-décoder
                                                await message.edit_text(
                                                    f"🌊 **Réponse en cours...**\n\n{response_text}{'▌' if len(response_text) < 500 else ''}",
                                                    parse_mode=ParseMode.MARKDOWN
                                                )
                                                last_update_time = current_time
                                            except Exception as edit_error:
                                                # Ignore les erreurs d'édition (message identique, etc.)
                                                pass
                                    
                                    # Gestion des erreurs
                                    elif data.get('type') == 'error':
                                        error_msg = data.get('error', 'Erreur inconnue')
                                        error_msg = self.fix_unicode_encoding(error_msg)
                                        await message.edit_text(
                                            f"❌ **Erreur lors du streaming**\n\n{error_msg}",
                                            parse_mode=ParseMode.MARKDOWN
                                        )
                                        self.stats['total_queries'] += 1
                                        self.stats['failed_queries'] += 1
                                        return
                                        
                                except json.JSONDecodeError:
                                    continue
                        
                        # Message final
                        if response_text.strip():
                            # Le texte a déjà été décodé chunk par chunk, une correction finale
                            response_text = self.fix_unicode_encoding(response_text)
                            
                            # Vérifier si c'est un message d'erreur
                            if response_text.startswith(("❌", "🔌", "⚠️")):
                                await message.edit_text(
                                    response_text,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                                self.stats['total_queries'] += 1
                                self.stats['failed_queries'] += 1
                                
                                # Ajout à l'historique pour les erreurs
                                self.add_to_history(user_session, question, response_text, False)
                            else:
                                # Réponse réussie - ajouter les boutons de feedback
                                keyboard = InlineKeyboardMarkup([
                                    [
                                        InlineKeyboardButton("👍 Utile", callback_data="feedback_positive"),
                                        InlineKeyboardButton("👎 Pas utile", callback_data="feedback_negative")
                                    ],
                                    [InlineKeyboardButton("🔙 Menu Principal", callback_data="main_menu")]
                                ])
                                
                                await message.edit_text(
                                    f"✅ **Réponse complète**\n\n{response_text}",
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=keyboard
                                )
                                
                                response_time = time.time() - start_time
                                logger.info(f"API streaming réussie en {response_time:.2f}s - Question: {question[:50]}...")
                                
                                self.stats['total_queries'] += 1
                                self.stats['successful_queries'] += 1
                                
                                # Mise en cache
                                cache_key = self.cache_manager.generate_cache_key("stream", question)
                                await self.cache_manager.set(cache_key, response_text)
                                
                                # Ajout à l'historique
                                self.add_to_history(user_session, question, response_text, True)

                        else:
                            response_time = time.time() - start_time
                            logger.warning(f"Streaming terminé sans contenu en {response_time:.2f}s - Question: {question[:50]}...")
                            await message.edit_text(
                                "⚠️ **Aucune réponse reçue**\n\nLe streaming s'est terminé sans contenu.",
                                parse_mode=ParseMode.MARKDOWN
                            )
                            self.stats['total_queries'] += 1
                            self.stats['failed_queries'] += 1
                    else:
                        error_text = await response.text()
                        response_time = time.time() - start_time
                        logger.error(f"Erreur API streaming: {response.status} - {error_text} - Temps: {response_time:.2f}s")
                        error_msg = f"❌ **Erreur API CSS (Code: {response.status})**\n\nL'API CSS a retourné une erreur. Veuillez réessayer plus tard.\n\n🔧 **Détails techniques:** {error_text[:100]}..."
                        # Décoder les caractères Unicode échappés
                        try:
                            error_msg = error_msg.encode().decode('unicode_escape')
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            pass
                        await message.edit_text(
                            error_msg,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        self.stats['total_queries'] += 1
                        self.stats['failed_queries'] += 1
                        
        except aiohttp.ClientConnectorError:
            response_time = time.time() - start_time
            logger.error(f"Impossible de se connecter à l'API CSS: {self.css_api_url} - Temps: {response_time:.2f}s")
            error_msg = "🔌 **API CSS indisponible**\n\nImpossible de se connecter au service CSS.\n\n💡 **Solutions possibles:**\n• Vérifiez que l'API CSS est démarrée\n• Contactez l'administrateur si le problème persiste"
            # Utiliser la méthode de correction d'encodage
            error_msg = self.fix_unicode_encoding(error_msg)
            await message.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
        except aiohttp.ServerTimeoutError as e:
            response_time = time.time() - start_time
            logger.error(f"Timeout API streaming: {e} - URL: {self.css_api_url} - Temps: {response_time:.2f}s")
            error_msg = f"⏱️ **Timeout API CSS**\n\nLa requête streaming a pris trop de temps.\n\n🔧 **Solutions possibles:**\n• Réessayez avec une question plus simple\n• Vérifiez la charge du serveur\n• Contactez l'administrateur si le problème persiste"
            # Décoder les caractères Unicode échappés
            try:
                error_msg = error_msg.encode().decode('unicode_escape')
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            await message.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            logger.error(f"Erreur client HTTP API streaming: {type(e).__name__}: {e} - URL: {self.css_api_url} - Temps: {response_time:.2f}s")
            error_msg = f"🌐 **Erreur de connexion**\n\nProblème de communication avec l'API CSS.\n\n🔧 **Type d'erreur:** {type(e).__name__}\n**Détails:** {str(e)[:100]}..."
            # Décoder les caractères Unicode échappés
            try:
                error_msg = error_msg.encode().decode('unicode_escape')
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            await message.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Erreur appel API streaming: {type(e).__name__}: {e} - URL: {self.css_api_url} - Temps: {response_time:.2f}s")
            logger.exception("Stack trace complète:")
            error_msg = f'Erreur technique. Une erreur inattendue s\'est produite. Type: {type(e).__name__} Détails: {str(e)[:100]}...'
            # Décoder les caractères Unicode échappés
            try:
                # error_msg = error_msg.encode().decode('unicode_escape')
                # error_msg = error_msg.encode().decode('unicode_escape')
                pass
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            await message.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            self.stats['total_queries'] += 1
            self.stats['failed_queries'] += 1
    
    def fix_unicode_encoding(self, text: str) -> str:
        """Corrige les problèmes d'encodage Unicode dans le texte"""
        if not text or not isinstance(text, str):
            return text
            
        try:
            import json
            import re
            
            # NOUVEAU: Détecter si le texte est une chaîne JSON sérialisée accidentellement
            # (commence et finit par des guillemets)
            if text.startswith('"') and text.endswith('"') and len(text) > 2:
                try:
                    # Désérialiser la chaîne JSON
                    decoded_text = json.loads(text)
                    text = decoded_text
                except json.JSONDecodeError:
                    # Si ça échoue, enlever juste les guillemets
                    text = text[1:-1]
            
            # Méthode 1: Utiliser json.loads pour décoder les séquences Unicode
            # Entourer le texte de guillemets pour en faire un JSON valide
            if '\\u' in text:
                json_text = '"' + text.replace('"', '\\"') + '"'
                try:
                    decoded_text = json.loads(json_text)
                    return decoded_text
                except json.JSONDecodeError:
                    pass
            
            # Méthode 2: Utiliser une expression régulière pour remplacer les séquences \uXXXX
            def unicode_replacer(match):
                hex_code = match.group(1)
                try:
                    return chr(int(hex_code, 16))
                except ValueError:
                    return match.group(0)  # Retourner la séquence originale si erreur
            
            # Remplacer toutes les séquences \uXXXX
            text = re.sub(r'\\u([0-9a-fA-F]{4})', unicode_replacer, text)
            
            # Étape 2: Décoder les séquences d'échappement courantes
            text = text.replace('\\n', '\n')
            text = text.replace('\\t', '\t')
            text = text.replace('\\r', '\r')
            text = text.replace('\\"', '"')
            text = text.replace("\\\'", "'")
            

                
        except Exception as e:
            logger.warning(f"Erreur de décodage Unicode: {e}")
            # En cas d'erreur, essayer une approche alternative
            try:
                # Approche alternative : remplacer manuellement les séquences courantes
                replacements = {
                    '\\u00e0': 'à', '\\u00e1': 'á', '\\u00e2': 'â', '\\u00e3': 'ã',
                    '\\u00e4': 'ä', '\\u00e5': 'å', '\\u00e6': 'æ', '\\u00e7': 'ç',
                    '\\u00e8': 'è', '\\u00e9': 'é', '\\u00ea': 'ê', '\\u00eb': 'ë',
                    '\\u00ec': 'ì', '\\u00ed': 'í', '\\u00ee': 'î', '\\u00ef': 'ï',
                    '\\u00f0': 'ð', '\\u00f1': 'ñ', '\\u00f2': 'ò', '\\u00f3': 'ó',
                    '\\u00f4': 'ô', '\\u00f5': 'õ', '\\u00f6': 'ö', '\\u00f8': 'ø',
                    '\\u00f9': 'ù', '\\u00fa': 'ú', '\\u00fb': 'û', '\\u00fc': 'ü',
                    '\\u00fd': 'ý', '\\u00ff': 'ÿ',
                    # Majuscules
                    '\\u00c0': 'À', '\\u00c1': 'Á', '\\u00c2': 'Â', '\\u00c3': 'Ã',
                    '\\u00c4': 'Ä', '\\u00c5': 'Å', '\\u00c6': 'Æ', '\\u00c7': 'Ç',
                    '\\u00c8': 'È', '\\u00c9': 'É', '\\u00ca': 'Ê', '\\u00cb': 'Ë',
                    '\\u00cc': 'Ì', '\\u00cd': 'Í', '\\u00ce': 'Î', '\\u00cf': 'Ï',
                    '\\u00d1': 'Ñ', '\\u00d2': 'Ò', '\\u00d3': 'Ó', '\\u00d4': 'Ô',
                    '\\u00d5': 'Õ', '\\u00d6': 'Ö', '\\u00d8': 'Ø', '\\u00d9': 'Ù',
                    '\\u00da': 'Ú', '\\u00db': 'Û', '\\u00dc': 'Ü', '\\u00dd': 'Ý',
                }
                
                for escaped, char in replacements.items():
                    text = text.replace(escaped, char)
                    
                # Nettoyer les séquences d'échappement restantes
                text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                
            except Exception as e2:
                logger.error(f"Échec de l'approche alternative pour l'Unicode: {e2}")
        
        return text
    
    def format_response(self, response_data: dict) -> str:
        """Formate la réponse de l'API pour l'affichage avec décodage des caractères Unicode"""
        response_text = ""
        
        if isinstance(response_data, dict):
            if 'response' in response_data:
                response_text = response_data['response']
            elif 'answer' in response_data:
                response_text = response_data['answer']
            elif 'result' in response_data:
                response_text = response_data['result']
            else:
                response_text = str(response_data)
        else:
            response_text = str(response_data)
        
        # OBLIGATOIRE : Appliquer la correction Unicode
        response_text = self.fix_unicode_encoding(response_text)
        
        return response_text
    
    async def send_long_message(self, message_or_query, text: str, edit: bool = False):
        """Envoie un message long en le divisant si nécessaire"""
        # AJOUT OBLIGATOIRE : Corriger l'encodage Unicode avant l'envoi
        text = self.fix_unicode_encoding(text)
        
        max_length = 4096  # Limite Telegram
        
        # Déterminer si c'est un CallbackQuery ou un Message
        is_callback = hasattr(message_or_query, 'edit_message_text')
        
        if len(text) <= max_length:
            try:
                if edit and is_callback:
                    await message_or_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
                elif edit:
                    await message_or_query.edit_text(text, parse_mode=ParseMode.MARKDOWN)
                elif is_callback:
                    await message_or_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                else:
                    await message_or_query.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.warning(f"Erreur parsing Markdown: {e}")
                # Fallback sans markdown si erreur de parsing
                try:
                    if edit and is_callback:
                        await message_or_query.edit_message_text(text)
                    elif edit:
                        await message_or_query.edit_text(text)
                    elif is_callback:
                        await message_or_query.message.reply_text(text)
                    else:
                        await message_or_query.reply_text(text)
                except Exception as e2:
                    logger.error(f"Erreur envoi message: {e2}")
        else:
            # Divise le message en chunks
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            
            for i, chunk in enumerate(chunks):
                try:
                    if i == 0 and edit and is_callback:
                        await message_or_query.edit_message_text(f"📄 **Partie {i+1}/{len(chunks)}**\n\n{chunk}", parse_mode=ParseMode.MARKDOWN)
                    elif i == 0 and edit:
                        await message_or_query.edit_text(f"📄 **Partie {i+1}/{len(chunks)}**\n\n{chunk}", parse_mode=ParseMode.MARKDOWN)
                    elif is_callback:
                        await message_or_query.message.reply_text(f"📄 **Partie {i+1}/{len(chunks)}**\n\n{chunk}", parse_mode=ParseMode.MARKDOWN)
                    else:
                        await message_or_query.reply_text(f"📄 **Partie {i+1}/{len(chunks)}**\n\n{chunk}", parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logger.warning(f"Erreur parsing Markdown chunk {i+1}: {e}")
                    # Fallback sans markdown
                    try:
                        if i == 0 and edit and is_callback:
                            await message_or_query.edit_message_text(f"Partie {i+1}/{len(chunks)}\n\n{chunk}")
                        elif i == 0 and edit:
                            await message_or_query.edit_text(f"Partie {i+1}/{len(chunks)}\n\n{chunk}")
                        elif is_callback:
                            await message_or_query.message.reply_text(f"Partie {i+1}/{len(chunks)}\n\n{chunk}")
                        else:
                            await message_or_query.reply_text(f"Partie {i+1}/{len(chunks)}\n\n{chunk}")
                    except Exception as e2:
                        logger.error(f"Erreur envoi chunk {i+1}: {e2}")
                
                # Pause entre les messages pour éviter le rate limiting
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
    
    def add_to_history(self, session: UserSession, question: str, response: str, success: bool, response_id: str = None):
        """Ajoute une entrée à l'historique des questions"""
        entry = {
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'question': question,
            'response': response,
            'success': success,
            'query_type': session.current_query_type.value if session.current_query_type else 'unknown',
            'response_id': response_id
        }
        
        session.question_history.append(entry)
        
        # Limite l'historique à 50 entrées
        if len(session.question_history) > 50:
            session.question_history = session.question_history[-50:]
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire d'erreurs global"""
        logger.error(f"Exception lors de la mise à jour {update}: {context.error}")
        
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ **Erreur inattendue**\n\nUne erreur s'est produite. Veuillez réessayer.\n\nSi le problème persiste, utilisez /start pour redémarrer.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
    
    async def run_async(self):
        """Démarre le bot de manière asynchrone"""
        logger.info("🚀 Démarrage du bot Telegram CSS avancé...")
        
        # Création de l'application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Initialisation de l'application
        await application.initialize()
        
        # Configuration des gestionnaires
        self.setup_handlers(application)
        
        # Démarrage
        logger.info("✅ Bot démarré avec succès !")
        logger.info(f"🔗 API CSS: {self.css_api_url}")
        logger.info(f"💾 Cache: {'Redis' if self.cache_manager.redis_client else 'Mémoire'}")
        
        try:
            # Démarrage du polling
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            
            # Maintenir le bot en vie
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage: {e}")
            raise
        finally:
            # Nettoyage
            await application.stop()
            await application.shutdown()
    
    def run(self):
        """Démarre le bot (wrapper synchrone)"""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du bot demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur fatale dans run(): {e}")
            raise

def main():
    """Point d'entrée principal"""
    # Configuration de l'encodage pour éviter les erreurs Unicode
    import sys
    if sys.platform == "win32":
        # Configuration plus sûre pour l'encodage UTF-8 sur Windows
        import locale
        try:
            # Essayer de configurer l'encodage UTF-8 sans détacher les buffers
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            else:
                # Fallback pour les versions plus anciennes de Python
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except (AttributeError, locale.Error):
            # Si la configuration échoue, continuer sans modification
            pass
    
    # Vérification des variables d'environnement
    if not TELEGRAM_TOKEN:
        print("Erreur: TELEGRAM_TOKEN non défini")
        print("Définissez la variable d'environnement TELEGRAM_TOKEN")
        return
    
    if not CSS_API_URL:
        print("Erreur: CSS_API_URL non défini")
        print("Définissez la variable d'environnement CSS_API_URL")
        return
    
    print("🤖 Bot Telegram CSS Avancé")
    print("=" * 30)
    print(f"📡 Token: {TELEGRAM_TOKEN[:10]}...")
    print(f"🔗 API CSS: {CSS_API_URL}")
    print(f"💾 Redis: {'✅ Disponible' if REDIS_AVAILABLE else '❌ Non disponible'}")
    print(f"🐛 Debug: {'✅ Activé' if DEBUG_MODE else '❌ Désactivé'}")
    print("=" * 30)
    
    # Création et démarrage du bot
    bot = TelegramCSSBotAdvanced()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bot...")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        logger.error(f"Erreur fatale: {e}")

if __name__ == "__main__":
    main()