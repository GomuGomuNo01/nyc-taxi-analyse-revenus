"""
Orchestrateur : exécute le pipeline complet dans l'ordre, en une commande.
Chaque étape lève une exception en cas d'échec (fail-fast) : une étape ne
tourne jamais sur le résultat incomplet de la précédente.

Usage : python src/pipeline.py [fichier_source] [sample_fraction]
"""
import sys

from bronze import run_bronze
from export_powerbi import run_export
from gold import run_gold
from silver import run_silver
from validation import run_validation

if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "yellow_tripdata_2019-01.csv"
    frac = float(sys.argv[2]) if len(sys.argv) > 2 else None

    run_bronze(source, sample_fraction=frac)
    run_silver()
    run_gold()
    run_validation()
    run_export()
