import os
import time

import pandas as pd
from optimizer.sql_parser import analyze_query
from optimizer.candidate_generator import (
    generate_candidates,
    CANDIDATE_CONFIGS,
)
from optimizer.executor import execute_candidate
from workload.queries import QUERIES


OUTPUT_FILE = "data/query_plan_dataset.csv"

# Number of actual executions per candidate.
# Keep this at 3 for stable median measurements.
REPETITIONS = 3


def collect_dataset():

    rows = []
    settings_map = dict(CANDIDATE_CONFIGS)

    total_queries = len(QUERIES)

    successful_queries = 0
    failed_queries = 0
    total_candidates = 0

    start_time = time.time()

    print("=" * 70)
    print("        INTELLIGENT SQL QUERY OPTIMIZER")
    print("              DATASET COLLECTION")
    print("=" * 70)
    print()

    print(f"Total queries       : {total_queries}")
    print(f"Repetitions/candidate: {REPETITIONS}")
    print()

    for query_number, (query_id, query) in enumerate(
        QUERIES,
        start=1
    ):

        print(
            f"[{query_number:03d}/{total_queries}] "
            f"{query_id}",
            end=" "
        )

        try:

            # --------------------------------------------------------
            # Generate candidate plans
            # --------------------------------------------------------
            query_features = analyze_query(query)
            candidates = generate_candidates(query)

            if not candidates:
                print("-> NO CANDIDATE PLANS")
                failed_queries += 1
                continue

            print(
                f"-> {len(candidates)} candidate(s)"
            )

            successful_queries += 1
            total_candidates += len(candidates)

            # --------------------------------------------------------
            # Execute every unique candidate
            # --------------------------------------------------------

            query_results = []

            for candidate in candidates:

                candidate_name = candidate[
                    "candidate_name"
                ]

                settings = settings_map.get(
                    candidate_name,
                    {}
                )

                try:

                    execution = execute_candidate(
                        query=query,
                        settings=settings,
                        repetitions=REPETITIONS,
                    )

                    runtime = execution[
                        "actual_runtime_ms"
                    ]

                    planning_time = execution[
                        "planning_time_ms"
                    ]

                    row = {
                        "query_id": query_id,
                        "query_text": query,

                        # -------------------------------
                        # Query features
                        # -------------------------------

                        "number_of_tables":
                            query_features["number_of_tables"],

                        "number_of_joins":
                            query_features["number_of_joins"],

                        "number_of_predicates":
                            query_features["number_of_predicates"],

                        "has_group_by":
                            query_features["has_group_by"],

                        "has_order_by":
                            query_features["has_order_by"],

                        "has_limit":
                            query_features["has_limit"],

                        # -------------------------------
                        # Plan features
                        # -------------------------------

                        "root_node":
                            candidate.get(
                                "root_node"
                            ),

                        "estimated_startup_cost":
                            candidate.get(
                                "estimated_startup_cost"
                            ),

                        "estimated_total_cost":
                            candidate.get(
                                "estimated_total_cost"
                            ),

                        "estimated_rows":
                            candidate.get(
                                "estimated_rows"
                            ),

                        "plan_width":
                            candidate.get(
                                "plan_width"
                            ),

                        "plan_depth":
                            candidate.get(
                                "plan_depth"
                            ),

                        "operator_count":
                            candidate.get(
                                "operator_count"
                            ),

                        "join_count":
                            candidate.get(
                                "join_count"
                            ),

                        "hash_join_count":
                            candidate.get(
                                "hash_join_count"
                            ),

                        "merge_join_count":
                            candidate.get(
                                "merge_join_count"
                            ),

                        "nested_loop_count":
                            candidate.get(
                                "nested_loop_count"
                            ),

                        "seq_scan_count":
                            candidate.get(
                                "seq_scan_count"
                            ),

                        "index_scan_count":
                            candidate.get(
                                "index_scan_count"
                            ),

                        "index_only_scan_count":
                            candidate.get(
                                "index_only_scan_count"
                            ),

                        "bitmap_scan_count":
                            candidate.get(
                                "bitmap_scan_count"
                            ),

                        "sort_count":
                            candidate.get(
                                "sort_count"
                            ),

                        "aggregate_count":
                            candidate.get(
                                "aggregate_count"
                            ),

                        # -------------------------------
                        # Candidate information
                        # -------------------------------

                        "candidate_name":
                            candidate_name,

                        "fingerprint":
                            candidate.get(
                                "fingerprint"
                            ),

                        # -------------------------------
                        # Actual execution
                        # -------------------------------

                        "actual_runtime_ms":
                            runtime,

                        "planning_time_ms":
                            planning_time,

                        "runtime_samples_ms":
                            str(
                                execution[
                                    "runtime_samples_ms"
                                ]
                            ),
                    }

                    rows.append(row)
                    query_results.append(row)

                except Exception as candidate_error:

                    print(
                        f"    Candidate "
                        f"{candidate_name} failed: "
                        f"{candidate_error}"
                    )

            # --------------------------------------------------------
            # Display fastest candidate
            # --------------------------------------------------------

            if query_results:

                fastest = min(
                    query_results,
                    key=lambda x:
                    x["actual_runtime_ms"]
                )

                print(
                    f"    FASTEST -> "
                    f"{fastest['candidate_name']} "
                    f"({fastest['actual_runtime_ms']:.3f} ms)"
                )

        except Exception as error:

            failed_queries += 1

            print(
                f"    ERROR -> {error}"
            )

    # ================================================================
    # CREATE DATAFRAME
    # ================================================================

    if not rows:

        print()
        print("ERROR: No observations collected.")
        return

    df = pd.DataFrame(rows)

    # ================================================================
    # ADD BEST-PLAN INFORMATION
    # ================================================================

    # For every query, determine the candidate with the lowest
    # measured execution time.

    best_runtime = (
        df.groupby("query_id")[
            "actual_runtime_ms"
        ]
        .transform("min")
    )

    df["best_runtime_ms"] = best_runtime

    df["runtime_gap_ms"] = (
        df["actual_runtime_ms"]
        - df["best_runtime_ms"]
    )

    df["is_actual_best"] = (
        df["actual_runtime_ms"]
        == df["best_runtime_ms"]
    ).astype(int)

    # Percentage slower than the best candidate.
    df["runtime_gap_percent"] = (
        (
            df["actual_runtime_ms"]
            - df["best_runtime_ms"]
        )
        / df["best_runtime_ms"].replace(
            0,
            0.001
        )
    ) * 100

    # ================================================================
    # SAVE
    # ================================================================

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    elapsed = time.time() - start_time

    # ================================================================
    # SUMMARY
    # ================================================================

    print()
    print("=" * 70)
    print("             DATASET COLLECTION COMPLETE")
    print("=" * 70)

    print()
    print(f"Queries attempted       : {total_queries}")
    print(f"Successful queries      : {successful_queries}")
    print(f"Failed queries          : {failed_queries}")
    print(f"Candidate observations  : {len(df)}")
    print(f"Unique queries          : {df['query_id'].nunique()}")
    print(f"Unique plans            : {df['fingerprint'].nunique()}")
    print(f"Total collection time   : {elapsed / 60:.2f} minutes")

    print()
    print("Candidate distribution:")
    print(
        df["candidate_name"]
        .value_counts()
        .to_string()
    )

    print()
    print("Runtime statistics:")
    print(
        df["actual_runtime_ms"]
        .describe()
        .to_string()
    )

    print()
    print("Actual-best observations:")
    print(
        df["is_actual_best"]
        .value_counts()
        .to_string()
    )

    print()
    print(f"Saved to: {OUTPUT_FILE}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    collect_dataset()