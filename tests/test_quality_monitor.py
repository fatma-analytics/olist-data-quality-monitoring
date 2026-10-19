import pandas as pd

from src.quality_monitor import run_checks


def test_missing_values_and_duplicate_primary_key_are_detected():
    tables = {
        "customers": pd.DataFrame({"customer_id": ["c1", "c1"], "city": [None, "Recife"]}),
        "order_items": pd.DataFrame({"order_id": [], "order_item_id": [], "product_id": [], "seller_id": [],
                                      "price": [], "freight_value": []}),
        "order_payments": pd.DataFrame({"order_id": [], "payment_sequential": [], "payment_value": []}),
        "orders": pd.DataFrame({"order_id": [], "customer_id": [], "order_status": [],
                                "order_purchase_timestamp": [], "order_approved_at": [],
                                "order_delivered_customer_date": [], "order_estimated_delivery_date": []}),
        "products": pd.DataFrame({"product_id": [], "product_weight_g": [], "product_length_cm": [],
                                  "product_height_cm": [], "product_width_cm": []}),
        "sellers": pd.DataFrame({"seller_id": []}),
        "category_translation": pd.DataFrame({"product_category_name": []}),
        "order_reviews": pd.DataFrame({"order_id": []}),
        "geolocation": pd.DataFrame({"geolocation_lat": [], "geolocation_lng": []}),
    }
    checks, columns = run_checks(tables)
    assert ((checks.table_name == "customers") & (checks.rule_id == "UNIQUENESS_PRIMARY_KEY") & (checks.rows_failed == 2)).any()
    assert ((checks.table_name == "customers") & (checks.column_name == "city") & (checks.rows_failed == 1)).any()
    assert ((columns.table_name == "customers") & (columns.column_name == "city") & (columns.null_count == 1)).any()
