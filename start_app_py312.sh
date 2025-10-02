#!/bin/bash

# Script de lancement de la Plateforme WLC avec Python 3.12
# Résout le problème de compatibilité ifcopenshell avec Python 3.13

echo "🚀 Démarrage de la Plateforme WLC avec Python 3.12..."
echo "📦 Activation de l'environnement virtuel Python 3.12..."

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv_py312" ]; then
    echo "❌ L'environnement virtuel Python 3.12 n'existe pas!"
    echo "💡 Exécutez d'abord: /opt/homebrew/bin/python3.12 -m venv venv_py312"
    echo "💡 Puis installez les dépendances: source venv_py312/bin/activate && pip install ifcopenshell flask requests pandas openpyxl python-dotenv"
    exit 1
fi

# Activer l'environnement virtuel
source venv_py312/bin/activate

# Vérifier que les dépendances sont installées
echo "🔍 Vérification des dépendances..."
python -c "import ifcopenshell, flask, requests, pandas, openpyxl; print('✅ Toutes les dépendances sont disponibles')" || {
    echo "❌ Dépendances manquantes. Installation en cours..."
    pip install ifcopenshell flask requests pandas openpyxl python-dotenv
}

# Démarrer l'application
echo "🎯 Démarrage de l'application Flask..."
echo "🌐 Interface disponible sur: http://localhost:8000"
echo "📄 Fonctionnalité IFC parsing maintenant disponible!"
echo ""
echo "Pour arrêter l'application: Ctrl+C"
echo "=========================================="

cd Backend && python app.py 