# tests/test_pipeline.py
from optimizer.pipeline import optimize_query


def test_optimize_query_returns_dict():
    result = optimize_query(
        "SELECT * FROM customers WHERE city = 'Delhi' LIMIT 10"
    )
    assert "best_candidate_name" in result
    assert "total_candidates" in result
    assert "runtime_improvement_percent" in result
    assert "reasons" in result
    assert result["total_candidates"] >= 1


def test_optimize_query_returns_reasons():
    result = optimize_query(
        "SELECT * FROM orders WHERE customer_id = 100"
    )
    assert isinstance(result["reasons"], list)
    assert len(result["reasons"]) >= 1


def test_optimize_query_rejects_non_select():
    import pytest

    with pytest.raises(ValueError):
        optimize_query("DELETE FROM customers")
