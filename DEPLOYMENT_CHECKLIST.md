Installation des Composants

### GraphDB
- [ ] GraphDB téléchargé depuis [ontotext.com](https://www.ontotext.com/products/graphdb/)
- [ ] Repository `wlconto` créé 
      
### Python
- [ ] Python 3.8+ installé


---

## Import des Ontologies dans GraphDB

**Repository sélectionné** : `wlconto` 

## Import des Ontologies dans GraphDB (dans le repository: wlconto)

- [ ] **cgontologie1.ttl** (ontologie du coût global wlconto)
- [ ] **ontology.ttl**  (ontologie IFC)
- [ ] **Mapping.ttl** (Alignement ifc-WLCONTO)
      
- [ ] **stakeholder_mapping_clean.ttl** (extension avec les parties prenantes)

- [ ] **6_EndOfLifeManagement_Module_Protege.ttl** (ontologie avec les scénarios de fin de vie)  
- [ ] **WLCPODPP.ttl** (Alignement de WLCPO avec Digital Product Passport)

- [ ] **uniformat.ttl** (ontologie uniformat)
- [ ] **uniformat_ifc_broad_alignment.ttl** (alignement uniformat - ifc)

---

## Configuration de l'Environnement Python

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


## Démarrage et Tests

### 1. Démarrer GraphDB
- [ ] GraphDB accessible sur `http://localhost:7200`
- [ ] Repository `wlconto` sélectionné dans l'interface

### 2. Démarrer le serveur Flask

```bash
cd Backend
python app.py
```

- [ ] Message `Running on http://0.0.0.0:8000` visible

### 3. Tester l'Interface Web

**Ouvrir** : `http://localhost:8000`


### 4. Test Fonctionnel

**Test IFC** :
- [ ] Onglet "Gestion IFC" accessible
- [ ] Possibilité d'uploader un fichier `.ifc`
- [ ] Bouton "Parser vers ontologie" 
- [ ] Éléments s'affichent dans le tableau

**Test Fin de Vie** :
- [ ] Onglet "Gestion Fin de Vie" accessible
- [ ] Éléments s'affichent avec descriptions Uniformat
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


### Pour arrêter l'application

```bash
# Arrêter Flask
Ctrl + C (dans le terminal)

# Arrêter GraphDB (si nécessaire)
# Fermer la fenêtre GraphDB ou utiliser le script d'arrêt
```

---

##  Résumé Rapide (TL;DR)

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

