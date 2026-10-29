# ml/train.py
#
# Trains the runtime-prediction models on the collected plan dataset
# and saves their metrics to data/ml_results.csv.
#
# Models (all four named in the Review 2 report):
#   Linear Regression   - baseline linear model
#   Random Forest       - bagged trees
#   Gradient Boosting   - sklearn's boosted trees
#   XGBoost             - the primary runtime model used by the system
#
# The split is workload-aware: every candidate plan belonging to the
# same query stays in the same split, so the model never sees one
# candidate of a query while testing on another.

import os

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from xgboost import XGBRegressor


DATA_FILE = "data/query_plan_dataset.csv"
MODEL_DIR = "ml/models"
RESULTS_FILE = "data/ml_results.csv"
PREDICTIONS_FILE = "data/xgboost_test_predictions.csv"

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# FEATURES
# ============================================================

NUMERIC_FEATURES = [
    "number_of_tables",
    "number_of_joins",
    "number_of_predicates",
    "has_group_by",
    "has_order_by",
    "has_limit",

    "estimated_startup_cost",
    "estimated_total_cost",
    "estimated_rows",
    "plan_width",
    "plan_depth",
    "operator_count",

    "join_count",
    "hash_join_count",
    "merge_join_count",
    "nested_loop_count",

    "seq_scan_count",
    "index_scan_count",
    "index_only_scan_count",
    "bitmap_scan_count",

    "sort_count",
    "aggregate_count",

    "planning_time_ms",
]


CATEGORICAL_FEATURES = [
    "root_node",
    "candidate_name",
]


TARGET = "actual_runtime_ms"

TEST_SIZE = 0.20
RANDOM_STATE = 42


# ============================================================
# MODEL DEFINITIONS
# ============================================================

def get_model_definitions() -> dict:
    """The four models compared in the report."""
    return {
        "Linear Regression": (
            LinearRegression(),
            "linear_regression.joblib",
        ),
        "Random Forest": (
            RandomForestRegressor(
                n_estimators=200,
                random_state=RANDOM_STATE,
                max_depth=12,
                min_samples_leaf=1,
                n_jobs=-1,
            ),
            "random_forest.joblib",
        ),
        "Gradient Boosting": (
            GradientBoostingRegressor(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.85,
                random_state=RANDOM_STATE,
            ),
            "gradient_boosting.joblib",
        ),
        "XGBoost": (
            XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                objective="reg:squarederror",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
            "xgboost_runtime.joblib",
        ),
    }


# ============================================================
# PREPROCESSING
# ============================================================

def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore"),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ]
    )


# ============================================================
# CORE TRAINING ROUTINE
# ============================================================

def train_all_models(
    dataset_file: str = DATA_FILE,
    results_file: str = RESULTS_FILE,
    predictions_file: str = PREDICTIONS_FILE,
    save_predictions: bool = True,
    verbose: bool = True,
) -> list:
    """
    Train every model on the dataset and save the metrics.

    Returns a list of dicts, one per model, with the keys
    model / MAE / RMSE / R2 / model_file.
    """
    df = pd.read_csv(dataset_file)

    if verbose:
        print()
        print("=" * 70)
        print("        SQL PLAN RUNTIME MODEL TRAINING")
        print("=" * 70)
        print()
        print("Dataset shape:", df.shape)
        print("Unique queries:", df["query_id"].nunique())
        print("Unique plans:", df["fingerprint"].nunique())

    # --------------------------------------------------------
    # Drop unusable rows
    # --------------------------------------------------------

    df = df.dropna(subset=[TARGET])
    df = df[df[TARGET] > 0].copy()

    missing = [
        c for c in
        NUMERIC_FEATURES + CATEGORICAL_FEATURES
        if c not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if verbose:
        print("Usable observations:", len(df))

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    # --------------------------------------------------------
    # Workload-aware split
    # --------------------------------------------------------

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    train_idx, test_idx = next(
        splitter.split(X, y, groups=df["query_id"])
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    if verbose:
        print()
        print("Training observations:", len(X_train))
        print("Testing observations :", len(X_test))
        print(
            "Training queries:",
            df.iloc[train_idx]["query_id"].nunique(),
        )
        print(
            "Testing queries:",
            df.iloc[test_idx]["query_id"].nunique(),
        )

    results = []
    xgb_predictions = None

    for name, (estimator, filename) in (
        get_model_definitions().items()
    ):

        if verbose:
            print()
            print(f"Training {name}...")

        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("model", estimator),
            ]
        )

        pipeline.fit(X_train, y_train)

        predictions = np.maximum(
            pipeline.predict(X_test),
            0.001,
        )

        mae = mean_absolute_error(y_test, predictions)
        rmse = float(
            np.sqrt(mean_squared_error(y_test, predictions))
        )
        r2 = r2_score(y_test, predictions)

        model_path = os.path.join(MODEL_DIR, filename)
        joblib.dump(pipeline, model_path)

        if name == "XGBoost":
            xgb_predictions = predictions

        results.append(
            {
                "model": name,
                "MAE": round(float(mae), 4),
                "RMSE": round(float(rmse), 4),
                "R2": round(float(r2), 4),
                "model_file": filename,
            }
        )

        if verbose:
            print(f"  MAE  : {mae:.4f} ms")
            print(f"  RMSE : {rmse:.4f} ms")
            print(f"  R2   : {r2:.4f}")
            print(f"  Saved: {model_path}")

    # --------------------------------------------------------
    # Save metrics for every model
    # --------------------------------------------------------

    results_df = pd.DataFrame(results)

    os.makedirs(
        os.path.dirname(results_file),
        exist_ok=True,
    )

    results_df.to_csv(results_file, index=False)

    # --------------------------------------------------------
    # Save XGBoost test predictions
    # --------------------------------------------------------

    if save_predictions and xgb_predictions is not None:

        pred_rows = df.iloc[test_idx].copy()
        pred_rows["predicted_runtime_ms"] = xgb_predictions
        pred_rows["prediction_error_ms"] = (
            pred_rows["actual_runtime_ms"]
            - pred_rows["predicted_runtime_ms"]
        )

        pred_rows.to_csv(predictions_file, index=False)

        if verbose:
            print()
            print("Test predictions saved to:")
            print(predictions_file)

    if verbose:
        print()
        print("Results:")
        print(results_df.to_string(index=False))
        print()
        print("Saved:", results_file)
        print()
        print("=" * 70)
        print("TRAINING COMPLETE")
        print("=" * 70)

    return results


def main():
    train_all_models()


if __name__ == "__main__":
    main()
