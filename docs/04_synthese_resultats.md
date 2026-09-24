# Synthèse des résultats et recommandations

Périmètre : Yellow Taxis de New York, janvier 2019, **7 440 812 courses analysées** (97,04 % des
7 667 792 courses brutes). Tous les chiffres proviennent des requêtes de `sql/analyses_metier.sql`
(résultats bruts dans `analysis/results/`).

## Chiffres clés du mois

| Indicateur | Valeur |
|---|---|
| Courses | 7,44 M (240 000 par jour) |
| Chiffre d'affaires | 114,8 M$ |
| Panier moyen | 15,43 $ |
| Durée moyenne | 13,0 min |
| Distance moyenne | 2,83 miles |
| Revenu par minute de course | 1,19 $ |
| Paiement par carte | 72,0 % des courses |
| Taux de pourboire (carte) | 20,2 % du tarif |

## Q1 et Q7. Quand la demande est-elle la plus forte ?

- Pic en semaine à **18h** : environ 18 000 courses par heure le jeudi et le vendredi.
- Creux à 3h-4h en semaine (environ 800 courses par heure), soit 22 fois moins qu'au pic.
- **Nuits du week-end** : entre 0h et 2h, le samedi et le dimanche comptent environ 3 fois plus de courses
  qu'une nuit du lundi au jeudi (11 400 courses à 0h dans la nuit de samedi à dimanche contre 3 500 un mardi).
- Jeudi et vendredi sont les jours les plus chargés (262 000 courses par jour) ; le dimanche le plus
  calme (208 000, soit -21 %). Les jours fériés baissent encore : -26 % le 1er janvier par rapport à un
  mardi moyen, -19 % le Martin Luther King Day par rapport à un lundi moyen.

## Q2. À quelle heure une minute de course rapporte-t-elle le plus ?

- Le revenu par minute culmine à **1,66 $ à 5h** et tombe à **1,08 $ entre 8h et 9h (-35 %)**.
- La vitesse moyenne suit la même courbe (23 mph à 5h, 11 mph à 9h) : la **congestion** en est la cause.
- L'effet n'est pas un simple effet de mix (plus de courses aéroport tôt le matin) : **à l'intérieur de
  Manhattan uniquement**, le revenu par minute passe de 1,49 $ à 5h à 1,00 $ à 9h (-33 %).
- Le pic de demande (18h) ne coïncide donc pas avec le pic de rentabilité : de 7h à 18h, un chauffeur a
  beaucoup de clients mais chaque minute rapporte moins.

## Q3. Quels types de course portent le CA et la productivité ?

| Type de course | Part des courses | Part du CA | Panier moyen | Revenu par minute |
|---|---|---|---|---|
| Intra-Manhattan | 85,2 % | 65,5 % | 11,86 $ | 1,10 $ |
| Aéroport | 6,4 % | **21,2 %** | 51,18 $ | **1,59 $** |
| Manhattan <> autres boroughs | 5,2 % | 10,0 % | 29,75 $ | 1,19 $ |
| Hors Manhattan | 3,2 % | 3,4 % | 16,00 $ | 1,18 $ |

Les courses aéroport sont **45 % plus productives** à la minute que les courses intra-Manhattan.
Détail par aéroport : JFK 58,87 $ par course (1,60 $/min), LaGuardia 42,01 $ (1,53 $/min).

**Nuance importante** : les données ne mesurent que le temps passé avec un client. L'attente dans la
file de taxis de l'aéroport n'est pas enregistrée. Seuil de rentabilité indicatif : au-delà d'environ
**17 minutes d'attente à JFK** (11 minutes à LaGuardia), une course aéroport rapporte moins par minute
qu'une course intra-Manhattan (calcul : 58,87 $ / 1,10 $ par minute = 53,5 min, moins 36,9 min de
course ; ce calcul néglige aussi le temps à vide entre deux courses à Manhattan).

## Q4. Quelles zones concentrent le chiffre d'affaires ?

- **14 zones sur 263** génèrent 50 % du CA ; 32 zones en génèrent 80 %.
- JFK (9,3 % du CA) et LaGuardia (6,4 %) arrivent en tête, suivies de Midtown Center (3,8 %),
  Times Square (3,4 %), Midtown East (3,3 %) et Upper East Side (2 × 3,2 %).

## Q5. Courses courtes ou longues ?

Le revenu par minute suit une **courbe en U** :

| Tranche | Part des courses | Revenu par minute |
|---|---|---|
| < 1 mile | 27,0 % | 1,39 $ |
| 1 à 2 miles | 34,5 % | 1,09 $ |
| **2 à 5 miles** | 25,3 % | **1,01 $** (minimum) |
| 5 à 10 miles | 7,6 % | 1,24 $ |
| 10 miles et plus | 5,6 % | 1,54 $ |

Les très courtes courses bénéficient de la prise en charge fixe (2,50 $) ; les longues roulent plus vite
(voies rapides). Les courses de 2 à 5 miles cumulent les inconvénients : trafic urbain et prise en
charge amortie.

## Q6. Paiement et pourboires

- 72,0 % des courses sont payées par carte, 27,7 % en espèces.
- Taux de pourboire sur carte : **20,2 %** du tarif ; il est plus faible hors Manhattan (13,7 %) et sur
  les trajets entre Manhattan et les autres boroughs (15,6 %).
- Les pourboires en espèces ne sont pas enregistrés (638 $ au total sur 2 millions de courses) : le revenu
  réel des chauffeurs est **sous-estimé** pour 28 % des courses.

## Q8. Qualité des données

| Étape | Courses | % du brut |
|---|---|---|
| Courses brutes | 7 667 792 | 100 % |
| Rejets (règles métier) | 177 276 | 2,31 % |
| Anomalies signalées | 49 704 | 0,65 % |
| **Courses analysées** | **7 440 812** | **97,04 %** |

- Premier motif de rejet : « aucun passager » (115 573 courses, 1,5 %). **99,9 % de ces rejets
  proviennent d'un seul fournisseur de taximètre** (Creative Mobile Technologies, 3,9 % de ses courses) :
  il s'agit d'un défaut de saisie systémique, pas d'erreurs aléatoires.
- 508 courses portent une date hors de janvier 2019 (jusqu'en 2008) : horloges de taximètre déréglées.

## Recommandations

| # | Recommandation | Appui chiffré | Priorité |
|---|---|---|---|
| 1 | **Renforcer la présence aux aéroports, JFK en priorité**, en mesurant le temps d'attente dans la file : au-delà de ~17 min à JFK, réorienter vers Manhattan | 21 % du CA pour 6 % des courses ; 1,59 $/min contre 1,10 $ | Haute |
| 2 | **Aligner le planning sur la demande** : maximum de véhicules de 17h à 20h en semaine et de 0h à 2h les nuits de week-end ; réduire l'offre le dimanche et les jours fériés | Pic de 18 000 courses/h ; nuits du week-end x3 ; dimanche -21 % | Haute |
| 3 | **Encourager les créneaux du petit matin (4h-6h)** par des incitations, car ce sont les heures les plus productives | 1,66 $/min à 5h, +40 % par rapport à la moyenne ; 15 % de courses aéroport à 5h | Moyenne |
| 4 | **Concentrer le positionnement sur 14 zones** qui font la moitié du CA (Midtown, Upper East Side, Penn Station, Times Square) | 14 zones sur 263 = 50 % du CA | Moyenne |
| 5 | **Promouvoir le paiement par carte** (terminaux, communication) : pourboires traçables et plus élevés | 28 % de paiements en espèces sans pourboire enregistré | Moyenne |
| 6 | **Signaler au fournisseur Creative Mobile Technologies** le défaut de saisie du nombre de passagers | 115 000 courses rejetées, 99,9 % chez ce fournisseur | Basse |
| 7 | **Mesurer l'impact de la surtaxe de congestion** (2,50 $ dès février 2019) en relançant le pipeline sur février et mars | Janvier 2019 = période de référence | Basse |
