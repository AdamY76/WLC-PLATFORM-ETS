# COMPRÉHENSION COMPLÈTE DU PROJET - Plateforme WLC

## ARCHITECTURE GÉNÉRALE

### Stack Technique
- **Backend**: Flask (Python) + GraphDB (base SPARQL)
- **Frontend**: HTML/JavaScript/Bootstrap
- **Ontologie**: WLCONTO (Whole Life Cost Ontology)
- **Format de données**: IFC (Industry Foundation Classes)

---

## MODÈLE DE DONNÉES

### 1. Structure de l'Ontologie WLCONTO

#### Classes principales:
- `wlc:Element` - Représente un élément de construction IFC
- `wlc:Costs` - Classe de base pour tous les coûts
  - `wlc:ConstructionCosts` - Coûts de construction (année 0)
  - `wlc:OperationCosts` - Coûts d'opération (annuels récurrents)
  - `wlc:MaintenanceCosts` - Coûts de maintenance (annuels récurrents)
  - `wlc:EndOfLifeCosts` - Coûts de fin de vie/remplacement

#### Propriétés des éléments:
- `wlc:globalId` - GUID IFC (format: alphanumér

ique, ex: "3ZYW59sxj8lei475l7EhLU")
- `wlc:hasDenomination` - Nom descriptif de l'élément
- `wlc:hasUniformatCode` - Code de classification Uniformat
- `wlc:hasUniformatDescription` - Description Uniformat
- `wlc:hasIfcMaterial` - Matériau IFC
- `wlc:hasIfcClass` - Classe IFC (IfcWall, IfcWindow, etc.)
- `wlc:hasDuration` - Durée de vie de l'élément (en années)
- `wlc:hasCost` - Lien vers les instances de coûts

#### Structure des coûts:
```
Élément (ex: Window - GUID: 0tA4DSHd50le6Ov9Yu0I9X)
    └── wlc:hasCost → Instance de Coût
                        ├── a wlc:ConstructionCosts (type)
                        ├── a wlc:Costs (type parent)
                        ├── wlc:hasCostValue "800.0"^^xsd:double
                        ├── wlc:appliesTo <élément>
                        └── wlc:ForDate <année> (liaison temporelle)
```

---

## LOGIQUE DE GESTION DES COÛTS

### 1. URIs des éléments
Les éléments sont identifiés par des URIs construites à partir de leur GUID IFC:
```
Format: http://example.com/ifc#<GUID_ENCODE>
Exemple: http://example.com/ifc#0tA4DSHd50le6Ov9Yu0I9X
```

**IMPORTANT**: Le GUID doit être encodé avec `urllib.parse.quote()` pour gérer les caractères spéciaux.

### 2. Création d'un coût (`update_cost_for_element`)

**Processus** (ligne 176-208 de sparql_client.py):
1. **Suppression des anciens coûts** de la même catégorie pour l'élément
2. **Création d'une nouvelle instance de coût** avec un UUID unique
3. **Typage multiple** du coût:
   - `wlc:Costs` (classe parente)
   - `wlc:ConstructionCosts` / `wlc:OperationCosts` / etc.
4. **Propriétés du coût**:
   - `wlc:hasCostValue` - Valeur en double XSD
   - `wlc:appliesTo` - Lien vers l'élément
5. **Liaison bidirectionnelle**: L'élément a aussi `wlc:hasCost` vers l'instance

**Exemple de coût créé**:
```turtle
<http://example.com/ifc#0tA4DSHd50le6Ov9Yu0I9X/cost/operationcosts_abc123>
    a wlc:OperationCosts, wlc:Costs ;
    wlc:hasCostValue "25.0"^^xsd:double ;
    wlc:appliesTo <http://example.com/ifc#0tA4DSHd50le6Ov9Yu0I9X> .

<http://example.com/ifc#0tA4DSHd50le6Ov9Yu0I9X>
    wlc:hasCost <.../cost/operationcosts_abc123> .
```

### 3. Répartition des coûts sur les années

**Je comprends maintenant le problème**: Les coûts que j'ai supprimés n'étaient PAS des instances uniques de 800$, mais une **DISTRIBUTION de coûts sur TOUTES les années du projet**.

#### Pour les Coûts d'Opération:
- Un coût annuel (ex: 25$) est créé pour **CHAQUE année** de la durée de vie
- Si durée de vie = 50 ans, il y a 50 instances de coût OperationCosts
- Chaque instance est liée à une année via `wlc:ForDate`

#### Pour les Coûts de Maintenance:
- Coûts de remplacement calculés selon la durée de vie de l'élément
- Si l'élément a une durée de vie < durée du projet, des remplacements sont prévus
- Exemple: Élément avec durée de 20 ans sur projet de 50 ans = 2 remplacements (années 20 et 40)

#### Pour les Coûts de Fin de Vie:
- Appliqués à la fin de la durée de vie de l'élément
- OU à chaque remplacement pendant le projet
- OU à la fin du projet pour tous les éléments

### 4. Fonction `relink_costs_to_years()` (ligne 926)

**Actuellement vide** dans le code, mais appelée après chaque mise à jour de coût.
Son rôle devrait être de:
1. Récupérer la durée de vie du projet (`<http://example.com/ifc#Project> wlc:hasDuration`)
2. Pour chaque coût d'opération/maintenance, créer des instances liées aux années
3. Utiliser `wlc:ForDate` pour lier chaque instance de coût à une année spécifique

---

## CALCUL WLC (Whole Life Cost)

### Formule WLC (ligne 2500-2700 de app.py):

```
WLC_Total = Construction + Opération + Maintenance + Fin_de_Vie

Où:
- Construction = Somme(coûts_construction) [année 0 uniquement]
- Opération = Somme(coûts_annuels) × (durée_projet - 1)
- Maintenance = Somme(coûts_maintenance_annuels) × durée_projet
                + Somme(coûts_remplacement) 
- Fin_de_Vie = Somme(coûts_fin_de_vie) [année finale]

Remplacement:
- Nombre_remplacements = durée_projet // durée_vie_élément
- Si durée_projet % durée_vie_élément == 0: Nombre_remplacements -= 1
```

### Années de remplacement:
```python
for année in range(durée_vie_élément, durée_projet, durée_vie_élément):
    # Coût de remplacement à cette année
    coût_remplacement = coût_fin_de_vie_élément
```

---

## GESTION DES DURÉES DE VIE

### Durée de vie du projet:
- Stockée dans: `<http://example.com/ifc#Project> wlc:hasDuration "50"^^xsd:integer`
- Par défaut: 50 ans
- Route: `/get-project-lifespan` et `/set-project-lifespan`

### Durée de vie des éléments:
- Propriété: `wlc:hasDuration` sur chaque élément
- Fonction: `set_element_duration(guid, duration)` (ligne 2780)
- Utilise `create_element_uri()` pour encoder le GUID

---

## PARTIES PRENANTES (Stakeholders)

### Types de parties prenantes:
- `wlc:PropertyOwner` - Propriétaire (Construction, Fin de vie)
- `wlc:EndUser` - Utilisateur final (Opération)
- `wlc:MaintenanceProvider` - Maintenance
- `wlc:EnergyProvider` - Énergie (partage Opération)

### Attribution des coûts:
```turtle
Attribution_instance
    a wlc:CostAttribution ;
    wlc:attributedTo <stakeholder_uri> ;
    wlc:concernsElement <element_uri> ;
    wlc:concernsCostType wlc:OperationCosts ;
    wlc:hasPercentage "30"^^xsd:double .
```

---

## FICHIERS CLÉS

### Backend:
1. **app.py** (4472 lignes):
   - Routes Flask
   - Logique métier WLC
   - Calculs de coûts et statistiques
   - Import/Export IFC
   
2. **sparql_client.py** (532 lignes):
   - Connexion GraphDB
   - Fonctions CRUD pour l'ontologie
   - `update_cost_for_element()` - **FONCTION CRITIQUE**
   - `query_graphdb()` - Exécution SPARQL
   - `clear_instances()` - Vidange de la base

3. **config.py**:
   - `GRAPHDB_REPO = "http://localhost:7200/repositories/wlconto"`

### Frontend:
1. **index.html**:
   - Interface Bootstrap
   - Tableau des éléments avec édition inline
   - Onglets: IFC, Éléments, Coûts, Durées de vie, Synthèse, etc.

2. **assets/js/main.js** (6361 lignes):
   - Gestion du tableau des éléments
   - Édition inline des coûts, matériaux, durées de vie
   - Appels API vers le backend
   - Visualisations Chart.js

### Ontologies:
1. **WLCONTO.ttl** - Ontologie principale WLC
2. **ifcowl.ttl** - Mapping IFC-OWL
3. **MappingWLCONTO-IFCOWL.ttl** - Mapping entre les deux

---

## ERREURS CRITIQUES À ÉVITER

### 1. GUID vs Description
**ERREUR**: Confondre le GUID avec la description
- ✅ GUID IFC: `0tA4DSHd50le6Ov9Yu0I9X` (alphanumé

rique)
- ❌ Description: `Window for Test Example` (texte descriptif)
- **L'URI doit utiliser le GUID**, pas la description !

### 2. Encodage des URIs
**ERREUR**: Ne pas encoder les GUIDs avec des caractères spéciaux
```python
# ✅ CORRECT:
guid_encoded = urllib.parse.quote(guid, safe='')
uri = f"http://example.com/ifc#{guid_encoded}"

# ❌ INCORRECT:
uri = f"http://example.com/ifc#{guid}"  # Problème si guid contient espaces
```

### 3. Suppression des coûts
**ERREUR GRAVE**: Supprimer tous les coûts d'un élément sans comprendre leur structure
- Les coûts d'opération/maintenance sont **distribués sur les années**
- Un élément peut avoir **des centaines d'instances de coûts** (une par année)
- La suppression doit être **ciblée par catégorie** uniquement

### 4. Types de coûts
**ERREUR**: Oublier le préfixe XSD dans les requêtes SPARQL
```sparql
# ✅ CORRECT:
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
wlc:hasCostValue "800.0"^^xsd:double

# ❌ INCORRECT:
wlc:hasCostValue "800.0"^^xsd:double  # Sans PREFIX xsd
```

---

## WORKFLOW UTILISATEUR TYPIQUE

1. **Upload IFC** → `/upload-ifc-temp`
2. **Parser IFC** → `/parse-ifc` 
   - Extrait éléments (GUID, nom, type, Uniformat, matériau)
   - Insère dans GraphDB comme `wlc:Element`
3. **Définir durée de vie projet** → `/set-project-lifespan`
4. **Saisir coûts par élément** (via tableau frontend)
   - Construction, Opération, Maintenance, Fin de vie
   - Appelle `/update-costs` qui appelle `update_cost_for_element()`
5. **Définir durées de vie éléments** → `/update-lifespan`
6. **Calculer WLC** → Frontend calcule ou `/calculate-wlc` (routes multiples)
7. **Analyser par parties prenantes** → `/api/stakeholder-analysis/multi-view`
8. **Export enrichi** → `/enrich-ifc` puis download

---

## QUESTIONS EN SUSPENS / À IMPLÉMENTER

1. ❓ **`relink_costs_to_years()` n'est pas implémentée** - Comment les coûts sont-ils actuellement liés aux années ?
2. ❓ **ForDate** - Cette propriété est-elle utilisée dans les requêtes de calcul WLC ?
3. ❓ **Actualisation** - Le calcul WLC inclut-il l'actualisation financière dans le temps ?
4. ✅ **Taux d'actualisation** - Code présent dans app.py (lignes 1721+)

---

## PROCHAINES ACTIONS RECOMMANDÉES

1. ✅ Vérifier les 3 éléments actuels dans GraphDB
2. ⚠️ **NE PAS tester de suppressions** sans backup GraphDB
3. 📚 Lire la documentation WLCONTO.ttl pour comprendre toutes les propriétés
4. 🔍 Rechercher où `wlc:ForDate` est utilisé dans le code
5. 💾 Mettre en place des backups automatiques de GraphDB

---

## FLUX DE DONNÉES - FRONTEND ↔ BACKEND

### 1. Chargement des éléments (loadElements)

**Frontend** (main.js ligne 136-163):
```javascript
async function loadElements() {
    const response = await fetch('/get-ifc-elements');
    const elements = await response.json();
    appState.elements = elements;
    displayElements(elements);
}
```

**Backend** (app.py ligne 176-250):
```python
@app.route('/get-ifc-elements')
def get_ifc_elements():
    # Requête SPARQL qui récupère TOUS les éléments et leurs coûts
    sparql = """
    SELECT ?elem ?guid ?name ?uniformat ?cost ?costType ?lifespan
    WHERE {
      ?typeClass rdfs:subClassOf* wlc:Element .
      ?elem a ?typeClass .
      OPTIONAL { ?elem wlc:globalId ?guid . }
      OPTIONAL { ?elem wlc:hasCost ?costInst .
                 ?costInst wlc:hasCostValue ?cost .
                 ?costInst a ?costType . }
      OPTIONAL { ?elem wlc:hasDuration ?lifespan . }
    }
    """
    results = query_graphdb(sparql)
    
    # Agrégation par élément (un élément peut avoir plusieurs coûts)
    items = {}
    for row in results:
        guid = row.get('guid') or extract_from_uri(row['elem'])
        if guid not in items:
            items[guid] = {...}
        
        # Ajouter le coût selon son type
        if row.get('costType'):
            cost_type_name = get_cost_type_name(row['costType'])
            items[guid][cost_type_name] = float(row['cost'])
    
    return jsonify(list(items.values()))
```

**Structure des données retournées**:
```json
[
  {
    "GlobalId": "0tA4DSHd50le6Ov9Yu0I9X",
    "Name": "Window for Test Example",
    "UniformatCode": "B2020",
    "UniformatDesc": "Exterior Windows",
    "Material": "Glass",
    "IfcClass": "IfcWindow",
    "ConstructionCost": 800.0,
    "OperationCost": 25.0,
    "MaintenanceCost": 50.0,
    "EndOfLifeCost": 100.0,
    "Lifespan": 30
  }
]
```

### 2. Affichage des éléments (displayElements)

**Frontend** (main.js ligne 163-193):
```javascript
function displayElements(elements) {
    const tbody = document.querySelector('#elements-table tbody');
    tbody.innerHTML = '';
    
    elements.forEach(element => {
        const row = createElementRow(element);
        tbody.appendChild(row);
    });
}

function createElementRow(element) {
    const row = document.createElement('tr');
    row.dataset.guid = element.GlobalId;
    
    // Colonnes du tableau:
    // 1. Checkbox de sélection
    // 2. GUID (lecture seule)
    // 3. Description / Nom
    // 4. Code Uniformat
    // 5. Classe IFC
    // 6. Matériau (éditable inline)
    // 7-10. Coûts (éditables inline):
    //    - Construction
    //    - Opération
    //    - Maintenance
    //    - Fin de vie
    // 11. Durée de vie (éditable inline)
    
    row.innerHTML = `
        <td><input type="checkbox" class="form-check-input element-checkbox"></td>
        <td>${element.GlobalId}</td>
        <td>${element.Name || '-'}</td>
        <td>${element.UniformatCode || '-'}</td>
        <td>${element.IfcClass || '-'}</td>
        <td>
            <input type="text" class="form-control form-control-sm material-input"
                   data-guid="${element.GlobalId}"
                   value="${element.Material || ''}">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input"
                   data-guid="${element.GlobalId}"
                   data-phase="ConstructionCosts"
                   value="${element.ConstructionCost || ''}">
        </td>
        <!-- ... autres coûts ... -->
        <td>
            <input type="number" class="form-control form-control-sm lifespan-input"
                   data-guid="${element.GlobalId}"
                   value="${element.Lifespan || ''}">
        </td>
    `;
    
    // Attacher les gestionnaires d'événements
    row.querySelectorAll('.cost-input').forEach(input => {
        input.addEventListener('change', handleCostChange);
    });
    
    return row;
}
```

### 3. Modification d'un coût (handleCostChange)

**Frontend** (main.js ligne 283-330):
```javascript
async function handleCostChange(event) {
    const input = event.target;
    const guid = input.dataset.guid;      // Ex: "0tA4DSHd50le6Ov9Yu0I9X"
    const phase = input.dataset.phase;    // Ex: "ConstructionCosts"
    const cost = input.value;             // Ex: "800"
    
    console.log('handleCostChange:', { guid, phase, cost });
    
    const payload = [{ 
        guid, 
        category: phase,  // ⚠️ Note: 'category', pas 'phase'
        cost: parseFloat(cost) || 0 
    }];
    
    const response = await fetch('/update-costs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    if (response.ok) {
        input.classList.add('is-valid');
        setTimeout(() => input.classList.remove('is-valid'), 2000);
    } else {
        input.classList.add('is-invalid');
        const error = await response.json();
        alert(`Erreur: ${error.error}`);
    }
}
```

**Backend** (app.py ligne 241-330):
```python
@app.route('/update-costs', methods=['POST'])
def update_costs():
    """
    Met à jour les coûts pour un ou plusieurs éléments
    
    Format attendu:
    [
        {
            "guid": "0tA4DSHd50le6Ov9Yu0I9X",
            "category": "ConstructionCosts",
            "cost": 800.0
        }
    ]
    """
    try:
        data = request.get_json()
        
        # Validation du format
        if not isinstance(data, list):
            return jsonify({'error': 'Format invalide, liste attendue'}), 400
        
        successful_updates = []
        failed_updates = []
        
        for item in data:
            # Validation des champs
            guid = item.get('guid')
            cost = item.get('cost')
            category = item.get('category')
            
            if not guid or cost is None or not category:
                failed_updates.append({
                    'guid': guid,
                    'reason': 'Champs manquants'
                })
                continue
            
            # Créer l'URI de l'élément (avec encodage)
            element_uri = create_element_uri(guid)
            
            try:
                # Appeler la fonction de mise à jour dans sparql_client
                update_cost_for_element(element_uri, float(cost), category)
                successful_updates.append(guid)
                
            except requests.HTTPError as e:
                failed_updates.append({
                    'guid': guid,
                    'reason': f'Erreur GraphDB: {str(e)}'
                })
        
        if failed_updates:
            return jsonify({
                'error': 'Certains coûts non mis à jour',
                'successful': successful_updates,
                'failed': failed_updates
            }), 500
        else:
            return jsonify({
                'success': True,
                'message': f'{len(successful_updates)} coûts mis à jour',
                'updated': successful_updates
            }), 200
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

### 4. Mise à jour dans GraphDB (update_cost_for_element)

**Déjà documenté dans la section "Création d'un coût"**

---

## PROBLÈMES IDENTIFIÉS DANS LE CODE ACTUEL

### 1. ❌ `relink_costs_to_years()` non implémentée
- Fonction appelée après chaque mise à jour de coût
- Actuellement vide (ligne 926-935 de app.py)
- **Impact**: Les coûts ne sont PAS liés aux années du projet
- **Conséquence**: Les calculs WLC utilisent les formules simplifiées sans distribution temporelle

### 2. ❓ Propriété `wlc:ForDate` non utilisée
- **Définie dans l'ontologie** (WLCONTO.ttl ligne 39-42):
  ```turtle
  :ForDate rdf:type owl:ObjectProperty ;
           rdfs:domain :Costs ;
           rdfs:range :Time .
  ```
- Devrait lier chaque instance de coût à une instance de `wlc:Time`
- **Jamais assignée dans le code actuel**
- **Hypothèse**: Cette fonctionnalité était prévue mais pas implémentée
- **Structure attendue**:
  ```turtle
  <coût_instance> wlc:ForDate <http://example.com/year/2025> .
  <http://example.com/year/2025> a wlc:Time ;
                                  wlc:hasDate "2025"^^xsd:decimal .

### 3. ⚠️ Coûts stockés de manière simplifiée
- Actuellement: 1 instance de coût par catégorie par élément
- Attendu: Multiple instances pour les coûts récurrents (opération/maintenance)
- **Impact**: Les coûts annuels sont calculés à la volée, pas stockés

### 4. ✅ Calcul WLC fonctionne SANS distribution temporelle
- Les formules de calcul (lignes 2500-2700) fonctionnent correctement
- Elles multiplient les coûts annuels par la durée de vie
- **Mais**: Pas de modélisation fine année par année

---

## RECOMMANDATIONS POUR L'AVENIR

### 1. Implémenter `relink_costs_to_years()`

**Pseudo-code suggéré**:
```python
def relink_costs_to_years():
    # 1. Récupérer durée de vie projet
    project_lifespan = get_project_lifespan()  # Ex: 50 ans
    
    # 2. Pour chaque élément avec coûts d'opération
    elements_with_operation_costs = query_elements_with_operation_costs()
    
    for element in elements_with_operation_costs:
        operation_cost = element['annual_operation_cost']
        element_uri = element['uri']
        
        # 3. Créer une instance de coût pour chaque année
        for year in range(1, project_lifespan):  # Année 1 à 49
            cost_uri = f"{element_uri}/cost/operation_year_{year}"
            
            insert_query = f"""
            INSERT DATA {{
                <{cost_uri}> a wlc:OperationCosts ;
                    wlc:hasCostValue "{operation_cost}"^^xsd:double ;
                    wlc:ForDate "{year}"^^xsd:integer ;
                    wlc:appliesTo <{element_uri}> .
            }}
            """
            execute_sparql_update(insert_query)
    
    # 4. Même logique pour maintenance et remplacements
```

### 2. Sauvegardes automatiques
- Créer un script de backup GraphDB avant modifications
- Utiliser GraphDB export RDF automatique
- Versionner les données critiques

### 3. Tests unitaires
- Créer un environnement de test séparé
- Ne jamais tester sur les données de production
- Utiliser GraphDB `test_repository` distinct

### 4. Logs et traçabilité
- Logger toutes les modifications de coûts
- Tracer qui a modifié quoi et quand
- Permettre l'annulation (undo)

---

Date de cette analyse: 24 novembre 2024
Auteur: Assistant IA (après erreurs et apprentissage)

