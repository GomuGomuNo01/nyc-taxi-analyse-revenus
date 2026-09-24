"""
Génère les graphiques d'analyse (docs/images/*.png) à partir des requêtes SQL.
Principes : une couleur d'accent pour le message, du gris pour le contexte,
un seul axe par graphique, des libellés directs plutôt qu'une légende quand c'est possible.

Usage : python analysis/make_charts.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from run_queries import ROOT, run_all

IMAGES = os.path.join(ROOT, "docs", "images")
ACCENT = "#2a78d6"
ACCENT_DARK = "#104281"
CONTEXT = "#c9c8c1"
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_MUTED = "#52514e"
GRID = "#e6e5e0"
BLUES = LinearSegmentedColormap.from_list("blues", ["#f0f5fc", "#9ec5f4", "#3987e5", "#1c5cab", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": TEXT,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT_MUTED, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 14,
    "xtick.color": TEXT_MUTED, "ytick.color": TEXT_MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
})


def fmt_k(x):
    return f"{x / 1e6:.1f} M" if x >= 1e6 else f"{x / 1e3:.0f} k"


def save(fig, name, source=True):
    if source:
        fig.text(0.01, -0.03, "Source : NYC TLC, Yellow Taxi janvier 2019 (7,44 M de courses analysées)",
                 fontsize=8, color=TEXT_MUTED)
    fig.savefig(os.path.join(IMAGES, name), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[charts] docs/images/{name}")


def chart_heatmap(df):
    pivot = df.pivot(index="day_of_week", columns="hour", values="courses_moyennes")
    days = df.drop_duplicates("day_of_week").set_index("day_of_week")["day_name"]
    fig, ax = plt.subplots(figsize=(12, 3.8))
    im = ax.imshow(pivot.values, aspect="auto", cmap=BLUES)
    ax.set_yticks(range(7), [days[d] for d in pivot.index])
    ax.set_xticks(range(24), [f"{h}h" for h in range(24)])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Demande : nombre moyen de courses par heure et jour de semaine")
    cbar = fig.colorbar(im, ax=ax, pad=0.01, fraction=0.03)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=TEXT_MUTED, labelsize=8)
    save(fig, "01_demande_heure_jour.png")


def chart_demand_vs_productivity(df):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True, gridspec_kw={"hspace": 0.35})
    peak = df["nb_courses"].idxmax()
    ax1.bar(df["hour"], df["nb_courses"], width=0.8,
            color=[ACCENT if i == peak else CONTEXT for i in df.index])
    ax1.set_title("Le pic de demande (18h) ne coïncide pas avec le pic de rentabilité")
    ax1.set_ylabel("Courses sur le mois")
    ax1.yaxis.set_major_formatter(lambda x, _: fmt_k(x) if x else "0")
    ax1.grid(axis="x", visible=False)
    ax1.annotate(f"{df.loc[peak, 'nb_courses']:,.0f} courses".replace(",", " "),
                 (df.loc[peak, "hour"], df.loc[peak, "nb_courses"]), xytext=(0, 4),
                 textcoords="offset points", ha="center", fontsize=9, color=TEXT)

    ax2.plot(df["hour"], df["revenu_par_minute_usd"], color=ACCENT, linewidth=2, marker="o", markersize=5)
    ax2.set_ylabel("Revenu par minute ($)")
    ax2.set_ylim(0.9, 1.8)
    ax2.set_title("Revenu par minute de course : -35 % entre 5h et 8h-9h (congestion)", fontsize=11)
    best, worst = df["revenu_par_minute_usd"].idxmax(), df["revenu_par_minute_usd"].idxmin()
    for i, dy in [(best, 8), (worst, -16)]:
        ax2.annotate(f"{df.loc[i, 'revenu_par_minute_usd']:.2f} $/min à {df.loc[i, 'hour']}h",
                     (df.loc[i, "hour"], df.loc[i, "revenu_par_minute_usd"]), xytext=(0, dy),
                     textcoords="offset points", ha="center", fontsize=9, color=TEXT)
    ax2.set_xticks(range(24), [f"{h}h" for h in range(24)])
    save(fig, "02_demande_vs_productivite.png")


def chart_trip_category(df):
    df = df.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    y = range(len(df))
    h = 0.36
    ax.barh([i + h / 2 + 0.02 for i in y], df["part_courses_pct"], height=h, color=CONTEXT, label="Part des courses")
    ax.barh([i - h / 2 - 0.02 for i in y], df["part_ca_pct"], height=h, color=ACCENT, label="Part du chiffre d'affaires")
    for i, r in df.iterrows():
        ax.text(r["part_courses_pct"] + 0.8, i + h / 2 + 0.02, f"{r['part_courses_pct']:.1f} %", va="center", fontsize=9, color=TEXT_MUTED)
        ax.text(r["part_ca_pct"] + 0.8, i - h / 2 - 0.02,
                f"{r['part_ca_pct']:.1f} %   ({r['revenu_par_minute_usd']:.2f} $/min)", va="center", fontsize=9, color=TEXT)
    ax.set_yticks(list(y), df["type_course"])
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f} %")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", frameon=False)
    ax.set_title("Aéroports : 6 % des courses, 21 % du chiffre d'affaires")
    save(fig, "03_type_de_course.png")


def chart_top_zones(df):
    df = df.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = [ACCENT if "Airport" in z else CONTEXT for z in df["zone"]]
    ax.barh(df["zone"], df["chiffre_affaires_usd"], color=colors, height=0.7)
    for i, r in df.iterrows():
        ax.text(r["chiffre_affaires_usd"] + 1.5e5, i, f"{r['chiffre_affaires_usd'] / 1e6:.1f} M$  ({r['part_ca_pct']:.1f} %)",
                va="center", fontsize=9, color=TEXT)
    ax.set_xlim(0, df["chiffre_affaires_usd"].max() * 1.25)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x / 1e6:.0f} M$")
    ax.grid(axis="y", visible=False)
    ax.set_title("Top 10 des zones de prise en charge par chiffre d'affaires")
    save(fig, "04_top_zones.png")


def chart_distance(df):
    fig, ax = plt.subplots(figsize=(10, 4))
    labels = [b.split(". ", 1)[1] for b in df["tranche_distance"]]
    worst = df["revenu_par_minute_usd"].idxmin()
    ax.bar(labels, df["revenu_par_minute_usd"], width=0.6,
           color=[CONTEXT if i == worst else ACCENT for i in df.index])
    for i, r in df.iterrows():
        ax.text(i, r["revenu_par_minute_usd"] + 0.02, f"{r['revenu_par_minute_usd']:.2f} $/min\n{r['part_courses_pct']:.0f} % des courses",
                ha="center", fontsize=9, color=TEXT)
    ax.set_ylim(0, 1.9)
    ax.set_ylabel("Revenu par minute ($)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Courses de 2 à 5 miles : les moins rentables à la minute (courbe en U)")
    save(fig, "05_tranche_distance.png")


def chart_daily(df):
    fig, ax = plt.subplots(figsize=(12, 3.8))
    colors = [ACCENT_DARK if h else (ACCENT if j in ("Samedi", "Dimanche") else CONTEXT)
              for h, j in zip(df["is_holiday"], df["jour"])]
    ax.bar(df["date"].astype(str).str[-2:], df["nb_courses"], color=colors, width=0.75)
    for i, r in df[df["is_holiday"]].iterrows():
        label = "Nouvel An" if r["date"].day == 1 else "MLK Day"
        ax.annotate(label, (i, r["nb_courses"]), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=8, color=TEXT)
    ax.yaxis.set_major_formatter(lambda x, _: fmt_k(x) if x else "0")
    ax.grid(axis="x", visible=False)
    ax.set_xlabel("Jour de janvier 2019   (bleu : week-end, bleu foncé : jour férié)")
    ax.set_title("Activité quotidienne : creux le dimanche et les jours fériés")
    save(fig, "06_activite_quotidienne.png")


if __name__ == "__main__":
    os.makedirs(IMAGES, exist_ok=True)
    r = run_all()
    chart_heatmap(r["demande_heure_jour"])
    chart_demand_vs_productivity(r["productivite_par_heure"])
    chart_trip_category(r["type_de_course"])
    chart_top_zones(r["top_zones"])
    chart_distance(r["tranche_distance"])
    chart_daily(r["activite_quotidienne"])
