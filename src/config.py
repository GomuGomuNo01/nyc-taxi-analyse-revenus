"""
Configuration Spark et chemins partagés par le pipeline.
"""
import os

from pyspark.sql import SparkSession

# Chemins calculés depuis la racine du projet : les scripts fonctionnent
# quel que soit le dossier depuis lequel on les lance.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_BRONZE = os.path.join(PROJECT_ROOT, "data", "bronze")
DATA_SILVER = os.path.join(PROJECT_ROOT, "data", "silver")
DATA_GOLD = os.path.join(PROJECT_ROOT, "data", "gold")
DATA_AUDIT = os.path.join(PROJECT_ROOT, "data", "audit")
POWERBI_DATA = os.path.join(PROJECT_ROOT, "powerbi", "data")

# Période analysée (fichier TLC de janvier 2019)
EXPECTED_YEAR = 2019
EXPECTED_MONTH = 1


def get_spark(app_name: str = "nyc-taxi-pipeline") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")  # petit cluster local -> pas besoin de 200 partitions par défaut
        .getOrCreate()
    )
