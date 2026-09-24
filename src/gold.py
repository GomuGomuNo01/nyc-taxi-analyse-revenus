"""
Gold : modélise les données Silver en star schema orienté métier, prêt pour
la consommation analytique (SQL, Power BI).

Apports par rapport à Silver :
- dimensions complètes et lisibles (calendrier en français, 265 zones, créneaux horaires) ;
- segmentation métier de chaque course (type de trajet, tranche de distance) ;
- anomalies résiduelles signalées par une colonne, pour être exclues des KPI
  sans être supprimées.
"""
import calendar
from datetime import date

from pyspark.sql import functions as F

from business_rules import AIRPORT_ZONE_IDS, anomaly_reason, distance_band, time_slot, trip_category
from config import get_spark, DATA_RAW, DATA_SILVER, DATA_GOLD, EXPECTED_YEAR, EXPECTED_MONTH

DAY_NAMES = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
# Jours fériés fédéraux US de la période analysée (la demande y est atypique)
US_HOLIDAYS = {date(2019, 1, 1): "New Year's Day", date(2019, 1, 21): "Martin Luther King Jr. Day"}
PAYMENT_LABELS = {1: "Carte bancaire", 2: "Espèces", 3: "Gratuit", 4: "Litige", 5: "Inconnu", 6: "Course annulée"}
VENDOR_LABELS = {1: "Creative Mobile Technologies", 2: "VeriFone Inc", 4: "Autre fournisseur"}


def build_dim_date(spark, year: int, month: int):
    """Calendrier complet du mois (et pas seulement les jours présents dans les données)."""
    rows = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        rows.append((
            int(d.strftime("%Y%m%d")), d, d.year, d.month, d.day,
            d.isoweekday(), DAY_NAMES[d.weekday()], d.isoweekday() >= 6,
            d in US_HOLIDAYS, US_HOLIDAYS.get(d), d.isocalendar()[1],
        ))
    return spark.createDataFrame(rows, [
        "date_id", "date", "year", "month", "day",
        "day_of_week", "day_name", "is_weekend",
        "is_holiday", "holiday_name", "iso_week",
    ])


def build_dim_hour(spark):
    return (
        spark.range(24).select(F.col("id").cast("int").alias("hour"))
        .withColumn("hour_label", F.format_string("%02dh", F.col("hour")))
        .withColumn("time_slot", time_slot("hour"))
    )


def build_dim_zone(spark):
    """Les 265 zones officielles TLC (prise en charge ET dépose)."""
    zones = spark.read.csv(f"{DATA_RAW}/taxi_zone_lookup.csv", header=True, inferSchema=True)
    return zones.select(
        F.col("LocationID").cast("int").alias("location_id"),
        F.col("Borough").alias("borough"),
        F.col("Zone").alias("zone"),
        F.col("service_zone"),
        F.col("LocationID").isin(AIRPORT_ZONE_IDS).alias("is_airport"),
    )


def build_label_dim(spark, labels: dict, id_col: str, label_col: str):
    return spark.createDataFrame(list(labels.items()), [id_col, label_col])


def build_fact_trips(df):
    df = (
        df.withColumn("trip_category", trip_category())
        .withColumn("distance_band", distance_band())
        .withColumn("anomaly_reason", anomaly_reason(EXPECTED_YEAR, EXPECTED_MONTH))
    )
    return df.select(
        F.date_format("tpep_pickup_datetime", "yyyyMMdd").cast("int").alias("date_id"),
        F.col("pickup_hour").alias("hour"),
        F.col("tpep_pickup_datetime").alias("pickup_datetime"),
        F.col("tpep_dropoff_datetime").alias("dropoff_datetime"),
        F.col("PULocationID").alias("pickup_location_id"),
        F.col("DOLocationID").alias("dropoff_location_id"),
        F.col("VendorID").alias("vendor_id"),
        "payment_type",
        "passenger_count",
        "trip_distance",
        "trip_duration_minutes",
        "avg_speed_mph",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "trip_category",
        "distance_band",
        "anomaly_reason",
    )


def run_gold():
    spark = get_spark("gold")
    silver = spark.read.parquet(f"{DATA_SILVER}/yellow_tripdata")

    tables = {
        "dim_date": build_dim_date(spark, EXPECTED_YEAR, EXPECTED_MONTH),
        "dim_hour": build_dim_hour(spark),
        "dim_zone": build_dim_zone(spark),
        "dim_payment": build_label_dim(spark, PAYMENT_LABELS, "payment_type", "payment_label"),
        "dim_vendor": build_label_dim(spark, VENDOR_LABELS, "vendor_id", "vendor_name"),
        "fact_trips": build_fact_trips(silver),
    }

    for name, table in tables.items():
        table.write.mode("overwrite").parquet(f"{DATA_GOLD}/{name}")
        print(f"[gold] {name:<12}: {spark.read.parquet(f'{DATA_GOLD}/{name}').count():,} lignes")

    spark.stop()


if __name__ == "__main__":
    run_gold()
