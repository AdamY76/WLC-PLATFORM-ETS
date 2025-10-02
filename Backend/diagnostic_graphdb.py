#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'état des données dans GraphDB
"""

import requests
import json
from config import GRAPHDB_REPO

def query_graphdb(sparql_query):
    """Exécute une requête SPARQL SELECT sur GraphDB"""
    try:
        response = requests.get(
            f"{GRAPHDB_REPO}",
            params={'query': sparql_query},
            headers={'Accept': 'application/sparql-results+json'}
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('results', {}).get('bindings', [])
        else:
            print(f"Erreur requête GraphDB: {response.status_code}")
            return []
    except Exception as e:
        print(f"Erreur lors de la requête: {e}")
        return []

def diagnostic_complet():
    """Effectue un diagnostic complet de GraphDB"""
    
    print("=" * 80)
    print("🔍 DIAGNOSTIC COMPLET DE GRAPHDB")
    print("=" * 80)
    
    # 1. VÉRIFIER LES ÉLÉMENTS IFC
    print("\n📦 1. ÉLÉMENTS IFC")
    print("-" * 40)
    
    elements_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT (COUNT(?element) as ?count) WHERE {
        ?element a wlc:Element .
    }
    """
    
    elements_count = query_graphdb(elements_query)
    if elements_count:
        print(f"✅ Éléments IFC trouvés: {elements_count[0]['count']['value']}")
    else:
        print("❌ Aucun élément IFC trouvé")
    
    # 2. VÉRIFIER LES PARTIES PRENANTES
    print("\n👥 2. PARTIES PRENANTES")
    print("-" * 40)
    
    stakeholders_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?stakeholder ?type ?name WHERE {
        ?stakeholder a ?type .
        ?type rdfs:subClassOf* wlc:Stakeholder .
        OPTIONAL { ?stakeholder wlc:hasName ?name }
        FILTER(?type != wlc:Stakeholder)
    }
    LIMIT 10
    """
    
    stakeholders = query_graphdb(stakeholders_query)
    print(f"✅ Parties prenantes trouvées: {len(stakeholders)}")
    for stakeholder in stakeholders[:5]:  # Afficher les 5 premières
        name = stakeholder.get('name', {}).get('value', 'Sans nom')
        type_name = stakeholder['type']['value'].split('#')[-1]
        print(f"   - {name} ({type_name})")
    
    # 3. VÉRIFIER LES INSTANCES DE COÛTS
    print("\n💰 3. INSTANCES DE COÛTS")
    print("-" * 40)
    
    costs_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?costType (COUNT(?cost) as ?count) WHERE {
        ?cost a ?costType .
        FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
    }
    GROUP BY ?costType
    """
    
    costs = query_graphdb(costs_query)
    total_costs = 0
    for cost in costs:
        cost_type = cost['costType']['value'].split('#')[-1]
        count = int(cost['count']['value'])
        total_costs += count
        print(f"   - {cost_type}: {count} instances")
    print(f"✅ Total instances de coûts: {total_costs}")
    
    # 4. VÉRIFIER LES ATTRIBUTIONS DE COÛTS
    print("\n🔗 4. ATTRIBUTIONS DE COÛTS")
    print("-" * 40)
    
    attributions_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT (COUNT(?attribution) as ?count) WHERE {
        ?attribution a wlc:CostAttribution .
    }
    """
    
    attributions_count = query_graphdb(attributions_query)
    if attributions_count:
        count = int(attributions_count[0]['count']['value'])
        print(f"✅ Attributions de coûts trouvées: {count}")
        
        if count > 0:
            # Détail des attributions par partie prenante
            attributions_detail_query = """
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            SELECT ?stakeholder ?stakeholderName (COUNT(?attribution) as ?count) WHERE {
                ?attribution a wlc:CostAttribution ;
                            wlc:attributedTo ?stakeholder .
                ?stakeholder wlc:hasName ?stakeholderName .
            }
            GROUP BY ?stakeholder ?stakeholderName
            """
            
            attributions_detail = query_graphdb(attributions_detail_query)
            for detail in attributions_detail:
                name = detail['stakeholderName']['value']
                count = detail['count']['value']
                print(f"   - {name}: {count} attributions")
    else:
        print("❌ Aucune attribution de coûts trouvée")
    
    # 5. VÉRIFIER LES RELATIONS RESPONSIBLEFOR/AFFECTEDBY (ANCIEN SYSTÈME)
    print("\n🔗 5. RELATIONS RESPONSIBLEFOR/AFFECTEDBY")
    print("-" * 40)
    
    relations_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?relation (COUNT(*) as ?count) WHERE {
        ?stakeholder ?relation ?cost .
        ?stakeholder a ?stakeholderType .
        ?stakeholderType rdfs:subClassOf* wlc:Stakeholder .
        FILTER(?relation IN (wlc:responsibleFor, wlc:affectedBy))
    }
    GROUP BY ?relation
    """
    
    relations = query_graphdb(relations_query)
    total_relations = 0
    for relation in relations:
        relation_name = relation['relation']['value'].split('#')[-1]
        count = int(relation['count']['value'])
        total_relations += count
        print(f"   - {relation_name}: {count} relations")
    print(f"✅ Total relations: {total_relations}")
    
    # 6. VÉRIFIER LES VALEURS DE COÛTS
    print("\n💵 6. VALEURS DE COÛTS")
    print("-" * 40)
    
    cost_values_query = """
    PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
    SELECT ?costType (COUNT(?cost) as ?withValue) (SUM(?value) as ?totalValue) WHERE {
        ?cost a ?costType ;
              wlc:hasCostValue ?value .
        FILTER(?costType IN (wlc:ConstructionCosts, wlc:OperationCosts, wlc:MaintenanceCosts, wlc:EndOfLifeCosts))
    }
    GROUP BY ?costType
    """
    
    cost_values = query_graphdb(cost_values_query)
    total_value = 0
    for cost_value in cost_values:
        cost_type = cost_value['costType']['value'].split('#')[-1]
        count = int(cost_value['withValue']['value'])
        value = float(cost_value['totalValue']['value'])
        total_value += value
        print(f"   - {cost_type}: {count} avec valeurs, total: {value:,.2f}$")
    print(f"✅ Valeur totale des coûts: {total_value:,.2f}$")
    
    # 7. TESTER L'API MULTI-STAKEHOLDER-VIEW
    print("\n🔍 7. TEST API MULTI-STAKEHOLDER-VIEW")
    print("-" * 40)
    
    try:
        response = requests.get('http://localhost:8000/api/stakeholder-analysis/multi-view')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stakeholders_analysis = data.get('stakeholders_analysis', {})
                total_cost = data.get('total_attributed_costs', 0)
                print(f"✅ API fonctionne: {len(stakeholders_analysis)} stakeholders analysés")
                print(f"   - Coût total attribué: {total_cost:,.2f}$")
                
                for name, analysis in list(stakeholders_analysis.items())[:3]:
                    print(f"   - {name}: {analysis.get('total_cost', 0):,.2f}$")
            else:
                print(f"❌ API échoue: {data.get('error', 'Erreur inconnue')}")
        else:
            print(f"❌ API inaccessible: status {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur API: {e}")
    
    # 8. RÉSUMÉ ET RECOMMANDATIONS
    print("\n📋 8. RÉSUMÉ ET RECOMMANDATIONS")
    print("-" * 40)
    
    if not elements_count or int(elements_count[0]['count']['value']) == 0:
        print("⚠️  PROBLÈME: Aucun élément IFC trouvé")
        print("   → Importez un fichier IFC d'abord")
    
    if len(stakeholders) == 0:
        print("⚠️  PROBLÈME: Aucune partie prenante trouvée")
        print("   → Créez des parties prenantes dans l'onglet Stakeholders")
    
    if total_costs == 0:
        print("⚠️  PROBLÈME: Aucune instance de coûts trouvée")
        print("   → Importez des coûts via Excel ou assignez des coûts manuellement")
    
    if attributions_count and int(attributions_count[0]['count']['value']) == 0 and total_relations == 0:
        print("⚠️  PROBLÈME: Aucune attribution de coûts trouvée")
        print("   → Utilisez l'attribution automatique ou manuelle dans l'onglet Stakeholders")
    
    if total_value == 0:
        print("⚠️  PROBLÈME: Aucune valeur de coût assignée")
        print("   → Assignez des valeurs de coûts aux éléments")
    
    print("\n✅ Diagnostic terminé")
    print("=" * 80)

if __name__ == "__main__":
    diagnostic_complet() 