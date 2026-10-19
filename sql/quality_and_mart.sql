-- Lancer depuis la racine du dépôt avec DuckDB.
-- Les CSV bruts sont téléchargés localement dans data/raw/ et ne sont pas versionnés.

CREATE OR REPLACE VIEW stg_orders AS
SELECT * FROM read_csv_auto('data/raw/olist_orders_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_customers AS
SELECT * FROM read_csv_auto('data/raw/olist_customers_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_order_items AS
SELECT * FROM read_csv_auto('data/raw/olist_order_items_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_order_payments AS
SELECT * FROM read_csv_auto('data/raw/olist_order_payments_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_order_reviews AS
SELECT * FROM read_csv_auto('data/raw/olist_order_reviews_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_products AS
SELECT * FROM read_csv_auto('data/raw/olist_products_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_sellers AS
SELECT * FROM read_csv_auto('data/raw/olist_sellers_dataset.csv', header = true);
CREATE OR REPLACE VIEW stg_category_translation AS
SELECT * FROM read_csv_auto('data/raw/product_category_name_translation.csv', header = true);

-- Fait de commande au grain commande : les agrégations évitent le fan-out entre lignes,
-- paiements et avis avant la jointure.
CREATE OR REPLACE VIEW mart_orders AS
WITH item_totals AS (
    SELECT order_id,
           COUNT(*) AS item_count,
           SUM(price) AS merchandise_value,
           SUM(freight_value) AS freight_value
    FROM stg_order_items
    GROUP BY order_id
), payment_totals AS (
    SELECT order_id,
           SUM(payment_value) AS payment_value,
           COUNT(*) AS payment_count
    FROM stg_order_payments
    GROUP BY order_id
), review_totals AS (
    SELECT order_id,
           AVG(review_score) AS average_review_score,
           COUNT(*) AS review_count
    FROM stg_order_reviews
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    i.item_count,
    i.merchandise_value,
    i.freight_value,
    p.payment_value,
    p.payment_count,
    r.average_review_score,
    r.review_count
FROM stg_orders AS o
LEFT JOIN stg_customers AS c USING (customer_id)
LEFT JOIN item_totals AS i USING (order_id)
LEFT JOIN payment_totals AS p USING (order_id)
LEFT JOIN review_totals AS r USING (order_id);

-- Résultats des principaux contrôles référentiels pour l’exploration SQL.
CREATE OR REPLACE VIEW dq_referential_checks AS
SELECT 'order_items.order_id -> orders.order_id' AS check_name,
       COUNT(*) FILTER (WHERE o.order_id IS NULL) AS failed_rows
FROM stg_order_items i LEFT JOIN stg_orders o USING (order_id)
UNION ALL
SELECT 'orders.customer_id -> customers.customer_id',
       COUNT(*) FILTER (WHERE c.customer_id IS NULL)
FROM stg_orders o LEFT JOIN stg_customers c USING (customer_id)
UNION ALL
SELECT 'order_items.product_id -> products.product_id',
       COUNT(*) FILTER (WHERE p.product_id IS NULL)
FROM stg_order_items i LEFT JOIN stg_products p USING (product_id)
UNION ALL
SELECT 'order_items.seller_id -> sellers.seller_id',
       COUNT(*) FILTER (WHERE s.seller_id IS NULL)
FROM stg_order_items i LEFT JOIN stg_sellers s USING (seller_id);

-- Exemples d’inspection :
-- SELECT * FROM dq_referential_checks;
-- SELECT order_status, COUNT(*) FROM mart_orders GROUP BY 1 ORDER BY 2 DESC;
