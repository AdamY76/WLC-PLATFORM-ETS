# Guide d'Installation - Plateforme WLC

Ce guide explique comment installer la plateforme sur Windows ou Mac. L'installation prend environ 30 minutes.

---

## Vue d'Ensemble

**Ce dont vous avez besoin :**
- Miniconda (gestionnaire de packages Python)
- GraphDB Desktop (base de données RDF)
- Le code source de la plateforme
- Une connexion internet pour télécharger les dépendances

**Pourquoi Miniconda ?**
Sur Windows, certaines bibliothèques Python (notamment `ifcopenshell`) sont difficiles à installer avec `pip` standard. Miniconda installe automatiquement les versions pré-compilées compatibles, ce qui évite 90% des problèmes d'installation.

---

## Installation sur Windows

### Étape 1 : Installer Miniconda (5 minutes)

1. Aller sur : https://docs.conda.io/en/latest/miniconda.html
2. Télécharger **"Miniconda3 Windows 64-bit"** (fichier `.exe`)
3. Double-cliquer sur le fichier pour lancer l'installation
4. **Important** : Ne PAS cocher "Add Miniconda to my PATH" (méthode recommandée par l'installeur)
5. Cliquer sur "Install" et attendre 2-3 minutes
6. Cliquer sur "Finish"

### Étape 2 : Télécharger le Projet (2 minutes)

Ouvrir **"Anaconda Prompt"** (le chercher dans le menu Démarrer Windows) :

```bash
# Aller sur le Bureau
cd C:\Users\VotreNom\Desktop

# Cloner le projet depuis GitHub
git clone https://github.com/AdamY76/WLC-PLATFORM-ETS.git

# Entrer dans le dossier
cd WLC-PLATFORM-ETS
```

Si Git n'est pas installé, télécharger depuis : https://git-scm.com/download/win

Alternativement, télécharger le ZIP depuis GitHub et le décompresser sur le Bureau.

### Étape 3 : Créer l'Environnement Python (10 minutes)

**Dans Anaconda Prompt** :

```bash
# Créer un environnement virtuel avec Python 3.11
conda create -n wlc python=3.11 -y

# Activer l'environnement
conda activate wlc
```

Vous devez maintenant voir `(wlc)` au début de votre ligne de commande.

**Installer les dépendances** :

```bash
# Installer les packages complexes via conda (méthode fiable)
conda install -c conda-forge ifcopenshell pandas flask flask-cors requests openpyxl python-dotenv -y

# Installer les packages simples via pip
pip install Werkzeug==3.0.1 gunicorn==21.2.0
```

Attendre 5-10 minutes que tout se télécharge.

### Étape 4 : Installer GraphDB (5 minutes)

1. Aller sur : https://www.ontotext.com/products/graphdb/
2. Choisir **"GraphDB Free"** (version gratuite)
3. Télécharger la version Windows
4. Installer en double-cliquant sur le fichier `.exe`
5. Lancer **"GraphDB Desktop"** depuis le menu Démarrer
6. Attendre 30 secondes que l'application démarre

### Étape 5 : Configurer GraphDB (5 minutes)

**Dans l'interface GraphDB qui s'est ouverte** :

1. **Créer le repository** :
   - Cliquer sur **"Setup"** (en haut) puis **"Repositories"**
   - Cliquer sur **"Create new repository"**
   - **Repository ID** : taper exactement `wlconto`
   - **Ruleset** : choisir **"OWL-Horst (optimized)"**
   - Cliquer sur **"Create"**

2. **Importer les ontologies** :
   - Cliquer sur **"Import"** (menu du haut) puis **"RDF"**
   - Cliquer sur **"Upload RDF files"**
   - Naviguer vers `C:\Users\VotreNom\Desktop\WLC-PLATFORM-ETS\Ontology\`
   - Sélectionner les fichiers suivants (un par un) :
     - `cgontologie1.ttl`
     - `ontology.ttl` (fichier volumineux, prend 3-5 minutes)
     - `stakeholder_mapping_clean.ttl`
   - Pour chaque fichier, avant de cliquer "Import", définir la **Base URI** :
     ```
     http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#
     ```
   - Cliquer sur **"Import"** et attendre

**Vérification** : En haut à droite de GraphDB, vous devez voir `wlconto` sélectionné dans le menu déroulant.

### Étape 6 : Lancer l'Application (1 minute)

**Retourner dans Anaconda Prompt** (avec `(wlc)` visible) :

```bash
cd Backend
python app.py
```

Vous devez voir :
```
 * Running on http://0.0.0.0:8000
 * Running on http://127.0.0.1:8000
```

**Ouvrir le navigateur** : http://localhost:8000

Vérifier qu'un badge vert "Connecté" apparaît en haut à droite de l'interface.

---

## Installation sur Mac

### Étape 1 : Installer Miniconda (3 minutes)

**Méthode A : Via Terminal (recommandée)** :

```bash
# Télécharger Miniconda pour Mac
# Pour Mac avec puce Apple Silicon (M1/M2/M3) :
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh

# Pour Mac Intel (ancien) :
# curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

# Installer
bash Miniconda3-latest-MacOSX-arm64.sh

# Suivre les instructions :
# - Appuyer sur Entrée pour lire la licence
# - Taper "yes" pour accepter
# - Appuyer sur Entrée pour confirmer l'emplacement
# - Taper "yes" pour initialiser conda

# Fermer et rouvrir le Terminal
```

**Méthode B : Via le site web** :
1. Aller sur : https://docs.conda.io/en/latest/miniconda.html
2. Télécharger le fichier `.pkg` correspondant à votre Mac (Apple Silicon ou Intel)
3. Double-cliquer et suivre l'assistant d'installation
4. Fermer et rouvrir le Terminal

### Étape 2 : Télécharger le Projet (2 minutes)

**Dans le Terminal** :

```bash
# Aller sur le Bureau
cd ~/Desktop

# Cloner le projet depuis GitHub
git clone https://github.com/AdamY76/WLC-PLATFORM-ETS.git

# Entrer dans le dossier
cd WLC-PLATFORM-ETS
```

### Étape 3 : Créer l'Environnement Python (10 minutes)

**Dans le Terminal** :

```bash
# Créer un environnement virtuel avec Python 3.11
conda create -n wlc python=3.11 -y

# Activer l'environnement
conda activate wlc
```

Vous devez voir `(wlc)` au début de votre ligne.

**Installer les dépendances** :

```bash
# Installer via conda (packages complexes)
conda install -c conda-forge ifcopenshell pandas flask flask-cors requests openpyxl python-dotenv -y

# Installer via pip (packages simples)
pip install Werkzeug==3.0.1 gunicorn==21.2.0
```

### Étape 4 : Installer GraphDB (5 minutes)

1. Aller sur : https://www.ontotext.com/products/graphdb/
2. Choisir **"GraphDB Free"**
3. Télécharger la version Mac
4. Ouvrir le fichier `.dmg` téléchargé
5. Glisser l'application GraphDB dans le dossier Applications
6. Lancer GraphDB depuis le dossier Applications
7. Si macOS bloque l'ouverture : Préférences Système → Confidentialité et sécurité → Autoriser

### Étape 5 : Configurer GraphDB (5 minutes)

Suivre exactement les mêmes étapes que pour Windows (voir section Windows, Étape 5).

### Étape 6 : Lancer l'Application (1 minute)

**Dans le Terminal** (avec `(wlc)` visible) :

```bash
cd Backend
python app.py
```

**Ouvrir le navigateur** : http://localhost:8000

---

## Utilisation Quotidienne

### Windows

Chaque fois que vous voulez utiliser la plateforme :

1. Lancer **GraphDB Desktop** (menu Démarrer)
2. Ouvrir **"Anaconda Prompt"** (menu Démarrer)
3. Taper les commandes suivantes :
   ```bash
   conda activate wlc
   cd C:\Users\VotreNom\Desktop\WLC-PLATFORM-ETS\Backend
   python app.py
   ```
4. Ouvrir le navigateur : http://localhost:8000

### Mac

1. Lancer **GraphDB** (Applications)
2. Ouvrir le **Terminal**
3. Taper les commandes suivantes :
   ```bash
   conda activate wlc
   cd ~/Desktop/WLC-PLATFORM-ETS/Backend
   python app.py
   ```
4. Ouvrir le navigateur : http://localhost:8000

---

## Dépannage

### Problème : "conda: command not found" (Windows)

**Cause** : Vous utilisez PowerShell ou CMD au lieu d'Anaconda Prompt.

**Solution** : Toujours utiliser **"Anaconda Prompt"** depuis le menu Démarrer Windows.

### Problème : "conda: command not found" (Mac)

**Cause** : Miniconda n'a pas été initialisé dans le Terminal.

**Solution** :
```bash
# Initialiser conda manuellement
~/miniconda3/bin/conda init zsh  # ou bash selon votre shell

# Fermer et rouvrir le Terminal
```

### Problème : "(wlc) n'apparaît pas"

**Cause** : L'environnement n'est pas activé.

**Solution** : Taper `conda activate wlc` avant toute commande.

### Problème : "ModuleNotFoundError: No module named 'ifcopenshell'"

**Cause** : Vous n'êtes pas dans l'environnement wlc, ou ifcopenshell n'est pas installé.

**Solution** :
```bash
# Vérifier que (wlc) est visible
conda activate wlc

# Réinstaller ifcopenshell si nécessaire
conda install -c conda-forge ifcopenshell -y
```

### Problème : "ValueError: numpy.dtype size changed"

**Cause** : Conflit entre les versions de pandas et numpy.

**Solution** :
```bash
conda activate wlc
conda install -c conda-forge pandas -y
```

### Problème : Badge "Déconnecté" dans l'interface

**Cause** : GraphDB n'est pas lancé ou le repository n'existe pas.

**Solution** :
1. Vérifier que GraphDB Desktop est lancé
2. Ouvrir http://localhost:7200 pour vérifier l'accès à GraphDB
3. Vérifier que le repository `wlconto` existe (Setup → Repositories)
4. Vérifier le fichier `Backend/config/config.py` :
   ```python
   GRAPHDB_URL = "http://localhost:7200"
   GRAPHDB_REPO = "wlconto"
   ```

### Problème : "Port 8000 already in use"

**Windows** :
```bash
netstat -ano | findstr :8000
taskkill /F /PID <numero_du_processus>
```

**Mac** :
```bash
lsof -i :8000
kill -9 <PID>
```

### Problème : "Repository wlconto not found"

**Cause** : Le repository n'a pas été créé dans GraphDB.

**Solution** : Retourner à l'Étape 5 de l'installation et créer le repository.

---

## Désinstallation Complète

### Windows

1. Supprimer l'environnement conda :
   ```bash
   conda deactivate
   conda env remove -n wlc
   ```
2. Désinstaller Miniconda : Panneau de configuration → Programmes → Désinstaller Miniconda3
3. Désinstaller GraphDB : Panneau de configuration → Programmes → Désinstaller GraphDB
4. Supprimer le dossier du projet : Supprimer `C:\Users\VotreNom\Desktop\WLC-PLATFORM-ETS`

### Mac

1. Supprimer l'environnement conda :
   ```bash
   conda deactivate
   conda env remove -n wlc
   ```
2. Désinstaller Miniconda :
   ```bash
   rm -rf ~/miniconda3
   ```
3. Supprimer GraphDB : Glisser l'application GraphDB de Applications vers la Corbeille
4. Supprimer le dossier du projet :
   ```bash
   rm -rf ~/Desktop/WLC-PLATFORM-ETS
   ```

---

## Résumé des Commandes Essentielles

| Action | Windows | Mac |
|--------|---------|-----|
| Ouvrir terminal spécial | Anaconda Prompt (menu Démarrer) | Terminal normal |
| Activer environnement | `conda activate wlc` | `conda activate wlc` |
| Aller au projet | `cd C:\Users\...\WLC-PLATFORM-ETS\Backend` | `cd ~/Desktop/WLC-PLATFORM-ETS/Backend` |
| Lancer l'application | `python app.py` | `python app.py` |
| Arrêter l'application | `Ctrl+C` | `Ctrl+C` |

---

## Support

Pour toute question ou problème :
1. Consulter la section Dépannage ci-dessus
2. Vérifier les logs dans le terminal lors du lancement
3. Créer une issue sur GitHub avec :
   - Votre système d'exploitation (Windows 10/11 ou macOS version)
   - Version de Python : `python --version`
   - Message d'erreur complet

