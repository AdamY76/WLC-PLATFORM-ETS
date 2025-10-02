# Dockerfile pour le Backend Flask
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer répertoire de travail
WORKDIR /app

# Copier requirements (sans ifcopenshell - parsing IFC fait sur machine hôte)
COPY Backend/requirements-docker.txt requirements.txt

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code backend
COPY Backend/ .

# Copier le frontend (sera servi par Flask)
COPY Frontend/ /app/Frontend/

# Exposer le port
EXPOSE 8000

# Variables d'environnement
ENV FLASK_APP=app.py
ENV GRAPHDB_URL=http://graphdb:7200
ENV GRAPHDB_REPO=wlconto

# Commande de démarrage
CMD ["python", "app.py"]

