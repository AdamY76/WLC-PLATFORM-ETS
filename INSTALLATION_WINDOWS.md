# 🪟 Installation sur Windows (Guide Simplifié)

## **Solution Conda - La Plus Fiable pour Windows**

ifcopenshell est compliqué à installer sur Windows avec pip. **Conda est LA solution** qui marche à tous les coups.

---

## 📋 Installation en 5 Minutes

### **Étape 1 : Installer Miniconda** (une seule fois)

1. **Télécharger Miniconda** :
   - Aller sur : https://docs.conda.io/en/latest/miniconda.html
   - Cliquer sur **"Miniconda3 Windows 64-bit"**
   - Télécharger `Miniconda3-latest-Windows-x86_64.exe`

2. **Installer** :
   - Double-cliquer sur le fichier téléchargé
   - **Cocher** : "Add Miniconda3 to my PATH environment variable" (recommandé)
   - Cliquer **"Install"**
   - Attendre 2-3 minutes
   - Cliquer **"Finish"**

---

### **Étape 2 : Cloner le Projet**

Ouvrir **PowerShell** ou **CMD** et taper :

```bash
cd C:\Users\VotreNom\Documents
git clone https://github.com/AdamY76/WLC-PLATFORM-ETS.git
cd WLC-PLATFORM-ETS
```

*(Si git n'est pas installé : https://git-scm.com/download/win)*

---

### **Étape 3 : Créer l'Environnement Conda**

Ouvrir **"Anaconda Prompt"** (chercher dans le menu Démarrer) et taper :

```bash
# Aller dans le dossier du projet
cd C:\Users\VotreNom\Documents\WLC-PLATFORM-ETS

# Créer environnement avec Python 3.11
conda create -n wlc python=3.11 -y

# Activer l'environnement
conda activate wlc
```

Votre invite de commande devrait maintenant commencer par `(wlc)` ✅

---

### **Étape 4 : Installer les Dépendances**

**Toujours dans Anaconda Prompt** avec `(wlc)` visible :

```bash
# Installer ifcopenshell via conda
conda install -c conda-forge ifcopenshell -y

# Installer les autres dépendances
pip install -r Backend\requirements.txt
```

Attendre 2-3 minutes. ✅

---

### **Étape 5 : Installer et Configurer GraphDB**

1. **Télécharger GraphDB** :
   - https://www.ontotext.com/products/graphdb/
   - Choisir **GraphDB Free**
   - Télécharger la version Windows

2. **Installer GraphDB** :
   - Exécuter le fichier téléchargé
   - Suivre l'assistant d'installation

3. **Lancer GraphDB** :
   - Ouvrir **GraphDB Desktop** depuis le menu Démarrer
   - Attendre que ça démarre (30 secondes)

4. **Créer le Repository** :
   - Dans GraphDB, cliquer **"Setup"** → **"Repositories"**
   - Cliquer **"Create new repository"**
   - **Repository ID** : `wlconto`
   - **Ruleset** : OWL-Horst (optimized)
   - Cliquer **"Create"**

5. **Importer les Ontologies** :
   - Cliquer **"Import"** → **"RDF"**
   - **Upload RDF files**
   - Sélectionner les fichiers dans `Ontology/` :
     - `cgontologie1.ttl`
     - `ontology.ttl`
     - `stakeholder_mapping_clean.ttl`
   - Pour chaque fichier, mettre **Base URI** : `http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#`
   - Cliquer **"Import"**

---

### **Étape 6 : Lancer l'Application**

**Dans Anaconda Prompt** (avec `(wlc)` visible) :

```bash
cd Backend
python app.py
```

Tu devrais voir :
```
* Running on http://0.0.0.0:8000
```

✅ **Ouvrir le navigateur** : http://localhost:8000

---

## 🔄 Utilisation Quotidienne

### **Pour relancer l'application plus tard** :

```bash
# 1. Ouvrir "Anaconda Prompt"

# 2. Activer l'environnement
conda activate wlc

# 3. Aller dans le dossier Backend
cd C:\Users\VotreNom\Documents\WLC-PLATFORM-ETS\Backend

# 4. Lancer
python app.py

# 5. Ouvrir navigateur : http://localhost:8000
```

---

## 🆘 Dépannage

### **"conda: command not found"**

Miniconda pas dans le PATH. Solution :
1. Chercher **"Anaconda Prompt"** dans le menu Démarrer
2. **Utiliser Anaconda Prompt** au lieu de PowerShell/CMD

### **"Repository wlconto not found"**

GraphDB pas lancé ou repository pas créé :
1. Lancer **GraphDB Desktop**
2. Vérifier que repository `wlconto` existe
3. Importer les ontologies (étape 5)

### **Badge "Déconnecté" dans l'interface**

GraphDB pas accessible :
1. Vérifier que GraphDB Desktop est lancé
2. Ouvrir http://localhost:7200 pour vérifier
3. Rafraîchir la page de l'app

### **"ModuleNotFoundError: No module named 'ifcopenshell'"**

Environnement conda pas activé :
1. Ouvrir **Anaconda Prompt** (pas PowerShell)
2. Taper `conda activate wlc`
3. Vérifier que `(wlc)` apparaît au début de la ligne

---

## ✅ Checklist Rapide

**Avant de lancer l'app, vérifier** :

- [ ] Miniconda installé
- [ ] Environnement `wlc` créé (`conda create -n wlc python=3.11`)
- [ ] Environnement activé (voir `(wlc)` dans Anaconda Prompt)
- [ ] ifcopenshell installé (`conda install -c conda-forge ifcopenshell`)
- [ ] Autres dépendances installées (`pip install -r Backend\requirements.txt`)
- [ ] GraphDB Desktop lancé
- [ ] Repository `wlconto` créé et rempli
- [ ] Lancement depuis Anaconda Prompt avec `(wlc)` actif

**Si tout est coché → ça va marcher !** ✅

---

## 🎯 Pourquoi Conda ?

| **Méthode** | **Windows** | **Succès** |
|-------------|-------------|-----------|
| `pip install ifcopenshell` | ❌ Ne marche pas | 10% |
| Wheel GitHub manuel | ⚠️ Compliqué | 50% |
| **Conda** | ✅ **Simple** | **95%** |

**Conda gère automatiquement** :
- Les binaires compilés C++
- Les dépendances système (OpenCascade, etc.)
- La compatibilité Python/Windows

---

## 📞 Besoin d'Aide ?

**Problème persistant ?**

1. Vérifier les logs dans Anaconda Prompt
2. S'assurer que `(wlc)` est visible avant chaque commande
3. Relancer GraphDB Desktop
4. Créer une issue sur GitHub avec :
   - Version Windows (Win 10/11)
   - Version Python (`python --version`)
   - Message d'erreur complet

---

## 🎉 C'est Tout !

**Une fois configuré, c'est simple** :

```bash
# Anaconda Prompt
conda activate wlc
cd WLC-PLATFORM-ETS\Backend
python app.py
```

**Puis ouvrir** : http://localhost:8000

**Bon courage ! 🚀**

