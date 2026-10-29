import joblib
import pandas as pd

from optimizer.candidate_generator import (
    CANDIDATE_CONFIGS,
    generate_candidates,
)
from optimizer.executor import execute_candidate
from optimizer.sql_parser import analyze_query


MODEL_PATH = "ml/models/xgboost_runtime.joblib"

REPETITIONS = 3


# ============================================================
# FEATURE CONFIGURATION
# ============================================================

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


# ============================================================
# QUERY
# ============================================================

QUERY = """
SELECT c.city, SUM(o.amount)
FROM customers c
JOIN orders o
    ON c.customer_id = o.customer_id
WHERE c.city IN ('Delhi', 'Faridabad')
GROUP BY c.city;
"""


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("        INTELLIGENT SQL QUERY OPTIMIZER")
    print("=" * 70)

    # --------------------------------------------------------
    # Show query
    # --------------------------------------------------------

    print()
    print("QUERY")
    print("-" * 70)
    print(QUERY.strip())

    # --------------------------------------------------------
    # Analyze query
    # --------------------------------------------------------

    query_features = analyze_query(QUERY)

    print()
    print("QUERY FEATURES")
    print("-" * 70)
    print(query_features)

    # --------------------------------------------------------
    # Generate candidate plans
    # --------------------------------------------------------

    print()
    print("GENERATING CANDIDATE PLANS")
    print("-" * 70)

    candidates = generate_candidates(QUERY)

    if not candidates:
        print("No candidate plans were generated.")
        return

    for candidate in candidates:

        print(
            f"{candidate['candidate_name']:<18}"
            f"| {candidate['root_node']:<20}"
            f"| cost="
            f"{candidate['estimated_total_cost']:.2f}"
        )

    # --------------------------------------------------------
    # Load trained model
    # --------------------------------------------------------

    print()
    print("LOADING ML MODEL")
    print("-" * 70)

    try:
        model = joblib.load(MODEL_PATH)
        print("XGBoost model loaded successfully.")

    except Exception as error:
        print(f"Could not load model: {error}")
        return

    # --------------------------------------------------------
    # Execute candidates + ML prediction
    # --------------------------------------------------------

    settings_map = dict(CANDIDATE_CONFIGS)

    results = []

    print()
    print("EXECUTING CANDIDATES")
    print("-" * 70)

    for candidate in candidates:

        candidate_name = candidate["candidate_name"]

        settings = settings_map.get(
            candidate_name,
            {}
        )

        try:

            execution = execute_candidate(
                query=QUERY,
                settings=settings,
                repetitions=REPETITIONS,
            )

            actual_runtime = execution[
                "actual_runtime_ms"
            ]

            planning_time = execution[
                "planning_time_ms"
            ]

            # ------------------------------------------------
            # Create ML feature row
            # ------------------------------------------------

            feature_row = {}

            for feature in NUMERIC_FEATURES:

                if feature == "planning_time_ms":

                    feature_row[feature] = planning_time

                else:

                    feature_row[feature] = candidate.get(
                        feature,
                        0
                    )

            for feature in CATEGORICAL_FEATURES:

                feature_row[feature] = candidate.get(
                    feature,
                    "unknown"
                )

            feature_df = pd.DataFrame(
                [feature_row]
            )

            # ------------------------------------------------
            # Predict runtime
            # ------------------------------------------------

            predicted_runtime = float(
                model.predict(feature_df)[0]
            )

            predicted_runtime = max(
                predicted_runtime,
                0.001
            )

            results.append(
                {
                    "candidate_name": candidate_name,
                    "predicted_runtime_ms":
                        predicted_runtime,
                    "actual_runtime_ms":
                        actual_runtime,
                    "planning_time_ms":
                        planning_time,
                    "candidate": candidate,
                }
            )

            print(
                f"{candidate_name:<18}"
                f"-> actual "
                f"{actual_runtime:.3f} ms"
            )

        except Exception as error:

            print(
                f"{candidate_name:<18}"
                f"-> ERROR: {error}"
            )

    if not results:

        print()
        print("No candidates were successfully executed.")
        return

    # ========================================================
    # STORE RESULTS AS FEEDBACK (objective 7)
    # ========================================================

    ml_best = min(
        results,
        key=lambda x:
        x["predicted_runtime_ms"]
    )

    actual_best = min(
        results,
        key=lambda x:
        x["actual_runtime_ms"]
    )

    feedback_written = 0

    try:

        from optimizer.feedback import record_feedback

        for result in results:

            record_feedback(
                query_id="DEMO",
                query_text=QUERY,
                candidate_name=result[
                    "candidate_name"
                ],
                actual_runtime_ms=result[
                    "actual_runtime_ms"
                ],
                predicted_runtime_ms=result[
                    "predicted_runtime_ms"
                ],
                planning_time_ms=result[
                    "planning_time_ms"
                ],
                ml_selected=(
                    result["candidate_name"]
                    == ml_best["candidate_name"]
                ),
                is_actual_best=(
                    result["candidate_name"]
                    == actual_best["candidate_name"]
                ),
                model_file="xgboost_runtime.joblib",
            )

            feedback_written += 1

        print()
        print(
            f"Recorded {feedback_written} result(s) as feedback."
        )

    except Exception as error:

        print()
        print(f"Could not record feedback: {error}")

    # ========================================================
    # ML PREDICTIONS
    # ========================================================

    print()
    print("ML PREDICTION")
    print("-" * 70)

    for result in results:

        print(
            f"{result['candidate_name']:<18}"
            f"-> predicted "
            f"{result['predicted_runtime_ms']:.3f} ms"
        )

    # ========================================================
    # SELECT ML PLAN / ACTUAL BEST PLAN
    # (computed above when storing feedback; reused here)
    # ========================================================

    # ========================================================
    # DISPLAY ML RECOMMENDATION
    # ========================================================

    print()
    print("ML RECOMMENDED PLAN")
    print("-" * 70)

    print(
        f"Plan: "
        f"{ml_best['candidate_name']}"
    )

    print(
        f"Predicted runtime: "
        f"{ml_best['predicted_runtime_ms']:.3f} ms"
    )

    print(
        f"Observed runtime: "
        f"{ml_best['actual_runtime_ms']:.3f} ms"
    )

    # ========================================================
    # CALCULATE ESTIMATED IMPROVEMENT
    # ========================================================

    default_result = next(
        (
            r for r in results
            if r["candidate_name"] == "default"
        ),
        None,
    )

    if default_result is not None:

        default_predicted = (
            default_result[
                "predicted_runtime_ms"
            ]
        )

        recommended_predicted = (
            ml_best[
                "predicted_runtime_ms"
            ]
        )

        if default_predicted > 0:

            predicted_improvement = (
                (
                    default_predicted
                    - recommended_predicted
                )
                / default_predicted
            ) * 100

            print(
                f"Predicted improvement over "
                f"PostgreSQL default: "
                f"{predicted_improvement:.2f}%"
            )

    # ========================================================
    # ACTUAL BEST
    # ========================================================

    print()
    print("ACTUAL BEST PLAN")
    print("-" * 70)

    print(
        f"Plan: "
        f"{actual_best['candidate_name']}"
    )

    print(
        f"Actual runtime: "
        f"{actual_best['actual_runtime_ms']:.3f} ms"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print()
    print("PLAN SELECTION RESULT")
    print("-" * 70)

    if (
        ml_best["candidate_name"]
        == actual_best["candidate_name"]
    ):

        print(
            "ML selection matches the "
            "fastest observed plan: YES"
        )

    else:

        print(
            "ML selection matches the "
            "fastest observed plan: NO"
        )

    # ========================================================
    # PERFORMANCE COMPARISON
    # ========================================================

    print()
    print("ALL CANDIDATE RESULTS")
    print("-" * 70)

    print(
        f"{'PLAN':<20}"
        f"{'PREDICTED':>15}"
        f"{'ACTUAL':>15}"
    )

    print("-" * 50)

    for result in sorted(
        results,
        key=lambda x:
        x["predicted_runtime_ms"]
    ):

        marker = ""

        if (
            result["candidate_name"]
            == ml_best["candidate_name"]
        ):
            marker = " <- ML"

        if (
            result["candidate_name"]
            == actual_best["candidate_name"]
        ):
            marker += " <- ACTUAL BEST"

        print(
            f"{result['candidate_name']:<20}"
            f"{result['predicted_runtime_ms']:>12.3f} ms"
            f"{result['actual_runtime_ms']:>12.3f} ms"
            f"{marker}"
        )

    # ========================================================
    # OPTIMIZATION SUGGESTION
    # ========================================================

    print()
    print("OPTIMIZATION SUGGESTION")
    print("-" * 70)

    recommended_plan = (
        ml_best["candidate_name"]
    )

    if recommended_plan == "default":

        print(
            "Use PostgreSQL's default planner "
            "configuration for this query."
        )

        print(
            "The ML model does not predict a "
            "benefit from disabling the tested "
            "join strategies."
        )

    elif recommended_plan == "no_hash_join":

        print(
            "Try executing the query with "
            "hash joins disabled."
        )

        print(
            "This candidate was predicted to "
            "have the lowest execution time "
            "among the tested strategies."
        )

    elif recommended_plan == "no_merge_join":

        print(
            "Try executing the query with "
            "merge joins disabled."
        )

        print(
            "This candidate was predicted to "
            "have the lowest execution time "
            "among the tested strategies."
        )

    elif recommended_plan == "no_nested_loop":

        print(
            "Try executing the query with "
            "nested-loop joins disabled."
        )

        print(
            "This candidate was predicted to "
            "have the lowest execution time "
            "among the tested strategies."
        )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()