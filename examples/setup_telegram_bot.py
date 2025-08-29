#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Configuration Automatique - Bot Telegram CSS

Ce script automatise la configuration et le déploiement du bot Telegram
pour l'intégration avec l'API CSS.

Auteur: Assistant IA
Date: 2024
"""

import os
import sys
import subprocess
import requests
import json
from pathlib import Path
from typing import Optional

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    # Fallback si colorama n'est pas installé
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

class TelegramBotSetup:
    """Gestionnaire de configuration du bot Telegram CSS"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.examples_dir = self.project_root / "examples"
        self.env_file = self.examples_dir / ".env.telegram"
        
    def print_header(self):
        """Affiche l'en-tête du script"""
        print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
        print(f"{Fore.CYAN}{Style.BRIGHT}🤖 CONFIGURATION BOT TELEGRAM CSS")
        print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
        print(f"{Fore.WHITE}Configuration automatique du bot Telegram pour l'API CSS")
        print(f"{Fore.WHITE}Projet: {self.project_root}")
        print()
    
    def check_python_version(self):
        """Vérifie la version de Python"""
        print(f"{Fore.YELLOW}🔍 Vérification de la version Python...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"{Fore.RED}❌ Python 3.8+ requis. Version actuelle: {version.major}.{version.minor}")
            return False
        
        print(f"{Fore.GREEN}✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    
    def install_dependencies(self):
        """Installe les dépendances nécessaires"""
        print(f"{Fore.YELLOW}📦 Installation des dépendances...")
        
        requirements_file = self.project_root / "requirements_telegram.txt"
        
        if not requirements_file.exists():
            print(f"{Fore.RED}❌ Fichier requirements_telegram.txt non trouvé")
            return False
        
        try:
            # Installer les dépendances
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], capture_output=True, text=True, check=True)
            
            print(f"{Fore.GREEN}✅ Dépendances installées avec succès")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}❌ Erreur lors de l'installation: {e}")
            print(f"{Fore.RED}Sortie d'erreur: {e.stderr}")
            return False
    
    def get_user_input(self, prompt: str, default: str = "", required: bool = True) -> str:
        """Récupère une entrée utilisateur avec validation"""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if user_input or not required:
                return user_input
            
            print(f"{Fore.RED}❌ Cette information est requise")
    
    def create_env_file(self):
        """Crée le fichier de configuration .env.telegram"""
        print(f"{Fore.YELLOW}⚙️ Configuration des variables d'environnement...")
        print()
        
        # Récupérer les informations de configuration
        print(f"{Fore.CYAN}📱 Configuration Telegram:")
        telegram_token = self.get_user_input(
            f"{Fore.WHITE}Token du bot Telegram (obtenu via @BotFather)",
            required=True
        )
        
        print(f"\n{Fore.CYAN}🔗 Configuration API CSS:")
        css_api_url = self.get_user_input(
            f"{Fore.WHITE}URL de l'API CSS",
            default="http://localhost:8000",
            required=True
        )
        
        print(f"\n{Fore.CYAN}🔧 Configuration avancée:")
        debug_mode = self.get_user_input(
            f"{Fore.WHITE}Mode debug (true/false)",
            default="false",
            required=False
        ).lower() in ['true', '1', 'yes', 'oui']
        
        webhook_url = self.get_user_input(
            f"{Fore.WHITE}URL du webhook (optionnel, pour production)",
            default="",
            required=False
        )
        
        webhook_secret = self.get_user_input(
            f"{Fore.WHITE}Secret du webhook (optionnel)",
            default="telegram_css_secret_2024",
            required=False
        )
        
        port = self.get_user_input(
            f"{Fore.WHITE}Port du serveur webhook",
            default="5000",
            required=False
        )
        
        # Créer le contenu du fichier .env
        env_content = f"""# Configuration Bot Telegram CSS
# Généré automatiquement le {self.get_current_datetime()}

# ===== CONFIGURATION TELEGRAM =====
# Token du bot obtenu via @BotFather
TELEGRAM_TOKEN={telegram_token}

# ===== CONFIGURATION API CSS =====
# URL de base de l'API CSS
CSS_API_URL={css_api_url}

# ===== CONFIGURATION AVANCÉE =====
# Mode debug (true/false)
DEBUG_MODE={str(debug_mode).lower()}

# ===== CONFIGURATION WEBHOOK (PRODUCTION) =====
# URL publique pour le webhook (HTTPS requis)
WEBHOOK_URL={webhook_url}

# Secret pour sécuriser le webhook
WEBHOOK_SECRET={webhook_secret}

# Port du serveur webhook
WEBHOOK_PORT={port}

# ===== CONFIGURATION LOGGING =====
# Niveau de log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL={'DEBUG' if debug_mode else 'INFO'}

# Fichier de log
LOG_FILE=telegram_bot.log

# ===== CONFIGURATION BASE DE DONNÉES (OPTIONNEL) =====
# URL Redis pour le cache (optionnel)
# REDIS_URL=redis://localhost:6379/0

# Base de données SQLite pour les analytics
DATABASE_URL=sqlite:///telegram_bot_analytics.db

# ===== CONFIGURATION SÉCURITÉ =====
# Liste des IDs d'administrateurs (séparés par des virgules)
# ADMIN_USER_IDS=123456789,987654321

# Limite de requêtes par utilisateur par minute
RATE_LIMIT_PER_MINUTE=10

# ===== CONFIGURATION MONITORING =====
# Activer les métriques Prometheus (true/false)
ENABLE_METRICS=false

# Port pour les métriques
METRICS_PORT=9090
"""
        
        # Créer le répertoire si nécessaire
        self.examples_dir.mkdir(exist_ok=True)
        
        # Écrire le fichier .env
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            print(f"{Fore.GREEN}✅ Fichier de configuration créé: {self.env_file}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur lors de la création du fichier .env: {e}")
            return False
    
    def test_css_api_connection(self):
        """Teste la connexion à l'API CSS"""
        print(f"{Fore.YELLOW}🔍 Test de connexion à l'API CSS...")
        
        # Charger la configuration
        css_api_url = os.getenv('CSS_API_URL', 'http://localhost:8000')
        
        try:
            response = requests.get(f"{css_api_url}/health", timeout=10)
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ API CSS accessible à {css_api_url}")
                return True
            else:
                print(f"{Fore.YELLOW}⚠️ API CSS répond avec le code {response.status_code}")
                print(f"{Fore.YELLOW}   L'API est accessible mais peut avoir des problèmes")
                return True
                
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}❌ Impossible de se connecter à l'API CSS à {css_api_url}")
            print(f"{Fore.YELLOW}💡 Vérifiez que l'API CSS est démarrée")
            return False
            
        except requests.exceptions.Timeout:
            print(f"{Fore.YELLOW}⏰ Timeout lors de la connexion à l'API CSS")
            print(f"{Fore.YELLOW}   L'API peut être lente à répondre")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur lors du test de connexion: {e}")
            return False
    
    def test_telegram_token(self):
        """Teste la validité du token Telegram"""
        print(f"{Fore.YELLOW}🔍 Validation du token Telegram...")
        
        telegram_token = os.getenv('TELEGRAM_TOKEN')
        if not telegram_token:
            print(f"{Fore.RED}❌ Token Telegram non configuré")
            return False
        
        try:
            # Tester le token avec l'API Telegram
            response = requests.get(
                f"https://api.telegram.org/bot{telegram_token}/getMe",
                timeout=10
            )
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_data = bot_info.get('result', {})
                    bot_name = bot_data.get('first_name', 'Bot')
                    bot_username = bot_data.get('username', 'inconnu')
                    
                    print(f"{Fore.GREEN}✅ Token Telegram valide")
                    print(f"{Fore.GREEN}   Bot: {bot_name} (@{bot_username})")
                    return True
                else:
                    print(f"{Fore.RED}❌ Token Telegram invalide")
                    return False
            else:
                print(f"{Fore.RED}❌ Erreur API Telegram: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur lors de la validation du token: {e}")
            return False
    
    def load_env_file(self):
        """Charge le fichier .env dans les variables d'environnement"""
        if not self.env_file.exists():
            return False
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            return True
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur lors du chargement du fichier .env: {e}")
            return False
    
    def start_bot(self):
        """Démarre le bot Telegram"""
        print(f"{Fore.YELLOW}🚀 Démarrage du bot Telegram...")
        
        bot_script = self.examples_dir / "telegram_bot_simple.py"
        
        if not bot_script.exists():
            print(f"{Fore.RED}❌ Script du bot non trouvé: {bot_script}")
            return False
        
        try:
            print(f"{Fore.GREEN}✅ Démarrage du bot...")
            print(f"{Fore.CYAN}📱 Le bot est maintenant actif sur Telegram")
            print(f"{Fore.CYAN}🛑 Appuyez sur Ctrl+C pour arrêter")
            print()
            
            # Démarrer le bot
            subprocess.run([sys.executable, str(bot_script)], check=True)
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}🛑 Arrêt du bot demandé")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}❌ Erreur lors du démarrage du bot: {e}")
            return False
    
    def show_configuration_guide(self):
        """Affiche le guide de configuration Telegram"""
        print(f"{Fore.CYAN}{Style.BRIGHT}📱 GUIDE DE CONFIGURATION TELEGRAM")
        print(f"{Fore.CYAN}" + "="*50)
        print()
        
        print(f"{Fore.YELLOW}1. Créer un bot Telegram:")
        print(f"{Fore.WHITE}   • Ouvrir Telegram et chercher @BotFather")
        print(f"{Fore.WHITE}   • Envoyer /newbot")
        print(f"{Fore.WHITE}   • Choisir un nom pour votre bot")
        print(f"{Fore.WHITE}   • Choisir un username (doit finir par 'bot')")
        print(f"{Fore.WHITE}   • Copier le token fourni")
        print()
        
        print(f"{Fore.YELLOW}2. Configurer les commandes du bot:")
        print(f"{Fore.WHITE}   • Envoyer /setcommands à @BotFather")
        print(f"{Fore.WHITE}   • Sélectionner votre bot")
        print(f"{Fore.WHITE}   • Copier-coller ces commandes:")
        print(f"{Fore.GREEN}     start - Démarrer le bot CSS")
        print(f"{Fore.GREEN}     aide - Obtenir de l'aide")
        print(f"{Fore.GREEN}     menu - Voir les catégories")
        print(f"{Fore.GREEN}     contact - Informations de contact")
        print(f"{Fore.GREEN}     status - Statut du service")
        print()
        
        print(f"{Fore.YELLOW}3. Configurer la description (optionnel):")
        print(f"{Fore.WHITE}   • Envoyer /setdescription à @BotFather")
        print(f"{Fore.WHITE}   • Description suggérée:")
        print(f"{Fore.GREEN}     Assistant virtuel de la Caisse de Sécurité Sociale du Sénégal")
        print()
        
        print(f"{Fore.YELLOW}4. Configurer l'image du bot (optionnel):")
        print(f"{Fore.WHITE}   • Envoyer /setuserpic à @BotFather")
        print(f"{Fore.WHITE}   • Télécharger une image représentant la CSS")
        print()
        
        print(f"{Fore.CYAN}🔗 Liens utiles:")
        print(f"{Fore.WHITE}   • Documentation Telegram Bot API: https://core.telegram.org/bots/api")
        print(f"{Fore.WHITE}   • @BotFather: https://t.me/botfather")
        print()
    
    def show_deployment_options(self):
        """Affiche les options de déploiement"""
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 OPTIONS DE DÉPLOIEMENT")
        print(f"{Fore.CYAN}" + "="*40)
        print()
        
        print(f"{Fore.YELLOW}1. Mode Polling (Développement):")
        print(f"{Fore.WHITE}   • Simple à configurer")
        print(f"{Fore.WHITE}   • Idéal pour les tests")
        print(f"{Fore.WHITE}   • Le bot interroge Telegram régulièrement")
        print(f"{Fore.GREEN}   • Commande: python telegram_bot_simple.py")
        print()
        
        print(f"{Fore.YELLOW}2. Mode Webhook (Production):")
        print(f"{Fore.WHITE}   • Plus efficace")
        print(f"{Fore.WHITE}   • Nécessite HTTPS")
        print(f"{Fore.WHITE}   • Telegram envoie les messages directement")
        print(f"{Fore.GREEN}   • Nécessite un serveur web public")
        print()
        
        print(f"{Fore.YELLOW}3. Déploiement Docker:")
        print(f"{Fore.WHITE}   • Isolation complète")
        print(f"{Fore.WHITE}   • Facile à déployer")
        print(f"{Fore.WHITE}   • Gestion des dépendances automatique")
        print()
        
        print(f"{Fore.YELLOW}4. Déploiement Cloud:")
        print(f"{Fore.WHITE}   • Heroku, AWS, Google Cloud")
        print(f"{Fore.WHITE}   • Scalabilité automatique")
        print(f"{Fore.WHITE}   • Haute disponibilité")
        print()
    
    def get_current_datetime(self):
        """Retourne la date et heure actuelles formatées"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def run_setup(self):
        """Exécute la configuration complète"""
        self.print_header()
        
        # Étape 1: Vérifier Python
        if not self.check_python_version():
            return False
        
        # Étape 2: Installer les dépendances
        print()
        install_deps = input(f"{Fore.YELLOW}📦 Installer les dépendances ? (o/N): ").strip().lower()
        if install_deps in ['o', 'oui', 'y', 'yes']:
            if not self.install_dependencies():
                return False
        
        # Étape 3: Configuration
        print()
        if self.env_file.exists():
            overwrite = input(f"{Fore.YELLOW}⚙️ Fichier .env existe. Reconfigurer ? (o/N): ").strip().lower()
            if overwrite not in ['o', 'oui', 'y', 'yes']:
                print(f"{Fore.GREEN}✅ Utilisation de la configuration existante")
                self.load_env_file()
            else:
                if not self.create_env_file():
                    return False
                self.load_env_file()
        else:
            if not self.create_env_file():
                return False
            self.load_env_file()
        
        # Étape 4: Tests de connexion
        print()
        print(f"{Fore.CYAN}🔍 Tests de connexion...")
        
        css_ok = self.test_css_api_connection()
        telegram_ok = self.test_telegram_token()
        
        if not telegram_ok:
            print(f"{Fore.RED}❌ Configuration Telegram invalide")
            return False
        
        if not css_ok:
            print(f"{Fore.YELLOW}⚠️ API CSS non accessible, mais le bot peut démarrer")
        
        # Étape 5: Démarrage
        print()
        start_bot = input(f"{Fore.YELLOW}🚀 Démarrer le bot maintenant ? (O/n): ").strip().lower()
        if start_bot not in ['n', 'non', 'no']:
            self.start_bot()
        else:
            print(f"{Fore.GREEN}✅ Configuration terminée")
            print(f"{Fore.CYAN}💡 Pour démarrer le bot: python examples/telegram_bot_simple.py")
        
        return True

def main():
    """Point d'entrée principal"""
    setup = TelegramBotSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "guide":
            setup.show_configuration_guide()
        elif command == "deploy":
            setup.show_deployment_options()
        elif command == "test":
            setup.load_env_file()
            setup.test_css_api_connection()
            setup.test_telegram_token()
        else:
            print(f"{Fore.RED}❌ Commande inconnue: {command}")
            print(f"{Fore.YELLOW}💡 Commandes disponibles: guide, deploy, test")
    else:
        # Configuration interactive complète
        try:
            success = setup.run_setup()
            if success:
                print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 Configuration terminée avec succès !")
            else:
                print(f"\n{Fore.RED}{Style.BRIGHT}❌ Échec de la configuration")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}🛑 Configuration interrompue")
        except Exception as e:
            print(f"\n{Fore.RED}💥 Erreur inattendue: {e}")

if __name__ == '__main__':
    main()