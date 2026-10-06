import csv
import json

import pytest

from sim import config, messy

TRUTH = [{"customer_id": "C1", "members": ["crm:1", "billing:1", "ops:2"]}, {"customer_id": "C2", "members": ["crm:2", "ops:3"]},
         {"customer_id": "JUNK-crm-9", "members": ["crm:9"]}]


@pytest.fixture
def lab():
    d = config.LABS_DIR / "01-messy-data" / "lab"
    (d / ".truth").mkdir(parents=True)
    (d / "data").mkdir()
    (d / "out").mkdir()
    (d / ".truth" / "clusters.json").write_text(json.dumps(TRUTH))
    with (d / "data" / "crm.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["crm_id", "full_name"]); w.writeheader()
        w.writerows([{"crm_id": i, "full_name": f"Name {i}"} for i in (1, 2, 9)])
    (d / "data" / "billing.json").write_text(json.dumps([{"account_no": 1, "company": "Acme"}]))
    with (d / "data" / "ops_sheet.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["row", "Customer"]); w.writeheader()
        w.writerows([{"row": 2, "Customer": "acme"}, {"row": 3, "Customer": "n2"}])
    return d


def predict(lab, clusters):
    (lab / "out" / "clusters.json").write_text(json.dumps([{"members": m} for m in clusters]))


def test_a_perfect_answer_scores_one_and_is_logged(lab):
    predict(lab, [c["members"] for c in TRUTH])
    r = messy.score("exact")
    assert r["f1"] == 1.0 and r["passed"] and r["false_merges"] == [] and r["missed"] == []
    assert len(messy.history()) == 1 and messy.history()[0]["note"] == "exact"


def test_errors_come_back_with_the_raw_rows_but_the_log_does_not_store_them(lab):
    predict(lab, [["crm:1", "billing:1"], ["ops:2", "crm:2", "ops:3"], ["crm:9"]])   # misses ops:2 for C1, wrongly merges ops:2 into C2
    r = messy.score()
    assert r["recall"] < 1 and r["precision"] < 1 and not r["passed"]
    pair = r["false_merges"][0]["pair"]
    assert {x["id"] for x in pair} <= {"ops:2", "crm:2", "ops:3"} and all(x["row"] for x in pair)
    assert "false_merges" not in messy.history()[0]


def test_junk_merges_unknown_and_duplicate_ids_are_reported(lab):
    predict(lab, [["crm:1", "crm:9"], ["crm:1", "billing:1", "zzz:1"]])
    r = messy.score()
    assert r["junk_merged"] == ["crm:9"] and r["unknown_ids"] == ["zzz:1"] and r["in_multiple_clusters"] == ["crm:1"]
    assert r["unassigned"] == 3


def test_helpful_errors_when_not_ready(lab):
    with pytest.raises(messy.NotReady, match="clusters.json"):
        messy.score()
    (lab / "out" / "clusters.json").write_text("not json")
    with pytest.raises(messy.NotReady, match="shape"):
        messy.score()
    (lab / ".truth" / "clusters.json").unlink()
    with pytest.raises(messy.NotReady, match="make_messy_data"):
        messy.score()
    assert messy.status()["data_ready"] is False
