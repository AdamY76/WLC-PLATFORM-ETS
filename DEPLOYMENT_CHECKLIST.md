# ✅ Checklist de Déploiement - Plateforme WLC

## 📋 Avant de commencer

- [ ] Ordinateur avec au minimum 4 GB RAM
- [ ] Connexion Internet (pour télécharger GraphDB et dépendances)
- [ ] Droits administrateur sur l'ordinateur

---

## 🔧 Installation des Composants

### GraphDB
- [ ] GraphDB téléchargé depuis [ontotext.com](https://www.ontotext.com/products/graphdb/)
- [ ] GraphDB installé
- [ ] GraphDB démarré (accessible sur `http://localhost:7200`)
- [ ] Repository `wlconto` créé avec ruleset **OWL-Horst**

### Python
- [ ] Python 3.8+ installé
- [ ] Version vérifiée avec `python --version`

### Fichiers du Projet
- [ ] Dossier `Plateforme/` copié sur le nouvel ordinateur
- [ ] Structure des dossiers intacte (Backend/, Frontend/, Ontology/)

---

## 📚 Import des Ontologies dans GraphDB

**Repository sélectionné** : `wlconto` ✓

- [ ] **1. WLCONTO.ttl** importé
  - Base URI: `http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#`
  
- [ ] **2. stakeholder_mapping_clean.ttl** importé
  - Base URI: `http://www.semanticweb.org/adamy/ontologies/2025/WLCPO#`

- [ ] **3. Ontologie End-of-Life** importée (si disponible)
  - Base URI: `http://www.w3id.org/dpp/EoL#`
  
- [ ] **4. Module d'alignement DPP** créé et importé :
  ```turtle
  @prefix wlcpo: <http://www.semanticweb.org/adamy/ontologies/2025/WLCPO#> .
  @prefix dpp: <http://www.semanticweb.org/adamy/ontologies/2025/DPP#> .
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  
  wlcpo:Asset rdfs:subClassOf dpp:Product .
  ```

---

## 🐍 Configuration de l'Environnement Python

```bash
cd Plateforme/Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

- [ ] Environnement virtuel créé dans `Backend/venv/`
- [ ] Environnement virtuel activé (invite de commande commence par `(venv)`)
- [ ] Toutes les dépendances installées sans erreur
- [ ] `ifcopenshell` installé correctement

**Si erreur avec ifcopenshell** :
```bash
pip install --force-reinstall ifcopenshell==0.8.2
```

---

## ⚙️ Configuration de l'Application

- [ ] Fichier `Backend/config/config.py` vérifié :
  - `GRAPHDB_URL = "http://localhost:7200"` ✓
  - `GRAPHDB_REPO = "wlconto"` ✓

- [ ] Dossier `Backend/uploads/` existe (ou sera créé automatiquement)

---

## 🚀 Démarrage et Tests

### 1. Démarrer GraphDB
- [ ] GraphDB accessible sur `http://localhost:7200`
- [ ] Repository `wlconto` sélectionné dans l'interface

### 2. Démarrer le serveur Flask

```bash
cd Backend
python app.py
```

- [ ] Serveur démarre sans erreur
- [ ] Message `Running on http://0.0.0.0:8000` visible
- [ ] Aucun message d'erreur dans le terminal

### 3. Tester l'Interface Web

**Ouvrir** : `http://localhost:8000`

- [ ] Page s'affiche correctement
- [ ] Badge **"Connecté"** (vert) visible en haut à droite
- [ ] Onglets visibles : Analyse WLC, Gestion IFC, Durées de vie, etc.

### 4. Test Fonctionnel

**Test IFC** :
- [ ] Onglet "Gestion IFC" accessible
- [ ] Possibilité d'uploader un fichier `.ifc`
- [ ] Bouton "Parser vers ontologie" fonctionne
- [ ] Éléments s'affichent dans le tableau

**Test Fin de Vie** :
- [ ] Onglet "Gestion Fin de Vie" accessible
- [ ] Éléments s'affichent avec descriptions Uniformat
- [ ] Dropdowns stratégies (Refuse, Recycle, etc.) fonctionnent
- [ ] Modification d'une stratégie enregistrée dans GraphDB

**Test GraphDB** :
- [ ] Aller dans GraphDB > "Explore" > "Visual graph"
- [ ] Rechercher un élément (ex: un GUID)
- [ ] Visualiser les relations RDF

---

## 🔍 Troubleshooting

### ❌ Badge "Déconnecté" (rouge)
**Solutions** :
- [ ] Vérifier que GraphDB est démarré
- [ ] Vérifier URL dans `config.py`: `http://localhost:7200`
- [ ] Vérifier nom repository: `wlconto`
- [ ] Tester manuellement : `http://localhost:7200/repositories/wlconto`

### ❌ Port 8000 déjà utilisé
**Solutions** :
```bash
# Trouver le processus
lsof -i :8000
# Tuer le processus (remplacer [PID])
kill -9 [PID]
```

### ❌ Erreur `ifcopenshell` au démarrage
**Solutions** :
- [ ] Réinstaller : `pip install --force-reinstall ifcopenshell==0.8.2`
- [ ] Sur Windows, télécharger depuis [GitHub releases](https://github.com/IfcOpenShell/IfcOpenShell/releases)

### ❌ Onglet "Fin de Vie" vide
**Solutions** :
- [ ] Vérifier que l'ontologie EoL est importée dans GraphDB
- [ ] Vérifier les logs du terminal backend
- [ ] Tester l'endpoint : `http://localhost:8000/get-eol-management-data`

### ❌ Erreur SPARQL "MALFORMED QUERY"
**Solutions** :
- [ ] Vérifier que tous les prefixes sont définis dans les requêtes
- [ ] Vérifier que les URIs sont correctement encodées
- [ ] Consulter les logs GraphDB : GraphDB > "Monitoring" > "Query log"

---

## 📦 Export/Import de Données (Optionnel)

### Pour transférer des données d'un GraphDB à un autre

**Export** :
- [ ] Dans GraphDB source : "Export" > Format "TriG"
- [ ] Fichier téléchargé (ex: `wlconto_export.trig`)

**Import** :
- [ ] Repository `wlconto` créé sur nouveau GraphDB
- [ ] "Import" > "RDF" > Upload `wlconto_export.trig`
- [ ] Import terminé sans erreur

---

## ✅ Installation Terminée !

### Dernières vérifications

- [ ] Application accessible sur `http://localhost:8000`
- [ ] GraphDB accessible sur `http://localhost:7200`
- [ ] Badge "Connecté" vert
- [ ] Tous les onglets fonctionnels
- [ ] Tests IFC et EOL passés

### Pour arrêter l'application

```bash
# Arrêter Flask
Ctrl + C (dans le terminal)

# Arrêter GraphDB (si nécessaire)
# Fermer la fenêtre GraphDB ou utiliser le script d'arrêt
```

---

## 📞 Support

**Problèmes persistants ?**
- Consulter le fichier `README.md` section "Troubleshooting"
- Vérifier les logs Flask dans le terminal
- Vérifier les logs GraphDB dans l'interface

**Logs utiles** :
- Backend Flask : visible dans le terminal
- GraphDB : `Monitoring` > `Query log` et `System log`

---

## 🎯 Résumé Rapide (TL;DR)

```bash
# 1. Installer GraphDB + créer repository "wlconto"
# 2. Importer ontologies dans GraphDB
# 3. Copier dossier Plateforme/
cd Plateforme/Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# 4. Ouvrir http://localhost:8000
```

**✅ C'est tout !**

