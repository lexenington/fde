LATEST_ORDER_PER_CUSTOMER = """
SELECT customer_id, id AS order_id, placed_on FROM (
  SELECT customer_id, id, placed_on,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY placed_on DESC, id DESC) AS rn
  FROM orders)
WHERE rn = 1 ORDER BY customer_id"""

INACTIVE_CUSTOMERS = """
SELECT c.id AS customer_id FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.placed_on >= date(:today, '-' || :days || ' days'))
ORDER BY c.id"""

RUNNING_BALANCE = """
WITH ledger AS (
  SELECT customer_id, placed_on AS on_date, total_ghs AS delta, 0 AS kind, id FROM orders
  UNION ALL
  SELECT customer_id, paid_on, -amount_ghs, 1, id FROM payments)
SELECT customer_id, on_date, delta,
       SUM(delta) OVER (PARTITION BY customer_id ORDER BY on_date, kind, id ROWS UNBOUNDED PRECEDING) AS balance
FROM ledger ORDER BY customer_id, on_date, kind, id"""

DUPLICATE_EMAILS = """
SELECT lower(trim(email)) AS email_key, COUNT(*) AS n FROM customers GROUP BY email_key HAVING n > 1 ORDER BY email_key"""

UPSERT_CUSTOMER = """
INSERT INTO customers (email, name, created) VALUES (:email, :name, :created)
ON CONFLICT(email) DO UPDATE SET name = excluded.name"""
