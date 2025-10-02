# 📘 Résumé Complet du Déploiement - Plateforme WLC

## 🎯 Vue d'Ensemble

Cette plateforme permet de gérer le **coût global (WLC)** des projets de construction en s'appuyant sur :
- Une **ontologie RDF (WLCONTO)** hébergée dans **GraphDB**
- Un **backend Flask (Python)** pour l'API et la logique métier
- Un **frontend HTML/JS** pour l'interface utilisateur

---

## 📚 Documentation Disponible

| **Fichier** | **Contenu** | **Pour qui ?** |
|-------------|-------------|----------------|
| `QUICK_START.md` | Démarrage rapide en 4 étapes | 🔰 Débutants |
| `DEPLOYMENT_CHECKLIST.md` | Checklist détaillée avec cases à cocher | ✅ Installation complète |
| `FILES_TO_COPY.md` | Liste exacte des fichiers à copier | 📁 Migration/Copie |
| `README.md` | Documentation technique complète | 📖 Référence |
| `.gitignore` | Fichiers à exclure de Git | 🐙 Versioning |
| Ce fichier | Vue d'ensemble et résumé | 👀 Aperçu général |

---

## 🚀 Déploiement en 3 Niveaux

### Niveau 1 : Installation Locale (même ordinateur)

**Situation** : Vous avez déjà le code, GraphDB installé, et voulez démarrer.

```bash
# 1. Démarrer GraphDB
cd /path/to/graphdb/bin && ./graphdb

# 2. Activer venv et démarrer Flask
cd Plateforme/Backend
source venv/bin/activate
python app.py

# 3. Ouvrir http://localhost:8000
```

**📄 Consulter** : `QUICK_START.md`

---

### Niveau 2 : Nouveau PC (installation fraîche)

**Situation** : Vous copiez la plateforme sur un nouvel ordinateur.

**Étapes** :
1. Installer GraphDB + Python
2. Copier le dossier `Plateforme/`
3. Créer repository `wlconto` dans GraphDB
4. Importer ontologies (WLCONTO.ttl, etc.)
5. Créer environnement Python : `python -m venv venv`
6. Installer dépendances : `pip install -r requirements.txt`
7. Démarrer : `python app.py`

**📄 Consulter** : 
- `DEPLOYMENT_CHECKLIST.md` (checklist complète)
- `README.md` section "Guide de Déploiement"

---

### Niveau 3 : Production / Serveur Distant

**Situation** : Déploiement sur serveur web pour accès multi-utilisateurs.

**Étapes supplémentaires** :
1. Configurer GraphDB en mode serveur (pas Desktop)
2. Configurer firewall pour ports 7200 et 8000
3. Utiliser `gunicorn` au lieu de `python app.py` :
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```
4. Configurer reverse proxy (nginx/Apache)
5. Activer HTTPS avec Let's Encrypt
6. Mettre en place backup automatique GraphDB

**📄 Consulter** : `README.md` + documentation GraphDB officielle

---

## 🔧 Architecture Technique

```
┌─────────────────────────────────────────────────────────┐
│                    UTILISATEUR                          │
│                  (Navigateur Web)                       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FRONTEND (HTML/JS)                         │
│  • index.html                                           │
│  • main.js (logique client)                             │
│  • main.css (styles)                                    │
└────────────────────┬────────────────────────────────────┘
                     │ REST API
                     ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND (Flask/Python)                     │
│  • app.py (routes API)                                  │
│  • sparql_client.py (requêtes SPARQL)                   │
│  • comparison_routes.py (comparaisons WLC)              │
└────────────────────┬────────────────────────────────────┘
                     │ SPARQL HTTP
                     ▼
┌─────────────────────────────────────────────────────────┐
│              BASE DE CONNAISSANCES                      │
│                   (GraphDB)                             │
│  • Repository: wlconto                                  │
│  • Ontologies: WLCONTO, WLCPO, DPP, EoL                │
│  • Données: Éléments IFC, Coûts, Durées, Stratégies    │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Composants Principaux

### 1. GraphDB (Base de données RDF)
- **Rôle** : Stockage sémantique des données
- **Port** : 7200
- **Repository** : `wlconto`
- **Ontologies** :
  - `WLCONTO.ttl` : Ontologie principale (coûts, durées de vie)
  - `stakeholder_mapping_clean.ttl` : Parties prenantes
  - `6_EndOfLifeManagement_Module_Protege.ttl` : Gestion fin de vie
  - Modules d'alignement (DPP, etc.)

### 2. Backend Flask
- **Rôle** : API REST, logique métier
- **Port** : 8000
- **Fichiers clés** :
  - `app.py` : 4000+ lignes, toutes les routes
  - `sparql_client.py` : Interactions GraphDB
  - `comparison_routes.py` : Comparaisons WLC
- **Dépendances** : voir `requirements.txt`

### 3. Frontend HTML/JS
- **Rôle** : Interface utilisateur
- **Accès** : `http://localhost:8000`
- **Fichiers clés** :
  - `index.html` : Structure de l'interface
  - `assets/js/main.js` : Logique frontend (7000+ lignes)
  - `assets/css/main.css` : Styles

---

## 🎨 Fonctionnalités Principales

### Onglet 1 : Analyse WLC
- Visualisation des coûts par phase (Construction, Opération, Maintenance, Fin de vie)
- Graphiques interactifs (Chart.js)
- Calcul du coût global sur la durée du projet

### Onglet 2 : Gestion IFC
- Import de fichiers IFC (Industry Foundation Classes)
- Parsing avec `ifcopenshell`
- Extraction des propriétés Uniformat
- Stockage dans l'ontologie RDF

### Onglet 3 : Durées de Vie
- Import Excel des durées de vie
- Affectation automatique ou manuelle
- Calcul des occurrences de maintenance

### Onglet 4 : Taux d'Actualisation
- Import des taux d'actualisation
- Application dans les calculs WLC
- Visualisation par année

### Onglet 5 : Parties Prenantes
- Gestion des acteurs du projet
- Requêtes SPARQL personnalisées
- Visualisation des relations

### Onglet 6 : Gestion Fin de Vie ⭐ NOUVEAU
- **10 Stratégies R** : Refuse, Rethink, Reduce, Reuse, Repair, Refurbish, Remanufacture, Repurpose, Recycle, Recover
- **Colonnes** : Élément, Stratégie, Destination, Responsable, Coût
- **Affichage** : Description Uniformat au lieu du GUID
- **Ontologie** : Utilise les propriétés de `6_EndOfLifeManagement_Module_Protege.ttl`
  - `eol:hasType` → Stratégie
  - `eol:atPlace` → Destination
  - `eol:providesParticipantRole` → Responsable

---

## 🔑 Points Critiques pour le Déploiement

### ✅ À Faire Absolument

1. **GraphDB doit être démarré** avant Flask
2. **Repository `wlconto`** doit exister
3. **Ontologies importées** dans l'ordre correct
4. **Environnement virtuel Python** recréé sur chaque nouvelle machine
5. **Vérifier `config.py`** : URLs et noms de repository

### ❌ Erreurs Courantes

| **Erreur** | **Cause** | **Solution** |
|------------|-----------|--------------|
| Badge "Déconnecté" | GraphDB pas démarré | Démarrer GraphDB sur port 7200 |
| Port 8000 occupé | Flask déjà lancé | `lsof -i :8000` puis `kill -9 [PID]` |
| Module `ifcopenshell` | Pas installé | `pip install ifcopenshell==0.8.2` |
| Onglet EOL vide | Ontologie EoL manquante | Importer ontologie avec prefix `eol:` |
| SPARQL malformé | GUIDs avec espaces | Backend utilise `urllib.parse.quote()` |

---

## 📦 Fichiers à Copier (Résumé)

### ✅ OBLIGATOIRES (4-5 MB)
```
Backend/app.py
Backend/sparql_client.py
Backend/comparison_routes.py
Backend/config/config.py
Backend/requirements.txt
Frontend/index.html
Frontend/assets/js/main.js
Frontend/assets/css/main.css
Ontology/WLCONTO.ttl
Ontology/stakeholder_mapping_clean.ttl
```

### ❌ NE PAS COPIER
```
Backend/venv/               (recréer)
__pycache__/                (fichiers compilés)
*.log                       (logs)
Backend_backup_*/           (backups)
dev-tools/                  (scripts de dev)
```

---

## 🧪 Tests de Validation

### Test 1 : Connexion GraphDB
```bash
curl http://localhost:7200/rest/repositories
# Doit retourner la liste avec "wlconto"
```

### Test 2 : Backend Flask
```bash
curl http://localhost:8000/ping
# Doit retourner {"status": "OK"}
```

### Test 3 : Données EOL
```bash
curl http://localhost:8000/get-eol-management-data | jq
# Doit retourner un JSON avec les éléments
```

### Test 4 : Interface Web
- Ouvrir `http://localhost:8000`
- Badge "Connecté" vert ✓
- Onglets visibles ✓
- Import IFC fonctionne ✓
- Onglet EOL affiche éléments ✓

---

## 🔄 Workflow Complet (exemple)

```
1. Utilisateur upload fichier IFC
   ↓
2. Backend parse IFC avec ifcopenshell
   ↓
3. Backend extrait propriétés (GUID, Uniformat, matériau, etc.)
   ↓
4. Backend génère requêtes SPARQL INSERT
   ↓
5. GraphDB stocke les données RDF
   ↓
6. Utilisateur importe coûts (Excel)
   ↓
7. Backend associe coûts aux éléments via SPARQL
   ↓
8. Utilisateur définit stratégies fin de vie
   ↓
9. Backend stocke via propriétés eol:hasType, eol:atPlace, etc.
   ↓
10. Utilisateur lance calcul WLC
    ↓
11. Backend requête GraphDB (SPARQL SELECT)
    ↓
12. Backend calcule coûts sur durée projet
    ↓
13. Frontend affiche graphiques et tableaux
```

---

## 📞 Support et Dépannage

### Ressources Utiles
- **GraphDB Docs** : [https://graphdb.ontotext.com/documentation/](https://graphdb.ontotext.com/documentation/)
- **Flask Docs** : [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
- **SPARQL Tutorial** : [https://www.w3.org/TR/sparql11-query/](https://www.w3.org/TR/sparql11-query/)
- **IfcOpenShell** : [https://ifcopenshell.org/](https://ifcopenshell.org/)

### Logs à Consulter
1. **Terminal Flask** : Erreurs backend, requêtes SPARQL
2. **GraphDB Monitoring** : Requêtes SPARQL, performances
3. **Console Navigateur (F12)** : Erreurs JavaScript, requêtes API

### Commandes de Debug
```bash
# Vérifier processus
lsof -i :7200  # GraphDB
lsof -i :8000  # Flask

# Tester GraphDB
curl http://localhost:7200/rest/repositories/wlconto

# Tester Flask endpoints
curl http://localhost:8000/ping
curl http://localhost:8000/get-ifc-elements
curl http://localhost:8000/get-end-of-life-strategies

# Logs Flask en temps réel
tail -f Backend/app.log  # Si logging activé
```

---

## 🎓 Pour Aller Plus Loin

### Personnalisation
- Ajouter de nouvelles routes dans `app.py`
- Créer de nouveaux onglets dans `index.html`
- Étendre l'ontologie WLCONTO
- Ajouter de nouvelles propriétés EOL

### Optimisation
- Activer le cache SPARQL dans GraphDB
- Paginer les résultats pour grandes données
- Utiliser connexions persistantes HTTP
- Indexer les propriétés fréquemment requêtées

### Sécurité
- Ajouter authentification utilisateur (Flask-Login)
- Activer HTTPS avec certificat SSL
- Configurer CORS correctement pour production
- Sauvegardes régulières GraphDB

---

## ✅ Checklist Finale

**Avant de dire "C'est déployé !" :**

- [ ] GraphDB installé et démarré
- [ ] Repository `wlconto` créé avec OWL-Horst
- [ ] Ontologies WLCONTO, stakeholder, EoL importées
- [ ] Python 3.8+ installé
- [ ] Environnement virtuel créé
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] `config.py` vérifié et correct
- [ ] Flask démarre sans erreur (`python app.py`)
- [ ] Interface accessible (`http://localhost:8000`)
- [ ] Badge "Connecté" vert
- [ ] Import IFC fonctionne
- [ ] Onglet EOL affiche éléments
- [ ] Sélection stratégie EOL enregistrée dans GraphDB
- [ ] GraphDB visualisation montre les relations RDF

**🎉 Si toutes les cases sont cochées : DÉPLOIEMENT RÉUSSI !**

---

**📧 Questions ?** Consulter les autres fichiers de documentation dans le projet.

