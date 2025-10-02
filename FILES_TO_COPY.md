# 📁 Fichiers Nécessaires pour le Déploiement

## ✅ Fichiers OBLIGATOIRES à copier

### Structure minimale (environ 50 MB sans venv)

```
Plateforme/
│
├── Backend/                          [OBLIGATOIRE]
│   ├── config/
│   │   ├── __init__.py              ✓ Obligatoire
│   │   └── config.py                ✓ Obligatoire (configuration GraphDB)
│   │
│   ├── app.py                       ✓ Obligatoire (serveur Flask principal)
│   ├── sparql_client.py             ✓ Obligatoire (client GraphDB)
│   ├── comparison_routes.py         ✓ Obligatoire (routes de comparaison WLC)
│   ├── requirements.txt             ✓ Obligatoire (dépendances Python)
│   │
│   └── uploads/                     □ Optionnel (créé automatiquement)
│
├── Frontend/                         [OBLIGATOIRE]
│   ├── assets/
│   │   ├── css/
│   │   │   └── main.css             ✓ Obligatoire (styles interface)
│   │   │
│   │   └── js/
│   │       ├── main.js              ✓ Obligatoire (logique frontend)
│   │       └── components/          □ Optionnel mais recommandé
│   │           ├── dataTable.js
│   │           ├── fileUpload.js
│   │           └── notifications.js
│   │
│   ├── index.html                   ✓ Obligatoire (page principale)
│   └── package.json                 □ Optionnel (métadonnées frontend)
│
├── Ontology/                         [RECOMMANDÉ]
│   ├── WLCONTO.ttl                  ✓ Obligatoire (ontologie principale)
│   ├── stakeholder_mapping_clean.ttl ✓ Obligatoire (mapping parties prenantes)
│   └── [autres .ttl]                 □ Si disponibles (EoL, DPP, etc.)
│
├── README.md                         □ Optionnel (documentation)
├── QUICK_START.md                    □ Optionnel (guide rapide)
├── DEPLOYMENT_CHECKLIST.md           □ Optionnel (checklist déploiement)
└── FILES_TO_COPY.md                  □ Optionnel (ce fichier)
```

---

## 🚫 Fichiers à NE PAS copier

### Automatiquement exclus si vous utilisez Git

```
Plateforme/
│
├── Backend/
│   ├── venv/                        ❌ NE PAS copier (recréer sur nouvelle machine)
│   ├── __pycache__/                 ❌ NE PAS copier (fichiers compilés Python)
│   ├── *.pyc                        ❌ NE PAS copier (bytecode Python)
│   ├── app.log                      ❌ NE PAS copier (logs)
│   ├── uploads/*.ifc                ❌ NE PAS copier (sauf si nécessaire)
│   ├── *.backup                     ❌ NE PAS copier (fichiers temporaires)
│   └── .env                         ⚠️  À adapter (configuration locale)
│
├── venv_py312/                      ❌ NE PAS copier
├── Backend_backup_*/                ❌ NE PAS copier (anciens backups)
├── dev-tools/                       ❌ NE PAS copier (outils de développement)
├── docs/historical/                 ❌ NE PAS copier (documentation historique)
│
├── *.ifc                            ⚠️  Selon besoin (fichiers IFC de test)
├── *.csv                            ⚠️  Selon besoin (données d'import)
├── *.xlsx                           ⚠️  Selon besoin (fichiers coûts/durées)
│
└── .git/                            □ Optionnel (historique Git)
```

---

## 📦 Méthodes de Copie

### Méthode 1 : Copie manuelle (USB, réseau)

**Créer une archive ZIP/TAR** :
```bash
# Depuis le dossier parent de Plateforme/
cd /chemin/vers/parent

# Créer archive (exclut venv et fichiers temporaires)
tar -czf plateforme_deploy.tar.gz \
  --exclude='Plateforme/Backend/venv' \
  --exclude='Plateforme/venv_py312' \
  --exclude='Plateforme/Backend/__pycache__' \
  --exclude='Plateforme/Backend/*.log' \
  --exclude='Plateforme/Backend_backup_*' \
  --exclude='Plateforme/dev-tools' \
  Plateforme/

# Taille attendue : environ 5-10 MB
```

**Décompresser sur nouveau PC** :
```bash
tar -xzf plateforme_deploy.tar.gz
cd Plateforme/Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Méthode 2 : Git (recommandé)

**Sur PC source** :
```bash
cd Plateforme
git init
git add Backend/ Frontend/ Ontology/ *.md
git commit -m "Initial deployment"
git remote add origin <URL_REPOSITORY>
git push origin main
```

**Sur PC destination** :
```bash
git clone <URL_REPOSITORY>
cd Plateforme/Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Méthode 3 : SCP (réseau local/distant)

```bash
# Copie complète (exclut venv)
scp -r \
  --exclude='venv' \
  --exclude='__pycache__' \
  Plateforme/ \
  utilisateur@192.168.1.X:/chemin/destination/
```

---

## 📊 Taille des Fichiers (approximatif)

| **Composant** | **Taille** | **Nécessité** |
|---------------|-----------|---------------|
| Backend/*.py (code) | ~500 KB | ✓ Obligatoire |
| Frontend/assets/ | ~200 KB | ✓ Obligatoire |
| Ontology/*.ttl | ~3 MB | ✓ Obligatoire |
| requirements.txt | ~1 KB | ✓ Obligatoire |
| Documentation (*.md) | ~50 KB | □ Optionnel |
| **Total minimal** | **~4 MB** | |
| | | |
| Backend/venv/ | ~300 MB | ❌ Recréer |
| Fichiers .ifc (tests) | Variable | ⚠️ Selon besoin |

---

## 🔐 Fichiers de Configuration à Adapter

### Backend/config/config.py

**Vérifier/Adapter** :
```python
GRAPHDB_URL = "http://localhost:7200"  # Adapter si GraphDB sur autre machine
GRAPHDB_REPO = "wlconto"               # Adapter si repository différent
```

### Backend/.env (optionnel)

**Si utilisé, adapter** :
```
FLASK_ENV=development
GRAPHDB_URL=http://localhost:7200
GRAPHDB_REPO=wlconto
SECRET_KEY=your_secret_key_here
```

---

## ✅ Checklist Rapide

**Avant de copier** :
- [ ] Identifier les fichiers obligatoires ci-dessus
- [ ] Exclure `venv/`, `__pycache__/`, `*.log`
- [ ] Inclure `Ontology/` (ontologies à importer dans GraphDB)

**Après copie** :
- [ ] Recréer environnement virtuel : `python -m venv venv`
- [ ] Installer dépendances : `pip install -r requirements.txt`
- [ ] Adapter `config.py` si nécessaire
- [ ] Importer ontologies dans GraphDB

**Test** :
- [ ] `python app.py` démarre sans erreur
- [ ] `http://localhost:8000` accessible
- [ ] Badge "Connecté" vert

---

## 🎯 Script de Copie Automatique

**Créer un script** `prepare_deployment.sh` :
```bash
#!/bin/bash
# Script de préparation pour déploiement

echo "🚀 Préparation du déploiement..."

# Créer dossier de déploiement
mkdir -p Plateforme_Deploy

# Copier fichiers essentiels
cp -r Backend/ Plateforme_Deploy/
cp -r Frontend/ Plateforme_Deploy/
cp -r Ontology/ Plateforme_Deploy/
cp *.md Plateforme_Deploy/ 2>/dev/null

# Nettoyer fichiers inutiles
cd Plateforme_Deploy
find . -name "venv" -type d -exec rm -rf {} + 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.log" -delete 2>/dev/null
rm -rf Backend_backup_* dev-tools/ 2>/dev/null

cd ..

# Créer archive
tar -czf plateforme_deploy_$(date +%Y%m%d).tar.gz Plateforme_Deploy/

echo "✅ Archive créée : plateforme_deploy_$(date +%Y%m%d).tar.gz"
echo "📦 Taille : $(du -h plateforme_deploy_*.tar.gz | cut -f1)"
```

**Utilisation** :
```bash
chmod +x prepare_deployment.sh
./prepare_deployment.sh
# → Génère plateforme_deploy_YYYYMMDD.tar.gz
```

---

## 📞 Support

**Doutes sur quels fichiers copier ?**
→ Copier **TOUT** sauf `venv/` et `__pycache__/`

**Erreur "module not found" au démarrage ?**
→ Recréer `venv` et réinstaller : `pip install -r requirements.txt`

**Badge "Déconnecté" après déploiement ?**
→ Vérifier `Backend/config/config.py` et GraphDB

