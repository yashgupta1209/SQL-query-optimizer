import joblib
import pandas as pd

from optimizer.candidate_generator import (
    CANDIDATE_CONFIGS,
    generate_candidates,
)
from optimizer.executor import execute_candidate


DATA_FILE = "data/query_plan_dataset.csv"
MODEL_FILE = "ml/models/xgboost_runtime.joblib"

REPETITIONS = 3


NUMERIC_FEATURES = [
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

CATEGORICAL_FEATURES = [
    "root_node",
    "candidate_name",
]


def main():

    print("=" * 70)
    print("        PLAN SELECTION ACCURACY EVALUATION")
    print("=" * 70)

    # ------------------------------------------------------------
    # Load dataset
    # ------------------------------------------------------------

    df = pd.read_csv(DATA_FILE)

    print()
    print("Dataset observations:", len(df))
    print("Unique queries:", df["query_id"].nunique())

    # ------------------------------------------------------------
    # Recreate EXACT same train/test split used by train.py
    # ------------------------------------------------------------

    from sklearn.model_selection import GroupShuffleSplit

    X = df[
        NUMERIC_FEATURES + CATEGORICAL_FEATURES
    ]

    y = df["actual_runtime_ms"]

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(
            X,
            y,
            groups=df["query_id"],
        )
    )

    test_queries = (
        df.iloc[test_idx]["query_id"]
        .unique()
        .tolist()
    )

    print("Test queries:", len(test_queries))

    # ------------------------------------------------------------
    # Load trained model
    # ------------------------------------------------------------

    model = joblib.load(MODEL_FILE)

    print("XGBoost model loaded.")

    settings_map = dict(CANDIDATE_CONFIGS)

    # ------------------------------------------------------------
    # Evaluate every unseen test query
    # ------------------------------------------------------------

    correct = 0
    incorrect = 0

    selection_results = []

    print()
    print("Evaluating test queries...")
    print()

    for query_number, query_id in enumerate(
        test_queries,
        start=1
    ):

        query_rows = df[
            df["query_id"] == query_id
        ]

        query = query_rows.iloc[0]["query_text"]

        try:

            candidates = generate_candidates(query)

            predictions = []

            actuals = []

            for candidate in candidates:

                candidate_name = (
                    candidate["candidate_name"]
                )

                settings = settings_map.get(
                    candidate_name,
                    {},
                )

                # --------------------------------------------
                # Execute candidate
                # --------------------------------------------

                execution = execute_candidate(
                    query=query,
                    settings=settings,
                    repetitions=REPETITIONS,
                )

                actual_runtime = execution[
                    "actual_runtime_ms"
                ]

                planning_time = execution[
                    "planning_time_ms"
                ]

                # --------------------------------------------
                # Build feature row
                # --------------------------------------------

                feature_row = {}

                for feature in NUMERIC_FEATURES:

                    if feature == "planning_time_ms":

                        feature_row[feature] = (
                            planning_time
                        )

                    else:

                        feature_row[feature] = (
                            candidate.get(
                                feature,
                                0,
                            )
                        )

                for feature in CATEGORICAL_FEATURES:

                    feature_row[feature] = (
                        candidate.get(
                            feature,
                            "unknown",
                        )
                    )

                feature_df = pd.DataFrame(
                    [feature_row]
                )

                # --------------------------------------------
                # XGBoost prediction
                # --------------------------------------------

                predicted_runtime = float(
                    model.predict(
                        feature_df
                    )[0]
                )

                predicted_runtime = max(
                    predicted_runtime,
                    0.001,
                )

                predictions.append(
                    {
                        "candidate_name":
                            candidate_name,
                        "predicted_runtime":
                            predicted_runtime,
                        "actual_runtime":
                            actual_runtime,
                    }
                )

                actuals.append(
                    {
                        "candidate_name":
                            candidate_name,
                        "actual_runtime":
                            actual_runtime,
                    }
                )

            if not predictions:
                continue

            # ------------------------------------------------
            # ML-selected plan
            # ------------------------------------------------

            ml_best = min(
                predictions,
                key=lambda x:
                x["predicted_runtime"],
            )

            # ------------------------------------------------
            # Actually fastest plan
            # ------------------------------------------------

            actual_best = min(
                actuals,
                key=lambda x:
                x["actual_runtime"],
            )

            is_correct = (
                ml_best["candidate_name"]
                == actual_best["candidate_name"]
            )

            if is_correct:
                correct += 1
            else:
                incorrect += 1

            selection_results.append(
                {
                    "query_id": query_id,
                    "ml_selected":
                        ml_best["candidate_name"],
                    "actual_best":
                        actual_best["candidate_name"],
                    "ml_predicted_ms":
                        ml_best["predicted_runtime"],
                    "actual_best_ms":
                        actual_best["actual_runtime"],
                    "correct":
                        int(is_correct),
                }
            )

            status = "YES" if is_correct else "NO"

            print(
                f"[{query_number:03d}/"
                f"{len(test_queries)}] "
                f"{query_id:<8} "
                f"ML={ml_best['candidate_name']:<16} "
                f"ACTUAL={actual_best['candidate_name']:<16} "
                f"-> {status}"
            )

        except Exception as error:

            print(
                f"[{query_number:03d}/"
                f"{len(test_queries)}] "
                f"{query_id} -> ERROR: {error}"
            )

    # ============================================================
    # FINAL METRICS
    # ============================================================

    total_evaluated = (
        correct + incorrect
    )

    if total_evaluated == 0:

        print()
        print("No queries were evaluated.")
        return

    accuracy = (
        correct
        / total_evaluated
    ) * 100

    results_df = pd.DataFrame(
        selection_results
    )

    results_df.to_csv(
        "data/plan_selection_results.csv",
        index=False,
    )

    # ============================================================
    # FINAL REPORT
    # ============================================================

    print()
    print("=" * 70)
    print("             FINAL SELECTION RESULTS")
    print("=" * 70)

    print()
    print(
        f"Test queries evaluated : "
        f"{total_evaluated}"
    )

    print(
        f"Correct selections     : "
        f"{correct}"
    )

    print(
        f"Incorrect selections   : "
        f"{incorrect}"
    )

    print()
    print(
        f"PLAN SELECTION ACCURACY: "
        f"{accuracy:.2f}%"
    )

    print()
    print(
        "Results saved to:"
    )

    print(
        "data/plan_selection_results.csv"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()