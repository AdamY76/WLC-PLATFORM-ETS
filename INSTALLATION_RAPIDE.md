# ⚡ Installation Rapide (5 Minutes)

## **LA Méthode qui Marche Partout**

### **Étape 1 : Installer Miniconda** (une fois)

**Windows** : https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
**Mac** : https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.pkg
**Linux** : https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

Double-clic pour installer (5 minutes).

---

### **Étape 2 : Ouvrir le Terminal**

- **Windows** : Chercher "Anaconda Prompt" dans le menu Démarrer
- **Mac/Linux** : Terminal normal

---

### **Étape 3 : 5 Commandes Magiques**

```bash
# 1. Clone le projet
git clone https://github.com/AdamY76/WLC-PLATFORM-ETS.git
cd WLC-PLATFORM-ETS

# 2. Crée environnement
conda create -n wlc python=3.11 -y

# 3. Active-le
conda activate wlc

# 4. Installe tout
conda install -c conda-forge ifcopenshell -y
pip install -r Backend/requirements.txt

# 5. Lance !
cd Backend
python app.py
```

**Ouvrir** : http://localhost:8000

---

## ✅ **C'est Tout !**

**Pour relancer plus tard** :

```bash
conda activate wlc
cd WLC-PLATFORM-ETS/Backend
python app.py
```

---

## 🔧 **GraphDB (Séparé)**

1. Télécharger : https://www.ontotext.com/products/graphdb/
2. Installer
3. Lancer GraphDB
4. Créer repository "wlconto"
5. Importer les fichiers de `Ontology/`

**Une fois fait, plus besoin d'y toucher.**

---

## ⚠️ Problème ?

**"conda: command not found"**
→ Utilise "Anaconda Prompt" (pas PowerShell/Terminal normal)

**Badge "Déconnecté" dans l'app**
→ GraphDB pas lancé

**C'est tout.**

