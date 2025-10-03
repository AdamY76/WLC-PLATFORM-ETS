# Plateforme de Gestion du Coût Global (WLC)

Plateforme web permettant d'analyser et gérer le coût global (Whole Life Cost) des projets de construction basés sur des modèles BIM (fichiers IFC). Le système utilise une base de connaissances sémantique (ontologie RDF) hébergée dans GraphDB pour enrichir et analyser les données.

---

## Fonctionnalités Principales

**Analyse de Cycle de Vie**
- Import et analyse de fichiers IFC (modèles BIM)
- Calcul des coûts par phase : Construction, Opération, Maintenance, Fin de vie
- Gestion des durées de vie des éléments de construction
- Visualisation des coûts répartis dans le temps

**Édition Interactive**
- Modification directe des coûts par phase dans le tableau
- Modification des durées de vie et matériaux des éléments
- Synchronisation automatique avec l'ontologie RDF
- Feedback visuel en temps réel

**Intégration Ontologique**
- Base de connaissances RDF avec GraphDB
- Requêtes SPARQL pour l'extraction et l'analyse de données
- Mise à jour automatique des instances RDF lors des modifications

---

## Prérequis Système

- **Python 3.11 ou supérieur** (via Miniconda recommandé)
- **GraphDB 10.0+** (version Free suffit)
- **Navigateur web moderne** (Chrome, Firefox, Safari, Edge)
- **4 GB RAM minimum** (8 GB recommandé)

---

## Installation

Consultez le guide d'installation détaillé : [INSTALLATION.md](INSTALLATION.md)

Le guide couvre :
- Installation sur Windows
- Installation sur Mac
- Configuration de GraphDB
- Résolution des problèmes courants

---

## Démarrage Rapide

Une fois l'installation terminée :

1. Démarrer GraphDB Desktop
2. Ouvrir le terminal approprié (Anaconda Prompt sur Windows, Terminal sur Mac)
3. Activer l'environnement :
   ```bash
   conda activate wlc
   ```
4. Lancer l'application :
   ```bash
   cd Backend
   python app.py
   ```
5. Ouvrir le navigateur : `http://localhost:8000`

---

## Structure du Projet

```
Plateforme/
├── Backend/
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration GraphDB
│   ├── app.py                  # Application Flask principale
│   ├── sparql_client.py        # Client SPARQL pour GraphDB
│   ├── comparison_routes.py    # Routes de comparaison
│   ├── uniformat_importer.py   # Import classification Uniformat
│   └── requirements.txt        # Dépendances Python
├── Frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   └── main.css
│   │   └── js/
│   │       ├── main.js
│   │       └── components/     # Composants réutilisables
│   └── index.html              # Interface principale
├── Ontology/
│   ├── WLCONTO.ttl             # Ontologie WLCONTO principale
│   ├── ifcowl.ttl              # Ontologie IFC-OWL (instances)
│   ├── MappingWLCONTO-IFCOWL.ttl  # Mapping entre WLCONTO et IFC-OWL
│   └── stakeholder_mapping_clean.ttl
└── README.md
```

---

## API Backend Principale

### Gestion IFC
- `POST /ifc/upload` - Upload d'un fichier IFC
- `GET /ifc/elements` - Liste des éléments IFC
- `POST /ifc/reset` - Réinitialisation

### Gestion des Coûts
- `POST /cost/update` - Mise à jour d'un coût
- `POST /cost/upload-excel` - Import depuis Excel
- `GET /cost/summary` - Résumé des coûts
- `GET /cost/by-year` - Répartition annuelle

### Gestion des Durées de Vie
- `POST /lifespan/project` - Définir la durée du projet
- `POST /lifespan/element/<guid>` - Définir la durée d'un élément
- `POST /lifespan/upload-excel` - Import depuis Excel
- `POST /lifespan/autofill` - Auto-remplissage basé sur l'ontologie

---

## Mapping Interface ↔ Ontologie RDF

### Classes de Coûts

| Colonne Interface | Classe RDF | Attribution Temporelle |
|-------------------|------------|------------------------|
| `ConstructionCost` | `wlc:ConstructionCosts` | Année 0 |
| `OperationCost` | `wlc:OperationCosts` | Années 1 à N-1 |
| `MaintenanceCost` | `wlc:MaintenanceCosts` | Multiples de la durée de vie |
| `EndOfLifeCost` | `wlc:EndOfLifeCosts` | Année N (fin de projet) |

### Logique de Répétition

Pour un élément avec une durée de vie de 30 ans dans un projet de 100 ans :
- Coûts de maintenance appliqués aux années : 30, 60, 90
- Génération automatique d'instances RDF liées via `wlc:ForDate`

---

## Dépannage

**Badge "Déconnecté" dans l'interface**
- Vérifier que GraphDB Desktop est lancé
- Vérifier que le repository `wlconto` existe et est sélectionné
- Vérifier l'URL dans `Backend/config/config.py` : `http://localhost:7200`

**Erreur "ModuleNotFoundError: ifcopenshell"**
- Vérifier que l'environnement conda est activé : `conda activate wlc`
- Réinstaller si nécessaire : `conda install -c conda-forge ifcopenshell -y`

**Port 8000 déjà utilisé**
- Windows : `netstat -ano | findstr :8000` puis `taskkill /F /PID <numero>`
- Mac/Linux : `lsof -i :8000` puis `kill -9 <PID>`

**Erreur "numpy.dtype size changed"**
- Réinstaller pandas via conda : `conda install -c conda-forge pandas -y`

Plus de solutions dans [INSTALLATION.md](INSTALLATION.md)

---

## Licence

Ce projet est sous licence MIT.
