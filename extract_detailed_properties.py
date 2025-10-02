#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ifcopenshell
import csv
import json

def extract_all_properties(element):
    """Extraire TOUTES les propriétés d'un élément IFC"""
    all_properties = {}
    
    try:
        if hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a('IfcRelDefinesByProperties'):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a('IfcPropertySet'):
                        prop_set_name = getattr(prop_set, 'Name', 'Unknown')
                        
                        for prop in prop_set.HasProperties:
                            prop_name = getattr(prop, 'Name', 'Unknown')
                            prop_value = "N/A"
                            
                            # Extraire la valeur selon le type de propriété
                            if hasattr(prop, 'NominalValue') and prop.NominalValue:
                                prop_value = str(prop.NominalValue.wrappedValue)
                            elif hasattr(prop, 'Value') and prop.Value:
                                prop_value = str(prop.Value)
                            elif hasattr(prop, 'EnumerationValues') and prop.EnumerationValues:
                                prop_value = str([str(val.wrappedValue) for val in prop.EnumerationValues])
                            
                            # Clé complète avec nom du set de propriétés
                            full_key = f"{prop_set_name}.{prop_name}"
                            all_properties[full_key] = prop_value
    
    except Exception as e:
        print(f"Erreur extraction propriétés pour {element.GlobalId}: {e}")
    
    return all_properties

def find_hvac_equipment():
    """Trouver tous les équipements CVCA avec leurs propriétés détaillées"""
    
    # Charger le modèle IFC
    model = ifcopenshell.open('filtered_model_with_groups.ifc')
    
    # Rechercher les équipements CVCA
    hvac_keywords = ['daikin', 'blower', 'fan', 'coil', 'hvac', 'climatique', 'chauffage', 'ventilation']
    
    hvac_equipment = []
    
    # Chercher dans tous les types d'éléments
    element_types = ['IfcBuildingElementProxy', 'IfcFlowTerminal', 'IfcEnergyConversionDevice', 
                    'IfcFlowMovingDevice', 'IfcFlowController', 'IfcDistributionElement']
    
    for element_type in element_types:
        elements = model.by_type(element_type)
        print(f"Analyse de {len(elements)} éléments {element_type}")
        
        for element in elements:
            element_name = getattr(element, 'Name', '') or ''
            element_desc = getattr(element, 'Description', '') or ''
            element_type_name = getattr(element, 'ObjectType', '') or ''
            
            # Vérifier si c'est un équipement CVCA
            text_to_check = f"{element_name} {element_desc} {element_type_name}".lower()
            
            if any(keyword in text_to_check for keyword in hvac_keywords):
                print(f"Équipement CVCA trouvé: {element_name}")
                
                # Extraire toutes les propriétés
                all_props = extract_all_properties(element)
                
                equipment_data = {
                    'GUID': element.GlobalId,
                    'Type_IFC': element.is_a(),
                    'Name': element_name,
                    'Description': element_desc,
                    'ObjectType': element_type_name,
                    'Tag': getattr(element, 'Tag', '') or '',
                    'Properties': all_props
                }
                
                hvac_equipment.append(equipment_data)
    
    return hvac_equipment

def extract_brand_info(properties):
    """Extraire les informations de marque des propriétés"""
    brand_info = {}
    
    # Mots-clés pour identifier les propriétés importantes
    important_keywords = {
        'fabricant': ['fabricant', 'manufacturer', 'brand', 'marque'],
        'modele': ['model', 'modèle', 'type', 'designation'],
        'produit': ['product', 'produit', 'name'],
        'url': ['url', 'website', 'site'],
        'copyright': ['copyright', '©'],
        'poids': ['weight', 'poids'],
        'note': ['note', 'identification', 'id'],
        'sales': ['sales', 'rep', 'locator']
    }
    
    for prop_key, prop_value in properties.items():
        prop_key_lower = prop_key.lower()
        
        for category, keywords in important_keywords.items():
            if any(keyword in prop_key_lower for keyword in keywords):
                if category not in brand_info:
                    brand_info[category] = {}
                brand_info[category][prop_key] = prop_value
    
    return brand_info

def save_detailed_csv(equipment_list):
    """Sauvegarder les équipements avec leurs propriétés détaillées"""
    
    with open('equipements_cvca_detailles.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'GUID', 'Type_IFC', 'Name', 'Description', 'ObjectType', 'Tag',
            'Fabricant', 'Modele', 'Produit', 'URL', 'Copyright', 'Poids',
            'Note_ID', 'Sales_Rep', 'Toutes_Proprietes'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for equipment in equipment_list:
            brand_info = extract_brand_info(equipment['Properties'])
            
            # Extraire les valeurs spécifiques
            fabricant = next(iter(brand_info.get('fabricant', {}).values()), '')
            modele = next(iter(brand_info.get('modele', {}).values()), '')
            produit = next(iter(brand_info.get('produit', {}).values()), '')
            url = next(iter(brand_info.get('url', {}).values()), '')
            copyright_val = next(iter(brand_info.get('copyright', {}).values()), '')
            poids = next(iter(brand_info.get('poids', {}).values()), '')
            note_id = next(iter(brand_info.get('note', {}).values()), '')
            sales_rep = next(iter(brand_info.get('sales', {}).values()), '')
            
            writer.writerow({
                'GUID': equipment['GUID'],
                'Type_IFC': equipment['Type_IFC'],
                'Name': equipment['Name'],
                'Description': equipment['Description'],
                'ObjectType': equipment['ObjectType'],
                'Tag': equipment['Tag'],
                'Fabricant': fabricant,
                'Modele': modele,
                'Produit': produit,
                'URL': url,
                'Copyright': copyright_val,
                'Poids': poids,
                'Note_ID': note_id,
                'Sales_Rep': sales_rep,
                'Toutes_Proprietes': json.dumps(equipment['Properties'], ensure_ascii=False, indent=2)
            })

if __name__ == "__main__":
    print("Extraction détaillée des équipements CVCA...")
    
    # Trouver tous les équipements CVCA
    hvac_equipment = find_hvac_equipment()
    
    print(f"\nTrouvé {len(hvac_equipment)} équipements CVCA")
    
    if hvac_equipment:
        # Afficher quelques exemples
        print("\n=== EXEMPLES D'ÉQUIPEMENTS TROUVÉS ===")
        for i, equipment in enumerate(hvac_equipment[:3]):
            print(f"\n{i+1}. {equipment['Name']}")
            print(f"   Type: {equipment['Type_IFC']}")
            print(f"   GUID: {equipment['GUID']}")
            
            # Afficher les propriétés importantes
            brand_info = extract_brand_info(equipment['Properties'])
            if brand_info:
                print("   Informations de marque:")
                for category, props in brand_info.items():
                    print(f"     {category.upper()}:")
                    for key, value in props.items():
                        print(f"       {key}: {value}")
        
        # Sauvegarder dans un CSV
        save_detailed_csv(hvac_equipment)
        print(f"\nDonnées sauvegardées dans 'equipements_cvca_detailles.csv'")
    else:
        print("Aucun équipement CVCA trouvé.") 