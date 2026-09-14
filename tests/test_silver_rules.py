"""
Tests unitaires sur la logique de nettoyage Silver, indépendants de la volumétrie.
Lancer avec : pytest tests/test_silver_rules.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


@pytest.fixture(scope="module")
def spark():
    s = SparkSession.builder.appName("test").master("local[1]").getOrCreate()
    yield s
    s.stop()


def test_negative_fare_is_rejected(spark):
    df = spark.createDataFrame(
        [(1, "2019-01-01 10:00:00", "2019-01-01 10:20:00", 1, 2.5, -10.0, 100, 200)],
        ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count",
         "trip_distance", "fare_amount", "PULocationID", "DOLocationID"],
    )
    valid = (
        (F.col("trip_distance") > 0) &
        (F.col("fare_amount") > 0) &
        (F.col("passenger_count") > 0)
    )
    result = df.filter(valid).count()
    assert result == 0, "Une course à tarif négatif doit être rejetée"


def test_dropoff_before_pickup_is_rejected(spark):
    df = spark.createDataFrame(
        [(1, "2019-01-01 10:20:00", "2019-01-01 10:00:00")],  # dropoff avant pickup
        ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime"],
    )
    df = df.withColumn("tpep_pickup_datetime", F.col("tpep_pickup_datetime").cast("timestamp"))
    df = df.withColumn("tpep_dropoff_datetime", F.col("tpep_dropoff_datetime").cast("timestamp"))
    valid = F.col("tpep_dropoff_datetime") > F.col("tpep_pickup_datetime")
    result = df.filter(valid).count()
    assert result == 0, "Un trajet dont le dropoff précède le pickup doit être rejeté"


def test_valid_trip_passes(spark):
    df = spark.createDataFrame(
        [(1, "2019-01-01 10:00:00", "2019-01-01 10:20:00", 1, 2.5, 12.0, 100, 200)],
        ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count",
         "trip_distance", "fare_amount", "PULocationID", "DOLocationID"],
    )
    valid = (
        (F.col("trip_distance") > 0) &
        (F.col("fare_amount") > 0) &
        (F.col("passenger_count") > 0)
    )
    result = df.filter(valid).count()
    assert result == 1, "Un trajet valide ne doit pas être rejeté"
