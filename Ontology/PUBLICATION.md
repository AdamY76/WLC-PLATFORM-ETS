# Publication de l'ontologie WLCONTO

## URLs

| Ressource | URL |
|-----------|-----|
| Documentation (GitHub Pages) | https://adamY76.github.io/WLC-PLATFORM-ETS/ |
| URI permanente (w3id.org) | https://w3id.org/wlconto |
| IRI de l'ontologie | http://www.semanticweb.org/adamy/ontologies/2025/WLCONTO |
| Licence | [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) |

## Regénérer la documentation

```bash
java -jar widoco.jar \
  -ontFile Ontology/WLCONTO.ttl \
  -outFolder docs \
  -rewriteAll \
  -getOntologyMetadata \
  -htaccess \
  -webVowl \
  -lang en \
  -rewriteBase /WLC-PLATFORM-ETS/

cp docs/index-en.html docs/index.html
```

## Activer GitHub Pages

1. Ouvrir https://github.com/AdamY76/WLC-PLATFORM-ETS/settings/pages
2. **Source** : Deploy from a branch
3. **Branch** : `main` → dossier **`/docs`**
4. Sauvegarder — la doc sera disponible sur https://adamY76.github.io/WLC-PLATFORM-ETS/

## URI permanente w3id.org

Le fichier `w3id/wlconto/.htaccess` contient la redirection vers GitHub Pages.
Pour activer `https://w3id.org/wlconto`, soumettre une PR sur https://github.com/perma-id/w3id
en copiant le dossier `w3id/wlconto/` dans ce dépôt.
