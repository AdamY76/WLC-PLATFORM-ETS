"""
Routes pour la comparaison d'analyses WLC
"""

from flask import jsonify, request, make_response
# from rdflib import Graph, Namespace, Literal, RDF, XSD  # Temporairement commenté
from datetime import datetime
import traceback
import json
import requests
from config import GRAPHDB_REPO
from sparql_client import query_graphdb

# Variable globale pour stocker l'analyse précédente temporairement
previous_analysis_graph = None
previous_analysis_info = None

def register_comparison_routes(app, g, calculate_wlc_dynamically, get_multi_stakeholder_view):
    """
    Enregistre les routes de comparaison d'analyses
    """
    
    @app.route('/export-complete-analysis')
    def export_complete_analysis():
        """
        Exporte l'analyse complète actuelle au format RDF/Turtle
        """
        try:
            print("🔄 Export de l'analyse complète...")
            
            # Créer un nouveau graphe pour l'export
            export_graph = Graph()
            
            # Définir les namespaces
            WLC = Namespace("http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#")
            ANALYSIS = Namespace("http://wlc-platform.com/analysis/")
            
            # Bind namespaces pour un TTL plus lisible
            export_graph.bind("wlc", WLC)
            export_graph.bind("analysis", ANALYSIS)
            export_graph.bind("rdf", RDF)
            export_graph.bind("xsd", XSD)
            
            # 1. UTILISER LA FONCTION UNIFIÉE POUR GARANTIR LA COHÉRENCE
            current_analysis = get_current_analysis_data()
            print(f"🔍 Données unifiées pour export: WLC nominal={current_analysis.get('total_wlc', 0)}$, WLC actualisé={current_analysis.get('discounted_wlc', 0)}$")
            
            # 2. AJOUTER LES MÉTADONNÉES DE L'ANALYSE
            current_time = datetime.now()
            analysis_uri = ANALYSIS[f"analysis_{current_time.strftime('%Y_%m_%d_%H_%M_%S')}"]
            
            export_graph.add((analysis_uri, RDF.type, WLC.WLCAnalysis))
            export_graph.add((analysis_uri, WLC.analysisDate, Literal(current_time.isoformat(), datatype=XSD.dateTime)))
            export_graph.add((analysis_uri, WLC.currency, Literal("USD")))
            
            # Ajouter les données de l'analyse actuelle (EXACTEMENT LES MÊMES QUE POUR LA COMPARAISON)
            export_graph.add((analysis_uri, WLC.totalWLC, Literal(current_analysis.get('discounted_wlc', 0))))
            export_graph.add((analysis_uri, WLC.nominalWLC, Literal(current_analysis.get('total_wlc', 0))))
            export_graph.add((analysis_uri, WLC.elementsCount, Literal(current_analysis.get('elements_count', 0))))
            
            # 3. RÉCUPÉRER TOUTES LES DONNÉES DE GRAPHDB (contenu original)
            print("📊 Récupération des données de GraphDB...")
            
            # Requête pour récupérer TOUT le contenu du repository
            sparql_query = """
            CONSTRUCT { ?s ?p ?o }
            WHERE { ?s ?p ?o }
            """
            
            # Exécuter la requête sur GraphDB
            response = requests.get(
                f"{GRAPHDB_REPO}",
                params={
                    'query': sparql_query
                },
                headers={'Accept': 'text/turtle'}
            )
            
            if response.status_code == 200:
                # Parser le contenu RDF retourné par GraphDB
                graphdb_content = response.text
                temp_graph = Graph()
                temp_graph.parse(data=graphdb_content, format='turtle')
                
                print(f"📊 Données récupérées de GraphDB: {len(temp_graph)} triplets")
                
                # Ajouter tout le contenu au graphe d'export
                for triple in temp_graph:
                    export_graph.add(triple)
            else:
                print(f"⚠️ Erreur récupération GraphDB: {response.status_code}")
            
            # 4. AJOUTER LES DONNÉES DES PARTIES PRENANTES (EXACTEMENT COMME DANS LA FONCTION UNIFIÉE)
            stakeholders_analysis = current_analysis.get('stakeholders_analysis', {})
            stakeholders_totals = current_analysis.get('stakeholders_totals', {})
            
            print(f"🔍 Export parties prenantes: {len(stakeholders_analysis)} avec analyse, {len(stakeholders_totals)} avec totaux")
            
            # Si on a des données d'analyse détaillées, les utiliser
            if stakeholders_analysis:
                for stakeholder_name, stakeholder_data in stakeholders_analysis.items():
                    stakeholder_uri = ANALYSIS[f"stakeholder_{stakeholder_name.replace(' ', '_').replace('-', '_')}"]
                    export_graph.add((stakeholder_uri, RDF.type, WLC.StakeholderView))
                    export_graph.add((stakeholder_uri, WLC.stakeholderName, Literal(stakeholder_name)))
                    export_graph.add((stakeholder_uri, WLC.totalImpact, Literal(stakeholder_data.get('total_cost', 0))))
                    export_graph.add((analysis_uri, WLC.hasStakeholderView, stakeholder_uri))
                    
                    # Ajouter les détails de coûts par phase avec la bonne structure
                    cost_types = stakeholder_data.get('cost_types', {})
                    export_graph.add((stakeholder_uri, WLC.costConstructionCosts, Literal(cost_types.get('ConstructionCosts', 0))))
                    export_graph.add((stakeholder_uri, WLC.costOperationCosts, Literal(cost_types.get('OperationCosts', 0))))
                    export_graph.add((stakeholder_uri, WLC.costMaintenanceCosts, Literal(cost_types.get('MaintenanceCosts', 0))))
                    export_graph.add((stakeholder_uri, WLC.costEndOfLifeCosts, Literal(cost_types.get('EndOfLifeCosts', 0))))
                    
                    print(f"  ✅ Exporté: {stakeholder_name} = {stakeholder_data.get('total_cost', 0)}$")
            
            # Sinon, utiliser les totaux simples
            elif stakeholders_totals:
                for stakeholder_name, total_cost in stakeholders_totals.items():
                    stakeholder_uri = ANALYSIS[f"stakeholder_{stakeholder_name.replace(' ', '_').replace('-', '_')}"]
                    export_graph.add((stakeholder_uri, RDF.type, WLC.StakeholderView))
                    export_graph.add((stakeholder_uri, WLC.stakeholderName, Literal(stakeholder_name)))
                    export_graph.add((stakeholder_uri, WLC.totalImpact, Literal(total_cost)))
                    export_graph.add((analysis_uri, WLC.hasStakeholderView, stakeholder_uri))
                    
                    print(f"  ✅ Exporté (simple): {stakeholder_name} = {total_cost}$")
            
            # 5. AJOUTER LES TOTAUX PAR PHASE (EXACTEMENT COMME DANS LA FONCTION UNIFIÉE)
            phases_totals = current_analysis.get('phases_totals', {})
            if phases_totals:
                for phase_name, phase_cost in phases_totals.items():
                    phase_uri = ANALYSIS[f"phase_{phase_name.replace(' ', '_')}"]
                    export_graph.add((phase_uri, RDF.type, WLC.PhaseTotal))
                    export_graph.add((phase_uri, WLC.phaseName, Literal(phase_name)))
                    export_graph.add((phase_uri, WLC.totalCost, Literal(phase_cost)))
                    export_graph.add((analysis_uri, WLC.hasPhaseTotal, phase_uri))
                    
                    print(f"  ✅ Phase exportée: {phase_name} = {phase_cost}$")
            
            # 6. SÉRIALISER EN TURTLE
            ttl_content = export_graph.serialize(format='turtle')
            
            # Créer la réponse
            response = make_response(ttl_content)
            response.headers['Content-Type'] = 'text/turtle'
            response.headers['Content-Disposition'] = f'attachment; filename=analyse_wlc_complete_{current_time.strftime("%Y%m%d_%H%M%S")}.ttl'
            
            print(f"✅ Export réussi: {len(export_graph)} triplets")
            print(f"   - WLC actualisé: {current_analysis.get('discounted_wlc', 0)}$")
            print(f"   - WLC nominal: {current_analysis.get('total_wlc', 0)}$")
            print(f"   - Éléments: {current_analysis.get('elements_count', 0)}")
            print(f"   - Parties prenantes: {len(stakeholders_analysis) or len(stakeholders_totals)}")
            print(f"   - Phases: {sum(1 for v in phases_totals.values() if v > 0)}")
            
            return response
            
        except Exception as e:
            print(f"❌ Erreur export: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/import-previous-analysis', methods=['POST'])
    def import_previous_analysis():
        """
        Importe une analyse précédente pour comparaison
        """
        global previous_analysis_graph, previous_analysis_info
        
        try:
            print("=== IMPORT ANALYSE PRÉCÉDENTE ===")
            
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400
            
            # Lire le contenu du fichier
            file_content = file.read().decode('utf-8')
            
            # Parser le graphe RDF
            previous_analysis_graph = Graph()
            previous_analysis_graph.parse(data=file_content, format='turtle')
            
            print(f"Graphe importé: {len(previous_analysis_graph)} triplets")
            
            # Extraire les informations de l'analyse
            WLC = Namespace("http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#")
            ANALYSIS = Namespace("http://wlc-platform.com/analysis/")
            
            # Rechercher les métadonnées de l'analyse
            analysis_query = """
            PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
            PREFIX analysis: <http://wlc-platform.com/analysis/>
            
            SELECT ?analysis ?date ?lifespan ?totalWLC ?elementsCount WHERE {
                ?analysis a wlc:WLCAnalysis .
                OPTIONAL { ?analysis wlc:analysisDate ?date }
                OPTIONAL { ?analysis wlc:projectLifespan ?lifespan }
                OPTIONAL { ?analysis wlc:totalWLC ?totalWLC }
                OPTIONAL { ?analysis wlc:elementsCount ?elementsCount }
            }
            """
            
            analysis_results = list(previous_analysis_graph.query(analysis_query))
            
            # Compter les éléments si pas dans les métadonnées
            elements_count_query = "SELECT (COUNT(?element) as ?count) WHERE { ?element a <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#Element> . }"
            elements_count_results = list(previous_analysis_graph.query(elements_count_query))
            elements_count = int(elements_count_results[0][0]) if elements_count_results else 0
            
            # Préparer les informations de l'analyse
            previous_analysis_info = {
                'filename': file.filename,
                'elements_count': elements_count,
                'triplets_count': len(previous_analysis_graph)
            }
            
            if analysis_results:
                result = analysis_results[0]
                if result[1]:  # date
                    previous_analysis_info['date'] = str(result[1])
                if result[2]:  # lifespan
                    previous_analysis_info['lifespan'] = int(result[2])
                if result[3]:  # totalWLC
                    previous_analysis_info['total_wlc'] = float(result[3])
                if result[4]:  # elementsCount
                    previous_analysis_info['elements_count'] = int(result[4])
            
            print(f"✅ Analyse importée: {previous_analysis_info}")
            
            return jsonify({
                'success': True,
                'analysis_info': previous_analysis_info
            })
            
        except Exception as e:
            print(f"❌ Erreur import: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/compare-analyses', methods=['POST'])
    def compare_analyses():
        """
        Compare l'analyse actuelle avec l'analyse précédente importée
        """
        global previous_analysis_graph, previous_analysis_info
        
        try:
            print("=== COMPARAISON D'ANALYSES ===")
            
            if not previous_analysis_graph:
                return jsonify({'success': False, 'error': 'Aucune analyse précédente importée'}), 400
            
            # 1. ANALYSER L'ANALYSE ACTUELLE
            current_analysis = analyze_current_state(g, get_multi_stakeholder_view)
            
            # 2. ANALYSER L'ANALYSE PRÉCÉDENTE
            previous_analysis = analyze_previous_state(previous_analysis_graph)
            
            # 3. COMPARER LES ANALYSES (PASSER LE GRAPHE PRÉCÉDENT)
            comparison = compare_analysis_states(current_analysis, previous_analysis, previous_analysis_graph)
            
            print(f"✅ Comparaison terminée")
            
            return jsonify({
                'success': True,
                'comparison': comparison,
                'current_analysis': current_analysis,
                'previous_analysis': previous_analysis
            })
            
        except Exception as e:
            print(f"❌ Erreur comparaison: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/export-comparison-report', methods=['POST'])
    def export_comparison_report():
        """
        Exporte un rapport de comparaison au format PDF (simplifié)
        """
        try:
            # Pour le moment, on génère un rapport texte simple
            # Dans une implémentation complète, on utiliserait une bibliothèque PDF
            
            report_content = f"""
RAPPORT DE COMPARAISON WLC
========================

Date de génération : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ANALYSES COMPARÉES :
- Analyse précédente : {previous_analysis_info.get('date', 'Inconnue') if previous_analysis_info else 'Aucune'}
- Analyse actuelle : {datetime.now().strftime('%Y-%m-%d')}

RÉSUMÉ :
Cette fonctionnalité de rapport détaillé sera implémentée dans une version future.
Le rapport inclurait :
- Évolution détaillée des coûts par phase
- Impact sur chaque partie prenante
- Changements dans les paramètres du projet
- Recommandations d'optimisation

Pour le moment, utilisez l'interface web pour consulter les résultats de comparaison.
            """
            
            response = make_response(report_content)
            response.headers['Content-Type'] = 'text/plain'
            response.headers['Content-Disposition'] = f'attachment; filename=rapport_comparaison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            
            return response
            
        except Exception as e:
            print(f"Erreur export rapport: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

def get_current_analysis_data():
    """
    Fonction unifiée pour récupérer les données d'analyse actuelles
    Utilise EXACTEMENT la même logique que get_multi_stakeholder_view() dans app.py
    MAIS avec calcul correct des coûts totaux par phase (multiplication par durée de vie)
    """
    try:
        print("🔍 Récupération unifiée des données d'analyse actuelles (logique identique à app.py + correction phases)...")
        
        # Initialiser les résultats
        result = {
            'date': datetime.now().isoformat(),
            'total_wlc': 0,
            'discounted_wlc': 0,
            'phases_totals': {
                'Construction': 0,
                'Opération': 0,
                'Maintenance': 0,
                'Fin de vie': 0
            },
            'stakeholders_totals': {},
            'elements_count': 0,
            'stakeholders_analysis': {}
        }
        
        # 1. RÉCUPÉRER LA DURÉE DE VIE DU PROJET (même logique que app.py)
        sparql_lifespan = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        lifespan_result = query_graphdb(sparql_lifespan)
        project_lifespan = int(float(lifespan_result[0]['lifespan'])) if lifespan_result and 'lifespan' in lifespan_result[0] else 50
        
        print(f"🔍 Durée de vie du projet: {project_lifespan} ans")
        
        # 2. RÉCUPÉRER TOUTES LES ATTRIBUTIONS (même requête que app.py)
        attributions_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?attribution ?stakeholder ?stakeholder_name ?element ?element_guid 
               ?cost_type ?percentage ?construction_cost ?operation_cost 
               ?maintenance_cost ?end_of_life_cost WHERE {
            ?attribution a wlc:CostAttribution ;
                        wlc:attributedTo ?stakeholder ;
                        wlc:concernsElement ?element ;
                        wlc:concernsCostType ?cost_type ;
                        wlc:hasPercentage ?percentage .
            
            ?stakeholder wlc:hasName ?stakeholder_name .
            ?element wlc:globalId ?element_guid .
            
            # Récupérer les coûts WLC ANNUELS de l'élément
            OPTIONAL { 
                ?element wlc:hasCost ?constructionCost .
                ?constructionCost a wlc:ConstructionCosts ;
                                 wlc:hasCostValue ?construction_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?operationCost .
                ?operationCost a wlc:OperationCosts ;
                              wlc:hasCostValue ?operation_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?maintenanceCost .
                ?maintenanceCost a wlc:MaintenanceCosts ;
                                wlc:hasCostValue ?maintenance_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?endOfLifeCost .
                ?endOfLifeCost a wlc:EndOfLifeCosts ;
                              wlc:hasCostValue ?end_of_life_cost .
            }
        }
        ORDER BY ?stakeholder_name ?element_guid
        """
        
        attributions_result = query_graphdb(attributions_query)
        
        print(f"🔍 Nombre d'attributions trouvées: {len(attributions_result) if attributions_result else 0}")
        
        if not attributions_result:
            print("⚠️ Aucune attribution trouvée")
            return result
        
        # 3. ANALYSER LES ATTRIBUTIONS AVEC CORRECTION DES COÛTS TOTAUX PAR PHASE
        stakeholders_analysis = {}
        total_attributed_costs = 0
        
        for row in attributions_result:
            stakeholder_name = row['stakeholder_name']
            cost_type = row['cost_type'].split('#')[-1] if '#' in row['cost_type'] else row['cost_type']
            percentage = float(row['percentage']) / 100.0
            element_guid = row['element_guid']
            
            print(f"🔍 Traitement: {stakeholder_name}, {cost_type}, {percentage}%, élément: {element_guid}")
            
            # CONVERTIR LES COÛTS ANNUELS EN COÛTS TOTAUX PAR PHASE (MÊME LOGIQUE QUE analyze_cost_by_phase)
            phase_total_cost = 0
            
            if cost_type == 'ConstructionCosts' and row.get('construction_cost'):
                # Construction : coût direct (année 0)
                phase_total_cost = float(row['construction_cost'])
                
            elif cost_type == 'OperationCosts' and row.get('operation_cost'):
                # Opération : coût annuel × (durée_vie - 1)
                annual_cost = float(row['operation_cost'])
                operation_years = max(0, project_lifespan - 1)
                phase_total_cost = annual_cost * operation_years
                print(f"  🔧 Opération: {annual_cost}$/an × {operation_years} ans = {phase_total_cost}$")
                
            elif cost_type == 'MaintenanceCosts' and row.get('maintenance_cost'):
                # Maintenance : coût annuel × durée_vie (à simplifier - dans la vraie logique il y a aussi les remplacements)
                annual_cost = float(row['maintenance_cost'])
                phase_total_cost = annual_cost * project_lifespan
                print(f"  🔧 Maintenance: {annual_cost}$/an × {project_lifespan} ans = {phase_total_cost}$")
                
            elif cost_type == 'EndOfLifeCosts' and row.get('end_of_life_cost'):
                # Fin de vie : coût direct (dernière année) - pour simplifier, on prend le coût direct
                # Dans la vraie logique, il faudrait calculer les remplacements selon les durées de vie
                phase_total_cost = float(row['end_of_life_cost'])
            
            print(f"🔍 Coût total de phase (corrigé): {phase_total_cost}$")
            
            # Calculer le coût attribué sur le coût total de phase
            attributed_cost = phase_total_cost * percentage
            total_attributed_costs += attributed_cost
            
            print(f"🔍 Coût attribué (sur total phase): {attributed_cost}$")
            
            # Analyser par partie prenante
            if stakeholder_name not in stakeholders_analysis:
                stakeholders_analysis[stakeholder_name] = {
                    'total_cost': 0,
                    'cost_types': {
                        'ConstructionCosts': 0,
                        'OperationCosts': 0,
                        'MaintenanceCosts': 0,
                        'EndOfLifeCosts': 0
                    },
                    'elements_count': set(),
                    'attributions_count': 0
                }
            
            stakeholders_analysis[stakeholder_name]['total_cost'] += attributed_cost
            stakeholders_analysis[stakeholder_name]['cost_types'][cost_type] += attributed_cost
            stakeholders_analysis[stakeholder_name]['elements_count'].add(row['element_guid'])
            stakeholders_analysis[stakeholder_name]['attributions_count'] += 1
            
            # Ajouter aux totaux par phase (COÛTS TOTAUX CORRIGÉS)
            if cost_type == 'ConstructionCosts':
                result['phases_totals']['Construction'] += attributed_cost
            elif cost_type == 'OperationCosts':
                result['phases_totals']['Opération'] += attributed_cost
            elif cost_type == 'MaintenanceCosts':
                result['phases_totals']['Maintenance'] += attributed_cost
            elif cost_type == 'EndOfLifeCosts':
                result['phases_totals']['Fin de vie'] += attributed_cost
        
        # 4. FINALISER LES RÉSULTATS
        # Convertir les sets en nombres pour la cohérence
        for stakeholder_name, stakeholder_data in stakeholders_analysis.items():
            stakeholder_data['elements_count'] = len(stakeholder_data['elements_count'])
            result['stakeholders_totals'][stakeholder_name] = stakeholder_data['total_cost']
        
        result['stakeholders_analysis'] = stakeholders_analysis
        result['total_wlc'] = total_attributed_costs
        result['discounted_wlc'] = total_attributed_costs  # Pour l'instant, même valeur
        
        # 5. COMPTER LES ÉLÉMENTS TOTAUX
        elements_count_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT (COUNT(DISTINCT ?element) as ?count) WHERE {
            ?element wlc:globalId ?guid .
        }
        """
        elements_count_result = query_graphdb(elements_count_query)
        if elements_count_result and 'count' in elements_count_result[0]:
            result['elements_count'] = int(elements_count_result[0]['count'])
        
        print(f"✅ Analyse actuelle terminée (avec correction coûts phases):")
        print(f"   - WLC nominal: {result['total_wlc']:,.2f}$")
        print(f"   - WLC actualisé: {result['discounted_wlc']:,.2f}$")
        print(f"   - Construction: {result['phases_totals']['Construction']:,.2f}$")
        print(f"   - Opération: {result['phases_totals']['Opération']:,.2f}$ (sur {project_lifespan-1} ans)")
        print(f"   - Maintenance: {result['phases_totals']['Maintenance']:,.2f}$ (sur {project_lifespan} ans)")
        print(f"   - Fin de vie: {result['phases_totals']['Fin de vie']:,.2f}$")
        print(f"   - Stakeholders: {len(result['stakeholders_totals'])}")
        print(f"   - Éléments: {result['elements_count']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erreur get_current_analysis_data: {e}")
        traceback.print_exc()
        return {
            'date': datetime.now().isoformat(),
            'total_wlc': 0,
            'discounted_wlc': 0,
            'phases_totals': {'Construction': 0, 'Opération': 0, 'Maintenance': 0, 'Fin de vie': 0},
            'stakeholders_totals': {},
            'elements_count': 0,
            'stakeholders_analysis': {}
        }

def analyze_current_state(g, get_multi_stakeholder_view):
    """Analyse l'état actuel du système en utilisant la fonction unifiée"""
    print("🔍 Analyse de l'état actuel (via fonction unifiée)...")
    return get_current_analysis_data()

def analyze_previous_state(previous_graph):
    """Analyse l'état de l'analyse précédente EN UTILISANT LA MÊME LOGIQUE QUE L'ACTUELLE + CORRECTION PHASES"""
    try:
        print("🔍 Analyse de l'état précédent (logique identique à l'actuelle + correction phases)...")
        
        # Initialiser le résultat
        result = {
            'date': previous_analysis_info.get('date', 'Inconnue'),
            'total_wlc': 0,
            'elements_count': previous_analysis_info.get('elements_count', 0),
            'phases_totals': {
                'Construction': 0,
                'Opération': 0,
                'Maintenance': 0,
                'Fin de vie': 0
            },
            'stakeholders_totals': {},
            'discounted_wlc': previous_analysis_info.get('total_wlc', 0),
            'stakeholders_analysis': {}
        }
        
        print(f"🔍 Informations de base: {result['elements_count']} éléments")
        
        # 1. RÉCUPÉRER LA DURÉE DE VIE DU PROJET DEPUIS L'ANALYSE PRÉCÉDENTE
        project_lifespan_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?lifespan WHERE {
          <http://example.com/ifc#Project> wlc:hasDuration ?lifespan .
        }
        """
        
        lifespan_results = list(previous_graph.query(project_lifespan_query))
        project_lifespan = int(float(lifespan_results[0][0])) if lifespan_results and lifespan_results[0][0] else 50
        
        print(f"🔍 Durée de vie du projet (analyse précédente): {project_lifespan} ans")
        
        # 2. PRIORITÉ : UTILISER LES COSTATTRIBUTION SI DISPONIBLES (MÊME LOGIQUE QUE L'ACTUELLE + CORRECTION PHASES)
        attributions_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?attribution ?stakeholder ?stakeholder_name ?element ?element_guid 
               ?cost_type ?percentage ?construction_cost ?operation_cost 
               ?maintenance_cost ?end_of_life_cost WHERE {
            ?attribution a wlc:CostAttribution ;
                        wlc:attributedTo ?stakeholder ;
                        wlc:concernsElement ?element ;
                        wlc:concernsCostType ?cost_type ;
                        wlc:hasPercentage ?percentage .
            
            ?stakeholder wlc:hasName ?stakeholder_name .
            ?element wlc:globalId ?element_guid .
            
            # Récupérer les coûts WLC ANNUELS de l'élément
            OPTIONAL { 
                ?element wlc:hasCost ?constructionCost .
                ?constructionCost a wlc:ConstructionCosts ;
                                 wlc:hasCostValue ?construction_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?operationCost .
                ?operationCost a wlc:OperationCosts ;
                              wlc:hasCostValue ?operation_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?maintenanceCost .
                ?maintenanceCost a wlc:MaintenanceCosts ;
                                wlc:hasCostValue ?maintenance_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?endOfLifeCost .
                ?endOfLifeCost a wlc:EndOfLifeCosts ;
                              wlc:hasCostValue ?end_of_life_cost .
            }
        }
        ORDER BY ?stakeholder_name ?element_guid
        """
        
        attributions_results = list(previous_graph.query(attributions_query))
        print(f"🔍 CostAttribution trouvées: {len(attributions_results)}")
        
        if attributions_results:
            # UTILISER LA MÊME LOGIQUE QUE get_current_analysis_data() AVEC CORRECTION PHASES
            stakeholders_analysis = {}
            total_attributed_costs = 0
            
            for row in attributions_results:
                stakeholder_name = row[2] if row[2] else 'Inconnu'  # stakeholder_name
                cost_type = str(row[5]).split('#')[-1] if '#' in str(row[5]) else str(row[5])  # cost_type
                percentage = float(row[6]) / 100.0 if row[6] else 0  # percentage
                element_guid = row[4] if row[4] else 'Inconnu'  # element_guid
                
                print(f"🔍 Traitement: {stakeholder_name}, {cost_type}, {percentage}%, élément: {element_guid}")
                
                # CONVERTIR LES COÛTS ANNUELS EN COÛTS TOTAUX PAR PHASE (MÊME LOGIQUE QUE L'ACTUELLE)
                phase_total_cost = 0
                
                if cost_type == 'ConstructionCosts' and row[7]:  # construction_cost
                    # Construction : coût direct (année 0)
                    phase_total_cost = float(row[7])
                elif cost_type == 'OperationCosts' and row[8]:  # operation_cost
                    # Opération : coût annuel × (durée_vie - 1)
                    annual_cost = float(row[8])
                    operation_years = max(0, project_lifespan - 1)
                    phase_total_cost = annual_cost * operation_years
                    print(f"  🔧 Opération: {annual_cost}$/an × {operation_years} ans = {phase_total_cost}$")
                elif cost_type == 'MaintenanceCosts' and row[9]:  # maintenance_cost
                    # Maintenance : coût annuel × durée_vie
                    annual_cost = float(row[9])
                    phase_total_cost = annual_cost * project_lifespan
                    print(f"  🔧 Maintenance: {annual_cost}$/an × {project_lifespan} ans = {phase_total_cost}$")
                elif cost_type == 'EndOfLifeCosts' and row[10]:  # end_of_life_cost
                    # Fin de vie : coût direct (dernière année)
                    phase_total_cost = float(row[10])
                
                print(f"🔍 Coût total de phase (corrigé): {phase_total_cost}$")
                
                # Calculer le coût attribué sur le coût total de phase
                attributed_cost = phase_total_cost * percentage
                total_attributed_costs += attributed_cost
                
                print(f"🔍 Coût attribué (sur total phase): {attributed_cost}$")
                
                # Analyser par partie prenante (MÊME STRUCTURE QUE L'ACTUELLE)
                if stakeholder_name not in stakeholders_analysis:
                    stakeholders_analysis[stakeholder_name] = {
                        'total_cost': 0,
                        'cost_types': {
                            'ConstructionCosts': 0,
                            'OperationCosts': 0,
                            'MaintenanceCosts': 0,
                            'EndOfLifeCosts': 0
                        },
                        'elements_count': set(),
                        'attributions_count': 0
                    }
                
                stakeholders_analysis[stakeholder_name]['total_cost'] += attributed_cost
                stakeholders_analysis[stakeholder_name]['cost_types'][cost_type] += attributed_cost
                stakeholders_analysis[stakeholder_name]['elements_count'].add(element_guid)
                stakeholders_analysis[stakeholder_name]['attributions_count'] += 1
                
                # Ajouter aux totaux par phase (COÛTS TOTAUX CORRIGÉS)
                if cost_type == 'ConstructionCosts':
                    result['phases_totals']['Construction'] += attributed_cost
                elif cost_type == 'OperationCosts':
                    result['phases_totals']['Opération'] += attributed_cost
                elif cost_type == 'MaintenanceCosts':
                    result['phases_totals']['Maintenance'] += attributed_cost
                elif cost_type == 'EndOfLifeCosts':
                    result['phases_totals']['Fin de vie'] += attributed_cost
            
            # Finaliser les résultats (MÊME LOGIQUE QUE L'ACTUELLE)
            for stakeholder_name, stakeholder_data in stakeholders_analysis.items():
                stakeholder_data['elements_count'] = len(stakeholder_data['elements_count'])
                result['stakeholders_totals'][stakeholder_name] = stakeholder_data['total_cost']
            
            result['stakeholders_analysis'] = stakeholders_analysis
            result['total_wlc'] = total_attributed_costs
            result['discounted_wlc'] = total_attributed_costs
            
            print(f"✅ Analyse précédente via CostAttribution (avec correction phases):")
            print(f"   - WLC nominal: {result['total_wlc']:,.2f}$")
            print(f"   - WLC actualisé: {result['discounted_wlc']:,.2f}$")
            print(f"   - Construction: {result['phases_totals']['Construction']:,.2f}$")
            print(f"   - Opération: {result['phases_totals']['Opération']:,.2f}$ (sur {project_lifespan-1} ans)")
            print(f"   - Maintenance: {result['phases_totals']['Maintenance']:,.2f}$ (sur {project_lifespan} ans)")
            print(f"   - Fin de vie: {result['phases_totals']['Fin de vie']:,.2f}$")
            print(f"   - Stakeholders: {len(result['stakeholders_totals'])}")
            
            return result
        
        # 3. FALLBACK : UTILISER LES STAKEHOLDERVIEW SI PAS DE COSTATTRIBUTION
        print("🔍 Pas de CostAttribution, utilisation des StakeholderView...")
        
        stakeholder_views_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX analysis: <http://wlc-platform.com/analysis/>
        
        SELECT ?stakeholder ?name ?totalImpact ?costConstruction ?costOperation ?costMaintenance ?costEndOfLife WHERE {
            ?stakeholder a wlc:StakeholderView .
            OPTIONAL { ?stakeholder wlc:stakeholderName ?name }
            OPTIONAL { ?stakeholder wlc:totalImpact ?totalImpact }
            OPTIONAL { ?stakeholder wlc:costConstructionCosts ?costConstruction }
            OPTIONAL { ?stakeholder wlc:costOperationCosts ?costOperation }
            OPTIONAL { ?stakeholder wlc:costMaintenanceCosts ?costMaintenance }
            OPTIONAL { ?stakeholder wlc:costEndOfLifeCosts ?costEndOfLife }
        }
        """
        
        stakeholder_results = list(previous_graph.query(stakeholder_views_query))
        print(f"🔍 StakeholderView trouvées: {len(stakeholder_results)}")
        
        total_wlc_from_stakeholders = 0
        
        for row in stakeholder_results:
            stakeholder_name = str(row[1]) if row[1] else 'Inconnu'
            total_impact = float(row[2]) if row[2] else 0
            cost_construction = float(row[3]) if row[3] else 0
            cost_operation = float(row[4]) if row[4] else 0
            cost_maintenance = float(row[5]) if row[5] else 0
            cost_endoflife = float(row[6]) if row[6] else 0
            
            result['stakeholders_totals'][stakeholder_name] = total_impact
            total_wlc_from_stakeholders += total_impact
            
            # Ajouter aux totaux par phase (SUPPOSÉS DÉJÀ CORRIGÉS DANS L'EXPORT)
            result['phases_totals']['Construction'] += cost_construction
            result['phases_totals']['Opération'] += cost_operation
            result['phases_totals']['Maintenance'] += cost_maintenance
            result['phases_totals']['Fin de vie'] += cost_endoflife
            
            print(f"  - {stakeholder_name}: {total_impact:,.2f}$ (C:{cost_construction:,.2f}, O:{cost_operation:,.2f}, M:{cost_maintenance:,.2f}, E:{cost_endoflife:,.2f})")
        
        # 4. EXTRAIRE LES DONNÉES PRINCIPALES DE L'ANALYSE
        main_analysis_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        PREFIX analysis: <http://wlc-platform.com/analysis/>
        
        SELECT ?analysis ?totalWLC ?nominalWLC ?elementsCount WHERE {
            ?analysis a wlc:WLCAnalysis .
            OPTIONAL { ?analysis wlc:totalWLC ?totalWLC }
            OPTIONAL { ?analysis wlc:nominalWLC ?nominalWLC }
            OPTIONAL { ?analysis wlc:elementsCount ?elementsCount }
        }
        """
        
        main_results = list(previous_graph.query(main_analysis_query))
        print(f"🔍 Analyses principales trouvées: {len(main_results)}")
        
        if main_results:
            main_result = main_results[0]
            if main_result[1]:  # totalWLC (actualisé)
                result['discounted_wlc'] = float(main_result[1])
                print(f"   - WLC actualisé trouvé: {result['discounted_wlc']:,.2f}$")
            if main_result[2]:  # nominalWLC
                result['total_wlc'] = float(main_result[2])
                print(f"   - WLC nominal trouvé: {result['total_wlc']:,.2f}$")
            if main_result[3]:  # elementsCount
                result['elements_count'] = int(main_result[3])
                print(f"   - Nombre d'éléments trouvé: {result['elements_count']}")
        
        # 5. COHÉRENCE DES DONNÉES
        if total_wlc_from_stakeholders > 0 and result['total_wlc'] == 0:
            result['total_wlc'] = total_wlc_from_stakeholders
            print(f"🔍 WLC nominal calculé depuis stakeholders: {result['total_wlc']:,.2f}$")
        
        if result['discounted_wlc'] == 0 and result['total_wlc'] > 0:
            result['discounted_wlc'] = result['total_wlc']
            print(f"🔍 WLC actualisé = WLC nominal: {result['discounted_wlc']:,.2f}$")
        
        if result['total_wlc'] == 0:
            result['total_wlc'] = sum(result['phases_totals'].values())
            print(f"🔍 WLC nominal calculé depuis phases: {result['total_wlc']:,.2f}$")
        
        print(f"✅ Analyse précédente terminée (via StakeholderView avec correction phases):")
        print(f"   - WLC nominal: {result['total_wlc']:,.2f}$")
        print(f"   - WLC actualisé: {result['discounted_wlc']:,.2f}$")
        print(f"   - Construction: {result['phases_totals']['Construction']:,.2f}$")
        print(f"   - Opération: {result['phases_totals']['Opération']:,.2f}$")
        print(f"   - Maintenance: {result['phases_totals']['Maintenance']:,.2f}$")
        print(f"   - Fin de vie: {result['phases_totals']['Fin de vie']:,.2f}$")
        print(f"   - Stakeholders: {len(result['stakeholders_totals'])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erreur analyse état précédent: {e}")
        import traceback
        traceback.print_exc()
        return {
            'date': previous_analysis_info.get('date', 'Inconnue') if previous_analysis_info else 'Inconnue',
            'total_wlc': 0,
            'discounted_wlc': 0,
            'phases_totals': {'Construction': 0, 'Opération': 0, 'Maintenance': 0, 'Fin de vie': 0},
            'stakeholders_totals': {},
            'elements_count': 0,
            'stakeholders_analysis': {}
        }

def compare_analysis_states(current, previous, previous_graph):
    """Compare deux états d'analyse"""
    try:
        print("🔍 Comparaison des états d'analyse...")
        
        # Évolution du WLC total (nominal)
        current_wlc = current.get('total_wlc', 0)
        previous_wlc = previous.get('total_wlc', 0)
        
        # Seuil de tolérance pour éviter les faux positifs dus aux arrondis (0.01$)
        tolerance = 0.01
        
        wlc_absolute_change = current_wlc - previous_wlc
        wlc_percentage_change = (wlc_absolute_change / previous_wlc * 100) if previous_wlc > 0 else 0
        
        # Considérer comme identique si la différence est inférieure au seuil
        if abs(wlc_absolute_change) < tolerance:
            wlc_absolute_change = 0
            wlc_percentage_change = 0
        
        wlc_evolution = {
            'current': current_wlc,
            'previous': previous_wlc,
            'absolute_change': wlc_absolute_change,
            'percentage_change': wlc_percentage_change
        }
        
        # Évolution du WLC actualisé (indicateur principal)
        current_discounted_wlc = current.get('discounted_wlc', 0)
        previous_discounted_wlc = previous.get('discounted_wlc', 0)
        
        discounted_absolute_change = current_discounted_wlc - previous_discounted_wlc
        discounted_percentage_change = (discounted_absolute_change / previous_discounted_wlc * 100) if previous_discounted_wlc > 0 else 0
        
        # Appliquer la même tolérance pour le WLC actualisé
        if abs(discounted_absolute_change) < tolerance:
            discounted_absolute_change = 0
            discounted_percentage_change = 0
        
        discounted_wlc_evolution = {
            'current': current_discounted_wlc,
            'previous': previous_discounted_wlc,
            'absolute_change': discounted_absolute_change,
            'percentage_change': discounted_percentage_change
        }
        
        # Comparaison par phases avec tolérance
        current_phases = current.get('phases_totals', {})
        previous_phases = previous.get('phases_totals', {})
        
        phases_comparison = {
            'current': current_phases,
            'previous': previous_phases,
            'changes': {}
        }
        
        # Analyser les changements par phase
        all_phases = set(current_phases.keys()) | set(previous_phases.keys())
        significant_phase_changes = 0
        
        for phase in all_phases:
            current_phase_cost = current_phases.get(phase, 0)
            previous_phase_cost = previous_phases.get(phase, 0)
            phase_change = current_phase_cost - previous_phase_cost
            
            if abs(phase_change) >= tolerance:
                phases_comparison['changes'][phase] = {
                    'current': current_phase_cost,
                    'previous': previous_phase_cost,
                    'change': phase_change,
                    'percentage_change': (phase_change / previous_phase_cost * 100) if previous_phase_cost > 0 else 0
                }
                significant_phase_changes += 1
        
        # Comparaison parties prenantes avec tolérance
        current_stakeholders = current.get('stakeholders_totals', {})
        previous_stakeholders = previous.get('stakeholders_totals', {})
        
        stakeholders_comparison = {
            'current': current_stakeholders,
            'previous': previous_stakeholders,
            'changes': {}
        }
        
        # Analyser les changements par partie prenante
        all_stakeholders = set(current_stakeholders.keys()) | set(previous_stakeholders.keys())
        significant_stakeholder_changes = 0
        
        for stakeholder in all_stakeholders:
            current_stakeholder_cost = current_stakeholders.get(stakeholder, 0)
            previous_stakeholder_cost = previous_stakeholders.get(stakeholder, 0)
            stakeholder_change = current_stakeholder_cost - previous_stakeholder_cost
            
            if abs(stakeholder_change) >= tolerance:
                stakeholders_comparison['changes'][stakeholder] = {
                    'current': current_stakeholder_cost,
                    'previous': previous_stakeholder_cost,
                    'change': stakeholder_change,
                    'percentage_change': (stakeholder_change / previous_stakeholder_cost * 100) if previous_stakeholder_cost > 0 else 0
                }
                significant_stakeholder_changes += 1
        
        # NOUVELLE FONCTIONNALITÉ : COMPARAISON DES ÉLÉMENTS
        print("🔍 Comparaison des éléments entre analyses...")
        
        try:
            # Récupérer les éléments actuels
            current_elements = get_current_elements_data()
            print(f"🔍 Éléments actuels récupérés: {len(current_elements)}")
            
            # Récupérer les éléments précédents
            previous_elements = get_previous_elements_data(previous_graph)
            print(f"🔍 Éléments précédents récupérés: {len(previous_elements)}")
            
            # Analyser les changements d'éléments
            elements_comparison = compare_elements(current_elements, previous_elements, tolerance)
            print(f"🔍 Comparaison éléments terminée: {elements_comparison.get('total_changes', 0)} changements")
            
        except Exception as e:
            print(f"❌ Erreur lors de la comparaison des éléments: {e}")
            import traceback
            traceback.print_exc()
            # Fallback avec données vides
            elements_comparison = {
                'added': [],
                'removed': [],
                'modified': [],
                'added_count': 0,
                'removed_count': 0,
                'modified_count': 0,
                'total_changes': 0
            }
        
        # Changements d'éléments
        elements_changed = abs(current.get('elements_count', 0) - previous.get('elements_count', 0))
        
        # Parties prenantes affectées (seulement celles avec des changements significatifs)
        stakeholders_affected = significant_stakeholder_changes
        
        # Déterminer l'impact principal basé sur les changements réels
        main_impact = "Analyses identiques"
        
        if elements_changed > 0:
            main_impact = f"Changement du nombre d'éléments ({elements_changed} éléments)"
        elif abs(discounted_percentage_change) > 10:
            if discounted_percentage_change > 0:
                main_impact = f"Augmentation significative du WLC actualisé (+{discounted_percentage_change:.1f}%)"
            else:
                main_impact = f"Réduction significative du WLC actualisé ({discounted_percentage_change:.1f}%)"
        elif abs(discounted_percentage_change) > 1:
            if discounted_percentage_change > 0:
                main_impact = f"Légère augmentation du WLC actualisé (+{discounted_percentage_change:.1f}%)"
            else:
                main_impact = f"Légère diminution du WLC actualisé ({discounted_percentage_change:.1f}%)"
        elif significant_phase_changes > 0:
            main_impact = f"Redistribution des coûts entre phases ({significant_phase_changes} phases modifiées)"
        elif significant_stakeholder_changes > 0:
            main_impact = f"Changements dans la répartition des parties prenantes ({significant_stakeholder_changes} modifiées)"
        elif elements_comparison.get('modified_count', 0) > 0:
            main_impact = f"Modifications des coûts d'éléments ({elements_comparison['modified_count']} éléments modifiés)"
        
        # Paramètres modifiés (simplifié)
        parameters_changed = 0
        if elements_changed > 0:
            parameters_changed += 1
        if significant_phase_changes > 0:
            parameters_changed += 1
        if significant_stakeholder_changes > 0:
            parameters_changed += 1
        if elements_comparison.get('modified_count', 0) > 0:
            parameters_changed += 1
        
        # Générer les changements détaillés
        detailed_changes = []
        
        print(f"🔍 Génération des changements détaillés...")
        print(f"    INCLUS : Changements par phase, éléments ajoutés/supprimés/modifiés, nombre d'éléments")
        print(f"    EXCLUS : Changements par partie prenante, WLC globaux (affichés dans les graphiques)")
        
        # 1. Changements par phase
        for phase, change_data in phases_comparison.get('changes', {}).items():
            if abs(change_data['change']) >= tolerance:
                detailed_changes.append({
                    'element_id': f"Phase {phase}",
                    'change_type': 'Coût par phase',
                    'previous_value': f"{change_data['previous']:,.2f}$",
                    'current_value': f"{change_data['current']:,.2f}$",
                    'evolution': change_data['percentage_change'],
                    'absolute_change': change_data['change']
                })
        
        # 3. NOUVEAU : Changements d'éléments individuels UNIQUEMENT
        for element_change in elements_comparison.get('added', []):
            detailed_changes.append({
                'element_id': element_change['guid'],
                'change_type': 'Élément ajouté',
                'previous_value': '0$',
                'current_value': f"{element_change['total_cost']:,.2f}$",
                'evolution': float('inf'),
                'absolute_change': element_change['total_cost'],
                'element_description': element_change.get('description', 'N/A'),
                'element_class': element_change.get('ifc_class', 'N/A'),
                'uniformat_code': element_change.get('uniformat_code', 'N/A'),
                'uniformat_description': element_change.get('uniformat_description', 'N/A'),
                'construction_cost': element_change.get('construction_cost', 0)
            })
        
        for element_change in elements_comparison.get('removed', []):
            detailed_changes.append({
                'element_id': element_change['guid'],
                'change_type': 'Élément supprimé',
                'previous_value': f"{element_change['total_cost']:,.2f}$",
                'current_value': '0$',
                'evolution': -100,
                'absolute_change': -element_change['total_cost'],
                'element_description': element_change.get('description', 'N/A'),
                'element_class': element_change.get('ifc_class', 'N/A'),
                'uniformat_code': element_change.get('uniformat_code', 'N/A'),
                'uniformat_description': element_change.get('uniformat_description', 'N/A'),
                'construction_cost': element_change.get('construction_cost', 0)
            })
        
        for element_change in elements_comparison.get('modified', []):
            detailed_changes.append({
                'element_id': element_change['guid'],
                'change_type': 'Élément modifié',
                'previous_value': f"{element_change['previous_cost']:,.2f}$",
                'current_value': f"{element_change['current_cost']:,.2f}$",
                'evolution': element_change['percentage_change'],
                'absolute_change': element_change['cost_change'],
                'element_description': element_change.get('description', 'N/A'),
                'element_class': element_change.get('ifc_class', 'N/A'),
                'uniformat_code': element_change.get('uniformat_code', 'N/A'),
                'uniformat_description': element_change.get('uniformat_description', 'N/A'),
                'construction_cost': element_change.get('current_construction_cost', 0),
                'previous_construction_cost': element_change.get('previous_construction_cost', 0)
            })
        
        # 4. Changement du nombre d'éléments (si significatif)
        if elements_changed > 0:
            detailed_changes.append({
                'element_id': 'Nombre d\'éléments',
                'change_type': 'Modification structurelle',
                'previous_value': str(previous.get('elements_count', 0)),
                'current_value': str(current.get('elements_count', 0)),
                'evolution': ((current.get('elements_count', 0) - previous.get('elements_count', 0)) / previous.get('elements_count', 1) * 100) if previous.get('elements_count', 0) > 0 else 0,
                'absolute_change': elements_changed
            })
        
        # Trier les changements par importance (valeur absolue du changement)
        detailed_changes.sort(key=lambda x: abs(x.get('absolute_change', 0)), reverse=True)
        
        print(f"✅ Comparaison terminée:")
        print(f"   - WLC nominal: {wlc_percentage_change:.2f}% ({wlc_absolute_change:+.2f}$)")
        print(f"   - WLC actualisé: {discounted_percentage_change:.2f}% ({discounted_absolute_change:+.2f}$)")
        print(f"   - Éléments changés: {elements_changed}")
        print(f"   - Éléments ajoutés: {len(elements_comparison.get('added', []))}")
        print(f"   - Éléments supprimés: {len(elements_comparison.get('removed', []))}")
        print(f"   - Éléments modifiés: {len(elements_comparison.get('modified', []))}")
        print(f"   - Phases modifiées: {significant_phase_changes}")
        print(f"   - Stakeholders modifiés: {significant_stakeholder_changes}")
        print(f"   - Changements détaillés: {len(detailed_changes)}")
        print(f"   - Impact principal: {main_impact}")
        
        return {
            'current_date': current.get('date'),
            'previous_date': previous.get('date'),
            'wlc_evolution': wlc_evolution,
            'discounted_wlc_evolution': discounted_wlc_evolution,
            'phases_comparison': phases_comparison,
            'stakeholders_comparison': stakeholders_comparison,
            'elements_comparison': elements_comparison,
            'elements_changed': elements_changed,
            'stakeholders_affected': stakeholders_affected,
            'phases_affected': significant_phase_changes,
            'parameters_changed': parameters_changed,
            'main_impact': main_impact,
            'is_identical': (
                abs(discounted_percentage_change) < 0.01 and 
                elements_changed == 0 and 
                significant_phase_changes == 0 and 
                significant_stakeholder_changes == 0 and
                elements_comparison.get('modified_count', 0) == 0
            ),
            'detailed_changes': detailed_changes
        }
        
    except Exception as e:
        print(f"❌ Erreur comparaison: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'wlc_evolution': {'percentage_change': 0},
            'discounted_wlc_evolution': {'percentage_change': 0},
            'phases_comparison': {},
            'stakeholders_comparison': {},
            'elements_comparison': {'added': [], 'removed': [], 'modified': [], 'added_count': 0, 'removed_count': 0, 'modified_count': 0},
            'elements_changed': 0,
            'stakeholders_affected': 0,
            'parameters_changed': 0,
            'main_impact': 'Erreur lors de la comparaison',
            'is_identical': False,
            'detailed_changes': []
        }

def get_current_elements_data():
    """Récupère les données détaillées des éléments actuels"""
    try:
        print("🔍 Récupération des éléments actuels...")
        
        elements_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?description ?ifcClass ?material ?uniformatCode ?uniformatDescription
               ?construction_cost ?operation_cost ?maintenance_cost ?end_of_life_cost WHERE {
            ?element wlc:globalId ?guid .
            OPTIONAL { ?element wlc:hasDescription ?description }
            OPTIONAL { ?element wlc:hasIfcClass ?ifcClass }
            OPTIONAL { ?element wlc:hasMaterial ?material }
            OPTIONAL { ?element wlc:hasUniformatCode ?uniformatCode }
            OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDescription }
            
            # Récupérer les coûts WLC
            OPTIONAL { 
                ?element wlc:hasCost ?constructionCost .
                ?constructionCost a wlc:ConstructionCosts ;
                                 wlc:hasCostValue ?construction_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?operationCost .
                ?operationCost a wlc:OperationCosts ;
                              wlc:hasCostValue ?operation_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?maintenanceCost .
                ?maintenanceCost a wlc:MaintenanceCosts ;
                                wlc:hasCostValue ?maintenance_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?endOfLifeCost .
                ?endOfLifeCost a wlc:EndOfLifeCosts ;
                              wlc:hasCostValue ?end_of_life_cost .
            }
        }
        ORDER BY ?guid
        """
        
        elements_result = query_graphdb(elements_query)
        
        elements_data = {}
        for row in elements_result:
            guid = row['guid']
            construction_cost = float(row.get('construction_cost', 0) or 0)
            operation_cost = float(row.get('operation_cost', 0) or 0)
            maintenance_cost = float(row.get('maintenance_cost', 0) or 0)
            end_of_life_cost = float(row.get('end_of_life_cost', 0) or 0)
            
            total_cost = construction_cost + operation_cost + maintenance_cost + end_of_life_cost
            
            elements_data[guid] = {
                'guid': guid,
                'description': row.get('description', 'N/A'),
                'ifc_class': row.get('ifcClass', 'N/A'),
                'material': row.get('material', 'N/A'),
                'uniformat_code': row.get('uniformatCode', 'N/A'),
                'uniformat_description': row.get('uniformatDescription', 'N/A'),
                'construction_cost': construction_cost,
                'operation_cost': operation_cost,
                'maintenance_cost': maintenance_cost,
                'end_of_life_cost': end_of_life_cost,
                'total_cost': total_cost
            }
        
        print(f"✅ {len(elements_data)} éléments actuels récupérés")
        return elements_data
        
    except Exception as e:
        print(f"❌ Erreur récupération éléments actuels: {e}")
        return {}

def get_previous_elements_data(previous_graph):
    """Récupère les données détaillées des éléments de l'analyse précédente"""
    try:
        print("🔍 Récupération des éléments précédents...")
        
        elements_query = """
        PREFIX wlc: <http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#>
        SELECT ?element ?guid ?description ?ifcClass ?material ?uniformatCode ?uniformatDescription
               ?construction_cost ?operation_cost ?maintenance_cost ?end_of_life_cost WHERE {
            ?element wlc:globalId ?guid .
            OPTIONAL { ?element wlc:hasDescription ?description }
            OPTIONAL { ?element wlc:hasIfcClass ?ifcClass }
            OPTIONAL { ?element wlc:hasMaterial ?material }
            OPTIONAL { ?element wlc:hasUniformatCode ?uniformatCode }
            OPTIONAL { ?element wlc:hasUniformatDescription ?uniformatDescription }
            
            # Récupérer les coûts WLC
            OPTIONAL { 
                ?element wlc:hasCost ?constructionCost .
                ?constructionCost a wlc:ConstructionCosts ;
                                 wlc:hasCostValue ?construction_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?operationCost .
                ?operationCost a wlc:OperationCosts ;
                              wlc:hasCostValue ?operation_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?maintenanceCost .
                ?maintenanceCost a wlc:MaintenanceCosts ;
                                wlc:hasCostValue ?maintenance_cost .
            }
            OPTIONAL { 
                ?element wlc:hasCost ?endOfLifeCost .
                ?endOfLifeCost a wlc:EndOfLifeCosts ;
                              wlc:hasCostValue ?end_of_life_cost .
            }
        }
        ORDER BY ?guid
        """
        
        elements_results = list(previous_graph.query(elements_query))
        
        elements_data = {}
        for row in elements_results:
            guid = str(row[1]) if row[1] else 'Inconnu'
            description = str(row[2]) if row[2] else 'N/A'
            ifc_class = str(row[3]) if row[3] else 'N/A'
            material = str(row[4]) if row[4] else 'N/A'
            uniformat_code = str(row[5]) if row[5] else 'N/A'
            uniformat_description = str(row[6]) if row[6] else 'N/A'
            
            construction_cost = float(row[7]) if row[7] else 0
            operation_cost = float(row[8]) if row[8] else 0
            maintenance_cost = float(row[9]) if row[9] else 0
            end_of_life_cost = float(row[10]) if row[10] else 0
            
            total_cost = construction_cost + operation_cost + maintenance_cost + end_of_life_cost
            
            elements_data[guid] = {
                'guid': guid,
                'description': description,
                'ifc_class': ifc_class,
                'material': material,
                'uniformat_code': uniformat_code,
                'uniformat_description': uniformat_description,
                'construction_cost': construction_cost,
                'operation_cost': operation_cost,
                'maintenance_cost': maintenance_cost,
                'end_of_life_cost': end_of_life_cost,
                'total_cost': total_cost
            }
        
        print(f"✅ {len(elements_data)} éléments précédents récupérés")
        return elements_data
        
    except Exception as e:
        print(f"❌ Erreur récupération éléments précédents: {e}")
        return {}

def compare_elements(current_elements, previous_elements, tolerance=0.01):
    """Compare les éléments entre deux analyses"""
    try:
        print("🔍 Comparaison détaillée des éléments...")
        
        current_guids = set(current_elements.keys())
        previous_guids = set(previous_elements.keys())
        
        # Éléments ajoutés
        added_guids = current_guids - previous_guids
        added_elements = []
        for guid in added_guids:
            element_data = current_elements[guid].copy()
            added_elements.append(element_data)
        
        # Éléments supprimés
        removed_guids = previous_guids - current_guids
        removed_elements = []
        for guid in removed_guids:
            element_data = previous_elements[guid].copy()
            removed_elements.append(element_data)
        
        # Éléments modifiés (présents dans les deux mais avec des coûts différents)
        common_guids = current_guids & previous_guids
        modified_elements = []
        
        for guid in common_guids:
            current_element = current_elements[guid]
            previous_element = previous_elements[guid]
            
            current_total = current_element['total_cost']
            previous_total = previous_element['total_cost']
            cost_change = current_total - previous_total
            
            if abs(cost_change) >= tolerance:
                percentage_change = (cost_change / previous_total * 100) if previous_total > 0 else 0
                
                modified_element = {
                    'guid': guid,
                    'description': current_element.get('description', 'N/A'),
                    'ifc_class': current_element.get('ifc_class', 'N/A'),
                    'material': current_element.get('material', 'N/A'),
                    'uniformat_code': current_element.get('uniformat_code', 'N/A'),
                    'uniformat_description': current_element.get('uniformat_description', 'N/A'),
                    'current_cost': current_total,
                    'previous_cost': previous_total,
                    'cost_change': cost_change,
                    'percentage_change': percentage_change,
                    'current_breakdown': {
                        'construction': current_element['construction_cost'],
                        'operation': current_element['operation_cost'],
                        'maintenance': current_element['maintenance_cost'],
                        'end_of_life': current_element['end_of_life_cost']
                    },
                    'previous_breakdown': {
                        'construction': previous_element['construction_cost'],
                        'operation': previous_element['operation_cost'],
                        'maintenance': previous_element['maintenance_cost'],
                        'end_of_life': previous_element['end_of_life_cost']
                    }
                }
                modified_elements.append(modified_element)
        
        # Trier les éléments par importance du changement
        added_elements.sort(key=lambda x: x['total_cost'], reverse=True)
        removed_elements.sort(key=lambda x: x['total_cost'], reverse=True)
        modified_elements.sort(key=lambda x: abs(x['cost_change']), reverse=True)
        
        result = {
            'added': added_elements,
            'removed': removed_elements,
            'modified': modified_elements,
            'added_count': len(added_elements),
            'removed_count': len(removed_elements),
            'modified_count': len(modified_elements),
            'total_changes': len(added_elements) + len(removed_elements) + len(modified_elements)
        }
        
        print(f"✅ Comparaison éléments terminée:")
        print(f"   - Éléments ajoutés: {result['added_count']}")
        print(f"   - Éléments supprimés: {result['removed_count']}")
        print(f"   - Éléments modifiés: {result['modified_count']}")
        print(f"   - Total changements: {result['total_changes']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erreur comparaison éléments: {e}")
        return {
            'added': [],
            'removed': [],
            'modified': [],
            'added_count': 0,
            'removed_count': 0,
            'modified_count': 0,
            'total_changes': 0
        } 