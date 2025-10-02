#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ifcopenshell
import csv
import json
from collections import defaultdict

def get_element_properties(element):
    """Extraire toutes les propriétés d'un élément IFC"""
    properties = {}
    try:
        if hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a('IfcRelDefinesByProperties'):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a('IfcPropertySet'):
                        prop_set_name = prop_set.Name or "Unknown"
                        for prop in prop_set.HasProperties:
                            if hasattr(prop, 'NominalValue') and prop.NominalValue:
                                key = f"{prop_set_name}.{prop.Name}"
                                properties[key] = str(prop.NominalValue.wrappedValue)
                            elif hasattr(prop, 'Name'):
                                key = f"{prop_set_name}.{prop.Name}"
                                properties[key] = "N/A"
    except Exception as e:
        print(f"Erreur lors de l'extraction des propriétés: {e}")
    return properties

def extract_brand_info():
    """Extraire les informations de marques du fichier IFC"""
    
    # Charger le modèle IFC
    model = ifcopenshell.open('../filtered_model_with_groups.ifc')
    
    # Types d'éléments à analyser
    element_types = [
        'IfcCurtainWall', 'IfcDoor', 'IfcWindow', 'IfcMember', 
        'IfcFlowTerminal', 'IfcFlowSegment', 'IfcFlowFitting', 
        'IfcEnergyConversionDevice', 'IfcFlowMovingDevice', 
        'IfcFlowController', 'IfcDistributionElement',
        'IfcBoiler', 'IfcChiller', 'IfcAirTerminal', 'IfcFan'
    ]
    
    # Mots-clés pour identifier les propriétés de marques
    brand_keywords = [
        'brand', 'marque', 'manufacturer', 'fabricant', 'model', 
        'modèle', 'type', 'reference', 'série', 'serie', 'mark',
        'make', 'vendor', 'supplier', 'product', 'produit'
    ]
    
    elements_with_brands = []
    
    for element_type in element_types:
        elements = model.by_type(element_type)
        print(f"Analyse de {len(elements)} éléments {element_type}")
        
        for element in elements:
            props = get_element_properties(element)
            
            # Rechercher les propriétés liées aux marques
            brand_info = {}
            for prop_name, prop_value in props.items():
                if any(keyword in prop_name.lower() for keyword in brand_keywords):
                    brand_info[prop_name] = prop_value
            
            # Inclure le nom et le type si disponibles
            element_data = {
                'GUID': element.GlobalId,
                'Type_IFC': element.is_a(),
                'Name': element.Name or '',
                'Description': getattr(element, 'Description', '') or '',
                'Tag': getattr(element, 'Tag', '') or '',
                'Properties': brand_info,
                'All_Properties': props  # Garder toutes les propriétés pour référence
            }
            
            # Ajouter seulement si l'élément a des informations utiles
            if brand_info or element.Name or element.Tag:
                elements_with_brands.append(element_data)
    
    return elements_with_brands

def save_to_csv(elements_data, filename):
    """Sauvegarder les données dans un fichier CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['GUID', 'Type_IFC', 'Name', 'Description', 'Tag', 'Brand_Properties', 'Suggested_Group']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for element in elements_data:
            # Déterminer le groupe suggéré basé sur le type
            suggested_group = determine_group(element['Type_IFC'], element['Name'])
            
            writer.writerow({
                'GUID': element['GUID'],
                'Type_IFC': element['Type_IFC'],
                'Name': element['Name'],
                'Description': element['Description'],
                'Tag': element['Tag'],
                'Brand_Properties': json.dumps(element['Properties'], ensure_ascii=False),
                'Suggested_Group': suggested_group
            })

def determine_group(ifc_type, name):
    """Déterminer le groupe suggéré basé sur le type IFC et le nom"""
    name_lower = (name or '').lower()
    
    if 'curtain' in ifc_type.lower() or 'mur' in name_lower or 'rideau' in name_lower:
        return 'Murs-Rideaux'
    elif any(keyword in ifc_type.lower() for keyword in ['boiler', 'energyconversion']):
        return 'Production Chaleur (D3020)'
    elif any(keyword in ifc_type.lower() for keyword in ['chiller', 'aircondition']):
        return 'Production Froid (D3030)'
    elif any(keyword in ifc_type.lower() for keyword in ['flowmoving', 'fan', 'terminal']):
        return 'Distribution CVCA (D3040)'
    elif 'ventil' in name_lower or 'uv-' in name_lower:
        return 'Unités Autonomes (D3050)'
    else:
        return 'Autre'

if __name__ == "__main__":
    print("Début de l'extraction des marques du fichier IFC...")
    
    # Extraire les données
    elements = extract_brand_info()
    
    print(f"\nTrouvé {len(elements)} éléments avec informations de marque/modèle")
    
    # Sauvegarder dans un CSV
    save_to_csv(elements, 'marques_equipements_ifc.csv')
    print("Données sauvegardées dans 'marques_equipements_ifc.csv'")
    
    # Afficher quelques exemples
    print("\n=== EXEMPLES D'ÉLÉMENTS TROUVÉS ===")
    for i, elem in enumerate(elements[:10]):
        print(f"\n{i+1}. GUID: {elem['GUID']}")
        print(f"   Type: {elem['Type_IFC']}")
        print(f"   Nom: {elem['Name']}")
        print(f"   Tag: {elem['Tag']}")
        print(f"   Propriétés marque: {elem['Properties']}") 