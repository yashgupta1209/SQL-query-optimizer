# optimizer/feedback.py
#
# Feedback loop (objective 7 of Review 2).
#
# After a query is optimized and executed, the real result is stored as
# feedback. That feedback is later merged back into the training dataset
# and the models are retrained on it.
#
#   1. record_feedback()   - write one row per (query, candidate)
#   2. collect_feedback()  - bulk-record the whole workload
#   3. feedback_to_dataset()- merge feedback rows into the training CSV
#   4. retrain()           - merge + retrain every model
#
# The feedback table lives in PostgreSQL so the loop survives restarts.

import os

import pandas as pd

from .db import get_connection
from .feature_extraction import extract_features

FEEDBACK_TABLE = "feedback"

DATASET_FILE = "data/query_plan_dataset.csv"

# The feature columns the models are trained on. Feedback rows need the
# same columns, otherwise they cannot be merged into the dataset.
FEATURE_COLUMNS = [
    "number_of_tables",
    "number_of_joins",
    "number_of_predicates",
    "has_group_by",
    "has_order_by",
    "has_limit",
    "estimated_startup_cost",
    "estimated_total_cost",
    "estimated_rows",
    "plan_width",
    "plan_depth",
    "operator_count",
    "join_count",
    "hash_join_count",
    "merge_join_count",
    "nested_loop_count",
    "seq_scan_count",
    "index_scan_count",
    "index_only_scan_count",
    "bitmap_scan_count",
    "sort_count",
    "aggregate_count",
    "planning_time_ms",
]

CATEGORICAL_COLUMNS = [
    "root_node",
    "candidate_name",
]

# The exact column layout data/query_plan_dataset.csv must have,
# taken from a copy of that file. If the dataset changes shape, this
# keeps the merge honest instead of silently producing a bad table.
DATASET_COLUMNS = [
    "query_id",
    "query_text",
    "number_of_tables",
    "number_of_joins",
    "number_of_predicates",
    "has_group_by",
    "has_order_by",
    "has_limit",
    "root_node",
    "estimated_startup_cost",
    "estimated_total_cost",
    "estimated_rows",
    "plan_width",
    "plan_depth",
    "operator_count",
    "join_count",
    "hash_join_count",
    "merge_join_count",
    "nested_loop_count",
    "seq_scan_count",
    "index_scan_count",
    "index_only_scan_count",
    "bitmap_scan_count",
    "sort_count",
    "aggregate_count",
    "candidate_name",
    "fingerprint",
    "actual_runtime_ms",
    "planning_time_ms",
    "runtime_samples_ms",
    "best_runtime_ms",
    "runtime_gap_ms",
    "is_actual_best",
    "runtime_gap_percent",
    "source",
]


# ============================================================
# SCHEMA
# ============================================================

def ensure_feedback_table() -> None:
    """Create the feedback table if it does not exist yet."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id                   SERIAL PRIMARY KEY,
                    query_id             TEXT NOT NULL,
                    query_text           TEXT NOT NULL,
                    candidate_name       TEXT NOT NULL,
                    predicted_runtime_ms DOUBLE PRECISION,
                    actual_runtime_ms    DOUBLE PRECISION NOT NULL,
                    planning_time_ms     DOUBLE PRECISION,
                    ml_selected          BOOLEAN,
                    is_actual_best       BOOLEAN,
                    model_file           TEXT,
                    source               TEXT NOT NULL DEFAULT 'live',
                    recorded_at          TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_feedback_query ON feedback(query_id)"
            )


# ============================================================
# RECORDING
# ============================================================

def record_feedback(
    query_id: str,
    query_text: str,
    candidate_name: str,
    actual_runtime_ms: float,
    predicted_runtime_ms: float = None,
    planning_time_ms: float = None,
    ml_selected: bool = False,
    is_actual_best: bool = False,
    model_file: str = None,
    source: str = "live",
) -> int:
    """
    Store one executed candidate as feedback.

    Returns the id of the inserted row.
    """
    ensure_feedback_table()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feedback (
                    query_id,
                    query_text,
                    candidate_name,
                    predicted_runtime_ms,
                    actual_runtime_ms,
                    planning_time_ms,
                    ml_selected,
                    is_actual_best,
                    model_file,
                    source
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    query_id,
                    query_text,
                    candidate_name,
                    predicted_runtime_ms,
                    actual_runtime_ms,
                    planning_time_ms,
                    ml_selected,
                    is_actual_best,
                    model_file,
                    source,
                ),
            )
            row_id = cur.fetchone()[0]

    return row_id


def collect_feedback(
    queries: list = None,
    repetitions: int = 1,
    model=None,
    progress: bool = True,
) -> int:
    """
    Execute every candidate of every query and store the observed
    runtime as feedback.

    Returns the number of feedback rows written.
    """
    from .candidate_generator import (
        CANDIDATE_CONFIGS,
        generate_candidates,
    )
    from .executor import execute_candidate
    from .feature_extraction import extract_features
    from .pipeline import _load_model

    if queries is None:
        from workload.queries import QUERIES
        queries = QUERIES

    if model is None:
        model = _load_model()

    settings_map = dict(CANDIDATE_CONFIGS)

    ensure_feedback_table()

    written = 0
    total = len(queries)

    for number, (query_id, query) in enumerate(queries, start=1):

        if progress:
            print(
                f"[{number:03d}/{total}] {query_id}",
                end=" ",
                flush=True,
            )

        try:
            candidates = generate_candidates(query)

            results = []

            for candidate in candidates:

                name = candidate["candidate_name"]

                execution = execute_candidate(
                    query=query,
                    settings=settings_map.get(name, {}),
                    repetitions=repetitions,
                )

                actual = execution["actual_runtime_ms"]

                features = extract_features(
                    query=query,
                    explain_json=candidate["plan_json"],
                )
                features["candidate_name"] = name

                predicted = float(
                    model.predict(pd.DataFrame([features]))[0]
                )
                predicted = max(predicted, 0.001)

                results.append(
                    {
                        "candidate_name": name,
                        "predicted_runtime_ms": predicted,
                        "actual_runtime_ms": actual,
                        "planning_time_ms": execution[
                            "planning_time_ms"
                        ],
                        "features": features,
                    }
                )

            if not results:
                continue

            best = min(
                results,
                key=lambda r: r["actual_runtime_ms"],
            )

            for result in results:

                record_feedback(
                    query_id=query_id,
                    query_text=query,
                    candidate_name=result["candidate_name"],
                    actual_runtime_ms=result[
                        "actual_runtime_ms"
                    ],
                    predicted_runtime_ms=result[
                        "predicted_runtime_ms"
                    ],
                    planning_time_ms=result["planning_time_ms"],
                    ml_selected=(
                        result["candidate_name"]
                        == best["candidate_name"]
                    ),
                    is_actual_best=(
                        result["candidate_name"]
                        == best["candidate_name"]
                    ),
                    model_file="xgboost_runtime.joblib",
                    source="bulk",
                )

                written += 1

            if progress:
                print(
                    f"-> {len(results)} candidate(s) recorded",
                    flush=True,
                )

        except Exception as error:

            if progress:
                print(f"-> ERROR: {error}", flush=True)

    return written


# ============================================================
# READING
# ============================================================

def read_feedback() -> pd.DataFrame:
    """Read every feedback row into a DataFrame."""
    ensure_feedback_table()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       query_id,
                       query_text,
                       candidate_name,
                       predicted_runtime_ms,
                       actual_runtime_ms,
                       planning_time_ms,
                       ml_selected,
                       is_actual_best,
                       model_file,
                       source,
                       recorded_at
                FROM feedback
                ORDER BY id
                """
            )
            rows = cur.fetchall()

    columns = [
        "id",
        "query_id",
        "query_text",
        "candidate_name",
        "predicted_runtime_ms",
        "actual_runtime_ms",
        "planning_time_ms",
        "ml_selected",
        "is_actual_best",
        "model_file",
        "source",
        "recorded_at",
    ]

    return pd.DataFrame(rows, columns=columns)


def feedback_summary() -> dict:
    """Small statistics about the feedback collected so far."""
    df = read_feedback()

    if df.empty:
        return {
            "rows": 0,
            "queries": 0,
            "candidates": 0,
            "mean_actual_runtime_ms": 0.0,
            "mean_prediction_error_ms": 0.0,
            "ml_pick_accuracy": 0.0,
        }

    with_predicted = df[
        df["predicted_runtime_ms"].notna()
    ]

    if with_predicted.empty:
        mean_error = 0.0
    else:
        mean_error = float(
            (
                with_predicted["actual_runtime_ms"]
                - with_predicted["predicted_runtime_ms"]
            ).abs().mean()
        )

    ml_rows = df[
        df["ml_selected"].notna() & df["is_actual_best"].notna()
    ]

    if ml_rows.empty:
        ml_accuracy = 0.0
    else:
        ml_accuracy = float(
            (
                ml_rows["ml_selected"]
                == ml_rows["is_actual_best"]
            ).mean() * 100
        )

    return {
        "rows": len(df),
        "queries": df["query_id"].nunique(),
        "candidates": df["candidate_name"].nunique(),
        "mean_actual_runtime_ms": float(
            df["actual_runtime_ms"].mean()
        ),
        "mean_prediction_error_ms": mean_error,
        "ml_pick_accuracy": ml_accuracy,
    }


# ============================================================
# MERGING INTO THE DATASET
# ============================================================

def extract_features_for(
    query_text: str,
    plan_json: list,
    planning_time_ms,
    candidate_name: str,
) -> dict:
    """
    Feature dict for one (query, candidate) pair, in the same
    shape as a row of the training dataset.
    """
    if planning_time_ms is None or pd.isna(planning_time_ms):
        planning_time_ms = 0.0

    features = extract_features(
        query=query_text,
        explain_json=plan_json,
        planning_time_ms=float(planning_time_ms),
    )

    features["candidate_name"] = candidate_name

    return features

def backup_dataset(dataset_file: str = DATASET_FILE) -> str:
    """
    Copy the dataset aside before it is modified, so a bad merge can
    be reverted. Returns the backup path, or None if there was
    nothing to back up.
    """
    if not os.path.exists(dataset_file):
        return None

    backup = dataset_file + ".pre_feedback"

    with open(dataset_file, "rb") as src, open(
        backup, "wb"
    ) as dst:
        dst.write(src.read())

    print(f"Backed up dataset to {backup}")

    return backup


def restore_dataset(
    dataset_file: str = DATASET_FILE,
    backup_file: str = None,
) -> str:
    """Restore the dataset from a backup made by backup_dataset."""
    if backup_file is None:
        backup_file = dataset_file + ".pre_feedback"

    if not os.path.exists(backup_file):
        raise FileNotFoundError(
            f"No dataset backup found at {backup_file}"
        )

    with open(backup_file, "rb") as src, open(
        dataset_file, "wb"
    ) as dst:
        dst.write(src.read())

    print(f"Restored dataset from {backup_file}")

    return backup_file


def feedback_to_dataset(
    dataset_file: str = DATASET_FILE,
    feedback_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Turn feedback rows into dataset rows and append them to the
    training dataset.

    A feedback row only knows the runtime and the candidate name, so the
    plan features are recovered by re-explaining the query with the same
    planner settings the candidate used. That keeps the feature schema
    identical to the original dataset.

    The merge is idempotent: a feedback row is skipped when the dataset
    already holds an observation of the same query and candidate. Running
    the retraining step repeatedly therefore does not duplicate data.

    A backup of the dataset is written before it is modified.

    Returns the updated dataset as a DataFrame.
    """
    from .candidate_generator import generate_candidates

    if feedback_df is None:
        feedback_df = read_feedback()

    if os.path.exists(dataset_file):
        base = pd.read_csv(dataset_file)
    else:
        base = pd.DataFrame()

    if feedback_df.empty:
        print("No feedback rows to merge.")
        return base

    # Observation keyed by query + candidate. A feedback row refreshes
    # the existing observation (if any) instead of appending a duplicate,
    # so the dataset stays at one row per query + candidate and repeated
    # retraining cycles do not grow the file.
    known = {}
    if not base.empty:
        for r in base.itertuples():
            key = (r.query_id, r.candidate_name)
            if key not in known:
                known[key] = r

    # Only the most recent observation per query + candidate.
    latest = (
        feedback_df.sort_values("id")
        .groupby(["query_id", "candidate_name"], as_index=False)
        .last()
    )

    new_rows = []
    skipped = 0
    replaced = 0

    for _, entry in latest.iterrows():

        query_id = entry["query_id"]
        query_text = entry["query_text"]
        candidate_name = entry["candidate_name"]
        actual = float(entry["actual_runtime_ms"])

        key = (query_id, candidate_name)

        row = {c: None for c in DATASET_COLUMNS}
        row["query_id"] = query_id
        row["query_text"] = query_text
        row["candidate_name"] = candidate_name
        row["actual_runtime_ms"] = actual
        row["source"] = "feedback"
        row["is_actual_best"] = bool(entry["is_actual_best"])
        row["runtime_samples_ms"] = ""

        existing = known.get(key)

        if existing is not None:
            # Reuse the plan features already collected for this
            # query + candidate, refreshing only the runtime.
            for column in DATASET_COLUMNS:
                if row[column] is None:
                    row[column] = getattr(existing, column, None)

            row["actual_runtime_ms"] = actual
            row["source"] = "feedback"
            row["is_actual_best"] = bool(entry["is_actual_best"])
            replaced += 1

        else:
            try:
                candidates = generate_candidates(query_text)

                match = next(
                    (
                        c for c in candidates
                        if c["candidate_name"] == candidate_name
                    ),
                    None,
                )

                if match is None:
                    skipped += 1
                    continue

                features = extract_features_for(
                    query_text,
                    match["plan_json"],
                    entry["planning_time_ms"],
                    candidate_name,
                )

                for column in DATASET_COLUMNS:
                    if column in features:
                        row[column] = features[column]

                row["fingerprint"] = match.get("fingerprint")
                row["actual_runtime_ms"] = actual
                row["source"] = "feedback"
                row["is_actual_best"] = bool(entry["is_actual_best"])

            except Exception as error:
                print(
                    f"  skipping {query_id}/{candidate_name}: {error}"
                )
                skipped += 1
                continue

        new_rows.append(row)

    if replaced:
        print(
            f"Refreshed {replaced} existing observation(s) with "
            "the latest feedback."
        )

    if skipped:
        print(f"Skipped {skipped} feedback row(s) that could not be merged.")

    if not new_rows:
        print("No new feedback rows to add.")
        return base

    feedback_rows = pd.DataFrame(new_rows)

    # Drop base rows that a feedback row refreshes (one row per
    # query + candidate), then append the refreshed rows.
    refresh_keys = {
        (n["query_id"], n["candidate_name"])
        for n in new_rows
    }

    if not base.empty:
        for column in base.columns:
            if column not in feedback_rows.columns:
                feedback_rows[column] = None

        feedback_rows = feedback_rows[base.columns]

        base_part = base[
            ~base.apply(
                lambda r: (
                    r.query_id,
                    r.candidate_name,
                ) in refresh_keys,
                axis=1,
            )
        ][base.columns]
    else:
        base_part = pd.DataFrame()

    merged = pd.concat(
        [base_part, feedback_rows],
        ignore_index=True,
    )

    # Recompute the per-candidate comparison columns.
    merged = recompute_comparison_columns(merged)

    os.makedirs(
        os.path.dirname(dataset_file),
        exist_ok=True,
    )

    backup_dataset(dataset_file)

    merged.to_csv(dataset_file, index=False)

    print(
        f"Merged {len(feedback_rows)} feedback observation(s) "
        f"into {dataset_file} "
        f"({len(base_part)} kept + {len(feedback_rows)} from feedback)."
    )

    return merged


def recompute_comparison_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recompute best_runtime_ms, runtime_gap_ms and runtime_gap_percent
    for every query, so the merged dataset stays internally consistent.
    """
    if df.empty or "query_id" not in df.columns:
        return df

    df = df.copy()

    df["actual_runtime_ms"] = pd.to_numeric(
        df["actual_runtime_ms"],
        errors="coerce",
    )

    best = df.groupby("query_id")["actual_runtime_ms"].transform("min")
    df["best_runtime_ms"] = best

    df["runtime_gap_ms"] = (
        df["actual_runtime_ms"] - df["best_runtime_ms"]
    )

    df["runtime_gap_percent"] = (
        (
            df["actual_runtime_ms"] - df["best_runtime_ms"]
        )
        / df["best_runtime_ms"].replace(0, 0.001)
    ) * 100

    df["is_actual_best"] = df["runtime_gap_ms"].abs() < 1e-9

    return df


# ============================================================
# RETRAINING
# ============================================================

def retrain(
    dataset_file: str = DATASET_FILE,
    feedback_df: pd.DataFrame = None,
) -> dict:
    """
    Close the loop: merge the recorded feedback into the training
    dataset and retrain every model on the enlarged dataset.

    Returns a dict describing what happened.
    """
    from ml.train import train_all_models

    print("=" * 70)
    print("          FEEDBACK-DRIVEN RETRAINING")
    print("=" * 70)
    print()

    before = {}
    if os.path.exists(dataset_file):
        before = pd.read_csv(dataset_file)
        print(
            f"Dataset before retraining : {len(before)} observations"
        )

    merged = feedback_to_dataset(
        dataset_file=dataset_file,
        feedback_df=feedback_df,
    )

    print(
        f"Dataset after retraining  : {len(merged)} observations"
    )

    print()
    print("Retraining models...")
    print()

    results = train_all_models(
        dataset_file=dataset_file,
        save_predictions=True,
    )

    print()
    print("=" * 70)
    print("          RETRAINING COMPLETE")
    print("=" * 70)

    return {
        "observations_before": len(before),
        "observations_after": len(merged),
        "models": results,
    }
