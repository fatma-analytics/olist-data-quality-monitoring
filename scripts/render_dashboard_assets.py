from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

NAVY = "#13233A"
TEAL = "#168C85"
BLUE = "#3C78A6"
AMBER = "#E4A548"
RED = "#C75454"
INK = "#233248"
MUTED = "#66758A"
PANEL = "#FFFFFF"
CANVAS = "#F3F6FA"
GRID = "#E6EBF1"


def setup_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.labelcolor": MUTED,
        "text.color": INK,
        "axes.edgecolor": GRID,
        "axes.linewidth": 0.8,
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "xtick.color": MUTED,
        "ytick.color": INK,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "figure.facecolor": CANVAS,
        "savefig.facecolor": CANVAS,
    })


def shorten_rule(row: pd.Series) -> str:
    rule = str(row["rule_id"])
    table = str(row["table_name"])
    if rule == "DATE_DELIVERED_VS_ESTIMATE":
        return "Commandes · retard livraison"
    if rule.startswith("COMPLETENESS_"):
        col = str(row.get("column_name", ""))
        labels = {
            "product_category_name": "Produits · catégorie manquante",
            "product_name_lenght": "Produits · nom manquant",
            "product_description_lenght": "Produits · description manquante",
            "product_photos_qty": "Produits · nb photos manquant",
            "product_weight_g": "Produits · poids manquant",
            "product_length_cm": "Produits · longueur manquante",
            "product_height_cm": "Produits · hauteur manquante",
            "product_width_cm": "Produits · largeur manquante",
            "order_approved_at": "Commandes · date approbation manquante",
            "order_delivered_customer_date": "Commandes · date livraison manquante",
            "order_delivered_carrier_date": "Commandes · date transporteur manquante",
        }
        return labels.get(col, f"{table} · {col.replace('_', ' ')} manquant")
    return rule.replace("_", " ").title()


def shorten_column(table: str, column: str) -> str:
    labels = {
        ("order_reviews", "review_comment_title"): "Avis · titre commentaire",
        ("order_reviews", "review_comment_message"): "Avis · texte commentaire",
        ("orders", "order_delivered_customer_date"): "Commandes · date livraison",
        ("orders", "order_delivered_carrier_date"): "Commandes · date transporteur",
        ("orders", "order_approved_at"): "Commandes · date approbation",
        ("products", "product_category_name"): "Produits · catégorie",
        ("products", "product_description_lenght"): "Produits · description",
        ("products", "product_name_lenght"): "Produits · nom",
        ("products", "product_photos_qty"): "Produits · photos",
    }
    return labels.get((table, column), f"{table} · {column}")


def save_chart(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor=CANVAS)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rendre des PNG depuis les résultats du monitoring.")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--assets", type=Path, default=Path("assets"))
    args = parser.parse_args()
    args.assets.mkdir(parents=True, exist_ok=True)
    required = ["run_summary.csv", "table_quality.csv", "quality_issues.csv", "column_quality.csv"]
    missing = [name for name in required if not (args.outputs / name).exists()]
    if missing:
        raise FileNotFoundError("Exécutez d’abord le pipeline ; sorties manquantes : " + ", ".join(missing))

    setup_style()
    summary = pd.read_csv(args.outputs / "run_summary.csv").iloc[0]
    tables = pd.read_csv(args.outputs / "table_quality.csv").sort_values("quality_score_pct")
    issues = pd.read_csv(args.outputs / "quality_issues.csv")
    columns = pd.read_csv(args.outputs / "column_quality.csv")
    timestamp = str(summary.generated_at_utc)[:10]

    # Graphique individuel : score par table, axe resserré pour rendre visibles les écarts.
    fig, ax = plt.subplots(figsize=(9, 5.4))
    vals = tables.sort_values("quality_score_pct", ascending=True)
    colors = [RED if x < 95 else AMBER if x < 99 else TEAL for x in vals.quality_score_pct]
    bars = ax.barh(vals.table_name, vals.quality_score_pct, color=colors, height=0.68)
    ax.set_xlim(95, 100.6)
    ax.set_xlabel("Score qualité (%) · axe zoomé de 95 à 100")
    ax.set_title("Score de qualité par table", loc="left", pad=15)
    ax.grid(axis="x", alpha=0.8)
    ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, vals.quality_score_pct):
        ax.text(value + 0.07, bar.get_y() + bar.get_height()/2, f"{value:.2f}%", va="center", fontsize=9, color=INK)
    save_chart(fig, args.assets / "quality_by_table.png")

    # Graphique individuel : taux d’échec des règles réellement détectées.
    fig, ax = plt.subplots(figsize=(10, 6.1))
    issue_plot = issues.copy()
    issue_plot["label"] = issue_plot.apply(shorten_rule, axis=1)
    issue_plot = issue_plot.sort_values("failure_rate_pct", ascending=True).tail(10)
    bars = ax.barh(issue_plot.label, issue_plot.failure_rate_pct,
                   color=[RED if s == "Critical" else AMBER if s in ("High", "Medium") else BLUE
                          for s in issue_plot.severity], height=0.7)
    ax.set_xlabel("Lignes en échec parmi les lignes testées (%)")
    ax.set_title("Règles en échec · taux observé", loc="left", pad=15)
    ax.grid(axis="x", alpha=0.8)
    ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, issue_plot.failure_rate_pct):
        ax.text(value + max(issue_plot.failure_rate_pct.max() * 0.012, 0.02),
                bar.get_y() + bar.get_height()/2, f"{value:.2f}%", va="center", fontsize=9)
    save_chart(fig, args.assets / "anomaly_rates.png")

    # Graphique individuel : profil de valeurs manquantes ; les commentaires sont facultatifs.
    fig, ax = plt.subplots(figsize=(10, 5.7))
    nulls = columns.sort_values("null_rate_pct", ascending=False).head(10).sort_values("null_rate_pct")
    labels = [f"{r.table_name} · {r.column_name}" for r in nulls.itertuples()]
    bar_colors = [AMBER if r.table_name == "order_reviews" and r.column_name.startswith("review_comment") else BLUE
                  for r in nulls.itertuples()]
    bars = ax.barh(labels, nulls.null_rate_pct, color=bar_colors, height=0.7)
    ax.set_xlabel("Valeurs manquantes (%)")
    ax.set_title("Colonnes les plus incomplètes", loc="left", pad=15)
    ax.grid(axis="x", alpha=0.8)
    ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, nulls.null_rate_pct):
        ax.text(value + 1.0, bar.get_y() + bar.get_height()/2, f"{value:.1f}%", va="center", fontsize=9)
    ax.text(0.99, -0.17, "Orange : commentaires d’avis facultatifs, hors score qualité.",
            transform=ax.transAxes, ha="right", fontsize=8, color=MUTED)
    save_chart(fig, args.assets / "completeness_profile.png")

    # Aperçu composite du dashboard, au format image directement intégrable dans GitHub.
    fig = plt.figure(figsize=(16, 10), facecolor=CANVAS)
    grid = fig.add_gridspec(3, 4, height_ratios=[0.86, 2.1, 2.5], hspace=0.42, wspace=0.38,
                            left=0.055, right=0.97, top=0.88, bottom=0.09)
    fig.text(0.055, 0.965, "Monitoring BI · Qualité des données", fontsize=23, weight="bold", color=NAVY, va="top")
    fig.text(0.055, 0.925, "Olist Brazilian E-Commerce  |  Exécution réelle du pipeline  |  " + timestamp,
             fontsize=10.5, color=MUTED, va="top")
    kpis = [
        ("SCORE QUALITÉ", f"{summary.overall_quality_score_pct:.2f}%", TEAL),
        ("TABLES", f"{int(summary.tables_monitored)}", BLUE),
        ("LIGNES PROFILÉES", f"{int(summary.rows_profiled):,}".replace(",", " "), NAVY),
        ("RÈGLES EN ÉCHEC", f"{int(summary.checks_failed)} / {int(summary.checks_total)}", AMBER),
    ]
    for i, (label, value, color) in enumerate(kpis):
        ax = fig.add_subplot(grid[0, i])
        ax.set_facecolor(PANEL)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_color(GRID)
        ax.text(0.08, 0.72, label, transform=ax.transAxes, fontsize=8.5, weight="bold", color=MUTED, va="center")
        ax.text(0.08, 0.33, value, transform=ax.transAxes, fontsize=20, weight="bold", color=color, va="center")

    ax = fig.add_subplot(grid[1, :2])
    ax.set_facecolor(PANEL)
    vals = tables.sort_values("quality_score_pct").copy()
    vals["table_label"] = vals.table_name.str.replace("_", " ", regex=False)
    bars = ax.barh(vals.table_label, vals.quality_score_pct,
                   color=[RED if x < 95 else AMBER if x < 99 else TEAL for x in vals.quality_score_pct], height=0.68)
    ax.set_xlim(95, 102); ax.set_xlabel("Score (%) · échelle zoomée")
    ax.set_title("Qualité par table", loc="left", color=NAVY, pad=12)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, vals.quality_score_pct):
        ax.text(value + 0.06, bar.get_y()+bar.get_height()/2, f"{value:.2f}", va="center", fontsize=8)

    ax = fig.add_subplot(grid[1, 2:])
    ax.set_facecolor(PANEL)
    issue_plot = issues.copy()
    issue_plot["label"] = issue_plot.apply(shorten_rule, axis=1)
    issue_plot = issue_plot.sort_values("failure_rate_pct", ascending=True).tail(7)
    bars = ax.barh(issue_plot.label, issue_plot.failure_rate_pct,
                   color=[RED if s == "Critical" else AMBER if s in ("High", "Medium") else BLUE
                          for s in issue_plot.severity], height=0.68)
    ax.set_xlabel("Lignes en échec (%)")
    ax.set_title("Principales règles en échec", loc="left", color=NAVY, pad=12)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, issue_plot.failure_rate_pct):
        ax.text(value + max(issue_plot.failure_rate_pct.max()*0.015, 0.02), bar.get_y()+bar.get_height()/2,
                f"{value:.2f}%", va="center", fontsize=8)

    ax = fig.add_subplot(grid[2, :2])
    ax.set_facecolor(PANEL)
    nulls = columns.sort_values("null_rate_pct", ascending=False).head(8).sort_values("null_rate_pct")
    labels = [shorten_column(r.table_name, r.column_name) for r in nulls.itertuples()]
    bar_colors = [AMBER if r.table_name == "order_reviews" and r.column_name.startswith("review_comment") else BLUE
                  for r in nulls.itertuples()]
    bars = ax.barh(labels, nulls.null_rate_pct, color=bar_colors, height=0.68)
    ax.set_xlabel("Valeurs manquantes (%)")
    ax.set_title("Profil de complétude", loc="left", color=NAVY, pad=12)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, nulls.null_rate_pct):
        ax.text(value + 1.0, bar.get_y()+bar.get_height()/2, f"{value:.1f}%", va="center", fontsize=8)

    ax = fig.add_subplot(grid[2, 2:])
    ax.set_facecolor(PANEL); ax.axis("off")
    ax.set_title("Lecture métier", loc="left", color=NAVY, pad=12)
    ax.text(0.02, 0.78, "RETARDS DE LIVRAISON", fontsize=9, weight="bold", color=MUTED, transform=ax.transAxes)
    delay = issues[issues.rule_id == "DATE_DELIVERED_VS_ESTIMATE"]
    delay_text = (f"{int(delay.iloc[0].rows_failed):,} commandes livrées après la date estimée "
                  f"({delay.iloc[0].failure_rate_pct:.2f}% des commandes livrées comparables).".replace(",", " ")) if len(delay) else "Aucun retard détecté."
    ax.text(0.02, 0.60, delay_text, fontsize=11, color=INK, wrap=True, transform=ax.transAxes)
    ax.text(0.02, 0.37, "À SURVEILLER", fontsize=9, weight="bold", color=MUTED, transform=ax.transAxes)
    ax.text(0.02, 0.19, "Les attributs produits incomplets sont classés en priorité moyenne. Les commentaires d’avis sont facultatifs et restent hors score.",
            fontsize=10, color=INK, wrap=True, transform=ax.transAxes)
    fig.text(0.055, 0.035, "Source : Olist via Kaggle · données brutes non incluses · détails et licence dans le README.",
             fontsize=8.5, color=MUTED)
    save_chart(fig, args.assets / "dashboard_preview.png")

    print("PNG générés dans", args.assets.resolve())
    for name in ["dashboard_preview.png", "quality_by_table.png", "anomaly_rates.png", "completeness_profile.png"]:
        path = args.assets / name
        print(f"{name}: {path.stat().st_size:,} octets")


if __name__ == "__main__":
    main()
