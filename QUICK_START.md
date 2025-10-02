# 🚀 Quick Start - Plateforme WLC

## Pour l'utilisateur qui veut juste démarrer rapidement

### 📋 Prérequis (à installer une seule fois)
1. **GraphDB** : [Télécharger ici](https://www.ontotext.com/products/graphdb/)
2. **Python 3.8+** : [Télécharger ici](https://www.python.org/downloads/)

---

## 🔥 Démarrage en 4 étapes

### 1️⃣ Démarrer GraphDB

```bash
# Sur macOS/Linux
cd /path/to/graphdb/bin
./graphdb

# Sur Windows  
graphdb.bat
```

**Vérifier** : Ouvrir `http://localhost:7200`

### 2️⃣ Créer le repository (première fois seulement)

Dans GraphDB :
1. **Setup** → **Repositories** → **Create new repository**
2. **Repository ID** : `wlconto`
3. **Ruleset** : OWL-Horst (optimized)
4. Cliquer **Create**

### 3️⃣ Importer les ontologies (première fois seulement)

Dans GraphDB, onglet **Import** :
- Importer `Ontology/WLCONTO.ttl`
- Importer `Ontology/stakeholder_mapping_clean.ttl`

### 4️⃣ Démarrer la plateforme

```bash
cd Plateforme/Backend

# Première fois : créer environnement
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# À chaque démarrage
source venv/bin/activate  # Windows: venv\Scripts\activate
python app.py
```

**✅ C'est prêt !** Ouvrir : `http://localhost:8000`

---

## 🔄 Démarrage quotidien (après installation)

```bash
# 1. Démarrer GraphDB
cd /path/to/graphdb/bin && ./graphdb

# 2. Démarrer la plateforme (nouveau terminal)
cd Plateforme/Backend
source venv/bin/activate
python app.py

# 3. Ouvrir navigateur : http://localhost:8000
```

---

## 🛑 Arrêt

```bash
# Arrêter Flask
Ctrl + C (dans le terminal Backend)

# Arrêter GraphDB (optionnel)
# Fermer la fenêtre ou Ctrl + C
```

---

## ❓ Problème ?

| **Symptôme** | **Solution** |
|--------------|-------------|
| Badge "Déconnecté" rouge | GraphDB pas démarré → voir étape 1 |
| Port 8000 occupé | `lsof -i :8000` puis `kill -9 [PID]` |
| Erreur au démarrage Python | Réinstaller : `pip install -r requirements.txt` |

**Aide détaillée** : Consulter `README.md` ou `DEPLOYMENT_CHECKLIST.md`

---

## 📦 Transférer sur un autre ordinateur

1. **Copier** le dossier `Plateforme/` complet
2. **Installer** GraphDB et Python sur le nouvel ordinateur
3. **Suivre** les étapes 1 à 4 ci-dessus

**Pour transférer les données GraphDB aussi** :
- Dans GraphDB source : **Export** → Format **TriG**
- Dans GraphDB destination : **Import** → Upload le fichier exporté

---

## 🎯 Commandes de Vérification

```bash
# Vérifier Python
python --version  # Doit être 3.8+

# Vérifier GraphDB
curl http://localhost:7200/rest/repositories

# Vérifier Flask
curl http://localhost:8000/ping

# Tester l'onglet EOL
curl http://localhost:8000/get-eol-management-data
```

---

**📧 Questions ?** Consulter `README.md` section complète.

