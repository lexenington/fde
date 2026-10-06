import re

from policy_chunking import chunk_manual

MANUAL = """Savanna Microfinance Ltd. Credit Policy Manual.
Part 4. Individual loans
4.2 Amounts
4.2.1 Maximum amount, first loan
The maximum amount for a first individual loan is GHS 5,000.
4.2.2 Maximum amount, repeat borrowers
The maximum amount for a repeat borrower is GHS 20,000. The officer shall record the repayment history. The branch manager shall countersign the file.
4.3 Tenor
4.3.1 Maximum tenor
The maximum tenor of an individual loan is 12 months.
Part 5. Pricing
5.1 Rates
5.1.1 Interest cap
The interest rate shall not exceed 4.0% per month.
It is charged on a flat basis.
"""


def by_id(chunks):
    return {c["id"]: c for c in chunks}


def test_one_chunk_per_rule_in_order():
    got = chunk_manual(MANUAL)
    assert [c["id"] for c in got] == ["4.2.1", "4.2.2", "4.3.1", "5.1.1"]


def test_every_chunk_carries_its_section_title_and_path():
    c = by_id(chunk_manual(MANUAL))
    assert c["4.2.1"]["section"] == "4.2.1" and c["4.2.1"]["title"] == "Maximum amount, first loan"
    assert c["4.2.1"]["path"] == ["Part 4. Individual loans", "4.2 Amounts"]
    assert c["4.3.1"]["path"] == ["Part 4. Individual loans", "4.3 Tenor"]
    assert c["5.1.1"]["path"] == ["Part 5. Pricing", "5.1 Rates"]


def test_the_text_is_self_describing():
    c = by_id(chunk_manual(MANUAL))
    assert c["4.2.1"]["text"] == "4.2.1 Maximum amount, first loan\nThe maximum amount for a first individual loan is GHS 5,000."
    assert c["5.1.1"]["text"].splitlines()[0] == "5.1.1 Interest cap"


def test_multi_line_bodies_are_kept_together():
    assert by_id(chunk_manual(MANUAL))["5.1.1"]["text"].endswith("It is charged on a flat basis.")


def test_text_before_the_first_rule_is_not_a_chunk():
    assert all("Credit Policy Manual" not in c["text"] for c in chunk_manual(MANUAL))


def test_a_long_rule_is_split_between_sentences_and_headed_each_time():
    got = chunk_manual(MANUAL, max_chars=120)
    parts = [c for c in got if c["section"] == "4.2.2"]
    assert [c["id"] for c in parts] == ["4.2.2#1", "4.2.2#2", "4.2.2#3"]
    for c in parts:
        assert c["text"].startswith("4.2.2 Maximum amount, repeat borrowers\n")
        assert c["text"].endswith("."), "a chunk ended mid-sentence"
        assert len(c["text"]) <= 120


def test_splitting_loses_and_duplicates_nothing():
    sentences = re.findall(r"[^.]+\.", "The maximum amount for a repeat borrower is GHS 20,000. The officer shall record the repayment history. The branch manager shall countersign the file.")
    joined = "\n".join(c["text"] for c in chunk_manual(MANUAL, max_chars=120) if c["section"] == "4.2.2")
    for s in sentences:
        assert joined.count(s.strip()) == 1


def test_packing_is_greedy_so_chunks_are_as_few_as_possible():
    body = " ".join(f"Sentence number {i} is here." for i in range(10))   # 10 sentences of 26 chars, room for 3 per chunk
    text = f"Part 1. A\n1.1 B\n1.1.1 Long rule\n{body}\n"
    got = chunk_manual(text, max_chars=100)
    assert all(len(c["text"]) <= 100 for c in got)
    assert len(got) == 4, f"expected 4 chunks with greedy packing, got {len(got)}"


def test_a_single_sentence_longer_than_the_limit_stays_whole():
    long = "This sentence is very long and goes on " + "and on " * 30 + "until the end."
    got = chunk_manual(f"Part 1. A\n1.1 B\n1.1.1 R\n{long}\n", max_chars=80)
    assert len(got) == 1 and long in got[0]["text"]


def test_a_rule_that_fits_is_not_suffixed():
    assert "4.2.1" in by_id(chunk_manual(MANUAL, max_chars=120))
