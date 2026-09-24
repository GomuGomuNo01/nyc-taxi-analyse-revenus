"""
Export BI : prépare les tables consommées par Power BI (dossier powerbi/data).

Pourquoi une table agrégée plutôt que les 7,4 M de courses ?
- Power BI reste fluide et le fichier .pbix reste léger ;
- les fichiers tiennent sous la limite GitHub (100 Mo), le dashboard est
  donc reproductible sans relancer Spark ;
- aucune perte d'exactitude : on ne stocke que des sommes et des comptages,
  les ratios (panier moyen, revenu par minute, taux de pourboire) sont
  recalculés dans Power BI comme SUM(a) / SUM(b).

Format Parquet : typé (pas de problème de séparateur décimal entre un
Power BI en français et des données US) et compressé.
"""
import glob
import os
import shutil

from pyspark.sql import functions as F

from config import get_spark, DATA_GOLD, POWERBI_DATA, PROJECT_ROOT

GRAIN = ["date_id", "hour", "pickup_location_id", "payment_type", "trip_category", "distance_band"]
DIMENSIONS = ["dim_date", "dim_hour", "dim_zone", "dim_payment", "data_quality"]


def write_single_parquet(df, name: str):
    """Spark écrit un dossier de fichiers part-*.parquet : on le réduit à un seul fichier nommé."""
    tmp_dir = os.path.join(POWERBI_DATA, f"_{name}_tmp")
    df.coalesce(1).write.mode("overwrite").option("compression", "snappy").parquet(tmp_dir)
    part_file = glob.glob(os.path.join(tmp_dir, "part-*.parquet"))[0]
    target = os.path.join(POWERBI_DATA, f"{name}.parquet")
    shutil.move(part_file, target)
    shutil.rmtree(tmp_dir)
    print(f"[export] {name:<16}: {df.count():>9,} lignes -> {os.path.relpath(target, PROJECT_ROOT)} "
          f"({os.path.getsize(target) / 1e6:.1f} Mo)")


def build_fact_trips_agg(fact):
    return (
        fact.filter(F.col("anomaly_reason").isNull())
        .groupBy(*GRAIN)
        .agg(
            F.count("*").alias("nb_trips"),
            F.sum("passenger_count").alias("nb_passengers"),
            F.round(F.sum("trip_distance"), 2).alias("distance_miles"),
            F.round(F.sum("trip_duration_minutes"), 2).alias("duration_minutes"),
            F.round(F.sum("fare_amount"), 2).alias("fare_amount"),
            F.round(F.sum("tip_amount"), 2).alias("tip_amount"),
            F.round(F.sum("tolls_amount"), 2).alias("tolls_amount"),
            F.round(F.sum(F.col("extra") + F.col("mta_tax") + F.col("improvement_surcharge")), 2)
             .alias("surcharges_amount"),
            F.round(F.sum("total_amount"), 2).alias("total_amount"),
        )
        .orderBy(*GRAIN)
    )


def run_export():
    spark = get_spark("export_powerbi")
    os.makedirs(POWERBI_DATA, exist_ok=True)

    fact = spark.read.parquet(f"{DATA_GOLD}/fact_trips")
    write_single_parquet(build_fact_trips_agg(fact), "fact_trips_agg")
    for name in DIMENSIONS:
        write_single_parquet(spark.read.parquet(f"{DATA_GOLD}/{name}"), name)

    spark.stop()


if __name__ == "__main__":
    run_export()
