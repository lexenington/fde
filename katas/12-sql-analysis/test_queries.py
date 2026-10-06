import sqlite3

import pytest

import queries

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, email TEXT, name TEXT, created TEXT);
CREATE UNIQUE INDEX customers_email ON customers (email);          -- exact match: 'A@x.com' and 'a@x.com' are different here
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, placed_on TEXT, total_ghs REAL);
CREATE TABLE payments (id INTEGER PRIMARY KEY, customer_id INTEGER, paid_on TEXT, amount_ghs REAL);
"""


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.executemany("INSERT INTO customers VALUES (?,?,?,?)", [
        (1, "ama@x.com", "Ama", "2026-01-01"), (2, "kofi@x.com", "Kofi", "2026-01-02"), (3, "Kofi@X.com ", "Kofi M", "2026-02-01"),
        (4, "esi@x.com", "Esi", "2026-03-01"), (5, "yaw@x.com", "Yaw", "2026-03-02"),
    ])
    c.executemany("INSERT INTO orders VALUES (?,?,?,?)", [
        (1, 1, "2026-09-01", 100), (2, 1, "2026-09-20", 250), (3, 2, "2026-05-01", 80), (4, 2, "2026-05-01", 90), (5, 4, "2026-10-01", 60),
    ])
    c.executemany("INSERT INTO payments VALUES (?,?,?,?)", [(1, 1, "2026-09-05", 100), (2, 1, "2026-09-20", 50), (3, 4, "2026-10-03", 20)])
    yield c
    c.close()


def test_latest_order_per_customer(db):
    assert db.execute(queries.LATEST_ORDER_PER_CUSTOMER).fetchall() == [(1, 2, "2026-09-20"), (2, 4, "2026-05-01"), (4, 5, "2026-10-01")]


def test_inactive_customers(db):
    got = db.execute(queries.INACTIVE_CUSTOMERS, {"today": "2026-10-06", "days": 90}).fetchall()
    assert got == [(2,), (3,), (5,)]


def test_inactive_boundary_is_inclusive(db):
    # 2026-09-20 is exactly 16 days before 2026-10-06: customer 1 is recent at 16 days, not at 15
    assert (1,) not in db.execute(queries.INACTIVE_CUSTOMERS, {"today": "2026-10-06", "days": 16}).fetchall()
    assert (1,) in db.execute(queries.INACTIVE_CUSTOMERS, {"today": "2026-10-06", "days": 15}).fetchall()


def test_running_balance(db):
    got = db.execute(queries.RUNNING_BALANCE).fetchall()
    assert got == [
        (1, "2026-09-01", 100.0, 100.0), (1, "2026-09-05", -100.0, 0.0), (1, "2026-09-20", 250.0, 250.0), (1, "2026-09-20", -50.0, 200.0),
        (2, "2026-05-01", 80.0, 80.0), (2, "2026-05-01", 90.0, 170.0),
        (4, "2026-10-01", 60.0, 60.0), (4, "2026-10-03", -20.0, 40.0),
    ]


def test_duplicate_emails_ignore_case_and_spaces(db):
    assert db.execute(queries.DUPLICATE_EMAILS).fetchall() == [("kofi@x.com", 2)]


def test_upsert_inserts_then_updates_only_the_name(db):
    db.execute(queries.UPSERT_CUSTOMER, {"email": "new@x.com", "name": "New", "created": "2026-10-01"})
    db.execute(queries.UPSERT_CUSTOMER, {"email": "new@x.com", "name": "Renamed", "created": "2099-01-01"})
    rows = db.execute("SELECT email, name, created FROM customers WHERE email = 'new@x.com'").fetchall()
    assert rows == [("new@x.com", "Renamed", "2026-10-01")]


def test_upsert_treats_a_differently_cased_email_as_a_different_customer(db):
    db.execute(queries.UPSERT_CUSTOMER, {"email": "AMA@x.com", "name": "Ama 2", "created": "2026-10-01"})
    assert db.execute("SELECT count(*) FROM customers WHERE lower(email) = 'ama@x.com'").fetchone()[0] == 2
