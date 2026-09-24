# Guide Power BI Desktop : construire le dashboard

Ce guide te fait construire le dashboard de A à Z dans **Power BI Desktop** (interface en français).
Chaque étape indique **quoi faire** et **pourquoi**, ce qui sert dans un vrai projet et en entretien.

Durée estimée : 3 à 4 heures.
Prérequis : le dépôt cloné en local (les fichiers de données sont déjà dans `powerbi/data/`, **aucun besoin de lancer Spark**).

> Si ton Power BI est en anglais, les noms des menus sont indiqués entre crochets : *Accueil* [Home].

---

## Étape 0 : Comprendre ce que l'on charge

| Fichier | Rôle | Lignes |
|---|---|---|
| `fact_trips_agg.parquet` | **Table de faits** : sommes et comptages au grain jour × heure × zone de départ × paiement × type de course × tranche de distance | 638 473 |
| `dim_date.parquet` | Calendrier de janvier 2019 (jour en français, week-end, jours fériés) | 31 |
| `dim_hour.parquet` | Heures 0 à 23 et créneaux (nuit, pointe du matin...) | 24 |
| `dim_zone.parquet` | Les 265 zones de taxi officielles (borough, zone, aéroport) | 265 |
| `dim_payment.parquet` | Libellés des modes de paiement | 6 |
| `data_quality.parquet` | Traçabilité : combien de courses écartées, à quelle étape et pourquoi | 12 |

**Pourquoi un modèle en étoile ?** La table de faits contient les chiffres ; les dimensions contiennent
les axes d'analyse (quand, où, comment). Power BI est optimisé pour ce modèle : les filtres
se propagent des dimensions vers les faits, les calculs restent simples et rapides.

**Pourquoi du Parquet et pas du CSV ?** Les types sont stockés dans le fichier (entier, décimal, date).
Avec un CSV américain (`12.5`) ouvert dans un Power BI français (`12,5`), les décimales sont souvent
mal interprétées. Le Parquet supprime ce risque.

---

## Étape 1 : Charger les données avec un paramètre de chemin

**Pourquoi un paramètre ?** Le chemin du dossier est écrit une seule fois. Si tu déplaces le projet
ou si un recruteur ouvre ton `.pbix`, il suffit de changer ce paramètre au lieu de modifier six requêtes.
C'est une bonne pratique professionnelle.

1. Ouvre Power BI Desktop > *Nouveau rapport*.
2. *Accueil* > **Transformer les données** [Transform data]. L'éditeur Power Query s'ouvre.
3. *Accueil* > **Gérer les paramètres** > **Nouveau paramètre** :
   - Nom : `DossierDonnees`
   - Type : `Texte`
   - Valeur actuelle : le chemin complet de `powerbi\data\` **avec la barre oblique finale**,
     par exemple `C:\Users\Cedric\IdeaProjects\nyc-taxi-data-engineering\powerbi\data\`
4. *Accueil* > **Nouvelle source** > **Requête vide** [Blank query], puis *Accueil* > **Éditeur avancé**.
   Remplace tout le contenu par :

   ```powerquery
   let
       Source = Parquet.Document(File.Contents(DossierDonnees & "fact_trips_agg.parquet"))
   in
       Source
   ```

5. Clique sur *Terminé*, puis renomme la requête `fact_trips_agg` (clic droit sur la requête > *Renommer*).
6. Recommence les étapes 4 et 5 pour `dim_date`, `dim_hour`, `dim_zone`, `dim_payment` et `data_quality`
   (en changeant le nom du fichier dans la formule et le nom de la requête).
7. Clic droit sur la requête `DossierDonnees` > décoche **Activer le chargement** (un paramètre n'est pas une table).
8. Vérifie les types (icône à gauche de chaque en-tête de colonne) : `date` doit être de type *Date*,
   les montants de type *Nombre décimal*, `nb_trips` de type *Nombre entier*.
9. *Accueil* > **Fermer et appliquer** [Close & Apply].

✅ Contrôle : dans la vue *Table* (icône grille à gauche), `fact_trips_agg` affiche 638 473 lignes (en bas à gauche).

---

## Étape 2 : Construire le modèle (relations)

**Pourquoi ?** Sans relation, un segment « Jour de la semaine » ne filtrerait pas les courses.
Les relations indiquent à Power BI comment les tables se répondent.

1. Va dans la vue **Modèle** (troisième icône à gauche).
2. Crée les 4 relations en faisant glisser la colonne de la table de faits vers la colonne de la dimension :

   | De (plusieurs) | Vers (un) |
   |---|---|
   | `fact_trips_agg[date_id]` | `dim_date[date_id]` |
   | `fact_trips_agg[hour]` | `dim_hour[hour]` |
   | `fact_trips_agg[pickup_location_id]` | `dim_zone[location_id]` |
   | `fact_trips_agg[payment_type]` | `dim_payment[payment_type]` |

3. Double-clique chaque relation et vérifie : Cardinalité **Plusieurs à un (\*:1)**,
   Direction du filtrage croisé **Unique**.
   *Pourquoi « Unique » ?* Le filtre va de la dimension vers les faits, jamais l'inverse :
   c'est le comportement prévisible d'un modèle en étoile et il évite les ambiguïtés.
4. `data_quality` reste **sans relation** : c'est une table de synthèse indépendante.

---

## Étape 3 : Préparer les dimensions pour le lecteur

**Pourquoi ?** Un rapport professionnel n'affiche jamais « day_of_week = 3 » ni les jours triés par
ordre alphabétique (Dimanche, Jeudi, Lundi...).

1. **Table de dates** : sélectionne `dim_date` > *Outils de table* > **Marquer comme table de dates** > colonne `date`.
   Cela active les fonctions de temps de DAX et garantit un axe chronologique correct.
2. **Tri des libellés** (vue *Table*, sélectionne la colonne puis *Outils de colonne* > **Trier par colonne**) :
   - `dim_date[day_name]` trié par `dim_date[day_of_week]`
   - `dim_hour[hour_label]` trié par `dim_hour[hour]`
   Les créneaux (`time_slot`) et tranches de distance (`distance_band`) sont préfixés par un numéro
   (« 1. », « 2. »...) : ils se trient naturellement dans le bon ordre.
3. **Renommer pour le lecteur** (double-clic sur la colonne dans le volet *Données*) :
   `day_name` > `Jour`, `hour_label` > `Heure`, `time_slot` > `Créneau`, `borough` > `Borough`,
   `zone` > `Zone`, `payment_label` > `Mode de paiement`, `trip_category` > `Type de course`,
   `distance_band` > `Tranche de distance`.
4. **Masquer les clés techniques** (clic droit > *Masquer dans la vue rapport*) : dans `fact_trips_agg`,
   masque `date_id`, `hour`, `pickup_location_id`, `payment_type` et **toutes les colonnes numériques**
   (on les exploitera uniquement via des mesures). Le volet *Données* ne montre plus que ce qui a du sens.

---

## Étape 4 : Appliquer le thème

*Affichage* [View] > **Thèmes** > **Parcourir les thèmes** > sélectionne `powerbi/theme_nyc_taxi.json`.

**Pourquoi ?** Une charte appliquée à tout le rapport en un clic : couleurs cohérentes et accessibles,
fond gris clair et cartes blanches (lisibilité), mêmes polices partout.

---

## Étape 5 : Créer les mesures DAX

**Pourquoi des mesures et pas des colonnes ?** Une mesure est calculée **à la volée selon les filtres**
(un jour, une zone, un segment...). Un ratio comme le panier moyen doit être recalculé pour chaque
sélection : c'est le rôle d'une mesure.

1. *Accueil* > **Entrer des données** [Enter data] > nomme la table `_Mesures` > *Charger*.
   (Le tiret bas la place en haut de la liste : toutes les mesures sont rangées au même endroit.)
2. Sélectionne `_Mesures` puis *Accueil* > **Nouvelle mesure**, colle la première mesure du fichier
   `powerbi/mesures_dax.dax`, valide avec Entrée. Répète pour chaque mesure.
3. Pour chaque mesure, règle le format dans *Outils de mesure* > *Format* comme indiqué en commentaire
   dans le fichier (Devise $, Pourcentage, nombre de décimales).
4. Supprime la colonne vide `Colonne1` de la table `_Mesures`.

Les mesures essentielles à comprendre :

| Mesure | Formule métier | Pourquoi elle compte |
|---|---|---|
| Revenu par minute | CA / minutes de course | Productivité d'un chauffeur : KPI central du projet |
| Panier moyen | CA / courses | Valeur moyenne d'une course |
| Part du CA | CA du segment / CA de la sélection | Poids d'un segment (aéroports, zone...) |
| Taux de pourboire (carte) | pourboires / tarif, sur carte uniquement | Les pourboires espèces ne sont pas enregistrés |
| Taux de données exploitables | courses analysées / courses brutes | Crédibilité des chiffres présentés |

✅ **Valeurs de contrôle** (place une *Carte* par mesure, sans filtre, et compare) :

| Mesure | Valeur attendue |
|---|---|
| Courses | 7 440 812 |
| Chiffre d'affaires | 114 788 696 $ |
| Courses par jour | 240 026 |
| Panier moyen | 15,43 $ |
| Revenu par minute | 1,19 $ |
| Durée moyenne (min) | 13,0 |
| Distance moyenne (miles) | 2,83 |
| Vitesse moyenne (mph) | 13,1 |
| Part paiement carte | 72,0 % |
| Taux de pourboire (carte) | 20,2 % |
| Part du CA aéroports | 21,2 % |
| Taux de données exploitables | 97,04 % |

Si une valeur diffère, vérifie d'abord les relations (étape 2), puis la formule. Cette vérification
s'appelle la **recette** : on ne présente jamais un chiffre qu'on n'a pas recoupé avec une autre source
(ici, les requêtes SQL de `analysis/results/`).

---

## Étape 6 : Construire les pages du rapport

Principe de conception pour chaque page :
- **une question métier par page**, écrite dans le titre ;
- les **KPI en haut** (cartes), le **détail en dessous** (graphiques) ;
- une **zone de texte « À retenir »** avec l'enseignement principal : le lecteur ne doit pas deviner la conclusion ;
- 4 à 6 visuels maximum.

Format de page : *Format de la page* > *Paramètres du canevas* > 16:9 (1280 × 720).

### Page 1 : « Vue d'ensemble »

*Question : comment se porte l'activité ce mois-ci ?*

| Visuel | Configuration |
|---|---|
| 6 cartes (visuel **Carte**) | Courses, Chiffre d'affaires, Panier moyen, Revenu par minute, Part du CA aéroports, Taux de pourboire (carte) |
| **Graphique en courbes** | Axe X : `dim_date[date]` ; Axe Y : Chiffre d'affaires |
| **Graphique à barres groupées** | Axe Y : Type de course ; Axe X : Part des courses **et** Part du CA |
| 3 **Segments** [Slicer] | `dim_date[date]` (style *Entre*), Type de course, Mode de paiement |
| Zone de texte « À retenir » | *Les aéroports représentent 6 % des courses mais 21 % du chiffre d'affaires.* |

Astuce : *Affichage* > **Synchroniser les segments** pour que les filtres suivent le lecteur de page en page.

### Page 2 : « Quand ? Demande et productivité »

*Question : à quelles heures faut-il maximiser le nombre de véhicules en service ?*

| Visuel | Configuration |
|---|---|
| **Matrice** (carte de chaleur) | Lignes : Jour ; Colonnes : Heure ; Valeurs : Courses par jour. Puis *Format du visuel* > *Éléments de cellule* > **Couleur d'arrière-plan** activée (dégradé blanc vers bleu foncé) |
| **Histogramme groupé** | Axe X : Heure ; Axe Y : Courses |
| **Graphique en courbes** | Axe X : Heure ; Axe Y : Revenu par minute. Dans le volet *Analytique* (loupe) : **Ligne moyenne** |
| **Graphique à barres** | Axe Y : Créneau ; Axe X : Revenu par minute |
| Zone de texte « À retenir » | *Pic de demande à 18h, mais le revenu par minute chute de 35 % entre 5h et 8h-9h à cause de la congestion.* |

Ajoute un filtre de page `dim_date[is_holiday]` = Faux pour ne comparer que des jours ordinaires
(le 1er janvier et le Martin Luther King Day faussent les moyennes).

### Page 3 : « Où ? Zones de prise en charge »

*Question : où positionner les véhicules ?*

| Visuel | Configuration |
|---|---|
| **Graphique à barres groupées** | Axe Y : Zone ; Axe X : Chiffre d'affaires. Volet *Filtres* > Zone > Type de filtre **N premiers**, Afficher les éléments : Haut 10, Par valeur : Chiffre d'affaires |
| **Nuage de points** | Valeurs : Zone ; Axe X : Courses ; Axe Y : Revenu par minute ; Taille : Chiffre d'affaires ; Légende : Borough |
| **Table** | Zone, Borough, Courses, Chiffre d'affaires, Part du CA, Panier moyen, Revenu par minute. *Mise en forme conditionnelle* > **Barres de données** sur Chiffre d'affaires |
| **Carte proportionnelle** [Treemap] | Catégorie : Borough ; Valeurs : Chiffre d'affaires |
| Zone de texte « À retenir » | *14 zones sur 263 génèrent la moitié du CA ; JFK et LaGuardia en tête avec 15,7 % du CA.* |

Le nuage de points est le visuel le plus « analyste » du rapport : en haut à droite, les zones à fort
volume **et** forte productivité (les priorités) ; en bas à droite, du volume peu rentable.

### Page 4 : « Quelles courses sont les plus rentables ? »

| Visuel | Configuration |
|---|---|
| **Histogramme groupé** | Axe X : Type de course ; Axe Y : Revenu par minute |
| **Histogramme groupé** | Axe X : Tranche de distance ; Axe Y : Revenu par minute |
| **Graphique à barres groupées** | Axe Y : Type de course ; Axe X : Taux de pourboire (carte) |
| **Graphique en anneau** | Légende : Mode de paiement ; Valeurs : Courses |
| Zone de texte « À retenir » | *Les courses de 2 à 5 miles sont les moins rentables à la minute (1,01 $) ; les courses aéroport les plus rentables (1,59 $).* |

### Page 5 : « Qualité des données »

*Question : peut-on faire confiance aux chiffres ?*

| Visuel | Configuration |
|---|---|
| 3 cartes | Courses brutes, Courses analysées, Taux de données exploitables |
| **Graphique à barres groupées** | Axe Y : `data_quality[reason]` ; Axe X : `nb_trips` ; Légende : `data_quality[step]`. Filtre du visuel : `category` n'est pas *Entrée* ni *Sortie* |
| **Table** | step, reason, nb_trips, pct_of_raw (format Pourcentage) |
| Zone de texte | *Aucune donnée n'est supprimée silencieusement : 2,3 % des courses rejetées (règles métier) et 0,7 % signalées comme anomalies, chacune avec son motif.* |

**Pourquoi cette page ?** En entreprise, la première question d'un décideur face à un chiffre surprenant
est « d'où vient ce chiffre ? ». Montrer la qualité des données est un marqueur de maturité.

---

## Étape 7 : Finitions (ce qui distingue un rapport professionnel)

- **Titres explicites** sur chaque visuel (*Format* > *Général* > *Titre*) : « Revenu par minute selon l'heure »
  plutôt que « Revenu par minute par hour_label ».
- **Alignement** : sélectionne plusieurs visuels > *Format* > *Aligner*. Garde des marges régulières.
- **Info-bulles** : vérifie qu'au survol d'une barre les valeurs sont formatées (devise, %).
- **Navigation** : insère des *Boutons* > *Navigateur* > **Navigateur de pages** en haut de chaque page.
- **Titre dynamique** : ajoute la mesure `Titre période` dans une carte en haut de la page 1.
- **Nom des pages** : double-clic sur l'onglet de page.

---

## Étape 8 : Enregistrer et publier sur GitHub

1. *Fichier* > **Enregistrer sous** > `powerbi/nyc_taxi_dashboard.pbix` (dans le dossier du projet).
2. *Fichier* > **Exporter** > **Exporter au format PDF** > `powerbi/nyc_taxi_dashboard.pdf`
   (un recruteur sans Power BI pourra quand même consulter le rapport).
3. Captures d'écran de chaque page (Windows : `Win + Maj + S`), enregistrées dans `docs/images/` avec ces noms exacts :
   `dashboard_1_vue_ensemble.png`, `dashboard_2_quand.png`, `dashboard_3_ou.png`,
   `dashboard_4_rentabilite.png`, `dashboard_5_qualite.png`.
4. Dans le `README.md`, section **Dashboard Power BI**, supprime les balises de commentaire `<!--` et `-->`
   autour des images pour les afficher.
5. Dans IntelliJ IDEA : menu *Git* > **Commit** (coche les nouveaux fichiers), message par exemple
   `Ajout du dashboard Power BI et des captures`, puis **Commit and Push** vers la branche `dev`.

**Pourquoi IntelliJ pour Git ?** Tu l'utilises déjà : inutile d'ajouter un outil. Power BI Desktop
n'a pas d'intégration Git, on enregistre donc le `.pbix` dans le dossier du projet et on le versionne depuis l'IDE.
