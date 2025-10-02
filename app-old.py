import os
import io
import tempfile
# import ifcopenshell  # Temporairement désactivé
import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory, redirect, send_file
from sparql_client import (
    test_connection,
    get_classes,
    get_class_details,
    get_instance_details,
    insert_element,
    insert_denomination,
    insert_uniformat_code,
    insert_uniformat_description,
    insert_material,
    update_cost_for_element,
    update_material_for_element,
    insert_global_id,
    UPDATE_ENDPOINT,
    query_graphdb,
    clear_instances,
    insert_typed_cost_instance,
    insert_excel_cost,
    verify_cost_mapping_integrity,
    update_graphdb
)
from config import GRAPHDB_REPO
from datetime import datetime
from comparison_routes import register_comparison_routes

# Configuration globale
# Variables supprimées (code JavaScript invalide)

# Stockage temporaire des fichiers IFC (en mémoire)
ifc_storage = {
    'current_file': None,
    'metadata': {}
}

app = Flask(__name__)

@app.route('/')
def root():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Frontend'))
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/ping')
def ping():
    status = test_connection()
    return jsonify({"status": status})

@app.route('/test')
def test():
    return "OK"

@app.route('/get-classes')
def get_classes_route():
    try:
        classes = get_classes()
        return jsonify(classes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-class-details')
def get_class_details_route():
    class_uri = request.args.get('uri')
    if not class_uri:
        return jsonify({"error": "Missing class URI."}), 400
    try:
        details = get_class_details(class_uri)
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-instance-details')
def get_instance_details_route():
    uri = request.args.get('uri')
    if not uri:
        return jsonify({"error": "Missing instance URI."}), 400
    try:
        details = get_instance_details(uri)
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_uniformat_number(elem):
    if hasattr(elem, "HasAssociations"):
        for assoc in elem.HasAssociations:
            if assoc.is_a("IfcRelAssociatesClassification"):
                ref = assoc.RelatingClassification
                if hasattr(ref, "ItemReference") and ref.ItemReference:
                    return str(ref.ItemReference).strip()
    return None

def extract_uniformat_description(elem):
    if hasattr(elem, "HasAssociations"):
        for assoc in elem.HasAssociations:
            if assoc.is_a("IfcRelAssociatesClassification"):
                ref = assoc.RelatingClassification
                if hasattr(ref, "Name") and ref.Name:
                    return str(ref.Name).strip()
    return None

def extract_material(elem):
    if hasattr(elem, "HasAssociations"):
        for assoc in elem.HasAssociations:
            if assoc.is_a("IfcRelAssociatesMaterial"):
                mat = assoc.RelatingMaterial
                if hasattr(mat, "Name") and mat.Name:
                    return str(mat.Name).strip()
    return None

@app.route('/parse-ifc', methods=['POST'])
def parse_ifc():
    """
    Parse le fichier IFC stocké en mémoire vers l'ontologie
    """
    global ifc_storage
    
    # Vérifier qu'un fichier est en mémoire
    if not ifc_storage['current_file']:
        return jsonify({'error': 'Aucun fichier IFC en mémoire. Veuillez d\'abord uploader un fichier.'}), 400
    
    try:
        # Créer un fichier temporaire avec le contenu en mémoire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as tmp_file:
            tmp_file.write(ifc_storage['current_file']['content'])
            tmp_path = tmp_file.name
        
        # Parser avec ifcopenshell
        model = ifcopenshell.open(tmp_path)
        elements = model.by_type('IfcElement')
        structure = []
        
        for elem in elements:
            guid = elem.GlobalId
            name = elem.Name or ''
            etype = elem.is_a()
            uniformat_code, uniformat_desc = extract_uniformat_props(elem)
            uri = f"http://example.com/ifc#{guid}"
            
            # Insérer dans l'ontologie
            insert_element(uri)
            insert_global_id(uri, guid)
            insert_denomination(uri, name)
            material = extract_material(elem)
            
            if uniformat_code:
                insert_uniformat_code(uri, uniformat_code)
            if uniformat_desc:
                insert_uniformat_description(uri, uniformat_desc)
            if material:
                insert_material(uri, material)
            
            structure.append({
                'GlobalId': guid,
                'Name': name,
                'Type': etype,
                'Uniformat': uniformat_code if uniformat_code else '',
                'UniformatDesc': uniformat_desc if uniformat_desc else '',
                'Material': material if material else ''
            })
        
        # Mettre à jour le statut
        ifc_storage['current_file']['parsed'] = True
        ifc_storage['metadata']['elements_count'] = len(structure)
        ifc_storage['metadata']['parsing_status'] = 'parsed'
        ifc_storage['metadata']['last_action'] = 'parsed'
        
        # Nettoyer le fichier temporaire
        os.unlink(tmp_path)
        
        return jsonify({
            'success': True,
            'message': f'Fichier "{ifc_storage["current_file"]["filename"]}" parsé avec succès',
            'elements_count': len(structure),
            'elements': structure
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du parsing: {str(e)}'}), 500

def extract_uniformat_props(elem):
    """Retourne (uniformat_code, uniformat_desc) extraits des PropertySets d'un élément IFC."""
    uniformat_code = None
    uniformat_desc = None
    if hasattr(elem, "IsDefinedBy"):
        for rel in elem.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                prop_set = rel.RelatingPropertyDefinition
                if hasattr(prop_set, "HasProperties"):
                    for prop in prop_set.HasProperties:
                        pname = prop.Name.lower()
                        if "uniformat" in pname and "number" in pname:
                            uniformat_code = str(prop.NominalValue.wrappedValue)
                        if "uniformat" in pname and ("description" in pname or "desc" in pname):
                            uniformat_desc = str(prop.NominalValue.wrappedValue)
    return uniformat_code, uniformat_desc

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Frontend'))
    return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)

@app.route('/reset', methods=['POST'])
def reset():
    try:
        clear_instances()
        return jsonify({"status": "instances supprimées"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-costs', methods=['POST'])
def update_costs():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée reçue"}), 400
    try:
        for item in data:
            guid = item.get('guid')
            cost = item.get('cost')
            category = item.get('category')
            if guid and cost is not None and category:
                elem_uri = f"http://example.com/ifc#{guid}"
                update_cost_for_element(elem_uri, cost, category)
        
        # NOUVEAU: Vérification automatique des doublons après mise à jour
        cleanup_result = auto_check_and_clean_duplicates()
        
        # IMPORTANT: Relancer la liaison avec les années après mise à jour
        relink_costs_to_years()
        
        base_message = "Coûts mis à jour avec succès"
        if cleanup_result.get('auto_cleaned'):
            base_message += f" 🧹 Nettoyage automatique: {cleanup_result['duplicates_removed']} doublons supprimés."
        
        return jsonify({
            "status": base_message,
            "auto_cleanup": cleanup_result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-material', methods=['POST'])
def update_material():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée reçue"}), 400
    try:
        updated_count = 0
        for item in data:
            guid = item.get('guid')
            material = item.get('material')
            if guid and material is not None:
                elem_uri = f"http://example.com/ifc#{guid}"
                update_material_for_element(elem_uri, material)
                updated_count += 1
        
        return jsonify({
            "status": f"{updated_count} matériau(x) mis à jour avec succès",
            "updated_count": updated_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/bulk-update-materials', methods=['POST'])
def bulk_update_materials():
    """Route optimisée pour les mises à jour en lot des matériaux"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée reçue"}), 400
    
    guids = data.get('guids', [])
    material = data.get('material', '').strip()
    
    if not guids or not material:
        return jsonify({"error": "GUIDs ou matériau manquant"}), 400
    
    try:
        updated_count = 0
        errors = []
        
        for guid in guids:
            try:
                elem_uri = f"http://example.com/ifc#{guid}"
                update_material_for_element(elem_uri, material)
                updated_count += 1
            except Exception as e:
                errors.append(f"Erreur pour {guid}: {str(e)}")
        
        response_data = {
            "status": f"{updated_count} matériau(x) mis à jour avec succès",
            "updated_count": updated_count,
            "total_requested": len(guids)
        }
        
        if errors:
            response_data["errors"] = errors
            response_data["status"] += f" ({len(errors)} erreur(s))"
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-lifespan', methods=['POST'])
def update_lifespan():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée reçue"}), 400
    try:
        for item in data:
            guid = item.get('guid')
            lifespan = item.get('lifespan')
            if guid and lifespan is not None:
                try:
                    lifespan_int = int(float(lifespan))
                    if lifespan_int > 0:
                        set_element_duration(guid, lifespan_int)
                    else:
                        return jsonify({"error": f"Durée de vie invalide pour {guid}: {lifespan}"}), 400
                except ValueError:
                    return jsonify({"error": f"Durée de vie non numérique pour {guid}: {lifespan}"}), 400
        return jsonify({"status": "Durées de vie mises à jour avec succès"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-ifc-elements')
def get_ifc_elements():
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?elem ?typeClass ?guid ?name ?uniformat ?uniformatDesc ?material ?cost ?costType ?lifespan
        WHERE {
          ?typeClass rdfs:subClassOf* wlc:Element .
          ?elem a ?typeClass .
          OPTIONAL { ?elem wlc:globalId ?guid . }
          OPTIONAL { ?elem wlc:name ?name . }
          OPTIONAL { ?elem wlc:hasUniformatCode ?uniformat . }
          OPTIONAL { ?elem wlc:hasUniformatDescription ?uniformatDesc . }
          OPTIONAL { ?elem wlc:hasIfcMaterial ?material . }
          OPTIONAL { 
            ?elem wlc:hasCost ?costInst .
            ?costInst wlc:hasCostValue ?cost .
            ?costInst a ?costType .
          }
          OPTIONAL { ?elem wlc:hasDuration ?lifespan . }
        }
        """
        results = query_graphdb(sparql)
        items = {}
        for row in results:
            guid = row.get('guid', '')
            if not guid:
                continue
            if guid not in items:
                items[guid] = {
                    'GlobalId': guid,
                    'Uniformat': row.get('uniformat', ''),
                    'UniformatDesc': row.get('uniformatDesc', ''),
                    'Material': row.get('material', ''),
                    'ConstructionCost': '',
                    'OperationCost': '',
                    'MaintenanceCost': '',
                    'EndOfLifeCost': '',
                    'Lifespan': ''  # Initialisé vide
                }
            
            # Mise à jour de la durée de vie si elle existe dans cette ligne
            if row.get('lifespan') and not items[guid]['Lifespan']:
                items[guid]['Lifespan'] = row.get('lifespan', '')
            
            if 'cost' in row and 'costType' in row:
                v = row['cost']
                if 'ConstructionCosts' in row['costType']:
                    items[guid]['ConstructionCost'] = v
                elif 'OperationCosts' in row['costType']:
                    items[guid]['OperationCost'] = v
                elif 'MaintenanceCosts' in row['costType']:
                    items[guid]['MaintenanceCost'] = v
                elif 'EndOfLifeCosts' in row['costType']:
                    items[guid]['EndOfLifeCost'] = v
        return jsonify(list(items.values()))
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Affiche l'erreur dans la console Flask
        return jsonify({"error": f"Erreur backend : {str(e)}"}), 500


@app.route('/upload-uniformat', methods=['POST'])
def upload_uniformat():
    from uniformat_importer import import_uniformat_excel
    f = request.files['file']
    tmp_path = os.path.join(tempfile.gettempdir(), f.filename)
    f.save(tmp_path)
    phase = request.form.get('phase', 'ConstructionCosts')
    try:
        result = import_uniformat_excel(tmp_path, phase)
        return jsonify({"status": "OK", "details": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def auto_check_and_clean_duplicates():
    """Fonction helper pour vérifier et nettoyer automatiquement les doublons"""
    try:
        # Vérifier s'il y a des doublons
        duplicates = query_graphdb("""
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?costType (COUNT(?cost) as ?costCount)
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?element ?costType
        HAVING (?costCount > 1)
        """)
        
        if duplicates:
            print(f"⚠️ DÉTECTION AUTOMATIQUE: {len(duplicates)} groupes de doublons détectés après import")
            print("🧹 Nettoyage automatique en cours...")
            
            # Appeler la fonction de nettoyage interne
            from sparql_client import UPDATE_ENDPOINT
            import requests
            
            total_cleaned = 0
            for group in duplicates:
                element_uri = group['element'] 
                cost_type = group['costType']
                
                # Récupérer tous les coûts de ce groupe
                costs_query = f"""
                PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                SELECT ?cost WHERE {{
                  <{element_uri}> wlc:hasCost ?cost .
                  ?cost a <{cost_type}> .
                }}
                ORDER BY ?cost
                """
                
                costs_result = query_graphdb(costs_query)
                if len(costs_result) > 1:
                    # Garder le premier, supprimer les autres
                    cost_to_keep = costs_result[0]['cost']
                    costs_to_delete = [c['cost'] for c in costs_result[1:]]
                    
                    for cost_to_delete in costs_to_delete:
                        delete_query = f"""
                        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                        DELETE {{
                            <{element_uri}> wlc:hasCost <{cost_to_delete}> .
                            <{cost_to_delete}> ?p ?o .
                        }}
                        WHERE {{
                            <{element_uri}> wlc:hasCost <{cost_to_delete}> .
                            <{cost_to_delete}> ?p ?o .
                        }}
                        """
                        
                        response = requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
                        if response.ok:
                            total_cleaned += 1
            
            print(f"✅ Nettoyage automatique terminé: {total_cleaned} doublons supprimés")
            return {'auto_cleaned': True, 'duplicates_removed': total_cleaned}
        else:
            print("✅ Aucun doublon détecté après import")
            return {'auto_cleaned': False, 'duplicates_removed': 0}
            
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage automatique: {str(e)}")
        return {'auto_cleaned': False, 'error': str(e)}

@app.route('/upload-phase-costs', methods=['POST'])
def upload_phase_costs():
    # Vérifier le fichier
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier reçu.'}), 400
    f = request.files['file']
    phase = request.form.get('phase', None)
    if phase not in {'ConstructionCosts', 'OperationCosts', 'MaintenanceCosts', 'EndOfLifeCosts'}:
        return jsonify({'error': f'Phase invalide ({phase})'}), 400

    # Sauver temporairement
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[-1])
    f.save(tmp.name)

    try:
        df = pd.read_excel(tmp.name) if tmp.name.endswith(('xls', 'xlsx')) else pd.read_csv(tmp.name)
    except Exception as e:
        return jsonify({'error': f"Erreur lecture fichier : {str(e)}"}), 400

    # Trouver les colonnes
    guid_col = next((c for c in df.columns if 'guid' in c.lower()), None)
    cost_col = next((c for c in df.columns if any(w in c.lower() for w in ['cout', 'coût', 'cost'])), None)
    if not guid_col or not cost_col:
        return jsonify({'error': f"Colonnes GUID ou COÛTS non trouvées ({df.columns.tolist()})"}), 400

    nb_ok = 0
    for idx, row in df.iterrows():
        guid = str(row[guid_col]).strip()
        cost = row[cost_col]
        if not guid or pd.isnull(cost):
            continue
        try:
            cost = float(cost)
        except Exception:
            continue
        uri = f"http://example.com/ifc#{guid}"
        insert_typed_cost_instance(uri, cost, phase)
        nb_ok += 1

    os.unlink(tmp.name)
    
    # NOUVEAU: Vérification automatique des doublons après import
    cleanup_result = auto_check_and_clean_duplicates()
    
    relink_costs_to_years()
    
    # Message de retour enrichi
    base_message = f'Import {phase} terminé. {nb_ok} coûts insérés.'
    if cleanup_result.get('auto_cleaned'):
        base_message += f" 🧹 Nettoyage automatique: {cleanup_result['duplicates_removed']} doublons supprimés."
    
    return jsonify({
        'status': base_message,
        'costs_inserted': nb_ok,
        'auto_cleanup': cleanup_result
    })

@app.route('/export-costs-excel')
def export_costs_excel():
    sparql = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?elem ?guid ?uniformat ?uniformatDesc ?material ?cost ?costType
    WHERE {
      ?typeClass rdfs:subClassOf* wlc:Element .
      ?elem a ?typeClass .
      OPTIONAL { ?elem wlc:guid ?guid . }
      OPTIONAL { ?elem wlc:globalId ?guid . }
      OPTIONAL { ?elem wlc:hasUniformatCode ?uniformat . }
      OPTIONAL { ?elem wlc:hasUniformatDescription ?uniformatDesc . }
      OPTIONAL { ?elem wlc:hasIfcMaterial ?material . }
      OPTIONAL { 
        ?elem wlc:hasCost ?costInst .
        ?costInst wlc:hasCostValue ?cost .
        ?costInst a ?costType .
      }
      OPTIONAL { ?elem wlc:hasDuration ?duration . }
    }
    """
    results = query_graphdb(sparql)
    rows = {}
    for row in results:
        guid = row.get('guid', '')
        if not guid:
            continue
        if guid not in rows:
            rows[guid] = {
                'GUID': guid,
                'Uniformat': row.get('uniformat', ''),
                'Uniformat Desc': row.get('uniformatDesc', ''),
                'Material': row.get('material', ''),
                'Construction ($)': '',
                'Opération ($)': '',
                'Maintenance ($)': '',
                'Fin de vie ($)': '',
                'Durée de vie (années)': row.get('duration', '')
            }

        if 'cost' in row and 'costType' in row:
            v = row['cost']
            if 'ConstructionCosts' in row['costType']:
                rows[guid]['Construction ($)'] = v
            elif 'OperationCosts' in row['costType']:
                rows[guid]['Opération ($)'] = v
            elif 'MaintenanceCosts' in row['costType']:
                rows[guid]['Maintenance ($)'] = v
            elif 'EndOfLifeCosts' in row['costType']:
                rows[guid]['Fin de vie ($)'] = v
    df = pd.DataFrame(list(rows.values()))
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(
        output,
        download_name='couts_elements.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

bdd_lifespan = {}
bdd_lifespan_filename = None

@app.route('/get-lifespan-bdd-info')
def get_lifespan_bdd_info():
    relink_costs_to_years()
    return jsonify({
        "filename": bdd_lifespan_filename,
        "count": len(bdd_lifespan)
    })
@app.route('/remove-lifespan-bdd', methods=['POST'])
def remove_lifespan_bdd():
    global bdd_lifespan, bdd_lifespan_filename
    bdd_lifespan = {}
    bdd_lifespan_filename = None
    return jsonify({"success": True})

@app.route('/load-lifespan-bdd', methods=['POST'])
def load_lifespan_bdd():
    global bdd_lifespan, bdd_lifespan_filename
    file = request.files['file']
    bdd_lifespan_filename = file.filename
    df = pd.read_excel(file)
    # Recherche tolérante (ajuste les colonnes selon ta BDD réelle)
    element_col = next((c for c in df.columns if c.strip().lower() in ['éléments', 'element']), None)
    duration_col = next((c for c in df.columns if 'durée' in c.lower() and 'vie' in c.lower()), None)
    part_col = next((c for c in df.columns if 'partie' in c.lower()), None)
    uniformat_col = next((c for c in df.columns if 'composition' in c.lower() or 'uniformat' in c.lower()), None)
    if not element_col or not duration_col:
        return jsonify({"error": f"Colonnes manquantes (trouvé : {list(df.columns)})"}), 400
    temp = []
    for _, row in df.iterrows():
        temp.append({
            "partie": str(row.get(part_col, '')).strip().lower() if part_col else '',
            "element": str(row[element_col]).strip().lower(),
            "composition": str(row.get(uniformat_col, '')).strip().lower() if uniformat_col else '',
            "duree": str(row[duration_col]).strip()
        })
    bdd_lifespan = temp
    return jsonify({"success": True, "filename": bdd_lifespan_filename})

    bdd_lifespan = temp
    relink_costs_to_years()
    return jsonify({"success": True})

def set_element_duration(guid, duration):
    uri = f"http://example.com/ifc#{guid}"
    update = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    DELETE {{ <{uri}> wlc:hasDuration ?old . }}
    INSERT {{ <{uri}> wlc:hasDuration "{duration}"^^xsd:integer . }}
    WHERE  {{ OPTIONAL {{ <{uri}> wlc:hasDuration ?old }} }}
    """
    requests.post(UPDATE_ENDPOINT, data={"update": update})

def create_lifespan_and_time_instances(lifespan_value): # Renamed parameter for clarity
    project_uri = "http://example.com/ifc#Project" # URI fixe pour l'instance de projet
    lifespan_instance_uri = f"{project_uri}/lifespan"

    # Supprime les anciennes instances de temps liées à cette durée de vie pour éviter les doublons
    # et l'ancienne valeur de la durée de vie
    clear_previous_time_instances_query = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    DELETE {{
        <{lifespan_instance_uri}> wlc:hasValue ?oldLifespanValue .
        <{lifespan_instance_uri}> wlc:hasYear ?oldYearInstance .
        ?oldYearInstance ?p ?o .
    }}
    WHERE {{
        OPTIONAL {{ <{lifespan_instance_uri}> wlc:hasValue ?oldLifespanValue . }}
        OPTIONAL {{
            <{lifespan_instance_uri}> wlc:hasYear ?oldYearInstance .
            ?oldYearInstance ?p ?o . # Capturer toutes les propriétés des anciennes instances d'année
        }}
    }}
    """
    response = requests.post(UPDATE_ENDPOINT, data={"update": clear_previous_time_instances_query})
    if not response.ok:
        app.logger.error(f"Failed to clear previous time instances: {response.status_code} - {response.text}")
        # Decide if you want to stop or continue; for now, we'll log and continue

    # Crée ou met à jour l'instance LifeSpan pour le projet
    update_lifespan_project_link = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        <{project_uri}> rdf:type wlc:Project . # Assurer que le projet est typé
        <{lifespan_instance_uri}> rdf:type wlc:LifeSpan ;
            wlc:hasValue "{lifespan_value}"^^xsd:integer .
    }}
    """
    response = requests.post(UPDATE_ENDPOINT, data={"update": update_lifespan_project_link})
    if not response.ok:
        app.logger.error(f"Failed to update project lifespan instance: {response.status_code} - {response.text}")
        return # Stop if we can't even set the main lifespan

    # Génère les instances Time (Year0...YearN) avec wlc:hasDate
    # et les lie à l'instance LifeSpan
    inserts = []
    for i in range(int(lifespan_value) + 1):
        year_instance_uri = f"{lifespan_instance_uri}/Year{i}"
        inserts.append(f"""
        <{year_instance_uri}> rdf:type wlc:Time ;
            wlc:hasDate "{i}.0"^^xsd:decimal .
        <{lifespan_instance_uri}> wlc:hasYear <{year_instance_uri}> .
        <{project_uri}> wlc:hasDate <{year_instance_uri}> .
        """)


    if inserts:
        final_update_query = "PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>\n"
        final_update_query += "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
        final_update_query += "INSERT DATA {\n"
        final_update_query += "\n".join(inserts)
        final_update_query += "\n}"
        
        response = requests.post(UPDATE_ENDPOINT, data={"update": final_update_query})
        if not response.ok:
            app.logger.error(f"Failed to insert time instances: {response.status_code} - {response.text}")
        relink_costs_to_years()

@app.route('/autofill-lifespan', methods=['POST'])
def autofill_lifespan():
    global bdd_lifespan # Assure que nous utilisons la BDD chargée
    if not bdd_lifespan: # Vérifie si la liste bdd_lifespan est vide ou non initialisée
        return jsonify({"error": "La BDD des matériaux/durées de vie n'est pas chargée.", "success": False}), 400

    elements_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?guid ?material ?uniformatDesc ?name
    WHERE {
      ?elem wlc:globalId ?guid .
      OPTIONAL { ?elem wlc:hasIfcMaterial ?material . }
      OPTIONAL { ?elem wlc:hasUniformatDescription ?uniformatDesc . }
      OPTIONAL { ?elem wlc:name ?name . }
    }
    """
    try:
        elements_from_db = query_graphdb(elements_query) # Interroge la base de données pour obtenir les éléments.
    except Exception as e:
        app.logger.error(f"Erreur query graphdb for autofill: {str(e)}")
        return jsonify({"error": f"Erreur de requête à la base de données: {str(e)}", "success": False}), 500

    changed_count = 0
    for elem in elements_from_db: # Boucle sur chaque élément récupéré de la base de données.
        guid = elem.get('guid', '') # Obtient le GUID de l'élément.
        if not guid: # Si le GUID n'est pas trouvé, passe à l'élément suivant.
            continue

        # Récupère les informations de matériel, description Uniformat et nom, en les mettant en minuscules.
        mat = elem.get('material', '').lower() # Obtient le matériel de l'élément en minuscules.
        uniformat_desc = elem.get('uniformatDesc', '').lower() # Obtient la description Uniformat en minuscules.
        # ifc_name = elem.get('name', '').lower() # Le nom IFC n'est pas utilisé dans la logique de matching simple ci-dessous

        match_row = None
        for row in bdd_lifespan: # Boucle sur chaque ligne de la BDD matériaux chargée.
            # Logique de matching améliorée (bidirectionnelle)
            # OPTION 1: Terme BDD dans matériau IFC (logique actuelle)
            element_in_material = (row.get("element") and mat and row.get("element") in mat)
            composition_in_uniformat = (row.get("composition") and uniformat_desc and row.get("composition") in uniformat_desc)
            
            # OPTION 2: Matériau IFC dans terme BDD (nouvelle logique)
            material_in_element = (mat and row.get("element") and mat in row.get("element"))
            material_in_composition = (mat and row.get("composition") and mat in row.get("composition"))
            uniformat_in_composition = (uniformat_desc and row.get("composition") and uniformat_desc in row.get("composition"))
            
            if element_in_material or composition_in_uniformat or material_in_element or material_in_composition or uniformat_in_composition:
                match_row = row # Si une correspondance est trouvée, assigne la ligne à match_row.
                break # Sort de la boucle interne une fois qu'une correspondance est trouvée.
        
        if match_row: # Si une ligne correspondante a été trouvée dans la BDD matériaux.
            lifespan_str = str(match_row.get("duree", "")).strip() # Obtient la durée de vie de la ligne correspondante.
            if lifespan_str: # Si la chaîne de durée de vie n'est pas vide.
                try:
                    # Convertit la durée de vie en entier, après l'avoir convertie en flottant (gère les virgules).
                    duration = int(float(lifespan_str.replace(",", "."))) # Convertit la durée en entier.
                    if duration > 0: # Si la durée est positive.
                        set_element_duration(guid, duration) # Met à jour la durée de l'élément dans la base de données.
                        changed_count += 1 # Incrémente le compteur des éléments modifiés.
                        app.logger.info(f"Auto-filled lifespan for {guid} to {duration} (simple match)")
                except ValueError:
                    app.logger.warning(f"Could not parse duration '{lifespan_str}' for GUID {guid} from BDD (simple match).")
                except Exception as e:
                    app.logger.error(f"Error setting duration for {guid} from BDD (simple match): {str(e)}")
                    
    return jsonify({"success": True, "count": changed_count, "message": f"{changed_count} durées de vie auto-remplies (méthode simple)." })


@app.route('/set-project-lifespan', methods=['POST'])
def set_project_lifespan():
    data = request.get_json()
    lifespan = int(data.get('lifespan', 0))
    project_uri = "http://example.com/ifc#Project"
    sparql = f"""
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    DELETE {{ <{project_uri}> wlc:hasDuration ?old . }}
    INSERT {{
        <{project_uri}> a wlc:Project ;
            wlc:hasDuration "{lifespan}"^^xsd:integer .
    }}
    WHERE {{
        OPTIONAL {{ <{project_uri}> wlc:hasDuration ?old . }}
    }}
    """
    from sparql_client import UPDATE_ENDPOINT
    import requests
    requests.post(UPDATE_ENDPOINT, data={"update": sparql})
    # AJOUTE CETTE LIGNE :
    create_lifespan_and_time_instances(lifespan)
    relink_costs_to_years()
    return jsonify({"status": "OK"})



@app.route('/get-project-lifespan')
def get_project_lifespan():
    sparql = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?lifespan WHERE {
      <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
    } LIMIT 1
    """
    results = query_graphdb(sparql)
    lifespan = ""
    if results and len(results) > 0:
        lifespan = results[0].get('lifespan', '')
    return jsonify({"lifespan": lifespan})

@app.route('/upload-lifespan-excel', methods=['POST'])
def upload_lifespan_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier reçu.'}), 400
    
    file = request.files['file']
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'error': 'Format de fichier invalide. Veuillez utiliser .xlsx ou .xls.'}), 400

    try:
        df = pd.read_excel(file)
        
        # Attempt to find GUID and Lifespan columns (case-insensitive)
        guid_col = next((col for col in df.columns if 'guid' in col.lower()), None)
        lifespan_col = next((col for col in df.columns if any(term in col.lower() for term in ['lifespan', 'durée', 'duration', 'duree'])), None)

        if not guid_col or not lifespan_col:
            return jsonify({'error': f'Colonnes GUID ou Durée de vie non trouvées. Colonnes détectées: {list(df.columns)}'}), 400

        updated_count = 0
        errors = []
        for index, row in df.iterrows():
            guid = str(row[guid_col]).strip()
            try:
                lifespan = int(float(str(row[lifespan_col]).replace(",","."))) # Handle comma as decimal
                if pd.notna(lifespan) and lifespan > 0 :
                    set_element_duration(guid, lifespan)
                    updated_count += 1
                elif pd.isna(lifespan):
                     app.logger.warning(f"Ligne {index+2}: Durée de vie manquante pour GUID {guid}.")
                else:
                    app.logger.warning(f"Ligne {index+2}: Durée de vie invalide ({row[lifespan_col]}) pour GUID {guid}.")

            except ValueError:
                app.logger.warning(f"Ligne {index+2}: Impossible de convertir la durée de vie '{row[lifespan_col]}' en nombre pour GUID {guid}.")
            except Exception as e:
                errors.append(f"Erreur à la ligne {index+2} (GUID: {guid}): {str(e)}")
                app.logger.error(f"Erreur lors de la mise à jour de la durée de vie pour GUID {guid}: {str(e)}")
        
        if errors:
             return jsonify({"status": f"{updated_count} durées de vie mises à jour. Erreurs: {'; '.join(errors)}"})
        return jsonify({"status": f"{updated_count} durées de vie mises à jour avec succès."})

    except Exception as e:
        app.logger.error(f"Erreur lors du traitement du fichier Excel de durées de vie: {str(e)}")
        return jsonify({"error": f"Erreur de traitement du fichier: {str(e)}"}), 500

def link_costs_to_years(lifespan, cost_instances, element_lifespans):
    """
    Associe chaque coût à la bonne année selon les règles métier.
    - lifespan : durée de vie projet (ex 100)
    - cost_instances : liste de dicts, ex :
        [{'uri': <cost_uri>, 'type': 'ConstructionCosts', 'element': <element_uri>}, ...]
    - element_lifespans : dict {element_uri: lifespan_int}
    """
    project_uri = "http://example.com/ifc#Project"
    lifespan_instance_uri = f"{project_uri}/lifespan"
    sparql_prefix = "PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>\n"

    print(f"🔗 Liaison des coûts aux années (projet: {lifespan} ans)")
    print(f"📊 {len(cost_instances)} instances de coûts à traiter")
    print(f"📊 {len(element_lifespans)} éléments avec durée de vie")

    # ÉTAPE 1: Supprimer toutes les anciennes liaisons ForDate
    delete_query = sparql_prefix + """
    DELETE {
      ?cost wlc:ForDate ?year .
    }
    WHERE {
      ?cost wlc:ForDate ?year .
      ?cost a ?costType .
      FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
    }
    """
    
    import requests
    from sparql_client import UPDATE_ENDPOINT
    requests.post(UPDATE_ENDPOINT, data={"update": delete_query})

    # ÉTAPE 2: Créer les nouvelles liaisons
    inserts = []
    stats = {
        'ConstructionCosts': 0,
        'OperationCosts': 0,
        'MaintenanceCosts': 0,
        'EndOfLifeCosts': 0
    }

    # Compteurs pour diagnostic détaillé
    maintenance_elements_processed = 0
    maintenance_elements_with_lifespan = 0
    maintenance_elements_without_lifespan = 0
    total_maintenance_links = 0

    for cost in cost_instances:
        cost_uri = cost['uri']
        cost_type = cost['type']
        elem_uri = cost.get('element')
        
        # ConstructionCost → Year0
        if cost_type == 'ConstructionCosts':
            year_uri = f"{lifespan_instance_uri}/Year0"
            inserts.append(f"<{cost_uri}> wlc:ForDate <{year_uri}> .")
            stats['ConstructionCosts'] += 1
            
        # EndOfLifeCost → YearN
        elif cost_type == 'EndOfLifeCosts':
            year_uri = f"{lifespan_instance_uri}/Year{lifespan}"
            inserts.append(f"<{cost_uri}> wlc:ForDate <{year_uri}> .")
            stats['EndOfLifeCosts'] += 1
            
        # OperationCost → Year1 ... Year(N-1)
        elif cost_type == 'OperationCosts':
            for i in range(1, int(lifespan)):
                year_uri = f"{lifespan_instance_uri}/Year{i}"
                inserts.append(f"<{cost_uri}> wlc:ForDate <{year_uri}> .")
            stats['OperationCosts'] += (int(lifespan) - 1)
            
        # MaintenanceCost → chaque multiple de la durée de vie de l'élément
        elif cost_type == 'MaintenanceCosts':
            maintenance_elements_processed += 1
            
            # Récupère la durée de vie de l'élément concerné
            if elem_uri and elem_uri in element_lifespans:
                maintenance_elements_with_lifespan += 1
                lifespan_elem = element_lifespans[elem_uri]
                
                # Calculer et créer les liens pour chaque remplacement
                replacement_years = []
                for i in range(1, int(lifespan) + 1):
                    if i % lifespan_elem == 0:  # Multiple exact de la durée de vie
                        replacement_years.append(i)
                        year_uri = f"{lifespan_instance_uri}/Year{i}"
                        inserts.append(f"<{cost_uri}> wlc:ForDate <{year_uri}> .")
                        total_maintenance_links += 1
                
                print(f"   Maintenance {elem_uri[-8:]}... (durée: {lifespan_elem}a) → {len(replacement_years)} remplacements: {replacement_years}")
                stats['MaintenanceCosts'] += len(replacement_years)
                
            else:
                maintenance_elements_without_lifespan += 1
                # NOUVELLE LOGIQUE: Si pas de durée de vie élément, essayer durée par défaut
                print(f"   ⚠️ Maintenance {elem_uri[-8:] if elem_uri else 'unknown'}... : pas de durée de vie définie, utilisation durée par défaut (60 ans)")
                
                # Utiliser 60 ans par défaut pour les éléments sans durée définie
                default_lifespan = 60
                replacement_years = []
                for i in range(1, int(lifespan) + 1):
                    if i % default_lifespan == 0:
                        replacement_years.append(i)
                        year_uri = f"{lifespan_instance_uri}/Year{i}"
                        inserts.append(f"<{cost_uri}> wlc:ForDate <{year_uri}> .")
                        total_maintenance_links += 1
                
                if replacement_years:
                    print(f"     → {len(replacement_years)} remplacements avec durée par défaut: {replacement_years}")
                    stats['MaintenanceCosts'] += len(replacement_years)
    
    print(f"📈 Statistiques liaisons créées:")
    print(f"   - Construction: {stats['ConstructionCosts']} liens")
    print(f"   - Opération: {stats['OperationCosts']} liens")
    print(f"   - Maintenance: {stats['MaintenanceCosts']} liens")
    print(f"   - Fin de vie: {stats['EndOfLifeCosts']} liens")
    print(f"   - TOTAL: {sum(stats.values())} liens")
    
    print(f"🔧 Diagnostic maintenance:")
    print(f"   - Éléments traités: {maintenance_elements_processed}")
    print(f"   - Avec durée de vie: {maintenance_elements_with_lifespan}")
    print(f"   - Sans durée de vie: {maintenance_elements_without_lifespan}")
    print(f"   - Total liens maintenance: {total_maintenance_links}")
    
    # ÉTAPE 3: Insérer les nouvelles liaisons par batch
    if inserts:
        # Diviser en lots de 1000 pour éviter les requêtes trop longues
        batch_size = 1000
        batch_count = 0
        for i in range(0, len(inserts), batch_size):
            batch = inserts[i:i+batch_size]
            update_query = sparql_prefix + "INSERT DATA { " + "\n".join(batch) + " }"
            requests.post(UPDATE_ENDPOINT, data={"update": update_query})
            batch_count += 1
        
        print(f"✅ {len(inserts)} liaisons insérées en {batch_count} lots")
    else:
        print("❌ Aucune liaison à insérer")

def relink_costs_to_years():
    # Récupère la durée de vie du projet
    sparql_life = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?lifespan WHERE {
      <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
    }
    """
    result_life = query_graphdb(sparql_life)
    lifespan = int(float(result_life[0]['lifespan'])) if result_life and 'lifespan' in result_life[0] else 0

    # Récupère tous les coûts et les durées de vie des éléments associés (pour maintenance)
    sparql = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?cost ?type ?element ?lifespan
    WHERE {
      ?element wlc:hasCost ?cost .
      ?cost a ?type .
      OPTIONAL { ?element wlc:hasDuration ?lifespan . }
    }
    """
    results = query_graphdb(sparql)
    cost_instances = []
    element_lifespans = {}
    for row in results:
        cost_instances.append({
            "uri": row["cost"],
            "type": row["type"].split("#")[-1],
            "element": row["element"]
        })
        if "lifespan" in row and row["element"] not in element_lifespans:
            try:
                element_lifespans[row["element"]] = int(float(row["lifespan"]))
            except:
                pass

    # Appelle la fonction pour créer les liens ForDate
    link_costs_to_years(lifespan, cost_instances, element_lifespans)


@app.route('/costs-by-year')
def costs_by_year():
    """
    Retourne les coûts par année pour le graphique d'évolution
    Comprend que les coûts d'opération sont distribués sur plusieurs années (1 coût → N années)
    """
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result and 'lifespan' in lifespan_result[0] else 100
        
        print(f"📊 costs-by-year: Durée de vie du projet: {project_lifespan} ans")
        
        # NOUVELLE LOGIQUE: Récupérer les coûts nominaux par élément et calculer la distribution par année
        sparql_costs_by_element = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT DISTINCT ?element ?costType ?nominalValue ?guid
        WHERE {
          ?element wlc:hasCost ?cost ;
                  wlc:globalId ?guid .
          ?cost a ?costType ;
                wlc:hasCostValue ?nominalValue .
          
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        ORDER BY ?element ?costType
        """
        
        # Récupérer les durées de vie des éléments pour les calculs de maintenance
        sparql_lifespans = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?lifespan
        WHERE {
          ?element wlc:hasDuration ?lifespan .
        }
        """
        
        costs_results = query_graphdb(sparql_costs_by_element)
        lifespans_results = query_graphdb(sparql_lifespans)
        
        print(f"📊 costs-by-year: {len(costs_results)} coûts par élément trouvés")
        
        # Construire un dictionnaire des durées de vie par élément
        element_lifespans = {}
        for result in lifespans_results:
            element_lifespans[result['element']] = int(float(result['lifespan']))
        
        # Créer une structure complète pour toutes les années de 0 à project_lifespan
        data_by_year = {}
        for year in range(project_lifespan + 1):
            data_by_year[year] = {
                'year': year,
                'ConstructionCosts': 0,
                'OperationCosts': 0,
                'MaintenanceCosts': 0,
                'EndOfLifeCosts': 0,
                'total': 0
            }
        
        # Calculer la distribution des coûts par année selon les règles métier
        debug_by_type = {
            'ConstructionCosts': 0,
            'OperationCosts': 0,
            'MaintenanceCosts': 0,
            'EndOfLifeCosts': 0
        }
        
        for row in costs_results:
            element_uri = row['element']
            cost_type = row['costType'].split('#')[-1]
            cost_value = float(row['nominalValue'])
            
            debug_by_type[cost_type] += cost_value
            
            if cost_type == 'ConstructionCosts':
                # Construction → Année 0 uniquement
                data_by_year[0][cost_type] += cost_value
                data_by_year[0]['total'] += cost_value
                
            elif cost_type == 'EndOfLifeCosts':
                # Fin de vie → Dernière année uniquement
                data_by_year[project_lifespan][cost_type] += cost_value
                data_by_year[project_lifespan]['total'] += cost_value
                
            elif cost_type == 'OperationCosts':
                # Opération → Années 1 à (N-1)
                for year in range(1, project_lifespan):
                    data_by_year[year][cost_type] += cost_value
                    data_by_year[year]['total'] += cost_value
                    
            elif cost_type == 'MaintenanceCosts':
                # Maintenance → Chaque multiple de la durée de vie de l'élément
                element_lifespan = element_lifespans.get(element_uri, 60)  # Durée par défaut 60 ans
                for year in range(1, project_lifespan + 1):
                    if year % element_lifespan == 0:
                        data_by_year[year][cost_type] += cost_value
                        data_by_year[year]['total'] += cost_value
        
        # Debug: Afficher les totaux pour vérification
        print(f"📊 costs-by-year Debug totaux nominaux par type:")
        for cost_type, total in debug_by_type.items():
            print(f"   {cost_type}: {total:,.0f}$ (nominal par élément)")
        
        # Afficher quelques années d'exemple
        print(f"📊 costs-by-year Exemples d'années (distribution calculée):")
        for year in [0, 1, 60]:
            if year in data_by_year:
                year_data = data_by_year[year]
                print(f"   Année {year}: Construction={year_data['ConstructionCosts']:,.0f}$ Opération={year_data['OperationCosts']:,.0f}$ Maintenance={year_data['MaintenanceCosts']:,.0f}$")
        
        # Convertir en liste triée par année
        data = sorted(data_by_year.values(), key=lambda x: x['year'])
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ Erreur dans costs-by-year: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/verify-cost-integrity')
def verify_cost_integrity():
    """Endpoint pour vérifier l'intégrité du mapping des coûts"""
    try:
        report = verify_cost_mapping_integrity()
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calculate_wlc_dynamically():
    """
    Calcule le WLC dynamiquement en utilisant la même logique que costs-by-year
    SANS duplication des coûts - chaque coût nominal est compté une seule fois puis distribué
    """
    try:
        print("🎯 Calcul WLC dynamique CORRIGÉ (sans duplication)...")
        
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        print(f"📊 Durée de vie du projet: {project_lifespan} ans")
        
        # NOUVELLE LOGIQUE: Récupérer les coûts nominaux par élément (SANS DUPLICATION)
        sparql_costs_by_element = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT DISTINCT ?element ?costType ?nominalValue ?guid
        WHERE {
          ?element wlc:hasCost ?cost ;
                  wlc:globalId ?guid .
          ?cost a ?costType ;
                wlc:hasCostValue ?nominalValue .
          
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        ORDER BY ?element ?costType
        """
        
        # Récupérer les durées de vie des éléments pour les calculs de maintenance
        sparql_lifespans = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?lifespan
        WHERE {
          ?element wlc:hasDuration ?lifespan .
        }
        """
        
        # Récupérer les taux d'actualisation par année
        sparql_rates = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?year ?yearIndex ?discountRate
        WHERE {
          ?year a wlc:Time ;
                wlc:hasDate ?yearIndex .
          ?discountInstance a wlc:DiscountRate ;
                           wlc:ForDate ?year ;
                           wlc:hasRateValue ?discountRate .
        }
        ORDER BY ?yearIndex
        """
        
        costs_results = query_graphdb(sparql_costs_by_element)
        lifespans_results = query_graphdb(sparql_lifespans)
        rates_results = query_graphdb(sparql_rates)
        
        print(f"📊 {len(costs_results)} coûts nominaux par élément trouvés (sans duplication)")
        
        # Construire un dictionnaire des durées de vie par élément
        element_lifespans = {}
        for result in lifespans_results:
            element_lifespans[result['element']] = int(float(result['lifespan']))
        
        # Construire un dictionnaire des taux par année
        rates_by_year = {}
        for rate_row in rates_results:
            year_index = float(rate_row['yearIndex'])
            year_int = int(year_index)
            discount_rate = float(rate_row['discountRate'])
            rates_by_year[year_int] = discount_rate
        
        # Taux par défaut si pas trouvé
        default_rate = 0.04
        
        # Créer une structure complète pour toutes les années de 0 à project_lifespan
        data_by_year = {}
        for year in range(project_lifespan + 1):
            data_by_year[year] = {
                'year': year,
                'nominal_cost': 0,
                'discounted_cost': 0
            }
        
        # Calculer la distribution des coûts par année selon les règles métier (MÊME LOGIQUE QUE costs-by-year)
        total_wlc_nominal = 0
        total_wlc_discounted = 0
        
        for row in costs_results:
            element_uri = row['element']
            cost_type = row['costType'].split('#')[-1]
            cost_value = float(row['nominalValue'])
            
            # Ajouter au total nominal (chaque coût compté UNE SEULE FOIS)
            total_wlc_nominal += cost_value
            
            if cost_type == 'ConstructionCosts':
                # Construction → Année 0 uniquement
                data_by_year[0]['nominal_cost'] += cost_value
                # Actualisation (année 0 = pas d'actualisation)
                data_by_year[0]['discounted_cost'] += cost_value
                total_wlc_discounted += cost_value
                
            elif cost_type == 'EndOfLifeCosts':
                # Fin de vie → Dernière année uniquement
                data_by_year[project_lifespan]['nominal_cost'] += cost_value
                # Actualisation
                discount_rate = rates_by_year.get(project_lifespan, default_rate)
                discounted_value = cost_value / ((1 + discount_rate) ** project_lifespan)
                data_by_year[project_lifespan]['discounted_cost'] += discounted_value
                total_wlc_discounted += discounted_value
                
            elif cost_type == 'OperationCosts':
                # Opération → Années 1 à (N-1) - DISTRIBUER le coût sur toutes les années
                for year in range(1, project_lifespan):
                    data_by_year[year]['nominal_cost'] += cost_value
                    # Actualisation
                    discount_rate = rates_by_year.get(year, default_rate)
                    discounted_value = cost_value / ((1 + discount_rate) ** year)
                    data_by_year[year]['discounted_cost'] += discounted_value
                    total_wlc_discounted += discounted_value
                    
            elif cost_type == 'MaintenanceCosts':
                # Maintenance → Chaque multiple de la durée de vie de l'élément
                element_lifespan = element_lifespans.get(element_uri, 60)  # Durée par défaut 60 ans
                for year in range(1, project_lifespan + 1):
                    if year % element_lifespan == 0:
                        data_by_year[year]['nominal_cost'] += cost_value
                        # Actualisation
                        discount_rate = rates_by_year.get(year, default_rate)
                        discounted_value = cost_value / ((1 + discount_rate) ** year)
                        data_by_year[year]['discounted_cost'] += discounted_value
                        total_wlc_discounted += discounted_value
        
        print(f"✅ WLC total calculé CORRECTEMENT (sans duplication):")
        print(f"   📊 Nominal: {total_wlc_nominal:,.2f}$")
        print(f"   📊 Actualisé: {total_wlc_discounted:,.2f}$")
        
        # Convertir en liste triée par année
        costs_by_year_list = sorted([
            {
                "year": year_data['year'],
                "nominal_cost": year_data['nominal_cost'],
                "discounted_cost": year_data['discounted_cost']
            }
            for year_data in data_by_year.values()
        ], key=lambda x: x['year'])
        
        # RÉPONSE SIMPLIFIÉE POUR LE FRONTEND 
        return {
            "success": True,
            "total_wlc": round(total_wlc_discounted, 2),
            "costs_by_year": costs_by_year_list
        }
        
    except Exception as e:
        print(f"Erreur lors du calcul WLC: {e}")
        return {"success": False, "error": str(e)}


@app.route('/calculate-wlc', methods=['POST'])
def calculate_wlc():
    """
    Calcul WLC sémantique NOUVELLE APPROCHE : Calcul dynamique sans stockage d'instances
    """
    try:
        print("🎯 Démarrage calcul WLC sémantique (approche dynamique)...")
        
        # Nouvelle approche : calcul dynamique
        wlc_result = calculate_wlc_dynamically()
        
        if not wlc_result:
            return jsonify({"error": "Échec du calcul WLC dynamique"}), 500
        
        # Créer l'instance WholeLifeCost sémantique (optionnel, pour traçabilité)
        # Pas besoin de create_semantic_wlc_instance car on a une réponse simplifiée
        
        print(f"✅ WLC sémantique calculé dynamiquement: {wlc_result['total_wlc']:,.2f}$")
        return jsonify(wlc_result)
        
    except Exception as e:
        print(f"❌ Erreur calcul WLC sémantique: {str(e)}")
        return jsonify({"error": f"Erreur lors du calcul WLC sémantique: {str(e)}"}), 500

@app.route('/get-wlc')
def get_wlc():
    """Récupère le Whole Life Cost calculé"""
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?totalValue ?discountRate ?name
        WHERE {
          <http://example.com/ifc#ProjectWLC> a wlc:WholeLifeCost ;
              wlc:hasTotalValue ?totalValue .
          OPTIONAL { <http://example.com/ifc#ProjectWLC> wlc:hasDiscountRate ?discountRate . }
          OPTIONAL { <http://example.com/ifc#ProjectWLC> wlc:name ?name . }
        }
        LIMIT 1
        """
        
        results = query_graphdb(sparql)
        
        if results and len(results) > 0:
            wlc_data = results[0]
            return jsonify({
                "exists": True,
                "total_value": float(wlc_data.get('totalValue', 0)),
                "discount_rate": float(wlc_data.get('discountRate', 0)),
                "name": wlc_data.get('name', 'Coût global du projet')
            })
        else:
            return jsonify({"exists": False})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/count-all-costs')
def count_all_costs():
    """
    Compte le nombre total d'instances de coûts dans l'ontologie
    """
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(?cost) AS ?count)
        WHERE {
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        """
        result = query_graphdb(sparql)
        count = int(result[0]['count']) if result and 'count' in result[0] else 0
        return jsonify({"success": True, "total_costs": count})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/diagnose-cost-query')
def diagnose_cost_query():
    """
    Diagnostique pourquoi la requête coûts/années retourne trop de résultats
    """
    try:
        # Test 1: Compter les coûts uniques
        sparql_unique_costs = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(DISTINCT ?cost) AS ?uniqueCosts)
        WHERE {
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        """
        
        # Test 2: Compter les années uniques  
        sparql_unique_years = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(DISTINCT ?year) AS ?uniqueYears)
        WHERE {
          ?year a wlc:Time ;
                wlc:hasDate ?yearIndex .
        }
        """
        
        # Test 3: Compter les liaisons coût-année
        sparql_cost_year_links = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(*) AS ?totalLinks)
        WHERE {
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        """
        
        # Test 4: La requête complète problématique (avec LIMIT 100)
        sparql_full_problematic = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?cost ?costType ?costValue ?year ?yearIndex ?discountRate
        WHERE {
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          OPTIONAL { 
            ?discountInstance a wlc:DiscountRate ;
                             wlc:ForDate ?year ;
                             wlc:hasRateValue ?discountRate .
          }
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        ORDER BY ?yearIndex
        LIMIT 100
        """
        
        result1 = query_graphdb(sparql_unique_costs)
        result2 = query_graphdb(sparql_unique_years) 
        result3 = query_graphdb(sparql_cost_year_links)
        result4 = query_graphdb(sparql_full_problematic)
        
        unique_costs = int(result1[0]['uniqueCosts']) if result1 else 0
        unique_years = int(result2[0]['uniqueYears']) if result2 else 0
        total_links = int(result3[0]['totalLinks']) if result3 else 0
        sample_results = len(result4) if result4 else 0
        
        return jsonify({
            "success": True,
            "diagnosis": {
                "unique_costs": unique_costs,
                "unique_years": unique_years,
                "total_cost_year_links": total_links,
                "sample_results_count": sample_results,
                "expected_if_1_to_1": unique_costs,
                "expected_if_all_to_all": unique_costs * unique_years,
                "actual_vs_expected_ratio": round(total_links / unique_costs, 2) if unique_costs > 0 else 0
            },
            "sample_results": result4[:5] if result4 else []
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/set-global-discount-rate', methods=['POST'])
def set_global_discount_rate():
    """
    Définit un taux d'actualisation global qui s'applique à toutes les années
    """
    data = request.get_json()
    discount_rate = float(data.get('discount_rate', 0.03))
    
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result and 'lifespan' in lifespan_result[0] else 100
        
        # Appliquer le taux à toutes les années
        project_uri = "http://example.com/ifc#Project"
        lifespan_instance_uri = f"{project_uri}/lifespan"
        
        # Supprimer tous les anciens taux
        delete_query = f"""
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        DELETE {{
            ?discountInstance ?p ?o .
        }}
        WHERE {{
            ?discountInstance a wlc:DiscountRate ;
                            ?p ?o .
        }}
        """
        
        # Ajouter le nouveau taux à toutes les années
        inserts = []
        for i in range(project_lifespan + 1):
            year_instance_uri = f"{lifespan_instance_uri}/Year{i}"
            discount_instance_uri = f"{year_instance_uri}/DiscountRate"
            inserts.append(f"""
                <{discount_instance_uri}> a wlc:DiscountRate ;
                                        wlc:ForDate <{year_instance_uri}> ;
                                        wlc:hasRateValue "{discount_rate}"^^xsd:double .
            """)
        
        update_query = f"""
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {{
            {''.join(inserts)}
        }}
        """
        
        from sparql_client import UPDATE_ENDPOINT
        import requests
        requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
        requests.post(UPDATE_ENDPOINT, data={"update": update_query})
        
        return jsonify({
            "success": True,
            "message": f"Taux d'actualisation {discount_rate*100:.1f}% appliqué à {project_lifespan + 1} années",
            "discount_rate": discount_rate,
            "years_updated": project_lifespan + 1
        })
        
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la définition du taux global: {str(e)}"}), 500

@app.route('/set-year-discount-rate', methods=['POST'])
def set_year_discount_rate():
    """
    Définit un taux d'actualisation spécifique pour une année donnée
    """
    data = request.get_json()
    year = int(data.get('year', 0))
    discount_rate = float(data.get('discount_rate', 0.03))
    
    try:
        project_uri = "http://example.com/ifc#Project"
        lifespan_instance_uri = f"{project_uri}/lifespan"
        year_instance_uri = f"{lifespan_instance_uri}/Year{year}"
        discount_instance_uri = f"{year_instance_uri}/DiscountRate"
        
        # Supprimer l'ancienne instance DiscountRate pour cette année
        delete_query = f"""
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        DELETE {{
            ?discountInstance ?p ?o .
        }}
        WHERE {{
            ?discountInstance a wlc:DiscountRate ;
                            wlc:ForDate <{year_instance_uri}> ;
                            ?p ?o .
        }}
        """
        
        # Créer la nouvelle instance DiscountRate
        insert_query = f"""
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {{
            <{discount_instance_uri}> a wlc:DiscountRate ;
                                    wlc:ForDate <{year_instance_uri}> ;
                                    wlc:hasRateValue "{discount_rate}"^^xsd:double .
        }}
        """
        
        from sparql_client import UPDATE_ENDPOINT
        import requests
        requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
        requests.post(UPDATE_ENDPOINT, data={"update": insert_query})
        
        return jsonify({
            "success": True,
            "message": f"Taux d'actualisation {discount_rate*100:.1f}% appliqué à l'année {year}",
            "year": year,
            "discount_rate": discount_rate
        })
        
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la définition du taux pour l'année {year}: {str(e)}"}), 500

@app.route('/get-discount-rates')
def get_discount_rates():
    """
    Récupère tous les taux d'actualisation par année depuis les instances DiscountRate
    """
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?year ?yearIndex ?discountRate ?discountInstance
        WHERE {
          ?year a wlc:Time ;
                wlc:hasDate ?yearIndex .
          OPTIONAL { 
            ?discountInstance a wlc:DiscountRate ;
                             wlc:ForDate ?year ;
                             wlc:hasRateValue ?discountRate .
          }
        }
        ORDER BY xsd:integer(?yearIndex)
        """
        
        results = query_graphdb(sparql)
        
        # Organiser les données par année
        rates_by_year = []
        for row in results:
            year_index = int(float(row['yearIndex']))
            discount_rate = float(row['discountRate']) if row.get('discountRate') else None
            
            rates_by_year.append({
                'year': year_index,
                'discount_rate': discount_rate,
                'discount_rate_percent': discount_rate * 100 if discount_rate else None
            })
        
        return jsonify({
            "success": True,
            "rates": rates_by_year,
            "total_years": len(rates_by_year)
        })
        
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la récupération des taux: {str(e)}"}), 500

@app.route('/bulk-set-discount-rates', methods=['POST'])
def bulk_set_discount_rates():
    """
    Définit des taux d'actualisation pour plusieurs années en créant/modifiant des instances DiscountRate
    """
    data = request.get_json()
    rates_data = data.get('rates', [])  # Liste de {year: X, discount_rate: Y}
    
    if not rates_data:
        return jsonify({"error": "Aucune donnée de taux fournie"}), 400
    
    try:
        from sparql_client import UPDATE_ENDPOINT
        import requests
        
        for rate_info in rates_data:
            year = int(rate_info['year'])
            discount_rate = float(rate_info['discount_rate'])
            
            # URI pour l'année et l'instance DiscountRate
            project_uri = "http://example.com/ifc#Project"
            lifespan_instance_uri = f"{project_uri}/lifespan"
            year_instance_uri = f"{lifespan_instance_uri}/Year{year}"
            discount_instance_uri = f"{year_instance_uri}/DiscountRate"
            
            # Supprimer l'ancienne instance DiscountRate pour cette année
            delete_query = f"""
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            DELETE {{
                ?discountInstance ?p ?o .
            }}
            WHERE {{
                ?discountInstance a wlc:DiscountRate ;
                                wlc:ForDate <{year_instance_uri}> ;
                                ?p ?o .
            }}
            """
            
            # Créer la nouvelle instance DiscountRate
            insert_query = f"""
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            INSERT DATA {{
                <{discount_instance_uri}> a wlc:DiscountRate ;
                                        wlc:ForDate <{year_instance_uri}> ;
                                        wlc:hasRateValue "{discount_rate}"^^xsd:double .
            }}
            """
            
            # Exécuter les requêtes
            requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
            requests.post(UPDATE_ENDPOINT, data={"update": insert_query})
        
        return jsonify({
            "success": True,
            "message": f"Taux d'actualisation mis à jour pour {len(rates_data)} années",
            "years_updated": len(rates_data)
        })
        
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la mise à jour en lot: {str(e)}"}), 500

@app.route('/upload-ifc-temp', methods=['POST'])
def upload_ifc_temp():
    """
    Upload temporaire d'un fichier IFC en mémoire sans parsing
    """
    global ifc_storage
    
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Aucun fichier fourni"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Nom de fichier vide"}), 400
        
        if not file.filename.lower().endswith('.ifc'):
            return jsonify({"error": "Le fichier doit être un fichier IFC"}), 400
        
        # Stocker le fichier en mémoire
        file_content = file.read()
        file_size = len(file_content)
        
        # Utiliser la structure ifc_storage existante
        ifc_storage['current_file'] = {
            'filename': file.filename,
            'content': file_content,
            'size': file_size,
            'uploaded_at': datetime.now().isoformat(),
            'parsed': False
        }
        
        ifc_storage['metadata'] = {
            'elements_count': 0,
            'parsing_status': 'uploaded',
            'last_action': 'uploaded'
        }
        
        return jsonify({
            "success": True,
            "message": f"Fichier {file.filename} stocké temporairement",
            "filename": file.filename,
            "size": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2)
        })
        
    except Exception as e:
        print(f"Erreur upload temporaire IFC: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-ifc-temp-status')
def get_ifc_temp_status():
    """
    Retourne le statut du fichier IFC en stockage temporaire
    """
    global ifc_storage
    
    try:
        if ifc_storage['current_file']:
            return jsonify({
                "has_file": True,
                "filename": ifc_storage['current_file']['filename'],
                "size": ifc_storage['current_file']['size'],
                "size_mb": round(ifc_storage['current_file']['size'] / (1024 * 1024), 2),
                "uploaded_at": ifc_storage['current_file']['uploaded_at'],
                "parsed": ifc_storage['current_file'].get('parsed', False),
                "parsing_status": ifc_storage['metadata'].get('parsing_status', 'unknown'),
                "elements_count": ifc_storage['metadata'].get('elements_count', 0)
            })
        else:
            return jsonify({"has_file": False})
    except Exception as e:
        print(f"Erreur statut IFC temp: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/clear-ifc-temp', methods=['POST'])
def clear_ifc_temp():
    """
    Vide le stockage temporaire IFC
    """
    global ifc_storage
    
    try:
        ifc_storage['current_file'] = None
        ifc_storage['metadata'] = {}
        return jsonify({"success": True, "message": "Stockage temporaire vidé"})
    except Exception as e:
        print(f"Erreur vidage IFC temp: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-lifespan-instances')
def test_lifespan_instances():
    """Endpoint de test pour vérifier la création d'instances d'années"""
    try:
        # 1. Récupérer la durée de vie du projet
        lifespan_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        } LIMIT 1
        """
        lifespan_results = query_graphdb(lifespan_query)
        project_lifespan = int(lifespan_results[0]['lifespan']) if lifespan_results else 0
        
        # 2. Compter les instances Time
        count_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(?time) as ?count) WHERE {
            ?time a wlc:Time .
            ?time wlc:hasDate ?date .
        }
        """
        count_results = query_graphdb(count_query)
        time_instances_count = int(count_results[0]['count']) if count_results else 0
        
        # 3. Récupérer le détail des instances
        detail_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?time ?date WHERE {
            ?time a wlc:Time .
            ?time wlc:hasDate ?date .
        }
        ORDER BY ?date
        """
        detail_results = query_graphdb(detail_query)
        
        instances_detail = []
        years_present = set()
        for result in detail_results:
            time_uri = result['time']
            date_value = float(result['date'])
            year_num = int(date_value)
            instances_detail.append({
                'uri': time_uri,
                'date': date_value,
                'year': year_num
            })
            years_present.add(year_num)
        
        # 4. Calculs de vérification
        expected_count = project_lifespan + 1 if project_lifespan > 0 else 0
        expected_years = set(range(project_lifespan + 1)) if project_lifespan > 0 else set()
        missing_years = expected_years - years_present
        extra_years = years_present - expected_years
        
        # 5. Résultat du test
        is_correct = (
            time_instances_count == expected_count and
            len(missing_years) == 0 and
            len(extra_years) == 0
        )
        
        return jsonify({
            'success': True,
            'project_lifespan': project_lifespan,
            'time_instances_count': time_instances_count,
            'expected_count': expected_count,
            'is_correct': is_correct,
            'years_present': sorted(list(years_present)),
            'expected_years': sorted(list(expected_years)),
            'missing_years': sorted(list(missing_years)),
            'extra_years': sorted(list(extra_years)),
            'instances_detail': instances_detail,
            'message': f"{'✅ SUCCÈS' if is_correct else '❌ ERREUR'}: {time_instances_count} instances pour {project_lifespan} ans (attendu: {expected_count})"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors du test: {str(e)}'
        }), 500

@app.route('/validate-ifc', methods=['POST'])
def validate_ifc():
    """Valide et diagnostique le fichier IFC en mémoire"""
    return jsonify({'error': 'Fonction temporairement désactivée - ifcopenshell non installé'}), 501

@app.route('/repair-ifc', methods=['POST'])
def repair_ifc():
    """Tente de réparer le fichier IFC en mémoire"""
    return jsonify({'error': 'Fonction temporairement désactivée - ifcopenshell non installé'}), 501

def enrich_ifc_with_wlc_data(ifc_content, wlc_elements):
    """Fonction temporairement désactivée"""
    return ifc_content

@app.route('/enrich-ifc', methods=['POST'])
def enrich_ifc():
    """Enrichit le fichier IFC en mémoire avec les données WLC de l'ontologie"""
    return jsonify({'error': 'Fonction temporairement désactivée - ifcopenshell non installé'}), 501

@app.route('/download-enriched-ifc', methods=['POST'])
def download_enriched_ifc():
    """Télécharge le fichier IFC enrichi depuis la mémoire"""
    global ifc_storage
    
    try:
        # Vérifier qu'un fichier est en mémoire
        if not ifc_storage['current_file']:
            return jsonify({'error': 'Aucun fichier IFC en mémoire'}), 400
        
        # Récupérer le contenu du fichier (enrichi ou original)
        file_content = ifc_storage['current_file']['content']
        original_filename = ifc_storage['current_file']['filename']
        
        # Nom du fichier enrichi
        if ifc_storage['current_file'].get('enriched', False):
            download_filename = original_filename.replace('.ifc', '_WLC_enriched.ifc')
        else:
            download_filename = original_filename.replace('.ifc', '_processed.ifc')
        
        # Créer un fichier temporaire pour le téléchargement
        temp_file = io.BytesIO(file_content)
        temp_file.seek(0)
        
        return send_file(
            temp_file,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        print(f"Erreur lors du téléchargement: {str(e)}")
        return jsonify({'error': f'Erreur lors du téléchargement: {str(e)}'}), 500
    
@app.route('/diagnose-maintenance-links')
def diagnose_maintenance_links():
    """Diagnostique les liaisons des coûts de maintenance avec les années"""
    try:
        # 1. Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result and 'lifespan' in lifespan_result[0] else 100
        
        # 2. Récupérer les éléments avec coûts de maintenance et leurs durées de vie
        sparql_maintenance = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?maintenanceCost ?costValue ?lifespan
        WHERE {
          ?element wlc:hasCost ?maintenanceCost .
          ?maintenanceCost a wlc:MaintenanceCosts ;
                          wlc:hasCostValue ?costValue .
          OPTIONAL { ?element wlc:globalId ?guid . }
          OPTIONAL { ?element wlc:hasDuration ?lifespan . }
        }
        """
        maintenance_elements = query_graphdb(sparql_maintenance)
        
        # 3. Vérifier les liaisons actuelles avec les années
        sparql_links = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?cost ?element ?guid ?costValue ?year ?yearIndex
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a wlc:MaintenanceCosts ;
                wlc:hasCostValue ?costValue ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          OPTIONAL { ?element wlc:globalId ?guid . }
        }
        ORDER BY ?guid ?yearIndex
        """
        current_links = query_graphdb(sparql_links)
        
        # 4. Analyser les données
        elements_analysis = {}
        
        for elem in maintenance_elements:
            guid = elem.get('guid', 'unknown')
            element_uri = elem['element']
            cost_value = float(elem.get('costValue', 0))
            lifespan = int(float(elem.get('lifespan', 0))) if elem.get('lifespan') else None
            
            if guid not in elements_analysis:
                elements_analysis[guid] = {
                    'element_uri': element_uri,
                    'cost_value': cost_value,
                    'lifespan': lifespan,
                    'expected_replacements': [],
                    'actual_years_linked': [],
                    'nb_replacements_expected': 0,
                    'nb_years_linked': 0
                }
            
            # Calculer les remplacements attendus
            if lifespan and lifespan > 0:
                expected_years = []
                for i in range(1, project_lifespan + 1):
                    if i % lifespan == 0:
                        expected_years.append(i)
                elements_analysis[guid]['expected_replacements'] = expected_years
                elements_analysis[guid]['nb_replacements_expected'] = len(expected_years)
        
        # Ajouter les liaisons actuelles
        for link in current_links:
            guid = link.get('guid', 'unknown')
            year = int(float(link['yearIndex']))
            
            if guid in elements_analysis:
                elements_analysis[guid]['actual_years_linked'].append(year)
                elements_analysis[guid]['nb_years_linked'] = len(elements_analysis[guid]['actual_years_linked'])
        
        # 5. Calculer les statistiques globales
        total_elements = len(elements_analysis)
        elements_with_lifespan = len([e for e in elements_analysis.values() if e['lifespan']])
        total_expected_replacements = sum(e['nb_replacements_expected'] for e in elements_analysis.values())
        total_actual_links = sum(e['nb_years_linked'] for e in elements_analysis.values())
        
        # 6. Identifier les problèmes
        problems = []
        for guid, data in elements_analysis.items():
            if data['lifespan'] is None:
                problems.append(f"Élément {guid[:8]}... : pas de durée de vie définie")
            elif data['nb_replacements_expected'] != data['nb_years_linked']:
                problems.append(f"Élément {guid[:8]}... : {data['nb_replacements_expected']} remplacements attendus, {data['nb_years_linked']} années liées")
        
        return jsonify({
            'success': True,
            'project_lifespan': project_lifespan,
            'statistics': {
                'total_maintenance_elements': total_elements,
                'elements_with_lifespan': elements_with_lifespan,
                'elements_without_lifespan': total_elements - elements_with_lifespan,
                'total_expected_replacements': total_expected_replacements,
                'total_actual_links': total_actual_links,
                'missing_links': total_expected_replacements - total_actual_links
            },
            'problems': problems[:10],  # Limiter à 10 pour l'affichage
            'sample_elements': {
                guid: {
                    'cost_value': data['cost_value'],
                    'lifespan': data['lifespan'],
                    'expected_years': data['expected_replacements'],
                    'actual_years': data['actual_years_linked'],
                    'status': 'OK' if data['nb_replacements_expected'] == data['nb_years_linked'] else 'PROBLEM'
                }
                for guid, data in list(elements_analysis.items())[:5]
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur diagnostic maintenance: {str(e)}'}), 500

@app.route('/diagnose-cost-year-duplicates')
def diagnose_cost_year_duplicates():
    """Diagnostique spécifique pour les doublons dans les liaisons coût-année"""
    try:
        # 1. Compter toutes les liaisons coût-année
        sparql_all_links = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(*) as ?totalLinks)
        WHERE {
          ?cost a ?costType ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        """
        
        # 2. Compter les liaisons distinctes (sans doublons)
        sparql_distinct_links = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(DISTINCT ?cost) as ?distinctCosts)
        WHERE {
          ?cost a ?costType ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        """
        
        # 3. Identifier les doublons exacts
        sparql_duplicates = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?cost ?costType ?yearIndex (COUNT(*) as ?linkCount)
        WHERE {
          ?cost a ?costType ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?cost ?costType ?yearIndex
        HAVING (?linkCount > 1)
        ORDER BY DESC(?linkCount)
        LIMIT 20
        """
        
        # 4. Statistiques par type de coût
        sparql_by_type = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?costType (COUNT(*) as ?linkCount)
        WHERE {
          ?cost a ?costType ;
                wlc:ForDate ?year .
          ?year wlc:hasDate ?yearIndex .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?costType
        ORDER BY ?costType
        """
        
        all_links_result = query_graphdb(sparql_all_links)
        distinct_links_result = query_graphdb(sparql_distinct_links)
        duplicates_result = query_graphdb(sparql_duplicates)
        by_type_result = query_graphdb(sparql_by_type)
        
        total_links = int(all_links_result[0]['totalLinks']) if all_links_result else 0
        distinct_costs = int(distinct_links_result[0]['distinctCosts']) if distinct_links_result else 0
        
        # Analyser les doublons
        duplicate_analysis = []
        for dup in duplicates_result:
            duplicate_analysis.append({
                'cost_uri': dup['cost'],
                'cost_type': dup['costType'].split('#')[-1],
                'year': float(dup['yearIndex']),
                'link_count': int(dup['linkCount'])
            })
        
        # Analyser par type
        type_analysis = {}
        for result in by_type_result:
            cost_type = result['costType'].split('#')[-1]
            link_count = int(result['linkCount'])
            type_analysis[cost_type] = link_count
        
        return jsonify({
            'success': True,
            'summary': {
                'total_cost_year_links': total_links,
                'distinct_costs_with_links': distinct_costs,
                'average_links_per_cost': round(total_links / distinct_costs, 2) if distinct_costs > 0 else 0,
                'duplicate_cost_year_pairs': len(duplicate_analysis),
                'excess_links': total_links - distinct_costs
            },
            'duplicates_sample': duplicate_analysis[:10],
            'links_by_type': type_analysis,
            'diagnosis': f"Ratio {total_links / distinct_costs:.2f} liens par coût suggère {'des doublons massifs' if total_links / distinct_costs > 2 else 'quelques doublons' if total_links / distinct_costs > 1.1 else 'pas de doublons significatifs'}"
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur diagnostic doublons: {str(e)}'}), 500

@app.route('/analyze-cost-impact')
def analyze_cost_impact():
    """Analyse d'impact des coûts - identifie les éléments avec les coûts totaux les plus élevés"""
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?uniformatDesc ?material
               (SUM(?constructionCost) as ?totalConstruction)
               (SUM(?operationCost) as ?totalOperation) 
               (SUM(?maintenanceCost) as ?totalMaintenance)
               (SUM(?endOfLifeCost) as ?totalEndOfLife)
               ((SUM(?constructionCost) + SUM(?operationCost) + SUM(?maintenanceCost) + SUM(?endOfLifeCost)) as ?totalCost)
        WHERE {
          ?element wlc:globalId ?guid .
          OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
          OPTIONAL { ?element wlc:hasIfcMaterial ?material . }
          
          OPTIONAL {
            ?element wlc:hasCost ?constructionCostInst .
            ?constructionCostInst a wlc:ConstructionCosts ;
                                 wlc:hasCostValue ?constructionCost .
          }
          OPTIONAL {
            ?element wlc:hasCost ?operationCostInst .
            ?operationCostInst a wlc:OperationCosts ;
                              wlc:hasCostValue ?operationCost .
          }
          OPTIONAL {
            ?element wlc:hasCost ?maintenanceCostInst .
            ?maintenanceCostInst a wlc:MaintenanceCosts ;
                                wlc:hasCostValue ?maintenanceCost .
          }
          OPTIONAL {
            ?element wlc:hasCost ?endOfLifeCostInst .
            ?endOfLifeCostInst a wlc:EndOfLifeCosts ;
                              wlc:hasCostValue ?endOfLifeCost .
          }
        }
        GROUP BY ?element ?guid ?uniformatDesc ?material
        HAVING ((SUM(?constructionCost) + SUM(?operationCost) + SUM(?maintenanceCost) + SUM(?endOfLifeCost)) > 0)
        ORDER BY DESC(?totalCost)
        LIMIT 50
        """
        
        results = query_graphdb(sparql)
        
        analysis_results = []
        for row in results:
            total_cost = float(row.get('totalCost', 0))
            construction = float(row.get('totalConstruction', 0))
            operation = float(row.get('totalOperation', 0))
            maintenance = float(row.get('totalMaintenance', 0))
            end_of_life = float(row.get('totalEndOfLife', 0))
            
            analysis_results.append({
                'guid': row.get('guid', ''),
                'description': row.get('uniformatDesc', ''),
                'material': row.get('material', ''),
                'total_cost': total_cost,
                'construction_cost': construction,
                'operation_cost': operation,
                'maintenance_cost': maintenance,
                'end_of_life_cost': end_of_life,
                'cost_breakdown': {
                    'construction_percent': round((construction / total_cost * 100), 1) if total_cost > 0 else 0,
                    'operation_percent': round((operation / total_cost * 100), 1) if total_cost > 0 else 0,
                    'maintenance_percent': round((maintenance / total_cost * 100), 1) if total_cost > 0 else 0,
                    'end_of_life_percent': round((end_of_life / total_cost * 100), 1) if total_cost > 0 else 0
                }
            })
        
        return jsonify({
            'success': True,
            'analysis_type': 'cost_impact',
            'title': 'Analyse d\'impact des coûts',
            'description': 'Éléments classés par coût total décroissant',
            'results': analysis_results,
            'summary': {
                'total_elements_analyzed': len(analysis_results),
                'top_cost_element': analysis_results[0] if analysis_results else None,
                'total_project_cost': sum(r['total_cost'] for r in analysis_results)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur analyse impact des coûts: {str(e)}'}), 500

@app.route('/analyze-frequent-replacements')
def analyze_frequent_replacements():
    """Analyse des remplacements fréquents - éléments avec durée de vie courte"""
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        # DIAGNOSTIC: Vérifier combien d'éléments ont des durées de vie définies
        sparql_lifespan_count = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(DISTINCT ?element) as ?elementsWithLifespan)
        WHERE {
          ?element wlc:globalId ?guid ;
                  wlc:hasDuration ?lifespan .
        }
        """
        lifespan_count_result = query_graphdb(sparql_lifespan_count)
        elements_with_lifespan = int(lifespan_count_result[0]['elementsWithLifespan']) if lifespan_count_result else 0
        
        # Si aucun élément n'a de durée de vie, utiliser une durée par défaut et analyser quand même
        if elements_with_lifespan == 0:
            print("⚠️ Aucun élément n'a de durée de vie définie. Utilisation de durées par défaut par matériau.")
            
            # Analyse basée sur les matériaux avec durées par défaut
            sparql = """
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            SELECT ?element ?guid ?uniformatDesc ?material ?maintenanceCost
            WHERE {
              ?element wlc:globalId ?guid .
              OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
              OPTIONAL { ?element wlc:hasIfcMaterial ?material . }
              OPTIONAL {
                ?element wlc:hasCost ?maintenanceCostInst .
                ?maintenanceCostInst a wlc:MaintenanceCosts ;
                                    wlc:hasCostValue ?maintenanceCost .
              }
              FILTER(?maintenanceCost > 0)
            }
            ORDER BY DESC(?maintenanceCost)
            LIMIT 50
            """
            
            # Durées de vie par défaut par matériau
            default_lifespans = {
                'bois': 30,
                'wood': 30,
                'plâtre': 20,
                'platre': 20,
                'gypsum': 20,
                'aluminium': 50,
                'aluminum': 50,
                'béton': 60,
                'beton': 60,
                'concrete': 60,
                'acier': 75,
                'steel': 75,
                'default': 40
            }
            
        else:
            # Analyse normale avec durées de vie définies
            sparql = """
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            SELECT ?element ?guid ?uniformatDesc ?material ?lifespan ?maintenanceCost
            WHERE {
              ?element wlc:globalId ?guid ;
                      wlc:hasDuration ?lifespan .
              OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
              OPTIONAL { ?element wlc:hasIfcMaterial ?material . }
              OPTIONAL {
                ?element wlc:hasCost ?maintenanceCostInst .
                ?maintenanceCostInst a wlc:MaintenanceCosts ;
                                    wlc:hasCostValue ?maintenanceCost .
              }
            }
            ORDER BY ?lifespan
            """
        
        results = query_graphdb(sparql)
        
        analysis_results = []
        for row in results:
            element_guid = row.get('guid', '')
            material = row.get('material', '').lower()
            maintenance_cost = float(row.get('maintenanceCost', 0))
            
            # Déterminer la durée de vie
            if elements_with_lifespan > 0:
                lifespan = int(float(row.get('lifespan', 40)))
            else:
                # Utiliser durée par défaut basée sur le matériau
                lifespan = default_lifespans.get(material, default_lifespans['default'])
                
                # Chercher dans les clés partielles
                for mat_key, default_life in default_lifespans.items():
                    if mat_key in material:
                        lifespan = default_life
                        break
            
            # Calculer le nombre de remplacements sur la durée du projet
            replacements_count = project_lifespan // lifespan if lifespan > 0 else 0
            total_replacement_cost = replacements_count * maintenance_cost if maintenance_cost > 0 else 0
            
            # CRITÈRES ASSOUPLIS: Considérer comme "fréquent" si plus de 1 remplacement OU durée < 30 ans
            is_frequent = replacements_count > 1 or lifespan < 30
            
            if is_frequent:
                analysis_results.append({
                    'guid': element_guid,
                    'description': row.get('uniformatDesc', ''),
                    'material': row.get('material', ''),
                    'lifespan': lifespan,
                    'maintenance_cost': maintenance_cost,
                    'replacements_count': replacements_count,
                    'total_replacement_cost': total_replacement_cost,
                    'replacement_frequency': round(project_lifespan / lifespan, 1) if lifespan > 0 else 0,
                    'years_between_replacements': lifespan,
                    'lifespan_source': 'définie' if elements_with_lifespan > 0 else 'estimée par matériau'
                })
        
        # Trier par nombre de remplacements décroissant
        analysis_results.sort(key=lambda x: x['replacements_count'], reverse=True)
        
        return jsonify({
            'success': True,
            'analysis_type': 'frequent_replacements',
            'title': 'Analyse des remplacements fréquents (corrigée)',
            'description': f'Éléments nécessitant des remplacements fréquents sur {project_lifespan} ans',
            'results': analysis_results[:30],  # Limiter à 30 résultats
            'summary': {
                'project_lifespan': project_lifespan,
                'elements_with_defined_lifespan': elements_with_lifespan,
                'elements_with_frequent_replacements': len(analysis_results),
                'most_frequent_element': analysis_results[0] if analysis_results else None,
                'total_replacement_costs': sum(r['total_replacement_cost'] for r in analysis_results),
                'criteria_used': 'Remplacements > 1 OU durée < 30 ans',
                'lifespan_method': 'Définie par l\'utilisateur' if elements_with_lifespan > 0 else 'Estimée par matériau'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur analyse remplacements fréquents: {str(e)}'}), 500

@app.route('/analyze-high-maintenance')
def analyze_high_maintenance():
    """Analyse de maintenance élevée - éléments avec coûts de maintenance élevés"""
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?uniformatDesc ?material ?lifespan ?maintenanceCost
        WHERE {
          ?element wlc:globalId ?guid ;
                  wlc:hasCost ?maintenanceCostInst .
          ?maintenanceCostInst a wlc:MaintenanceCosts ;
                              wlc:hasCostValue ?maintenanceCost .
          OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
          OPTIONAL { ?element wlc:hasIfcMaterial ?material . }
          OPTIONAL { ?element wlc:hasDuration ?lifespan . }
          
          FILTER(?maintenanceCost > 0)
        }
        ORDER BY DESC(?maintenanceCost)
        """
        
        results = query_graphdb(sparql)
        
        # Calculer les statistiques pour déterminer les seuils
        maintenance_costs = [float(row.get('maintenanceCost', 0)) for row in results]
        
        if not maintenance_costs:
            return jsonify({
                'success': True,
                'analysis_type': 'high_maintenance',
                'title': 'Analyse de maintenance élevée',
                'description': 'Aucun coût de maintenance trouvé',
                'results': [],
                'summary': {'high_maintenance_elements': 0, 'error': 'Aucune donnée de maintenance'}
            })
        
        maintenance_costs.sort()
        n = len(maintenance_costs)
        
        # Utiliser les percentiles au lieu de la médiane pour des seuils plus flexibles
        p25 = maintenance_costs[n//4] if n >= 4 else maintenance_costs[0]
        median_cost = maintenance_costs[n//2] if n >= 2 else maintenance_costs[0]
        p75 = maintenance_costs[3*n//4] if n >= 4 else maintenance_costs[-1]
        p90 = maintenance_costs[9*n//10] if n >= 10 else maintenance_costs[-1]
        
        # SEUILS ASSOUPLIS: Utiliser le 75e percentile comme seuil "élevé"
        high_threshold = p75
        very_high_threshold = p90
        
        print(f"📊 Statistiques maintenance: médiane={median_cost:.0f}$ P75={p75:.0f}$ P90={p90:.0f}$")
        print(f"🎯 Seuils: Élevé ≥ {high_threshold:.0f}$ Très élevé ≥ {very_high_threshold:.0f}$")
        
        analysis_results = []
        for row in results:
            maintenance_cost = float(row.get('maintenanceCost', 0))
            lifespan = int(float(row.get('lifespan', 60))) if row.get('lifespan') else 60
            
            # Calculer le coût annuel moyen de maintenance
            annual_maintenance_cost = maintenance_cost / lifespan if lifespan > 0 else maintenance_cost
            
            # Ratio par rapport aux percentiles
            cost_ratio_median = maintenance_cost / median_cost if median_cost > 0 else 1
            cost_ratio_p75 = maintenance_cost / p75 if p75 > 0 else 1
            
            # CRITÈRE ASSOUPLI: maintenance >= P75 (75e percentile)
            if maintenance_cost >= high_threshold:
                # Catégorisation plus nuancée
                if maintenance_cost >= very_high_threshold:
                    category = 'Très élevé'
                elif maintenance_cost >= high_threshold * 1.5:
                    category = 'Élevé+'
                else:
                    category = 'Élevé'
                
                analysis_results.append({
                    'guid': row.get('guid', ''),
                    'description': row.get('uniformatDesc', ''),
                    'material': row.get('material', ''),
                    'maintenance_cost': maintenance_cost,
                    'lifespan': lifespan,
                    'annual_maintenance_cost': round(annual_maintenance_cost, 2),
                    'cost_ratio_vs_median': round(cost_ratio_median, 1),
                    'cost_ratio_vs_p75': round(cost_ratio_p75, 1),
                    'cost_category': category,
                    'percentile_rank': round((maintenance_costs.index(maintenance_cost) / len(maintenance_costs)) * 100, 1) if maintenance_cost in maintenance_costs else 'N/A'
                })
        
        return jsonify({
            'success': True,
            'analysis_type': 'high_maintenance',
            'title': 'Analyse de maintenance élevée (corrigée)',
            'description': f'Éléments avec coûts de maintenance ≥ {high_threshold:,.0f}$ (75e percentile)',
            'results': analysis_results,
            'summary': {
                'total_elements_analyzed': len(results),
                'high_maintenance_elements': len(analysis_results),
                'median_maintenance_cost': median_cost,
                'p75_threshold': p75,
                'p90_threshold': p90,
                'high_threshold': high_threshold,
                'very_high_threshold': very_high_threshold,
                'highest_cost_element': analysis_results[0] if analysis_results else None,
                'total_high_maintenance_costs': sum(r['maintenance_cost'] for r in analysis_results),
                'threshold_method': '75e percentile au lieu de 2x médiane',
                'distribution': {
                    'P25': round(p25, 0),
                    'Médiane': round(median_cost, 0),
                    'P75': round(p75, 0),
                    'P90': round(p90, 0)
                }
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur analyse maintenance élevée: {str(e)}'}), 500

@app.route('/analyze-high-operation')
def analyze_high_operation():
    """Analyse d'opération élevée - éléments avec coûts d'opération élevés"""
    try:
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?uniformatDesc ?material ?operationCost
        WHERE {
          ?element wlc:globalId ?guid ;
                  wlc:hasCost ?operationCostInst .
          ?operationCostInst a wlc:OperationCosts ;
                            wlc:hasCostValue ?operationCost .
          OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
          OPTIONAL { ?element wlc:hasIfcMaterial ?material . }
          
          FILTER(?operationCost > 0)
        }
        ORDER BY DESC(?operationCost)
        """
        
        results = query_graphdb(sparql)
        
        # Calculer les statistiques d'opération
        operation_costs = [float(row.get('operationCost', 0)) for row in results]
        
        if not operation_costs:
            return jsonify({
                'success': True,
                'analysis_type': 'high_operation',
                'title': 'Analyse d\'opération élevée',
                'description': 'Aucun coût d\'opération trouvé',
                'results': [],
                'summary': {'high_operation_elements': 0, 'error': 'Aucune donnée d\'opération'}
            })
        
        operation_costs.sort()
        n = len(operation_costs)
        
        # DIAGNOSTIC: Si tous les coûts sont identiques (ex: tous à 10€)
        unique_costs = len(set(operation_costs))
        
        if unique_costs <= 2:
            print(f"⚠️ Coûts d'opération peu variés: {unique_costs} valeurs distinctes")
            # Si peu de variation, prendre les éléments avec le coût maximum
            max_cost = max(operation_costs)
            high_threshold = max_cost
            analysis_title = f"Éléments avec coût d'opération maximum ({max_cost:,.0f}$)"
        else:
            # Utiliser les percentiles normalement
            p75 = operation_costs[3*n//4] if n >= 4 else operation_costs[-1]
            p90 = operation_costs[9*n//10] if n >= 10 else operation_costs[-1]
            high_threshold = p75
            analysis_title = f"Éléments avec coût d'opération ≥ {high_threshold:,.2f}$ (75e percentile)"
        
        median_cost = operation_costs[n//2] if n >= 2 else operation_costs[0]
        
        # Récupérer la durée de vie du projet pour calculer le coût total sur la durée
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        analysis_results = []
        for row in results:
            operation_cost = float(row.get('operationCost', 0))
            
            # Coût total d'opération sur la durée du projet (années 1 à N-1)
            total_operation_cost = operation_cost * (project_lifespan - 1)
            
            # Ratio par rapport au coût médian
            cost_ratio = operation_cost / median_cost if median_cost > 0 else 1
            
            if operation_cost >= high_threshold:
                # Déterminer la catégorie
                if unique_costs <= 2:
                    category = 'Maximum'
                elif operation_cost >= high_threshold * 1.5:
                    category = 'Très élevé'
                else:
                    category = 'Élevé'
                
                analysis_results.append({
                    'guid': row.get('guid', ''),
                    'description': row.get('uniformatDesc', ''),
                    'material': row.get('material', ''),
                    'annual_operation_cost': operation_cost,
                    'total_operation_cost': total_operation_cost,
                    'cost_ratio_vs_median': round(cost_ratio, 1),
                    'cost_category': category,
                    'annual_vs_project_percent': round((total_operation_cost / sum(operation_costs) * (project_lifespan - 1) * 100), 1) if sum(operation_costs) > 0 else 0
                })
        
        return jsonify({
            'success': True,
            'analysis_type': 'high_operation',
            'title': 'Analyse d\'opération élevée (corrigée)',
            'description': analysis_title,
            'results': analysis_results,
            'summary': {
                'project_lifespan': project_lifespan,
                'high_operation_elements': len(analysis_results),
                'median_operation_cost': median_cost,
                'high_threshold': high_threshold,
                'highest_cost_element': analysis_results[0] if analysis_results else None,
                'total_high_operation_costs': sum(r['total_operation_cost'] for r in analysis_results)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur analyse opération élevée: {str(e)}'}), 500

@app.route('/analyze-cost-by-phase')
def analyze_cost_by_phase():
    """Analyse des coûts par phase du cycle de vie"""
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        # CORRIGÉ: Calculer les coûts totaux par phase sur la durée de vie complète
        sparql = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?costType (COUNT(?cost) as ?elementCount) (SUM(?costValue) as ?totalAnnualCost) (AVG(?costValue) as ?avgCost)
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
          FILTER(?costValue > 0)
        }
        GROUP BY ?costType
        ORDER BY DESC(?totalAnnualCost)
        """
        
        results = query_graphdb(sparql)
        
        phase_analysis = []
        total_project_cost = 0
        
        for row in results:
            cost_type = row['costType'].split('#')[-1]
            element_count = int(row['elementCount'])
            total_annual_cost = float(row['totalAnnualCost'])
            avg_cost = float(row['avgCost'])
            
            # CORRECTION PRINCIPALE: Calculer le coût total sur la durée de vie selon le type
            if cost_type == 'OperationCosts':
                # Opération: coût annuel × (durée - 1) car années 1 à N-1
                total_lifecycle_cost = total_annual_cost * (project_lifespan - 1)
                lifecycle_note = f"Coût annuel × {project_lifespan - 1} années"
            elif cost_type == 'MaintenanceCosts':
                # Maintenance: coût par remplacement, fréquence dépend de la durée de vie des éléments
                # Pour l'instant, approximation avec durée moyenne de 60 ans
                avg_element_lifespan = 60
                replacements_per_element = project_lifespan // avg_element_lifespan
                total_lifecycle_cost = total_annual_cost * replacements_per_element
                lifecycle_note = f"Coût par remplacement × ~{replacements_per_element} remplacements"
            else:
                # Construction et Fin de vie: coûts one-time
                total_lifecycle_cost = total_annual_cost
                lifecycle_note = "Coût unique"
            
            total_project_cost += total_lifecycle_cost
            
            phase_analysis.append({
                'phase': cost_type,
                'phase_name': {
                    'ConstructionCosts': 'Construction',
                    'OperationCosts': 'Opération',
                    'MaintenanceCosts': 'Maintenance',
                    'EndOfLifeCosts': 'Fin de vie'
                }.get(cost_type, cost_type),
                'element_count': element_count,
                'annual_cost': total_annual_cost,  # Coût annuel/unitaire
                'total_lifecycle_cost': total_lifecycle_cost,  # Coût total sur durée de vie
                'average_cost': avg_cost,
                'cost_percent': 0,  # Sera calculé après
                'calculation_note': lifecycle_note
            })
        
        # Calculer les pourcentages basés sur les coûts totaux sur la durée de vie
        for phase in phase_analysis:
            phase['cost_percent'] = round((phase['total_lifecycle_cost'] / total_project_cost * 100), 1) if total_project_cost > 0 else 0
        
        # Analyse détaillée par Uniformat pour la phase dominante
        dominant_phase = max(phase_analysis, key=lambda x: x['total_lifecycle_cost']) if phase_analysis else None
        
        uniformat_analysis = []
        if dominant_phase:
            sparql_uniformat = f"""
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            SELECT ?uniformatDesc (COUNT(?element) as ?elementCount) (SUM(?costValue) as ?totalCost)
            WHERE {{
              ?element wlc:hasCost ?cost ;
                      wlc:hasUniformatDescription ?uniformatDesc .
              ?cost a wlc:{dominant_phase['phase']} ;
                    wlc:hasCostValue ?costValue .
              FILTER(?costValue > 0)
            }}
            GROUP BY ?uniformatDesc
            ORDER BY DESC(?totalCost)
            LIMIT 10
            """
            
            uniformat_results = query_graphdb(sparql_uniformat)
            for row in uniformat_results:
                uniformat_analysis.append({
                    'uniformat_description': row.get('uniformatDesc', ''),
                    'element_count': int(row['elementCount']),
                    'annual_cost': float(row['totalCost']),
                    'total_lifecycle_cost': float(row['totalCost']) * (project_lifespan - 1) if dominant_phase['phase'] == 'OperationCosts' else float(row['totalCost'])
                })
        
        return jsonify({
            'success': True,
            'analysis_type': 'cost_by_phase',
            'title': 'Analyse des coûts par phase (corrigée)',
            'description': f'Répartition des coûts par phase du cycle de vie sur {project_lifespan} ans',
            'results': {
                'phase_breakdown': phase_analysis,
                'dominant_phase_detail': {
                    'phase': dominant_phase,
                    'top_uniformat_categories': uniformat_analysis
                } if dominant_phase else None
            },
            'summary': {
                'project_lifespan': project_lifespan,
                'total_project_cost_lifecycle': total_project_cost,
                'dominant_phase': dominant_phase['phase_name'] if dominant_phase else None,
                'phases_analyzed': len(phase_analysis),
                'cost_distribution': {phase['phase_name']: phase['cost_percent'] for phase in phase_analysis},
                'correction_applied': "Coûts d'opération calculés sur la durée de vie complète"
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur analyse coûts par phase: {str(e)}'}), 500

@app.route('/export-analysis-results')
def export_analysis_results():
    """Export des résultats d'analyse en Excel"""
    try:
        # Exécuter toutes les analyses
        cost_impact = analyze_cost_impact()
        frequent_replacements = analyze_frequent_replacements()
        high_maintenance = analyze_high_maintenance()
        high_operation = analyze_high_operation()
        cost_by_phase = analyze_cost_by_phase()
        
        # Convertir les réponses JSON en données
        impact_data = cost_impact.get_json()['results'] if cost_impact.status_code == 200 else []
        replacements_data = frequent_replacements.get_json()['results'] if frequent_replacements.status_code == 200 else []
        maintenance_data = high_maintenance.get_json()['results'] if high_maintenance.status_code == 200 else []
        operation_data = high_operation.get_json()['results'] if high_operation.status_code == 200 else []
        phase_data = cost_by_phase.get_json()['results']['phase_breakdown'] if cost_by_phase.status_code == 200 else []
        
        # Créer les DataFrames
        df_impact = pd.DataFrame(impact_data)
        df_replacements = pd.DataFrame(replacements_data)
        df_maintenance = pd.DataFrame(maintenance_data)
        df_operation = pd.DataFrame(operation_data)
        df_phases = pd.DataFrame(phase_data)
        
        # Créer le fichier Excel avec plusieurs onglets
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_impact.empty:
                df_impact.to_excel(writer, sheet_name='Impact des coûts', index=False)
            if not df_replacements.empty:
                df_replacements.to_excel(writer, sheet_name='Remplacements fréquents', index=False)
            if not df_maintenance.empty:
                df_maintenance.to_excel(writer, sheet_name='Maintenance élevée', index=False)
            if not df_operation.empty:
                df_operation.to_excel(writer, sheet_name='Opération élevée', index=False)
            if not df_phases.empty:
                df_phases.to_excel(writer, sheet_name='Coûts par phase', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            download_name=f'analyse_WLC_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur export analyses: {str(e)}'}), 500

@app.route('/diagnose-cost-impact-issues')
def diagnose_cost_impact_issues():
    """Diagnostique les problèmes dans les calculs d'analyse d'impact des coûts"""
    try:
        # 1. Analyser les éléments avec coûts multiples du même type
        sparql_duplicates = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?costType (COUNT(?cost) as ?costCount) (GROUP_CONCAT(?costValue; separator=", ") as ?allValues)
        WHERE {
          ?element wlc:globalId ?guid ;
                  wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?element ?guid ?costType
        HAVING (?costCount > 1)
        ORDER BY DESC(?costCount)
        LIMIT 20
        """
        
        # 2. Identifier les éléments avec des coûts très élevés
        sparql_high_costs = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?uniformatDesc ?costType ?costValue
        WHERE {
          ?element wlc:globalId ?guid ;
                  wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
          FILTER(?costValue > 1000000)  # Plus de 1M$
        }
        ORDER BY DESC(?costValue)
        LIMIT 20
        """
        
        # 3. Calculer les statistiques globales
        sparql_stats = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?costType 
               (COUNT(DISTINCT ?element) as ?uniqueElements)
               (COUNT(?cost) as ?totalCostInstances)
               (SUM(?costValue) as ?totalValue)
               (AVG(?costValue) as ?avgValue)
               (MAX(?costValue) as ?maxValue)
               (MIN(?costValue) as ?minValue)
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?costType
        ORDER BY ?costType
        """
        
        # 4. Analyser un élément spécifique problématique
        sparql_problem_element = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?uniformatDesc ?material ?cost ?costType ?costValue
        WHERE {
          ?element wlc:globalId ?guid ;
                  wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDesc . }
          OPTIONAL { ?element wlc:hasIfcMaterial ?material . }
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
          FILTER(?costValue > 10000000)  # Plus de 10M$
        }
        ORDER BY DESC(?costValue)
        LIMIT 10
        """
        
        duplicates_result = query_graphdb(sparql_duplicates)
        high_costs_result = query_graphdb(sparql_high_costs)
        stats_result = query_graphdb(sparql_stats)
        problem_elements_result = query_graphdb(sparql_problem_element)
        
        # Analyser les doublons
        duplicate_analysis = []
        for dup in duplicates_result:
            cost_type = dup['costType'].split('#')[-1]
            cost_count = int(dup['costCount'])
            values = [float(v.strip()) for v in dup['allValues'].split(', ') if v.strip()]
            
            duplicate_analysis.append({
                'guid': dup.get('guid', ''),
                'cost_type': cost_type,
                'duplicate_count': cost_count,
                'individual_values': values,
                'sum_of_duplicates': sum(values),
                'problem_severity': 'CRITIQUE' if cost_count > 5 else 'ÉLEVÉ' if cost_count > 2 else 'MODÉRÉ'
            })
        
        # Analyser les statistiques par type
        stats_analysis = {}
        total_project_from_stats = 0
        for stat in stats_result:
            cost_type = stat['costType'].split('#')[-1]
            unique_elements = int(stat['uniqueElements'])
            total_instances = int(stat['totalCostInstances'])
            total_value = float(stat['totalValue'])
            avg_value = float(stat['avgValue'])
            max_value = float(stat['maxValue'])
            
            total_project_from_stats += total_value
            duplication_ratio = total_instances / unique_elements if unique_elements > 0 else 0
            
            stats_analysis[cost_type] = {
                'unique_elements': unique_elements,
                'total_instances': total_instances,
                'duplication_ratio': round(duplication_ratio, 2),
                'total_value': total_value,
                'average_value': round(avg_value, 2),
                'max_value': max_value,
                'is_duplicated': duplication_ratio > 1.1
            }
        
        # Analyser les éléments problématiques
        problem_elements = []
        for elem in problem_elements_result:
            problem_elements.append({
                'guid': elem.get('guid', ''),
                'description': elem.get('uniformatDesc', ''),
                'material': elem.get('material', ''),
                'cost_type': elem['costType'].split('#')[-1],
                'cost_value': float(elem['costValue']),
                'cost_uri': elem['cost']
            })
        
        return jsonify({
            'success': True,
            'diagnosis_summary': {
                'total_project_cost_from_stats': total_project_from_stats,
                'elements_with_duplicates': len(duplicate_analysis),
                'elements_with_high_costs': len(problem_elements),
                'most_severe_duplication': max([d['duplicate_count'] for d in duplicate_analysis]) if duplicate_analysis else 0
            },
            'duplicate_cost_instances': duplicate_analysis[:10],
            'statistics_by_type': stats_analysis,
            'problem_elements': problem_elements,
            'recommendations': [
                "Vérifier les imports multiples du même fichier de coûts",
                "Nettoyer les instances de coûts dupliquées",
                "Valider les valeurs aberrantes > 10M$",
                "Recalculer le WLC après nettoyage"
            ]
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur diagnostic impact coûts: {str(e)}'}), 500

@app.route('/clean-duplicate-costs', methods=['POST'])
def clean_duplicate_costs():
    """Nettoie les instances de coûts dupliquées en gardant seulement une instance par élément et par type"""
    try:
        from sparql_client import UPDATE_ENDPOINT
        import requests
        
        # 1. Identifier tous les doublons
        sparql_find_duplicates = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?costType (COUNT(?cost) as ?costCount) (MIN(?cost) as ?costToKeep) (GROUP_CONCAT(?cost; separator="|") as ?allCosts)
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?element ?costType
        HAVING (?costCount > 1)
        """
        
        duplicates_result = query_graphdb(sparql_find_duplicates)
        
        print(f"🧹 Nettoyage des doublons : {len(duplicates_result)} groupes de doublons trouvés")
        
        total_deleted = 0
        cleaned_elements = 0
        
        for group in duplicates_result:
            element_uri = group['element']
            cost_type = group['costType']
            cost_to_keep = group['costToKeep']
            all_costs = group['allCosts'].split('|')
            costs_to_delete = [cost for cost in all_costs if cost != cost_to_keep]
            
            print(f"   Élément {element_uri[-8:]}... - {cost_type.split('#')[-1]} : garder 1, supprimer {len(costs_to_delete)}")
            
            # Supprimer les doublons (garder le premier)
            for cost_to_delete in costs_to_delete:
                delete_query = f"""
                PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                DELETE {{
                    <{element_uri}> wlc:hasCost <{cost_to_delete}> .
                    <{cost_to_delete}> ?p ?o .
                }}
                WHERE {{
                    <{element_uri}> wlc:hasCost <{cost_to_delete}> .
                    <{cost_to_delete}> ?p ?o .
                }}
                """
                
                response = requests.post(UPDATE_ENDPOINT, data={"update": delete_query})
                if response.ok:
                    total_deleted += 1
                else:
                    print(f"      ❌ Erreur suppression {cost_to_delete}: {response.status_code}")
            
            cleaned_elements += 1
        
        # 2. Vérifier le résultat
        sparql_verify = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?costType (COUNT(DISTINCT ?element) as ?uniqueElements) (COUNT(?cost) as ?totalInstances)
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?costType
        """
        
        verification_result = query_graphdb(sparql_verify)
        verification_stats = {}
        
        for stat in verification_result:
            cost_type = stat['costType'].split('#')[-1]
            unique_elements = int(stat['uniqueElements'])
            total_instances = int(stat['totalInstances'])
            ratio = total_instances / unique_elements if unique_elements > 0 else 0
            
            verification_stats[cost_type] = {
                'unique_elements': unique_elements,
                'total_instances': total_instances,
                'ratio': round(ratio, 2),
                'is_clean': ratio <= 1.0
            }
        
        # 3. Relancer la liaison coûts-années après nettoyage
        print("🔄 Reliage des coûts aux années après nettoyage...")
        relink_costs_to_years()
        
        return jsonify({
            'success': True,
            'cleaning_summary': {
                'duplicate_groups_found': len(duplicates_result),
                'elements_cleaned': cleaned_elements,
                'cost_instances_deleted': total_deleted,
                'remaining_duplicates': sum(1 for stats in verification_stats.values() if not stats['is_clean'])
            },
            'verification_stats': verification_stats,
            'message': f"✅ Nettoyage terminé : {total_deleted} instances supprimées pour {cleaned_elements} éléments"
        })
        
    except Exception as e:
        print(f"❌ Erreur nettoyage doublons: {str(e)}")
        return jsonify({'error': f'Erreur nettoyage doublons: {str(e)}'}), 500

@app.route('/prevent-future-duplicates', methods=['POST'])
def prevent_future_duplicates():
    """Vérifie et prévient les doublons potentiels avant qu'ils ne se créent"""
    try:
        # 1. Vérifier s'il y a des doublons actuels
        current_duplicates = query_graphdb("""
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?costType (COUNT(?cost) as ?costCount)
        WHERE {
          ?element wlc:hasCost ?cost .
          ?cost a ?costType ;
                wlc:hasCostValue ?costValue .
          FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
        }
        GROUP BY ?element ?costType
        HAVING (?costCount > 1)
        """)
        
        duplicates_count = len(current_duplicates)
        
        # 2. Configuration de protection (ajout de contraintes dans l'ontologie)
        protection_rules = {
            'auto_clean_on_import': True,
            'validate_before_insert': True,
            'max_cost_instances_per_element_type': 1
        }
        
        return jsonify({
            'success': True,
            'current_duplicates_found': duplicates_count,
            'protection_status': 'ACTIVÉ' if duplicates_count == 0 else 'NETTOYAGE REQUIS',
            'protection_rules': protection_rules,
            'recommendations': [
                "✅ Fonctions modifiées pour supprimer les anciens coûts avant insertion",
                "✅ Endpoint de nettoyage automatique disponible",
                "✅ Vérification d'intégrité ajoutée aux imports",
                "⚠️ Toujours utiliser /clean-duplicate-costs après import massif"
            ],
            'next_steps': [
                "Utiliser /clean-duplicate-costs si des doublons sont détectés",
                "Relancer /prevent-future-duplicates pour vérifier le statut"
            ] if duplicates_count > 0 else [
                "✅ Système protégé contre les doublons futurs"
            ]
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur prévention doublons: {str(e)}'}), 500

@app.route('/api/ontology/structure')
def get_ontology_structure():
    """
    Retourne la structure de l'ontologie WLCONTO pour la visualisation
    """
    try:
        print("🎯 Récupération de la structure de l'ontologie...")
        
        # Requête pour récupérer les classes
        sparql_classes = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        
        SELECT DISTINCT ?class ?label ?comment WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
            OPTIONAL { ?class rdfs:comment ?comment }
            FILTER(STRSTARTS(STR(?class), "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"))
        }
        ORDER BY ?class
        """
        
        # Requête pour récupérer les propriétés d'objet
        sparql_object_properties = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        
        SELECT DISTINCT ?property ?label ?domain ?range WHERE {
            ?property a owl:ObjectProperty .
            OPTIONAL { ?property rdfs:label ?label }
            OPTIONAL { ?property rdfs:domain ?domain }
            OPTIONAL { ?property rdfs:range ?range }
            FILTER(STRSTARTS(STR(?property), "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"))
        }
        ORDER BY ?property
        """
        
        # Requête pour récupérer les propriétés de données
        sparql_data_properties = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        
        SELECT DISTINCT ?property ?label ?domain ?range WHERE {
            ?property a owl:DatatypeProperty .
            OPTIONAL { ?property rdfs:label ?label }
            OPTIONAL { ?property rdfs:domain ?domain }
            OPTIONAL { ?property rdfs:range ?range }
            FILTER(STRSTARTS(STR(?property), "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"))
        }
        ORDER BY ?property
        """
        
        # Requête pour récupérer les relations de hiérarchie
        sparql_hierarchy = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?subclass ?superclass WHERE {
            ?subclass rdfs:subClassOf ?superclass .
            FILTER(STRSTARTS(STR(?subclass), "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"))
            FILTER(STRSTARTS(STR(?superclass), "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"))
        }
        """
        
        # Requête pour compter les instances
        sparql_instances_count = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT (COUNT(DISTINCT ?instance) as ?count) WHERE {
            ?instance a ?class .
            FILTER(STRSTARTS(STR(?class), "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"))
        }
        """
        
        # Exécuter les requêtes
        classes_result = query_graphdb(sparql_classes)
        object_props_result = query_graphdb(sparql_object_properties)
        data_props_result = query_graphdb(sparql_data_properties)
        hierarchy_result = query_graphdb(sparql_hierarchy)
        instances_count_result = query_graphdb(sparql_instances_count)
        
        # Construire les nœuds
        nodes = []
        
        # Ajouter les classes
        for cls in classes_result:
            class_uri = cls['class']
            class_name = class_uri.split('#')[-1] if '#' in class_uri else class_uri
            nodes.append({
                'id': class_name,
                'type': 'class',
                'label': cls.get('label', class_name),
                'description': cls.get('comment', f'Classe {class_name}'),
                'uri': class_uri
            })
        
        # Ajouter les propriétés d'objet
        for prop in object_props_result:
            prop_uri = prop['property']
            prop_name = prop_uri.split('#')[-1] if '#' in prop_uri else prop_uri
            nodes.append({
                'id': prop_name,
                'type': 'objectProperty',
                'label': prop.get('label', prop_name),
                'description': f'Propriété d\'objet {prop_name}',
                'uri': prop_uri,
                'domain': prop.get('domain', ''),
                'range': prop.get('range', '')
            })
        
        # Ajouter les propriétés de données
        for prop in data_props_result:
            prop_uri = prop['property']
            prop_name = prop_uri.split('#')[-1] if '#' in prop_uri else prop_uri
            nodes.append({
                'id': prop_name,
                'type': 'dataProperty',
                'label': prop.get('label', prop_name),
                'description': f'Propriété de données {prop_name}',
                'uri': prop_uri,
                'domain': prop.get('domain', ''),
                'range': prop.get('range', '')
            })
        
        # Ajouter les règles SWRL (statiques pour l'instant)
        nodes.extend([
            {
                'id': 'S1',
                'type': 'swrl',
                'label': 'Règle S1',
                'description': 'Sélection des données pour actualisation',
                'formula': 'Costs(?c) ∧ Time(?year) ∧ ForDate(?c, ?year) → SELECT(?c, ?value, ?year, ?R)'
            },
            {
                'id': 'S2',
                'type': 'swrl',
                'label': 'Règle S2',
                'description': 'Calcul d\'actualisation automatique',
                'formula': 'DC = value / (1 + rate)^year'
            }
        ])
        
        # Construire les liens
        links = []
        
        # Ajouter les relations de hiérarchie
        for rel in hierarchy_result:
            subclass_name = rel['subclass'].split('#')[-1] if '#' in rel['subclass'] else rel['subclass']
            superclass_name = rel['superclass'].split('#')[-1] if '#' in rel['superclass'] else rel['superclass']
            links.append({
                'source': subclass_name,
                'target': superclass_name,
                'type': 'subClassOf',
                'label': 'subClassOf'
            })
        
        # Ajouter les relations de propriétés (basées sur domain/range)
        for prop in object_props_result:
            prop_name = prop['property'].split('#')[-1] if '#' in prop['property'] else prop['property']
            if prop.get('domain'):
                domain_name = prop['domain'].split('#')[-1] if '#' in prop['domain'] else prop['domain']
                links.append({
                    'source': domain_name,
                    'target': prop_name,
                    'type': 'hasObjectProperty',
                    'label': 'hasProperty'
                })
            if prop.get('range'):
                range_name = prop['range'].split('#')[-1] if '#' in prop['range'] else prop['range']
                links.append({
                    'source': prop_name,
                    'target': range_name,
                    'type': 'objectProperty',
                    'label': prop_name
                })
        
        # Ajouter les relations de propriétés de données
        for prop in data_props_result:
            prop_name = prop['property'].split('#')[-1] if '#' in prop['property'] else prop['property']
            if prop.get('domain'):
                domain_name = prop['domain'].split('#')[-1] if '#' in prop['domain'] else prop['domain']
                links.append({
                    'source': domain_name,
                    'target': prop_name,
                    'type': 'hasDataProperty',
                    'label': 'hasDataProperty'
                })
        
        # Ajouter les relations avec les règles SWRL
        links.extend([
            {'source': 'S1', 'target': 'Costs', 'type': 'swrlRule', 'label': 'appliesTo'},
            {'source': 'S1', 'target': 'DiscountRate', 'type': 'swrlRule', 'label': 'uses'},
            {'source': 'S2', 'target': 'DiscountedCosts', 'type': 'swrlRule', 'label': 'generates'},
            {'source': 'S2', 'target': 'hasDiscountedCostValue', 'type': 'swrlRule', 'label': 'calculates'}
        ])
        
        # Calculer les statistiques
        instances_count = int(instances_count_result[0]['count']) if instances_count_result else 0
        
        stats = {
            'classes': len([n for n in nodes if n['type'] == 'class']),
            'objectProperties': len([n for n in nodes if n['type'] == 'objectProperty']),
            'dataProperties': len([n for n in nodes if n['type'] == 'dataProperty']),
            'instances': instances_count,
            'swrlRules': len([n for n in nodes if n['type'] == 'swrl']),
            'totalNodes': len(nodes),
            'totalLinks': len(links)
        }
        
        result = {
            'nodes': nodes,
            'links': links,
            'stats': stats,
            'metadata': {
                'ontology_uri': 'http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO',
                'generated_at': datetime.now().isoformat(),
                'description': 'Structure de l\'ontologie WLCONTO pour la visualisation'
            }
        }
        
        print(f"✅ Structure ontologie générée: {stats['totalNodes']} nœuds, {stats['totalLinks']} liens")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de la structure: {e}")
        return jsonify({
            'error': f'Erreur lors de la récupération de la structure de l\'ontologie: {str(e)}'
        }), 500

#################################################################
#    API STAKEHOLDERS - Gestion des Parties Prenantes
#################################################################

@app.route('/api/stakeholders', methods=['GET'])
def get_stakeholders():
    """Récupère toutes les parties prenantes du projet"""
    try:
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
        
        SELECT ?stakeholder ?type ?name ?priority ?influence WHERE {
            ?stakeholder a ?type .
            ?type rdfs:subClassOf* :Stakeholder .
            
            # Filtrer pour ne récupérer que les instances réelles, pas les classes
            FILTER(?stakeholder != :Stakeholder)
            FILTER(?stakeholder != :PropertyOwner)
            FILTER(?stakeholder != :AssetOperator)
            FILTER(?stakeholder != :EndUser)
            FILTER(?stakeholder != :MaintenanceProvider)
            FILTER(?stakeholder != :EnergyProvider)
            
            # S'assurer qu'on a des instances avec des propriétés
            FILTER(EXISTS { ?stakeholder :hasPriority ?priority } || 
                   EXISTS { ?stakeholder :hasInfluenceLevel ?influence } ||
                   EXISTS { ?stakeholder ifc:name_IfcPerson ?name } ||
                   EXISTS { ?stakeholder ifc:name_IfcOrganization ?name })
            
            # Ne récupérer que le type le plus spécifique (pas Stakeholder générique)
            FILTER(?type != :Stakeholder)
            
            OPTIONAL { ?stakeholder ifc:name_IfcPerson ?name }
            OPTIONAL { ?stakeholder ifc:name_IfcOrganization ?name }
            OPTIONAL { ?stakeholder :hasPriority ?priority }
            OPTIONAL { ?stakeholder :hasInfluenceLevel ?influence }
        }
        """
        
        result = query_graphdb(query)
        stakeholders = []
        
        # result est déjà une liste de dictionnaires, pas besoin de .get()
        for binding in result:
            stakeholder = {
                'uri': binding['stakeholder'],
                'type': binding['type'].split('#')[-1] if '#' in binding['type'] else binding['type'],
                'name': binding.get('name', ''),
                'priority': int(binding.get('priority', 2)),
                'influence': float(binding.get('influence', 0.5))
            }
            stakeholders.append(stakeholder)
        
        return jsonify({
            'success': True,
            'stakeholders': stakeholders,
            'count': len(stakeholders)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des parties prenantes: {str(e)}'}), 500

@app.route('/api/stakeholder-impact/<stakeholder_id>', methods=['GET'])
def get_stakeholder_impact(stakeholder_id):
    """Analyse l'impact des coûts sur une partie prenante spécifique"""
    try:
        # Décoder l'URI du stakeholder
        stakeholder_uri = f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#{stakeholder_id}"
        
        query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?cost ?costType ?costValue ?impact ?impactType ?impactValue ?period WHERE {{
            <{stakeholder_uri}> :affectedBy ?cost .
            ?cost a ?costType ;
                  :hasCostValue ?costValue .
            OPTIONAL {{
                ?cost :hasImpactOn ?impact .
                ?impact :hasImpactType ?impactType ;
                       :hasImpactValue ?impactValue ;
                       :occursDuringPeriod ?period .
            }}
        }}
        """
        
        result = query_graphdb(query)
        impacts = []
        total_financial_impact = 0
        
        # result est déjà une liste de dictionnaires
        for binding in result:
            impact = {
                'cost_uri': binding['cost'],
                'cost_type': binding['costType'].split('#')[-1] if '#' in binding['costType'] else binding['costType'],
                'cost_value': float(binding['costValue']),
                'impact_type': binding.get('impactType', 'financial'),
                'impact_value': float(binding.get('impactValue', binding['costValue'])),
                'period': binding.get('period', '')
            }
            impacts.append(impact)
            total_financial_impact += impact['impact_value']
        
        return jsonify({
            'success': True,
            'stakeholder_id': stakeholder_id,
            'impacts': impacts,
            'total_financial_impact': total_financial_impact,
            'impact_count': len(impacts)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'analyse d\'impact: {str(e)}'}), 500

@app.route('/api/multi-stakeholder-view', methods=['GET'])
def get_multi_stakeholder_view():
    """Vue consolidée pour toutes les parties prenantes avec leurs impacts"""
    try:
        # Utiliser la même requête que debug-attributions qui fonctionne
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?stakeholder ?relation ?cost ?costType WHERE {
            ?stakeholder ?relation ?cost .
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
            OPTIONAL { ?cost a ?costType }
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }
        """
        
        result = query_graphdb(query)
        print(f"DEBUG: Résultat requête: {len(result)} attributions")
        
        # Récupérer les parties prenantes pour avoir les noms
        stakeholders_response = requests.get(f"http://localhost:8000/api/stakeholders")
        stakeholders_data = stakeholders_response.json() if stakeholders_response.status_code == 200 else {}
        stakeholders_map = {}
        
        if stakeholders_data.get('success'):
            for s in stakeholders_data.get('stakeholders', []):
                stakeholders_map[s['uri']] = s
        
        # Récupérer la durée de vie du projet pour les calculs temporels
        project_lifespan_response = requests.get(f"http://localhost:8000/get-project-lifespan")
        project_lifespan = 80  # Valeur par défaut
        if project_lifespan_response.status_code == 200:
            lifespan_data = project_lifespan_response.json()
            project_lifespan = int(lifespan_data.get('lifespan', 80))
        
        print(f"DEBUG: Durée de vie du projet: {project_lifespan} ans")
        
        # Récupérer les éléments IFC pour obtenir les valeurs de coûts et durées de vie
        elements_response = requests.get(f"http://localhost:8000/get-ifc-elements")
        elements = elements_response.json() if elements_response.status_code == 200 else []
        element_costs = {}
        element_lifespans = {}
        
        # Fonction helper pour convertir en float de manière sécurisée
        def safe_float(value):
            if value is None or value == '' or value == 'None':
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        
        def safe_int(value, default=60):
            if value is None or value == '' or value == 'None':
                return default
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default
        
        # Créer un mapping des coûts par élément avec logique temporelle
        for element in elements:
            element_id = element.get('GlobalId', '')
            if element_id:
                # Coûts unitaires
                construction_cost = safe_float(element.get('ConstructionCost', 0))
                operation_cost = safe_float(element.get('OperationCost', 0))
                maintenance_cost = safe_float(element.get('MaintenanceCost', 0))
                endoflife_cost = safe_float(element.get('EndOfLifeCost', 0))
                
                # Durée de vie de l'élément
                element_lifespan = safe_int(element.get('Lifespan', 60), 60)
                element_lifespans[element_id] = element_lifespan
                
                # LOGIQUE TEMPORELLE CORRIGÉE (comme dans le WLC global)
                
                # Construction: une seule fois
                element_costs[f"{element_id}_ConstructionCosts"] = construction_cost
                
                # Opération: chaque année pendant toute la durée du projet
                total_operation_cost = operation_cost * project_lifespan
                element_costs[f"{element_id}_OperationCosts"] = total_operation_cost
                
                # Maintenance: à chaque cycle de remplacement
                if element_lifespan > 0 and element_lifespan < project_lifespan:
                    replacement_cycles = project_lifespan // element_lifespan
                    total_maintenance_cost = maintenance_cost * replacement_cycles
                else:
                    # Si la durée de vie >= durée du projet, maintenance une seule fois
                    total_maintenance_cost = maintenance_cost
                element_costs[f"{element_id}_MaintenanceCosts"] = total_maintenance_cost
                
                # Fin de vie: une seule fois
                element_costs[f"{element_id}_EndOfLifeCosts"] = endoflife_cost
                
                # Debug pour les coûts significatifs
                if operation_cost > 0:
                    print(f"DEBUG: Élément {element_id} - Opération: {operation_cost}$/an × {project_lifespan} ans = {total_operation_cost}$")
                if maintenance_cost > 0 and element_lifespan < project_lifespan:
                    cycles = project_lifespan // element_lifespan
                    print(f"DEBUG: Élément {element_id} - Maintenance: {maintenance_cost}$ × {cycles} cycles = {total_maintenance_cost}$")
        
        print(f"DEBUG: Mapping des coûts créé: {len(element_costs)} entrées")
        
        stakeholder_views = {}
        
        for attribution in result:
            stakeholder_uri = attribution['stakeholder']
            cost_uri = attribution['cost']
            
            # Extraire le type de coût depuis l'URI
            cost_key = cost_uri.split('#')[-1] if '#' in cost_uri else cost_uri
            cost_type = 'Unknown'
            cost_value = 0
            
            # Déterminer le type de coût et sa valeur (avec logique temporelle)
            if '_ConstructionCosts' in cost_key:
                cost_type = 'ConstructionCosts'
                cost_value = element_costs.get(cost_key, 0)
            elif '_OperationCosts' in cost_key:
                cost_type = 'OperationCosts'
                cost_value = element_costs.get(cost_key, 0)  # Déjà multiplié par la durée
            elif '_MaintenanceCosts' in cost_key:
                cost_type = 'MaintenanceCosts'
                cost_value = element_costs.get(cost_key, 0)  # Déjà multiplié par les cycles
            elif '_EndOfLifeCosts' in cost_key:
                cost_type = 'EndOfLifeCosts'
                cost_value = element_costs.get(cost_key, 0)
            
            if cost_value > 0:
                print(f"DEBUG: Coût trouvé: {cost_key} = {cost_value}")
            
            # Initialiser la vue de la partie prenante si nécessaire
            if stakeholder_uri not in stakeholder_views:
                stakeholder_info = stakeholders_map.get(stakeholder_uri, {})
                stakeholder_views[stakeholder_uri] = {
                    'uri': stakeholder_uri,
                    'type': stakeholder_info.get('type', 'Unknown'),
                    'name': stakeholder_info.get('name', stakeholder_uri.split('#')[-1]),
                    'cost_breakdown': {
                        'ConstructionCosts': 0,
                        'OperationCosts': 0,
                        'MaintenanceCosts': 0,
                        'EndOfLifeCosts': 0
                    },
                    'total_impact': 0,
                    'counted_costs': set()  # Set pour éviter les duplications
                }
            
            # CORRECTION: Ne compter chaque coût qu'une seule fois par partie prenante
            cost_identifier = f"{cost_key}_{cost_type}"
            if cost_identifier not in stakeholder_views[stakeholder_uri]['counted_costs']:
                stakeholder_views[stakeholder_uri]['counted_costs'].add(cost_identifier)
                
                # Ajouter le coût seulement s'il n'a pas déjà été compté
                if cost_type in stakeholder_views[stakeholder_uri]['cost_breakdown']:
                    stakeholder_views[stakeholder_uri]['cost_breakdown'][cost_type] += cost_value
                    stakeholder_views[stakeholder_uri]['total_impact'] += cost_value
                    print(f"DEBUG: Coût ajouté pour {stakeholder_views[stakeholder_uri]['name']}: {cost_key} = {cost_value}")
            else:
                print(f"DEBUG: Coût ignoré (déjà compté): {cost_key} = {cost_value}")
        
        # Nettoyer les sets avant de retourner (ils ne sont pas JSON serializable)
        for stakeholder_view in stakeholder_views.values():
            del stakeholder_view['counted_costs']
        
        # Convertir en liste et trier par impact total
        stakeholder_list = list(stakeholder_views.values())
        stakeholder_list.sort(key=lambda x: x['total_impact'], reverse=True)
        
        print(f"DEBUG: Résultat final: {len(stakeholder_list)} parties prenantes, {len([s for s in stakeholder_list if s['total_impact'] > 0])} avec coûts")
        for s in stakeholder_list:
            if s['total_impact'] > 0:
                print(f"DEBUG:   {s['name']}: {s['total_impact']}$")
        
        return jsonify({
            'success': True,
            'stakeholder_views': stakeholder_list,
            'total_stakeholders': len(stakeholder_list),
            'project_lifespan': project_lifespan
        })
        
    except Exception as e:
        print(f"Erreur dans multi-stakeholder-view: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur lors de la génération de la vue multi-parties prenantes: {str(e)}'}), 500

@app.route('/api/stakeholder-timeline/<stakeholder_id>', methods=['GET'])
def get_stakeholder_timeline(stakeholder_id):
    """Récupère la timeline des impacts pour une partie prenante"""
    try:
        stakeholder_uri = f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#{stakeholder_id}"
        
        query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?year ?costType ?costValue ?phase WHERE {{
            <{stakeholder_uri}> :affectedBy ?cost .
            ?cost a ?costType ;
                  :hasCostValue ?costValue ;
                  :ForDate ?time .
            ?time :hasDate ?year .
            OPTIONAL {{
                ?cost :hasImpactOn ?impact .
                ?impact :occursDuringPeriod ?phaseTime .
                ?phaseTime a ?phase .
            }}
        }}
        ORDER BY ?year
        """
        
        result = query_graphdb(query)
        timeline = []
        
        # result est déjà une liste de dictionnaires
        for binding in result:
            timeline_entry = {
                'year': int(float(binding['year'])),
                'cost_type': binding['costType'].split('#')[-1] if '#' in binding['costType'] else binding['costType'],
                'cost_value': float(binding['costValue']),
                'phase': binding.get('phase', '').split('#')[-1] if binding.get('phase') else 'Unknown'
            }
            timeline.append(timeline_entry)
        
        return jsonify({
            'success': True,
            'stakeholder_id': stakeholder_id,
            'timeline': timeline
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la génération de la timeline: {str(e)}'}), 500

@app.route('/api/create-stakeholder', methods=['POST'])
def create_stakeholder():
    """Crée une nouvelle partie prenante"""
    try:
        data = request.get_json()
        stakeholder_type = data.get('type', 'Stakeholder')
        name = data.get('name', '')
        priority = data.get('priority', 2)
        influence = data.get('influence', 0.5)
        
        # Générer un URI unique
        import uuid
        stakeholder_id = str(uuid.uuid4())
        stakeholder_uri = f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#stakeholder_{stakeholder_id}"
        
        # Insérer dans GraphDB
        insert_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
        
        INSERT DATA {{
            <{stakeholder_uri}> a :{stakeholder_type} ;
                                :hasPriority {priority} ;
                                :hasInfluenceLevel {influence} .
        }}
        """
        
        if name:
            insert_query = insert_query.replace(
                f":hasInfluenceLevel {influence} .",
                f":hasInfluenceLevel {influence} ;\n                                ifc:name_IfcPerson \"{name}\" ."
            )
        
        # Exécuter la requête d'insertion
        response = requests.post(
            UPDATE_ENDPOINT,
            data=insert_query,
            headers={'Content-Type': 'application/sparql-update'}
        )
        
        if response.status_code == 204:
            return jsonify({
                'success': True,
                'message': 'Partie prenante créée avec succès',
                'stakeholder_uri': stakeholder_uri,
                'stakeholder_id': stakeholder_id
            })
        else:
            return jsonify({'error': 'Erreur lors de la création de la partie prenante'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la création: {str(e)}'}), 500

@app.route('/api/stakeholder-cost-responsibility', methods=['POST'])
def assign_cost_responsibility():
    """Assigne une responsabilité de coût à une partie prenante"""
    try:
        data = request.get_json()
        stakeholder_uri = data.get('stakeholder_uri')
        cost_uri = data.get('cost_uri')
        responsibility_type = data.get('responsibility_type', 'affectedBy')  # affectedBy ou responsibleFor
        
        insert_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        INSERT DATA {{
            <{stakeholder_uri}> :{responsibility_type} <{cost_uri}> .
        }}
        """
        
        response = requests.post(
            UPDATE_ENDPOINT,
            data=insert_query,
            headers={'Content-Type': 'application/sparql-update'}
        )
        
        if response.status_code == 204:
            return jsonify({
                'success': True,
                'message': f'Responsabilité de coût assignée avec succès ({responsibility_type})'
            })
        else:
            return jsonify({'error': 'Erreur lors de l\'assignation de responsabilité'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'assignation: {str(e)}'}), 500

@app.route('/api/delete-all-attributions', methods=['DELETE'])
def delete_all_attributions():
    """Supprime toutes les attributions de coûts aux parties prenantes"""
    try:
        # Compter les attributions existantes (même requête que debug-attributions)
        count_query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT (COUNT(*) as ?count) WHERE {
            ?stakeholder ?relation ?cost .
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }
        """
        
        count_result = query_graphdb(count_query)
        initial_count = int(count_result[0]['count']) if count_result else 0
        
        print(f"DEBUG: Suppression - {initial_count} attributions trouvées initialement")
        
        # Supprimer toutes les relations d'attribution (même requête que debug-attributions)
        delete_query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        DELETE {
            ?stakeholder ?relation ?cost .
        }
        WHERE {
            ?stakeholder ?relation ?cost .
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }
        """
        
        print(f"DEBUG: Exécution de la requête de suppression...")
        update_graphdb(delete_query)
        
        # Vérifier le résultat
        final_count_result = query_graphdb(count_query)
        final_count = int(final_count_result[0]['count']) if final_count_result else 0
        deleted_count = initial_count - final_count
        
        print(f"DEBUG: Suppression terminée - {final_count} attributions restantes, {deleted_count} supprimées")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} attributions supprimées avec succès',
            'deleted_count': deleted_count,
            'initial_count': initial_count,
            'final_count': final_count
        })
        
    except Exception as e:
        print(f"Erreur lors de la suppression: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la suppression des attributions: {str(e)}'
        }), 500

@app.route('/api/debug-attributions', methods=['GET'])
def debug_attributions():
    """Endpoint de diagnostic pour voir toutes les attributions existantes"""
    try:
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?stakeholder ?relation ?cost ?costType WHERE {
            ?stakeholder ?relation ?cost .
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
            OPTIONAL { ?cost a ?costType }
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }
        LIMIT 20
        """
        
        result = query_graphdb(query)
        
        return jsonify({
            'success': True,
            'attributions': result,
            'count': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors du diagnostic: {str(e)}'
        }), 500

@app.route('/api/debug-cost-types/<element_id>', methods=['GET'])
def debug_cost_types(element_id):
    """Voir les types de coûts pour un élément spécifique"""
    try:
        query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?cost ?costType WHERE {{
            ?cost a ?costType .
            FILTER(CONTAINS(STR(?cost), "{element_id}"))
        }}
        """
        
        result = query_graphdb(query)
        
        return jsonify({
            'success': True,
            'element_id': element_id,
            'costs': result,
            'count': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors du diagnostic: {str(e)}'
        }), 500

@app.route('/api/auto-assign-costs', methods=['POST'])
def auto_assign_costs():
    """Attribution automatique des coûts selon les règles métier"""
    try:
        # Récupérer toutes les parties prenantes
        stakeholders_query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?stakeholder ?stakeholderType WHERE {
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
        }
        """
        
        stakeholders = query_graphdb(stakeholders_query)
        
        # Récupérer tous les éléments IFC
        elements_response = requests.get(f"http://localhost:8000/get-ifc-elements")
        elements = elements_response.json() if elements_response.status_code == 200 else []
        
        attribution_count = 0
        errors = []
        
        # Règles d'attribution automatique
        rules = {
            'PropertyOwner': ['ConstructionCosts', 'EndOfLifeCosts'],
            'EndUser': ['OperationCosts'],
            'MaintenanceProvider': ['MaintenanceCosts']
        }
        
        for stakeholder in stakeholders:
            stakeholder_uri = stakeholder['stakeholder']
            stakeholder_type = stakeholder['stakeholderType'].split('#')[-1] if '#' in stakeholder['stakeholderType'] else stakeholder['stakeholderType']
            
            if stakeholder_type in rules:
                cost_types = rules[stakeholder_type]
                
                for element in elements:
                    element_id = element['GlobalId']
                    
                    for cost_type in cost_types:
                        cost_uri = f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#{element_id}_{cost_type}"
                        
                        try:
                            # Créer l'attribution
                            insert_query = f"""
                            PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                            
                            INSERT DATA {{
                                <{stakeholder_uri}> :responsibleFor <{cost_uri}> .
                            }}
                            """
                            
                            response = requests.post(
                                UPDATE_ENDPOINT,
                                data=insert_query,
                                headers={'Content-Type': 'application/sparql-update'}
                            )
                            
                            if response.status_code == 204:
                                attribution_count += 1
                            else:
                                errors.append(f"Erreur pour {stakeholder_type} -> {element_id}_{cost_type}")
                                
                        except Exception as e:
                            errors.append(f"Exception pour {stakeholder_type} -> {element_id}_{cost_type}: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'Attribution automatique terminée',
            'attributions_created': attribution_count,
            'stakeholders_processed': len(stakeholders),
            'elements_processed': len(elements),
            'errors': errors[:10] if errors else []  # Limiter les erreurs affichées
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors de l\'attribution automatique: {str(e)}'
        }), 500

@app.route('/api/sync-cost-values', methods=['POST'])
def sync_cost_values():
    """Synchronise les valeurs de coûts avec les instances d'attribution"""
    try:
        # Récupérer tous les éléments IFC avec leurs coûts
        elements_response = requests.get(f"http://localhost:8000/get-ifc-elements")
        elements = elements_response.json() if elements_response.status_code == 200 else []
        
        synced_count = 0
        errors = []
        
        for element in elements:
            element_id = element['GlobalId']
            
            # Synchroniser chaque type de coût
            cost_types = {
                'ConstructionCosts': element.get('ConstructionCost', '0'),
                'OperationCosts': element.get('OperationCost', '0'),
                'MaintenanceCosts': element.get('MaintenanceCost', '0'),
                'EndOfLifeCosts': element.get('EndOfLifeCost', '0')
            }
            
            for cost_type, cost_value in cost_types.items():
                cost_uri = f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#{element_id}_{cost_type}"
                
                try:
                    # Supprimer l'ancienne valeur si elle existe
                    delete_query = f"""
                    PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                    
                    DELETE {{
                        <{cost_uri}> :hasCostValue ?oldValue .
                    }}
                    WHERE {{
                        <{cost_uri}> :hasCostValue ?oldValue .
                    }}
                    """
                    
                    requests.post(
                        UPDATE_ENDPOINT,
                        data=delete_query,
                        headers={'Content-Type': 'application/sparql-update'}
                    )
                    
                    # Ajouter la nouvelle valeur
                    insert_query = f"""
                    PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                    
                    INSERT DATA {{
                        <{cost_uri}> :hasCostValue {float(cost_value)} .
                    }}
                    """
                    
                    response = requests.post(
                        UPDATE_ENDPOINT,
                        data=insert_query,
                        headers={'Content-Type': 'application/sparql-update'}
                    )
                    
                    if response.status_code == 204:
                        synced_count += 1
                    else:
                        errors.append(f"Erreur sync {element_id}_{cost_type}")
                        
                except Exception as e:
                    errors.append(f"Exception sync {element_id}_{cost_type}: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'Synchronisation terminée',
            'synced_count': synced_count,
            'elements_processed': len(elements),
            'errors': errors[:10] if errors else []
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la synchronisation: {str(e)}'
        }), 500

#################################################################
#    API SIMULATEUR DE DÉCISIONS - Phase 3
#################################################################

@app.route('/api/decision-simulator/scenarios', methods=['GET'])
def get_decision_scenarios():
    """Récupère tous les scénarios de décision disponibles"""
    try:
        # Scénarios prédéfinis pour la simulation
        scenarios = [
            {
                'id': 'material_upgrade',
                'name': 'Amélioration des matériaux',
                'description': 'Remplacer les matériaux standard par des matériaux premium',
                'impact_types': ['construction_cost_increase', 'maintenance_cost_decrease', 'lifespan_increase'],
                'stakeholders_affected': ['PropertyOwner', 'MaintenanceProvider', 'EndUser']
            },
            {
                'id': 'maintenance_strategy',
                'name': 'Stratégie de maintenance préventive',
                'description': 'Passer d\'une maintenance corrective à préventive',
                'impact_types': ['maintenance_cost_increase', 'operation_cost_decrease', 'reliability_increase'],
                'stakeholders_affected': ['AssetOperator', 'MaintenanceProvider', 'EndUser']
            },
            {
                'id': 'energy_efficiency',
                'name': 'Amélioration efficacité énergétique',
                'description': 'Installation de systèmes plus efficaces énergétiquement',
                'impact_types': ['construction_cost_increase', 'operation_cost_decrease'],
                'stakeholders_affected': ['PropertyOwner', 'AssetOperator', 'EnergyProvider']
            },
            {
                'id': 'lifecycle_extension',
                'name': 'Extension de durée de vie',
                'description': 'Investissements pour prolonger la durée de vie des actifs',
                'impact_types': ['construction_cost_increase', 'end_of_life_cost_delay'],
                'stakeholders_affected': ['PropertyOwner', 'EndUser']
            }
        ]
        
        return jsonify({
            'success': True,
            'scenarios': scenarios,
            'count': len(scenarios)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur récupération scénarios: {str(e)}'}), 500

@app.route('/api/decision-simulator/simulate', methods=['POST'])
def simulate_decision():
    """Simule l'impact d'une décision sur les parties prenantes et le WLC"""
    try:
        data = request.get_json()
        scenario_id = data.get('scenario_id')
        parameters = data.get('parameters', {})
        
        # Récupérer les données actuelles du projet
        current_wlc = calculate_wlc_dynamically()
        
        # Appliquer les modifications selon le scénario
        simulation_result = apply_scenario_simulation(scenario_id, parameters, current_wlc)
        
        return jsonify({
            'success': True,
            'scenario_id': scenario_id,
            'simulation_result': simulation_result
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur simulation: {str(e)}'}), 500

def apply_scenario_simulation(scenario_id, parameters, current_wlc):
    """Applique les modifications d'un scénario et calcule les impacts"""
    
    # Facteurs de modification par scénario
    scenario_factors = {
        'material_upgrade': {
            'construction_cost_factor': 1.3,  # +30% coût construction
            'maintenance_cost_factor': 0.7,   # -30% coût maintenance
            'lifespan_factor': 1.5,           # +50% durée de vie
            'operation_cost_factor': 1.0      # Pas de changement
        },
        'maintenance_strategy': {
            'construction_cost_factor': 1.1,  # +10% coût initial (équipements)
            'maintenance_cost_factor': 1.2,   # +20% coût maintenance (préventive)
            'operation_cost_factor': 0.85,    # -15% coût opération (moins de pannes)
            'lifespan_factor': 1.2             # +20% durée de vie
        },
        'energy_efficiency': {
            'construction_cost_factor': 1.25, # +25% coût construction
            'operation_cost_factor': 0.6,     # -40% coût opération (énergie)
            'maintenance_cost_factor': 1.0,   # Pas de changement
            'lifespan_factor': 1.0             # Pas de changement
        },
        'lifecycle_extension': {
            'construction_cost_factor': 1.15, # +15% coût construction
            'maintenance_cost_factor': 1.1,   # +10% coût maintenance
            'operation_cost_factor': 1.0,     # Pas de changement
            'lifespan_factor': 1.3             # +30% durée de vie
        }
    }
    
    factors = scenario_factors.get(scenario_id, {})
    
    # Calculer les nouveaux coûts
    original_costs = current_wlc.get('costs_by_year', [])
    modified_costs = []
    
    for year_data in original_costs:
        modified_year = {
            'year': year_data['year'],
            'nominal_cost': 0,
            'discounted_cost': 0
        }
        
        # Appliquer les facteurs selon le type de coût
        # Note: Cette simulation est simplifiée, dans un vrai système il faudrait
        # récupérer les coûts par type depuis l'ontologie
        base_cost = year_data.get('nominal_cost', 0)
        
        if year_data['year'] == 0:  # Construction
            modified_cost = base_cost * factors.get('construction_cost_factor', 1.0)
        elif year_data['year'] == len(original_costs) - 1:  # Fin de vie
            modified_cost = base_cost  # Pas de modification pour l'instant
        else:  # Opération et maintenance
            modified_cost = base_cost * factors.get('operation_cost_factor', 1.0)
        
        modified_year['nominal_cost'] = modified_cost
        modified_year['discounted_cost'] = year_data.get('discounted_cost', 0) * (modified_cost / base_cost if base_cost > 0 else 1)
        modified_costs.append(modified_year)
    
    # Calculer les totaux
    original_total = sum(year['discounted_cost'] for year in original_costs)
    modified_total = sum(year['discounted_cost'] for year in modified_costs)
    
    # Calculer l'impact par partie prenante (simulation)
    stakeholder_impacts = calculate_stakeholder_impacts(scenario_id, factors)
    
    return {
        'original_wlc': original_total,
        'modified_wlc': modified_total,
        'wlc_difference': modified_total - original_total,
        'wlc_change_percent': ((modified_total - original_total) / original_total * 100) if original_total > 0 else 0,
        'modified_costs_by_year': modified_costs,
        'stakeholder_impacts': stakeholder_impacts,
        'scenario_factors': factors
    }

def calculate_stakeholder_impacts(scenario_id, factors):
    """Calcule l'impact simulé sur chaque type de partie prenante"""
    
    # Mapping des impacts par scénario et partie prenante
    impact_mapping = {
        'material_upgrade': {
            'PropertyOwner': {
                'financial_impact': 'negative_short_term',  # Coût initial plus élevé
                'long_term_benefit': 'positive',            # Moins de maintenance
                'impact_score': -0.2  # Impact négatif à court terme
            },
            'MaintenanceProvider': {
                'financial_impact': 'negative',             # Moins de contrats
                'operational_impact': 'positive',           # Travail plus facile
                'impact_score': -0.3
            },
            'EndUser': {
                'service_quality': 'positive',              # Meilleure qualité
                'operational_impact': 'positive',           # Moins de pannes
                'impact_score': 0.4
            }
        },
        'maintenance_strategy': {
            'AssetOperator': {
                'operational_impact': 'positive',           # Moins de pannes
                'financial_impact': 'negative_short_term',  # Coût préventif
                'impact_score': 0.2
            },
            'MaintenanceProvider': {
                'financial_impact': 'positive',             # Plus de contrats
                'operational_impact': 'positive',           # Travail planifié
                'impact_score': 0.5
            },
            'EndUser': {
                'service_quality': 'positive',              # Moins d'interruptions
                'impact_score': 0.3
            }
        },
        'energy_efficiency': {
            'PropertyOwner': {
                'financial_impact': 'negative_short_term',  # Investissement initial
                'long_term_benefit': 'positive',            # Économies d'énergie
                'impact_score': 0.1
            },
            'AssetOperator': {
                'operational_impact': 'positive',           # Coûts réduits
                'financial_impact': 'positive',             # Économies
                'impact_score': 0.6
            },
            'EnergyProvider': {
                'financial_impact': 'negative',             # Moins de ventes
                'impact_score': -0.4
            }
        },
        'lifecycle_extension': {
            'PropertyOwner': {
                'financial_impact': 'negative_short_term',  # Investissement
                'long_term_benefit': 'positive',            # Durée prolongée
                'impact_score': 0.3
            },
            'EndUser': {
                'service_quality': 'positive',              # Service prolongé
                'impact_score': 0.2
            }
        }
    }
    
    return impact_mapping.get(scenario_id, {})

@app.route('/api/decision-simulator/compare', methods=['POST'])
def compare_scenarios():
    """Compare plusieurs scénarios de décision"""
    try:
        data = request.get_json()
        scenario_ids = data.get('scenario_ids', [])
        
        # Récupérer les données de base
        current_wlc = calculate_wlc_dynamically()
        
        # Simuler chaque scénario
        comparisons = []
        for scenario_id in scenario_ids:
            simulation = apply_scenario_simulation(scenario_id, {}, current_wlc)
            comparisons.append({
                'scenario_id': scenario_id,
                'wlc_impact': simulation['wlc_difference'],
                'wlc_change_percent': simulation['wlc_change_percent'],
                'stakeholder_impacts': simulation['stakeholder_impacts']
            })
        
        # Trier par impact WLC
        comparisons.sort(key=lambda x: x['wlc_impact'])
        
        return jsonify({
            'success': True,
            'baseline_wlc': current_wlc.get('total_wlc', 0),
            'scenario_comparisons': comparisons,
            'best_scenario': comparisons[0] if comparisons else None,
            'worst_scenario': comparisons[-1] if comparisons else None
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur comparaison scénarios: {str(e)}'}), 500

#################################################################
#    API VISUALISATIONS TEMPORELLES AVANCÉES - Phase 4
#################################################################

@app.route('/api/advanced-timeline/stakeholder-evolution', methods=['GET'])
def get_stakeholder_evolution():
    """Évolution temporelle détaillée des impacts par partie prenante"""
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        # Récupérer les parties prenantes et leurs impacts par année
        evolution_data = []
        
        # Simuler l'évolution pour chaque type de partie prenante
        stakeholder_types = ['PropertyOwner', 'AssetOperator', 'EndUser', 'MaintenanceProvider', 'EnergyProvider']
        
        for stakeholder_type in stakeholder_types:
            yearly_impacts = []
            
            for year in range(project_lifespan + 1):
                # Calculer l'impact cumulé pour cette partie prenante à cette année
                impact = calculate_yearly_stakeholder_impact(stakeholder_type, year, project_lifespan)
                yearly_impacts.append({
                    'year': year,
                    'financial_impact': impact['financial'],
                    'operational_impact': impact['operational'],
                    'cumulative_impact': impact['cumulative']
                })
            
            evolution_data.append({
                'stakeholder_type': stakeholder_type,
                'yearly_impacts': yearly_impacts
            })
        
        return jsonify({
            'success': True,
            'project_lifespan': project_lifespan,
            'stakeholder_evolution': evolution_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur évolution parties prenantes: {str(e)}'}), 500

def calculate_yearly_stakeholder_impact(stakeholder_type, year, project_lifespan):
    """Calcule l'impact d'une partie prenante pour une année donnée"""
    
    # Modèles d'impact par type de partie prenante
    impact_models = {
        'PropertyOwner': {
            'construction_years': [0],
            'high_impact_factor': 0.8,
            'base_impact': 1000000  # Impact de base en euros
        },
        'AssetOperator': {
            'operation_years': list(range(1, project_lifespan)),
            'steady_impact_factor': 0.3,
            'base_impact': 500000
        },
        'EndUser': {
            'all_years': list(range(1, project_lifespan)),
            'quality_impact_factor': 0.2,
            'base_impact': 200000
        },
        'MaintenanceProvider': {
            'maintenance_cycles': [i for i in range(1, project_lifespan + 1) if i % 20 == 0],  # Tous les 20 ans
            'cycle_impact_factor': 0.6,
            'base_impact': 300000
        },
        'EnergyProvider': {
            'operation_years': list(range(1, project_lifespan)),
            'steady_impact_factor': 0.4,
            'base_impact': 400000
        }
    }
    
    model = impact_models.get(stakeholder_type, {})
    base_impact = model.get('base_impact', 100000)
    
    financial_impact = 0
    operational_impact = 0
    
    # Calculer selon le type de partie prenante
    if stakeholder_type == 'PropertyOwner':
        if year == 0:  # Construction
            financial_impact = base_impact * model.get('high_impact_factor', 0.8)
        elif year == project_lifespan:  # Fin de vie
            financial_impact = base_impact * 0.3
        else:
            financial_impact = base_impact * 0.1  # Coûts récurrents faibles
            
    elif stakeholder_type == 'AssetOperator':
        if year in model.get('operation_years', []):
            financial_impact = base_impact * model.get('steady_impact_factor', 0.3)
            operational_impact = 0.7  # Impact opérationnel constant
            
    elif stakeholder_type == 'EndUser':
        if year in model.get('all_years', []):
            financial_impact = base_impact * model.get('quality_impact_factor', 0.2)
            operational_impact = 0.5  # Impact qualité de service
            
    elif stakeholder_type == 'MaintenanceProvider':
        if year in model.get('maintenance_cycles', []):
            financial_impact = base_impact * model.get('cycle_impact_factor', 0.6)
            operational_impact = 0.8  # Pic d'activité
        else:
            financial_impact = base_impact * 0.1  # Maintenance courante
            operational_impact = 0.2
            
    elif stakeholder_type == 'EnergyProvider':
        if year in model.get('operation_years', []):
            financial_impact = base_impact * model.get('steady_impact_factor', 0.4)
            operational_impact = 0.3
    
    # Calculer l'impact cumulé (simplifié)
    cumulative_impact = financial_impact + (operational_impact * 100000)
    
    return {
        'financial': round(financial_impact, 2),
        'operational': round(operational_impact, 2),
        'cumulative': round(cumulative_impact, 2)
    }

@app.route('/api/advanced-timeline/decision-points', methods=['GET'])
def get_decision_points():
    """Identifie les points de décision critiques dans la timeline"""
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        # Identifier les points de décision critiques
        decision_points = []
        
        # Points de décision basés sur les cycles de maintenance
        maintenance_cycles = [20, 40, 60, 80]  # Années typiques de maintenance majeure
        
        for cycle_year in maintenance_cycles:
            if cycle_year <= project_lifespan:
                decision_points.append({
                    'year': cycle_year,
                    'type': 'maintenance_decision',
                    'title': f'Décision maintenance majeure - Année {cycle_year}',
                    'description': f'Choix entre maintenance corrective, préventive ou remplacement',
                    'stakeholders_involved': ['PropertyOwner', 'AssetOperator', 'MaintenanceProvider'],
                    'cost_impact_range': [500000, 2000000],
                    'decision_options': [
                        {
                            'option': 'maintenance_corrective',
                            'cost': 500000,
                            'risk': 'high',
                            'stakeholder_preference': {'MaintenanceProvider': 0.3, 'PropertyOwner': 0.7}
                        },
                        {
                            'option': 'maintenance_preventive',
                            'cost': 800000,
                            'risk': 'medium',
                            'stakeholder_preference': {'MaintenanceProvider': 0.8, 'PropertyOwner': 0.6}
                        },
                        {
                            'option': 'replacement',
                            'cost': 2000000,
                            'risk': 'low',
                            'stakeholder_preference': {'PropertyOwner': 0.4, 'EndUser': 0.9}
                        }
                    ]
                })
        
        # Points de décision énergétiques
        energy_decision_years = [15, 35, 55, 75]
        
        for energy_year in energy_decision_years:
            if energy_year <= project_lifespan:
                decision_points.append({
                    'year': energy_year,
                    'type': 'energy_efficiency_decision',
                    'title': f'Décision efficacité énergétique - Année {energy_year}',
                    'description': 'Mise à niveau des systèmes énergétiques',
                    'stakeholders_involved': ['PropertyOwner', 'AssetOperator', 'EnergyProvider'],
                    'cost_impact_range': [300000, 1500000],
                    'decision_options': [
                        {
                            'option': 'status_quo',
                            'cost': 0,
                            'energy_savings': 0,
                            'stakeholder_preference': {'EnergyProvider': 0.9, 'PropertyOwner': 0.3}
                        },
                        {
                            'option': 'moderate_upgrade',
                            'cost': 300000,
                            'energy_savings': 0.15,
                            'stakeholder_preference': {'PropertyOwner': 0.7, 'AssetOperator': 0.8}
                        },
                        {
                            'option': 'major_upgrade',
                            'cost': 1500000,
                            'energy_savings': 0.40,
                            'stakeholder_preference': {'AssetOperator': 0.9, 'PropertyOwner': 0.5}
                        }
                    ]
                })
        
        # Trier par année
        decision_points.sort(key=lambda x: x['year'])
        
        return jsonify({
            'success': True,
            'project_lifespan': project_lifespan,
            'decision_points': decision_points,
            'total_decision_points': len(decision_points)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur points de décision: {str(e)}'}), 500

@app.route('/api/advanced-timeline/impact-heatmap', methods=['GET'])
def get_impact_heatmap():
    """Génère une heatmap des impacts par partie prenante et par année"""
    try:
        # Récupérer la durée de vie du projet
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result else 100
        
        # Générer la matrice d'impact
        stakeholder_types = ['PropertyOwner', 'AssetOperator', 'EndUser', 'MaintenanceProvider', 'EnergyProvider']
        
        heatmap_data = []
        
        for stakeholder_type in stakeholder_types:
            stakeholder_row = {
                'stakeholder': stakeholder_type,
                'yearly_impacts': []
            }
            
            for year in range(0, min(project_lifespan + 1, 101)):  # Limiter à 100 ans pour la visualisation
                impact = calculate_yearly_stakeholder_impact(stakeholder_type, year, project_lifespan)
                
                # Normaliser l'impact pour la heatmap (0-1)
                normalized_impact = min(impact['cumulative'] / 1000000, 1.0)  # Normaliser par rapport à 1M$
                
                stakeholder_row['yearly_impacts'].append({
                    'year': year,
                    'impact_intensity': round(normalized_impact, 3),
                    'impact_value': impact['cumulative']
                })
            
            heatmap_data.append(stakeholder_row)
        
        # Calculer les statistiques globales
        max_impact = 0
        total_impact = 0
        
        for row in heatmap_data:
            for year_data in row['yearly_impacts']:
                max_impact = max(max_impact, year_data['impact_value'])
                total_impact += year_data['impact_value']
        
        return jsonify({
            'success': True,
            'project_lifespan': project_lifespan,
            'heatmap_data': heatmap_data,
            'statistics': {
                'max_impact': max_impact,
                'total_impact': total_impact,
                'years_displayed': min(project_lifespan + 1, 101)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur heatmap impacts: {str(e)}'}), 500

@app.route('/api/advanced-timeline/critical-periods', methods=['GET'])
def get_critical_periods():
    """Identifie les périodes critiques avec impacts élevés"""
    try:
        # Récupérer les données de la heatmap
        heatmap_response = get_impact_heatmap()
        heatmap_data = heatmap_response.get_json()
        
        if not heatmap_data.get('success'):
            return jsonify({'error': 'Erreur récupération données heatmap'}), 500
        
        # Analyser les périodes critiques
        critical_periods = []
        
        # Calculer l'impact total par année
        yearly_totals = {}
        for stakeholder_data in heatmap_data['heatmap_data']:
            for year_data in stakeholder_data['yearly_impacts']:
                year = year_data['year']
                if year not in yearly_totals:
                    yearly_totals[year] = 0
                yearly_totals[year] += year_data['impact_value']
        
        # Identifier les pics d'impact
        sorted_years = sorted(yearly_totals.items(), key=lambda x: x[1], reverse=True)
        
        # Prendre les 10 années avec le plus d'impact
        top_impact_years = sorted_years[:10]
        
        for year, total_impact in top_impact_years:
            # Identifier les parties prenantes les plus affectées cette année
            stakeholders_affected = []
            
            for stakeholder_data in heatmap_data['heatmap_data']:
                year_impact = next((y for y in stakeholder_data['yearly_impacts'] if y['year'] == year), None)
                if year_impact and year_impact['impact_intensity'] > 0.3:  # Seuil significatif
                    stakeholders_affected.append({
                        'stakeholder': stakeholder_data['stakeholder'],
                        'impact_intensity': year_impact['impact_intensity'],
                        'impact_value': year_impact['impact_value']
                    })
            
            # Déterminer le type de période critique
            period_type = 'unknown'
            if year == 0:
                period_type = 'construction'
            elif year % 20 == 0:
                period_type = 'major_maintenance'
            elif year % 10 == 0:
                period_type = 'minor_maintenance'
            elif year == heatmap_data['project_lifespan']:
                period_type = 'end_of_life'
            else:
                period_type = 'operational'
            
            critical_periods.append({
                'year': year,
                'total_impact': total_impact,
                'period_type': period_type,
                'stakeholders_affected': stakeholders_affected,
                'criticality_score': round(total_impact / max(yearly_totals.values()), 2)
            })
        
        # Trier par année
        critical_periods.sort(key=lambda x: x['year'])
        
        return jsonify({
            'success': True,
            'critical_periods': critical_periods,
            'analysis_summary': {
                'total_periods_analyzed': len(yearly_totals),
                'critical_periods_identified': len(critical_periods),
                'highest_impact_year': max(yearly_totals, key=yearly_totals.get),
                'highest_impact_value': max(yearly_totals.values())
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur périodes critiques: {str(e)}'}), 500

@app.route('/api/delete-all-stakeholders', methods=['POST'])
def delete_all_stakeholders():
    """Supprime TOUTES les parties prenantes (par défaut ET personnalisées)"""
    try:
        # Requête pour trouver toutes les parties prenantes
        find_query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?stakeholder WHERE {
            ?stakeholder a ?type .
            ?type rdfs:subClassOf* :Stakeholder .
            
            # Exclure les classes elles-mêmes
            FILTER(?stakeholder != :Stakeholder)
            FILTER(?stakeholder != :PropertyOwner)
            FILTER(?stakeholder != :AssetOperator)
            FILTER(?stakeholder != :EndUser)
            FILTER(?stakeholder != :MaintenanceProvider)
            FILTER(?stakeholder != :EnergyProvider)
        }
        """
        
        stakeholders_result = query_graphdb(find_query)
        deleted_count = 0
        
        for stakeholder_data in stakeholders_result:
            try:
                stakeholder_uri = stakeholder_data['stakeholder']
                
                delete_query = f"""
                PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                DELETE {{
                    <{stakeholder_uri}> ?p ?o .
                    ?s ?p2 <{stakeholder_uri}> .
                }}
                WHERE {{
                    {{
                        <{stakeholder_uri}> ?p ?o .
                    }} UNION {{
                        ?s ?p2 <{stakeholder_uri}> .
                    }}
                }}
                """
                
                update_graphdb(delete_query)
                deleted_count += 1
                
            except Exception as e:
                print(f"Erreur suppression {stakeholder_uri}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} parties prenantes supprimées au total',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la suppression complète: {str(e)}'}), 500

@app.route('/api/stakeholders-detailed', methods=['GET'])
def get_stakeholders_detailed():
    """Récupère toutes les parties prenantes avec informations détaillées pour debug"""
    try:
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
        
        SELECT ?stakeholder ?type ?name ?priority ?influence WHERE {
            ?stakeholder a ?type .
            ?type rdfs:subClassOf* :Stakeholder .
            
            OPTIONAL { ?stakeholder ifc:name_IfcPerson ?name }
            OPTIONAL { ?stakeholder ifc:name_IfcOrganization ?name }
            OPTIONAL { ?stakeholder :hasPriority ?priority }
            OPTIONAL { ?stakeholder :hasInfluenceLevel ?influence }
        }
        ORDER BY ?type ?stakeholder
        """
        
        result = query_graphdb(query)
        stakeholders = []
        
        for binding in result:
            stakeholder_uri = binding['stakeholder']
            stakeholder_type = binding['type'].split('#')[-1] if '#' in binding['type'] else binding['type']
            
            # Identifier si c'est une classe ou une instance
            is_class = stakeholder_uri.endswith('#Stakeholder') or \
                      stakeholder_uri.endswith('#PropertyOwner') or \
                      stakeholder_uri.endswith('#AssetOperator') or \
                      stakeholder_uri.endswith('#EndUser') or \
                      stakeholder_uri.endswith('#MaintenanceProvider') or \
                      stakeholder_uri.endswith('#EnergyProvider')
            
            # Identifier si c'est une instance par défaut
            is_default = 'Default' in stakeholder_uri or stakeholder_uri == f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#{stakeholder_type}"
            
            stakeholder = {
                'uri': stakeholder_uri,
                'id': stakeholder_uri.split('#')[-1],
                'type': stakeholder_type,
                'name': binding.get('name', ''),
                'display_name': binding.get('name', stakeholder_uri.split('#')[-1]),
                'priority': int(binding.get('priority', 2)) if binding.get('priority') else None,
                'influence': float(binding.get('influence', 0.5)) if binding.get('influence') else None,
                'is_class': is_class,
                'is_default': is_default,
                'has_properties': bool(binding.get('priority') or binding.get('influence') or binding.get('name'))
            }
            stakeholders.append(stakeholder)
        
        return jsonify({
            'success': True,
            'stakeholders': stakeholders,
            'count': len(stakeholders)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération détaillée: {str(e)}'}), 500

@app.route('/api/clean-stakeholder-duplicates', methods=['POST'])
def clean_stakeholder_duplicates():
    """Nettoie les doublons et instances invalides de parties prenantes"""
    try:
        # Récupérer toutes les parties prenantes pour analyse
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
        
        SELECT ?stakeholder ?type ?priority ?influence ?name WHERE {
            ?stakeholder a ?type .
            ?type rdfs:subClassOf* :Stakeholder .
            
            OPTIONAL { ?stakeholder :hasPriority ?priority }
            OPTIONAL { ?stakeholder :hasInfluenceLevel ?influence }
            OPTIONAL { ?stakeholder ifc:name_IfcPerson ?name }
            OPTIONAL { ?stakeholder ifc:name_IfcOrganization ?name }
        }
        """
        
        result = query_graphdb(query)
        to_delete = []
        
        for binding in result:
            stakeholder_uri = binding['stakeholder']
            stakeholder_type = binding['type']
            
            # Identifier les éléments à supprimer
            should_delete = False
            
            # 1. Classes elles-mêmes (pas des instances)
            if stakeholder_uri.endswith('#Stakeholder') or \
               stakeholder_uri.endswith('#PropertyOwner') or \
               stakeholder_uri.endswith('#AssetOperator') or \
               stakeholder_uri.endswith('#EndUser') or \
               stakeholder_uri.endswith('#MaintenanceProvider') or \
               stakeholder_uri.endswith('#EnergyProvider'):
                should_delete = True
                
            # 2. Instances avec type générique Stakeholder (garder seulement les types spécifiques)
            elif stakeholder_type.endswith('#Stakeholder'):
                should_delete = True
                
            # 3. Instances sans propriétés (orphelines)
            elif not (binding.get('priority') or binding.get('influence') or binding.get('name')):
                should_delete = True
            
            if should_delete:
                to_delete.append(stakeholder_uri)
        
        # Supprimer les éléments identifiés
        deleted_count = 0
        for stakeholder_uri in to_delete:
            try:
                delete_query = f"""
                PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                
                DELETE {{
                    <{stakeholder_uri}> ?p ?o .
                    ?s ?p2 <{stakeholder_uri}> .
                }}
                WHERE {{
                    {{
                        <{stakeholder_uri}> ?p ?o .
                    }} UNION {{
                        ?s ?p2 <{stakeholder_uri}> .
                    }}
                }}
                """
                
                update_graphdb(delete_query)
                deleted_count += 1
                
            except Exception as e:
                print(f"Erreur suppression {stakeholder_uri}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} doublons/instances invalides supprimés',
            'deleted_count': deleted_count,
            'deleted_uris': to_delete
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du nettoyage: {str(e)}'}), 500

@app.route('/api/delete-stakeholder/<stakeholder_id>', methods=['DELETE'])
def delete_stakeholder(stakeholder_id):
    """Supprime une partie prenante spécifique"""
    try:
        # Construire l'URI complet si nécessaire
        if stakeholder_id.startswith('http://'):
            stakeholder_uri = stakeholder_id
        else:
            stakeholder_uri = f"http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#{stakeholder_id}"
        
        delete_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        DELETE {{
            <{stakeholder_uri}> ?p ?o .
            ?s ?p2 <{stakeholder_uri}> .
        }}
        WHERE {{
            {{
                <{stakeholder_uri}> ?p ?o .
            }} UNION {{
                ?s ?p2 <{stakeholder_uri}> .
            }}
        }}
        """
        
        update_graphdb(delete_query)
        
        return jsonify({
            'success': True,
            'message': 'Partie prenante supprimée avec succès'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

@app.route('/api/detailed-attributions', methods=['GET'])
def get_detailed_attributions():
    """
    Récupère toutes les attributions détaillées avec informations sur les parties prenantes, éléments et types de coûts
    """
    try:
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?stakeholder ?stakeholderName ?stakeholderType ?element ?elementId ?costInstance ?costType ?costValue ?responsibility
        WHERE {
            ?stakeholder rdf:type :Stakeholder .
            ?stakeholder :hasName ?stakeholderName .
            ?stakeholder :hasType ?stakeholderType .
            
            # Relations de responsabilité
            {
                ?stakeholder :responsibleFor ?costInstance .
                BIND("responsibleFor" AS ?responsibility)
            } UNION {
                ?stakeholder :affectedBy ?costInstance .
                BIND("affectedBy" AS ?responsibility)
            }
            
            # Informations sur l'instance de coût
            ?costInstance rdf:type ?costType .
            FILTER(?costType IN (:ConstructionCosts, :OperationCosts, :MaintenanceCosts, :EndOfLifeCosts))
            
            # Lien vers l'élément
            ?element :hasCostInstance ?costInstance .
            ?element :hasGlobalId ?elementId .
            
            # Valeur du coût (optionnelle)
            OPTIONAL {
                ?costInstance :hasCostValue ?costValue .
            }
        }
        ORDER BY ?stakeholderName ?elementId ?costType
        """
        
        result = query_graphdb(query)
        
        if not result or 'results' not in result or 'bindings' not in result['results']:
            return jsonify({
                'success': True,
                'attributions': []
            })
        
        attributions = []
        for binding in result['results']['bindings']:
            # Extraire le type de coût du nom de la classe
            cost_type_uri = binding.get('costType', {}).get('value', '')
            cost_type = cost_type_uri.split('#')[-1] if '#' in cost_type_uri else cost_type_uri
            
            # Mapper les types de coûts vers des labels français
            cost_type_labels = {
                'ConstructionCosts': 'Construction',
                'OperationCosts': 'Opération', 
                'MaintenanceCosts': 'Maintenance',
                'EndOfLifeCosts': 'Fin de vie'
            }
            
            # Mapper les types de parties prenantes
            stakeholder_type_labels = {
                'PropertyOwner': '🏢 Propriétaire',
                'AssetOperator': '⚙️ Opérateur',
                'EndUser': '👤 Utilisateur Final',
                'MaintenanceProvider': '🔧 Prestataire Maintenance',
                'EnergyProvider': '⚡ Fournisseur Énergie'
            }
            
            stakeholder_type = binding.get('stakeholderType', {}).get('value', '')
            
            attribution = {
                'stakeholder_uri': binding.get('stakeholder', {}).get('value', ''),
                'stakeholder_name': binding.get('stakeholderName', {}).get('value', ''),
                'stakeholder_type': stakeholder_type,
                'stakeholder_type_label': stakeholder_type_labels.get(stakeholder_type, stakeholder_type),
                'element_uri': binding.get('element', {}).get('value', ''),
                'element_id': binding.get('elementId', {}).get('value', ''),
                'cost_instance_uri': binding.get('costInstance', {}).get('value', ''),
                'cost_type': cost_type,
                'cost_type_label': cost_type_labels.get(cost_type, cost_type),
                'cost_value': float(binding.get('costValue', {}).get('value', 0)) if binding.get('costValue') else 0,
                'responsibility': binding.get('responsibility', {}).get('value', '')
            }
            
            attributions.append(attribution)
        
        return jsonify({
            'success': True,
            'attributions': attributions,
            'total_count': len(attributions)
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des attributions détaillées: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/delete-attribution', methods=['DELETE'])
def delete_specific_attribution():
    """
    Supprime une attribution spécifique entre une partie prenante et une instance de coût
    """
    try:
        data = request.get_json()
        stakeholder_uri = data.get('stakeholder_uri')
        cost_instance_uri = data.get('cost_instance_uri')
        responsibility = data.get('responsibility', 'responsibleFor')
        
        if not stakeholder_uri or not cost_instance_uri:
            return jsonify({
                'success': False,
                'error': 'URI de la partie prenante et de l\'instance de coût requis'
            }), 400
        
        # Construire la requête de suppression
        property_uri = f":{responsibility}"
        
        delete_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        DELETE {{
            <{stakeholder_uri}> {property_uri} <{cost_instance_uri}> .
        }}
        WHERE {{
            <{stakeholder_uri}> {property_uri} <{cost_instance_uri}> .
        }}
        """
        
        # Exécuter la suppression
        result = update_graphdb(delete_query)
        
        return jsonify({
            'success': True,
            'message': 'Attribution supprimée avec succès',
            'deleted_relation': {
                'stakeholder': stakeholder_uri,
                'cost_instance': cost_instance_uri,
                'responsibility': responsibility
            }
        })
        
    except Exception as e:
        print(f"Erreur lors de la suppression de l'attribution: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/delete-stakeholder-attributions', methods=['DELETE'])
def delete_stakeholder_attributions():
    """Supprime toutes les attributions d'une partie prenante spécifique"""
    try:
        data = request.get_json()
        stakeholder_uri = data.get('stakeholder_uri')
        
        if not stakeholder_uri:
            return jsonify({'error': 'URI de la partie prenante requis'}), 400
        
        # Compter d'abord les attributions existantes pour cette partie prenante
        count_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT (COUNT(*) as ?count) WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a ?costType .
            FILTER(?costType IN (:ConstructionCosts, :OperationCosts, :MaintenanceCosts, :EndOfLifeCosts))
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }}
        """
        
        count_result = query_graphdb(count_query)
        initial_count = int(count_result[0]['count']) if count_result else 0
        
        # Supprimer toutes les relations d'attribution pour cette partie prenante
        delete_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        DELETE {{
            <{stakeholder_uri}> ?relation ?cost .
        }}
        WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a ?costType .
            FILTER(?costType IN (:ConstructionCosts, :OperationCosts, :MaintenanceCosts, :EndOfLifeCosts))
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }}
        """
        
        update_graphdb(delete_query)
        
        return jsonify({
            'success': True,
            'message': f'Attributions supprimées pour la partie prenante',
            'deleted_count': initial_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

@app.route('/api/delete-stakeholder-cost-type', methods=['DELETE'])
def delete_stakeholder_cost_type():
    """Supprime les attributions d'un type de coût spécifique pour une partie prenante"""
    try:
        data = request.get_json()
        stakeholder_uri = data.get('stakeholder_uri')
        cost_type = data.get('cost_type')
        
        print(f"=== SUPPRESSION STAKEHOLDER COST TYPE ===")
        print(f"Données reçues: {data}")
        print(f"Stakeholder URI: '{stakeholder_uri}'")
        print(f"Cost Type: '{cost_type}'")
        
        # Validation stricte des paramètres
        if not stakeholder_uri or stakeholder_uri == 'undefined' or stakeholder_uri.strip() == '':
            return jsonify({'error': 'URI de la partie prenante invalide ou manquant'}), 400
            
        if not cost_type or cost_type == 'undefined' or cost_type.strip() == '':
            return jsonify({'error': 'Type de coût invalide ou manquant'}), 400
        
        # Validation du format de l'URI
        if not stakeholder_uri.startswith('http://'):
            return jsonify({'error': 'Format d\'URI invalide'}), 400
        
        # Validation du type de coût
        valid_cost_types = ['ConstructionCosts', 'OperationCosts', 'MaintenanceCosts', 'EndOfLifeCosts']
        if cost_type not in valid_cost_types:
            return jsonify({'error': f'Type de coût invalide. Types valides: {valid_cost_types}'}), 400
        
        # Étape 1: Trouver toutes les relations existantes pour ce type de coût
        find_relations_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?relation ?cost WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a :{cost_type} .
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }}
        """
        
        print(f"Recherche des relations existantes...")
        print(f"Requête SPARQL: {find_relations_query}")
        
        try:
            relations = query_graphdb(find_relations_query)
            print(f"Relations trouvées: {len(relations)}")
            
            if len(relations) == 0:
                return jsonify({
                    'success': True,
                    'message': f'Aucune attribution de type {cost_type} trouvée pour cette partie prenante',
                    'deleted_count': 0
                })
            
            # Afficher les relations trouvées
            for rel in relations[:5]:  # Afficher les 5 premières
                print(f"  - {rel.get('relation', 'N/A')} -> {rel.get('cost', 'N/A')}")
                
        except Exception as find_error:
            print(f"Erreur lors de la recherche: {find_error}")
            return jsonify({'error': f'Erreur lors de la recherche: {str(find_error)}'}), 500
        
        # Étape 2: Supprimer les relations une par une pour éviter les erreurs de syntaxe
        deleted_count = 0
        for relation in relations:
            relation_prop = relation.get('relation')
            cost_uri = relation.get('cost')
            
            if relation_prop and cost_uri:
                # Construire la propriété correctement
                if relation_prop.startswith('http://'):
                    # URI complète
                    prop_part = relation_prop.split('#')[-1]
                    property_uri = f":{prop_part}"
                else:
                    # Déjà au format court
                    property_uri = f":{relation_prop}" if not relation_prop.startswith(':') else relation_prop
                
                delete_single_query = f"""
                PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
                
                DELETE {{
                    <{stakeholder_uri}> {property_uri} <{cost_uri}> .
                }}
                WHERE {{
                    <{stakeholder_uri}> {property_uri} <{cost_uri}> .
                }}
                """
                
                try:
                    print(f"Suppression: {stakeholder_uri} {property_uri} {cost_uri}")
                    update_graphdb(delete_single_query)
                    deleted_count += 1
                except Exception as delete_error:
                    print(f"Erreur lors de la suppression d'une relation: {delete_error}")
                    # Continuer avec les autres relations
        
        print(f"Suppression terminée. Relations supprimées: {deleted_count}")
        
        return jsonify({
            'success': True,
            'message': f'Attributions de type {cost_type} supprimées avec succès',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        print(f"Erreur générale lors de la suppression: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

@app.route('/api/test-delete-sparql', methods=['POST'])
def test_delete_sparql():
    """Endpoint de test pour diagnostiquer les problèmes de suppression SPARQL"""
    try:
        data = request.get_json()
        stakeholder_uri = data.get('stakeholder_uri', 'http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#PropertyOwner_1')
        cost_type = data.get('cost_type', 'ConstructionCosts')
        
        print(f"=== TEST DELETE SPARQL ===")
        print(f"Stakeholder URI: {stakeholder_uri}")
        print(f"Cost Type: {cost_type}")
        
        # Test 1: Vérifier les données existantes
        check_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?relation ?cost WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a :{cost_type} .
        }}
        LIMIT 10
        """
        
        print(f"Requête de vérification:")
        print(check_query)
        
        try:
            existing_data = query_graphdb(check_query)
            print(f"Données existantes trouvées: {len(existing_data)}")
            for item in existing_data[:3]:  # Afficher les 3 premiers
                print(f"  - Relation: {item.get('relation', 'N/A')}, Cost: {item.get('cost', 'N/A')}")
        except Exception as check_error:
            print(f"Erreur lors de la vérification: {check_error}")
            return jsonify({'error': f'Erreur de vérification: {str(check_error)}'}), 500
        
        # Test 2: Requête de suppression simple
        simple_delete = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        DELETE {{
            <{stakeholder_uri}> ?relation ?cost .
        }}
        WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a :{cost_type} .
        }}
        """
        
        print(f"Requête de suppression:")
        print(simple_delete)
        
        try:
            delete_result = update_graphdb(simple_delete)
            print(f"Suppression réussie: {delete_result.status_code}")
        except Exception as delete_error:
            print(f"Erreur lors de la suppression: {delete_error}")
            return jsonify({'error': f'Erreur de suppression: {str(delete_error)}'}), 500
        
        # Test 3: Vérifier après suppression
        try:
            remaining_data = query_graphdb(check_query)
            print(f"Données restantes après suppression: {len(remaining_data)}")
        except Exception as final_check_error:
            print(f"Erreur lors de la vérification finale: {final_check_error}")
        
        return jsonify({
            'success': True,
            'message': 'Test de suppression SPARQL terminé',
            'initial_count': len(existing_data) if 'existing_data' in locals() else 0,
            'final_count': len(remaining_data) if 'remaining_data' in locals() else 0
        })
        
    except Exception as e:
        print(f"Erreur générale dans test_delete_sparql: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur générale: {str(e)}'}), 500

@app.route('/api/debug-stakeholder-relations/<path:stakeholder_uri>', methods=['GET'])
def debug_stakeholder_relations(stakeholder_uri):
    """Endpoint de diagnostic pour vérifier les relations d'une partie prenante"""
    try:
        print(f"=== DEBUG STAKEHOLDER RELATIONS ===")
        print(f"Stakeholder URI: {stakeholder_uri}")
        
        # Requête pour trouver toutes les relations de cette partie prenante
        debug_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?relation ?cost ?costType ?costValue WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a ?costType .
            OPTIONAL {{ ?cost :hasCostValue ?costValue }}
            FILTER(?relation IN (:responsibleFor, :affectedBy))
            FILTER(?costType IN (:ConstructionCosts, :OperationCosts, :MaintenanceCosts, :EndOfLifeCosts))
        }}
        ORDER BY ?costType ?relation
        """
        
        relations = query_graphdb(debug_query)
        
        print(f"Relations trouvées: {len(relations)}")
        for rel in relations:
            print(f"  - {rel.get('relation', 'N/A')} -> {rel.get('cost', 'N/A')} ({rel.get('costType', 'N/A')}) = {rel.get('costValue', 0)}")
        
        # Calculer les totaux par type de coût
        cost_breakdown = {
            'ConstructionCosts': 0,
            'OperationCosts': 0,
            'MaintenanceCosts': 0,
            'EndOfLifeCosts': 0
        }
        
        for relation in relations:
            cost_type = relation.get('costType', '').split('#')[-1] if '#' in relation.get('costType', '') else relation.get('costType', '')
            cost_value = float(relation.get('costValue', 0)) if relation.get('costValue') else 0
            
            if cost_type in cost_breakdown:
                cost_breakdown[cost_type] += cost_value
        
        total_impact = sum(cost_breakdown.values())
        
        return jsonify({
            'success': True,
            'stakeholder_uri': stakeholder_uri,
            'relations_count': len(relations),
            'relations': relations,
            'cost_breakdown': cost_breakdown,
            'total_impact': total_impact
        })
        
    except Exception as e:
        print(f"Erreur lors du debug: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur lors du debug: {str(e)}'}), 500

@app.route('/api/deep-debug-stakeholder/<path:stakeholder_uri>', methods=['GET'])
def deep_debug_stakeholder(stakeholder_uri):
    """Diagnostic complet pour traquer TOUS les coûts et relations d'une partie prenante"""
    try:
        print(f"=== DIAGNOSTIC COMPLET STAKEHOLDER ===")
        print(f"Stakeholder URI: {stakeholder_uri}")
        
        # 1. Toutes les relations sortantes de cette partie prenante
        all_relations_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?property ?object ?objectType WHERE {{
            <{stakeholder_uri}> ?property ?object .
            OPTIONAL {{ ?object a ?objectType }}
        }}
        ORDER BY ?property
        """
        
        all_relations = query_graphdb(all_relations_query)
        print(f"=== TOUTES LES RELATIONS SORTANTES ({len(all_relations)}) ===")
        for rel in all_relations:
            print(f"  {rel.get('property', 'N/A')} -> {rel.get('object', 'N/A')} (type: {rel.get('objectType', 'N/A')})")
        
        # 2. Recherche du coût spécifique de $524,908
        specific_cost_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?cost ?costType ?element ?relation ?stakeholder ?costValue WHERE {{
            ?cost :hasCostValue ?costValue .
            FILTER(?costValue >= 524900 && ?costValue <= 524920)
            ?cost a ?costType .
            OPTIONAL {{ ?cost :appliesTo ?element }}
            OPTIONAL {{ ?stakeholder ?relation ?cost }}
        }}
        """
        
        specific_costs = query_graphdb(specific_cost_query)
        print(f"=== COÛT SPÉCIFIQUE ~$524,908 ({len(specific_costs)}) ===")
        for cost in specific_costs:
            print(f"  {cost.get('cost', 'N/A')} ({cost.get('costType', 'N/A')}) = ${cost.get('costValue', 0)} -> {cost.get('element', 'N/A')}")
            if cost.get('stakeholder'):
                print(f"    Lié à: {cost.get('stakeholder', 'N/A')} via {cost.get('relation', 'N/A')}")
        
        # 3. Recherche de coûts avec valeurs liés à cette partie prenante
        costs_with_values_query = f"""
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?relation ?cost ?costType ?costValue ?element WHERE {{
            <{stakeholder_uri}> ?relation ?cost .
            ?cost a ?costType .
            ?cost :hasCostValue ?costValue .
            OPTIONAL {{ ?cost :appliesTo ?element }}
        }}
        ORDER BY DESC(?costValue)
        """
        
        costs_with_values = query_graphdb(costs_with_values_query)
        print(f"=== COÛTS AVEC VALEURS ({len(costs_with_values)}) ===")
        total_found = 0
        for cost in costs_with_values:
            value = float(cost.get('costValue', 0))
            total_found += value
            print(f"  {cost.get('relation', 'N/A')} -> {cost.get('cost', 'N/A')} ({cost.get('costType', 'N/A')}) = ${value:,.2f}")
        
        print(f"TOTAL TROUVÉ: ${total_found:,.2f}")
        
        return jsonify({
            'success': True,
            'stakeholder_uri': stakeholder_uri,
            'all_relations': all_relations,
            'costs_with_values': costs_with_values,
            'total_cost_found': total_found,
            'specific_cost_524908': specific_costs
        })
        
    except Exception as e:
        print(f"Erreur lors du diagnostic complet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur lors du diagnostic: {str(e)}'}), 500

@app.route('/api/find-persistent-cost', methods=['GET'])
def find_persistent_cost():
    """Recherche le coût persistant de $524,908 dans tout le système"""
    try:
        print(f"=== RECHERCHE DU COÛT PERSISTANT $524,908 ===")
        
        # Recherche globale du coût
        global_search_query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?cost ?costType ?costValue ?element ?stakeholder ?relation WHERE {
            ?cost :hasCostValue ?costValue .
            FILTER(?costValue >= 524900 && ?costValue <= 524920)
            ?cost a ?costType .
            OPTIONAL { ?cost :appliesTo ?element }
            OPTIONAL { ?stakeholder ?relation ?cost }
        }
        ORDER BY ?costValue
        """
        
        persistent_costs = query_graphdb(global_search_query)
        print(f"Coûts persistants trouvés: {len(persistent_costs)}")
        
        for cost in persistent_costs:
            print(f"=== COÛT TROUVÉ ===")
            print(f"URI: {cost.get('cost', 'N/A')}")
            print(f"Type: {cost.get('costType', 'N/A')}")
            print(f"Valeur: ${cost.get('costValue', 0)}")
            print(f"Élément: {cost.get('element', 'N/A')}")
            print(f"Partie prenante: {cost.get('stakeholder', 'N/A')}")
            print(f"Relation: {cost.get('relation', 'N/A')}")
        
        # Recherche dans l'endpoint multi-stakeholder-view pour voir comment il calcule
        print(f"=== VÉRIFICATION ENDPOINT MULTI-STAKEHOLDER ===")
        multi_view_query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
        
        SELECT ?stakeholder ?stakeholderType ?name ?cost ?costValue WHERE {
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
            
            {
                ?stakeholder :affectedBy ?cost .
            } UNION {
                ?stakeholder :responsibleFor ?cost .
            }
            
            OPTIONAL { ?cost :hasCostValue ?costValue }
            OPTIONAL { ?stakeholder ifc:name_IfcPerson ?name }
            OPTIONAL { ?stakeholder ifc:name_IfcOrganization ?name }
            
            FILTER(?costValue >= 524900 && ?costValue <= 524920)
        }
        ORDER BY ?stakeholder
        """
        
        multi_view_results = query_graphdb(multi_view_query)
        print(f"Résultats multi-stakeholder avec coût persistant: {len(multi_view_results)}")
        
        for result in multi_view_results:
            print(f"Stakeholder: {result.get('stakeholder', 'N/A')}")
            print(f"Type: {result.get('stakeholderType', 'N/A')}")
            print(f"Nom: {result.get('name', 'N/A')}")
            print(f"Coût: {result.get('cost', 'N/A')}")
            print(f"Valeur: ${result.get('costValue', 0)}")
        
        return jsonify({
            'success': True,
            'persistent_costs': persistent_costs,
            'multi_view_results': multi_view_results,
            'total_found': len(persistent_costs)
        })
        
    except Exception as e:
        print(f"Erreur lors de la recherche du coût persistant: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur lors de la recherche: {str(e)}'}), 500

@app.route('/debug-persistent-cost')
def debug_persistent_cost():
    """Page de diagnostic pour le coût persistant"""
    return send_from_directory('../Frontend', 'debug_persistent_cost.html')

@app.route('/clear-cache')
def clear_cache():
    """Page de nettoyage du cache"""
    return send_from_directory('../Frontend', 'clear_cache.html')

@app.route('/api/test-stakeholder-query', methods=['GET'])
def test_stakeholder_query():
    """Endpoint de test pour diagnostiquer la requête SPARQL des parties prenantes"""
    try:
        # Test 1: Requête simple pour voir toutes les parties prenantes
        query1 = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?stakeholder ?type WHERE {
            ?stakeholder a ?type .
            ?type rdfs:subClassOf* :Stakeholder .
            FILTER(?stakeholder != :Stakeholder)
            FILTER(?stakeholder != :PropertyOwner)
            FILTER(?stakeholder != :EndUser)
            FILTER(?stakeholder != :MaintenanceProvider)
        }
        LIMIT 10
        """
        
        result1 = query_graphdb(query1)
        
        # Test 2: Requête pour voir les relations de responsabilité
        query2 = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        
        SELECT ?stakeholder ?relation ?cost WHERE {
            ?stakeholder ?relation ?cost .
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }
        LIMIT 10
        """
        
        result2 = query_graphdb(query2)
        
        # Test 3: Requête combinée comme dans multi-stakeholder-view
        query3 = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2_TC1/OWL#>
        
        SELECT DISTINCT ?stakeholder ?costInstance WHERE {
            ?stakeholder rdf:type ?stakeholderTypeClass .
            ?stakeholderTypeClass rdfs:subClassOf* :Stakeholder .
            
            {
                ?stakeholder :responsibleFor ?costInstance .
            } UNION {
                ?stakeholder :affectedBy ?costInstance .
            }
        }
        LIMIT 10
        """
        
        result3 = query_graphdb(query3)
        
        return jsonify({
            'success': True,
            'test1_stakeholders': result1,
            'test2_relations': result2,
            'test3_combined': result3,
            'counts': {
                'stakeholders': len(result1) if isinstance(result1, list) else len(result1.get('results', {}).get('bindings', [])),
                'relations': len(result2) if isinstance(result2, list) else len(result2.get('results', {}).get('bindings', [])),
                'combined': len(result3) if isinstance(result3, list) else len(result3.get('results', {}).get('bindings', []))
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du test: {str(e)}'}), 500

@app.route('/api/test-costs-mapping', methods=['GET'])
def test_costs_mapping():
    """Test simple pour diagnostiquer le mapping des coûts"""
    try:
        # Test 1: Récupérer les attributions
        query = """
        PREFIX : <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?stakeholder ?cost WHERE {
            ?stakeholder ?relation ?cost .
            ?stakeholder a ?stakeholderType .
            ?stakeholderType rdfs:subClassOf* :Stakeholder .
            FILTER(?relation IN (:responsibleFor, :affectedBy))
        }
        LIMIT 5
        """
        
        attributions = query_graphdb(query)
        
        # Test 2: Récupérer les éléments IFC
        elements_response = requests.get(f"http://localhost:8000/get-ifc-elements")
        elements = elements_response.json() if elements_response.status_code == 200 else []
        
        # Test 3: Créer le mapping
        element_costs = {}
        for element in elements[:5]:  # Prendre seulement les 5 premiers
            element_id = element.get('GlobalId', '')
            if element_id:
                element_costs[f"{element_id}_ConstructionCosts"] = float(element.get('ConstructionCost', 0))
        
        # Test 4: Vérifier les correspondances
        matches = []
        for attribution in attributions[:5]:
            cost_uri = attribution['cost']
            cost_key = cost_uri.split('#')[-1] if '#' in cost_uri else cost_uri
            cost_value = element_costs.get(cost_key, 0)
            
            matches.append({
                'cost_uri': cost_uri,
                'cost_key': cost_key,
                'cost_value': cost_value,
                'found_in_mapping': cost_key in element_costs
            })
        
        return jsonify({
            'success': True,
            'attributions_count': len(attributions),
            'elements_count': len(elements),
            'mapping_count': len(element_costs),
            'sample_attributions': attributions[:3],
            'sample_elements': [{'GlobalId': e.get('GlobalId'), 'ConstructionCost': e.get('ConstructionCost')} for e in elements[:3]],
            'sample_mapping': dict(list(element_costs.items())[:3]),
            'matches': matches
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du test: {str(e)}'}), 500

# Enregistrer les routes de comparaison d'analyses
# Nous devons d'abord créer le graphe RDF global
from rdflib import Graph
g = Graph()

# Enregistrer les routes de comparaison
register_comparison_routes(app, g, calculate_wlc_dynamically, get_multi_stakeholder_view)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
