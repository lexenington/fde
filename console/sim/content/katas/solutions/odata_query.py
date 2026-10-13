import re
from datetime import date, datetime, timezone
from decimal import Decimal

_OPS = {"eq", "ne", "gt", "ge", "lt", "le"}
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _field(name):
    if not isinstance(name, str) or not _IDENT.match(name):
        raise ValueError(f"not a plain property name: {name!r}")
    return name


def _literal(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime):
        return f"datetime'{v.strftime('%Y-%m-%dT%H:%M:%S')}'"
    if isinstance(v, date):
        return f"datetime'{v.isoformat()}T00:00:00'"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    raise ValueError(f"cannot express {type(v).__name__} in a filter")


def build_query(filters=(), *, select=None, orderby=None, top=None, expand=None, inline_count=False):
    q, terms = {}, []
    for field, op, value in filters:
        f = _field(field)
        if op == "contains":
            terms.append(f"substringof({_literal(str(value))},{f})")
        elif op in _OPS:
            terms.append(f"{f} {op} {_literal(value)}")
        else:
            raise ValueError(f"unknown operator {op!r}")
    if terms:
        q["$filter"] = " and ".join(terms)
    if select:
        q["$select"] = ",".join(_field(x) for x in select)
    if expand:
        q["$expand"] = ",".join(_field(x) for x in expand)
    if orderby:
        f, direction = (orderby, "asc") if isinstance(orderby, str) else orderby
        if direction not in ("asc", "desc"):
            raise ValueError("direction must be asc or desc")
        q["$orderby"] = _field(f) if direction == "asc" and isinstance(orderby, str) else f"{_field(f)} {direction}"
    if top is not None:
        if not isinstance(top, int) or top < 1:
            raise ValueError("top must be 1 or more")
        q["$top"] = str(top)
    if inline_count:
        q["$inlinecount"] = "allpages"
    return q


def parse_sap_date(raw):
    m = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", raw or "")
    if not m:
        raise ValueError(f"not an OData date: {raw!r}")
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc)


def pad_key(raw, width=10):
    runs = re.findall(r"\d+", raw or "")
    if len(runs) != 1:
        raise ValueError(f"expected one run of digits in {raw!r}")
    if len(runs[0]) > width:
        raise ValueError("too long to be a key")
    return runs[0].zfill(width)


def all_results(get_json, url, max_pages=1000):
    seen = set()
    for _ in range(max_pages):
        if url in seen:
            raise RuntimeError(f"the server repeated a page it already sent: {url}")
        seen.add(url)
        d = get_json(url)["d"]
        yield from d["results"]
        url = d.get("__next")
        if not url:
            return
    raise RuntimeError(f"more than max_pages={max_pages} pages")
