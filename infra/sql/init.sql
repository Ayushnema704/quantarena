CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS latency_snapshots (
    time        TIMESTAMPTZ NOT NULL,
    submission_id TEXT NOT NULL,
    p50_us      DOUBLE PRECISION NOT NULL,
    p90_us      DOUBLE PRECISION NOT NULL,
    p99_us      DOUBLE PRECISION NOT NULL,
    p50_intended_us DOUBLE PRECISION,
    p90_intended_us DOUBLE PRECISION,
    p99_intended_us DOUBLE PRECISION,
    event_count BIGINT NOT NULL DEFAULT 0,
    rps         DOUBLE PRECISION NOT NULL DEFAULT 0,
    error_rate  DOUBLE PRECISION NOT NULL DEFAULT 0,
    speed_score DOUBLE PRECISION,
    throughput_score DOUBLE PRECISION,
    correctness_score DOUBLE PRECISION,
    stability_score DOUBLE PRECISION,
    composite_score DOUBLE PRECISION
);

SELECT create_hypertable('latency_snapshots', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_latency_submission
    ON latency_snapshots (submission_id, time DESC);

CREATE TABLE IF NOT EXISTS submissions (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    test_status TEXT NOT NULL DEFAULT 'pending',
    ws_url      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS correctness_results (
    submission_id TEXT PRIMARY KEY,
    match_rate    DOUBLE PRECISION NOT NULL,
    total_fills   INTEGER NOT NULL DEFAULT 0,
    mismatched    INTEGER NOT NULL DEFAULT 0,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingester_offsets (
    stream_key    TEXT PRIMARY KEY,
    last_id       TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
