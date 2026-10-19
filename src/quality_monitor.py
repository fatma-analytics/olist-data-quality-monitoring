from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

TABLE_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

PRIMARY_KEYS = {
    "customers": ["customer_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "orders": ["order_id"],
    "products": ["product_id"],
    "sellers": ["seller_id"],
    "category_translation": ["product_category_name"],
}

SEVERITY_BY_TABLE = {
    "orders": "Critical",
    "order_items": "Critical",
    "order_payments": "High",
    "customers": "High",
    "products": "Medium",
    "sellers": "Medium",
}

OPTIONAL_NULL_FIELDS = {
    ("order_reviews", "review_comment_title"),
    ("order_reviews", "review_comment_message"),
}


def load_tables(data_dir: Path) -> dict[str, pd.DataFrame]:
    tables = {}
    missing = []
    for table, filename in TABLE_FILES.items():
        path = data_dir / filename
        if not path.exists():
            missing.append(str(path))
            continue
        tables[table] = pd.read_csv(path, low_memory=False)
    if missing:
        raise FileNotFoundError("Fichiers CSV manquants : " + ", ".join(missing))
    return tables


def _result(rows: list[dict], *, table: str, rule_id: str, category: str,
            failed: int, total: int, description: str, severity: str = "Low",
            column: str = "", dimensions: str = "", status_override: str | None = None) -> None:
    rate = (100.0 * failed / total) if total else 0.0
    rows.append({
        "table_name": table,
        "column_name": column,
        "rule_id": rule_id,
        "category": category,
        "severity": severity,
        "status": status_override or ("PASS" if failed == 0 else "FAIL"),
        "rows_tested": int(total),
        "rows_failed": int(failed),
        "failure_rate_pct": round(rate, 4),
        "description": description,
        "dimensions": dimensions,
    })


def _parse_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def run_checks(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    checks: list[dict] = []
    columns: list[dict] = []
    order_status = tables["orders"]["order_status"].astype("string").str.strip().str.lower()
    conditional_completeness = {
        ("orders", "order_approved_at"): (
            order_status.isin({"approved", "invoiced", "processing", "shipped", "delivered"}),
            "Date d’approbation requise pour les commandes ayant dépassé le statut créé.", "High"),
        ("orders", "order_delivered_carrier_date"): (
            order_status.eq("delivered"), "Date de remise au transporteur requise pour les commandes livrées.", "High"),
        ("orders", "order_delivered_customer_date"): (
            order_status.eq("delivered"), "Date de livraison client requise pour les commandes livrées.", "High"),
    }
    for table, df in tables.items():
        n = len(df)
        for col in df.columns:
            nulls = int(df[col].isna().sum())
            columns.append({
                "table_name": table,
                "column_name": col,
                "data_type": str(df[col].dtype),
                "rows_tested": n,
                "null_count": nulls,
                "null_rate_pct": round(100.0 * nulls / n, 4) if n else 0.0,
                "distinct_count": int(df[col].nunique(dropna=True)),
            })
            field = (table, col)
            if field in conditional_completeness:
                eligible, description, severity = conditional_completeness[field]
                eligible = eligible.reindex(df.index, fill_value=False)
                tested = int(eligible.sum())
                failed = int(df.loc[eligible, col].isna().sum())
                status_override = None
            elif field in OPTIONAL_NULL_FIELDS:
                tested, failed = n, nulls
                severity = "Low"
                description = f"Champ facultatif ; taux de valeurs manquantes suivi à titre informatif dans {col}."
                status_override = "INFO"
            else:
                tested, failed = n, nulls
                severity = SEVERITY_BY_TABLE.get(table, "Low")
                description = f"Valeurs manquantes dans {col}."
                status_override = None
            _result(checks, table=table, rule_id=f"COMPLETENESS_{col.upper()}",
                    category="Completeness", failed=failed, total=tested,
                    description=description, column=col, severity=severity,
                    status_override=status_override)

        key = PRIMARY_KEYS.get(table)
        if key and all(col in df.columns for col in key):
            duplicate_rows = int(df.duplicated(subset=key, keep=False).sum())
            _result(checks, table=table, rule_id="UNIQUENESS_PRIMARY_KEY",
                    category="Uniqueness", failed=duplicate_rows, total=n,
                    description="La clé primaire déclarée doit être unique : " + ", ".join(key),
                    column=", ".join(key), severity="Critical")

    # Referential integrity across the normalized source tables.
    relations = [
        ("orders", "customer_id", "customers", "customer_id"),
        ("order_items", "order_id", "orders", "order_id"),
        ("order_items", "product_id", "products", "product_id"),
        ("order_items", "seller_id", "sellers", "seller_id"),
        ("order_payments", "order_id", "orders", "order_id"),
        ("order_reviews", "order_id", "orders", "order_id"),
    ]
    for child, child_col, parent, parent_col in relations:
        child_df, parent_df = tables[child], tables[parent]
        values = child_df[child_col]
        parent_values = set(parent_df[parent_col].dropna().astype(str))
        non_null = values.notna()
        missing_fk = int((non_null & ~values.astype(str).isin(parent_values)).sum())
        _result(checks, table=child, rule_id=f"FK_{child_col.upper()}_TO_{parent.upper()}",
                category="Referential integrity", failed=missing_fk, total=int(non_null.sum()),
                description=f"{child}.{child_col} doit exister dans {parent}.{parent_col}.",
                column=child_col, severity="Critical")

    orders = tables["orders"]
    date_rules = [
        ("order_purchase_timestamp", "order_delivered_customer_date", "DATE_DELIVERED_AFTER_PURCHASE",
         "La livraison ne peut pas précéder la commande.", "Critical"),
        ("order_purchase_timestamp", "order_approved_at", "DATE_APPROVED_AFTER_PURCHASE",
         "L’approbation ne devrait pas précéder la commande.", "High"),
        ("order_estimated_delivery_date", "order_delivered_customer_date", "DATE_DELIVERED_VS_ESTIMATE",
         "La livraison après la date estimée est suivie comme retard opérationnel.", "Medium"),
    ]
    for start_col, end_col, rule_id, description, severity in date_rules:
        start, end = _parse_date(orders[start_col]), _parse_date(orders[end_col])
        valid = start.notna() & end.notna()
        failed = int((valid & (end > start if rule_id == "DATE_DELIVERED_VS_ESTIMATE" else end < start)).sum())
        _result(checks, table="orders", rule_id=rule_id, category="Validity", failed=failed,
                total=int(valid.sum()), description=description, column=f"{start_col}, {end_col}",
                severity=severity)

    status_col = orders["order_status"].astype("string").str.strip().str.lower()
    allowed = {"created", "approved", "invoiced", "processing", "shipped", "delivered", "unavailable", "canceled"}
    invalid = status_col.notna() & ~status_col.isin(allowed)
    _result(checks, table="orders", rule_id="DOMAIN_ORDER_STATUS", category="Validity",
            failed=int(invalid.sum()), total=int(status_col.notna().sum()),
            description="Le statut doit appartenir au domaine métier documenté.",
            column="order_status", severity="High")

    for table, col in [("order_items", "price"), ("order_items", "freight_value"),
                       ("order_payments", "payment_value")]:
        values = pd.to_numeric(tables[table][col], errors="coerce")
        invalid = values.notna() & (values < 0)
        _result(checks, table=table, rule_id=f"NON_NEGATIVE_{col.upper()}", category="Validity",
                failed=int(invalid.sum()), total=int(values.notna().sum()),
                description=f"{col} ne doit pas être négatif.", column=col, severity="High")

    geo = tables["geolocation"]
    for col, low, high in [("geolocation_lat", -90, 90), ("geolocation_lng", -180, 180)]:
        values = pd.to_numeric(geo[col], errors="coerce")
        invalid = values.notna() & ~values.between(low, high)
        _result(checks, table="geolocation", rule_id=f"RANGE_{col.upper()}", category="Validity",
                failed=int(invalid.sum()), total=int(values.notna().sum()),
                description=f"{col} doit être compris entre {low} et {high}.",
                column=col, severity="Medium")

    products = tables["products"]
    for col in ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]:
        values = pd.to_numeric(products[col], errors="coerce")
        invalid = values.notna() & (values < 0)
        _result(checks, table="products", rule_id=f"NON_NEGATIVE_{col.upper()}", category="Validity",
                failed=int(invalid.sum()), total=int(values.notna().sum()),
                description=f"{col} ne doit pas être négatif.", column=col, severity="Medium")

    checks_df = pd.DataFrame(checks)
    columns_df = pd.DataFrame(columns)
    return checks_df, columns_df


def build_outputs(data_dir: Path, out_dir: Path) -> dict[str, pd.DataFrame]:
    tables = load_tables(data_dir)
    checks, columns = run_checks(tables)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks.to_csv(out_dir / "check_results.csv", index=False)
    columns.to_csv(out_dir / "column_quality.csv", index=False)

    table_rows = []
    for table, df in tables.items():
        subset = checks[(checks.table_name == table) & (checks.status != "INFO")]
        score = 100.0 * (1.0 - subset.failure_rate_pct.mean() / 100.0) if len(subset) else 100.0
        failed = int((subset.status == "FAIL").sum())
        table_rows.append({
            "table_name": table,
            "row_count": len(df),
            "column_count": len(df.columns),
            "checks_total": len(subset),
            "checks_failed": failed,
            "quality_score_pct": round(max(0.0, score), 2),
            "null_cells": int(df.isna().sum().sum()),
        })
    table_quality = pd.DataFrame(table_rows).sort_values("quality_score_pct")
    table_quality.to_csv(out_dir / "table_quality.csv", index=False)

    issues = checks.loc[checks.status == "FAIL"].copy()
    issues.insert(0, "issue_id", [f"DQ-{i:04d}" for i in range(1, len(issues) + 1)])
    issues.to_csv(out_dir / "quality_issues.csv", index=False)

    total_checks = len(checks)
    failed_checks = int((checks.status == "FAIL").sum())
    summary = pd.DataFrame([{
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tables_monitored": len(tables),
        "rows_profiled": int(sum(len(df) for df in tables.values())),
        "checks_total": total_checks,
        "checks_failed": failed_checks,
        "issues_open": len(issues),
        "overall_quality_score_pct": round(float(table_quality.quality_score_pct.mean()), 2),
    }])
    summary.to_csv(out_dir / "run_summary.csv", index=False)
    return {"summary": summary, "tables": table_quality, "checks": checks,
            "columns": columns, "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(description="Profilage et monitoring de qualité des données Olist.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    result = build_outputs(args.data_dir, args.out_dir)
    summary = result["summary"].iloc[0]
    print(f"Contrôle terminé : {summary['tables_monitored']} tables, "
          f"{summary['checks_total']} contrôles, {summary['issues_open']} anomalies.")
    print(f"Score moyen de qualité : {summary['overall_quality_score_pct']} %")
    print(f"Résultats : {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
