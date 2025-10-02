# Architecture Complète de la Plateforme WLC

## Vue d'Ensemble

La Plateforme WLC (Whole Life Cost) est une application web full-stack qui utilise une ontologie RDF (WLCONTO) pour gérer et analyser les coûts globaux des projets de construction selon la norme ISO 15686-5.

## Architecture Générale

```mermaid
graph TB
    subgraph "Frontend - Interface Web"
        UI[Interface HTML/CSS/JS]
        UIT[Onglets Navigation]
        UIC[Composants Interactifs]
        UIV[Visualisations Chart.js]
    end
    
    subgraph "Backend - Serveur Flask"
        API[API REST Flask]
        IFC[Processeur IFC]
        CALC[Calculateur WLC]
        SPARQL[Client SPARQL]
    end
    
    subgraph "Base de Connaissances"
        GRAPHDB[(GraphDB)]
        ONT[Ontologie WLCONTO]
        RDF[Données RDF/SPARQL]
    end
    
    subgraph "Données Externes"
        IFCFILE[Fichiers IFC]
        EXCEL[Fichiers Excel]
        EXPORT[Exports/Rapports]
    end
    
    UI --> API
    API --> SPARQL
    SPARQL --> GRAPHDB
    GRAPHDB --> ONT
    GRAPHDB --> RDF
    IFC --> IFCFILE
    API --> EXCEL
    API --> EXPORT
    
    style GRAPHDB fill:#e1f5fe
    style ONT fill:#f3e5f5
    style API fill:#e8f5e8
    style UI fill:#fff3e0
```

## Diagramme de Séquence - Processus Principal WLC

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend
    participant A as API Flask
    participant S as SPARQL Client
    participant G as GraphDB
    participant O as Ontologie WLCONTO
    
    Note over U,O: Phase 1: Chargement Initial
    U->>F: Accès interface
    F->>A: GET /ping
    A->>S: test_connection()
    S->>G: SPARQL SELECT ?s ?p ?o LIMIT 1
    G-->>S: Statut connexion
    S-->>A: OK/Erreur
    A-->>F: {"status": "OK"}
    F-->>U: Badge "Connecté"
    
    Note over U,O: Phase 2: Import IFC
    U->>F: Upload fichier IFC
    F->>A: POST /upload-ifc-temp
    A->>A: Stockage temporaire ifc_storage
    A-->>F: {"success": true, "filename": "..."}
    
    U->>F: Clic "Parser vers ontologie"
    F->>A: POST /parse-ifc
    A->>A: ifcopenshell.open(tmp_file)
    A->>A: extract_uniformat_props()
    A->>S: insert_element(uri)
    S->>G: INSERT DATA {...}
    G->>O: Création instances Element
    A->>S: insert_global_id(), insert_material()
    S->>G: INSERT DATA propriétés
    G->>O: Mise à jour propriétés
    A-->>F: {"elements": [...]}
    F-->>U: Tableau éléments IFC
    
    Note over U,O: Phase 3: Gestion Coûts
    U->>F: Import Excel coûts
    F->>A: POST /upload-phase-costs
    A->>A: pandas.read_excel()
    A->>S: insert_typed_cost_instance()
    S->>G: INSERT DATA instances ConstructionCosts
    G->>O: Création coûts typés
    
    U->>F: Modification coût cellule
    F->>A: POST /update-costs
    A->>S: update_cost_for_element()
    S->>G: DELETE ancien coût + INSERT nouveau
    G->>O: Mise à jour atomique
    A-->>F: {"success": true}
    F-->>U: Feedback visuel succès
    
    Note over U,O: Phase 4: Configuration Durées
    U->>F: Définition durée projet
    F->>A: POST /set-project-lifespan
    A->>S: Création instances LifeSpan + Time
    S->>G: INSERT DATA durées projet
    G->>O: Structure temporelle
    
    U->>F: Import/modification durées éléments
    F->>A: POST /update-lifespan
    A->>A: set_element_duration()
    A->>S: Création LifeSpan élément
    S->>G: INSERT instances durées
    G->>O: Durées vie éléments
    A->>A: link_costs_to_years()
    A->>S: Liaison coûts ↔ années
    S->>G: INSERT ForDate relations
    G->>O: Répartition temporelle
    
    Note over U,O: Phase 5: Taux d'Actualisation
    U->>F: Configuration taux
    F->>A: POST /set-global-discount-rate
    A->>S: Création instances DiscountRate
    S->>G: INSERT taux par année
    G->>O: Structure actualisation
    
    Note over U,O: Phase 6: Calcul WLC
    U->>F: Clic "Calculer WLC"
    F->>A: POST /calculate-wlc
    A->>A: calculate_wlc_dynamically()
    A->>S: Requêtes coûts actualisés
    S->>G: SPARQL requêtes complexes
    G->>O: Récupération données
    A->>S: Création DiscountedCosts
    S->>G: INSERT coûts actualisés
    G->>O: Instances coûts actualisés
    A->>A: Calcul WLC total
    A->>S: Création WholeLifeCost
    S->>G: INSERT WLC final
    G->>O: Résultat WLC
    A-->>F: {"wlc_total": 123456.78, "breakdown": {...}}
    F-->>U: Affichage WLC + graphiques
    
    Note over U,O: Phase 7: Analyses Avancées
    U->>F: Analyses WLC intelligentes
    F->>A: GET /analyze-cost-impact
    A->>S: Requêtes SPARQL analytiques
    S->>G: SELECT avec agrégations
    G->>O: Données pour analyses
    A-->>F: {"top_elements": [...]}
    F-->>U: Tableaux + graphiques analyses
```

## Architecture de l'Ontologie WLCONTO

```mermaid
graph TD
    subgraph "Classes Principales"
        PROJ[Project/Asset]
        ELEM[Element]
        COSTS[Costs]
        TIME[Time]
        LIFE[LifeSpan]
        WLC[WholeLifeCost]
        DISC[DiscountRate]
    end
    
    subgraph "Classes de Coûts Spécialisées"
        CONST[ConstructionCosts]
        OPER[OperationCosts]
        MAINT[MaintenanceCosts]
        EOL[EndOfLifeCosts]
    end
    
    subgraph "Classes de Coûts Actualisés"
        DCONST[DiscountedConstructionCosts]
        DOPER[DiscountedOperationCosts]
        DMAINT[DiscountedMaintenanceCosts]
        DEOL[DiscountedEndOfLifeCosts]
        DCOSTS[DiscountedCosts]
    end
    
    subgraph "Propriétés d'Objet"
        hasCosts
        ForDate
        hasDiscountRate
        hasDuration
        isDiscountedValueOf
        isSumOf
        hasWLC
    end
    
    subgraph "Propriétés de Données"
        hasCostValue
        hasDiscountedCostValue
        hasTotalValue
        hasDate
        hasRateValue
        hasDenomination
    end
    
    PROJ -->|hasCosts| COSTS
    COSTS -->|ForDate| TIME
    TIME -->|hasDiscountRate| DISC
    PROJ -->|hasDuration| LIFE
    PROJ -->|hasWLC| WLC
    
    COSTS --> CONST
    COSTS --> OPER
    COSTS --> MAINT
    COSTS --> EOL
    
    DCOSTS --> DCONST
    DCOSTS --> DOPER
    DCOSTS --> DMAINT
    DCOSTS --> DEOL
    
    DCOSTS -->|isDiscountedValueOf| COSTS
    WLC -->|isSumOf| DCOSTS
    
    COSTS -->|hasCostValue| hasCostValue
    DCOSTS -->|hasDiscountedCostValue| hasDiscountedCostValue
    WLC -->|hasTotalValue| hasTotalValue
    TIME -->|hasDate| hasDate
    DISC -->|hasRateValue| hasRateValue
    PROJ -->|hasDenomination| hasDenomination
    
    style PROJ fill:#e3f2fd
    style COSTS fill:#f3e5f5
    style DCOSTS fill:#e8f5e8
    style WLC fill:#fff3e0
    style TIME fill:#fce4ec
```

## Diagramme de Classes - Structure Backend

```mermaid
classDiagram
    class FlaskApp {
        +app: Flask
        +ifc_storage: dict
        +routes: dict
        +run()
    }
    
    class IFCProcessor {
        +extract_uniformat_props()
        +extract_material()
        +parse_ifc()
        +enrich_ifc_with_wlc_data()
    }
    
    class SPARQLClient {
        +GRAPHDB_REPO: str
        +UPDATE_ENDPOINT: str
        +test_connection()
        +query_graphdb()
        +insert_element()
        +update_cost_for_element()
        +insert_typed_cost_instance()
    }
    
    class WLCCalculator {
        +calculate_wlc_dynamically()
        +link_costs_to_years()
        +set_element_duration()
        +create_lifespan_and_time_instances()
    }
    
    class AnalysisEngine {
        +analyze_cost_impact()
        +analyze_frequent_replacements()
        +analyze_high_maintenance()
        +analyze_high_operation()
        +analyze_cost_by_phase()
    }
    
    class DiscountRateManager {
        +set_global_discount_rate()
        +set_year_discount_rate()
        +get_discount_rates()
        +bulk_set_discount_rates()
    }
    
    class DataExporter {
        +export_costs_excel()
        +export_analysis_results()
        +download_enriched_ifc()
    }
    
    FlaskApp --> IFCProcessor
    FlaskApp --> SPARQLClient
    FlaskApp --> WLCCalculator
    FlaskApp --> AnalysisEngine
    FlaskApp --> DiscountRateManager
    FlaskApp --> DataExporter
    
    SPARQLClient --> GraphDB : SPARQL queries
    WLCCalculator --> SPARQLClient
    AnalysisEngine --> SPARQLClient
    DiscountRateManager --> SPARQLClient
    IFCProcessor --> SPARQLClient
```

## Diagramme de Composants - Frontend

```mermaid
graph TB
    subgraph "Frontend Architecture"
        subgraph "Interface Layers"
            HTML[index.html]
            CSS[main.css]
            JS[main.js]
        end
        
        subgraph "JavaScript Modules"
            MAIN[Application Principale]
            NOTIF[notifications.js]
            UPLOAD[fileUpload.js]
            TABLE[dataTable.js]
        end
        
        subgraph "UI Components"
            NAV[Navigation Tabs]
            IFC_TAB[Onglet IFC]
            ELEM_TAB[Onglet Éléments]
            COST_TAB[Onglet Coûts]
            LIFE_TAB[Onglet Durées]
            SUMM_TAB[Onglet Synthèse]
            ANAL_TAB[Onglet Analyses]
        end
        
        subgraph "Data Management"
            STATE[appState]
            ELEMENTS[elements[]]
            DISCOUNTS[discountRates[]]
            CHARTS[Chart.js Instances]
        end
        
        subgraph "API Communication"
            FETCH[Fetch API]
            REST[REST Endpoints]
            JSON[JSON Responses]
        end
    end
    
    HTML --> CSS
    HTML --> JS
    JS --> MAIN
    MAIN --> NOTIF
    MAIN --> UPLOAD
    MAIN --> TABLE
    
    NAV --> IFC_TAB
    NAV --> ELEM_TAB
    NAV --> COST_TAB
    NAV --> LIFE_TAB
    NAV --> SUMM_TAB
    NAV --> ANAL_TAB
    
    MAIN --> STATE
    STATE --> ELEMENTS
    STATE --> DISCOUNTS
    MAIN --> CHARTS
    
    MAIN --> FETCH
    FETCH --> REST
    REST --> JSON
    
    style MAIN fill:#e3f2fd
    style STATE fill:#f3e5f5
    style REST fill:#e8f5e8
```

## Flux de Données Principal

```mermaid
flowchart TD
    Start([Démarrage Application]) --> Load[Chargement Interface]
    Load --> Health[Vérification Santé Système]
    Health --> InitData[Chargement Données Initiales]
    
    InitData --> IFCFlow{Processus IFC}
    IFCFlow --> Upload[Upload Fichier IFC]
    Upload --> Parse[Parsing → Ontologie]
    Parse --> Elements[Affichage Éléments]
    
    Elements --> CostFlow{Gestion Coûts}
    CostFlow --> ImportCosts[Import Excel Coûts]
    CostFlow --> EditCosts[Édition Inline Coûts]
    ImportCosts --> CostUpdate[Mise à jour Ontologie]
    EditCosts --> CostUpdate
    
    CostUpdate --> LifeFlow{Durées de Vie}
    LifeFlow --> ProjectLife[Durée Projet]
    LifeFlow --> ElementLife[Durées Éléments]
    ProjectLife --> TimeStructure[Structure Temporelle]
    ElementLife --> TimeStructure
    
    TimeStructure --> DiscountFlow{Taux Actualisation}
    DiscountFlow --> GlobalRate[Taux Global]
    DiscountFlow --> YearRates[Taux par Année]
    GlobalRate --> RateStructure[Structure Actualisation]
    YearRates --> RateStructure
    
    RateStructure --> WLCCalc[Calcul WLC]
    WLCCalc --> DiscountedCosts[Coûts Actualisés]
    DiscountedCosts --> WLCTotal[WLC Total]
    WLCTotal --> Visualization[Graphiques & Analyses]
    
    Visualization --> Analysis{Analyses Avancées}
    Analysis --> CostImpact[Impact Coûts]
    Analysis --> Maintenance[Maintenance Élevée]
    Analysis --> Operations[Opérations Élevées]
    Analysis --> Replacements[Remplacements Fréquents]
    Analysis --> PhaseDistrib[Distribution Phases]
    
    CostImpact --> Export[Export Résultats]
    Maintenance --> Export
    Operations --> Export
    Replacements --> Export
    PhaseDistrib --> Export
    
    Export --> End([Fin Processus])
    
    style Start fill:#e8f5e8
    style WLCCalc fill:#fff3e0
    style Export fill:#f3e5f5
    style End fill:#e3f2fd
```

## Modèle de Données RDF - Instances Types

### Exemple d'Instance Complète dans l'Ontologie

```turtle
# Élément IFC
<http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl> a wlc:Element ;
    wlc:hasGlobalId "0M6O00Hb9CnBJN1ZE6l$Yl" ;
    wlc:hasDenomination "Mur porteur béton" ;
    wlc:hasUniformatCode "B2010" ;
    wlc:hasUniformatDescription "Bearing Walls" ;
    wlc:hasIfcMaterial "Concrete" ;
    wlc:hasDuration <http://example.com/project/lifespan/element_50years> ;
    wlc:hasCost <http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl/cost/constructioncosts_abc123> ,
                <http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl/cost/maintenancecosts_def456> ,
                <http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl/cost/endoflifecosts_ghi789> .

# Coût de Construction
<http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl/cost/constructioncosts_abc123> 
    a wlc:ConstructionCosts, wlc:Costs ;
    wlc:hasCostValue "15000.0"^^xsd:double ;
    wlc:appliesTo <http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl> ;
    wlc:ForDate <http://example.com/project/lifespan/Year0> .

# Coût de Maintenance (répétition tous les 50 ans)
<http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl/cost/maintenancecosts_def456> 
    a wlc:MaintenanceCosts, wlc:Costs ;
    wlc:hasCostValue "3000.0"^^xsd:double ;
    wlc:appliesTo <http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl> ;
    wlc:ForDate <http://example.com/project/lifespan/Year50> .

# Taux d'Actualisation Année 50
<http://example.com/project/discountrate/Year50> a wlc:DiscountRate ;
    wlc:hasRateValue "0.04"^^xsd:double ;
    wlc:ForYear <http://example.com/project/lifespan/Year50> .

# Coût Actualisé Résultant
<http://example.com/project/discounted/maintenancecosts_def456_discounted> 
    a wlc:DiscountedMaintenanceCosts, wlc:DiscountedCosts ;
    wlc:hasDiscountedCostValue "421.93"^^xsd:double ;
    wlc:isDiscountedValueOf <http://example.com/ifc#0M6O00Hb9CnBJN1ZE6l$Yl/cost/maintenancecosts_def456> ;
    wlc:ForDate <http://example.com/project/lifespan/Year50> .

# WLC Final du Projet
<http://example.com/project/wlc/final> a wlc:WholeLifeCost ;
    wlc:hasTotalValue "8547231.45"^^xsd:double ;
    wlc:isSumOf <http://example.com/project/discounted/constructioncosts_sum> ,
                <http://example.com/project/discounted/operationcosts_sum> ,
                <http://example.com/project/discounted/maintenancecosts_sum> ,
                <http://example.com/project/discounted/endoflifecosts_sum> .
```

## Requêtes SPARQL Clés

### 1. Requête WLC Total
```sparql
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>

SELECT (SUM(?discountedValue) AS ?wlcTotal) WHERE {
    ?discountedCost a wlc:DiscountedCosts ;
                   wlc:hasDiscountedCostValue ?discountedValue .
}
```

### 2. Analyse Impact Coûts par Élément
```sparql
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>

SELECT ?element ?denomination ?uniformat 
       (SUM(?constructionCost) AS ?totalConstruction)
       (SUM(?operationCost) AS ?totalOperation)
       (SUM(?maintenanceCost) AS ?totalMaintenance)
       (SUM(?endOfLifeCost) AS ?totalEndOfLife)
       ((?totalConstruction + ?totalOperation + ?totalMaintenance + ?totalEndOfLife) AS ?totalCost)
WHERE {
    ?element a wlc:Element ;
             wlc:hasDenomination ?denomination ;
             wlc:hasUniformatCode ?uniformat .
    
    OPTIONAL {
        ?element wlc:hasCost ?cc .
        ?cc a wlc:ConstructionCosts ;
            wlc:hasCostValue ?constructionCost .
    }
    
    OPTIONAL {
        ?element wlc:hasCost ?oc .
        ?oc a wlc:OperationCosts ;
            wlc:hasCostValue ?operationCost .
    }
    
    OPTIONAL {
        ?element wlc:hasCost ?mc .
        ?mc a wlc:MaintenanceCosts ;
            wlc:hasCostValue ?maintenanceCost .
    }
    
    OPTIONAL {
        ?element wlc:hasCost ?eol .
        ?eol a wlc:EndOfLifeCosts ;
            wlc:hasCostValue ?endOfLifeCost .
    }
}
GROUP BY ?element ?denomination ?uniformat
ORDER BY DESC(?totalCost)
LIMIT 20
```

### 3. Éléments avec Remplacements Fréquents
```sparql
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>

SELECT ?element ?denomination ?uniformat ?lifespanYears 
       (COUNT(?maintenanceCost) AS ?maintenanceCount)
       (SUM(?maintenanceCost) AS ?totalMaintenance)
WHERE {
    ?element a wlc:Element ;
             wlc:hasDenomination ?denomination ;
             wlc:hasUniformatCode ?uniformat ;
             wlc:hasDuration ?lifespan .
    
    ?lifespan wlc:hasLifeSpanValue ?lifespanYears .
    
    ?element wlc:hasCost ?mc .
    ?mc a wlc:MaintenanceCosts ;
        wlc:hasCostValue ?maintenanceCost .
    
    FILTER(?lifespanYears <= 25)
}
GROUP BY ?element ?denomination ?uniformat ?lifespanYears
HAVING (?maintenanceCount > 0)
ORDER BY ?lifespanYears DESC(?totalMaintenance)
```

## Points d'Extension et Évolutivité

### 1. Règles SWRL Potentielles
- Calcul automatique de coûts actualisés
- Validation de cohérence des données
- Inférence de durées de vie selon matériaux

### 2. Nouvelles Analyses
- Optimisation temporelle des maintenances
- Analyse de sensibilité aux taux d'actualisation
- Comparaisons de scénarios

### 3. Intégrations Futures
- BIM 360 / Autodesk Construction Cloud
- Bases de données de coûts nationales
- Outils de simulation énergétique

### 4. Améliorer Performances
- Cache Redis pour requêtes fréquentes
- Indexation GraphDB optimisée
- Pagination des résultats volumineux

## Conclusion

Cette architecture permet une gestion complète et sémantique du WLC en s'appuyant sur une ontologie formelle. La séparation claire entre interface, logique métier et base de connaissances facilite la maintenance et l'évolutivité du système. 