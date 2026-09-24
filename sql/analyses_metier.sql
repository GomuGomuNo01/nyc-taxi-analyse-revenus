-- =====================================================================
-- Analyses métier sur le star schema Gold (dialecte DuckDB / SQL standard)
-- Exécution : python analysis/analyse_metier.py
-- La vue "trips" = fact_trips sans les anomalies (anomaly_reason IS NULL).
-- Chaque bloc commence par "-- name: <nom>" : le script l'exécute et
-- sauvegarde le résultat dans analysis/results/<nom>.csv
-- =====================================================================

-- name: kpis_globaux
-- Vue d'ensemble du mois : volume, chiffre d'affaires, panier, productivité
SELECT
    COUNT(*)                                                    AS nb_courses,
    ROUND(SUM(total_amount), 0)                                 AS chiffre_affaires_usd,
    ROUND(COUNT(*) / 31.0, 0)                                   AS courses_par_jour,
    ROUND(SUM(total_amount) / COUNT(*), 2)                      AS panier_moyen_usd,
    ROUND(AVG(trip_distance), 2)                                AS distance_moyenne_miles,
    ROUND(AVG(trip_duration_minutes), 1)                        AS duree_moyenne_min,
    ROUND(SUM(total_amount) / SUM(trip_duration_minutes), 2)    AS revenu_par_minute_usd,
    ROUND(100.0 * COUNT(*) FILTER (WHERE payment_type = 1) / COUNT(*), 1) AS part_paiement_carte_pct,
    ROUND(100.0 * SUM(tip_amount) FILTER (WHERE payment_type = 1)
               / SUM(fare_amount) FILTER (WHERE payment_type = 1), 1)   AS taux_pourboire_carte_pct
FROM trips;

-- name: demande_heure_jour
-- Q1. Quand la demande est-elle la plus forte ? Courses moyennes par heure,
-- par jour de semaine (on divise par le nombre de jours pour comparer
-- équitablement : janvier 2019 compte 5 mardis mais 4 lundis).
SELECT
    d.day_of_week,
    d.day_name,
    t.hour,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT d.date_id), 0) AS courses_moyennes
FROM trips t
JOIN dim_date d ON t.date_id = d.date_id
WHERE NOT d.is_holiday
GROUP BY d.day_of_week, d.day_name, t.hour
ORDER BY d.day_of_week, t.hour;

-- name: productivite_par_heure
-- Q2. À quelle heure une minute de course rapporte-t-elle le plus ?
-- Le revenu par minute capte l'effet de la congestion : même tarif, mais
-- plus de temps passé par course quand la ville est bouchée.
SELECT
    t.hour,
    COUNT(*)                                                    AS nb_courses,
    ROUND(SUM(total_amount) / SUM(trip_duration_minutes), 2)    AS revenu_par_minute_usd,
    ROUND(SUM(trip_distance) / (SUM(trip_duration_minutes) / 60), 1) AS vitesse_moyenne_mph,
    ROUND(SUM(total_amount) / COUNT(*), 2)                      AS panier_moyen_usd
FROM trips t
GROUP BY t.hour
ORDER BY t.hour;

-- name: type_de_course
-- Q3. Quels segments portent le chiffre d'affaires et lesquels sont les plus
-- productifs pour un chauffeur ?
SELECT
    trip_category                                               AS type_course,
    COUNT(*)                                                    AS nb_courses,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS part_courses_pct,
    ROUND(SUM(total_amount), 0)                                 AS chiffre_affaires_usd,
    ROUND(100.0 * SUM(total_amount) / SUM(SUM(total_amount)) OVER (), 1) AS part_ca_pct,
    ROUND(SUM(total_amount) / COUNT(*), 2)                      AS panier_moyen_usd,
    ROUND(AVG(trip_duration_minutes), 1)                        AS duree_moyenne_min,
    ROUND(SUM(total_amount) / SUM(trip_duration_minutes), 2)    AS revenu_par_minute_usd
FROM trips
GROUP BY trip_category
ORDER BY chiffre_affaires_usd DESC;

-- name: top_zones
-- Q4. Où positionner les véhicules ? Top 10 des zones de prise en charge par CA.
SELECT
    z.zone,
    z.borough,
    COUNT(*)                                                    AS nb_courses,
    ROUND(SUM(t.total_amount), 0)                               AS chiffre_affaires_usd,
    ROUND(100.0 * SUM(t.total_amount) / SUM(SUM(t.total_amount)) OVER (), 1) AS part_ca_pct,
    ROUND(SUM(t.total_amount) / COUNT(*), 2)                    AS panier_moyen_usd
FROM trips t
JOIN dim_zone z ON t.pickup_location_id = z.location_id
GROUP BY z.zone, z.borough
ORDER BY chiffre_affaires_usd DESC
LIMIT 10;

-- name: concentration_zones
-- Q4 bis. Concentration géographique : combien de zones font 50 % et 80 % du CA ?
WITH ca_zone AS (
    SELECT pickup_location_id, SUM(total_amount) AS ca
    FROM trips GROUP BY pickup_location_id
), cumul AS (
    SELECT ca, SUM(ca) OVER (ORDER BY ca DESC) / SUM(ca) OVER () AS part_cumulee
    FROM ca_zone
)
SELECT
    (SELECT COUNT(*) FROM ca_zone)                              AS nb_zones_actives,
    COUNT(*) FILTER (WHERE part_cumulee <= 0.5) + 1             AS nb_zones_50pct_ca,
    COUNT(*) FILTER (WHERE part_cumulee <= 0.8) + 1             AS nb_zones_80pct_ca
FROM cumul;

-- name: tranche_distance
-- Q5. Courses courtes ou longues : laquelle rapporte le plus par minute ?
SELECT
    distance_band                                               AS tranche_distance,
    COUNT(*)                                                    AS nb_courses,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS part_courses_pct,
    ROUND(SUM(total_amount) / COUNT(*), 2)                      AS panier_moyen_usd,
    ROUND(SUM(total_amount) / SUM(trip_duration_minutes), 2)    AS revenu_par_minute_usd,
    ROUND(SUM(total_amount) / SUM(trip_distance), 2)            AS revenu_par_mile_usd
FROM trips
GROUP BY distance_band
ORDER BY distance_band;

-- name: pourboires
-- Q6. Paiement et pourboires. Les pourboires en espèces ne sont PAS
-- enregistrés par le taximètre : le taux de pourboire n'a de sens que
-- sur les paiements par carte.
SELECT
    p.payment_label                                             AS mode_paiement,
    COUNT(*)                                                    AS nb_courses,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS part_courses_pct,
    ROUND(SUM(t.tip_amount), 0)                                 AS pourboires_usd,
    ROUND(100.0 * SUM(t.tip_amount) / SUM(t.fare_amount), 1)    AS taux_pourboire_pct
FROM trips t
JOIN dim_payment p ON t.payment_type = p.payment_type
GROUP BY p.payment_label
ORDER BY nb_courses DESC;

-- name: pourboire_carte_par_type
-- Q6 bis. Taux de pourboire (paiements carte) par type de course
SELECT
    trip_category                                               AS type_course,
    ROUND(100.0 * SUM(tip_amount) / SUM(fare_amount), 1)        AS taux_pourboire_carte_pct,
    ROUND(AVG(tip_amount), 2)                                   AS pourboire_moyen_usd
FROM trips
WHERE payment_type = 1
GROUP BY trip_category
ORDER BY taux_pourboire_carte_pct DESC;

-- name: activite_par_jour
-- Q7. Saisonnalité hebdomadaire et effet des jours fériés
SELECT
    d.day_name                                                  AS jour,
    d.day_of_week,
    COUNT(DISTINCT d.date_id)                                   AS nb_jours,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT d.date_id), 0)        AS courses_par_jour,
    ROUND(SUM(t.total_amount) / COUNT(DISTINCT d.date_id), 0)   AS ca_par_jour_usd
FROM trips t
JOIN dim_date d ON t.date_id = d.date_id
WHERE NOT d.is_holiday
GROUP BY d.day_name, d.day_of_week
ORDER BY d.day_of_week;

-- name: activite_quotidienne
-- Q7 bis. Série journalière (repérer jours fériés et creux)
SELECT
    d.date,
    d.day_name                                                  AS jour,
    d.is_holiday,
    d.holiday_name,
    COUNT(*)                                                    AS nb_courses,
    ROUND(SUM(t.total_amount), 0)                               AS chiffre_affaires_usd
FROM trips t
JOIN dim_date d ON t.date_id = d.date_id
GROUP BY d.date, d.day_name, d.is_holiday, d.holiday_name
ORDER BY d.date;

-- name: qualite_donnees
-- Q8. Traçabilité : de la donnée brute à la donnée analysée
SELECT step, category, reason, nb_trips, ROUND(100 * pct_of_raw, 2) AS pct_du_brut
FROM data_quality
ORDER BY step_order, nb_trips DESC;
