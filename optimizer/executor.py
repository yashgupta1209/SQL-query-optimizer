import statistics
from .db import get_connection
from .candidate_generator import _set_local
from .sql_parser import validate_select

def execute_candidate(query: str, settings: dict, repetitions: int = 3) -> dict:
    validate_select(query)

    runtimes = []
    planning_times = []

    for _ in range(repetitions):
        with get_connection() as conn:
            with conn.cursor() as cur:
                _set_local(cur, settings)
                cur.execute(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query
                )
                raw = cur.fetchone()[0]

        info = raw[0]
        runtimes.append(float(info["Execution Time"]))
        planning_times.append(float(info["Planning Time"]))

    return {
        "actual_runtime_ms": statistics.median(runtimes),
        "planning_time_ms": statistics.median(planning_times),
        "runtime_samples_ms": runtimes,
    }
