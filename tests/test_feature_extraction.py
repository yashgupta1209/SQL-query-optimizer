# tests/test_feature_extraction.py
from optimizer.feature_extraction import extract_features

from tests.test_plan_parser import SAMPLE_PLAN_JSON


QUERY = (
    "SELECT * FROM customers WHERE city = 'Delhi' LIMIT 10"
)


def test_extract_features_produces_all_columns():
    row = extract_features(
        query=QUERY,
        explain_json=SAMPLE_PLAN_JSON,
        planning_time_ms=0.12,
    )

    assert row["planning_time_ms"] == 0.12

    expected_plan_columns = [
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
    ]

    expected_query_columns = [
        "number_of_tables",
        "number_of_joins",
        "number_of_predicates",
        "has_group_by",
        "has_order_by",
        "has_limit",
    ]

    for column in expected_plan_columns + expected_query_columns:
        assert column in row, f"missing feature column {column}"
