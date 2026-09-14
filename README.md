# 🚕 NYC Taxi Data Engineering Pipeline

Pipeline PySpark en architecture **médaillon** (Bronze → Silver → Gold) sur les données réelles NYC Yellow Taxi (TLC), avec modélisation en star schema, contrôles qualité et traitement incrémental.

## Problème

Les données brutes publiées par la NYC TLC sont volumineuses (plusieurs millions de lignes par mois), contiennent des erreurs de saisie (dates aberrantes, tarifs négatifs, trajets à vitesse impossible) et ne sont pas structurées pour l'analyse. Un pipeline de traitement doit : ingérer sans perte, nettoyer sans supprimer silencieusement, et livrer un modèle exploitable par une équipe BI.

## Données

- **Source** : [NYC TLC Yellow Taxi Trip Records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), janvier 2019 — format et schéma officiels.
- **Volume réel** : 7 663 792 trajets sur le mois complet. Ce repo est testé sur un échantillon de 500 000 lignes pour l'exécution rapide ; **le code tourne sans aucune modification sur le fichier complet** (`sample_fraction=None` dans `bronze.py`).
- **Dimension géographique** : `taxi_zone_lookup.csv` (265 zones officielles TLC).

## Architecture

```
CSV brut (TLC)
   │
   ▼
BRONZE   Ingestion telle quelle, typage, partitionnement par année/mois,
         audit incrémental (etl_audit)
   │
   ▼
SILVER   Règles de validité métier, rejets audités (pas de suppression
         silencieuse), dédoublonnage, champs dérivés, enrichissement
         géographique (broadcast join)
   │
   ▼
GOLD     Star schema : fact_trips + dim_date / dim_location / dim_payment /
         dim_vendor, prêt pour la consommation SQL/BI
```

## Décisions techniques (ce qui vaut la peine d'être expliqué en entretien)

- **Broadcast join pour la dimension zones** : 265 lignes vs. des millions de trajets — un join classique déclencherait un shuffle coûteux pour rien. `F.broadcast()` envoie la petite table à chaque exécuteur.
- **Rejets, pas suppressions** : les lignes qui échouent aux règles de validité (tarif négatif, distance nulle, dropoff avant pickup...) sont écrites dans `silver/rejected`, pas jetées. Le taux de rejet devient une métrique auditable (2,3% sur l'échantillon testé).
- **Traitement incrémental** : un fichier déjà marqué `SUCCESS` dans `data/audit/etl_audit` est skippé au prochain run, sauf `force=True`. Re-traiter un mois déjà chargé est un no-op.
- **Fail-fast** : si Bronze lève une exception, elle remonte et Silver/Gold ne s'exécutent jamais sur un batch à moitié chargé.
- **Anomalies documentées, pas cachées** : le contrôle qualité (`validation.py`) a détecté 355 trajets (0,07%) avec un timestamp hors du mois nominal (jusqu'à 2008) — une vraie erreur de saisie présente dans les données officielles TLC. Ces lignes passent les règles de validité de base mais sont signalées séparément plutôt que silencieusement ignorées ou arbitrairement supprimées.

## Résultats obtenus sur l'échantillon (500k lignes)

| Étape | Résultat |
|---|---|
| Bronze | 500 000 lignes ingérées, partitionnées par année/mois |
| Silver | 11 371 lignes rejetées (2,3%) — tarifs/distances invalides, dropoff < pickup |
| Silver | 2 doublons détectés et retirés |
| Silver → Gold | 488 627 trajets valides modélisés en star schema |
| Contrôle qualité | 355 trajets (0,07%) hors période nominale, 360 (0,07%) à vitesse aberrante |

Exemple de requête analytique (répartition du CA par borough) :

| Borough | Trajets | CA |
|---|---|---|
| Manhattan | 430 830 | 5 834 261 € |
| Queens | 40 559 | 1 795 660 € |
| Brooklyn | 7 919 | 165 194 € |

## Structure du repo

```
taxi-project/
├── src/
│   ├── config.py         # Config Spark partagée
│   ├── bronze.py         # Ingestion + audit incrémental
│   ├── silver.py         # Nettoyage, rejets, enrichissement
│   ├── gold.py           # Star schema
│   └── validation.py     # Contrôles qualité post-Silver
├── sql/
│   └── analytical_queries.sql   # 5 requêtes testées sur le star schema
├── tests/
│   └── test_silver_rules.py     # Tests unitaires des règles métier
├── data/
│   ├── raw/               # CSV bruts (non versionnés, voir .gitignore)
│   ├── bronze/ silver/ gold/ audit/   # Générés par le pipeline
└── requirements.txt
```

## Lancer le projet

```bash
pip install -r requirements.txt

# 1. Récupérer les données réelles (voir section Données ci-dessous)
# 2. Lancer le pipeline dans l'ordre :
python src/bronze.py yellow_tripdata_2019-01.csv
python src/silver.py
python src/gold.py
python src/validation.py

# Tests unitaires (ne nécessitent pas les données téléchargées)
pytest tests/ -v
```

### Récupérer le dataset complet

```bash
# Mois complet (2019-01), format officiel TLC, ~130 Mo compressé
curl -L -o data/raw/yellow_tripdata_2019-01.csv.gz \
  https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2019-01.csv.gz
gunzip data/raw/yellow_tripdata_2019-01.csv.gz

curl -L -o data/raw/taxi_zone_lookup.csv \
  https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv
```

Pour traiter le fichier complet plutôt qu'un échantillon, appeler `run_bronze()` sans `sample_fraction`, ou directement en ligne de commande : `python src/bronze.py yellow_tripdata_2019-01.csv` (l'échantillonnage n'est utilisé que si un deuxième argument est passé).

## Pistes d'amélioration

- Orchestration avec Airflow (DAG bronze → silver → gold → validation avec dépendances explicites)
- Chargement Gold dans Postgres ou DuckDB pour connecter un dashboard Power BI/Streamlit
- Dockeriser le pipeline pour une exécution reproductible
- Étendre à plusieurs mois pour analyser les tendances saisonnières

## Auteur

Cedric — Mastère IA & Big Data, ESGI Paris
