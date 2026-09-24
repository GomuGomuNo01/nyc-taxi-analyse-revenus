# Guide Power BI Desktop : ouvrir, comprendre et finaliser le dashboard

Le dashboard est livré sous forme de **projet Power BI (`.pbip`)**, généré par le script
[`powerbi/generer_pbip.py`](../powerbi/generer_pbip.py). Ce guide explique comment l'ouvrir, ce que
contient chaque partie et pourquoi, puis comment produire les livrables finaux (`.pbix`, PDF, captures).

Durée estimée : 45 minutes.

> Les noms des menus sont en français, avec l'équivalent anglais entre crochets : *Accueil* [Home].

---

## 1. Qu'est-ce qu'un projet `.pbip` et pourquoi ce format ?

Un `.pbix` est un fichier binaire : impossible de voir dans Git ce qui a changé d'une version à l'autre.
Un projet `.pbip` décrit le même rapport sous forme de **fichiers texte** :

```
powerbi/
├── NYC_Taxi_Dashboard.pbip              # Le fichier à ouvrir (raccourci vers le projet)
├── NYC_Taxi_Dashboard.SemanticModel/    # Le modèle de données (format TMDL)
│   └── definition/
│       ├── expressions.tmdl             # Paramètre DossierDonnees (chemin des fichiers)
│       ├── relationships.tmdl           # Les 4 relations du modèle en étoile
│       └── tables/*.tmdl                # Tables, colonnes, requêtes Power Query, mesures DAX
├── NYC_Taxi_Dashboard.Report/           # Le rapport (format PBIR)
│   └── definition/pages/<page>/visuals/<visuel>/visual.json
├── data/*.parquet                       # Les données
├── generer_pbip.py                      # Le script qui génère tout le projet
├── mesures_dax.dax                      # Les 26 mesures, lisibles en un seul fichier
└── theme_nyc_taxi.json                  # Le thème (couleurs, polices)
```

C'est la pratique « **BI as code** » : le rapport est versionné, relu et reproductible comme du code.
Le projet a été validé avant livraison :
- modèle chargé avec la bibliothèque officielle de Microsoft (Tabular Object Model) : 7 tables, 4 relations, 26 mesures, toutes les références DAX résolues ;
- 57 fichiers du rapport validés contre les schémas JSON officiels de Microsoft ;
- types de visuels et noms de rôles vérifiés sur 58 rapports d'exemple publiés par Microsoft.

---

## 2. Ouvrir le dashboard

### Prérequis
- **Power BI Desktop à jour** (version de mai 2025 ou plus récente). Si la tienne est plus ancienne : Microsoft Store > Power BI Desktop > *Mettre à jour*.
- Le dépôt à jour en local : dans IntelliJ IDEA, *Git* > **Pull** sur la branche `dev`.

### Étapes

1. Double-clique sur `powerbi/NYC_Taxi_Dashboard.pbip` (ou *Fichier* > *Ouvrir* dans Power BI Desktop).

   > Si Power BI affiche un message indiquant que le format n'est pas pris en charge :
   > *Fichier* > *Options et paramètres* > *Options* > **Fonctionnalités en préversion** [Preview features],
   > coche **Enregistrement de projet Power BI (.pbip)**, **Stocker le modèle sémantique au format TMDL** et
   > **Stocker les rapports au format PBIR** (selon ta version, certaines options n'existent plus car elles
   > sont activées par défaut), puis redémarre Power BI Desktop.

2. Les visuels sont vides ou en erreur : c'est normal, les données ne sont pas encore chargées.
   Le projet ne contient que la **définition** du rapport, pas de copie des données.

3. **Dossier des données** : le paramètre `DossierDonnees` est renseigné automatiquement par
   `generer_pbip.py` avec le chemin absolu de `powerbi\data\` sur le poste où le script a été lancé
   (Power Query n'accepte pas de chemin relatif). Si le dépôt a été cloné ou déplacé ailleurs :
   relance `python powerbi/generer_pbip.py`, ou bien *Accueil* > **Transformer les données** (flèche du bas) >
   **Modifier les paramètres** [Edit parameters] et colle le chemin de `powerbi\data\`
   **avec la barre oblique inverse finale**.

4. Clique sur **Actualiser maintenant** dans le bandeau jaune (ou *Accueil* > **Actualiser**).
   Le chargement prend quelques secondes (640 000 lignes).

5. **Recette** : sur la page *1. Vue d'ensemble*, sans filtre, vérifie les cartes :

   | Mesure | Valeur attendue |
   |---|---|
   | Courses | 7 440 812 (affiché 7 M ou 7,44 M selon l'unité automatique) |
   | Chiffre d'affaires | 114 788 696 $ (115 M) |
   | Panier moyen | 15,43 $ |
   | Revenu par minute | 1,19 $ |
   | Part du CA aéroports | 21,2 % |
   | Taux de pourboire (carte) | 20,2 % |

   Page *5. Qualité des données* : 7 667 792 courses brutes, 7 440 812 analysées, 97,04 % exploitables.
   Ces valeurs sont identiques aux résultats SQL de `analysis/results/`. **On ne présente jamais un chiffre
   qu'on n'a pas recoupé avec une autre source.**

6. *Fichier* > **Enregistrer** (Ctrl+S) : Power BI enregistre le projet `.pbip`.

### En cas de problème

| Symptôme | Cause probable | Solution |
|---|---|---|
| « Impossible de trouver le fichier ... parquet » | Chemin du paramètre incorrect | Vérifie la barre oblique finale et l'orthographe du chemin (étape 3) |
| Un visuel affiche une croix ou une erreur | Visuel non reconnu par ta version | Supprime-le et recrée-le à l'identique (voir section 4 : champs utilisés) |
| Couleurs par défaut au lieu du thème | Thème non appliqué | *Affichage* > *Thèmes* > *Parcourir les thèmes* > `powerbi/theme_nyc_taxi.json` |
| Les jours sont triés dans l'ordre alphabétique | Tri par colonne perdu | Vue *Table* > colonne `Jour` > *Outils de colonne* > *Trier par colonne* > `N° jour semaine` |

---

## 3. Comprendre le modèle de données

Ouvre la vue **Modèle** (troisième icône à gauche).

### Modèle en étoile

- **Au centre, `fact_trips_agg`** (table de faits) : 638 473 lignes de sommes et de comptages
  (nombre de courses, CA, minutes...) au grain jour × heure × zone × paiement × type de course × tranche de distance.
- **Autour, les dimensions** : `dim_date` (calendrier), `dim_hour` (heures et créneaux),
  `dim_zone` (265 zones), `dim_payment` (modes de paiement).
- **Relations plusieurs-à-un, filtrage unidirectionnel** : un filtre sur une dimension (par exemple
  « Samedi ») se propage vers les faits, jamais l'inverse. C'est le comportement le plus prévisible.
- **`data_quality`** est indépendante (pas de relation) : c'est une table de synthèse de la qualité.
- **`_Mesures`** regroupe les 26 mesures, rangées en dossiers (Volume et CA, Productivité, Parts...).

### Choix de modélisation à savoir expliquer

| Choix | Pourquoi |
|---|---|
| Colonnes renommées en français (`Jour`, `Heure`, `Zone`...) | Le lecteur métier ne doit jamais voir `day_name` ou `pickup_location_id` |
| Clés techniques et colonnes numériques masquées | On n'utilise que des mesures : pas de somme implicite fausse (option *discourage implicit measures* activée) |
| `Jour` trié par `N° jour semaine`, `Heure` par `N° heure` | Lundi à dimanche et 0h à 23h, pas l'ordre alphabétique |
| `dim_date` marquée comme **table de dates** | Axe chronologique correct et fonctions temporelles DAX disponibles |
| Paramètre `DossierDonnees` | Le chemin est modifiable en un seul endroit |
| Format Parquet | Types conservés, pas de problème de virgule ou de point décimal |

Pour voir la requête Power Query d'une table : *Transformer les données*, puis sélectionne la table.

### Les mesures DAX clés

Toutes les mesures sont listées et commentées dans [`powerbi/mesures_dax.dax`](../powerbi/mesures_dax.dax).

| Mesure | Formule | Idée à retenir |
|---|---|---|
| Revenu par minute | `DIVIDE([Chiffre d'affaires], [Minutes de course])` | KPI central. Toujours un rapport de sommes, jamais une moyenne de moyennes |
| Part du CA | `DIVIDE([CA], CALCULATE([CA], ALLSELECTED()))` | `ALLSELECTED` : total de la sélection des segments, en ignorant le découpage du visuel |
| Courses par jour (hors fériés) | `CALCULATE([Courses par jour], dim_date[Jour férié] = FALSE())` | `CALCULATE` modifie le contexte de filtre |
| CA top 10 zones | `RANKX` sur les zones, CA renvoyé seulement si rang ≤ 10 | Les autres zones renvoient une valeur vide et disparaissent du graphique |
| Taux de pourboire (carte) | Pourboires / tarif, filtrés sur la carte | Les pourboires en espèces ne sont pas enregistrés |

---

## 4. Les 5 pages du rapport

Chaque page répond à **une question métier** (écrite dans son titre), avec les KPI ou le visuel principal
en haut, le détail en dessous, et un encadré **« À retenir »** qui donne la conclusion.

| Page | Question | Visuels (champs utilisés) |
|---|---|---|
| 1. Vue d'ensemble | Comment se porte l'activité ? | Segments : Période (`Date`), Type de course, Mode de paiement, Jour. 6 cartes : Courses, CA, Panier moyen, Revenu par minute, Part du CA aéroports, Taux de pourboire. Courbe : CA par `Date`. Barres : Part des courses et Part du CA par Type de course |
| 2. Quand ? | À quelles heures renforcer la flotte ? | Matrice `Jour` × `Heure` avec Courses par jour (hors fériés) et fond en dégradé. Histogramme : Courses par Heure. Courbe : Revenu par minute par Heure. Barres : Revenu par minute par Créneau |
| 3. Où ? | Où positionner les véhicules ? | Barres : CA top 10 zones par Zone. Nuage de points : Zone, légende Borough, X = Courses, Y = Revenu par minute, taille = CA. Table : Zone, Borough, Courses, CA, Part du CA, Panier moyen, Revenu par minute. Carte proportionnelle : CA par Borough |
| 4. Rentabilité | Quelles courses privilégier ? | Histogrammes : Revenu par minute par Type de course et par Tranche de distance. Barres : Taux de pourboire par Type de course. Anneau : Courses par Mode de paiement |
| 5. Qualité des données | Peut-on faire confiance aux chiffres ? | 4 cartes : Courses brutes, écartées, analysées, Taux exploitable. Barres : Rejets et anomalies par Motif (légende Catégorie). Table : Étape, Motif, Courses (étape), Part des courses brutes |

**Comment lire le nuage de points (page 3)** : en haut à droite, les zones à fort volume **et** forte
productivité (priorités de positionnement) ; en bas à droite, du volume peu rentable (centre de Manhattan
aux heures de bureau) ; en haut à gauche, des zones rares mais rentables (aéroports).

---

## 5. Personnaliser (recommandé pour t'approprier le rapport)

Chaque page dispose déjà d'un **navigateur de pages** (en haut à droite). Quelques retouches dans
Power BI Desktop rendront le rapport plus personnel :
- ajuster tailles de police et couleurs des barres (*Format du visuel*) ;
- ajouter la **ligne moyenne** sur la courbe « Revenu par minute selon l'heure » (volet *Analytique*, icône loupe) ;
- synchroniser les segments de la page 1 sur les autres pages (*Affichage* > **Synchroniser les segments**).

> **Attention** : relancer `python powerbi/generer_pbip.py` régénère le projet et **écrase** les
> modifications faites dans Power BI Desktop. Après tes retouches manuelles, ne relance plus le script
> (ou reporte tes modifications dans le script).

---

## 6. Produire les livrables finaux

Les livrables sont déjà dans le dépôt (`powerbi/NYC_Taxi_Dashboard.pbix`, `powerbi/NYC_Taxi_Dashboard.pdf`,
`docs/images/dashboard_*.png`). Après une retouche du rapport, régénère-les ainsi :

1. **Fichier `.pbix`** (un seul fichier, pratique pour un recruteur) : *Fichier* > **Enregistrer sous** >
   type *Fichiers Power BI (.pbix)* > `powerbi/NYC_Taxi_Dashboard.pbix`.
   Le `.pbix` embarque les données : il s'ouvre sans configurer de chemin.
2. **Export PDF** : *Fichier* > **Exporter** > **Exporter au format PDF** > `powerbi/NYC_Taxi_Dashboard.pdf`.
3. **Captures d'écran** de chaque page : `Win + Maj + S` sur le canevas, ou conversion des pages du PDF
   en images (PyMuPDF, 150 dpi). Enregistrées dans `docs/images/` avec ces noms exacts :
   `dashboard_1_vue_ensemble.png`, `dashboard_2_quand.png`, `dashboard_3_ou.png`,
   `dashboard_4_rentabilite.png`, `dashboard_5_qualite.png`.
4. Dans IntelliJ IDEA : *Git* > **Commit** (coche les nouveaux fichiers), message par exemple
   `Ajout du dashboard finalisé, export PDF et captures`, puis **Commit and Push** vers `dev`.

Le fichier `.gitignore` exclut déjà le cache local de Power BI (`.pbi/cache.abf`, `localSettings.json`),
qui n'a pas sa place dans Git.
