-- Store Intelligence — initial schema.
-- Indexing strategy: BRIN on time columns (append-only), composite btree
-- on (camera_id, ts) for scoped time-range scans. See docs/SCALING.md.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS events (
    event_id    UUID PRIMARY KEY,
    event_type  TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL,
    camera_id   TEXT NOT NULL,
    track_id    INTEGER,
    zone        TEXT,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS events_ts_brin ON events USING BRIN (ts);
CREATE INDEX IF NOT EXISTS events_cam_ts ON events (camera_id, ts DESC);
CREATE INDEX IF NOT EXISTS events_type_ts ON events (event_type, ts DESC);
CREATE INDEX IF NOT EXISTS events_track ON events (track_id) WHERE track_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS tracks (
    track_id    INTEGER NOT NULL,
    camera_id   TEXT NOT NULL,
    first_seen  TIMESTAMPTZ NOT NULL,
    last_seen   TIMESTAMPTZ NOT NULL,
    path        JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (camera_id, track_id)
);
CREATE INDEX IF NOT EXISTS tracks_last_seen ON tracks (last_seen DESC);

CREATE TABLE IF NOT EXISTS zone_metrics (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL,
    camera_id   TEXT NOT NULL,
    zone        TEXT NOT NULL,
    occupancy   INTEGER NOT NULL,
    avg_dwell_s NUMERIC(10,2)
);
CREATE INDEX IF NOT EXISTS zm_brin ON zone_metrics USING BRIN (ts);
CREATE INDEX IF NOT EXISTS zm_zone_ts ON zone_metrics (zone, ts DESC);

CREATE TABLE IF NOT EXISTS queue_metrics (
    id            BIGSERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL,
    camera_id     TEXT NOT NULL,
    zone          TEXT NOT NULL,
    queue_length  INTEGER NOT NULL,
    wait_seconds  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS qm_zone_ts ON queue_metrics (zone, ts DESC);

CREATE TABLE IF NOT EXISTS anomalies (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL,
    camera_id   TEXT NOT NULL,
    kind        TEXT NOT NULL,
    track_id    INTEGER,
    zone        TEXT,
    detail      TEXT,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS anom_ts ON anomalies (ts DESC);
CREATE INDEX IF NOT EXISTS anom_kind_ts ON anomalies (kind, ts DESC);

CREATE TABLE IF NOT EXISTS heatmap_snapshots (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL,
    camera_id   TEXT NOT NULL,
    cols        INTEGER NOT NULL,
    rows        INTEGER NOT NULL,
    grid        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS heat_cam_ts ON heatmap_snapshots (camera_id, ts DESC);
