"""
Configuration Spark et chemins partagés par le pipeline.
"""
from pyspark.sql import SparkSession

DATA_RAW = "data/raw"
DATA_BRONZE = "data/bronze"
DATA_SILVER = "data/silver"
DATA_GOLD = "data/gold"
DATA_AUDIT = "data/audit"


def get_spark(app_name: str = "nyc-taxi-pipeline") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "8")  # petit cluster local -> pas besoin de 200 partitions par défaut
        .getOrCreate()
    )
