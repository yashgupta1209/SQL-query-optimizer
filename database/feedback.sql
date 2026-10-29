-- Review 2: feedback storage (objective 7).
-- One row per (query, candidate) execution recorded after a live run.
-- Rebuilt by schema.sql as well; this file can be applied to an
-- existing database.

CREATE TABLE IF NOT EXISTS feedback (
    id                  SERIAL PRIMARY KEY,
    query_id            TEXT NOT NULL,
    query_text          TEXT NOT NULL,
    candidate_name      TEXT NOT NULL,
    predicted_runtime_ms DOUBLE PRECISION,
    actual_runtime_ms   DOUBLE PRECISION NOT NULL,
    planning_time_ms    DOUBLE PRECISION,
    ml_selected         BOOLEAN,
    is_actual_best      BOOLEAN,
    model_file          TEXT,
    source              TEXT NOT NULL DEFAULT 'live',
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Apply to an existing database (idempotent).
ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'live';

CREATE INDEX IF NOT EXISTS idx_feedback_query ON feedback(query_id);
