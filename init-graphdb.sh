#!/bin/sh
# Script d'initialisation GraphDB - Création repository + Import ontologies

GRAPHDB_URL="http://graphdb:7200"
REPO_NAME="wlconto"

echo "🚀 Initialisation GraphDB..."

# Attendre que GraphDB soit prêt
echo "⏳ Attente de GraphDB..."
until curl -s "$GRAPHDB_URL/rest/repositories" > /dev/null 2>&1; do
    echo "   GraphDB pas encore prêt, attente..."
    sleep 5
done
echo "✅ GraphDB prêt!"

# Vérifier si le repository existe déjà
echo "🔍 Vérification du repository '$REPO_NAME'..."
REPO_EXISTS=$(curl -s "$GRAPHDB_URL/rest/repositories" | grep -o "$REPO_NAME" || echo "")

if [ -n "$REPO_EXISTS" ]; then
    echo "✅ Repository '$REPO_NAME' existe déjà"
else
    echo "📦 Création du repository '$REPO_NAME'..."
    
    # Configuration du repository
    REPO_CONFIG=$(cat <<EOF
{
  "id": "$REPO_NAME",
  "title": "WLC Platform Repository",
  "type": "free",
  "location": "",
  "params": {
    "ruleset": {
      "label": "Ruleset",
      "name": "ruleset",
      "value": "owl-horst-optimized"
    },
    "disableSameAs": {
      "label": "Disable owl:sameAs",
      "name": "disableSameAs",
      "value": "false"
    }
  }
}
EOF
)
    
    # Créer le repository
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "$REPO_CONFIG" \
        "$GRAPHDB_URL/rest/repositories" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ Repository '$REPO_NAME' créé avec succès"
    else
        echo "❌ Erreur lors de la création du repository"
        exit 1
    fi
fi

# Attendre que le repository soit accessible
sleep 5

# Importer les ontologies (dans l'ordre)
echo "📚 Import des ontologies..."

import_ontology() {
    FILE=$1
    BASE_URI=$2
    
    if [ -f "/ontologies/$FILE" ]; then
        echo "   📄 Import de $FILE..."
        
        curl -X POST \
            -H "Content-Type: application/x-turtle" \
            --data-binary "@/ontologies/$FILE" \
            "$GRAPHDB_URL/repositories/$REPO_NAME/statements?baseURI=$BASE_URI" \
            > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "      ✅ $FILE importé"
        else
            echo "      ⚠️  Erreur lors de l'import de $FILE (peut déjà exister)"
        fi
    else
        echo "   ⚠️  $FILE non trouvé, ignoré"
    fi
}

# Import des ontologies dans l'ordre
import_ontology "cgontologie1.ttl" "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"
import_ontology "ontology.ttl" "http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO#"
import_ontology "stakeholder_mapping_clean.ttl" "http://www.semanticweb.org/adamy/ontologies/2025/WLCPO#"

echo "🎉 Initialisation GraphDB terminée!"
echo "🌐 GraphDB accessible sur: http://localhost:7200"
echo "🌐 Backend Flask accessible sur: http://localhost:8000"

