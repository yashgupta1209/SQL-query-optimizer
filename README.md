# Intelligent SQL Query Optimizer — Review 2 Prototype

This is the first implementation milestone for the project described in the Review 1 document.

## Review 2 objective

Demonstrate a working prototype:

SQL query
→ SQL analysis
→ PostgreSQL EXPLAIN JSON
→ candidate-plan generation
→ plan feature extraction
→ candidate execution
→ actual runtime dataset
→ preliminary ML runtime prediction.

The complete feedback/retraining mechanism, large workload evaluation, tuning, and dashboard are intentionally left for Review 3.

## 1. Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Configure PostgreSQL

Copy `.env.example` to `.env` and fill in the PostgreSQL password.

Create the database:

```sql
CREATE DATABASE sql_optimizer;
```

Then:

```bash
psql -U postgres -d sql_optimizer -f database/schema.sql
psql -U postgres -d sql_optimizer -f database/seed.sql
```

## 3. Test EXPLAIN + candidate generation

```bash
python -c "from optimizer.candidate_generator import generate_candidates; print([(x['candidate_name'], x['root_node']) for x in generate_candidates('SELECT c.city, COUNT(*) FROM customers c JOIN orders o ON c.customer_id=o.customer_id GROUP BY c.city')])"
```

You want to see multiple plan candidates where PostgreSQL can produce them.

## 4. Generate Review 2 dataset

```bash
python collect_dataset.py
```

Output:

`data/query_plan_dataset.csv`

## 5. Train the models

```bash
python ml/train.py
```

This creates:

- `ml/models/linear_regression.joblib`
- `ml/models/random_forest.joblib`
- `ml/models/gradient_boosting.joblib`
- `ml/models/xgboost_runtime.joblib`

and writes `data/ml_results.csv` with the MAE / RMSE / R² of every model.

The primary runtime model is XGBoost (`ml/models/xgboost_runtime.joblib`).
Linear Regression, Random Forest and Gradient Boosting are trained for
comparison and their metrics are reported side by side in the dashboard.

## 5b. Evaluate live plan selection

```bash
python evaluate_selection.py
```

Re-executes the held-out 20% of queries, lets the ML model pick a plan for
each, and compares it against the actually fastest candidate. Output:

`data/plan_selection_results.csv`

## 6. Run the demo

```bash
python demo.py
```

The demo shows:

- SQL features
- candidate plans
- actual execution times
- ML predicted runtimes
- ML-selected candidate
- actual fastest candidate
- records the observed result in the feedback table (`feedback`)

## 6b. Feedback and retraining loop

```bash
python feedback.py collect   # record live execution results as feedback
python feedback.py retrain   # merge feedback into the dataset + retrain
python feedback.py show      # show feedback stats
```

- `feedback.collect_feedback()` is called automatically by `demo.py` after
  each candidate execution, so every demo run feeds the loop.
- `feedback.record_feedback()` writes one row per `(query, candidate)` to the
  `feedback` table in PostgreSQL.
- `python feedback.py collect` bulk-collects feedback for the whole workload
  (one observation per query per candidate).
- `python feedback.py retrain` merges the recorded feedback into
  `data/query_plan_dataset.csv` and retrains all four models, closing the
  "actual result stored as feedback, used to train the model again" loop from
  the report abstract.

## 7. Dashboard

```bash
streamlit run dashboard.py
```

Four pages:

- **Optimize a Query** — enter any SELECT query, get candidate plans, ML
  scores, and a recommendation; optional live execution to verify the pick
  against the observed fastest plan (feeds the feedback table).
- **Model Performance** — MAE / RMSE / R2 for all four models,
  predicted-vs-actual scatter, plan-selection accuracy.
- **Feedback & Retraining** — feedback-loop status, recorded observations,
  and before/after retraining comparison.
- **Dataset Explorer** — browse the collected dataset, runtime distribution,
  plan-shape frequency.

Requires PostgreSQL running with the seeded schema and a trained model
(`ml/models/xgboost_runtime.joblib`).

## Review 3 work

- Generate a much larger and more diverse workload.
- Add hyperparameter tuning for the models.
- Improve candidate-plan generation (more planner settings, index choices).
- Benchmark ML-selected plans against PostgreSQL's baseline at scale.
- Report average/median improvement and percentage of queries improved.
