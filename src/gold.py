"""
Gold : modélise les données Silver en star schema, prêt pour la
consommation analytique (BI, SQL, dashboards).
"""
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from config import get_spark, DATA_SILVER, DATA_GOLD


def run_gold():
    spark = get_spark("gold")
    df = spark.read.parquet(f"{DATA_SILVER}/yellow_tripdata")

    # --- dim_date ------------------------------------------------------
    dim_date = (
        df.select(F.to_date("tpep_pickup_datetime").alias("date"))
        .distinct()
        .withColumn("date_id", F.date_format("date", "yyyyMMdd").cast("int"))
        .withColumn("year", F.year("date"))
        .withColumn("month", F.month("date"))
        .withColumn("day", F.dayofmonth("date"))
        .withColumn("day_of_week", F.dayofweek("date"))
        .withColumn("is_weekend", F.col("day_of_week").isin([1, 7]))
    )
    dim_date.write.mode("overwrite").parquet(f"{DATA_GOLD}/dim_date")

    # --- dim_location ----------------------------------------------------
    dim_location = (
        df.select(
            F.col("PULocationID").alias("location_id"),
            F.col("pickup_borough").alias("borough"),
            F.col("pickup_zone").alias("zone"),
        )
        .distinct()
    )
    dim_location.write.mode("overwrite").parquet(f"{DATA_GOLD}/dim_location")

    # --- dim_payment -------------------------------------------------------
    payment_labels = {1: "Credit card", 2: "Cash", 3: "No charge", 4: "Dispute", 5: "Unknown", 6: "Voided trip"}
    mapping_expr = F.create_map([F.lit(x) for pair in payment_labels.items() for x in pair])
    dim_payment = (
        df.select("payment_type").distinct()
        .withColumn("payment_label", mapping_expr[F.col("payment_type")])
    )
    dim_payment.write.mode("overwrite").parquet(f"{DATA_GOLD}/dim_payment")

    # --- dim_vendor ----------------------------------------------------
    vendor_labels = {1: "Creative Mobile Technologies", 2: "VeriFone Inc", 4: "Unknown / Other TSP"}
    vendor_map = F.create_map([F.lit(x) for pair in vendor_labels.items() for x in pair])
    dim_vendor = (
        df.select("VendorID").distinct()
        .withColumn("vendor_name", vendor_map[F.col("VendorID")])
    )
    dim_vendor.write.mode("overwrite").parquet(f"{DATA_GOLD}/dim_vendor")

    # --- fact_trips ------------------------------------------------------
    fact_trips = df.select(
        F.date_format(F.to_date("tpep_pickup_datetime"), "yyyyMMdd").cast("int").alias("date_id"),
        F.col("PULocationID").alias("pickup_location_id"),
        F.col("DOLocationID").alias("dropoff_location_id"),
        "VendorID",
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
        "congestion_surcharge",
        "pickup_hour",
        "pickup_dow",
    )
    fact_trips.write.mode("overwrite").parquet(f"{DATA_GOLD}/fact_trips")

    print(f"[gold] dim_date      : {dim_date.count():,} lignes")
    print(f"[gold] dim_location  : {dim_location.count():,} lignes")
    print(f"[gold] dim_payment   : {dim_payment.count():,} lignes")
    print(f"[gold] dim_vendor    : {dim_vendor.count():,} lignes")
    print(f"[gold] fact_trips    : {fact_trips.count():,} lignes")

    spark.stop()


if __name__ == "__main__":
    run_gold()
