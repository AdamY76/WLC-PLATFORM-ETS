import ifcopenshell
import csv
import json

def extract_all_elements():
    # Charger le modèle IFC
    model = ifcopenshell.open('../filtered_model_with_groups.ifc')
    
    # Obtenir tous les types d'éléments disponibles
    all_types = set()
    for element in model.by_type('IfcProduct'):
        all_types.add(element.is_a())
    
    print(f"Types d'éléments trouvés: {sorted(all_types)}")
    
    # Analyser chaque type
    results = []
    for element_type in sorted(all_types):
        elements = model.by_type(element_type)
        if len(elements) > 0:
            print(f"\n=== {element_type}: {len(elements)} éléments ===")
            
            # Analyser les premiers éléments de chaque type
            for i, element in enumerate(elements[:3]):
                element_data = analyze_element(element)
                if element_data:
                    results.append(element_data)
                    print(f"  {i+1}. {element_data}")
    
    return results

def analyze_element(element):
    """Analyser un élément IFC pour extraire les informations utiles"""
    
    # Informations de base
    base_info = {
        'GUID': element.GlobalId,
        'Type': element.is_a(),
        'Name': getattr(element, 'Name', '') or '',
        'Description': getattr(element, 'Description', '') or '',
        'Tag': getattr(element, 'Tag', '') or '',
        'ObjectType': getattr(element, 'ObjectType', '') or ''
    }
    
    # Extraire les propriétés
    properties = {}
    try:
        if hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a('IfcRelDefinesByProperties'):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a('IfcPropertySet'):
                        prop_set_name = getattr(prop_set, 'Name', 'Unknown')
                        for prop in prop_set.HasProperties:
                            if hasattr(prop, 'NominalValue') and prop.NominalValue:
                                key = f"{prop_set_name}.{prop.Name}"
                                properties[key] = str(prop.NominalValue.wrappedValue)
    except Exception as e:
        pass
    
    # Ajouter les propriétés à l'info de base
    base_info['Properties'] = properties
    
    # Retourner seulement si l'élément a des informations intéressantes
    if any([base_info['Name'], base_info['Tag'], base_info['ObjectType'], properties]):
        return base_info
    
    return None

def save_detailed_csv(elements):
    """Sauvegarder un fichier CSV détaillé"""
    with open('marques_ifc_detaillees.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['GUID', 'Type', 'Name', 'Description', 'Tag', 'ObjectType', 'Properties_JSON', 'Suggested_Group']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for element in elements:
            # Déterminer le groupe suggéré
            suggested_group = determine_group(element)
            
            writer.writerow({
                'GUID': element['GUID'],
                'Type': element['Type'],
                'Name': element['Name'],
                'Description': element['Description'],
                'Tag': element['Tag'],
                'ObjectType': element['ObjectType'],
                'Properties_JSON': json.dumps(element['Properties'], ensure_ascii=False, indent=2),
                'Suggested_Group': suggested_group
            })

def determine_group(element):
    """Déterminer le groupe d'appartenance"""
    name = element['Name'].lower()
    obj_type = element['ObjectType'].lower()
    ifc_type = element['Type'].lower()
    
    if 'curtain' in ifc_type or 'mur' in name or 'rideau' in name:
        return 'Murs-Rideaux'
    elif any(keyword in name for keyword in ['chauffage', 'chaudiere', 'heating', 'boiler']):
        return 'Production Chaleur (D3020)'
    elif any(keyword in name for keyword in ['climatisation', 'refroidissement', 'cooling', 'chiller']):
        return 'Production Froid (D3030)'
    elif any(keyword in name for keyword in ['ventilation', 'distribution', 'conduit']):
        return 'Distribution CVCA (D3040)'
    elif any(keyword in name for keyword in ['uv-', 'unite', 'unité', 'autonome']):
        return 'Unités Autonomes (D3050)'
    else:
        return 'Autre'

if __name__ == "__main__":
    print("Extraction des marques et informations du fichier IFC...")
    elements = extract_all_elements()
    
    print(f"\nTotal éléments avec informations: {len(elements)}")
    
    if elements:
        save_detailed_csv(elements)
        print("Fichier sauvegardé: marques_ifc_detaillees.csv")
    else:
        print("Aucun élément avec informations trouvé.") 