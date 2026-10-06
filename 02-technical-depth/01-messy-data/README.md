# 02/01 — Messy data

**Prove it (skip if yes):** Given two CSVs of customers with no shared ID, inconsistent phone/name formats and duplicates, can you produce a merged table *plus a report saying how confident each match is and which records need a human* in under 2 hours?

## Why this matters for FDEs

Week one at almost every customer goes like this: "Here's an export from our CRM, here's billing, and here's the spreadsheet ops actually uses." They disagree about what a customer is. Your AI agent, dashboard or automation is only as good as the join. The FDE skill isn't pandas syntax. It's three habits:

1. **Profile before you transform.** Count nulls, distinct values and format variants *per column, per source*, then show the customer.
2. **Make every decision explicit and reversible.** Raw → staged → modelled layers. Never mutate raw.
3. **Report uncertainty.** "We matched 94% automatically, 4% need review (list attached), 2% are probably junk." Customers trust numbers more than they trust "it's done".

## Concepts to learn

| Concept | What to know | Resource |
|---|---|---|
| Layered modelling | raw / staging / marts; why dbt popularised it | dbt docs: "How we structure our dbt projects" |
| Entity resolution | Blocking, pairwise scoring, thresholds, transitive closure (union-find) | *Data Matching*, Peter Christen (ch. 1–4) |
| Normalisation | E.164 phone numbers, Unicode NFKC, case folding, name tokens | `phonenumbers` lib docs |
| Data quality checks | Uniqueness, not-null, referential integrity, freshness | Great Expectations / dbt tests concepts |
| SQL for analysis | Window functions, CTEs, `DISTINCT ON`, `GROUP BY ... HAVING` | Mode SQL tutorial (advanced section) |
| Warehouses | Snowflake/BigQuery/Databricks basics: what a "share" is, cost model | Each vendor's quickstart |
| Incremental loads | CDC, watermarks, upserts (`ON CONFLICT`) | Postgres docs: INSERT … ON CONFLICT |
| Pipeline orchestration | DAGs, schedules, retries, backfills, idempotent tasks, alerting on failure. Customers' data teams usually already run Airflow (or Dagster/Prefect); your job is to add a DAG or debug a failed run, not to pick a new tool | Airflow docs: "Fundamental concepts" + "Best practices" |
| Distributed processing | When data outgrows one machine: Spark DataFrames, partitioning, why shuffles are expensive. Know when DuckDB/Polars on one box is enough (usually, at West African enterprise scale) | Spark docs: "Quick start"; DuckDB docs |

## Lab: "Kumasi Fresh Foods" customer reconciliation

A (fictional) food distributor wants an AI agent that answers customer account questions over WhatsApp. Before any AI, they need **one customer record per real customer**. They've given you three exports.

```powershell
cd 02-technical-depth/01-messy-data/lab
python make_messy_data.py          # writes data/crm.csv, data/billing.json, data/ops_sheet.csv + .truth/
```

- `crm.csv`: from their CRM. Names with titles, emails sometimes uppercase, phones in mixed formats.
- `billing.json`: from billing. Has `account_no`, company names, MoMo numbers.
- `ops_sheet.csv`: the spreadsheet the delivery team actually uses. Nicknames, typos, landmarks instead of addresses.
- Prefer the Console: **01 Messy data** (http://localhost:3300/labs/messy-data) scores `lab/out/clusters.json` like `check.py`, logs every score with your note, and shows the raw rows of your wrong and missed merges.
- `.truth/clusters.json`: **don't open it.** It's the hidden ground truth `check.py` scores you against.

### Your deliverables

1. `SCOPE.md`: half a page. What's the success metric? What's out of scope?
2. `profile.md`: per-source column profile (nulls, distinct counts, format variants). Generate it with code.
3. `pipeline/`: your code. Load raw into Postgres (`docker run -e POSTGRES_PASSWORD=pw -p 5432:5432 postgres:16`), normalise, match, cluster.
4. `out/clusters.json`: `[{"customer_id": "...", "members": ["crm:12", "billing:A-0031", "ops:7"]}, ...]` in the same shape as the truth file.
5. `out/review_queue.csv`: pairs you weren't confident about, with your score and the reason.
6. `REPORT.md`: one page *written for the customer's ops manager*, not for an engineer.

### Score yourself

```powershell
python check.py out/clusters.json
```

It reports pairwise precision, recall and F1 against the truth. **Target: F1 ≥ 0.92**, with the review queue under 10% of records. Then ask yourself whether you'd rather have a false merge (two customers' balances combined) or a missed merge. Write the answer in REPORT.md. That trade-off conversation is the FDE part.

### Stretch

- Make the load **incremental**: re-run the generator with `--seed 2 --append` and upsert without duplicating.
- Add dbt-style tests (uniqueness of `customer_id`, every source row assigned exactly once).
- Run the pipeline as an **Airflow DAG** (the official `docker compose` quickstart is enough): one task per stage, retries, and a nightly schedule. Then break one task on purpose and practise the FDE job: read the logs, fix it, backfill the missed runs without creating duplicate customers.
