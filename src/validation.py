"""
Contrôles qualité post-Silver. Ne bloque pas le pipeline (les règles dures
sont déjà appliquées dans silver.py) — sert à détecter et documenter les
anomalies résiduelles qui passent les règles de validité de base mais
restent suspectes (ex : dates hors de la période nominale du fichier).
"""
from pyspark.sql import functions as F

from config import get_spark, DATA_SILVER


def run_validation(expected_year: int, expected_month: int):
    spark = get_spark("validation")
    df = spark.read.parquet(f"{DATA_SILVER}/yellow_tripdata")

    total = df.count()

    # Anomalie connue et documentée du dataset TLC : certains trajets portent
    # un timestamp hors du mois nominal du fichier (erreurs de saisie côté
    # taximètre). On ne les supprime pas silencieusement, on les compte.
    out_of_range = df.filter(
        (F.col("pickup_year") != expected_year) | (F.col("pickup_month") != expected_month)
    ).count()

    negative_speed_or_outlier = df.filter(
        (F.col("avg_speed_mph") > 100) | (F.col("avg_speed_mph") < 0)
    ).count()

    long_trips = df.filter(F.col("trip_duration_minutes") > 180).count()

    print("=== Rapport qualité (post-Silver) ===")
    print(f"Total lignes                          : {total:,}")
    print(f"Hors période nominale ({expected_year}-{expected_month:02d}) : {out_of_range:,} ({out_of_range/total:.2%})")
    print(f"Vitesse moyenne aberrante (>100mph)    : {negative_speed_or_outlier:,} ({negative_speed_or_outlier/total:.2%})")
    print(f"Trajets > 3h                           : {long_trips:,} ({long_trips/total:.2%})")
    print("\n-> Ces lignes restent dans le dataset (elles passent les règles de")
    print("   validité métier de base) mais sont signalées ici pour qu'une équipe")
    print("   business décide d'un seuil de filtrage adapté à son cas d'usage.")

    spark.stop()


if __name__ == "__main__":
    run_validation(expected_year=2019, expected_month=1)
