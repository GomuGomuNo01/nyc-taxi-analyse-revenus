"""
Exécute les requêtes de sql/analyses_metier.sql avec DuckDB, directement sur
les fichiers Parquet de la couche Gold (pas de base de données à installer),
et sauvegarde chaque résultat dans analysis/results/<nom>.csv.

Usage : python analysis/run_queries.py
"""
import os
import re

import duckdb

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLD = os.path.join(ROOT, "data", "gold")
RESULTS = os.path.join(ROOT, "analysis", "results")
SQL_FILE = os.path.join(ROOT, "sql", "analyses_metier.sql")


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for table in ["fact_trips", "dim_date", "dim_hour", "dim_zone", "dim_payment", "dim_vendor", "data_quality"]:
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{GOLD}/{table}/*.parquet')")
    con.execute("CREATE VIEW trips AS SELECT * FROM fact_trips WHERE anomaly_reason IS NULL")
    return con


def load_queries() -> dict:
    """Découpe le fichier SQL en requêtes nommées ("-- name: xxx")."""
    blocks = re.split(r"^-- name: (\w+)\s*$", open(SQL_FILE, encoding="utf-8").read(), flags=re.M)
    return {name: sql.strip().rstrip(";") for name, sql in zip(blocks[1::2], blocks[2::2])}


def run_all() -> dict:
    os.makedirs(RESULTS, exist_ok=True)
    con = connect()
    results = {}
    for name, sql in load_queries().items():
        df = con.execute(sql).df()
        df.to_csv(os.path.join(RESULTS, f"{name}.csv"), index=False)
        results[name] = df
    return results


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 200, "display.max_columns", 20)
    for name, df in run_all().items():
        if name != "demande_heure_jour":
            print(f"\n=== {name} ===\n{df.to_string(index=False)}")
