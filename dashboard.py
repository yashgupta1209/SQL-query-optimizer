# dashboard.py
#
# Streamlit dashboard for the Intelligent SQL Query Optimizer.
# Run with:
#   streamlit run dashboard.py
#
# Three pages:
#   1. Optimize a Query  - live plan selection with the XGBoost model
#   2. Model Performance - offline metrics + prediction quality charts
#   3. Dataset Explorer  - browse the collected dataset
#
# Prerequisites: PostgreSQL running with the sample schema loaded
# and ml/models/xgboost_runtime.joblib trained (ml/train.py).

import joblib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from optimizer.candidate_generator import generate_candidates
from optimizer.executor import execute_candidate
from optimizer.pipeline import optimize_query
from optimizer.sql_parser import analyze_query

st.set_page_config(
    page_title="Intelligent SQL Optimizer",
    page_icon="⚡",
    layout="wide",
)

MODEL_PATH = "ml/models/xgboost_runtime.joblib"


# ==============================================================
# CACHED LOADERS
# ==============================================================

@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_dataset():
    return pd.read_csv("data/query_plan_dataset.csv")


@st.cache_data
def load_predictions():
    return pd.read_csv("data/xgboost_test_predictions.csv")


@st.cache_data
def load_selection_results():
    return pd.read_csv("data/plan_selection_results.csv")


# ==============================================================
# SIDEBAR
# ==============================================================

st.sidebar.title("⚡ SQL Optimizer")
page = st.sidebar.radio(
    "Navigation",
    [
        "Optimize a Query",
        "Model Performance",
        "Feedback & Retraining",
        "Dataset Explorer",
    ],
)

st.sidebar.divider()

st.sidebar.caption(
    "Plan runtime prediction (Linear, Random Forest, "
    "Gradient Boosting, XGBoost) + plan selection + "
    "feedback loop. Requires PostgreSQL and a trained model."
)


@st.cache_data
def load_model_results():
    return pd.read_csv("data/ml_results.csv")

if page == "Optimize a Query":

    # ==========================================================
    # PAGE 1 : LIVE OPTIMIZATION
    # ==========================================================

    st.title("⚡ Optimize a Query")
    st.caption(
        "Generates candidate plans via planner settings, scores each "
        "with the trained XGBoost model, and recommends the best."
    )

    DEFAULT_QUERY = """SELECT c.city, SUM(o.amount)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.city IN ('Delhi', 'Faridabad')
GROUP BY c.city;"""

    query = st.text_area(
        "SQL Query (SELECT only)",
        value=DEFAULT_QUERY,
        height=140,
    )

    col1, col2 = st.columns([1, 5])

    with col1:
        analyze_btn = st.button("Analyze", type="primary")

    with col2:
        st.caption("Example queries live in workload/")

    if analyze_btn and query.strip():

        try:
            query_features = analyze_query(query)
        except Exception as e:
            st.error(f"Query analysis failed: {e}")
            st.stop()

        # -----------------------------------------------------
        # STEP 1 : query features
        # -----------------------------------------------------

        st.subheader("1 · Query Features")
        st.write(query_features)

        # -----------------------------------------------------
        # STEP 2 : candidates + ML scores
        # -----------------------------------------------------

        try:
            model = load_model()
            result = optimize_query(query, model=model)
        except FileNotFoundError as e:
            st.error(f"{e}")
            st.stop()
        except Exception as e:
            st.error(f"Candidate generation failed: {e}")
            st.stop()

        st.subheader("2 · Candidate Plans & ML Scores")

        cand_df = pd.DataFrame(result["all_candidates"])[
            [
                "candidate_name",
                "predicted_runtime_ms",
                "estimated_total_cost",
                "fingerprint",
            ]
        ]

        st.dataframe(cand_df, use_container_width=True)

        fig = px.bar(
            cand_df.sort_values("predicted_runtime_ms"),
            x="candidate_name",
            y="predicted_runtime_ms",
            color="candidate_name",
            title="Predicted Runtime by Candidate",
            labels={
                "candidate_name": "Candidate",
                "predicted_runtime_ms": "Predicted Runtime (ms)",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------------------------------
        # STEP 3 : recommendation
        # -----------------------------------------------------

        st.subheader("3 · ML Recommendation")

        best_name = result["best_candidate_name"]

        m1, m2, m3 = st.columns(3)

        with m1:
            st.metric(
                "Recommended Plan",
                best_name,
            )

        with m2:
            st.metric(
                "Predicted Speedup vs Default",
                f"{result['runtime_improvement_percent']:.1f}%",
            )

        with m3:
            st.metric(
                "Candidates Considered",
                result["total_candidates"],
            )

        st.markdown("**Why this plan?**")
        for reason in result["reasons"]:
            st.markdown(f"- {reason}")

        # -----------------------------------------------------
        # STEP 4 : optional live execution
        # -----------------------------------------------------

        st.subheader("4 · Verify with Live Execution (optional)")

        st.caption(
            "Runs each candidate 3 times with EXPLAIN ANALYZE and "
            "compares the ML pick against the observed fastest plan."
        )

        if st.button("Run live execution"):

            from optimizer.candidate_generator import CANDIDATE_CONFIGS
            from optimizer.feedback import record_feedback

            settings_map = dict(CANDIDATE_CONFIGS)

            progress = st.progress(0, text="Executing candidates...")

            rows = []

            for i, cand in enumerate(result["all_candidates"]):
                name = cand["candidate_name"]
                try:
                    execution = execute_candidate(
                        query=query,
                        settings=settings_map.get(name, {}),
                        repetitions=3,
                    )
                    rows.append(
                        {
                            "candidate_name": name,
                            "predicted_runtime_ms": cand[
                                "predicted_runtime_ms"
                            ],
                            **execution,
                        }
                    )
                except Exception as e:
                    st.warning(f"Candidate {name} failed: {e}")

                progress.progress(
                    (i + 1) / len(result["all_candidates"]),
                    text=f"Executed {name}",
                )

            if rows:
                live_df = pd.DataFrame(rows)
                actual_best = live_df.loc[
                    live_df["actual_runtime_ms"].idxmin(),
                    "candidate_name",
                ]
                predicted_best = live_df.loc[
                    live_df["predicted_runtime_ms"].idxmin(),
                    "candidate_name",
                ]

                # Store each observed candidate as feedback (objective 7).
                try:
                    for _, r in live_df.iterrows():
                        record_feedback(
                            query_id="DASHBOARD",
                            query_text=query,
                            candidate_name=r["candidate_name"],
                            actual_runtime_ms=r["actual_runtime_ms"],
                            predicted_runtime_ms=r[
                                "predicted_runtime_ms"
                            ],
                            planning_time_ms=r[
                                "planning_time_ms"
                            ],
                            ml_selected=(
                                r["candidate_name"]
                                == predicted_best
                            ),
                            is_actual_best=(
                                r["candidate_name"]
                                == actual_best
                            ),
                            model_file="xgboost_runtime.joblib",
                        )
                    st.info(
                        "Recorded "
                        + str(len(live_df))
                        + " result(s) as feedback in the database."
                    )
                except Exception as e:
                    st.warning(
                        f"Could not record feedback: {e}"
                    )

                verdict = (
                    "✅ Correct — ML picked the fastest plan"
                    if actual_best == best_name
                    else f"❌ Miss — actual best was {actual_best}"
                )

                n4a, n4b = st.columns(2)

                with n4a:
                    st.metric("Observed Fastest", actual_best)

                with n4b:
                    st.metric(
                        "Median Runtimes",
                        ", ".join(
                            f"{r:.2f}"
                            for r in live_df["actual_runtime_ms"]
                        ),
                    )

                fig2 = go.Figure()

                fig2.add_trace(
                    go.Bar(
                        x=live_df["candidate_name"],
                        y=live_df["predicted_runtime_ms"],
                        name="Predicted (ms)",
                        marker_color="#636EFA",
                    )
                )

                fig2.add_trace(
                    go.Bar(
                        x=live_df["candidate_name"],
                        y=live_df["actual_runtime_ms"],
                        name="Observed (ms)",
                        marker_color="#EF553B",
                    )
                )

                fig2.update_layout(
                    barmode="group",
                    title="Predicted vs Observed Runtime",
                    xaxis_title="Candidate",
                    yaxis_title="Runtime (ms)",
                )

                st.plotly_chart(fig2, use_container_width=True)

                st.success(verdict)

elif page == "Model Performance":

    # ==========================================================
    # PAGE 2 : MODEL PERFORMANCE
    # ==========================================================

    st.title("📊 Model Performance")
    st.caption(
        "Offline evaluation of the XGBoost runtime model on the "
        "held-out 20% of queries (workload-aware split)."
    )

    try:
        preds = load_predictions()
    except FileNotFoundError:
        st.error("Run ml/train.py first to produce test predictions.")
        st.stop()

    # -----------------------------------------------------
    # Model comparison (all four models, objective 5)
    # -----------------------------------------------------

    st.subheader("Model Comparison")

    st.caption(
        "MAE / RMSE / R2 of the four runtime-prediction models, "
        "evaluated on the same held-out 20% of queries."
    )

    try:
        results = load_model_results()
        st.dataframe(results, use_container_width=True, hide_index=True)

        cmp_fig = px.bar(
            results,
            x="model",
            y=["MAE", "RMSE"],
            color="model",
            title="MAE and RMSE by model (ms, lower is better)",
            labels={"value": "Error (ms)", "variable": "Metric"},
        )
        st.plotly_chart(cmp_fig, use_container_width=True)

        r2_fig = px.bar(
            results,
            x="model",
            y="R2",
            color="model",
            title="R2 by model (higher is better)",
        )
        st.plotly_chart(r2_fig, use_container_width=True)

    except FileNotFoundError:
        st.info(
            "Run ml/train.py to produce data/ml_results.csv."
        )

    st.divider()

    # -----------------------------------------------------
    # XGBoost scatter
    # -----------------------------------------------------

    actual = preds["actual_runtime_ms"]
    predicted = preds["predicted_runtime_ms"]

    mae = (actual - predicted).abs().mean()
    rmse = ((actual - predicted) ** 2).mean() ** 0.5
    ss_res = ((actual - predicted) ** 2).sum()
    ss_tot = ((actual - actual.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("MAE", f"{mae:.2f} ms")

    with c2:
        st.metric("RMSE", f"{rmse:.2f} ms")

    with c3:
        st.metric("R²", f"{r2:.4f}")

    st.divider()

    # -----------------------------------------------------
    # Scatter : predicted vs actual
    # -----------------------------------------------------

    st.subheader("Predicted vs Actual Runtime")

    max_val = max(actual.max(), predicted.max())

    scatter = go.Figure()

    scatter.add_trace(
        go.Scatter(
            x=actual,
            y=predicted,
            mode="markers",
            name="Test observations",
            text=preds["query_id"],
            hovertemplate=(
                "%{text}<br>Actual: %{x:.2f} ms<br>"
                "Predicted: %{y:.2f} ms<extra></extra>"
            ),
        )
    )

    scatter.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            name="Perfect prediction",
            line=dict(dash="dash", color="gray"),
        )
    )

    scatter.update_layout(
        xaxis_title="Actual runtime (ms)",
        yaxis_title="Predicted runtime (ms)",
        height=450,
    )

    st.plotly_chart(scatter, use_container_width=True)

    st.divider()

    # -----------------------------------------------------
    # Plan selection accuracy
    # -----------------------------------------------------

    st.subheader("Plan Selection Accuracy")

    try:
        sel = load_selection_results()

        accuracy = sel["correct"].mean() * 100

        a1, a2, a3 = st.columns(3)

        with a1:
            st.metric("Accuracy", f"{accuracy:.1f}%")

        with a2:
            st.metric(
                "Queries Evaluated",
                len(sel),
            )

        with a3:
            st.metric(
                "Correct Selections",
                int(sel["correct"].sum()),
            )

        pie = px.pie(
            names=["Correct", "Missed"],
            values=[
                int(sel["correct"].sum()),
                int((1 - sel["correct"]).sum()),
            ],
            hole=0.55,
            title="ML plan selection outcomes",
        )

        st.plotly_chart(pie, use_container_width=True)

        st.dataframe(sel, use_container_width=True)

    except FileNotFoundError:
        st.info(
            "Run evaluate_selection.py to produce "
            "data/plan_selection_results.csv."
        )

elif page == "Feedback & Retraining":

    # ==========================================================
    # PAGE 3 : FEEDBACK LOOP (objective 7)
    # ==========================================================

    st.title("🔄 Feedback & Retraining")
    st.caption(
        "The actual runtime of every executed candidate plan is "
        "stored in the PostgreSQL `feedback` table. Merging that "
        "feedback into the training set and retraining the models "
        "closes the loop described in the report abstract."
    )

    from optimizer import feedback as feedback_mod

    try:
        stats = feedback_mod.feedback_summary()
    except Exception as e:
        st.error(f"Could not read the feedback table: {e}")
        st.stop()

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.metric("Feedback Rows", stats["rows"])
    with s2:
        st.metric("Unique Queries", stats["queries"])
    with s3:
        st.metric(
            "Mean Prediction Error",
            f"{stats['mean_prediction_error_ms']:.3f} ms",
        )
    with s4:
        st.metric(
            "ML Pick Accuracy",
            f"{stats['ml_pick_accuracy']:.1f}%",
        )

    st.divider()

    fb_df = feedback_mod.read_feedback()

    if fb_df.empty:
        st.info(
            "No feedback recorded yet. Run the demo "
            "(`python demo.py`) or use the live execution on the "
            "Optimize a Query page to start feeding the loop."
        )
    else:
        st.subheader("Recent Feedback")
        recent = fb_df.sort_values(
            "recorded_at", ascending=False
        ).head(100)
        st.dataframe(
            recent[
                [
                    "query_id",
                    "candidate_name",
                    "predicted_runtime_ms",
                    "actual_runtime_ms",
                    "ml_selected",
                    "is_actual_best",
                    "recorded_at",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        error_df = fb_df[
            fb_df["predicted_runtime_ms"].notna()
        ].copy()
        error_df["abs_error_ms"] = (
            error_df["actual_runtime_ms"]
            - error_df["predicted_runtime_ms"]
        ).abs()

        err_hist = px.histogram(
            error_df,
            x="abs_error_ms",
            nbins=40,
            title="|Actual - Predicted| runtime error of recorded feedback",
            labels={"abs_error_ms": "Error (ms)"},
        )
        st.plotly_chart(err_hist, use_container_width=True)

    st.divider()

    st.subheader("Bulk collect & retrain")
    st.caption(
        "`python feedback.py collect` executes the whole workload and "
        "records the results. `python feedback.py retrain` merges the "
        "recorded feedback into the training dataset and retrains all "
        "four models."
    )

    if st.button("Run feedback.py retrain in a subprocess"):
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, "feedback.py", "retrain"],
            capture_output=True,
            text=True,
        )
        st.code(proc.stdout.strip() or "(no output)")
        if proc.returncode != 0:
            st.error(
                "Retraining failed:\n" + proc.stderr
            )
        else:
            st.success(
                "Feedback merged into the dataset and all models "
                "retrained. The new metrics are in "
                "data/ml_results.csv."
            )
            load_dataset.clear()
            load_model_results.clear()
            load_predictions.clear()

elif page == "Dataset Explorer":

    # ==========================================================
    # PAGE 3 : DATASET EXPLORER
    # ==========================================================

    st.title("🗃️ Dataset Explorer")

    try:
        df = load_dataset()
    except FileNotFoundError:
        st.error(
            "Run collect_dataset.py to produce "
            "data/query_plan_dataset.csv."
        )
        st.stop()

    st.write(f"**{len(df)}** observations")

    d1, d2, d3 = st.columns(3)

    with d1:
        st.metric("Unique Queries", df["query_id"].nunique())

    with d2:
        st.metric("Unique Plans", df["fingerprint"].nunique())

    with d3:
        st.metric(
            "Median Runtime",
            f"{df['actual_runtime_ms'].median():.2f} ms",
        )

    tab_overview, tab_runtime, tab_plans = st.tabs(
        ["Overview", "Runtime Distribution", "Plan Shapes"]
    )

    with tab_overview:
        st.dataframe(df.head(200), use_container_width=True)

    with tab_runtime:
        hist = px.histogram(
            df,
            x="actual_runtime_ms",
            nbins=50,
            title="Distribution of Actual Runtimes",
            labels={"actual_runtime_ms": "Runtime (ms)"},
        )
        st.plotly_chart(hist, use_container_width=True)

    with tab_plans:
        plan_shapes = (
            df.groupby("fingerprint")
            .agg(
                observations=("query_id", "size"),
                mean_runtime_ms=("actual_runtime_ms", "mean"),
            )
            .reset_index()
            .sort_values("observations", ascending=False)
        )

        st.caption("Top 15 plan shapes by observation count")

        shape_bar = px.bar(
            plan_shapes.head(15),
            x="fingerprint",
            y="observations",
            hover_data=["mean_runtime_ms"],
            title="Plan Shapes by Frequency",
        )
        st.plotly_chart(shape_bar, use_container_width=True)
