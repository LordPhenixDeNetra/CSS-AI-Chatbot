#!/usr/bin/env python3

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os


def create_test_pdf():
    """Crée un PDF de test simple"""
    filename = "test_document.pdf"

    try:
        # Création du PDF
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        # Ajout de contenu
        c.setFont("Helvetica", 16)
        c.drawString(100, height - 100, "Document de Test PDF")

        c.setFont("Helvetica", 12)
        y_position = height - 150

        content = [
            "Ceci est un document PDF de test pour vérifier",
            "le fonctionnement de l'endpoint upload-multimodal-document.",
            "",
            "Contenu du test:",
            "- Texte simple dans un PDF",
            "- Vérification de l'upload multimodal",
            "- Test de l'API RAG avec documents PDF",
            "",
            "Ce document contient du texte qui devrait être",
            "extrait et indexé par le système RAG multimodal.",
            "",
            "Test réalisé pour valider l'implémentation",
            "des fonctionnalités multimodales."
        ]

        for line in content:
            c.drawString(100, y_position, line)
            y_position -= 20

        c.save()
        print(f"✅ PDF créé: {filename}")
        return filename

    except ImportError:
        print("❌ Module reportlab non installé. Installation...")
        os.system("pip install reportlab")
        return create_test_pdf()
    except Exception as e:
        print(f"❌ Erreur lors de la création du PDF: {e}")
        return None


if __name__ == "__main__":
    create_test_pdf()
