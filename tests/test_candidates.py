# tests/test_candidates.py
from optimizer.candidate_generator import (
    generate_candidates,
    CANDIDATE_CONFIGS,
)


def test_candidate_configs_shape():
    # 1 default + 3 join-method-disabled variants
    assert len(CANDIDATE_CONFIGS) == 4
    names = [name for name, _ in CANDIDATE_CONFIGS]
    assert names == [
        "default",
        "no_hash_join",
        "no_merge_join",
        "no_nested_loop",
    ]
    # default must stay the untouched baseline
    assert dict(CANDIDATE_CONFIGS)["default"] == {}


def test_generate_candidates_returns_default_first():
    candidates = generate_candidates(
        "SELECT * FROM customers WHERE city = 'Delhi'"
    )
    assert candidates[0]["candidate_name"] == "default"
    for candidate in candidates:
        assert "fingerprint" in candidate
        assert "plan_json" in candidate
        assert "root_node" in candidate


def test_generate_candidates_dedupes_identical_plans():
    # A query whose plan cannot change under any setting
    # should collapse to fewer candidates than configs.
    candidates = generate_candidates(
        "SELECT * FROM customers WHERE customer_id = 1"
    )
    fingerprints = [c["fingerprint"] for c in candidates]
    assert len(fingerprints) == len(set(fingerprints))
