import os
from dotenv import load_dotenv

load_dotenv()

# Configuration de GraphDB
GRAPHDB_URL = os.getenv('GRAPHDB_URL', 'http://localhost:7200')
GRAPHDB_REPO_NAME = os.getenv('GRAPHDB_REPO_NAME', 'wlconto')
GRAPHDB_REPO = f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO_NAME}"

# Configuration de l'application
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'ifc'}

# Création du dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

# Debug: Afficher la configuration GraphDB
print(f"GraphDB URL configurée: {GRAPHDB_REPO}")
print(f"GraphDB Update Endpoint: {GRAPHDB_REPO}/statements") 