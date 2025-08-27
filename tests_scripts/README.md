# Scripts de Test

Ce dossier contient tous les scripts Python de test pour l'API RAG Ultra Performant Multimodal.

## Fichiers de test inclus :

### Tests de création et génération
- `create_test_pdf.py` - Script pour créer des fichiers PDF de test

### Tests de suppression
- `test_delete_document.py` - Test de suppression de documents
- `test_upload_and_delete.py` - Test d'upload et suppression de fichiers
- `test_standard_upload_delete.py` - Test standard d'upload et suppression

### Tests de fonctionnalités multimodales
- `test_multimodal_capabilities.py` - Test des capacités multimodales
- `test_multimodal_question.py` - Test des questions multimodales
- `test_multimodal_upload.py` - Test d'upload de contenu multimodal

### Tests de débogage et logging
- `test_logger_debug.py` - Test du système de logging en mode debug
- `test_stream_debug.py` - Test du streaming en mode debug

## Utilisation

Pour exécuter un test spécifique :
```bash
python tests_scripts/nom_du_test.py
```

Pour exécuter tous les tests :
```bash
python -m pytest tests_scripts/
```

## Notes

- Ces scripts sont conçus pour tester différents aspects de l'API RAG
- Assurez-vous que l'API est en cours d'exécution avant de lancer les tests
- Certains tests peuvent nécessiter des fichiers de test spécifiques