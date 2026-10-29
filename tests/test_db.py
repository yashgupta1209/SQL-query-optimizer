# tests/test_db.py
from optimizer.db import execute_sql, get_connection
from optimizer.feedback import ensure_feedback_table


def test_database_connection():
    rows = execute_sql(
        "SELECT COUNT(*) AS n FROM customers"
    )
    assert rows[0][0] > 0


def test_schema_changes_are_committed():
    # get_connection must auto-commit, otherwise DDL such as the
    # feedback table would be rolled back when the connection closes.
    ensure_feedback_table()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = 'feedback'"
            )
            count = cur.fetchone()[0]

    assert count == 1


def test_feedback_record_persists_across_connections():
    from optimizer.feedback import record_feedback

    record_feedback(
        query_id="Q_TEST_COMMIT",
        query_text="SELECT 42",
        candidate_name="default",
        actual_runtime_ms=2.0,
    )

    rows = execute_sql(
        "SELECT COUNT(*) FROM feedback WHERE query_id = 'Q_TEST_COMMIT'"
    )
    assert rows[0][0] >= 1

