# tests/test_plan_parser.py
from optimizer.plan_parser import parse_plan, plan_fingerprint


# Minimal realistic EXPLAIN (FORMAT JSON) payload.
SAMPLE_PLAN_JSON = [
    {
        "Plan": {
            "Node Type": "Limit",
            "Startup Cost": 1.0,
            "Total Cost": 2.5,
            "Plan Rows": 10,
            "Plan Width": 40,
            "Plans": [
                {
                    "Node Type": "Index Scan",
                    "Startup Cost": 0.5,
                    "Total Cost": 2.0,
                    "Plan Rows": 100,
                    "Plan Width": 40,
                },
            ],
        }
    }
]


def test_parse_plan_counts():
    stats = parse_plan(SAMPLE_PLAN_JSON)
    assert stats["root_node"] == "Limit"
    assert stats["estimated_total_cost"] == 2.5
    assert stats["estimated_rows"] == 10
    assert stats["plan_depth"] == 2
    assert stats["operator_count"] == 2
    assert stats["index_scan_count"] == 1
    assert stats["join_count"] == 0


def test_parse_plan_join_counting():
    two_way_join = [
        {
            "Plan": {
                "Node Type": "Hash Join",
                "Startup Cost": 1.0,
                "Total Cost": 100.0,
                "Plan Rows": 500,
                "Plan Width": 80,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Startup Cost": 0.0,
                        "Total Cost": 10.0,
                        "Plan Rows": 1000,
                        "Plan Width": 40,
                    },
                    {
                        "Node Type": "Hash",
                        "Startup Cost": 0.0,
                        "Total Cost": 5.0,
                        "Plan Rows": 1000,
                        "Plan Width": 40,
                        "Plans": [
                            {
                                "Node Type": "Seq Scan",
                                "Startup Cost": 0.0,
                                "Total Cost": 8.0,
                                "Plan Rows": 900,
                                "Plan Width": 40,
                            }
                        ],
                    },
                ],
            }
        }
    ]
    stats = parse_plan(two_way_join)
    assert stats["hash_join_count"] == 1
    assert stats["join_count"] == 1
    assert stats["seq_scan_count"] == 2
    assert stats["operator_count"] == 4


def test_plan_fingerprint_distinguishes_shapes():
    fp_a = plan_fingerprint(SAMPLE_PLAN_JSON)
    fp_b = plan_fingerprint(
        [
            {
                "Plan": {
                    "Node Type": "Seq Scan",
                    "Plans": [],
                }
            }
        ]
    )
    assert fp_a != fp_b
    assert "Limit" in fp_a
