-- Requêtes analytiques sur le star schema Gold
-- (à exécuter via Spark SQL, DuckDB, ou après chargement dans Postgres)

-- 1. Chiffre d'affaires et nombre de trajets par borough de prise en charge
SELECT
    l.borough,
    COUNT(*) AS nb_trips,
    ROUND(SUM(f.total_amount), 2) AS revenue,
    ROUND(AVG(f.trip_distance), 2) AS avg_distance_miles,
    ROUND(AVG(f.tip_amount / NULLIF(f.fare_amount, 0)) * 100, 1) AS avg_tip_pct
FROM fact_trips f
JOIN dim_location l ON f.pickup_location_id = l.location_id
GROUP BY l.borough
ORDER BY revenue DESC;

-- 2. Répartition horaire de la demande (identifier les heures de pointe)
SELECT
    pickup_hour,
    COUNT(*) AS nb_trips,
    ROUND(AVG(avg_speed_mph), 1) AS avg_speed_mph,
    ROUND(AVG(trip_duration_minutes), 1) AS avg_duration_min
FROM fact_trips
GROUP BY pickup_hour
ORDER BY pickup_hour;

-- 3. Top 10 des zones de prise en charge les plus rentables
SELECT
    l.zone,
    l.borough,
    COUNT(*) AS nb_trips,
    ROUND(SUM(f.total_amount), 2) AS revenue,
    ROUND(SUM(f.total_amount) / COUNT(*), 2) AS revenue_per_trip
FROM fact_trips f
JOIN dim_location l ON f.pickup_location_id = l.location_id
GROUP BY l.zone, l.borough
ORDER BY revenue DESC
LIMIT 10;

-- 4. Mode de paiement : répartition et générosité des pourboires
SELECT
    p.payment_label,
    COUNT(*) AS nb_trips,
    ROUND(AVG(f.tip_amount), 2) AS avg_tip,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_trips
FROM fact_trips f
JOIN dim_payment p ON f.payment_type = p.payment_type
GROUP BY p.payment_label
ORDER BY nb_trips DESC;

-- 5. Week-end vs semaine : volume et durée moyenne
SELECT
    d.is_weekend,
    COUNT(*) AS nb_trips,
    ROUND(AVG(f.trip_duration_minutes), 1) AS avg_duration_min,
    ROUND(AVG(f.total_amount), 2) AS avg_fare
FROM fact_trips f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.is_weekend;
