import json
from .db import get_connection
from .plan_parser import parse_plan, plan_fingerprint
from .sql_parser import validate_select

CANDIDATE_CONFIGS = [
    ("default", {}),
    ("no_hash_join", {"enable_hashjoin": "off"}),
    ("no_merge_join", {"enable_mergejoin": "off"}),
    ("no_nested_loop", {"enable_nestloop": "off"}),
]

def _set_local(cur, settings):
    for name, value in settings.items():
        cur.execute(f"SET LOCAL {name} = {value}")

def explain_candidate(query: str, name: str, settings: dict) -> dict:
    validate_select(query)

    with get_connection() as conn:
        with conn.cursor() as cur:
            _set_local(cur, settings)
            cur.execute("EXPLAIN (FORMAT JSON) " + query)
            raw = cur.fetchone()[0]

    parsed = parse_plan(raw)
    parsed["candidate_name"] = name
    parsed["plan_json"] = raw
    parsed["fingerprint"] = plan_fingerprint(raw)
    return parsed

def generate_candidates(query: str):
    candidates = []
    fingerprints = set()

    for name, settings in CANDIDATE_CONFIGS:
        candidate = explain_candidate(query, name, settings)
        if candidate["fingerprint"] not in fingerprints:
            candidates.append(candidate)
            fingerprints.add(candidate["fingerprint"])

    return candidates
