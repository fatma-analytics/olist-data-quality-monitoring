from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
st.set_page_config(page_title="Suivi qualité des données", page_icon="DQ", layout="wide")
st.title("Monitoring BI · Qualité des données")
st.caption("Olist Brazilian E-Commerce · suivi des contrôles, anomalies et complétude")

required = ["run_summary.csv", "table_quality.csv", "quality_issues.csv", "column_quality.csv", "check_results.csv"]
missing = [name for name in required if not (OUTPUTS / name).exists()]
if missing:
    st.warning("Aucun résultat complet détecté. Depuis la racine du projet, lancez `python src/quality_monitor.py`.")
    st.stop()

summary = pd.read_csv(OUTPUTS / "run_summary.csv").iloc[0]
tables = pd.read_csv(OUTPUTS / "table_quality.csv")
issues = pd.read_csv(OUTPUTS / "quality_issues.csv")
columns = pd.read_csv(OUTPUTS / "column_quality.csv")
checks = pd.read_csv(OUTPUTS / "check_results.csv")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Score qualité moyen", f"{summary.overall_quality_score_pct:.1f} %")
c2.metric("Tables suivies", f"{int(summary.tables_monitored)}")
c3.metric("Contrôles en échec", f"{int(summary.checks_failed)} / {int(summary.checks_total)}")
c4.metric("Anomalies ouvertes", f"{int(summary.issues_open)}")
st.caption(f"Dernière exécution UTC : {summary.generated_at_utc} · {int(summary.rows_profiled):,} lignes profilées")

left, right = st.columns([1.15, 1])
with left:
    st.subheader("Qualité par table")
    fig = px.bar(tables.sort_values("quality_score_pct"), x="quality_score_pct", y="table_name", color="quality_score_pct",
                 color_continuous_scale=["#d95f59", "#f0b44d", "#49a078"], range_color=(0, 100),
                 labels={"quality_score_pct": "Score (%)", "table_name": "Table"}, orientation="h")
    fig.update_layout(coloraxis_showscale=False, xaxis_range=[0, 100], height=410, margin=dict(l=10, r=10, t=15, b=10))
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Anomalies par catégorie")
    if issues.empty:
        st.success("Aucune anomalie détectée selon les règles exécutées.")
    else:
        counts = issues.groupby(["category", "severity"], as_index=False).size().rename(columns={"size": "anomalies"})
        fig = px.bar(counts, x="category", y="anomalies", color="severity", barmode="stack",
                     color_discrete_map={"Critical": "#8f1d2c", "High": "#d95f59", "Medium": "#f0b44d", "Low": "#4d79a8"},
                     labels={"category": "Type de contrôle", "anomalies": "Règles en échec", "severity": "Priorité"})
        fig.update_layout(height=410, margin=dict(l=10, r=10, t=15, b=10), xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Anomalies à examiner")
if issues.empty:
    st.info("La liste est vide pour cette exécution.")
else:
    filter_options = ["Toutes"] + sorted(issues["severity"].dropna().unique().tolist())
    severity = st.selectbox("Filtrer par priorité", filter_options)
    shown = issues if severity == "Toutes" else issues[issues.severity == severity]
    display_cols = ["issue_id", "table_name", "rule_id", "category", "severity", "rows_failed", "failure_rate_pct", "description"]
    st.dataframe(shown[display_cols], use_container_width=True, hide_index=True)

st.subheader("Complétude des colonnes")
threshold = st.slider("Afficher les colonnes avec au moins ce taux de valeurs manquantes", 0.0, 100.0, 0.1, 0.1)
nulls = columns[columns.null_rate_pct >= threshold].sort_values("null_rate_pct", ascending=False)
if nulls.empty:
    st.success("Aucune colonne ne dépasse le seuil choisi.")
else:
    fig = px.bar(nulls.head(30), x="null_rate_pct", y="table_name", color="null_rate_pct", facet_col="table_name",
                 hover_name="column_name", hover_data=["null_count", "distinct_count"], orientation="h",
                 color_continuous_scale=["#e9f1ed", "#f0b44d", "#d95f59"],
                 labels={"null_rate_pct": "Valeurs manquantes (%)", "table_name": "Table"})
    fig.update_layout(showlegend=False, height=390, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(nulls[["table_name", "column_name", "rows_tested", "null_count", "null_rate_pct", "distinct_count"]],
                 use_container_width=True, hide_index=True)

with st.expander("Détail des contrôles exécutés"):
    st.dataframe(checks, use_container_width=True, hide_index=True)
