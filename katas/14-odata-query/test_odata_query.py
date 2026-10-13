from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from odata_query import all_results, build_query, pad_key, parse_sap_date


def test_nothing_in_nothing_out():
    assert build_query() == {}


def test_filters_are_joined_with_and_and_typed():
    q = build_query([("SoldToParty", "eq", "0010000042"), ("TotalNetAmount", "gt", Decimal("1000.50")), ("DeliveryBlockReason", "eq", None)])
    assert q["$filter"] == "SoldToParty eq '0010000042' and TotalNetAmount gt 1000.50 and DeliveryBlockReason eq null"


def test_quotes_in_strings_are_doubled():
    assert build_query([("Name", "eq", "O'Neil's")])["$filter"] == "Name eq 'O''Neil''s'"


def test_booleans_and_numbers():
    assert build_query([("Flag", "eq", True), ("Qty", "le", 5), ("Ratio", "ge", 0.5)])["$filter"] == "Flag eq true and Qty le 5 and Ratio ge 0.5"


def test_dates_need_the_datetime_wrapper():
    assert build_query([("SalesOrderDate", "ge", date(2026, 10, 1))])["$filter"] == "SalesOrderDate ge datetime'2026-10-01T00:00:00'"
    assert build_query([("CreationDate", "lt", datetime(2026, 10, 1, 13, 5, 9))])["$filter"] == "CreationDate lt datetime'2026-10-01T13:05:09'"


def test_a_bool_is_not_a_number_and_a_date_is_not_a_string():
    # bool is a subclass of int in Python: 'true', never '1'
    assert build_query([("F", "eq", False)])["$filter"] == "F eq false"


def test_contains_is_substringof_in_v2():
    assert build_query([("Name", "contains", "Volta")])["$filter"] == "substringof('Volta',Name)"


def test_the_other_options():
    q = build_query(select=["SalesOrder", "TotalNetAmount"], expand=["to_Item"], orderby=("SalesOrderDate", "desc"), top=20, inline_count=True)
    assert q == {"$select": "SalesOrder,TotalNetAmount", "$expand": "to_Item", "$orderby": "SalesOrderDate desc", "$top": "20", "$inlinecount": "allpages"}
    assert build_query(orderby="SalesOrder")["$orderby"] == "SalesOrder"


@pytest.mark.parametrize("bad", [
    dict(filters=[("A", "like", "x")]),
    dict(filters=[("A b", "eq", "x")]),
    dict(filters=[("A eq 1 or B", "eq", "x")]),
    dict(filters=[("", "eq", "x")]),
    dict(top=0),
    dict(orderby=("A", "sideways")),
])
def test_bad_input_is_refused(bad):
    with pytest.raises(ValueError):
        build_query(**bad)


def test_parse_sap_date():
    assert parse_sap_date("/Date(1789344000000)/") == datetime(2026, 9, 14, tzinfo=timezone.utc)
    assert parse_sap_date("/Date(0)/") == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert parse_sap_date("/Date(-86400000)/") == datetime(1969, 12, 31, tzinfo=timezone.utc)


def test_an_offset_does_not_move_the_instant():
    assert parse_sap_date("/Date(1789344000000+0100)/") == parse_sap_date("/Date(1789344000000)/")
    assert parse_sap_date("/Date(1789344000000-0500)/") == parse_sap_date("/Date(1789344000000)/")


@pytest.mark.parametrize("bad", ["2026-09-14", "/Date()/", "Date(5)", "/Date(abc)/", "", "/Date(1.5)/"])
def test_parse_sap_date_refuses_the_rest(bad):
    with pytest.raises(ValueError):
        parse_sap_date(bad)


@pytest.mark.parametrize("raw", ["12345", "SO 12345", " so-12345 ", "0000012345", "Order #12345"])
def test_pad_key(raw):
    assert pad_key(raw) == "0000012345"


@pytest.mark.parametrize("raw", ["", "none", "SO 12 345", "12345678901", "1-2"])
def test_pad_key_refuses_what_is_not_an_order_number(raw):
    with pytest.raises(ValueError):
        pad_key(raw)


def test_pad_key_width():
    assert pad_key("7", width=4) == "0007"


def pages(*chunks):
    urls = {f"u{i}": {"d": {"results": c, **({"__next": f"u{i + 1}"} if i < len(chunks) - 1 else {})}} for i, c in enumerate(chunks)}
    calls = []

    def get(url):
        calls.append(url)
        return urls[url]
    return get, calls


def test_all_results_follows_next_until_it_stops():
    get, calls = pages([1, 2], [3], [4, 5])
    assert list(all_results(get, "u0")) == [1, 2, 3, 4, 5] and calls == ["u0", "u1", "u2"]


def test_all_results_is_lazy():
    get, calls = pages([1], [2], [3])
    it = all_results(get, "u0")
    assert next(it) == 1 and calls == ["u0"]


def test_an_empty_collection():
    assert list(all_results(lambda u: {"d": {"results": []}}, "u0")) == []


def test_a_server_that_loops_is_caught():
    body = {"d": {"results": [1], "__next": "u0"}}
    calls = []

    def get(url):
        calls.append(url)
        return body
    got = []
    with pytest.raises(RuntimeError, match="(?i)repeat|loop|already"):
        for row in all_results(get, "u0"):
            got.append(row)
    assert got == [1] and calls == ["u0"]


def test_a_runaway_is_capped():
    n = iter(range(10 ** 6))
    calls = []

    def get(url):
        calls.append(url)
        return {"d": {"results": [1], "__next": f"u{next(n)}"}}
    with pytest.raises(RuntimeError, match="(?i)max_pages|too many|pages"):
        list(all_results(get, "start", max_pages=5))
    assert len(calls) == 5
