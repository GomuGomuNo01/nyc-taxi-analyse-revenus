"""
Contrôles qualité de bout en bout. Ne bloque pas le pipeline (les règles dures
sont déjà appliquées dans silver.py) : il mesure ce qui a été écarté à chaque
étape et pourquoi, et écrit ces métriques dans gold/data_quality pour qu'elles
soient visibles dans le dashboard (un chiffre n'est crédible que si l'on sait
sur quelles données il repose).
"""
from pyspark.sql import functions as F

from config import get_spark, DATA_BRONZE, DATA_SILVER, DATA_GOLD


def run_validation():
    spark = get_spark("validation")

    bronze = spark.read.parquet(f"{DATA_BRONZE}/yellow_tripdata").count()
    rejected = spark.read.parquet(f"{DATA_SILVER}/rejected")
    silver = spark.read.parquet(f"{DATA_SILVER}/yellow_tripdata").count()
    fact = spark.read.parquet(f"{DATA_GOLD}/fact_trips")

    rejected_count = rejected.count()
    duplicates = bronze - rejected_count - silver
    analysed = fact.filter(F.col("anomaly_reason").isNull()).count()

    # (ordre, étape, catégorie, motif, nombre de courses)
    rows = [(1, "1. Ingestion (Bronze)", "Entrée", "Courses brutes ingérées", bronze)]
    for r in rejected.groupBy("reject_reason").count().orderBy(F.desc("count")).collect():
        rows.append((2, "2. Nettoyage (Silver)", "Rejet", r["reject_reason"], r["count"]))
    rows.append((2, "2. Nettoyage (Silver)", "Rejet", "Doublon", duplicates))
    for r in (fact.filter(F.col("anomaly_reason").isNotNull())
              .groupBy("anomaly_reason").count().orderBy(F.desc("count")).collect()):
        rows.append((3, "3. Contrôle qualité (Gold)", "Anomalie", r["anomaly_reason"], r["count"]))
    rows.append((4, "4. Analyse", "Sortie", "Courses retenues pour l'analyse", analysed))

    quality = spark.createDataFrame(rows, ["step_order", "step", "category", "reason", "nb_trips"])
    quality = quality.withColumn("pct_of_raw", F.round(F.col("nb_trips") / F.lit(bronze), 6))
    quality.write.mode("overwrite").parquet(f"{DATA_GOLD}/data_quality")

    print("=== Rapport qualité ===")
    for step_order, step, category, reason, nb in rows:
        print(f"{step:<28} {category:<9} {reason:<40} {nb:>10,} ({nb / bronze:.2%})")

    spark.stop()


if __name__ == "__main__":
    run_validation()
