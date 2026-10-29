# Intelligent SQL Optimizer — Review 2 Gap Report

Generated 2026-04-30. Compares the implemented code against the 9 objectives in the
two Review 2 report PDFs (`review 2 dbs project.pdf`, `dbms review 2 new.pdf`).

## Test run results (fresh, this session)

| Check | Result |
|-------|--------|
| `pytest tests/` (22 tests) | all pass |
| `demo.py` end-to-end | pass, records observed plans as feedback |
| `ml/train.py` | trains all 4 models; XGBoost R² 0.932, Gradient Boosting R² 0.929 |
| `evaluate_selection.py` live | 87.91% plan-selection accuracy over 91 held-out queries |
| `feedback.py retrain` | idempotent merge + retrain of all 4 models |

## Bugs fixed this session

- `demo.py`, `evaluate_selection.py`, `collect_dataset.py`, `ml/train.py` crashed on
  Windows with `UnicodeEncodeError` because their console output used non-ASCII arrows
  (`← →`). Replaced with ASCII `->` so the scripts run under the default cp1252 console.

## Objective-by-objective status

| # | Objective | Status | Notes |
|---|-----------|--------|-------|
| 1 | PostgreSQL environment for testing | Done | `database/schema.sql`, `seed.sql`; 4 tables seeded |
| 2 | Generate tables + SQL queries | Done | 451-query workload in `workload/queries.py` |
| 3 | Collect plans via EXPLAIN / EXPLAIN ANALYZE | Done | `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` in `optimizer/executor.py` |
| 4 | Extract query + plan features | Done | `sql_parser.py` (7 query feats), `plan_parser.py` (18 plan feats), `feature_extraction.py` |
| 5 | Train models to predict execution time | Done | All four models live: Linear Regression, Random Forest, Gradient Boosting, XGBoost. `ml/train.py` trains every model, prints and saves each metric to `data/ml_results.csv` (R²: LR 0.97, RF 0.90, GB 0.93, XGB 0.93). |
| 6 | Compare ML method vs PostgreSQL normal optimizer | Done | `default` candidate is the PG baseline; `evaluate_selection.py` + `plan_selection_results.csv` |
| 7 | Store actual results as feedback | Done | `database/feedback.sql` + `optimizer/feedback.py`: `record_feedback` / `read_feedback` / `feedback_summary`, a bulk `collect_feedback` loop, and an idempotent `feedback_to_dataset` merge that refreshes one row per query + candidate and recomputes the comparison columns. `feedback.py retrain` merges feedback and retrains all four models. Dashboard has a dedicated "Feedback & Retraining" page; `demo.py` records observed results automatically. |
| 8 | Measure prediction error + execution time | Done | MAE/RMSE/R² in `train.py`; `actual_runtime_ms`, `runtime_samples_ms`, `runtime_gap_ms` in the dataset |
| 9 | Show results in tables/graphs/dashboard | Done | `dashboard.py` (3 pages, Streamlit) + `data/*.csv` |

## Gaps to close before Review 2 submission

1. **Model is not demonstrably beating PostgreSQL on most queries.** PG's cost estimator
   already picks the actually-fastest plan 84.7% of the time on this workload (its cost
   ranks at Spearman ρ ≈ 0.85 with real runtime). The candidate space is small — 3
   join-method toggles — so in ~46% of multi-candidate queries PG is already optimal and
   there is nothing for ML to improve. Where a faster alternative *does* exist
   (no_hash_join on the customers/orders joins, 30–45% faster), the model usually finds
   it. The honest framing for Review 2: ML roughly matches PG's default (now 87.9%
   selection accuracy over 91 held-out queries, up from 86.8%) and occasionally exceeds
   it; the value shows up on the minority of queries where PG's cost estimate misranks
   the candidates. More candidate diversity (e.g. index/work_mem/join-order settings)
   would widen the space ML can actually win in.

## Review 3 ready-state

- `README.md` already lists Review 3 work (larger workload, workload-aware split, XGBoost
  tuning, feedback + retraining, baseline benchmarking, dashboard, improvement metrics).
- The split in `train.py`/`evaluate_selection.py` is already group-based on `query_id`,
  so the "workload-aware split" Review 3 item is effectively in place.
- `database/seed.sql` header says "Increase the multipliers later for Review 3" — the
  current seed is small (10k customers, 100k orders), which is why most plans are
  sub-10 ms and the improvement headroom is narrow.
