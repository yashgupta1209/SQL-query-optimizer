# tests/test_feedback.py
#
# Tests for the feedback loop (objective 7).
#
#   record_feedback   - write a row to the PostgreSQL feedback table
#   feedback_summary  - read statistics back
#   ensure_feedback_table - idempotent schema creation

from optimizer.feedback import (
    ensure_feedback_table,
    feedback_summary,
    record_feedback,
)


def test_ensure_feedback_table_idempotent():
    # Calling twice must not raise.
    ensure_feedback_table()
    ensure_feedback_table()


def test_record_feedback_returns_id():
    row_id = record_feedback(
        query_id="Q_TEST",
        query_text="SELECT 1",
        candidate_name="default",
        actual_runtime_ms=1.0,
        predicted_runtime_ms=0.8,
        planning_time_ms=0.2,
        ml_selected=True,
        is_actual_best=True,
    )

    assert row_id is not None
    assert row_id >= 1


def test_feedback_summary_counts_rows():
    before = feedback_summary()["rows"]

    record_feedback(
        query_id="Q_TEST_SUMMARY",
        query_text="SELECT 2",
        candidate_name="no_hash_join",
        actual_runtime_ms=5.5,
        predicted_runtime_ms=6.0,
        ml_selected=False,
        is_actual_best=True,
    )

    after = feedback_summary()

    assert after["rows"] == before + 1
    assert after["rows"] > 0
    assert after["candidates"] >= 1
    assert after["queries"] >= 1
    assert 0.0 <= after["ml_pick_accuracy"] <= 100.0


# ------------------------------------------------------------
# The feedback -> dataset merge (the retraining data path)
# ------------------------------------------------------------

import os

import pandas as pd
import pytest

from optimizer.feedback import (
    DATASET_COLUMNS,
    feedback_to_dataset,
    recompute_comparison_columns,
)


def _feedback_frame(rows):
    """Build a feedback DataFrame shaped like read_feedback() output."""
    return pd.DataFrame(rows)


def test_merge_is_a_no_op_without_feedback(tmp_path):
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame(
        [{"query_id": "Q1", "candidate_name": "default",
          "actual_runtime_ms": 1.0, "source": "collected"}]
    ).to_csv(dataset, index=False)

    result = feedback_to_dataset(
        dataset_file=str(dataset),
        feedback_df=pd.DataFrame(),
    )

    assert len(result) == 1
    assert result["source"].tolist() == ["collected"]


def test_merge_appends_a_new_observation(tmp_path):
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame(
        [{
            "query_id": "Q1",
            "candidate_name": "default",
            "actual_runtime_ms": 1.0,
            "source": "collected",
        }]
    ).to_csv(dataset, index=False)

    feedback = _feedback_frame(
        [{
            "id": 1,
            "query_id": "Q2",
            "query_text": "SELECT 1",
            "candidate_name": "default",
            "predicted_runtime_ms": 1.0,
            "actual_runtime_ms": 2.0,
            "planning_time_ms": 0.2,
            "ml_selected": True,
            "is_actual_best": True,
            "model_file": None,
            "source": "test",
            "recorded_at": None,
        }]
    )

    result = feedback_to_dataset(
        dataset_file=str(dataset),
        feedback_df=feedback,
    )

    assert len(result) == 2
    assert "Q2" in set(result["query_id"])


def test_merge_refreshes_instead_of_duplicating(tmp_path):
    # A second merge of the same feedback must not grow the dataset.
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame(
        [{
            "query_id": "Q1",
            "candidate_name": "default",
            "actual_runtime_ms": 1.0,
            "source": "collected",
        }]
    ).to_csv(dataset, index=False)

    feedback = _feedback_frame(
        [{
            "id": 1,
            "query_id": "Q1",
            "query_text": "SELECT 1",
            "candidate_name": "default",
            "predicted_runtime_ms": 1.0,
            "actual_runtime_ms": 5.0,
            "planning_time_ms": 0.2,
            "ml_selected": True,
            "is_actual_best": True,
            "model_file": None,
            "source": "test",
            "recorded_at": None,
        }]
    )

    first = feedback_to_dataset(
        dataset_file=str(dataset), feedback_df=feedback
    )
    second = feedback_to_dataset(
        dataset_file=str(dataset), feedback_df=feedback
    )

    # One row for Q1, holding the refreshed runtime.
    assert len(first) == 1
    assert len(second) == 1
    assert second["actual_runtime_ms"].tolist() == [5.0]


def test_recompute_marks_the_best_candidate():
    df = pd.DataFrame(
        {
            "query_id": ["Q1", "Q1", "Q2"],
            "actual_runtime_ms": [10.0, 4.0, 7.0],
        }
    )

    result = recompute_comparison_columns(df)

    assert result["best_runtime_ms"].tolist() == [4.0, 4.0, 7.0]
    assert result["is_actual_best"].tolist() == [False, True, True]
    assert result["runtime_gap_ms"].tolist() == [6.0, 0.0, 0.0]
