# optimizer/pipeline.py
#
# End-to-end optimizer: for a new query, generate candidate
# plans, score each with the trained XGBoost model, and return
# the best candidate together with an explainable reasons list.
#
# This is the "intelligent" half of the optimizer.  The
# candidate generation and execution half lives in
# candidate_generator.py and executor.py, which is what
# collect_dataset.py uses to build the training data.

import os

import joblib
import pandas as pd

from .candidate_generator import generate_candidates
from .feature_extraction import extract_features

MODEL_PATH = "ml/models/xgboost_runtime.joblib"


def _load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}. "
            "Run ml/train.py first."
        )
    return joblib.load(MODEL_PATH)


def optimize_query(query: str, model=None) -> dict:
    """
    Pick the best candidate plan for query using the trained
    XGBoost runtime model.

    Returns a dict with:
        best_candidate_name     - name of the chosen candidate
        all_candidates          - list of every candidate, with
                                  predicted runtime attached
        total_candidates        - how many candidates were generated
        runtime_improvement_percent - predicted speedup vs default
        reasons                 - human-readable explanation list
        model_path              - which model file was used
    """
    if model is None:
        model = _load_model()

    candidates = generate_candidates(query)

    rows = []
    for candidate in candidates:
        features = extract_features(
            query=query,
            explain_json=candidate["plan_json"],
        )
        features["candidate_name"] = candidate["candidate_name"]

        row = pd.DataFrame([features])
        predicted_runtime = float(model.predict(row)[0])
        predicted_runtime = max(predicted_runtime, 0.001)

        rows.append(
            {
                "candidate_name": candidate["candidate_name"],
                "fingerprint": candidate["fingerprint"],
                "predicted_runtime_ms": predicted_runtime,
                "estimated_total_cost": candidate.get("estimated_total_cost"),
                "fingerprint_str": candidate.get("fingerprint"),
            }
        )

    if not rows:
        return {
            "best_candidate_name": None,
            "all_candidates": [],
            "total_candidates": 0,
            "runtime_improvement_percent": 0.0,
            "reasons": ["No candidate plans could be generated."],
            "model_path": MODEL_PATH,
        }

    ranked = sorted(rows, key=lambda r: r["predicted_runtime_ms"])
    best = ranked[0]

    default = next(
        (r for r in rows if r["candidate_name"] == "default"),
        None,
    )

    improvement = 0.0
    if default and best["candidate_name"] != "default":
        improvement = (
            (default["predicted_runtime_ms"] - best["predicted_runtime_ms"])
            / default["predicted_runtime_ms"]
            * 100.0
        )

    reasons = _build_reasons(query, candidates, best, default, improvement)

    return {
        "best_candidate_name": best["candidate_name"],
        "all_candidates": ranked,
        "total_candidates": len(rows),
        "runtime_improvement_percent": improvement,
        "reasons": reasons,
        "model_path": MODEL_PATH,
    }


def _build_reasons(query, candidates, best, default, improvement) -> list:
    reasons = []

    best_plan = next(
        c for c in candidates if c["fingerprint"] == best["fingerprint_str"]
    )

    reasons.append(
        f"Best candidate is '{best['candidate_name']}' "
        f"(predicted {best['predicted_runtime_ms']:.3f} ms)."
    )

    if best["candidate_name"] == "default":
        reasons.append(
            "PostgreSQL's default planner settings already give "
            "the lowest predicted runtime, so no override is needed."
        )
    else:
        reasons.append(
            f"Predicted {improvement:.1f}% faster than the default "
            "candidate."
        )

    root = best_plan.get("root_node")
    if root:
        reasons.append(f"Chosen plan starts with a {root} node.")

    fingerprint = best["fingerprint_str"]
    if "Index" in fingerprint:
        reasons.append("The chosen plan uses index-based access.")
    elif "Bitmap" in fingerprint:
        reasons.append("The chosen plan uses bitmap scans.")
    elif "Seq Scan" in fingerprint:
        reasons.append("The chosen plan relies on sequential scans.")

    seq_count = best_plan.get("seq_scan_count", 0)
    if seq_count and seq_count > 1:
        reasons.append(
            f"The plan still contains {seq_count} sequential scans; "
            "ensure matching indexes exist for frequent filters."
        )

    join_count = best_plan.get("join_count", 0)
    if join_count:
        reasons.append(f"The plan performs {join_count} join operation(s).")

    return reasons
