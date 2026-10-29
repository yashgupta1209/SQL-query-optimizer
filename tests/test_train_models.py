# tests/test_train_models.py
#
# Objective 5: the report names four models - Linear Regression,
# Random Forest, Gradient Boosting and XGBoost. Verify the training
# routine is set up to train all four.

from ml.train import get_model_definitions, NUMERIC_FEATURES, CATEGORICAL_FEATURES


def test_all_four_models_defined():
    models = get_model_definitions()

    expected = {
        "Linear Regression",
        "Random Forest",
        "Gradient Boosting",
        "XGBoost",
    }

    assert set(models.keys()) == expected


def test_each_model_has_estimator_and_file():
    for name, (estimator, filename) in (
        get_model_definitions().items()
    ):
        assert estimator is not None
        assert filename.endswith(".joblib")
        assert filename.startswith(
            name.lower().replace(" ", "_")
        )


def test_feature_lists_are_consistent():
    # No accidental duplicates or placeholder entries.
    all_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    assert len(all_features) == len(set(all_features))
    assert "index_only_scan_scan_placeholder" not in all_features
    assert "index_only_scan_count" in all_features
