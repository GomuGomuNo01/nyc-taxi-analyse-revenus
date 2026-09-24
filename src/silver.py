"""
Silver : nettoie et enrichit les données Bronze.
Principe : les lignes invalides sont mises en quarantaine (silver/rejected),
jamais supprimées silencieusement -> le taux de rejet reste auditable.
"""
from pyspark.sql import functions as F

from business_rules import reject_reason
from config import get_spark, DATA_BRONZE, DATA_SILVER, DATA_RAW


def run_silver():
    spark = get_spark("silver")

    df = spark.read.parquet(f"{DATA_BRONZE}/yellow_tripdata")
    zones = spark.read.csv(f"{DATA_RAW}/taxi_zone_lookup.csv", header=True, inferSchema=True)

    total_in = df.count()

    # --- Règles de validité métier (définies dans business_rules.py) -------
    # Chaque ligne reçoit son motif de rejet : le métier sait ainsi pourquoi
    # une donnée a été écartée, et pas seulement combien.
    df = df.withColumn("reject_reason", reject_reason())

    valid_df = df.filter(F.col("reject_reason").isNull()).drop("reject_reason")
    rejected_df = df.filter(F.col("reject_reason").isNotNull())

    rejected_df.write.mode("overwrite").parquet(f"{DATA_SILVER}/rejected")
    reject_count = rejected_df.count()

    # --- Dédoublonnage -----------------------------------------------------
    before_dedupe = valid_df.count()
    valid_df = valid_df.dropDuplicates(
        ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID"]
    )
    after_dedupe = valid_df.count()

    # --- Champs dérivés -----------------------------------------------------
    valid_df = valid_df.withColumn(
        "trip_duration_minutes",
        (F.col("tpep_dropoff_datetime").cast("long") - F.col("tpep_pickup_datetime").cast("long")) / 60
    )
    valid_df = valid_df.withColumn(
        "avg_speed_mph",
        F.when(F.col("trip_duration_minutes") > 0,
               F.col("trip_distance") / (F.col("trip_duration_minutes") / 60))
         .otherwise(None)
    )
    valid_df = valid_df.withColumn("pickup_hour", F.hour("tpep_pickup_datetime"))
    valid_df = valid_df.withColumn("pickup_dow", F.dayofweek("tpep_pickup_datetime"))

    # --- Enrichissement géographique (broadcast join) -----------------------
    # La dimension zones est petite (265 lignes) et statique -> broadcast
    # plutôt qu'un join classique, pour éviter un shuffle coûteux sur la
    # table des trajets qui est, elle, volumineuse.
    pu_zones = zones.select(
        F.col("LocationID").alias("PULocationID"),
        F.col("Borough").alias("pickup_borough"),
        F.col("Zone").alias("pickup_zone"),
    )
    do_zones = zones.select(
        F.col("LocationID").alias("DOLocationID"),
        F.col("Borough").alias("dropoff_borough"),
        F.col("Zone").alias("dropoff_zone"),
    )

    valid_df = valid_df.join(F.broadcast(pu_zones), on="PULocationID", how="left")
    valid_df = valid_df.join(F.broadcast(do_zones), on="DOLocationID", how="left")

    valid_df.write.mode("overwrite").partitionBy("pickup_year", "pickup_month").parquet(
        f"{DATA_SILVER}/yellow_tripdata"
    )

    print(f"[silver] Entrée bronze     : {total_in:,} lignes")
    print(f"[silver] Rejetées (règles) : {reject_count:,} ({reject_count/total_in:.1%})")
    print(f"[silver] Doublons retirés  : {before_dedupe - after_dedupe:,}")
    print(f"[silver] Sortie silver     : {after_dedupe:,} lignes valides -> {DATA_SILVER}/yellow_tripdata")

    spark.stop()


if __name__ == "__main__":
    run_silver()
