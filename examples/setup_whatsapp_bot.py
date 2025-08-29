#!/usr/bin/env python3
"""
Script de configuration et démarrage du bot WhatsApp CSS
Ce script aide à configurer et démarrer le bot WhatsApp.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Vérifie la version de Python"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ requis")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} détecté")

def install_dependencies():
    """Installe les dépendances"""
    print("📦 Installation des dépendances...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements_whatsapp.txt"
        ])
        print("✅ Dépendances installées")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'installation des dépendances")
        sys.exit(1)

def create_env_file():
    """Crée le fichier .env avec les variables d'environnement"""
    env_file = Path(".env.whatsapp")
    
    if env_file.exists():
        print("📄 Fichier .env.whatsapp existe déjà")
        return
    
    print("📝 Création du fichier de configuration...")
    
    # Demander les informations à l'utilisateur
    print("\n🔧 Configuration WhatsApp Business API:")
    whatsapp_token = input("Token WhatsApp Business API: ").strip()
    phone_id = input("Phone Number ID: ").strip()
    verify_token = input("Webhook Verify Token: ").strip()
    
    print("\n🔧 Configuration API CSS:")
    css_api_url = input("URL API CSS [http://localhost:8000]: ").strip() or "http://localhost:8000"
    
    print("\n🔧 Configuration serveur:")
    port = input("Port du webhook [5000]: ").strip() or "5000"
    debug = input("Mode debug [false]: ").strip().lower() or "false"
    
    # Créer le contenu du fichier .env
    env_content = f"""# Configuration WhatsApp Business API
WHATSAPP_TOKEN={whatsapp_token}
WHATSAPP_PHONE_ID={phone_id}
WEBHOOK_VERIFY_TOKEN={verify_token}

# Configuration API CSS
CSS_API_URL={css_api_url}

# Configuration serveur
PORT={port}
DEBUG={debug}

# Configuration Redis (optionnel)
REDIS_URL=redis://localhost:6379

# Configuration logging
LOG_LEVEL=INFO
LOG_FILE=whatsapp_bot.log
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ Fichier {env_file} créé")
    print("⚠️  Assurez-vous de ne pas partager ce fichier (il contient vos tokens secrets)")

def check_css_api():
    """Vérifie si l'API CSS est accessible"""
    print("🔍 Vérification de l'API CSS...")
    
    try:
        import requests
        from dotenv import load_dotenv
        
        # Charger les variables d'environnement
        load_dotenv(".env.whatsapp")
        css_api_url = os.getenv('CSS_API_URL', 'http://localhost:8000')
        
        response = requests.get(f"{css_api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ API CSS accessible sur {css_api_url}")
            return True
        else:
            print(f"⚠️  API CSS répond avec le code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Impossible de se connecter à l'API CSS sur {css_api_url}")
        print("   Assurez-vous que le serveur CSS est démarré")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def start_bot():
    """Démarre le bot WhatsApp"""
    print("🚀 Démarrage du bot WhatsApp...")
    
    try:
        # Charger les variables d'environnement
        from dotenv import load_dotenv
        load_dotenv(".env.whatsapp")
        
        # Démarrer le bot
        subprocess.run([sys.executable, "whatsapp_bot_simple.py"])
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bot")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")

def show_configuration_help():
    """Affiche l'aide pour la configuration WhatsApp"""
    print("""
📋 **Guide de configuration WhatsApp Business API**

1️⃣ **Créer une application Meta**
   • Aller sur https://developers.facebook.com/
   • Créer une nouvelle application
   • Ajouter le produit "WhatsApp Business API"

2️⃣ **Obtenir les tokens**
   • Token d'accès temporaire (24h) dans la console
   • Phone Number ID dans les paramètres WhatsApp
   • Créer un Verify Token personnalisé

3️⃣ **Configurer le webhook**
   • URL: https://votre-domaine.com/webhook
   • Verify Token: celui que vous avez créé
   • Champs: messages

4️⃣ **Tester la configuration**
   • Envoyer un message au numéro de test
   • Vérifier les logs du webhook

📚 **Documentation officielle:**
https://developers.facebook.com/docs/whatsapp/business-management-api/get-started

⚠️  **Important:**
• Le webhook doit être accessible via HTTPS
• Utilisez ngrok pour les tests en local
• Les tokens temporaires expirent après 24h
""")

def main():
    """Fonction principale"""
    print("🤖 Configuration du Bot WhatsApp CSS")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "help":
            show_configuration_help()
            return
        elif command == "install":
            check_python_version()
            install_dependencies()
            return
        elif command == "config":
            create_env_file()
            return
        elif command == "check":
            check_css_api()
            return
        elif command == "start":
            start_bot()
            return
        else:
            print(f"❌ Commande inconnue: {command}")
            print("Commandes disponibles: help, install, config, check, start")
            return
    
    # Configuration complète
    print("🔧 Configuration automatique...\n")
    
    # 1. Vérifier Python
    check_python_version()
    
    # 2. Installer les dépendances
    install_dependencies()
    
    # 3. Créer le fichier de configuration
    create_env_file()
    
    # 4. Vérifier l'API CSS
    css_ok = check_css_api()
    
    print("\n" + "=" * 40)
    print("✅ Configuration terminée !")
    
    if css_ok:
        print("\n🚀 Pour démarrer le bot:")
        print("   python setup_whatsapp_bot.py start")
    else:
        print("\n⚠️  Démarrez d'abord l'API CSS:")
        print("   uvicorn app.main:app --reload")
        print("\n   Puis démarrez le bot:")
        print("   python setup_whatsapp_bot.py start")
    
    print("\n📚 Pour voir le guide de configuration WhatsApp:")
    print("   python setup_whatsapp_bot.py help")

if __name__ == "__main__":
    main()