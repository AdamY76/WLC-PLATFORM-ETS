# 🌍 Du fichier IFC au « graph » de données (explication simple)

Ce guide explique, sans jargon, comment ta plateforme transforme un fichier IFC en un « graph » de connaissances, et comment toute l’application s’appuie dessus comme sur un répertoire de données central.

---

## 1) C’est quoi un fichier IFC ?
- **IFC** = un fichier BIM qui décrit un bâtiment (murs, fenêtres, équipements...).
- Chaque élément a des infos (un identifiant, un nom, un matériau, parfois un code Uniformat, etc.).

Image mentale: un gros classeur plein de fiches d’objets du bâtiment.

---

## 2) C’est quoi un « graph RDF » (très simplement) ?
- Pense à un **Google Maps de tes données**: des points (les choses) et des flèches entre eux (les relations).
- En RDF, on enregistre des **phrases très simples**: « Sujet – Prédicat – Objet ».
  - Exemple: « Le mur123 – a pour matériau – Béton ».
- Ces phrases sont standardisées et stockées dans **GraphDB**.

Image mentale: chaque phrase est une flèche entre deux bulles. Tu peux parcourir les bulles et leurs liens librement.

---

## 3) Ce que fait la plateforme (en 3 étapes)

1. **Tu déposes un fichier IFC** dans l’interface.
   - La plateforme lit uniquement les infos utiles: identifiant unique (GUID), nom, code/description Uniformat, matériau, etc.

2. **On transforme ces infos en « phrases » RDF**.
   - Exemple simplifié pour un mur:
     - « mur123 est un Élément »
     - « mur123 a pour GUID “2Mn3Pz...” »
     - « mur123 a pour nom “Mur extérieur” »
     - « mur123 a pour code Uniformat “B2010” »
     - « mur123 a pour matériau “Béton” »

3. **On stocke ces phrases dans GraphDB** (le « graph ») et c’est tout.
   - Pas de base SQL à côté.
   - Pas de copies temporaires qui divergent.
   - Le graph devient le **répertoire de données central** de l’application.

---

## 4) Le « graph » comme répertoire de données central
- Toute l’application **lit** et **écrit** uniquement dans le graph via des requêtes (SPARQL).
- Quand tu changes un coût, une stratégie de fin de vie, ou un responsable: on **met à jour le graph**.
- Quand l’interface affiche un tableau: elle **lit le graph**.

Image mentale: un seul classeur bien rangé, tout le monde y lit/écrit au même endroit.

---

## 5) Pourquoi c’est bien ?
- **Une seule source de vérité**: fini les données dupliquées.
- **Relations explicites**: on sait « qui est lié à quoi » (un coût lié à un élément, à une année, etc.).
- **Évolutif**: on peut ajouter de nouvelles infos (ex: fin de vie) sans casser ce qui existe.
- **Interopérable**: format standard, compatible avec d’autres outils du web sémantique.

---

## 6) Exemple concret (mur)
Des « phrases » très simples (version lisible):
- Le mur123 est un Élément.
- Le mur123 a pour GUID "2Mn3Pz...".
- Le mur123 a pour description Uniformat "Murs extérieurs".
- Le mur123 a pour matériau "Béton".
- Le mur123 a un **coût de construction** de 50 000.
- Le mur123 a une **stratégie fin de vie** "Recycle".

Tu peux imaginer toutes ces phrases reliées entre elles comme un réseau.

---

## 7) Où se passent les choses ? (rôles des composants)
- **Frontend (interface web)**: affiche les tableaux et graphiques, envoie des demandes au serveur.
- **Backend (Flask)**: traduit les actions en requêtes vers le graph (lecture/écriture), sans stocker de données.
- **GraphDB (le graph)**: stocke toutes les phrases (les données) et gère les relations.

---

## 8) Petit schéma mental

IFC → (extraction) → Phrases simples → (stockage) → GraphDB → (lecture/écriture) → Application

- « Extraction » = on prend les infos utiles du fichier IFC.
- « Phrases simples » = on transforme en relations faciles à relier.
- « GraphDB » = le classeur unique où l’on range tout.
- « Application » = ne fait que lire/écrire dans ce classeur.

---

## 9) Comment vérifier que tout fonctionne ?
- Démarrer la plateforme et ouvrir l’interface: `http://localhost:8000`.
- Si le badge est **vert** (connecté), l’application parle bien au graph.
- Tu peux aussi tester un point simple: `http://localhost:8000/ping` → doit répondre « OK ».

---

## 10) Fin de vie (EOL) en 1 phrase
- Pour chaque élément, tu peux choisir une **stratégie de fin de vie** (ex: Recycle, Réutilise...).
- C’est enregistré comme une phrase dans le graph: « élémentX – a pour stratégie – Recycle ».
- L’onglet « Gestion Fin de Vie » lit et met à jour ces phrases directement dans GraphDB.

---

## 11) À retenir
- Le **fichier IFC** est la source brute.
- Le **graph RDF (GraphDB)** est le **répertoire unique** où l’on range des phrases simples sur chaque élément.
- L’**application** ne garde rien pour elle: elle **lit et écrit** uniquement dans ce graph.
- Résultat: des données cohérentes, liées, et faciles à faire évoluer.
