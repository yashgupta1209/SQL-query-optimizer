# tests/test_sql_parser.py
import pytest

from optimizer.sql_parser import analyze_query, validate_select


def test_simple_single_table():
    features = analyze_query(
        "SELECT * FROM customers WHERE city = 'Delhi'"
    )
    assert features["number_of_tables"] == 1
    assert features["number_of_joins"] == 0
    assert features["number_of_predicates"] == 1
    assert features["has_group_by"] == 0
    assert features["has_order_by"] == 0
    assert features["has_limit"] == 0


def test_join_query_features():
    features = analyze_query(
        """
        SELECT c.name, SUM(o.amount)
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE c.city = 'Delhi'
        GROUP BY c.name
        ORDER BY 2 DESC
        LIMIT 5
        """
    )
    assert features["number_of_tables"] == 2
    assert features["number_of_joins"] == 1
    assert features["has_group_by"] == 1
    assert features["has_order_by"] == 1
    assert features["has_limit"] == 1


def test_validate_select_rejects_insert():
    with pytest.raises(ValueError, match="SELECT queries only"):
        validate_select(
            "INSERT INTO customers (name, city, age) VALUES ('a','b',3)"
        )
