"""Kata 12: five queries a customer's data always needs.

Write each as a SQL string for SQLite (3.25+: window functions and ON CONFLICT upserts both work). The schema is
in test_queries.py. Named parameters look like :today.
"""

# One row per customer that has at least one order: (customer_id, order_id, placed_on) for their LATEST order.
# If two orders share the latest date, take the one with the higher id. Sorted by customer_id.
LATEST_ORDER_PER_CUSTOMER = ""

# Customers with no order in the last :days days up to and including :today (an order exactly :days days ago
# still counts as recent). Customers who never ordered are inactive too. Columns: (customer_id), sorted.
INACTIVE_CUSTOMERS = ""

# A ledger per customer: orders add `total_ghs` and payments subtract `amount_ghs`. One row per order or payment:
# (customer_id, on_date, delta, balance) where balance is the running total so far for that customer.
# Order rows by customer_id, on_date; on the same day, orders come before payments, then by id.
RUNNING_BALANCE = ""

# Emails that appear more than once once you ignore case and surrounding spaces: (email_key, n) where email_key is
# the lowercased, trimmed email. Sorted by email_key.
DUPLICATE_EMAILS = ""

# Insert a customer with :email, :name, :created. If the email already exists (exact match), update the name only:
# keep the original `created` date.
UPSERT_CUSTOMER = ""
