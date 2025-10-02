# Plateforme de Gestion du Coût Global (WLC)

Cette plateforme permet de visualiser et gérer le coût global (Whole Life Cost) des projets de construction, en s'appuyant sur une ontologie RDF (WLCONTO) hébergée dans GraphDB.

---

## 🚀 Démarrage Rapide (Recommandé)

### **🐳 Avec Docker (3 commandes, 5 minutes)**

```bash
git clone https://github.com/AdamY76/WLC-PLATFORM-ETS.git
cd WLC-PLATFORM-ETS
docker-compose up -d
```

**Puis ouvrir** : http://localhost:8000

✅ **Tout est automatique** : GraphDB, ontologies, backend Flask !

📖 **Guide complet** : Voir [`DOCKER_QUICKSTART.md`](DOCKER_QUICKSTART.md)

---

### **⚙️ Installation Manuelle (si pas Docker)**

Continuer avec le guide détaillé ci-dessous ⬇️

---

## 🚀 Fonctionnalités

### 📊 Analyse de Cycle de Vie (WLC)
- Import et parsing de fichiers IFC
- Gestion des coûts par phase (Construction, Opération, Maintenance, Fin de vie)
- Calcul des durées de vie des éléments
- Visualisation des coûts répartis dans le temps

### 🏗️ Édition Interactive
- **Édition des coûts** : Modification directe des coûts par phase dans le tableau
- **Édition des durées de vie** : Modification des durées de vie des éléments
- **Édition des matériaux** : Modification des matériaux des éléments
- **Feedback visuel amélioré** : Indicateurs de chargement, succès et erreur
- **Synchronisation automatique** : Mise à jour en temps réel de l'ontologie RDF

### 🔄 Intégration Ontologique
- Base de connaissances RDF avec GraphDB
- Requêtes SPARQL pour l'extraction de données
- Mise à jour automatique des instances RDF lors des modifications

### 🔍 Mapping Interface ↔ Ontologie RDF (WLCONTO)

#### **Correspondances Exactes des Classes de Coûts**

| **Colonne Interface** | **Classe RDF** | **Attribution Temporelle** |
|----------------------|----------------|---------------------------|
| `ConstructionCost` | `wlc:ConstructionCosts` | Année 0 |
| `OperationCost` | `wlc:OperationCosts` | Années 1 à N-1 |
| `MaintenanceCost` | `wlc:MaintenanceCosts` | Multiples de durée de vie élément |
| `EndOfLifeCost` | `wlc:EndOfLifeCosts` | Année N (fin de projet) |

#### **Logique de Répétition des MaintenanceCosts**

Pour un élément avec durée de vie de **30 ans** dans un projet de **100 ans** :
- Coût de maintenance appliqué aux années : **30, 60, 90**
- Génération automatique d'instances liées via `wlc:ForDate`

#### **Structure des Instances RDF Générées**

```sparql
<element_uri/cost/maintenancecosts_abc123> a wlc:MaintenanceCosts, wlc:Costs ;
    wlc:hasCostValue "5000"^^xsd:double ;
    wlc:appliesTo <element_uri> ;
    wlc:ForDate <project_uri/lifespan/Year30> .
```

#### **Gestion Anti-Doublons**

- **✅ Suppression automatique** des anciennes instances avant création de nouvelles
- **✅ Requêtes DELETE/INSERT** atomiques pour éviter les incohérences
- **✅ Vérification d'intégrité** disponible via `/verify-cost-integrity`

## 📦 Guide de Déploiement Complet (sur un autre ordinateur)

### Prérequis Système

- **Python 3.8+** (testé avec Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13)
  - ⚠️ **Note** : `requirements.txt` utilise `pandas==1.5.3` pour compatibilité Python 3.8+
  - Si vous utilisez Python 3.9+, vous pouvez upgrader pandas : `pip install pandas>=2.0`
- **GraphDB 10.0+** (base de données RDF)
- **Navigateur web moderne** (Chrome, Firefox, Safari, Edge)
- **4 GB RAM minimum** (8 GB recommandé)

### Étape 1 : Installation de GraphDB

1. **Télécharger GraphDB** :
   - Aller sur [https://www.ontotext.com/products/graphdb/](https://www.ontotext.com/products/graphdb/)
   - Télécharger **GraphDB Free** (ou version Desktop)
   - Installer en suivant les instructions pour votre OS

2. **Démarrer GraphDB** :
   ```bash
   # Sur macOS/Linux
   cd /path/to/graphdb/bin
   ./graphdb
   
   # Sur Windows
   graphdb.bat
   ```

3. **Accéder à l'interface GraphDB** :
   - Ouvrir navigateur : `http://localhost:7200`
   - GraphDB devrait afficher l'interface de gestion

### Étape 2 : Création et Configuration du Repository

1. **Créer un nouveau repository** :
   - Dans GraphDB, cliquer sur **"Setup"** > **"Repositories"**
   - Cliquer sur **"Create new repository"**
   - Paramètres :
     - **Repository ID** : `wlconto`
     - **Repository title** : `WLC Platform Repository`
     - **Ruleset** : OWL-Horst (optimized)
     - Garder les autres paramètres par défaut
   - Cliquer sur **"Create"**

2. **Sélectionner le repository** :
   - Dans le coin supérieur droit, sélectionner `wlconto` dans le menu déroulant

### Étape 3 : Import des Ontologies dans GraphDB

**IMPORTANT** : Importer les ontologies dans l'ordre suivant (du plus général au plus spécifique) :

**📍 Aller dans GraphDB → Import → RDF → Upload RDF files**

1. **cgontologie1.ttl** (ontologie principale WLCONTO)
   - Fichier : `Ontology/cgontologie1.ttl`
   - **Base URI** : `http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#`
   - Cliquer sur **"Import"**
   - ✅ ~202 statements

2. **ontology.ttl** (ontologie étendue - grosse)
   - Fichier : `Ontology/ontology.ttl`
   - **Base URI** : `http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#`
   - Cliquer sur **"Import"**
   - ⏱️ Import peut prendre 3-5 minutes
   - ✅ ~34,156 statements

3. **Mapping.ttl** (mappings entre ontologies)
   - Si disponible dans votre configuration
   - ✅ ~66 statements

4. **uniformat.ttl** (classification Uniformat)
   - Si disponible dans votre configuration
   - ✅ ~1,515 statements

5. **uniformat_ifc_broad_alignment.ttl** (alignement IFC-Uniformat)
   - Si disponible dans votre configuration
   - ✅ ~307 statements

6. **stakeholder_mapping_clean.ttl** (parties prenantes)
   - Fichier : `Ontology/stakeholder_mapping_clean.ttl`
   - **Base URI** : `http://www.semanticweb.org/adamy/ontologies/2025/WLCPO#`
   - Cliquer sur **"Import"**
   - ✅ ~153 statements

7. **6_EndOfLifeManagement_Module_Protege.ttl** (fin de vie)
   - Si disponible dans votre configuration GraphDB
   - **Base URI** : `http://www.w3id.org/dpp/EoL#`
   - ✅ ~512 statements

8. **WLCPODPP.ttl** (module d'alignement DPP)
   - Créer un fichier `WLCPODPP.ttl` avec :
     ```turtle
     @prefix wlcpo: <http://www.semanticweb.org/adamy/ontologies/2025/WLCPO#> .
     @prefix dpp: <http://www.semanticweb.org/adamy/ontologies/2025/DPP#> .
     @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
     
     wlcpo:Asset rdfs:subClassOf dpp:Product .
     ```
   - Importer ce fichier dans GraphDB
   - ✅ ~3 statements

**Total attendu** : ~36,914 statements (peut varier selon les fichiers disponibles)

### Étape 4 : Copie des Fichiers du Projet

1. **Copier le dossier complet** :
   ```bash
   # Copier tout le dossier Plateforme sur le nouvel ordinateur
   scp -r Plateforme/ utilisateur@nouveau-ordinateur:/chemin/destination/
   
   # Ou utiliser USB, Git, etc.
   ```

2. **Structure minimale requise** :
   ```
   Plateforme/
   ├── Backend/
   │   ├── config/
   │   │   ├── __init__.py
   │   │   └── config.py
   │   ├── app.py
   │   ├── sparql_client.py
   │   ├── comparison_routes.py
   │   ├── requirements.txt
   │   └── uploads/ (vide, sera créé automatiquement)
   ├── Frontend/
   │   ├── assets/
   │   │   ├── css/main.css
   │   │   └── js/main.js
   │   └── index.html
   └── Ontology/ (optionnel, déjà dans GraphDB)
   ```

### Étape 5 : Installation de l'Environnement Python

1. **Vérifier la version de Python** :
   ```bash
   python --version  # Doit être 3.8 ou supérieur
   # ou
   python3 --version
   ```

2. **Créer un environnement virtuel** :
   ```bash
   cd Plateforme/Backend
   python -m venv venv
   ```

3. **Activer l'environnement virtuel** :
   ```bash
   # Sur macOS/Linux
   source venv/bin/activate
   
   # Sur Windows
   venv\Scripts\activate
   ```

4. **Installer les dépendances** :
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   **Note** : Si `ifcopenshell` pose problème :
   ```bash
   # Sur macOS/Linux
   pip install ifcopenshell==0.8.2
   
   # Sur Windows, télécharger depuis:
   # https://github.com/IfcOpenShell/IfcOpenShell/releases
   ```

### Étape 6 : Configuration de l'Application

1. **Vérifier le fichier de configuration** :
   - Ouvrir `Backend/config/config.py`
   - Vérifier que les paramètres correspondent :
     ```python
     GRAPHDB_URL = "http://localhost:7200"
     GRAPHDB_REPO = "wlconto"  # Doit correspondre au nom du repository
     ```

2. **Configuration optionnelle** (fichier `.env`) :
   - Créer `Backend/.env` (optionnel) :
     ```
     FLASK_ENV=development
     GRAPHDB_URL=http://localhost:7200
     GRAPHDB_REPO=wlconto
     ```

### Étape 7 : Démarrage de l'Application

1. **S'assurer que GraphDB est démarré** :
   - Vérifier que `http://localhost:7200` est accessible
   - Le repository `wlconto` doit être sélectionné

2. **Démarrer le serveur Flask** :
   ```bash
   cd Backend
   python app.py
   ```

3. **Vérifier le démarrage** :
   - Le terminal devrait afficher :
     ```
     * Running on http://0.0.0.0:8000
     * Running on http://127.0.0.1:8000
     ```

4. **Accéder à l'application** :
   - Ouvrir navigateur : `http://localhost:8000`
   - Vérifier que le badge **"Connecté"** apparaît en haut à droite

### Étape 8 : Test de Fonctionnement

1. **Test de connexion GraphDB** :
   - Le badge en haut à droite doit être vert avec "Connecté"
   - Si rouge : vérifier que GraphDB est démarré et le repository existe

2. **Test d'import IFC** :
   - Aller dans l'onglet **"Gestion IFC"**
   - Importer un fichier `.ifc` de test
   - Cliquer sur **"Parser vers ontologie"**
   - Les éléments devraient apparaître dans le tableau

3. **Test de l'onglet Fin de Vie** :
   - Aller dans l'onglet **"Gestion Fin de Vie"**
   - Les éléments devraient s'afficher avec leurs descriptions Uniformat
   - Tester l'ajout d'une stratégie EOL

### Étape 9 : Troubleshooting Commun

| **Problème** | **Solution** |
|--------------|-------------|
| Port 8000 déjà utilisé | `lsof -i :8000` puis `kill -9 [PID]` |
| GraphDB non accessible | Vérifier que GraphDB est démarré sur port 7200 |
| Badge "Déconnecté" | Vérifier repository name dans `config.py` |
| Erreur `ifcopenshell` | Réinstaller : `pip install --force-reinstall ifcopenshell==0.8.2` |
| Erreur SPARQL | Vérifier que les ontologies sont importées dans GraphDB |
| Onglet EOL vide | Vérifier que l'ontologie EoL est importée avec prefix `eol:` |

### Étape 10 : Export/Import de Données GraphDB (optionnel)

**Pour transférer des données existantes** :

1. **Export depuis GraphDB source** :
   - Dans GraphDB, aller dans **"Export"**
   - Sélectionner le repository `wlconto`
   - Format : **"TriG"** ou **"N-Quads"** (pour conserver les named graphs)
   - Télécharger le fichier (ex: `wlconto_export.trig`)

2. **Import dans GraphDB destination** :
   - Créer le repository `wlconto` (voir Étape 2)
   - Aller dans **"Import"** > **"RDF"**
   - Uploader `wlconto_export.trig`
   - Cliquer sur **"Import"**

## Prérequis

- Python 3.8+
- GraphDB 10.0+
- Node.js 18+ (pour le frontend)

## Installation

1. Cloner le dépôt :
```bash
git clone [URL_DU_REPO]
cd Plateforme
```

2. Installer les dépendances backend :
```bash
cd Backend
python -m venv venv
source venv/bin/activate  # ou "venv\Scripts\activate" sous Windows
pip install -r requirements.txt
```

3. Installer les dépendances frontend :
```bash
cd ../Frontend
npm install
```

4. Configuration :
- Créer un fichier `.env` dans le dossier Backend :
```
GRAPHDB_URL=http://localhost:7200
GRAPHDB_REPO=WLCONTO
```

## Structure du Projet

```
Plateforme/
├── Backend/
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── app.py                    # Application Flask principale
│   ├── sparql_client.py          # Client SPARQL pour GraphDB
│   ├── uniformat_importer.py     # Utilitaire d'import Uniformat
│   ├── requirements.txt          # Dépendances Python
│   └── .env                      # Configuration (à créer)
├── Frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   └── main.css         # Styles principaux
│   │   └── js/
│   │       ├── main.js          # Application JavaScript principale
│   │       └── components/      # Composants réutilisables
│   ├── index.html               # Interface principale unique
│   └── package.json             # Métadonnées frontend
├── Ontology/
│   └── cgontologie1.ttl         # Ontologie WLCONTO
├── venv/                        # Environnement virtuel Python
└── README.md
```

## Démarrage

1. Démarrer GraphDB et créer un repository nommé "WLCONTO"

2. Importer l'ontologie :
- Ouvrir l'interface GraphDB
- Sélectionner le repository "WLCONTO"
- Importer le fichier `Ontology/cgontologie1.ttl`

3. Démarrer le backend :
```bash
cd Backend
source ../venv/bin/activate  # Activer l'environnement virtuel
python app.py
```

4. Ouvrir l'application :
- Naviguer vers `http://localhost:8000`
- L'interface unique contient tous les outils nécessaires

## Gestion du Serveur

### Démarrage du Serveur
Le serveur peut être démarré de deux manières :
```bash
# Méthode 1 : Depuis la racine du projet
python app.py

# Méthode 2 : Depuis le dossier Backend
cd Backend
python -m flask run
```

### Arrêt du Serveur
Pour arrêter le serveur, vous pouvez :

1. Si le serveur est en premier plan :
   - Appuyer sur `Ctrl+C` dans le terminal

2. Si le serveur est en arrière-plan ou bloqué :
```bash
# Trouver le processus utilisant le port 8000
lsof -i :8000

# Arrêter le processus (remplacer $PID par l'ID du processus)
kill $PID

# Ou forcer l'arrêt si nécessaire
kill -9 $PID
```

3. Sur macOS, vous pouvez aussi utiliser l'Activity Monitor :
   - Ouvrir Activity Monitor
   - Rechercher "python" ou "flask"
   - Sélectionner le processus
   - Cliquer sur le bouton "⬛" (Stop) dans la barre d'outils

### Vérification du Statut
Pour vérifier si le serveur est en cours d'exécution :
```bash
# Vérifier si le port 8000 est utilisé
lsof -i :8000

# Ou avec netstat
netstat -an | grep 8000
```

## API Backend

### Routes IFC

- `POST /ifc/upload` : Upload d'un fichier IFC
- `GET /ifc/elements` : Liste des éléments IFC
- `GET /ifc/element/<guid>` : Détails d'un élément
- `POST /ifc/reset` : Réinitialisation des éléments

### Routes Coûts

- `POST /cost/update` : Mise à jour d'un coût
- `GET /cost/element/<guid>` : Coûts d'un élément
- `POST /cost/upload-excel` : Import des coûts Excel
- `GET /cost/summary` : Résumé des coûts
- `GET /cost/by-year` : Coûts par année

### Routes Durées de Vie

- `POST /lifespan/project` : Définition durée projet
- `GET /lifespan/project` : Lecture durée projet
- `POST /lifespan/element/<guid>` : Définition durée élément
- `POST /lifespan/upload-excel` : Import des durées de vie
- `GET /lifespan/elements` : Liste des durées de vie
- `POST /lifespan/autofill` : Auto-remplissage

## Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## License

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails. 
