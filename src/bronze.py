"""
Bronze : ingère le CSV brut tel quel (typage minimal), partitionne par
année/mois, et journalise l'opération dans un audit pour permettre un
traitement incrémental (ré-exécuter sur un mois déjà chargé est un no-op
sauf si on force).
"""
import sys
import os
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, IntegerType, DoubleType, StringType, TimestampType
)

from config import get_spark, DATA_RAW, DATA_BRONZE, DATA_AUDIT

SCHEMA = StructType([
    StructField("VendorID", IntegerType(), True),
    StructField("tpep_pickup_datetime", TimestampType(), True),
    StructField("tpep_dropoff_datetime", TimestampType(), True),
    StructField("passenger_count", IntegerType(), True),
    StructField("trip_distance", DoubleType(), True),
    StructField("RatecodeID", IntegerType(), True),
    StructField("store_and_fwd_flag", StringType(), True),
    StructField("PULocationID", IntegerType(), True),
    StructField("DOLocationID", IntegerType(), True),
    StructField("payment_type", IntegerType(), True),
    StructField("fare_amount", DoubleType(), True),
    StructField("extra", DoubleType(), True),
    StructField("mta_tax", DoubleType(), True),
    StructField("tip_amount", DoubleType(), True),
    StructField("tolls_amount", DoubleType(), True),
    StructField("improvement_surcharge", DoubleType(), True),
    StructField("total_amount", DoubleType(), True),
    StructField("congestion_surcharge", DoubleType(), True),
])


def already_processed(spark, source_file: str) -> bool:
    audit_path = f"{DATA_AUDIT}/etl_audit"
    if not os.path.exists(audit_path):
        return False
    audit_df = spark.read.parquet(audit_path)
    return audit_df.filter(
        (F.col("source_file") == source_file) & (F.col("status") == "SUCCESS")
    ).count() > 0


def write_audit(spark, source_file: str, status: str, row_count: int):
    audit_path = f"{DATA_AUDIT}/etl_audit"
    record = spark.createDataFrame(
        [(source_file, status, row_count, datetime.now(timezone.utc).isoformat())],
        ["source_file", "status", "row_count", "processed_at"],
    )
    if os.path.exists(audit_path):
        record.write.mode("append").parquet(audit_path)
    else:
        record.write.mode("overwrite").parquet(audit_path)


def run_bronze(source_file: str, sample_fraction: float = None, force: bool = False):
    spark = get_spark("bronze")

    if not force and already_processed(spark, source_file):
        print(f"[bronze] {source_file} déjà chargé avec succès -> skip (incrémental)")
        spark.stop()
        return

    input_path = f"{DATA_RAW}/{source_file}"
    try:
        df = spark.read.csv(input_path, header=True, schema=SCHEMA)

        # Un échantillon volontaire pour ce run de démonstration : le pipeline
        # est écrit pour tourner tel quel sur le fichier complet (7,6M lignes),
        # sample_fraction=None traite tout.
        if sample_fraction:
            df = df.sample(fraction=sample_fraction, seed=42)

        df = df.withColumn("pickup_year", F.year("tpep_pickup_datetime"))
        df = df.withColumn("pickup_month", F.month("tpep_pickup_datetime"))
        df = df.withColumn("_ingested_at", F.current_timestamp())
        df = df.withColumn("_source_file", F.lit(source_file))

        row_count = df.count()

        (
            df.write
            .mode("overwrite")
            .partitionBy("pickup_year", "pickup_month")
            .parquet(f"{DATA_BRONZE}/yellow_tripdata")
        )

        write_audit(spark, source_file, "SUCCESS", row_count)
        print(f"[bronze] {source_file} -> {row_count:,} lignes écrites dans {DATA_BRONZE}/yellow_tripdata")

    except Exception as e:
        write_audit(spark, source_file, "FAILED", 0)
        spark.stop()
        raise e  # fail-fast : silver/gold ne doivent jamais tourner sur un batch à moitié chargé

    spark.stop()


if __name__ == "__main__":
    # Usage : python src/bronze.py yellow_tripdata_2019-01.csv [sample_fraction]
    source = sys.argv[1] if len(sys.argv) > 1 else "yellow_tripdata_2019-01.csv"
    frac = float(sys.argv[2]) if len(sys.argv) > 2 else None
    run_bronze(source, sample_fraction=frac)
