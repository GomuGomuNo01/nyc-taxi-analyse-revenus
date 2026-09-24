"""
Règles métier centralisées.

Toutes les règles (validité d'une course, segmentation métier) sont définies
ici une seule fois, puis réutilisées par silver.py, gold.py et les tests.
Une règle modifiée ici est donc automatiquement appliquée et testée partout.
"""
from pyspark.sql import Column
from pyspark.sql import functions as F

# Zones TLC des aéroports : Newark (1), JFK (132), LaGuardia (138)
AIRPORT_ZONE_IDS = [1, 132, 138]
MANHATTAN = "Manhattan"

# Seuils d'anomalies : la course passe les règles de validité mais reste
# suspecte. Elle est conservée dans Silver et exclue des analyses Gold.
MAX_SPEED_MPH = 100
MAX_DURATION_MIN = 180
MIN_DURATION_MIN = 1
MAX_TOTAL_AMOUNT = 1000  # la course légitime la plus chère observée (~130 miles) coûte ~600 $


# --- Validité d'une course (Silver) ---------------------------------------

def reject_reason() -> Column:
    """Premier motif de rejet rencontré, ou NULL si la course est valide."""
    return (
        F.when(F.col("PULocationID").isNull() | F.col("DOLocationID").isNull(), "Zone manquante")
        .when(F.col("tpep_pickup_datetime").isNull() | F.col("tpep_dropoff_datetime").isNull(), "Horodatage manquant")
        .when(F.col("tpep_dropoff_datetime") <= F.col("tpep_pickup_datetime"), "Dépose avant prise en charge")
        .when(F.col("trip_distance").isNull() | (F.col("trip_distance") <= 0), "Distance nulle ou négative")
        .when(F.col("fare_amount").isNull() | (F.col("fare_amount") <= 0), "Tarif nul ou négatif")
        .when(F.col("passenger_count").isNull() | (F.col("passenger_count") <= 0), "Aucun passager")
    )


def is_valid() -> Column:
    return reject_reason().isNull()


# --- Segmentation métier (Gold) -------------------------------------------

def trip_category() -> Column:
    """Type de course, du point de vue de l'exploitant."""
    is_airport = F.col("PULocationID").isin(AIRPORT_ZONE_IDS) | F.col("DOLocationID").isin(AIRPORT_ZONE_IDS)
    pu_manhattan = F.col("pickup_borough") == MANHATTAN
    do_manhattan = F.col("dropoff_borough") == MANHATTAN
    return (
        F.when(is_airport, "Aéroport")
        .when(pu_manhattan & do_manhattan, "Intra-Manhattan")
        .when(pu_manhattan | do_manhattan, "Manhattan <> autres boroughs")
        .otherwise("Hors Manhattan")
    )


def distance_band() -> Column:
    d = F.col("trip_distance")
    return (
        F.when(d < 1, "1. < 1 mile")
        .when(d < 2, "2. 1 à 2 miles")
        .when(d < 5, "3. 2 à 5 miles")
        .when(d < 10, "4. 5 à 10 miles")
        .otherwise("5. 10 miles et plus")
    )


def time_slot(hour_col: str = "hour") -> Column:
    h = F.col(hour_col)
    return (
        F.when(h < 6, "1. Nuit (0h-6h)")
        .when(h < 10, "2. Pointe du matin (6h-10h)")
        .when(h < 16, "3. Journée (10h-16h)")
        .when(h < 20, "4. Pointe du soir (16h-20h)")
        .otherwise("5. Soirée (20h-24h)")
    )


def anomaly_reason(expected_year: int, expected_month: int) -> Column:
    """Anomalie résiduelle détectée après Silver, ou NULL si la course est exploitable."""
    return (
        F.when((F.year("tpep_pickup_datetime") != expected_year) |
               (F.month("tpep_pickup_datetime") != expected_month), "Hors période analysée")
        .when(F.col("total_amount") > MAX_TOTAL_AMOUNT, "Montant aberrant (> 1 000 $)")
        .when(F.col("avg_speed_mph") > MAX_SPEED_MPH, "Vitesse aberrante (> 100 mph)")
        .when(F.col("trip_duration_minutes") > MAX_DURATION_MIN, "Durée aberrante (> 3 h)")
        .when(F.col("trip_duration_minutes") < MIN_DURATION_MIN, "Course trop courte (< 1 min)")
    )
