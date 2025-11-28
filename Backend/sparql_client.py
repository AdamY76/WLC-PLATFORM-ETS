import requests
import json
from config import GRAPHDB_REPO
import time

headers_query = {"Accept": "application/sparql-results+json"}
UPDATE_ENDPOINT = GRAPHDB_REPO.rstrip('/') + '/statements'

def test_connection():
    query = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"
    response = requests.post(GRAPHDB_REPO, data={"query": query}, headers=headers_query)
    return "OK" if response.status_code == 200 else f"Erreur {response.status_code}: {response.text}"

def get_classes():
    query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?uri ?label WHERE {
  { ?uri rdf:type owl:Class } UNION { ?uri rdf:type rdfs:Class }
  FILTER(STRSTARTS(STR(?uri), "http://"))
  OPTIONAL { ?uri rdfs:label ?label }
}
"""
    res_exp = requests.post(
        GRAPHDB_REPO,
        data={"query": query, "infer": "false"},
        headers=headers_query
    )
    res_exp.raise_for_status()
    exp_uris = {b["uri"]["value"] for b in res_exp.json()["results"]["bindings"]}
    res_all = requests.post(
        GRAPHDB_REPO,
        data={"query": query, "infer": "true"},
        headers=headers_query
    )
    res_all.raise_for_status()
    bindings = res_all.json()["results"]["bindings"]
    classes = []
    for b in bindings:
        uri = b["uri"]["value"]
        label = b.get("label", {}).get("value", "")
        classes.append({"uri": uri, "label": label, "inferred": uri not in exp_uris})
    return classes

def get_class_details(class_uri):
    def run(q, infer=True):
        data = {"query": q, "infer": "true" if infer else "false"}
        r = requests.post(GRAPHDB_REPO, data=data, headers=headers_query)
        r.raise_for_status()
        return r.json()["results"]["bindings"]
    def get_literal(bindings, key):
        for b in bindings:
            if key in b:
                return b[key]["value"]
        return ""
    meta_q = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?comment WHERE {{
  OPTIONAL {{ <{class_uri}> rdfs:label ?label }}
  OPTIONAL {{ <{class_uri}> rdfs:comment ?comment }}
}}
"""
    meta = run(meta_q)
    label = get_literal(meta, "label")
    comment = get_literal(meta, "comment")
    sup_q = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?super WHERE {{ <{class_uri}> rdfs:subClassOf ?super }}
"""
    superclasses = [b["super"]["value"].split('#')[-1] for b in run(sup_q)]
    sub_q = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?sub WHERE {{ ?sub rdfs:subClassOf <{class_uri}> }}
"""
    subclasses = [b["sub"]["value"].split('#')[-1] for b in run(sub_q)]
    prop_q = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?prop WHERE {{ ?prop rdfs:domain <{class_uri}> }}
"""
    properties = [b["prop"]["value"].split('#')[-1] for b in run(prop_q)]
    inst_q = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?inst WHERE {{ ?inst rdf:type <{class_uri}> }} LIMIT 10
"""
    exp_bind = run(inst_q, infer=False)
    exp_uris = {b["inst"]["value"] for b in exp_bind}
    all_bind = run(inst_q, infer=True)
    instances = [{"uri": b["inst"]["value"], "inferred": b["inst"]["value"] not in exp_uris} for b in all_bind]
    return {"label": label, "comment": comment, "superclasses": superclasses, "subclasses": subclasses, "properties": properties, "instances": instances}

def get_instance_details(instance_uri):
    query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?prop ?val ?valLabel WHERE {{
  <{instance_uri}> ?prop ?val .
  OPTIONAL {{ ?val rdfs:label ?valLabel }}
}}
"""
    r = requests.post(GRAPHDB_REPO, data={"query": query}, headers=headers_query)
    r.raise_for_status()
    bindings = r.json()["results"]["bindings"]
    details = []
    for b in bindings:
        prop = b["prop"]["value"].split('#')[-1]
        if "valLabel" in b and b["valLabel"]["value"]:
            val = b["valLabel"]["value"]
        else:
            val = b["val"]["value"].split('#')[-1] if b["val"]["type"] == "uri" else b["val"]["value"]
        details.append({"property": prop, "value": val})
    return details

def insert_element(uri):
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
INSERT DATA {{ <{uri}> a wlc:Element . }}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def insert_denomination(uri, denomination):
    safe_denomination = json.dumps(denomination)
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
INSERT DATA {{
  <{uri}> wlc:hasDenomination {safe_denomination} .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def insert_uniformat_code(uri, code):
    safe_code = json.dumps(code)
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
INSERT DATA {{
  <{uri}> wlc:hasUniformatCode {safe_code} .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def insert_uniformat_description(uri, description):
    safe_description = json.dumps(description)
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
INSERT DATA {{
  <{uri}> wlc:hasUniformatDescription {safe_description} .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def insert_material(uri, material):
    safe_mat = json.dumps(material)
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
INSERT DATA {{
  <{uri}> wlc:hasIfcMaterial {safe_mat} .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def insert_ifc_class(uri, ifc_class):
    """
    Insère la classe IFC comme lien vers l'ontologie IFC4 de buildingSMART
    Ex: ifc_class="IfcWall" -> lien vers ifc:IfcWall
    """
    # Créer l'URI IFC4 buildingSMART (déjà chargé dans GraphDB)
    ifc_class_uri = f"https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#{ifc_class}"
    
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

INSERT DATA {{
  <{uri}> wlc:hasIfcClass <{ifc_class_uri}> ;
          rdf:type <{ifc_class_uri}> .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def update_cost_for_element(uri, cost, category):
    import uuid
    
    # ÉTAPE 1: Supprimer les anciens coûts de cette catégorie
    delete_old = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
DELETE {{
  <{uri}> wlc:hasCost ?oldCost .
  ?oldCost ?prop ?value .
}}
WHERE {{
  <{uri}> wlc:hasCost ?oldCost .
  ?oldCost a wlc:{category} .
  ?oldCost ?prop ?value .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": delete_old})
    r.raise_for_status()
    
    # ÉTAPE 2: Créer la nouvelle instance
    cost_uri = f"{uri}/cost/{category.lower()}_{uuid.uuid4().hex}"
    insert_new = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {{
  <{cost_uri}> a wlc:{category}, wlc:Costs ;
      wlc:hasCostValue "{cost}"^^xsd:double ;
      wlc:appliesTo <{uri}> .
  <{uri}> wlc:hasCost <{cost_uri}> .
}}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": insert_new})
    r.raise_for_status()

def update_material_for_element(uri, material):
    safe_material = json.dumps(material)
    update = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
DELETE {{ <{uri}> wlc:hasIfcMaterial ?oldMaterial . }}
INSERT {{ <{uri}> wlc:hasIfcMaterial {safe_material} . }}
WHERE  {{ OPTIONAL {{ <{uri}> wlc:hasIfcMaterial ?oldMaterial }} }}
"""
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def query_graphdb(sparql_query):
    response = requests.post(GRAPHDB_REPO, data={"query": sparql_query}, headers=headers_query)
    response.raise_for_status()
    results = response.json()["results"]["bindings"]
    return [{k: v["value"] for k, v in r.items()} for r in results]

def query_ask_graphdb(sparql_ask_query):
    """Exécute une requête SPARQL ASK et retourne True/False"""
    response = requests.post(GRAPHDB_REPO, data={"query": sparql_ask_query}, headers=headers_query)
    response.raise_for_status()
    return response.json().get("boolean", False)

def update_graphdb(sparql_update):
    """Exécute une requête SPARQL UPDATE (INSERT, DELETE, etc.)"""
    response = requests.post(UPDATE_ENDPOINT, data={"update": sparql_update})
    response.raise_for_status()
    return response

def clear_instances():
    """
    Vide l'ontologie en supprimant uniquement les instances IFC (VERSION OPTIMISÉE)
    Préserve les classes et propriétés de l'ontologie.
    
    GAIN: 5-100x plus rapide que la suppression individuelle
    
    Returns:
        tuple: (success: bool, message: str)
    """
    print("🗑️ VIDANGE OPTIMISÉE - Début du nettoyage...")
    start_time = time.time()
    
    try:
        print("   🧹 Suppression des instances (préservation de l'ontologie)...")
        
        # Requête optimisée : supprime uniquement les instances, pas les classes
        optimized_delete = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        DELETE {
            ?s ?p ?o .
        }
        WHERE {
            ?s ?p ?o .
            FILTER(
                STRSTARTS(STR(?s), "http://example.com/ifc#") ||
                STRSTARTS(STR(?s), "http://example.com/ifc/group#") ||
                STRSTARTS(STR(?s), "http://example.com/test#") ||
                STRSTARTS(STR(?s), "http://example.com/cost/") ||
                STRSTARTS(STR(?s), "http://example.com/lifespan/") ||
                STRSTARTS(STR(?s), "http://example.com/year/") ||
                STRSTARTS(STR(?s), "http://example.com/stakeholder/")
            )
        }
        """
        
        r = requests.post(UPDATE_ENDPOINT, data={"update": optimized_delete})
        r.raise_for_status()
        
        elapsed_time = time.time() - start_time
        message = f"Vidange optimisée réussie en {elapsed_time:.2f}s"
        print(f"✅ {message}")
        return True, message
        
    except Exception as e:
        print(f"❌ Erreur lors de la vidange: {e}")
        print("🔄 Tentative avec méthode alternative...")
        
        try:
            # Méthode alternative plus simple
            simple_delete = """
            DELETE {
                ?s ?p ?o .
            }
WHERE {
  ?s ?p ?o .
                FILTER(STRSTARTS(STR(?s), "http://example.com/"))
}
"""
            r = requests.post(UPDATE_ENDPOINT, data={"update": simple_delete})
            r.raise_for_status()
            
            elapsed_time = time.time() - start_time
            message = f"Vidange alternative réussie en {elapsed_time:.2f}s"
            print(f"✅ {message}")
            return True, message
            
        except Exception as e2:
            elapsed_time = time.time() - start_time
            message = f"Erreur lors de la vidange: {e2}"
            print(f"❌ {message}")
            return False, message

def insert_excel_cost(guid, cost):
    uri = f"http://example.com/ifc#{guid}"
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    DELETE {{ <{uri}> wlc:hasCostValue ?oldValue . }}
    INSERT {{ <{uri}> wlc:hasCostValue "{cost}" . }}
    WHERE  {{ OPTIONAL {{ <{uri}> wlc:hasCostValue ?oldValue }} }}
    """
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()


def insert_global_id(uri, guid):
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    INSERT DATA {{
      <{uri}> wlc:globalId "{guid}" .
    }}
    """
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def insert_typed_cost_instance(uri, cost, category):
    import uuid
    
    # ÉTAPE 1: Supprimer les anciens coûts de cette catégorie pour éviter les doublons
    delete_old = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    DELETE {{
      <{uri}> wlc:hasCost ?oldCost .
      ?oldCost ?prop ?value .
    }}
    WHERE {{
      <{uri}> wlc:hasCost ?oldCost .
      ?oldCost a wlc:{category} .
      ?oldCost ?prop ?value .
    }}
    """
    r = requests.post(UPDATE_ENDPOINT, data={"update": delete_old})
    r.raise_for_status()
    
    # ÉTAPE 2: Créer la nouvelle instance
    cost_uri = f"{uri}/cost/{category.lower()}_{uuid.uuid4().hex}"
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    INSERT DATA {{
      <{cost_uri}> a wlc:{category}, wlc:Costs ;
        wlc:hasCostValue "{cost}"^^xsd:double ;
        wlc:appliesTo <{uri}> .
      <{uri}> wlc:hasCost <{cost_uri}> .
    }}
    """
    r = requests.post(UPDATE_ENDPOINT, data={"update": update})
    r.raise_for_status()

def verify_cost_mapping_integrity():
    """
    Vérifie l'intégrité du mapping des coûts dans l'ontologie.
    Retourne un rapport de cohérence.
    """
    # Vérifier les doublons de coûts par élément et catégorie
    sparql_duplicates = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?element ?category (COUNT(?cost) as ?count)
    WHERE {
      ?element wlc:hasCost ?cost .
      ?cost a ?category .
      FILTER(?category IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
    }
    GROUP BY ?element ?category
    HAVING (COUNT(?cost) > 1)
    """
    
    # Vérifier les coûts sans liaison ForDate
    sparql_orphaned = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?cost ?category
    WHERE {
      ?cost a ?category .
      ?cost a wlc:Costs .
      FILTER NOT EXISTS { ?cost wlc:ForDate ?year }
      FILTER(?category IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
    }
    """
    
    # Vérifier les classes de coûts utilisées
    sparql_classes = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT DISTINCT ?category (COUNT(?cost) as ?count)
    WHERE {
      ?cost a ?category .
      ?cost a wlc:Costs .
    }
    GROUP BY ?category
    ORDER BY ?category
    """
    
    duplicates = query_graphdb(sparql_duplicates)
    orphaned = query_graphdb(sparql_orphaned)
    classes = query_graphdb(sparql_classes)
    
    return {
        "duplicates": len(duplicates),
        "duplicate_details": duplicates,
        "orphaned_costs": len(orphaned),
        "orphaned_details": orphaned,
        "cost_classes": classes,
        "integrity_ok": len(duplicates) == 0 and len(orphaned) == 0
    }

def batch_insert_elements(elements_data):
    """
    Insère tous les éléments et leurs propriétés en une seule requête SPARQL batch.
    
    Args:
        elements_data: Liste de dictionnaires avec les clés:
            - uri: URI de l'élément
            - guid: GlobalId
            - name: Dénomination
            - uniformat_code: Code Uniformat (optionnel)
            - uniformat_desc: Description Uniformat (optionnel)
            - material: Matériau (optionnel)
            - ifc_class: Classe IFC (optionnel)
    
    Returns:
        bool: True si succès, False sinon
    """
    if not elements_data:
        return True
    
    # Construire la requête SPARQL batch
    insert_statements = []
    
    for elem in elements_data:
        uri = elem['uri']
        
        # Élément de base
        insert_statements.append(f"<{uri}> a wlc:Element .")
        
        # GlobalId (obligatoire)
        if elem.get('guid'):
            safe_guid = json.dumps(elem['guid'])
            insert_statements.append(f"<{uri}> wlc:hasGlobalId {safe_guid} .")
        
        # Dénomination
        if elem.get('name'):
            safe_name = json.dumps(elem['name'])
            insert_statements.append(f"<{uri}> wlc:hasDenomination {safe_name} .")
        
        # Code Uniformat
        if elem.get('uniformat_code'):
            safe_code = json.dumps(elem['uniformat_code'])
            insert_statements.append(f"<{uri}> wlc:hasUniformatCode {safe_code} .")
        
        # Description Uniformat
        if elem.get('uniformat_desc'):
            safe_desc = json.dumps(elem['uniformat_desc'])
            insert_statements.append(f"<{uri}> wlc:hasUniformatDescription {safe_desc} .")
        
        # Matériau
        if elem.get('material'):
            safe_material = json.dumps(elem['material'])
            insert_statements.append(f"<{uri}> wlc:hasIfcMaterial {safe_material} .")
        
        # Classe IFC
        if elem.get('ifc_class'):
            safe_class = json.dumps(elem['ifc_class'])
            insert_statements.append(f"<{uri}> wlc:hasIfcClass {safe_class} .")
    
    # Construire la requête finale
    batch_query = f"""
PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
INSERT DATA {{
    {' '.join(insert_statements)}
}}
"""
    
    try:
        # Exécuter la requête batch
        r = requests.post(UPDATE_ENDPOINT, data={"update": batch_query})
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Erreur lors de l'insertion batch: {e}")
        return False

def batch_insert_elements_chunked(elements_data, chunk_size=100):
    """
    Insère les éléments par chunks pour éviter les requêtes trop volumineuses.
    
    Args:
        elements_data: Liste des données d'éléments
        chunk_size: Taille des chunks (défaut: 100)
    
    Returns:
        tuple: (succès, nombre_traités, erreurs)
    """
    total_elements = len(elements_data)
    processed = 0
    errors = []
    
    print(f"🚀 Insertion batch de {total_elements} éléments par chunks de {chunk_size}...")
    
    for i in range(0, total_elements, chunk_size):
        chunk = elements_data[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        total_chunks = (total_elements + chunk_size - 1) // chunk_size
        
        print(f"   📦 Chunk {chunk_num}/{total_chunks} ({len(chunk)} éléments)...")
        
        success = batch_insert_elements(chunk)
        if success:
            processed += len(chunk)
            print(f"   ✅ Chunk {chunk_num} inséré avec succès")
        else:
            errors.append(f"Erreur chunk {chunk_num}")
            print(f"   ❌ Erreur chunk {chunk_num}")
    
    print(f"🎯 Résultat: {processed}/{total_elements} éléments insérés")
    return processed == total_elements, processed, errors

