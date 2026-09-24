# Checklist de finalisation du projet

Toutes les actions restantes pour terminer le projet, dans l'ordre. Coche au fur et à mesure.

Légende des outils : 🟦 IntelliJ IDEA · 🟨 Power BI Desktop · 🌐 Navigateur (GitHub) · 📝 Hors outil

---

## Étape 1 : Récupérer le projet (5 min)

- [ ] 🟦 *Git* > **Pull** sur la branche `dev` pour récupérer tout le travail.
- [ ] 🟦 Vérifier la présence de `powerbi/NYC_Taxi_Dashboard.pbip` et du dossier `powerbi/data/` (6 fichiers `.parquet`).

## Étape 2 : Ouvrir et vérifier le dashboard (20 min)

Détail : [docs/03_guide_powerbi.md](03_guide_powerbi.md), sections 2 et 3.

- [ ] 🟨 Mettre Power BI Desktop à jour si sa version est antérieure à mai 2025.
- [ ] 🟨 Ouvrir `powerbi/NYC_Taxi_Dashboard.pbip`.
- [x] 🟨 `DossierDonnees` renseigné automatiquement par `generer_pbip.py` (à relancer si le dépôt change de dossier).
- [ ] 🟨 *Actualiser maintenant* puis vérifier la **recette** (7 440 812 courses, 114,8 M$, 1,19 $/min, 97,04 %).
- [ ] 🟨 Parcourir les 5 pages, vérifier qu'aucun visuel n'est en erreur (sinon : tableau de dépannage du guide).
- [ ] 🟨 Parcourir la vue **Modèle** et la table `_Mesures` : savoir expliquer chaque relation et les mesures clés.

## Étape 3 : S'approprier le rapport (30 à 60 min, recommandé)

- [ ] 🟨 Retouches visuelles personnelles (polices, couleurs, unités des cartes).
- [ ] 🟨 Ajouter la ligne moyenne sur « Revenu par minute selon l'heure » (volet *Analytique*).
- [x] 🟨 Navigateur de pages (généré sur chaque page).
- [ ] 🟨 Synchroniser les segments de la page 1 sur les autres pages (optionnel).
- [ ] 🟨 Tester l'interactivité : cliquer sur « Aéroport » dans un visuel et observer le filtrage croisé.
- [ ] 🟨 *Fichier* > *Enregistrer* (Ctrl+S).

## Étape 4 : Produire les livrables (20 min)

- [x] 🟨 *Enregistrer sous* > `powerbi/NYC_Taxi_Dashboard.pbix`.
- [x] 🟨 *Exporter* > *PDF* > `powerbi/NYC_Taxi_Dashboard.pdf`.
- [x] 🟨 5 captures d'écran dans `docs/images/` : `dashboard_1_vue_ensemble.png`, `dashboard_2_quand.png`,
      `dashboard_3_ou.png`, `dashboard_4_rentabilite.png`, `dashboard_5_qualite.png`.
- [x] 🟦 Dans `README.md` (section 8), supprimer les lignes `<!--` et `-->` autour des images du dashboard.
- [ ] 🟦 Si tu as modifié des chiffres ou des visuels, vérifier la cohérence avec le README et `docs/04_synthese_resultats.md`.

## Étape 5 : Publier sur GitHub (15 min)

- [ ] 🟦 *Git* > **Commit** de tous les nouveaux fichiers, puis **Push** vers `dev`.
- [ ] 🌐 Ouvrir une **Pull Request** `dev` → `main` sur GitHub, la relire, puis la fusionner
      (la branche par défaut est celle que voient les visiteurs du dépôt).
- [ ] 🌐 Vérifier le rendu du README sur GitHub : images, schéma Mermaid, liens vers `docs/`.
- [ ] 🌐 Paramètres du dépôt (roue crantée à droite de *About*) :
  - Description : *Analyse de 7,7 M de courses de taxis new-yorkais : pipeline PySpark, SQL, dashboard Power BI et recommandations métier.*
  - Topics : `data-analysis`, `power-bi`, `sql`, `pyspark`, `data-visualization`, `nyc-taxi`, `portfolio`.
- [ ] 🌐 Optionnel : renommer le dépôt en `nyc-taxi-analyse-revenus` (le nom actuel évoque le Data Engineering alors que le projet est désormais orienté Data Analyst). GitHub redirige automatiquement l'ancien lien.
- [ ] 🌐 Épingler le dépôt sur ton profil GitHub (*Customize your pins*).

## Étape 6 : Valoriser le projet (30 min)

- [ ] 📝 **CV**, rubrique Projets (exemple) :
  > **Analyse de la rentabilité d'une flotte de taxis new-yorkais** (Python, PySpark, SQL, Power BI)
  > Analyse de 7,7 M de courses réelles pour identifier où et quand positionner les chauffeurs.
  > Pipeline de nettoyage traçable (97 % de données exploitables), modèle en étoile, 12 analyses SQL,
  > dashboard Power BI de 5 pages. Principal résultat : les aéroports génèrent 21 % du CA avec 6 % des courses.
- [ ] 📝 **LinkedIn** : ajouter le projet dans la section *Projets* avec le lien GitHub et une capture du dashboard.
- [ ] 📝 Préparer un **pitch oral de 2 minutes** : contexte, problématique, démarche, 3 résultats, 1 recommandation, 1 limite.
- [ ] 📝 Préparer les **questions d'entretien** probables :
  - Pourquoi le revenu par minute plutôt que le panier moyen ?
  - Comment as-tu choisi les seuils d'anomalie ?
  - Pourquoi une table agrégée dans Power BI ? Est-ce que les KPI restent exacts ?
  - Comment prouves-tu que la baisse de productivité vient de la congestion et pas d'un effet de mix ?
  - Quelles sont les limites de ton analyse ?
  - Différence entre `ALLSELECTED` et `ALL` en DAX ?

## Étape 7 : Pour aller plus loin (optionnel)

- [ ] Publier le rapport sur Power BI Service (compte professionnel ou étudiant requis) et ajouter le lien public dans le README.
- [ ] Étendre à plusieurs mois (février et mars 2019) pour mesurer l'impact de la surtaxe de congestion.
