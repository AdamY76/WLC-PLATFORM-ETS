# 🐳 Démarrage Ultra-Rapide avec Docker

## ⚡ 3 Commandes, C'est Tout !

### **Windows / macOS / Linux**

```bash
# 1. Cloner le projet
git clone https://github.com/AdamY76/WLC-PLATFORM-ETS.git
cd WLC-PLATFORM-ETS

# 2. Démarrer avec Docker
docker-compose up -d

# 3. Ouvrir l'application
# Attendre 30 secondes, puis ouvrir: http://localhost:8000
```

**C'EST TOUT !** ✨

---

## 🎯 Qu'est-ce qui se passe automatiquement ?

1. **GraphDB** démarre sur `http://localhost:7200`
2. **Repository `wlconto`** créé automatiquement
3. **Ontologies** importées automatiquement (cgontologie1.ttl, ontology.ttl, stakeholder_mapping_clean.ttl)
4. **Backend Flask** démarre sur `http://localhost:8000`
5. **Frontend** servi automatiquement

**Pas besoin de** :
- ❌ Installer Python
- ❌ Créer un environnement virtuel
- ❌ Installer GraphDB manuellement
- ❌ Créer le repository manuellement
- ❌ Importer les ontologies manuellement

---

## 📋 Pré-requis (Installation Une Fois)

### **Windows**

1. **Installer Docker Desktop** : https://www.docker.com/products/docker-desktop/
   - Télécharger et installer
   - Redémarrer Windows si demandé
   - Lancer Docker Desktop (icône baleine)

### **macOS**

1. **Installer Docker Desktop** : https://www.docker.com/products/docker-desktop/
   - Télécharger le .dmg
   - Glisser dans Applications
   - Lancer Docker Desktop

### **Linux**

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Déconnexion/reconnexion nécessaire

# Installer docker-compose
sudo apt-get install docker-compose-plugin
```

---

## 🚀 Utilisation

### **Démarrer la plateforme**

```bash
docker-compose up -d
```

**Attendre 30-60 secondes** que tout soit prêt, puis :

- **Interface Web** : http://localhost:8000
- **GraphDB** : http://localhost:7200

### **Arrêter la plateforme**

```bash
docker-compose down
```

### **Voir les logs**

```bash
# Logs de tous les services
docker-compose logs

# Logs du backend seulement
docker-compose logs backend

# Logs de GraphDB seulement
docker-compose logs graphdb

# Suivre les logs en temps réel
docker-compose logs -f
```

### **Redémarrer (sans tout reconstruire)**

```bash
docker-compose restart
```

### **Tout supprimer (y compris les données)**

```bash
docker-compose down -v
```

⚠️ **Attention** : Cela supprime aussi les données GraphDB !

---

## 🛠️ Développement

### **Modifier le code**

1. Modifier les fichiers dans `Backend/` ou `Frontend/`
2. Redémarrer les conteneurs :

```bash
docker-compose restart backend
```

### **Reconstruire après changement de dépendances**

```bash
docker-compose up -d --build
```

### **Accéder au conteneur backend**

```bash
docker exec -it wlc-backend /bin/bash
```

### **Accéder à GraphDB via interface**

```bash
# Ouvrir http://localhost:7200
# Repository: wlconto (déjà créé et rempli)
```

---

## 🐛 Troubleshooting

### **Port 7200 ou 8000 déjà utilisé**

Modifier `docker-compose.yml` :

```yaml
services:
  graphdb:
    ports:
      - "7201:7200"  # Changer 7200 → 7201
  
  backend:
    ports:
      - "8001:8000"  # Changer 8000 → 8001
```

### **GraphDB ne démarre pas (Windows)**

1. Vérifier que Docker Desktop est lancé
2. Dans Docker Desktop → Settings → Resources → augmenter RAM à 4GB minimum

### **"Repository wlconto not found"**

Attendre 1-2 minutes, le script d'initialisation est en cours.

Vérifier avec :
```bash
docker-compose logs graphdb-init
```

Si erreur, réinitialiser :
```bash
docker-compose down -v
docker-compose up -d
```

### **Ontologies pas importées**

Vérifier les logs :
```bash
docker-compose logs graphdb-init
```

Réimporter manuellement :
```bash
docker-compose restart graphdb-init
```

### **Badge "Déconnecté" dans l'interface**

1. Vérifier que GraphDB est prêt : http://localhost:7200
2. Attendre 1 minute
3. Rafraîchir la page

---

## 📊 Vérification du Démarrage

### **1. Vérifier que tout tourne**

```bash
docker-compose ps
```

Doit afficher :
```
NAME            STATUS          PORTS
wlc-backend     Up              0.0.0.0:8000->8000/tcp
wlc-graphdb     Up (healthy)    0.0.0.0:7200->7200/tcp
```

### **2. Tester GraphDB**

```bash
curl http://localhost:7200/rest/repositories
```

Doit retourner une liste avec `wlconto`.

### **3. Tester Backend Flask**

```bash
curl http://localhost:8000/ping
```

Doit retourner `{"status": "OK"}`.

### **4. Tester Interface Web**

Ouvrir http://localhost:8000

Badge vert **"Connecté"** doit apparaître.

---

## 🎓 Commandes Docker Utiles

```bash
# Voir tous les conteneurs
docker ps

# Arrêter un conteneur spécifique
docker stop wlc-backend

# Démarrer un conteneur spécifique
docker start wlc-backend

# Voir l'utilisation des ressources
docker stats

# Nettoyer tous les conteneurs arrêtés
docker system prune

# Voir les volumes
docker volume ls

# Supprimer volume GraphDB (⚠️ perte de données)
docker volume rm wlc-platform-ets_graphdb-data
```

---

## 🌐 Accès Réseau Local (Autres Ordinateurs)

Pour accéder depuis un autre PC sur le réseau :

1. **Trouver l'IP de la machine hôte** :
   ```bash
   # Windows
   ipconfig
   
   # macOS/Linux
   ifconfig
   ```

2. **Ouvrir depuis un autre PC** :
   ```
   http://192.168.x.x:8000  (remplacer par l'IP trouvée)
   ```

---

## ✅ Avantages Docker

| **Sans Docker** | **Avec Docker** |
|-----------------|-----------------|
| Installer Python 3.8+ | ❌ Pas besoin |
| Créer venv | ❌ Pas besoin |
| `pip install -r requirements.txt` | ❌ Pas besoin |
| Installer GraphDB | ❌ Pas besoin |
| Créer repository manuellement | ✅ Automatique |
| Importer ontologies manuellement | ✅ Automatique |
| Configuration OS-spécifique | ✅ Marche partout |
| Conflits de versions | ✅ Isolé |
| **Temps d'installation** : 30+ min | **Temps** : 5 min |

---

## 🚀 Pour les Développeurs

### **Structure des Conteneurs**

```
┌─────────────────────────────────────────┐
│         docker-compose.yml              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐   ┌──────────────┐   │
│  │   graphdb    │   │   backend    │   │
│  │  (port 7200) │◄──│  (port 8000) │   │
│  └──────────────┘   └──────────────┘   │
│         ▲                               │
│         │                               │
│  ┌──────────────┐                       │
│  │ graphdb-init │ (one-shot)            │
│  │  (import)    │                       │
│  └──────────────┘                       │
│                                         │
└─────────────────────────────────────────┘
```

### **Personnaliser l'Image**

Modifier `Dockerfile` puis reconstruire :
```bash
docker-compose build
docker-compose up -d
```

---

## 📞 Support

**Problème ?** Créer une issue sur GitHub avec :
```bash
docker-compose logs > logs.txt
```

**Tout marche !** ⭐ Star le projet ! 🎉

