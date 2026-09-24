"""
Génère le projet Power BI (format PBIP : modèle sémantique TMDL + rapport PBIR).

Le format PBIP décrit un rapport Power BI sous forme de fichiers texte :
il est versionnable dans Git (chaque modification est lisible dans un diff)
et peut être généré par code. Power BI Desktop l'ouvre comme un .pbix.

Tout est défini ici une seule fois (tables, relations, mesures, pages,
visuels) : une mesure utilisée par un visuel existe forcément dans le modèle.

Usage : python powerbi/generer_pbip.py
Sorties : powerbi/NYC_Taxi_Dashboard.pbip (+ dossiers .SemanticModel et .Report)
          powerbi/mesures_dax.dax (référence lisible des mesures)
"""
import hashlib
import json
import os
import shutil
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "NYC_Taxi_Dashboard"
MODEL_DIR = os.path.join(HERE, f"{NAME}.SemanticModel")
REPORT_DIR = os.path.join(HERE, f"{NAME}.Report")
SCHEMAS = "https://developer.microsoft.com/json-schemas/fabric"
DEFAULT_DATA_PATH = "C:\\A_REMPLACER\\nyc-taxi-data-engineering\\powerbi\\data\\"

# =====================================================================
# 1. MODÈLE SÉMANTIQUE
# =====================================================================
# (nom dans le modèle, colonne source Parquet, type TMDL, options)
# Options séparées par ";" : hidden, key, sort=<colonne de tri>, fmt=<format>
TABLES = {
    "fact_trips_agg": [
        ("date_id", "date_id", "int64", "hidden"),
        ("hour", "hour", "int64", "hidden"),
        ("pickup_location_id", "pickup_location_id", "int64", "hidden"),
        ("payment_type", "payment_type", "int64", "hidden"),
        ("Type de course", "trip_category", "string", ""),
        ("Tranche de distance", "distance_band", "string", ""),
        ("nb_trips", "nb_trips", "int64", "hidden"),
        ("nb_passengers", "nb_passengers", "int64", "hidden"),
        ("distance_miles", "distance_miles", "double", "hidden"),
        ("duration_minutes", "duration_minutes", "double", "hidden"),
        ("fare_amount", "fare_amount", "double", "hidden"),
        ("tip_amount", "tip_amount", "double", "hidden"),
        ("tolls_amount", "tolls_amount", "double", "hidden"),
        ("surcharges_amount", "surcharges_amount", "double", "hidden"),
        ("total_amount", "total_amount", "double", "hidden"),
    ],
    "dim_date": [
        ("date_id", "date_id", "int64", "hidden"),
        ("Date", "date", "dateTime", "key;fmt=dd/mm/yyyy"),
        ("Année", "year", "int64", "hidden"),
        ("Mois", "month", "int64", "hidden"),
        ("Jour du mois", "day", "int64", ""),
        ("N° jour semaine", "day_of_week", "int64", "hidden"),
        ("Jour", "day_name", "string", "sort=N° jour semaine"),
        ("Week-end", "is_weekend", "boolean", ""),
        ("Jour férié", "is_holiday", "boolean", ""),
        ("Nom du jour férié", "holiday_name", "string", ""),
        ("Semaine", "iso_week", "int64", ""),
    ],
    "dim_hour": [
        ("N° heure", "hour", "int64", "hidden"),
        ("Heure", "hour_label", "string", "sort=N° heure"),
        ("Créneau", "time_slot", "string", ""),
    ],
    "dim_zone": [
        ("ID zone", "location_id", "int64", "hidden"),
        ("Borough", "borough", "string", ""),
        ("Zone", "zone", "string", ""),
        ("Type de zone", "service_zone", "string", ""),
        ("Aéroport", "is_airport", "boolean", ""),
    ],
    "dim_payment": [
        ("ID paiement", "payment_type", "int64", "hidden"),
        ("Mode de paiement", "payment_label", "string", ""),
    ],
    "data_quality": [
        ("Ordre", "step_order", "int64", "hidden"),
        ("Étape", "step", "string", ""),
        ("Catégorie", "category", "string", ""),
        ("Motif", "reason", "string", ""),
        ("Nb courses", "nb_trips", "int64", "fmt=#,0"),
        ("Part du brut", "pct_of_raw", "double", "fmt=0.00 %"),
    ],
}
DATE_TABLE = "dim_date"

# (table de faits, colonne) -> (dimension, colonne) : relations plusieurs-à-un, filtre unidirectionnel
RELATIONSHIPS = [
    (("fact_trips_agg", "date_id"), ("dim_date", "date_id")),
    (("fact_trips_agg", "hour"), ("dim_hour", "N° heure")),
    (("fact_trips_agg", "pickup_location_id"), ("dim_zone", "ID zone")),
    (("fact_trips_agg", "payment_type"), ("dim_payment", "ID paiement")),
]

FMT_INT = "#,0"
FMT_USD0 = "$#,0"
FMT_USD2 = "$#,0.00"
FMT_PCT1 = "0.0 %"
FMT_PCT2 = "0.00 %"
FMT_DEC1 = "#,0.0"
FMT_DEC2 = "#,0.00"

# (dossier, nom, expression DAX, format, description)
MEASURES = [
    ("1. Volume et CA", "Courses", "SUM ( fact_trips_agg[nb_trips] )", FMT_INT,
     "Nombre de courses analysées"),
    ("1. Volume et CA", "Chiffre d'affaires", "SUM ( fact_trips_agg[total_amount] )", FMT_USD0,
     "Montant total payé (tarif, suppléments, taxes, péages, pourboires carte)"),
    ("1. Volume et CA", "Courses par jour", "AVERAGEX ( VALUES ( dim_date[Date] ), [Courses] )", FMT_INT,
     "Moyenne journalière, valable quel que soit le filtre de dates"),
    ("1. Volume et CA", "Courses par jour (hors fériés)",
     "CALCULATE ( [Courses par jour], dim_date[Jour férié] = FALSE () )", FMT_INT,
     "Moyenne journalière sur les jours ordinaires uniquement"),
    ("1. Volume et CA", "Panier moyen", "DIVIDE ( [Chiffre d'affaires], [Courses] )", FMT_USD2,
     "Montant moyen d'une course"),
    ("2. Productivité", "Minutes de course", "SUM ( fact_trips_agg[duration_minutes] )", FMT_INT,
     "Temps total passé avec un client"),
    ("2. Productivité", "Revenu par minute", "DIVIDE ( [Chiffre d'affaires], [Minutes de course] )", FMT_USD2,
     "KPI central : ce que rapporte une minute passée avec un client"),
    ("2. Productivité", "Durée moyenne (min)", "DIVIDE ( [Minutes de course], [Courses] )", FMT_DEC1,
     "Durée moyenne d'une course"),
    ("2. Productivité", "Distance moyenne (miles)",
     "DIVIDE ( SUM ( fact_trips_agg[distance_miles] ), [Courses] )", FMT_DEC2, "Distance moyenne d'une course"),
    ("2. Productivité", "Vitesse moyenne (mph)",
     "DIVIDE ( SUM ( fact_trips_agg[distance_miles] ), [Minutes de course] / 60 )", FMT_DEC1,
     "Indicateur de congestion"),
    ("2. Productivité", "Écart revenu par minute vs moyenne",
     "VAR _moyenne = CALCULATE ( [Revenu par minute], ALLSELECTED () ) "
     "RETURN DIVIDE ( [Revenu par minute] - _moyenne, _moyenne )", FMT_PCT1,
     "Écart d'un segment par rapport à la moyenne de la sélection"),
    ("3. Parts", "Part des courses", "DIVIDE ( [Courses], CALCULATE ( [Courses], ALLSELECTED () ) )", FMT_PCT1,
     "Poids du segment dans les courses de la sélection"),
    ("3. Parts", "Part du CA",
     "DIVIDE ( [Chiffre d'affaires], CALCULATE ( [Chiffre d'affaires], ALLSELECTED () ) )", FMT_PCT1,
     "Poids du segment dans le CA de la sélection"),
    ("3. Parts", "CA aéroports",
     "CALCULATE ( [Chiffre d'affaires], fact_trips_agg[Type de course] = \"Aéroport\" )", FMT_USD0,
     "CA des courses partant d'un aéroport ou s'y rendant"),
    ("3. Parts", "Part du CA aéroports", "DIVIDE ( [CA aéroports], [Chiffre d'affaires] )", FMT_PCT1,
     "Poids des aéroports dans le CA"),
    ("3. Parts", "CA top 10 zones",
     "VAR _rang = RANKX ( ALLSELECTED ( dim_zone[Zone] ), [Chiffre d'affaires] ) "
     "RETURN IF ( _rang <= 10, [Chiffre d'affaires] )", FMT_USD0,
     "CA affiché uniquement pour les 10 premières zones (les autres sont vides donc masquées)"),
    ("4. Paiement", "Part paiement carte",
     "DIVIDE ( CALCULATE ( [Courses], dim_payment[ID paiement] = 1 ), [Courses] )", FMT_PCT1,
     "Part des courses payées par carte"),
    ("4. Paiement", "Taux de pourboire (carte)",
     "DIVIDE ( CALCULATE ( SUM ( fact_trips_agg[tip_amount] ), dim_payment[ID paiement] = 1 ), "
     "CALCULATE ( SUM ( fact_trips_agg[fare_amount] ), dim_payment[ID paiement] = 1 ) )", FMT_PCT1,
     "Pourboire / tarif, sur carte uniquement (pourboires espèces non enregistrés)"),
    ("5. Qualité", "Courses brutes",
     "CALCULATE ( SUM ( data_quality[Nb courses] ), data_quality[Catégorie] = \"Entrée\" )", FMT_INT,
     "Courses présentes dans le fichier brut"),
    ("5. Qualité", "Courses analysées",
     "CALCULATE ( SUM ( data_quality[Nb courses] ), data_quality[Catégorie] = \"Sortie\" )", FMT_INT,
     "Courses retenues après nettoyage et contrôle qualité"),
    ("5. Qualité", "Courses écartées", "[Courses brutes] - [Courses analysées]", FMT_INT,
     "Rejets et anomalies"),
    ("5. Qualité", "Taux de données exploitables", "DIVIDE ( [Courses analysées], [Courses brutes] )", FMT_PCT2,
     "Part des courses brutes retenues pour l'analyse"),
    ("5. Qualité", "Rejets et anomalies",
     "CALCULATE ( SUM ( data_quality[Nb courses] ), data_quality[Catégorie] IN { \"Rejet\", \"Anomalie\" } )",
     FMT_INT, "Courses écartées, par motif"),
    ("6. Libellés", "Titre période",
     "\"Du \" & FORMAT ( MIN ( dim_date[Date] ), \"dd/mm/yyyy\" ) & \" au \" & FORMAT ( MAX ( dim_date[Date] ), \"dd/mm/yyyy\" )",
     None, "Période couverte par la sélection"),
]
MEASURE_TABLE = "_Mesures"
MEASURE_NAMES = {m[1] for m in MEASURES}


def q(name: str) -> str:
    """Nom TMDL : entre apostrophes (doublées à l'intérieur) s'il contient autre chose que [A-Za-z0-9_]."""
    if name.replace("_", "").isalnum() and name.isascii():
        return name
    return "'" + name.replace("'", "''") + "'"


def stable_id(*parts, n=20) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:n]


def m_type(tmdl_type):
    return {"int64": "Int64.Type", "double": "type number", "string": "type text",
            "boolean": "type logical", "dateTime": "type date"}[tmdl_type]


def table_tmdl(table: str, columns) -> str:
    lines = [f"table {q(table)}"]
    if table == DATE_TABLE:
        lines.append("\tdataCategory: Time")
    lines.append("")
    for name, source, dtype, opts in columns:
        opts = [o.strip() for o in opts.split(";") if o.strip()]
        lines.append(f"\tcolumn {q(name)}")
        lines.append(f"\t\tdataType: {dtype}")
        if "hidden" in opts:
            lines.append("\t\tisHidden")
        if "key" in opts:
            lines.append("\t\tisKey")
        fmt = next((o[4:] for o in opts if o.startswith("fmt=")), None)
        if fmt is None and dtype == "int64":
            fmt = "0"
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: {source}")
        sort = next((o[5:] for o in opts if o.startswith("sort=")), None)
        if sort:
            lines.append(f"\t\tsortByColumn: {q(sort)}")
        lines.append("")
    types = ", ".join(f'{{"{src}", {m_type(dt)}}}' for _, src, dt, _ in columns)
    lines += [
        f"\tpartition {q(table)} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = Parquet.Document(File.Contents(DossierDonnees & "{table}.parquet")),',
        f"\t\t\t\t    Typed = Table.TransformColumnTypes(Source, {{{types}}})",
        "\t\t\t\tin",
        "\t\t\t\t    Typed",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines)


def measures_tmdl() -> str:
    lines = [f"table {q(MEASURE_TABLE)}", ""]
    for folder, name, expr, fmt, desc in MEASURES:
        lines.append(f"\t/// {desc}")
        lines.append(f"\tmeasure {q(name)} = {expr}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append("")
    lines += [
        "\tcolumn Colonne",
        "\t\tdataType: string",
        "\t\tisHidden",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: Colonne",
        "",
        f"\tpartition {q(MEASURE_TABLE)} = m",
        "\t\tmode: import",
        "\t\tsource = #table(type table [Colonne = text], {})",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines)


def write(path: str, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not isinstance(content, str):
        content = json.dumps(content, indent=2, ensure_ascii=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def platform(item_type: str) -> dict:
    return {
        "$schema": f"{SCHEMAS}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": item_type, "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, NAME + item_type))},
    }


def build_model():
    d = os.path.join(MODEL_DIR, "definition")
    write(os.path.join(MODEL_DIR, ".platform"), platform("SemanticModel"))
    write(os.path.join(MODEL_DIR, "definition.pbism"), {
        "$schema": f"{SCHEMAS}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})
    write(os.path.join(d, "database.tmdl"), "database\n\tcompatibilityLevel: 1601\n")
    all_tables = list(TABLES) + [MEASURE_TABLE]
    write(os.path.join(d, "model.tmdl"), "\n".join([
        "model Model",
        "\tculture: fr-FR",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: fr-FR",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation PBI_ProTooling = [\"TMDL-Extension\"]",
        "",
        *[f"ref table {q(t)}" for t in all_tables],
        "",
    ]))
    write(os.path.join(d, "expressions.tmdl"),
          f'expression DossierDonnees = "{DEFAULT_DATA_PATH}" '
          'meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
          "\tannotation PBI_ResultType = Text\n")
    rels = []
    for (ft, fc), (tt, tc) in RELATIONSHIPS:
        rels += [f"relationship {uuid.uuid5(uuid.NAMESPACE_URL, ft + fc + tt + tc)}",
                 f"\tfromColumn: {q(ft)}.{q(fc)}", f"\ttoColumn: {q(tt)}.{q(tc)}", ""]
    write(os.path.join(d, "relationships.tmdl"), "\n".join(rels))
    for table, columns in TABLES.items():
        write(os.path.join(d, "tables", f"{table}.tmdl"), table_tmdl(table, columns))
    write(os.path.join(d, "tables", f"{MEASURE_TABLE}.tmdl"), measures_tmdl())


# =====================================================================
# 2. RAPPORT : helpers de requêtes et de mise en forme
# =====================================================================
def lit(value) -> dict:
    """Littéral Power BI : texte entre apostrophes, booléen, nombre décimal (D)."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def col(table: str, name: str) -> dict:
    assert any(c[0] == name for c in TABLES[table]), f"Colonne inconnue {table}[{name}]"
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def measure(name: str) -> dict:
    assert name in MEASURE_NAMES, f"Mesure inconnue [{name}]"
    return {"Measure": {"Expression": {"SourceRef": {"Entity": MEASURE_TABLE}}, "Property": name}}


def total(table: str, name: str) -> dict:
    return {"Aggregation": {"Expression": col(table, name), "Function": 0}}


def proj(field: dict, display: str = None) -> dict:
    if "Measure" in field:
        ref = f"{MEASURE_TABLE}.{field['Measure']['Property']}"
    elif "Aggregation" in field:
        c = field["Aggregation"]["Expression"]["Column"]
        ref = f"Sum({c['Expression']['SourceRef']['Entity']}.{c['Property']})"
    else:
        ref = f"{field['Column']['Expression']['SourceRef']['Entity']}.{field['Column']['Property']}"
    p = {"field": field, "queryRef": ref, "nativeQueryRef": ref.split(".", 1)[-1].rstrip(")")}
    if "Column" in field:
        p["active"] = True
    if display:
        p["displayName"] = display
    return p


def container_objects(title: str = None) -> dict:
    objs = {}
    if title:
        objs["title"] = [{"properties": {"show": lit(True), "text": lit(title)}}]
    return objs


class Page:
    def __init__(self, key: str, display_name: str):
        self.name = stable_id("page", key)
        self.display_name = display_name
        self.visuals = []

    def add(self, x, y, w, h, visual: dict, title: str = None, container_extra: dict = None):
        name = stable_id(self.name, str(len(self.visuals)))
        z = len(self.visuals) * 1000
        vc = container_objects(title)
        if container_extra:
            vc.update(container_extra)
        if vc:
            visual["visualContainerObjects"] = vc
        visual["drillFilterOtherVisuals"] = True
        self.visuals.append({
            "$schema": f"{SCHEMAS}/item/report/definition/visualContainer/2.0.0/schema.json",
            "name": name,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
            "visual": visual,
        })


def chart(visual_type: str, roles: dict, sort=None, objects=None) -> dict:
    v = {"visualType": visual_type,
         "query": {"queryState": {role: {"projections": projs} for role, projs in roles.items()}}}
    if sort:
        field, direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": field, "direction": direction}]}
    if objects:
        v["objects"] = objects
    return v


def data_labels() -> dict:
    return {"labels": [{"properties": {"show": lit(True)}}]}


def card(measure_name: str) -> dict:
    return chart("card", {"Values": [proj(measure(measure_name))]})


def slicer(table: str, column: str, mode: str) -> dict:
    return chart("slicer", {"Values": [proj(col(table, column))]},
                 objects={"data": [{"properties": {"mode": lit(mode)}}]})


def textbox(paragraphs) -> dict:
    """paragraphs : liste de (texte, taille en pt, gras, couleur)."""
    return {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [
        {"textRuns": [{"value": text, "textStyle": {
            "fontSize": f"{size}pt", "fontWeight": "bold" if bold else "normal", "color": color}}]}
        for text, size, bold, color in paragraphs]}}]}}


NO_BACKGROUND = {"background": [{"properties": {"show": lit(False)}}],
                 "border": [{"properties": {"show": lit(False)}}]}
INK, MUTED = "#0B0B0B", "#52514E"


def header(page: Page, title: str, subtitle: str):
    page.add(20, 8, 1240, 52, textbox([(title, 18, True, INK), (subtitle, 10, False, MUTED)]),
             container_extra=NO_BACKGROUND)


def takeaway(page: Page, y: int, h: int, text: str):
    page.add(20, y, 1240, h, textbox([("À retenir", 11, True, "#104281"), (text, 11, False, INK)]))


def heatmap_objects(measure_name: str) -> dict:
    measure(measure_name)  # vérifie que la mesure existe
    return {
        "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
        "values": [{
            "properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
                "Input": {"SelectRef": {"ExpressionName": f"{MEASURE_TABLE}.{measure_name}"}},
                "FillRule": {"linearGradient2": {
                    "min": {"color": {"Literal": {"Value": "'#F0F5FC'"}}},
                    "max": {"color": {"Literal": {"Value": "'#1C5CAB'"}}},
                    "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}},
                }},
            }}}}}},
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                         "metadata": f"{MEASURE_TABLE}.{measure_name}"},
        }],
    }


# =====================================================================
# 3. RAPPORT : les 5 pages
# =====================================================================
def build_pages():
    pages = []

    # --- Page 1 : Vue d'ensemble -------------------------------------------
    p = Page("overview", "1. Vue d'ensemble")
    header(p, "NYC Taxi | Vue d'ensemble de l'activité",
           "Yellow Taxis de New York, janvier 2019. Question : comment se porte l'activité ?")
    p.add(20, 66, 400, 72, slicer("dim_date", "Date", "Between"), title="Période")
    p.add(432, 66, 270, 72, slicer("fact_trips_agg", "Type de course", "Dropdown"), title="Type de course")
    p.add(714, 66, 270, 72, slicer("dim_payment", "Mode de paiement", "Dropdown"), title="Mode de paiement")
    p.add(996, 66, 264, 72, slicer("dim_date", "Jour", "Dropdown"), title="Jour de la semaine")
    kpis = ["Courses", "Chiffre d'affaires", "Panier moyen", "Revenu par minute",
            "Part du CA aéroports", "Taux de pourboire (carte)"]
    for i, k in enumerate(kpis):
        p.add(20 + i * 208, 150, 196, 96, card(k))
    p.add(20, 258, 760, 320, chart("lineChart", {
        "Category": [proj(col("dim_date", "Date"))],
        "Y": [proj(measure("Chiffre d'affaires"))]}),
        title="Chiffre d'affaires par jour (creux le dimanche et les jours fériés)")
    p.add(792, 258, 468, 320, chart("clusteredBarChart", {
        "Category": [proj(col("fact_trips_agg", "Type de course"))],
        "Y": [proj(measure("Part des courses")), proj(measure("Part du CA"))]},
        sort=(measure("Part du CA"), "Descending"), objects=data_labels()),
        title="Poids de chaque type de course : volume et CA")
    takeaway(p, 590, 118, "Les aéroports représentent 6 % des courses mais 21 % du chiffre d'affaires. "
             "Les courses dans Manhattan font 85 % du volume mais seulement 65 % du CA.")
    pages.append(p)

    # --- Page 2 : Quand ? ------------------------------------------------------
    p = Page("when", "2. Quand ?")
    header(p, "Quand ? Demande et productivité selon l'heure",
           "Question : à quelles heures faut-il maximiser le nombre de véhicules en service ?")
    p.add(20, 66, 1240, 270, chart("pivotTable", {
        "Rows": [proj(col("dim_date", "Jour"))],
        "Columns": [proj(col("dim_hour", "Heure"))],
        "Values": [proj(measure("Courses par jour (hors fériés)"))]},
        objects=heatmap_objects("Courses par jour (hors fériés)")),
        title="Nombre moyen de courses par heure et jour de semaine (hors jours fériés)")
    p.add(20, 348, 406, 238, chart("clusteredColumnChart", {
        "Category": [proj(col("dim_hour", "Heure"))],
        "Y": [proj(measure("Courses"))]},
        sort=(col("dim_hour", "Heure"), "Ascending")), title="Courses par heure")
    p.add(437, 348, 406, 238, chart("lineChart", {
        "Category": [proj(col("dim_hour", "Heure"))],
        "Y": [proj(measure("Revenu par minute"))]},
        sort=(col("dim_hour", "Heure"), "Ascending")), title="Revenu par minute selon l'heure")
    p.add(854, 348, 406, 238, chart("clusteredBarChart", {
        "Category": [proj(col("dim_hour", "Créneau"))],
        "Y": [proj(measure("Revenu par minute"))]},
        sort=(col("dim_hour", "Créneau"), "Ascending"), objects=data_labels()),
        title="Revenu par minute par créneau")
    takeaway(p, 598, 110, "Le pic de demande est à 18h, mais le revenu par minute chute de 35 % entre 5h et 8h-9h "
             "à cause de la congestion (vitesse divisée par deux). Les nuits du week-end sont 3 fois plus actives "
             "que celles de semaine.")
    pages.append(p)

    # --- Page 3 : Où ? -----------------------------------------------------------
    p = Page("where", "3. Où ?")
    header(p, "Où ? Les zones de prise en charge",
           "Question : où positionner les véhicules ?")
    p.add(20, 66, 560, 320, chart("clusteredBarChart", {
        "Category": [proj(col("dim_zone", "Zone"))],
        "Y": [proj(measure("CA top 10 zones"), "Chiffre d'affaires")]},
        sort=(measure("CA top 10 zones"), "Descending"), objects=data_labels()),
        title="Top 10 des zones par chiffre d'affaires")
    p.add(592, 66, 668, 320, chart("scatterChart", {
        "Category": [proj(col("dim_zone", "Zone"))],
        "Series": [proj(col("dim_zone", "Borough"))],
        "X": [proj(measure("Courses"))],
        "Y": [proj(measure("Revenu par minute"))],
        "Size": [proj(measure("Chiffre d'affaires"))]}),
        title="Volume vs productivité par zone (taille = CA)")
    p.add(20, 398, 820, 190, chart("tableEx", {
        "Values": [proj(col("dim_zone", "Zone")), proj(col("dim_zone", "Borough")),
                   proj(measure("Courses")), proj(measure("Chiffre d'affaires")),
                   proj(measure("Part du CA")), proj(measure("Panier moyen")),
                   proj(measure("Revenu par minute"))]},
        sort=(measure("Chiffre d'affaires"), "Descending")), title="Détail par zone")
    p.add(852, 398, 408, 190, chart("treemap", {
        "Group": [proj(col("dim_zone", "Borough"))],
        "Values": [proj(measure("Chiffre d'affaires"))]}), title="Chiffre d'affaires par borough")
    takeaway(p, 600, 108, "14 zones sur 263 génèrent la moitié du CA. JFK et LaGuardia arrivent en tête (15,7 % du CA "
             "à elles deux). En haut à droite du nuage de points : les zones à fort volume et forte productivité.")
    pages.append(p)

    # --- Page 4 : Rentabilité ---------------------------------------------------
    p = Page("profitability", "4. Rentabilité")
    header(p, "Quelles courses sont les plus rentables ?",
           "Question : quels types de course privilégier pour maximiser le revenu par minute ?")
    p.add(20, 66, 610, 300, chart("clusteredColumnChart", {
        "Category": [proj(col("fact_trips_agg", "Type de course"))],
        "Y": [proj(measure("Revenu par minute"))]},
        sort=(measure("Revenu par minute"), "Descending"), objects=data_labels()),
        title="Revenu par minute par type de course")
    p.add(650, 66, 610, 300, chart("clusteredColumnChart", {
        "Category": [proj(col("fact_trips_agg", "Tranche de distance"))],
        "Y": [proj(measure("Revenu par minute"))]},
        sort=(col("fact_trips_agg", "Tranche de distance"), "Ascending"), objects=data_labels()),
        title="Revenu par minute par tranche de distance (courbe en U)")
    p.add(20, 378, 610, 212, chart("clusteredBarChart", {
        "Category": [proj(col("fact_trips_agg", "Type de course"))],
        "Y": [proj(measure("Taux de pourboire (carte)"))]},
        sort=(measure("Taux de pourboire (carte)"), "Descending"), objects=data_labels()),
        title="Taux de pourboire (paiements carte) par type de course")
    p.add(650, 378, 610, 212, chart("donutChart", {
        "Category": [proj(col("dim_payment", "Mode de paiement"))],
        "Y": [proj(measure("Courses"))]}), title="Répartition des courses par mode de paiement")
    takeaway(p, 602, 106, "Une minute de course aéroport rapporte 1,59 $ contre 1,10 $ dans Manhattan (+45 %). "
             "Les courses de 2 à 5 miles sont les moins rentables (1,01 $/min). 28 % des courses sont payées "
             "en espèces, sans pourboire enregistré.")
    pages.append(p)

    # --- Page 5 : Qualité des données ---------------------------------------------
    p = Page("quality", "5. Qualité des données")
    header(p, "Peut-on faire confiance aux chiffres ?",
           "Traçabilité de la donnée brute à la donnée analysée : chaque exclusion a un motif.")
    for i, k in enumerate(["Courses brutes", "Courses écartées", "Courses analysées",
                           "Taux de données exploitables"]):
        p.add(20 + i * 314, 66, 302, 96, card(k))
    p.add(20, 174, 700, 416, chart("clusteredBarChart", {
        "Category": [proj(col("data_quality", "Motif"))],
        "Series": [proj(col("data_quality", "Catégorie"))],
        "Y": [proj(measure("Rejets et anomalies"), "Courses écartées")]},
        sort=(measure("Rejets et anomalies"), "Descending"), objects=data_labels()),
        title="Courses écartées par motif (rejet au nettoyage ou anomalie signalée)")
    p.add(732, 174, 528, 416, chart("tableEx", {
        "Values": [proj(col("data_quality", "Étape")), proj(col("data_quality", "Motif")),
                   proj(total("data_quality", "Nb courses"), "Courses"),
                   proj(total("data_quality", "Part du brut"), "Part du brut")]},
        sort=(col("data_quality", "Étape"), "Ascending")), title="Détail par étape du pipeline")
    takeaway(p, 602, 106, "97,04 % des courses brutes sont exploitables. 99,9 % des rejets « Aucun passager » "
             "viennent d'un seul fournisseur de taximètre : un défaut de saisie systémique, à lui signaler.")
    pages.append(p)
    return pages


def build_report():
    d = os.path.join(REPORT_DIR, "definition")
    write(os.path.join(REPORT_DIR, ".platform"), platform("Report"))
    write(os.path.join(REPORT_DIR, "definition.pbir"), {
        "$schema": f"{SCHEMAS}/item/report/definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    write(os.path.join(d, "version.json"), {
        "$schema": f"{SCHEMAS}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})

    # Thèmes : thème de base Microsoft + thème personnalisé du projet
    base_theme = "CY24SU10"
    static = os.path.join(REPORT_DIR, "StaticResources")
    shutil.copy(os.path.join(HERE, "theme_base", f"{base_theme}.json"),
                _mkdir_for(os.path.join(static, "SharedResources", "BaseThemes", f"{base_theme}.json")))
    shutil.copy(os.path.join(HERE, "theme_nyc_taxi.json"),
                _mkdir_for(os.path.join(static, "RegisteredResources", "theme_nyc_taxi.json")))
    write(os.path.join(d, "report.json"), {
        "$schema": f"{SCHEMAS}/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": base_theme, "reportVersionAtImport": "5.61", "type": "SharedResources"},
            "customTheme": {"name": "theme_nyc_taxi.json", "reportVersionAtImport": "5.61",
                            "type": "RegisteredResources"},
        },
        "layoutOptimization": "None",
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": base_theme, "path": f"BaseThemes/{base_theme}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "theme_nyc_taxi.json", "path": "theme_nyc_taxi.json", "type": "CustomTheme"}]},
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
        },
    })

    pages = build_pages()
    write(os.path.join(d, "pages", "pages.json"), {
        "$schema": f"{SCHEMAS}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.name for p in pages], "activePageName": pages[0].name})
    for p in pages:
        write(os.path.join(d, "pages", p.name, "page.json"), {
            "$schema": f"{SCHEMAS}/item/report/definition/page/1.4.0/schema.json",
            "name": p.name, "displayName": p.display_name, "displayOption": "FitToPage",
            "height": 720, "width": 1280})
        for v in p.visuals:
            write(os.path.join(d, "pages", p.name, "visuals", v["name"], "visual.json"), v)


def _mkdir_for(path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def build_dax_reference():
    lines = ["// Mesures DAX du dashboard (générées par powerbi/generer_pbip.py, table _Mesures)",
             "// Règle d'or : un ratio = DIVIDE(SUM(numérateur), SUM(dénominateur)), jamais une moyenne de moyennes.",
             ""]
    folder = None
    for f, name, expr, fmt, desc in MEASURES:
        if f != folder:
            lines += ["", f"// ---------- {f} " + "-" * (60 - len(f)), ""]
            folder = f
        lines += [f"// {desc}" + (f"  (format : {fmt})" if fmt else ""), f"{name} =", expr, ""]
    write(os.path.join(HERE, "mesures_dax.dax"), "\n".join(lines))


if __name__ == "__main__":
    for folder in (MODEL_DIR, REPORT_DIR):
        shutil.rmtree(folder, ignore_errors=True)
    build_model()
    build_report()
    build_dax_reference()
    write(os.path.join(HERE, f"{NAME}.pbip"), {
        "$schema": f"{SCHEMAS}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True}})
    print(f"Projet généré : powerbi/{NAME}.pbip")
