# optimizer/feature_extraction.py
#
# Build a flat feature row for a single (query, candidate plan)
# pair.  The row matches the column layout that ml/train.py
# expects in data/query_plan_dataset.csv, so a live plan fed
# through here can be scored by the trained XGBoost model
# without any reshaping.
#
# Query features come from sql_parser.analyze_query (already
# numeric).  Plan features come from plan_parser.parse_plan.
# planning_time_ms is the observed planner cost for this
# candidate; pass 0.0 when you only have a static EXPLAIN and
# no EXPLAIN ANALYZE has run yet (the median imputer in the
# ML pipeline will fill it in from the training distribution).

from .sql_parser import analyze_query
from .plan_parser import parse_plan


def extract_features(query: str, explain_json: list, planning_time_ms: float = 0.0) -> dict:
    """
    Return a dict with every column ml/train.py expects.

    Parameters
    ----------
    query           : the SELECT statement
    explain_json    : raw output of EXPLAIN (FORMAT JSON)
    planning_time_ms: observed planning time if available
    """
    qf = analyze_query(query)
    pf = parse_plan(explain_json)

    row = {**pf}
    row.update(qf)
    row["planning_time_ms"] = float(planning_time_ms)

    return row
