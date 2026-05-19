"""Seed the database with mock inventory, topology, baseline metrics, and dashboard panels."""

import asyncpg
import random
from datetime import datetime, timedelta, timezone


async def seed_all(pool: asyncpg.Pool):
    """Run all seed functions."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Serialize seeding across concurrent app instances
            await conn.execute("SELECT pg_advisory_xact_lock(984321)")
            count = await conn.fetchval("SELECT count(*) FROM ops.resources")
            if count > 0:
                print("[SEED] Database already seeded, skipping.")
                return

            await _seed_resources(conn)
            await _seed_topology(conn)

    # These use their own connections for bulk inserts
    await seed_baseline_metrics(pool)
    await seed_baseline_backups(pool)
    await seed_capacity_history(pool)
    await seed_dashboard_panels(pool)
    print("[SEED] All seed data loaded.")


async def _seed_resources(conn):
    """Seed the resource inventory (within an existing transaction)."""
    resources = [
        # SAP SID
        ("sap_sid:PRD", "sap_sid", "SAP", "S/4HANA", "SAP PRD (Production)", "blr-dc1"),
        # Hosts
        ("host:prd-hana-01", "host", "HPE", "ProLiant Compute DL380 Gen12", "prd-hana-01", "blr-dc1"),
        ("host:prd-hana-02", "host", "HPE", "ProLiant Compute DL380 Gen12", "prd-hana-02", "blr-dc1"),
        # Storage array
        ("array:primera-prod-01", "storage_array", "HPE", "GreenLake Mission Critical Storage", "primera-prod-01", "blr-dc1"),
        # Volumes
        ("volume:hana_log_lun_01", "volume", "HPE", "Primera Volume", "hana_log_lun_01", "blr-dc1"),
        ("volume:hana_data_lun_01", "volume", "HPE", "Primera Volume", "hana_data_lun_01", "blr-dc1"),
        ("volume:hana_backup_lun_01", "volume", "HPE", "Primera Volume", "hana_backup_lun_01", "blr-dc1"),
        # Services
        ("service:sales-order", "service", "SAP", "Sales Order Processing", "Sales Order Processing", "blr-dc1"),
        ("service:payroll-batch", "service", "SAP", "Payroll Batch Processing", "Payroll Batch Processing", "blr-dc1"),
    ]

    await conn.executemany(
        """INSERT INTO ops.resources (resource_id, resource_type, vendor, product, display_name, site)
           VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT DO NOTHING""",
        resources,
    )
    print(f"[SEED] Inserted {len(resources)} resources.")


async def _seed_topology(conn):
    """Seed the resource topology edges (within an existing transaction)."""
    edges = [
        # SAP SID runs on hosts
        ("sap_sid:PRD", "host:prd-hana-01", "runs_on"),
        ("sap_sid:PRD", "host:prd-hana-02", "runs_on"),
        # Hosts use volumes
        ("host:prd-hana-01", "volume:hana_log_lun_01", "uses_volume"),
        ("host:prd-hana-01", "volume:hana_data_lun_01", "uses_volume"),
        ("host:prd-hana-02", "volume:hana_backup_lun_01", "uses_volume"),
        ("host:prd-hana-02", "volume:hana_log_lun_01", "uses_volume"),
        # Volumes hosted by array
        ("volume:hana_log_lun_01", "array:primera-prod-01", "hosted_by"),
        ("volume:hana_data_lun_01", "array:primera-prod-01", "hosted_by"),
        ("volume:hana_backup_lun_01", "array:primera-prod-01", "hosted_by"),
        # Services served by SID
        ("sap_sid:PRD", "service:sales-order", "serves"),
        ("sap_sid:PRD", "service:payroll-batch", "serves"),
    ]

    await conn.executemany(
        """INSERT INTO ops.resource_edges (src_resource_id, dst_resource_id, edge_type)
           VALUES ($1, $2, $3) ON CONFLICT DO NOTHING""",
        edges,
    )
    print(f"[SEED] Inserted {len(edges)} topology edges.")


# Keep these as public functions for backward compat, but they're called from seed_all
async def seed_resources(pool: asyncpg.Pool):
    """Seed the resource inventory."""
    async with pool.acquire() as conn:
        await _seed_resources(conn)


async def seed_topology(pool: asyncpg.Pool):
    """Seed the resource topology edges."""
    async with pool.acquire() as conn:
        await _seed_topology(conn)


async def seed_baseline_metrics(pool: asyncpg.Pool):
    """Seed 2 hours of normal baseline metrics at 1-minute intervals."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=2)

    rows = []
    minutes = int(2 * 60)  # 120 minutes

    for i in range(minutes):
        ts = start + timedelta(minutes=i)

        # SAP response time - normal: 120-160ms
        rows.append((ts, "sap_sid:PRD", "sap.response.p95_ms", 120 + random.uniform(0, 40), "ms"))

        # Host metrics - normal
        for host_id in ["host:prd-hana-01", "host:prd-hana-02"]:
            rows.append((ts, host_id, "host.cpu.util_pct", 35 + random.uniform(0, 20), "%"))
            rows.append((ts, host_id, "host.temp.c", 38 + random.uniform(0, 4), "C"))
            rows.append((ts, host_id, "host.memory.util_pct", 60 + random.uniform(0, 10), "%"))

        # Storage array metrics - normal
        rows.append((ts, "array:primera-prod-01", "storage.latency.ms", 1.5 + random.uniform(0, 1.5), "ms"))
        rows.append((ts, "array:primera-prod-01", "storage.iops", 8000 + random.uniform(0, 4000), "iops"))
        rows.append((ts, "array:primera-prod-01", "storage.queue_depth", 4 + random.uniform(0, 4), "count"))
        rows.append((ts, "array:primera-prod-01", "storage.saturation.score", 15 + random.uniform(0, 10), "%"))

        # Volume metrics - normal
        for vol_id in ["volume:hana_log_lun_01", "volume:hana_data_lun_01", "volume:hana_backup_lun_01"]:
            rows.append((ts, vol_id, "storage.latency.ms", 1.5 + random.uniform(0, 1.5), "ms"))
            rows.append((ts, vol_id, "storage.iops", 3000 + random.uniform(0, 2000), "iops"))
            rows.append((ts, vol_id, "storage.queue_depth", 2 + random.uniform(0, 3), "count"))

    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO ops.metrics_norm (metric_ts, resource_id, metric_name, metric_value, unit)
               VALUES ($1, $2, $3, $4, $5)""",
            rows,
        )
    print(f"[SEED] Inserted {len(rows)} baseline metric data points.")


async def seed_baseline_backups(pool: asyncpg.Pool):
    """Seed historical backup records (all completed normally)."""
    now = datetime.now(timezone.utc)
    backups = []

    for i in range(7):
        # Daily data backup at 02:00
        backup_start = now - timedelta(days=i+1, hours=now.hour-2)
        backups.append((
            f"backup-data-{i}",
            "PRD",
            backup_start,
            backup_start + timedelta(minutes=45),
            "completed",
            "data",
            True,
            random.randint(50_000_000_000, 80_000_000_000),
        ))

        # Log backups every 4 hours
        for h in range(0, 24, 4):
            log_start = now - timedelta(days=i+1) + timedelta(hours=h)
            backups.append((
                f"backup-log-{i}-{h}",
                "PRD",
                log_start,
                log_start + timedelta(minutes=5),
                "completed",
                "log",
                False,
                random.randint(500_000_000, 2_000_000_000),
            ))

    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO ops.sap_backups
               (backup_id, sid, started_at, ended_at, status, backup_type, retained, bytes_written)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT DO NOTHING""",
            backups,
        )
    print(f"[SEED] Inserted {len(backups)} historical backup records.")


async def seed_capacity_history(pool: asyncpg.Pool):
    """Seed 30 days of storage capacity growth data for capacity drift scenario."""
    now = datetime.now(timezone.utc)
    rows = []

    for day in range(30):
        for hour in range(0, 24, 4):  # Every 4 hours
            ts = now - timedelta(days=30 - day) + timedelta(hours=hour)
            # Linear growth from 65% to ~89% over 30 days
            base_pct = 65 + (24 * (day / 29))
            noise = random.uniform(-0.5, 0.5)

            rows.append((ts, "array:primera-prod-01", "storage.used_pct",
                         round(base_pct + noise, 1), "%"))
            # Backup volume grows faster (retention buildup)
            backup_pct = 55 + (35 * (day / 29)) + noise
            rows.append((ts, "volume:hana_backup_lun_01", "storage.used_pct",
                         round(min(backup_pct, 95), 1), "%"))

    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO ops.metrics_norm (metric_ts, resource_id, metric_name, metric_value, unit)
               VALUES ($1, $2, $3, $4, $5)""",
            rows,
        )
    print(f"[SEED] Inserted {len(rows)} capacity history data points (30 days).")


async def seed_dashboard_panels(pool: asyncpg.Pool):
    """Seed dashboard panels with working SQL queries."""
    import json

    panels = [
        {
            "panel_id": "panel_sap_p95",
            "panel_name": "SAP Response Time",
            "contract_json": json.dumps({
                "columns": [{"name": "minute", "type": "timestamptz"}, {"name": "p95_ms", "type": "numeric"}],
                "chart_type": "line",
            }),
            "sql": """SELECT date_trunc('minute', metric_ts) AS minute,
                             avg(metric_value) AS p95_ms
                      FROM ops.metrics_norm
                      WHERE resource_id = 'sap_sid:PRD'
                        AND metric_name = 'sap.response.p95_ms'
                        AND metric_ts >= now() - interval '2 hours'
                      GROUP BY 1 ORDER BY 1""",
        },
        {
            "panel_id": "panel_storage_lat",
            "panel_name": "Storage Latency",
            "contract_json": json.dumps({
                "columns": [{"name": "minute", "type": "timestamptz"}, {"name": "latency_ms", "type": "numeric"}],
                "chart_type": "line",
            }),
            "sql": """SELECT date_trunc('minute', metric_ts) AS minute,
                             avg(metric_value) AS latency_ms
                      FROM ops.metrics_norm
                      WHERE resource_id = 'array:primera-prod-01'
                        AND metric_name = 'storage.latency.ms'
                        AND metric_ts >= now() - interval '2 hours'
                      GROUP BY 1 ORDER BY 1""",
        },
        {
            "panel_id": "panel_top_hosts",
            "panel_name": "Top Hosts by CPU Load",
            "contract_json": json.dumps({
                "columns": [{"name": "label", "type": "text"}, {"name": "value", "type": "numeric"}],
                "chart_type": "bar",
            }),
            "sql": """SELECT r.display_name AS label,
                             round(avg(m.metric_value)::numeric, 1) AS value
                      FROM ops.metrics_norm m
                      JOIN ops.resources r ON r.resource_id = m.resource_id
                      WHERE r.resource_type = 'host'
                        AND m.metric_name = 'host.cpu.util_pct'
                        AND m.metric_ts >= now() - interval '30 minutes'
                      GROUP BY r.display_name
                      ORDER BY value DESC""",
        },
        {
            "panel_id": "panel_top_volumes",
            "panel_name": "Hot Volumes",
            "contract_json": json.dumps({
                "columns": [
                    {"name": "label", "type": "text"},
                    {"name": "latency_ms", "type": "numeric"},
                    {"name": "iops", "type": "numeric"},
                ],
                "chart_type": "table",
            }),
            "sql": """SELECT r.display_name AS label,
                             round(avg(CASE WHEN m.metric_name = 'storage.latency.ms' THEN m.metric_value END)::numeric, 2) AS latency_ms,
                             round(avg(CASE WHEN m.metric_name = 'storage.iops' THEN m.metric_value END)::numeric, 0) AS iops
                      FROM ops.metrics_norm m
                      JOIN ops.resources r ON r.resource_id = m.resource_id
                      WHERE r.resource_type = 'volume'
                        AND m.metric_ts >= now() - interval '30 minutes'
                      GROUP BY r.display_name
                      ORDER BY latency_ms DESC""",
        },
        {
            "panel_id": "panel_alert_count",
            "panel_name": "Alert Summary",
            "contract_json": json.dumps({
                "columns": [{"name": "severity", "type": "text"}, {"name": "count", "type": "integer"}],
                "chart_type": "stat",
            }),
            "sql": """SELECT severity, count(*) AS count
                      FROM ops.events_norm
                      WHERE event_ts >= now() - interval '1 hour'
                        AND severity IS NOT NULL
                      GROUP BY severity
                      ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END""",
        },
    ]

    async with pool.acquire() as conn:
        async with conn.transaction():
            for p in panels:
                await conn.execute(
                    """INSERT INTO ops.dashboard_panels (panel_id, panel_name, contract_json, status)
                       VALUES ($1, $2, $3::jsonb, 'active') ON CONFLICT DO NOTHING""",
                    p["panel_id"], p["panel_name"], p["contract_json"],
                )
                await conn.execute(
                    """INSERT INTO ops.panel_query_versions (panel_id, version_no, sql_text, generated_by, is_active)
                       VALUES ($1, 1, $2, 'human', true) ON CONFLICT DO NOTHING""",
                    p["panel_id"], p["sql"],
                )
    print(f"[SEED] Inserted {len(panels)} dashboard panels with v1 queries.")
