# 🏗️ Architecture Technique : IFC → RDF → Application

## 📘 Document Technique Personnel

Ce document explique en détail :
1. **Comment les fichiers IFC sont transformés en données RDF**
2. **Comment le graph RDF sert de "répertoire de données" (repository) central**
3. **Comment l'application repose entièrement sur ce graph**

---

## 🎯 Concept Clé : Le Graph RDF comme Unique Source de Vérité

### Architecture Traditionnelle vs Architecture RDF

```
❌ ARCHITECTURE TRADITIONNELLE (SQL)
┌─────────────┐
│   IFC File  │──┐
└─────────────┘  │
                 ├──→ ┌──────────────┐
┌─────────────┐  │    │  SQL Database│
│  Excel File │──┤    │  (Tables)    │
└─────────────┘  │    └──────────────┘
                 │
┌─────────────┐  │
│   CSV File  │──┘
└─────────────┘

Problème : Multiples sources de données, relations difficiles à gérer


✅ NOTRE ARCHITECTURE (RDF Graph)
┌─────────────┐
│   IFC File  │──┐
└─────────────┘  │
                 │    ┌──────────────────────────────┐
┌─────────────┐  │    │     GraphDB (RDF Graph)      │
│  Excel File │──┼──→ │   🎯 UNIQUE SOURCE DE VÉRITÉ │
└─────────────┘  │    │                              │
                 │    │  • Triplets RDF              │
┌─────────────┐  │    │  • Ontologies (schéma)       │
│   Frontend  │──┘    │  • Données (instances)       │
└─────────────┘       │  • Relations sémantiques      │
                      └──────────────────────────────┘
                                    ↑
                                    │ SPARQL queries
                      ┌─────────────┴─────────────┐
                      │   Flask Backend (API)     │
                      │   • Pas de DB locale      │
                      │   • Tout vient de GraphDB │
                      └───────────────────────────┘

Avantage : UNE SEULE source de données, relations explicites, extensible
```

---

## 🔄 Processus Complet : De l'IFC au Graph RDF

### Phase 1 : Upload et Parsing IFC

#### Étape 1.1 : Upload du Fichier IFC

**Endpoint** : `POST /upload-ifc-temp`

**Code (Backend/app.py, ligne ~70-90)** :
```python
@app.route('/upload-ifc-temp', methods=['POST'])
def upload_ifc_temp():
    # Recevoir le fichier depuis le frontend
    file = request.files['file']
    
    # Stocker EN MÉMOIRE (pas sur disque)
    ifc_storage['current_file'] = {
        'content': file.read(),    # Contenu binaire du fichier IFC
        'filename': file.filename,
        'uploaded_at': datetime.now().isoformat(),
        'parsed': False
    }
    
    return jsonify({'success': True})
```

**📌 Point Important** : Le fichier reste en mémoire, pas encore dans GraphDB.

---

#### Étape 1.2 : Parsing IFC → Extraction des Propriétés

**Endpoint** : `POST /parse-ifc`

**Code (Backend/app.py, ligne 123-191)** :
```python
@app.route('/parse-ifc', methods=['POST'])
def parse_ifc():
    # 1. Créer fichier temporaire
    tmp_file.write(ifc_storage['current_file']['content'])
    
    # 2. PARSER avec ifcopenshell (bibliothèque Python)
    model = ifcopenshell.open(tmp_path)
    elements = model.by_type('IfcElement')  # Tous les éléments IFC
    
    # 3. Pour chaque élément IFC
    for elem in elements:
        # Extraire propriétés IFC natives
        guid = elem.GlobalId              # Ex: "2Mn3PzAhj3fwn..."
        name = elem.Name                   # Ex: "Basic Wall"
        etype = elem.is_a()               # Ex: "IfcWall"
        
        # Extraire propriétés Uniformat (si présentes)
        uniformat_code, uniformat_desc = extract_uniformat_props(elem)
        # Ex: "B2020", "Exterior Windows"
        
        # Extraire matériau
        material = extract_material(elem)  # Ex: "Concrete"
        
        # 4. GÉNÉRER URI unique pour cet élément
        uri = f"http://example.com/ifc#{guid}"
        # Ex: "http://example.com/ifc#2Mn3PzAhj3fwn..."
        
        # 5. INSÉRER dans GraphDB (voir Phase 2)
        insert_element(uri)
        insert_global_id(uri, guid)
        insert_denomination(uri, name)
        insert_uniformat_code(uri, uniformat_code)
        insert_uniformat_description(uri, uniformat_desc)
        insert_material(uri, material)
```

**📌 Fonction d'Extraction Uniformat** :
```python
def extract_uniformat_props(elem):
    """Extraction depuis les PropertySets IFC"""
    if hasattr(elem, "IsDefinedBy"):
        for rel in elem.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                prop_set = rel.RelatingPropertyDefinition
                for prop in prop_set.HasProperties:
                    pname = prop.Name.lower()
                    
                    # Chercher "Uniformat Number"
                    if "uniformat" in pname and "number" in pname:
                        uniformat_code = prop.NominalValue.wrappedValue
                    
                    # Chercher "Uniformat Description"
                    if "uniformat" in pname and "description" in pname:
                        uniformat_desc = prop.NominalValue.wrappedValue
    
    return uniformat_code, uniformat_desc
```

---

### Phase 2 : Transformation en Triplets RDF

#### Qu'est-ce qu'un Triplet RDF ?

Un **triplet RDF** est une assertion de la forme :
```
<Sujet> <Prédicat> <Objet>
```

**Exemple concret pour un mur** :
```turtle
# Triplet 1 : Type de l'élément
<http://example.com/ifc#2Mn3PzAhj3fwn> 
    rdf:type 
    wlc:Element .

# Triplet 2 : GUID
<http://example.com/ifc#2Mn3PzAhj3fwn> 
    wlc:globalId 
    "2Mn3PzAhj3fwn" .

# Triplet 3 : Nom
<http://example.com/ifc#2Mn3PzAhj3fwn> 
    wlc:hasDenomination 
    "Basic Wall" .

# Triplet 4 : Code Uniformat
<http://example.com/ifc#2Mn3PzAhj3fwn> 
    wlc:hasUniformatCode 
    "B2020" .

# Triplet 5 : Description Uniformat
<http://example.com/ifc#2Mn3PzAhj3fwn> 
    wlc:hasUniformatDescription 
    "Exterior Windows" .

# Triplet 6 : Matériau
<http://example.com/ifc#2Mn3PzAhj3fwn> 
    wlc:hasIfcMaterial 
    "Concrete" .
```

**Visualisation du Graph** :
```
         wlc:Element
              ↑
              │ rdf:type
              │
    ┌─────────────────────┐
    │  ifc#2Mn3PzAhj3fwn  │ (URI de l'élément)
    └─────────────────────┘
         │         │         │         │
         │         │         │         │
    globalId  hasDenomination hasUniformatCode  hasIfcMaterial
         │         │         │         │
         ↓         ↓         ↓         ↓
   "2Mn3P..."  "Basic Wall"  "B2020"  "Concrete"
```

---

#### Insertion des Triplets dans GraphDB

**Code (Backend/sparql_client.py, ligne 113-174)** :

```python
def insert_element(uri):
    """Insère le triplet de TYPE"""
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    INSERT DATA {{ 
        <{uri}> a wlc:Element . 
    }}
    """
    # Envoyer requête SPARQL UPDATE à GraphDB
    requests.post(UPDATE_ENDPOINT, data={"update": update})

def insert_global_id(uri, guid):
    """Insère le triplet GUID"""
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    INSERT DATA {{
        <{uri}> wlc:globalId "{guid}" .
    }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": update})

def insert_uniformat_code(uri, code):
    """Insère le triplet Uniformat Code"""
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    INSERT DATA {{
        <{uri}> wlc:hasUniformatCode "{code}" .
    }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": update})

# Etc. pour toutes les propriétés...
```

**📌 Point Crucial** : Chaque fonction génère une **requête SPARQL UPDATE** qui est envoyée à GraphDB via HTTP POST.

---

### Phase 3 : Stockage dans GraphDB

#### Qu'est-ce que GraphDB ?

**GraphDB** est une **base de données RDF native** qui :
- Stocke des **triplets RDF** (pas des tables SQL)
- Supporte le langage de requête **SPARQL** (équivalent de SQL pour RDF)
- Implémente le **raisonnement OWL** (inférence de nouvelles connaissances)
- Indexe automatiquement les relations sémantiques

#### Structure du Repository `wlconto`

```
GraphDB Repository : wlconto
│
├── Ontologies (Schéma / TBox)
│   ├── WLCONTO.ttl
│   │   ├── Classes (wlc:Element, wlc:Costs, wlc:LifeSpan, etc.)
│   │   ├── Propriétés (wlc:hasCost, wlc:hasUniformatCode, etc.)
│   │   └── Règles d'inférence (OWL)
│   │
│   ├── stakeholder_mapping_clean.ttl
│   │   ├── wlc:Stakeholder (parties prenantes)
│   │   └── Mappings spécifiques
│   │
│   └── 6_EndOfLifeManagement_Module_Protege.ttl
│       ├── eol:hasType (stratégie EOL)
│       ├── eol:atPlace (destination)
│       └── eol:providesParticipantRole (responsable)
│
└── Données (Instances / ABox)
    ├── Éléments IFC
    │   ├── <http://example.com/ifc#2Mn3PzAhj3fwn> a wlc:Element
    │   ├── <http://example.com/ifc#1Ab2Cd3Ef4Gh5> a wlc:Element
    │   └── ... (tous les éléments du projet)
    │
    ├── Coûts
    │   ├── <.../cost/construction_abc123> a wlc:ConstructionCosts
    │   ├── <.../cost/operation_xyz789> a wlc:OperationCosts
    │   └── ... (instances de coûts liées aux éléments)
    │
    ├── Durées de Vie
    │   ├── <.../lifespan/Year0> a wlc:Time
    │   ├── <.../lifespan/Year30> a wlc:Time
    │   └── ... (timeline du projet)
    │
    └── Stratégies EOL
        ├── <.../ifc#element1> eol:hasType "Recycle"
        ├── <.../ifc#element2> eol:atPlace "Centre de tri municipal"
        └── ... (stratégies de fin de vie)
```

---

## 📖 Le Graph RDF comme Répertoire de Données

### Concept : Single Source of Truth

**Définition** : Le **graph RDF dans GraphDB** est la **seule et unique source de données** de l'application.

```
┌────────────────────────────────────────────────────────┐
│              GraphDB (wlconto repository)              │
│                                                        │
│  🎯 UNIQUE RÉPERTOIRE DE DONNÉES                      │
│                                                        │
│  • Pas de base SQL en parallèle                       │
│  • Pas de fichiers JSON/CSV en cache                  │
│  • Toutes les données sont des triplets RDF           │
│  • Toutes les lectures/écritures passent par SPARQL   │
└────────────────────────────────────────────────────────┘
                         ↑
                         │ SPARQL HTTP
                         │
┌────────────────────────────────────────────────────────┐
│              Backend Flask (app.py)                    │
│                                                        │
│  • Aucune donnée stockée localement                   │
│  • Seulement logique métier + transformation          │
│  • Génère requêtes SPARQL selon besoins               │
└────────────────────────────────────────────────────────┘
                         ↑
                         │ REST API (JSON)
                         │
┌────────────────────────────────────────────────────────┐
│              Frontend (index.html, main.js)            │
│                                                        │
│  • Interface utilisateur                              │
│  • Appels API vers backend                            │
│  • Affichage dynamique des données                    │
└────────────────────────────────────────────────────────┘
```

---

### Avantages de cette Architecture

#### 1. **Cohérence des Données**

```python
# ❌ PROBLÈME avec SQL traditionnel
# Données dupliquées entre plusieurs tables
Table1: elements (id, name, material)
Table2: costs (element_id, value)
Table3: lifespans (element_id, years)
# Risque : incohérences si une table n'est pas mise à jour

# ✅ SOLUTION avec RDF
# UN SEUL élément avec toutes ses relations
<http://example.com/ifc#123> 
    wlc:hasDenomination "Wall" ;
    wlc:hasIfcMaterial "Concrete" ;
    wlc:hasCost <.../cost/construction_abc> ;
    wlc:hasLifespan <.../lifespan/30years> ;
    eol:hasType "Recycle" .
# Tout est connecté sémantiquement !
```

#### 2. **Relations Explicites**

```turtle
# Les relations sont EXPLICITES dans le graph
<ifc#wall123> wlc:hasCost <cost#construction_abc> .
<cost#construction_abc> wlc:hasCostValue "50000"^^xsd:double .
<cost#construction_abc> wlc:ForDate <project#Year0> .

# Requête SPARQL pour suivre la chaîne
SELECT ?element ?cost ?year WHERE {
    ?element wlc:hasCost ?costInst .
    ?costInst wlc:hasCostValue ?cost .
    ?costInst wlc:ForDate ?yearInst .
    ?yearInst wlc:hasYearValue ?year .
}
# Les relations se traversent naturellement !
```

#### 3. **Extensibilité**

```turtle
# ✅ Ajouter de nouvelles propriétés SANS changer le schéma
<ifc#wall123> 
    wlc:hasDenomination "Wall" ;           # Déjà présent
    wlc:hasIfcMaterial "Concrete" ;        # Déjà présent
    eol:hasType "Recycle" ;                # ✨ Nouveau (module EOL)
    eol:atPlace "Centre de tri" ;          # ✨ Nouveau
    myapp:hasCustomProperty "Value" .      # ✨ Extension personnalisée

# Pas besoin de ALTER TABLE !
# Juste ajouter les triplets
```

#### 4. **Interopérabilité**

```turtle
# ✅ Aligner avec d'autres ontologies
PREFIX dpp: <http://www.semanticweb.org/adamy/ontologies/2025/DPP#>
PREFIX wlcpo: <http://www.semanticweb.org/adamy/ontologies/2025/WLCPO#>

# Module d'alignement
wlcpo:Asset rdfs:subClassOf dpp:Product .

# Maintenant, tous les wlcpo:Asset SONT AUSSI des dpp:Product
# GraphDB infère automatiquement cette relation !
```

---

## 🔍 Comment l'Application Utilise le Graph

### 1. Lecture des Données : Requêtes SPARQL SELECT

#### Exemple 1 : Récupérer tous les éléments IFC

**Endpoint** : `GET /get-ifc-elements`

**Code (Backend/app.py, ligne ~600-700)** :
```python
@app.route('/get-ifc-elements')
def get_ifc_elements():
    # Générer requête SPARQL SELECT
    query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    
    SELECT ?element ?globalId ?name ?uniformatCode ?uniformatDesc ?material
    WHERE {
        ?element a wlc:Element .
        ?element wlc:globalId ?globalId .
        OPTIONAL { ?element wlc:hasDenomination ?name }
        OPTIONAL { ?element wlc:hasUniformatCode ?uniformatCode }
        OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc }
        OPTIONAL { ?element wlc:hasIfcMaterial ?material }
    }
    ORDER BY ?uniformatCode
    """
    
    # Envoyer à GraphDB
    response = requests.post(
        GRAPHDB_REPO,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"}
    )
    
    # Parser la réponse JSON SPARQL
    results = response.json()["results"]["bindings"]
    
    # Transformer en format API
    elements = []
    for row in results:
        elements.append({
            'GlobalId': row.get('globalId', {}).get('value', ''),
            'Name': row.get('name', {}).get('value', ''),
            'UniformatCode': row.get('uniformatCode', {}).get('value', ''),
            'UniformatDesc': row.get('uniformatDesc', {}).get('value', ''),
            'Material': row.get('material', {}).get('value', '')
        })
    
    # Retourner JSON au frontend
    return jsonify({'elements': elements})
```

**Réponse SPARQL de GraphDB** (format JSON) :
```json
{
  "results": {
    "bindings": [
      {
        "element": { "type": "uri", "value": "http://example.com/ifc#2Mn3PzAhj3fwn" },
        "globalId": { "type": "literal", "value": "2Mn3PzAhj3fwn" },
        "name": { "type": "literal", "value": "Basic Wall" },
        "uniformatCode": { "type": "literal", "value": "B2020" },
        "uniformatDesc": { "type": "literal", "value": "Exterior Windows" },
        "material": { "type": "literal", "value": "Concrete" }
      },
      ...
    ]
  }
}
```

---

#### Exemple 2 : Récupérer les coûts d'un élément

**Code** :
```python
query = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>

SELECT ?costType ?costValue ?year
WHERE {{
    <{element_uri}> wlc:hasCost ?costInst .
    ?costInst a ?costType ;
              wlc:hasCostValue ?costValue .
    OPTIONAL {{
        ?costInst wlc:ForDate ?timeInst .
        ?timeInst wlc:hasYearValue ?year .
    }}
    
    # Filtrer seulement les classes de coûts
    FILTER(?costType IN (
        wlc:ConstructionCosts, 
        wlc:OperationCosts, 
        wlc:MaintenanceCosts, 
        wlc:EndOfLifeCosts
    ))
}}
"""
```

**Résultat** :
```json
[
  {
    "costType": "http://.../WLCONTO#ConstructionCosts",
    "costValue": "50000",
    "year": "0"
  },
  {
    "costType": "http://.../WLCONTO#OperationCosts",
    "costValue": "2000",
    "year": "1"
  },
  ...
]
```

---

### 2. Écriture des Données : Requêtes SPARQL UPDATE

#### Exemple 1 : Ajouter un coût de construction

**Code (Backend/sparql_client.py, ligne 176-230)** :
```python
def update_cost_for_element(uri, cost, category):
    import uuid
    
    # ÉTAPE 1 : Supprimer l'ancien coût (si existe)
    delete_query = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    
    DELETE {{
        <{uri}> wlc:hasCost ?oldCost .
        ?oldCost ?p ?o .
    }}
    WHERE {{
        <{uri}> wlc:hasCost ?oldCost .
        ?oldCost a wlc:{category} .
        ?oldCost ?p ?o .
    }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
    
    # ÉTAPE 2 : Créer nouvelle instance de coût
    cost_uri = f"http://example.com/ifc/{uri.split('#')[-1]}/cost/{category.lower()}_{uuid.uuid4().hex[:8]}"
    
    insert_query = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    
    INSERT DATA {{
        <{uri}> wlc:hasCost <{cost_uri}> .
        <{cost_uri}> a wlc:{category} ;
                     a wlc:Costs ;
                     wlc:hasCostValue "{cost}"^^xsd:double ;
                     wlc:appliesTo <{uri}> .
    }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": insert_query})
```

**Ce qui se passe dans GraphDB** :
```turtle
# AVANT (ancien coût supprimé)
<ifc#wall123> wlc:hasCost <cost/old_abc123> .
<cost/old_abc123> a wlc:ConstructionCosts ;
                  wlc:hasCostValue "45000"^^xsd:double .

# APRÈS (nouveau coût ajouté)
<ifc#wall123> wlc:hasCost <cost/construction_xyz789> .
<cost/construction_xyz789> a wlc:ConstructionCosts ;
                           a wlc:Costs ;
                           wlc:hasCostValue "50000"^^xsd:double ;
                           wlc:appliesTo <ifc#wall123> .
```

---

#### Exemple 2 : Ajouter une stratégie EOL

**Code (Backend/app.py, ligne ~3700-3800)** :
```python
@app.route('/update-end-of-life-strategy', methods=['POST'])
def update_end_of_life_strategy():
    guid = request.json['guid']
    strategy = request.json['strategy']  # Ex: "Recycle"
    
    # Encoder GUID pour URI (gestion espaces)
    encoded_guid = urllib.parse.quote(str(guid), safe='')
    element_uri = f"http://example.com/ifc#{encoded_guid}"
    
    # ÉTAPE 1 : Supprimer ancienne stratégie
    delete_query = f"""
    PREFIX eol: <http://www.w3id.org/dpp/EoL#>
    PREFIX dpp: <http://www.semanticweb.org/adamy/ontologies/2025/DPP#>
    
    DELETE {{
        <{element_uri}> dpp:hasDisposalOption ?oldStrategy .
        <{element_uri}> eol:hasType ?oldStrategyText .
    }}
    WHERE {{
        OPTIONAL {{ <{element_uri}> dpp:hasDisposalOption ?oldStrategy }}
        OPTIONAL {{ <{element_uri}> eol:hasType ?oldStrategyText }}
    }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
    
    # ÉTAPE 2 : Ajouter nouvelle stratégie
    insert_query = f"""
    PREFIX eol: <http://www.w3id.org/dpp/EoL#>
    
    INSERT DATA {{
        <{element_uri}> eol:hasType "{strategy}" .
    }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": insert_query})
    
    return jsonify({'success': True})
```

**Triplets créés dans GraphDB** :
```turtle
<http://example.com/ifc#D3020%20-%20Syst%C3%A8me%20de%20Production%20de%20Chaleur>
    eol:hasType "Recycle" .
```

---

## 🔗 Relations Complexes dans le Graph

### Exemple : Chaîne de Relations pour le Calcul WLC

```turtle
# Élément IFC
<ifc#wall123> a wlc:Element ;
    wlc:globalId "wall123" ;
    wlc:hasDenomination "Exterior Wall" ;
    wlc:hasLifespan <lifespan#wall123_lifespan> ;
    wlc:hasCost <cost#wall123_construction> ;
    wlc:hasCost <cost#wall123_maintenance_year30> ;
    wlc:hasCost <cost#wall123_endoflife> .

# Durée de vie de l'élément
<lifespan#wall123_lifespan> a wlc:LifeSpan ;
    wlc:hasDuration "30"^^xsd:integer ;
    wlc:isLifeSpanOf <ifc#wall123> .

# Coût de construction (année 0)
<cost#wall123_construction> a wlc:ConstructionCosts, wlc:Costs ;
    wlc:hasCostValue "50000"^^xsd:double ;
    wlc:appliesTo <ifc#wall123> ;
    wlc:ForDate <project#lifespan#Year0> .

# Coût de maintenance (année 30)
<cost#wall123_maintenance_year30> a wlc:MaintenanceCosts, wlc:Costs ;
    wlc:hasCostValue "15000"^^xsd:double ;
    wlc:appliesTo <ifc#wall123> ;
    wlc:ForDate <project#lifespan#Year30> .

# Coût de fin de vie (année 100)
<cost#wall123_endoflife> a wlc:EndOfLifeCosts, wlc:Costs ;
    wlc:hasCostValue "8000"^^xsd:double ;
    wlc:appliesTo <ifc#wall123> ;
    wlc:ForDate <project#lifespan#Year100> .

# Timeline du projet
<project#lifespan#Year0> a wlc:Time ;
    wlc:hasYearValue "0"^^xsd:integer .

<project#lifespan#Year30> a wlc:Time ;
    wlc:hasYearValue "30"^^xsd:integer .

<project#lifespan#Year100> a wlc:Time ;
    wlc:hasYearValue "100"^^xsd:integer .
```

**Visualisation du Graph** :
```
                    ┌──────────────┐
                    │  ifc#wall123 │
                    │  (Element)   │
                    └──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   hasLifespan         hasCost            hasCost
        │                  │                  │
        ↓                  ↓                  ↓
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ LifeSpan      │  │ Construction │  │ Maintenance  │
│ Duration: 30  │  │ Value: 50000 │  │ Value: 15000 │
└───────────────┘  └──────┬───────┘  └──────┬───────┘
                          │                  │
                       ForDate            ForDate
                          │                  │
                          ↓                  ↓
                   ┌──────────┐       ┌──────────┐
                   │  Year 0  │       │  Year 30 │
                   └──────────┘       └──────────┘
```

**Requête SPARQL pour Calcul WLC** :
```sparql
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>

SELECT ?element ?costType ?costValue ?year
WHERE {
    ?element a wlc:Element .
    ?element wlc:hasCost ?costInst .
    ?costInst a ?costType ;
              wlc:hasCostValue ?costValue .
    OPTIONAL {
        ?costInst wlc:ForDate ?timeInst .
        ?timeInst wlc:hasYearValue ?year .
    }
}
ORDER BY ?element ?year
```

**Résultat** (utilisé pour le calcul et l'affichage) :
```json
[
  {
    "element": "ifc#wall123",
    "costType": "ConstructionCosts",
    "costValue": 50000,
    "year": 0
  },
  {
    "element": "ifc#wall123",
    "costType": "MaintenanceCosts",
    "costValue": 15000,
    "year": 30
  },
  {
    "element": "ifc#wall123",
    "costType": "EndOfLifeCosts",
    "costValue": 8000,
    "year": 100
  }
]
```

---

## 🧠 Inférence Automatique (OWL Reasoning)

### Concept : GraphDB Déduit de Nouvelles Connaissances

**Exemple : Alignement DPP** :

```turtle
# ONTOLOGIE (règle définie)
wlcpo:Asset rdfs:subClassOf dpp:Product .

# DONNÉES (instance créée)
<ifc#wall123> a wlcpo:Asset .

# INFÉRENCE AUTOMATIQUE (GraphDB déduit)
<ifc#wall123> a dpp:Product .  # ✨ Pas besoin de l'ajouter manuellement !
```

**Requête exploitant l'inférence** :
```sparql
# Cette requête trouve <ifc#wall123> même si on n'a jamais
# explicitement dit que c'est un dpp:Product !
SELECT ?product WHERE {
    ?product a dpp:Product .
}
# GraphDB raisonne : wall123 EST UN Asset, 
#                    ET Asset EST UN Product,
#                    DONC wall123 EST UN Product
```

---

## 📊 Flux de Données Complet : Exemple Concret

### Scénario : Utilisateur Modifie le Coût de Construction d'un Mur

```
1. FRONTEND : Utilisateur change "50000" → "55000" dans le tableau

2. JAVASCRIPT (main.js) :
   fetch('/update-costs', {
       method: 'POST',
       body: JSON.stringify({
           guid: 'wall123',
           cost: 55000,
           phase: 'ConstructionCosts'
       })
   })

3. BACKEND (app.py) :
   @app.route('/update-costs', methods=['POST'])
   def update_costs():
       # Générer URI
       uri = f"http://example.com/ifc#{guid}"
       
       # Appeler fonction SPARQL
       update_cost_for_element(uri, 55000, 'ConstructionCosts')

4. SPARQL CLIENT (sparql_client.py) :
   def update_cost_for_element(uri, cost, category):
       # DELETE ancienne valeur
       DELETE { <uri> wlc:hasCost ?old . ?old ?p ?o }
       WHERE { ... }
       
       # INSERT nouvelle valeur
       INSERT DATA {
           <uri> wlc:hasCost <new_cost_uri> .
           <new_cost_uri> a wlc:ConstructionCosts ;
                          wlc:hasCostValue "55000"^^xsd:double .
       }

5. GRAPHDB : 
   - Reçoit requête SPARQL UPDATE
   - Supprime triplets de l'ancien coût
   - Ajoute triplets du nouveau coût
   - ✅ Données PERSISTÉES dans le graph RDF

6. BACKEND : Retourne {"success": true}

7. FRONTEND : Affiche notification "✓ Coût mis à jour"
```

**Point Important** : À AUCUN MOMENT les données ne sont stockées ailleurs que dans GraphDB.

---

## 🎓 Pourquoi Cette Architecture Est Puissante

### 1. **Traçabilité Complète**

```sparql
# Qui a payé quoi pour quel élément ?
SELECT ?element ?stakeholder ?cost ?percentage
WHERE {
    ?element a wlc:Element .
    ?attribution wlc:attributesTo ?stakeholder ;
                 wlc:concernsElement ?element ;
                 wlc:concernsCostType ?costType ;
                 wlc:hasPercentage ?percentage .
    ?element wlc:hasCost ?costInst .
    ?costInst a ?costType ;
              wlc:hasCostValue ?cost .
}
# Toutes les relations sont explicites et requêtables !
```

### 2. **Flexibilité**

```turtle
# Ajouter nouvelle dimension SANS toucher au code existant
<ifc#wall123> 
    myapp:hasCarbonFootprint "150"^^xsd:double ;
    myapp:hasSupplier <supplier#CompanyXYZ> ;
    myapp:hasWarrantyYears "10"^^xsd:integer .

# Requête fonctionne immédiatement
SELECT ?element ?carbon WHERE {
    ?element myapp:hasCarbonFootprint ?carbon .
}
```

### 3. **Interopérabilité**

```turtle
# Exporter vers d'autres systèmes (format standard RDF)
# Import dans Protégé, OntoText, Apache Jena, etc.
# Fusion avec d'autres ontologies (BIM, GIS, etc.)
```

---

## 🔧 Outils pour Explorer le Graph

### 1. Interface GraphDB

**URL** : `http://localhost:7200`

**Explore → Visual Graph** :
- Rechercher un GUID : `2Mn3PzAhj3fwn`
- Visualiser toutes les relations connectées
- Cliquer sur les nœuds pour explorer

### 2. SPARQL Query Editor

**URL** : `http://localhost:7200/sparql`

**Exemples de requêtes utiles** :

```sparql
# Compter les éléments
SELECT (COUNT(?element) AS ?count) WHERE {
    ?element a wlc:Element .
}

# Lister tous les triplets d'un élément
SELECT ?p ?o WHERE {
    <http://example.com/ifc#wall123> ?p ?o .
}

# Trouver éléments avec stratégie EOL
SELECT ?element ?strategy WHERE {
    ?element eol:hasType ?strategy .
}
```

---

## 📝 Résumé : L'Architecture en 3 Points

### 1. **IFC → RDF** : Transformation
- Parsing IFC avec `ifcopenshell`
- Extraction propriétés (GUID, Uniformat, matériau)
- Génération URI unique
- Création triplets RDF
- Insertion dans GraphDB via SPARQL UPDATE

### 2. **GraphDB** : Répertoire Central
- **Unique source de vérité** pour toutes les données
- Stockage triplets RDF (Sujet-Prédicat-Objet)
- Ontologies définissent le schéma (classes, propriétés)
- Inférence OWL pour déductions automatiques
- Indexation automatique des relations

### 3. **Application** : Consommation
- Backend **NE STOCKE RIEN** localement
- Toutes les lectures via SPARQL SELECT
- Toutes les écritures via SPARQL UPDATE/INSERT/DELETE
- Frontend reçoit JSON transformé depuis SPARQL
- Architecture découplée et maintenable

---

## 🎯 Conclusion

Le **graph RDF dans GraphDB** n'est pas juste une "base de données alternative" :

✅ C'est un **modèle de connaissances** qui encode :
- Les **entités** (éléments IFC, coûts, durées)
- Les **relations** (hasCost, hasLifespan, ForDate)
- Les **règles** (ontologies OWL)
- Les **inférences** (raisonnement automatique)

✅ L'application **repose entièrement** sur ce graph :
- Pas de duplication de données
- Une seule source de vérité
- Relations explicites et requêtables
- Extensible sans modifier le code

✅ Cette architecture permet :
- Analyses complexes via SPARQL
- Traçabilité complète
- Interopérabilité (export RDF standard)
- Évolution sans rupture (ajout propriétés)

**C'est l'essence du Web Sémantique appliqué à la gestion de projets de construction ! 🏗️🧠**

