-- InsightSQL for HPE GreenLake SAP Operations
-- PostgreSQL 16 Schema
-- All objects in the 'ops' schema

CREATE SCHEMA IF NOT EXISTS ops;

-- ============================================================
-- INVENTORY & TOPOLOGY
-- ============================================================

CREATE TABLE IF NOT EXISTS ops.resources (
    resource_id   TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,        -- sap_sid, host, storage_array, volume, service, dashboard_panel
    vendor        TEXT,
    product       TEXT,
    display_name  TEXT NOT NULL,
    site          TEXT,
    tenant_id     TEXT DEFAULT 'greenlake-prod-east',
    labels        JSONB DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.resource_edges (
    src_resource_id TEXT NOT NULL REFERENCES ops.resources(resource_id),
    dst_resource_id TEXT NOT NULL REFERENCES ops.resources(resource_id),
    edge_type       TEXT NOT NULL,      -- runs_on, uses_volume, hosted_by, serves
    confidence      NUMERIC DEFAULT 1.0,
    PRIMARY KEY (src_resource_id, dst_resource_id, edge_type)
);

-- ============================================================
-- RAW INGESTION
-- ============================================================

CREATE TABLE IF NOT EXISTS ops.alerts_raw (
    alert_id       BIGSERIAL PRIMARY KEY,
    alert_group_id TEXT,
    source         TEXT NOT NULL DEFAULT 'grafana',
    received_at    TIMESTAMPTZ DEFAULT now(),
    payload        JSONB NOT NULL
);

-- ============================================================
-- NORMALIZED TELEMETRY
-- ============================================================

CREATE TABLE IF NOT EXISTS ops.events_norm (
    event_id   BIGSERIAL PRIMARY KEY,
    source     TEXT NOT NULL,
    resource_id TEXT REFERENCES ops.resources(resource_id),
    severity   TEXT,                    -- info, warning, critical
    event_type TEXT,                    -- alert, backup_start, backup_end, server_health, etc.
    event_ts   TIMESTAMPTZ NOT NULL,
    summary    TEXT,
    details    JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_events_resource_ts ON ops.events_norm(resource_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_ts ON ops.events_norm(event_ts DESC);

-- Partitioned time-series metrics
CREATE TABLE IF NOT EXISTS ops.metrics_norm (
    metric_ts    TIMESTAMPTZ NOT NULL,
    resource_id  TEXT NOT NULL,
    metric_name  TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    unit         TEXT,
    labels       JSONB DEFAULT '{}'::jsonb
) PARTITION BY RANGE (metric_ts);

CREATE INDEX IF NOT EXISTS idx_metrics_resource_name_ts
    ON ops.metrics_norm(resource_id, metric_name, metric_ts DESC);

-- ============================================================
-- SAP-SPECIFIC
-- ============================================================

CREATE TABLE IF NOT EXISTS ops.sap_backups (
    backup_id    TEXT PRIMARY KEY,
    sid          TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL,
    ended_at     TIMESTAMPTZ,
    status       TEXT,                  -- running, completed, failed
    backup_type  TEXT,                  -- data, log, differential
    retained     BOOLEAN DEFAULT false,
    bytes_written BIGINT
);

CREATE TABLE IF NOT EXISTS ops.sap_alerts (
    sap_alert_id BIGSERIAL PRIMARY KEY,
    sid          TEXT NOT NULL,
    host         TEXT,
    alert_name   TEXT NOT NULL,
    priority     TEXT,
    opened_at    TIMESTAMPTZ NOT NULL,
    closed_at    TIMESTAMPTZ,
    details      JSONB DEFAULT '{}'::jsonb
);

-- ============================================================
-- DASHBOARD SELF-HEALING
-- ============================================================

CREATE TABLE IF NOT EXISTS ops.dashboard_panels (
    panel_id      TEXT PRIMARY KEY,
    panel_name    TEXT NOT NULL,
    contract_json JSONB NOT NULL,       -- expected columns, chart type, semantics
    status        TEXT NOT NULL DEFAULT 'active',  -- active, failed, healing, healed
    owner         TEXT DEFAULT 'system'
);

CREATE TABLE IF NOT EXISTS ops.panel_query_versions (
    panel_id           TEXT NOT NULL REFERENCES ops.dashboard_panels(panel_id),
    version_no         INTEGER NOT NULL,
    sql_text           TEXT NOT NULL,
    generated_by       TEXT NOT NULL,   -- human, llm, healer
    is_active          BOOLEAN NOT NULL DEFAULT false,
    healed_from_version INTEGER,
    created_at         TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (panel_id, version_no)
);

CREATE TABLE IF NOT EXISTS ops.query_failures (
    failure_id BIGSERIAL PRIMARY KEY,
    panel_id   TEXT NOT NULL REFERENCES ops.dashboard_panels(panel_id),
    failed_at  TIMESTAMPTZ DEFAULT now(),
    sqlstate   TEXT,
    error_text TEXT,
    bad_sql    TEXT
);

-- ============================================================
-- AI EVIDENCE & INCIDENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS ops.incidents (
    incident_id  TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    severity     TEXT NOT NULL DEFAULT 'warning',  -- info, warning, critical
    status       TEXT NOT NULL DEFAULT 'active',   -- active, investigating, resolved
    started_at   TIMESTAMPTZ DEFAULT now(),
    resolved_at  TIMESTAMPTZ,
    root_cause   TEXT,
    confidence   NUMERIC,
    impact_per_min_usd NUMERIC DEFAULT 11800,
    details      JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ops.evidence_runs (
    run_id      BIGSERIAL PRIMARY KEY,
    incident_id TEXT REFERENCES ops.incidents(incident_id),
    question    TEXT NOT NULL,
    sql_text    TEXT NOT NULL,
    result_json JSONB,
    row_count   INTEGER,
    confidence  NUMERIC,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.remediation_actions (
    action_id         BIGSERIAL PRIMARY KEY,
    incident_id       TEXT REFERENCES ops.incidents(incident_id),
    action_type       TEXT NOT NULL,    -- reschedule_backup, throttle_io, investigate_fan, etc.
    target_resource_id TEXT,
    status            TEXT NOT NULL DEFAULT 'suggested',  -- suggested, simulated, completed
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- HELPER: Function to create daily partitions
-- ============================================================

CREATE OR REPLACE FUNCTION ops.create_metrics_partition(target_date DATE)
RETURNS void AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_name := 'ops.metrics_norm_' || to_char(target_date, 'YYYYMMDD');
    start_date := target_date;
    end_date := target_date + 1;

    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'ops'
          AND tablename = 'metrics_norm_' || to_char(target_date, 'YYYYMMDD')
    ) THEN
        EXECUTE format(
            'CREATE TABLE %s PARTITION OF ops.metrics_norm FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create partitions for today and surrounding days
SELECT ops.create_metrics_partition(CURRENT_DATE - 1);
SELECT ops.create_metrics_partition(CURRENT_DATE);
SELECT ops.create_metrics_partition(CURRENT_DATE + 1);
