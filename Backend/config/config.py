# backend/config.py
import os
from pathlib import Path

class Config:
    # Configuration de GraphDB
    # Supporte les variables d'environnement Docker
    GRAPHDB_URL = os.environ.get('GRAPHDB_URL', "http://localhost:7200")
    GRAPHDB_REPO = os.environ.get('GRAPHDB_REPO', "wlconto")  # Nom du repository uniquement
    
    # Configuration des dossiers
    BASE_DIR = Path(__file__).resolve().parent.parent
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    
    # Extensions de fichiers autorisées
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    
    # Configuration de l'application
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    @staticmethod
    def ensure_upload_folder():
        """
        S'assure que le dossier d'upload existe.
        """
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
            
    @staticmethod
    def allowed_file(filename, extension=None):
        """
        Vérifie si le fichier a une extension autorisée.
        
        Args:
            filename (str): Nom du fichier à vérifier
            extension (str, optional): Extension spécifique à vérifier. Si None, vérifie toutes les extensions autorisées.
            
        Returns:
            bool: True si le fichier est autorisé, False sinon
        """
        if not filename:
            return False
        if '.' not in filename:
            return False
            
        ext = filename.rsplit('.', 1)[1].lower()
        if extension:
            return ext == extension.lower()
        return ext in Config.ALLOWED_EXTENSIONS
            
    @staticmethod
    def get_upload_path(filename):
        """
        Retourne le chemin complet pour un fichier uploadé.
        
        Args:
            filename (str): Nom du fichier
            
        Returns:
            str: Chemin complet du fichier
        """
        Config.ensure_upload_folder()
        return os.path.join(Config.UPLOAD_FOLDER, filename)

