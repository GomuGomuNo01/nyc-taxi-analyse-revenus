"""
Tests unitaires des règles métier (src/business_rules.py), indépendants de la volumétrie.
Ils importent les règles réellement utilisées par le pipeline : modifier une
règle sans mettre à jour les tests fait échouer la suite.
Lancer avec : pytest tests/ -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from business_rules import anomaly_reason, distance_band, reject_reason, time_slot, trip_category

TRIP_COLUMNS = ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count",
                "trip_distance", "fare_amount", "PULocationID", "DOLocationID"]
VALID_TRIP = (1, "2019-01-01 10:00:00", "2019-01-01 10:20:00", 1, 2.5, 12.0, 100, 200)


@pytest.fixture(scope="module")
def spark():
    s = SparkSession.builder.appName("test").master("local[1]").getOrCreate()
    yield s
    s.stop()


def reason_for(spark, **overrides):
    row = dict(zip(TRIP_COLUMNS, VALID_TRIP), **overrides)
    df = spark.createDataFrame([tuple(row.values())], list(row.keys()))
    df = (df.withColumn("tpep_pickup_datetime", F.col("tpep_pickup_datetime").cast("timestamp"))
            .withColumn("tpep_dropoff_datetime", F.col("tpep_dropoff_datetime").cast("timestamp")))
    return df.select(reject_reason().alias("r")).first()["r"]


def test_valid_trip_passes(spark):
    assert reason_for(spark) is None


@pytest.mark.parametrize("overrides, expected", [
    ({"fare_amount": -10.0}, "Tarif nul ou négatif"),
    ({"trip_distance": 0.0}, "Distance nulle ou négative"),
    ({"passenger_count": 0}, "Aucun passager"),
    ({"tpep_dropoff_datetime": "2019-01-01 09:50:00"}, "Dépose avant prise en charge"),
])
def test_invalid_trip_is_rejected_with_reason(spark, overrides, expected):
    assert reason_for(spark, **overrides) == expected


@pytest.mark.parametrize("pu, do, pu_borough, do_borough, expected", [
    (132, 230, "Queens", "Manhattan", "Aéroport"),            # JFK -> Manhattan
    (100, 138, "Manhattan", "Queens", "Aéroport"),            # Manhattan -> LaGuardia
    (100, 230, "Manhattan", "Manhattan", "Intra-Manhattan"),
    (100, 61, "Manhattan", "Brooklyn", "Manhattan <> autres boroughs"),
    (61, 7, "Brooklyn", "Queens", "Hors Manhattan"),
])
def test_trip_category(spark, pu, do, pu_borough, do_borough, expected):
    df = spark.createDataFrame([(pu, do, pu_borough, do_borough)],
                               ["PULocationID", "DOLocationID", "pickup_borough", "dropoff_borough"])
    assert df.select(trip_category().alias("c")).first()["c"] == expected


@pytest.mark.parametrize("distance, expected", [
    (0.5, "1. < 1 mile"), (1.0, "2. 1 à 2 miles"), (3.2, "3. 2 à 5 miles"),
    (7.0, "4. 5 à 10 miles"), (17.0, "5. 10 miles et plus"),
])
def test_distance_band(spark, distance, expected):
    df = spark.createDataFrame([(distance,)], ["trip_distance"])
    assert df.select(distance_band().alias("b")).first()["b"] == expected


@pytest.mark.parametrize("hour, expected", [
    (3, "1. Nuit (0h-6h)"), (8, "2. Pointe du matin (6h-10h)"), (12, "3. Journée (10h-16h)"),
    (18, "4. Pointe du soir (16h-20h)"), (22, "5. Soirée (20h-24h)"),
])
def test_time_slot(spark, hour, expected):
    df = spark.createDataFrame([(hour,)], ["hour"])
    assert df.select(time_slot("hour").alias("s")).first()["s"] == expected


@pytest.mark.parametrize("pickup, speed, duration, total, expected", [
    ("2019-01-15 10:00:00", 12.0, 15.0, 20.0, None),
    ("2018-12-31 23:50:00", 12.0, 15.0, 20.0, "Hors période analysée"),
    ("2019-01-15 10:00:00", 150.0, 15.0, 20.0, "Vitesse aberrante (> 100 mph)"),
    ("2019-01-15 10:00:00", 1.0, 600.0, 20.0, "Durée aberrante (> 3 h)"),
    ("2019-01-15 10:00:00", 0.0, 0.5, 5.0, "Course trop courte (< 1 min)"),
    ("2019-01-15 10:00:00", 12.0, 15.0, 5000.0, "Montant aberrant (> 1 000 $)"),
])
def test_anomaly_reason(spark, pickup, speed, duration, total, expected):
    df = spark.createDataFrame([(pickup, speed, duration, total)],
                               ["tpep_pickup_datetime", "avg_speed_mph", "trip_duration_minutes", "total_amount"])
    df = df.withColumn("tpep_pickup_datetime", F.col("tpep_pickup_datetime").cast("timestamp"))
    assert df.select(anomaly_reason(2019, 1).alias("a")).first()["a"] == expected
