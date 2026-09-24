# Dictionnaire de données

## Source

- **NYC TLC Yellow Taxi Trip Records**, janvier 2019 : 7 667 792 courses, 18 colonnes
  ([page officielle](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)).
- **Taxi Zone Lookup** : référentiel des 265 zones officielles (borough, zone, type de zone).

Chaque course est enregistrée par le taximètre. Point d'attention : **les pourboires en espèces ne
sont pas saisis**, seuls les pourboires payés par carte apparaissent dans les données.

## Couches du pipeline

| Couche | Contenu | Emplacement |
|---|---|---|
| Bronze | Données brutes typées, partitionnées par année et mois | `data/bronze/` |
| Silver | Courses valides, dédoublonnées, enrichies (durée, vitesse, zones) | `data/silver/yellow_tripdata` |
| Silver (rejets) | Courses rejetées avec leur motif (`reject_reason`) | `data/silver/rejected` |
| Gold | Modèle en étoile au grain course + table qualité | `data/gold/` |
| Export BI | Tables prêtes pour Power BI (faits agrégés) | `powerbi/data/` |

## Table de faits `fact_trips` (Gold, une ligne par course)

| Colonne | Description |
|---|---|
| `date_id` | Date de prise en charge (AAAAMMJJ), clé vers `dim_date` |
| `hour` | Heure de prise en charge (0 à 23), clé vers `dim_hour` |
| `pickup_location_id` / `dropoff_location_id` | Zones de départ et d'arrivée, clés vers `dim_zone` |
| `vendor_id` | Fournisseur du taximètre, clé vers `dim_vendor` |
| `payment_type` | Mode de paiement, clé vers `dim_payment` |
| `passenger_count` | Nombre de passagers |
| `trip_distance` | Distance en miles |
| `trip_duration_minutes` | Durée calculée (dépose moins prise en charge) |
| `avg_speed_mph` | Vitesse moyenne calculée |
| `fare_amount` | Tarif au taximètre ($) |
| `extra`, `mta_tax`, `improvement_surcharge` | Suppléments et taxes ($) |
| `tip_amount` | Pourboire ($), carte uniquement |
| `tolls_amount` | Péages ($) |
| `total_amount` | Montant total payé ($) |
| `trip_category` | **Segment métier** : Aéroport, Intra-Manhattan, Manhattan <> autres boroughs, Hors Manhattan |
| `distance_band` | **Tranche de distance** : < 1, 1 à 2, 2 à 5, 5 à 10, 10 miles et plus |
| `anomaly_reason` | Motif d'anomalie (NULL si la course est exploitable) |

## Table de faits agrégée `fact_trips_agg` (Power BI)

Grain : **jour × heure × zone de départ × mode de paiement × type de course × tranche de distance**.
Colonnes de mesure (toutes additives) : `nb_trips`, `nb_passengers`, `distance_miles`,
`duration_minutes`, `fare_amount`, `tip_amount`, `tolls_amount`, `surcharges_amount`, `total_amount`.

## Dimensions

| Table | Colonnes principales |
|---|---|
| `dim_date` | `date_id`, `date`, `day`, `day_of_week` (1 = lundi), `day_name` (en français), `is_weekend`, `is_holiday`, `holiday_name`, `iso_week` |
| `dim_hour` | `hour`, `hour_label` (« 08h »), `time_slot` (Nuit, Pointe du matin, Journée, Pointe du soir, Soirée) |
| `dim_zone` | `location_id`, `borough`, `zone`, `service_zone`, `is_airport` |
| `dim_payment` | `payment_type`, `payment_label` |
| `dim_vendor` | `vendor_id`, `vendor_name` |
| `data_quality` | `step`, `category` (Entrée, Rejet, Anomalie, Sortie), `reason`, `nb_trips`, `pct_of_raw` |

## Règles de gestion

Toutes les règles sont codées une seule fois dans `src/business_rules.py` et couvertes par des tests.

**Règles de validité (Silver)** : une course est rejetée si l'une de ces conditions est vraie.

| Règle | Justification |
|---|---|
| Zone de départ ou d'arrivée manquante | Course non localisable |
| Dépose antérieure ou égale à la prise en charge | Horodatage incohérent |
| Distance nulle ou négative | Course non effectuée ou erreur de compteur |
| Tarif nul ou négatif | Remboursement, annulation ou erreur |
| Aucun passager | Course de test ou erreur de saisie |
| Doublon (même taximètre, horaires et zones) | Double enregistrement |

**Anomalies (Gold)** : la course reste dans les données mais est exclue des indicateurs.

| Anomalie | Seuil | Justification |
|---|---|---|
| Hors période analysée | Date hors janvier 2019 | Erreur d'horloge du taximètre (dates jusqu'en 2008) |
| Montant aberrant | > 1 000 $ | La plus longue course légitime observée (~130 miles) coûte ~600 $ |
| Vitesse aberrante | > 100 mph | Physiquement impossible en ville |
| Durée aberrante | > 3 heures | Taximètre non arrêté |
| Course trop courte | < 1 minute | Taximètre lancé par erreur (distance quasi nulle) |

**Segmentation** : les aéroports sont les zones 1 (Newark), 132 (JFK) et 138 (LaGuardia) ; une course
est classée « Aéroport » si elle part d'un aéroport **ou** s'y rend.
