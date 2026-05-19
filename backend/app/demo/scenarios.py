"""Demo scenario scripts — 4 scripted incidents with timed injection + real LLM calls."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import asyncpg

from app.ws.manager import manager
from app.ingestion.normalizer import normalize_alert, normalize_metrics, normalize_compute_event
from app.agent.text_to_sql import investigate
from app.agent.rca import generate_rca
from app.agent.healer import heal_panel


async def run_full_demo(pool: asyncpg.Pool):
    """Run the full 4-incident demo sequence."""
    try:
        await manager.broadcast("demo_phase", {
            "phase": "starting", "phase_number": 0,
            "title": "Demo Starting",
            "talking_point": "InsightSQL live operations dashboard initializing...",
        })
        await asyncio.sleep(5)

        await incident_1_sap_slowdown(pool)
        await asyncio.sleep(8)
        await incident_2_compute_degradation(pool)
        await asyncio.sleep(8)
        await incident_3_sql_self_heal(pool)
        await asyncio.sleep(8)
        await incident_4_capacity_drift(pool)

        await manager.broadcast("demo_phase", {
            "phase": "complete", "phase_number": 4,
            "title": "Demo Complete",
            "talking_point": "All four incidents demonstrated. InsightSQL auto-investigated, generated evidence-backed RCA, self-healed a broken dashboard panel, and forecast capacity risk.",
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        await manager.broadcast("demo_phase", {
            "phase": "error", "phase_number": 0,
            "title": "Demo Error",
            "talking_point": f"Error: {str(e)}",
        })


async def incident_1_sap_slowdown(pool: asyncpg.Pool):
    """Incident 1: SAP transaction slowdown from backup + storage contention."""
    now = datetime.now(timezone.utc)
    incident_id = "INC-001"

    # ── Phase 0: Pre-inject ALL DB data with backdated timestamps ──────
    # This ensures investigation queries always find the spike data.

    # Backup started 8 minutes ago — clearly within any 30-min query window
    backup_start = now - timedelta(minutes=8)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.sap_backups (backup_id, sid, started_at, status, backup_type)
               VALUES ('backup-incident-001', 'PRD', $1, 'running', 'data')
               ON CONFLICT DO NOTHING""",
            backup_start,
        )

    # Inject 10 minutes of metrics: minutes -10 to -1
    # First 4 minutes: normal baseline, last 6 minutes: clear spike
    metric_rows = []
    for i in range(10):
        ts = now - timedelta(minutes=10 - i)
        if i < 4:
            # Normal baseline
            p95 = 140 + (i * 3)         # 140–149 ms
            lat = 2.0 + (i * 0.15)      # 2.0–2.45 ms
            iops = 8000 + (i * 300)
            sat = 14 + i
        else:
            # Spike after backup kicks in
            progress = (i - 4) / 5
            p95 = 250 + (592 * progress)   # 250 → 842
            lat = 4.0 + (5.8 * progress)   # 4.0 → 9.8
            iops = 12000 + (16450 * progress)
            sat = 30 + (51 * progress)      # 30 → 81

        metric_rows.extend([
            (ts, "sap_sid:PRD", "sap.response.p95_ms", round(p95, 1), "ms"),
            (ts, "volume:hana_log_lun_01", "storage.latency.ms", round(lat, 2), "ms"),
            (ts, "volume:hana_log_lun_01", "storage.iops", round(iops), "iops"),
            (ts, "volume:hana_log_lun_01", "storage.saturation.score", round(sat), "%"),
            (ts, "array:primera-prod-01", "storage.latency.ms", round(lat, 2), "ms"),
        ])

    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO ops.metrics_norm (metric_ts, resource_id, metric_name, metric_value, unit)
               VALUES ($1, $2, $3, $4, $5)""",
            metric_rows,
        )

    # ── Phase 1: Visual flow — broadcasts + sleeps for UI ──────────────

    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: SAP Slowdown",
        "talking_point": "A HANA backup is running. Now a Grafana alert fires — SAP response time spiked to 842ms.",
    })
    await asyncio.sleep(4)

    # Create incident
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.incidents (incident_id, title, severity, status, impact_per_min_usd)
               VALUES ($1, $2, 'critical', 'active', 11800)
               ON CONFLICT (incident_id) DO UPDATE SET status = 'active', severity = 'critical'""",
            incident_id, "SAP SID PRD response time degradation",
        )

    await manager.broadcast("incident_created", {
        "incident_id": incident_id,
        "title": "SAP SID PRD response time degradation",
        "severity": "critical",
        "impact_per_min_usd": 11800,
    })

    # Fire alert
    alert_payload = {
        "receiver": "InsightSQL-Incidents", "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {"alertname": "SapResponseHigh", "sid": "PRD", "service": "sales-order"},
            "annotations": {"summary": "SAP PRD p95 response time elevated to 842ms"},
            "startsAt": now.isoformat(),
        }],
        "groupKey": "{sid=\"PRD\"}",
    }
    await normalize_alert(pool, alert_payload)
    await manager.broadcast("alert_received", {"status": "firing", "alerts": alert_payload["alerts"]})
    await asyncio.sleep(2)

    # Stream spike metrics to UI charts (data already in DB, this is just visual)
    for i in range(6):
        progress = i / 5
        p95 = 250 + (592 * progress)
        lat = 4.0 + (5.8 * progress)
        await manager.broadcast("metrics_update", {
            "resource_id": "sap_sid:PRD",
            "metrics": {"sap.response.p95_ms": round(p95, 1)},
            "event_ts": datetime.now(timezone.utc).isoformat(),
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "volume:hana_log_lun_01",
            "metrics": {"storage.latency.ms": round(lat, 2)},
            "event_ts": datetime.now(timezone.utc).isoformat(),
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "array:primera-prod-01",
            "metrics": {"storage.latency.ms": round(lat, 2)},
            "event_ts": datetime.now(timezone.utc).isoformat(),
        })
        await asyncio.sleep(1)

    # Topology
    await manager.broadcast("topology_update", {
        "resource_id": "volume:hana_log_lun_01", "status": "critical",
        "summary": "Storage latency 9.8ms, saturation 81%",
    })
    await manager.broadcast("topology_update", {
        "resource_id": "array:primera-prod-01", "status": "warning",
        "summary": "Array latency elevated",
    })

    await asyncio.sleep(6)

    # ── Phase 2: AI Investigation ──────────────────────────────────────

    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: AI Investigation",
        "talking_point": "InsightSQL auto-investigates. Watch the reasoning chain — schema → SQL → validate → execute.",
    })
    await asyncio.sleep(3)
    await investigate(pool, incident_id,
        "Show SAP PRD response time alongside storage latency on the log volume over the last 15 minutes, grouped by minute.",
        time_range_minutes=15)
    await asyncio.sleep(8)

    # AI Investigation 2
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: Backup Correlation",
        "talking_point": "Second query checks for backup contention.",
    })
    await investigate(pool, incident_id,
        "Are there any SAP HANA backups for SID PRD that started in the last 30 minutes? Show their start time, status, and type.",
        time_range_minutes=30)
    await asyncio.sleep(8)

    # RCA
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: Root Cause Analysis",
        "talking_point": "RCA names the root cause: backup I/O contention on HPE Primera log volume.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(5)

    # Remediation
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.remediation_actions (incident_id, action_type, target_resource_id, status, notes)
               VALUES ('INC-001', 'reschedule_backup', 'sap_sid:PRD', 'suggested',
                       'Reschedule HANA backup to off-peak window (02:00-04:00)')""",
        )

    # Broadcast remediation for action panel
    await manager.broadcast("remediation_suggested", {
        "incident_id": "INC-001",
        "action_type": "reschedule_backup",
        "target_resource_id": "sap_sid:PRD",
        "status": "suggested",
        "notes": "Reschedule HANA backup to off-peak window (02:00-04:00)",
    })


async def incident_2_compute_degradation(pool: asyncpg.Pool):
    """Incident 2: Host thermal throttling on prd-hana-02."""
    now = datetime.now(timezone.utc)
    incident_id = "INC-002"

    # ── Phase 0: Pre-inject compute metrics with backdated timestamps ──
    # Compute event
    await normalize_compute_event(pool, {
        "source": "mock_hpe_compute",
        "resource_id": "host:prd-hana-02",
        "event_ts": (now - timedelta(minutes=5)).isoformat(),
        "severity": "critical",
        "event_type": "server_health",
        "summary": "Thermal threshold exceeded on host prd-hana-02",
        "details": {"health_state": "Critical", "temperature_c": 72, "cpu_util_pct": 91, "fan_status": "degraded"},
    })

    # Inject 8 minutes of host metrics: temp rising from 40→72, CPU from 45→91
    metric_rows = []
    for i in range(8):
        ts = now - timedelta(minutes=8 - i)
        temp = 40 + (32 * (i / 7))
        cpu = 45 + (46 * (i / 7))
        metric_rows.extend([
            (ts, "host:prd-hana-02", "host.cpu.util_pct", round(cpu, 1), "%"),
            (ts, "host:prd-hana-02", "host.temp.c", round(temp, 1), "C"),
        ])

    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO ops.metrics_norm (metric_ts, resource_id, metric_name, metric_value, unit)
               VALUES ($1, $2, $3, $4, $5)""",
            metric_rows,
        )

    # ── Phase 1: Visual flow ──────────────────────────────────────────

    # Create incident
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.incidents (incident_id, title, severity, status, impact_per_min_usd)
               VALUES ($1, $2, 'critical', 'active', 8500)
               ON CONFLICT (incident_id) DO UPDATE SET status = 'active', severity = 'critical'""",
            incident_id, "Host thermal throttling — prd-hana-02",
        )

    await manager.broadcast("incident_created", {
        "incident_id": incident_id,
        "title": "Host thermal throttling — prd-hana-02",
        "severity": "critical",
        "impact_per_min_usd": 8500,
    })

    await manager.broadcast("demo_phase", {
        "phase": "incident_2", "phase_number": 2,
        "title": "Incident 2: Compute Degradation",
        "talking_point": "Second issue: host prd-hana-02 reports a critical thermal event.",
    })
    await asyncio.sleep(6)

    # Stream host metrics to UI (data already in DB)
    for i in range(6):
        progress = i / 5
        temp = 50 + (22 * progress)
        cpu = 55 + (36 * progress)
        await manager.broadcast("metrics_update", {
            "resource_id": "host:prd-hana-02",
            "metrics": {"host.cpu.util_pct": round(cpu, 1), "host.temp.c": round(temp, 1)},
            "event_ts": datetime.now(timezone.utc).isoformat(),
        })
        await asyncio.sleep(1)

    await manager.broadcast("topology_update", {
        "resource_id": "host:prd-hana-02", "status": "critical",
        "summary": "Thermal threshold exceeded, fan degraded",
    })
    await asyncio.sleep(4)

    # Investigation 3
    await manager.broadcast("demo_phase", {
        "phase": "incident_2", "phase_number": 2,
        "title": "Incident 2: Re-investigation",
        "talking_point": "InsightSQL cross-correlates storage and compute metrics.",
    })
    await investigate(pool, incident_id,
        "Compare average CPU utilization, temperature, and storage latency for each host and storage resource over the last 15 minutes.",
        time_range_minutes=15)
    await asyncio.sleep(8)

    # Investigation 4
    await investigate(pool, incident_id,
        "List all critical and warning events for hosts in the last 30 minutes, including severity, summary, and timestamp.",
        time_range_minutes=30)
    await asyncio.sleep(8)

    # Updated RCA
    await manager.broadcast("demo_phase", {
        "phase": "incident_2", "phase_number": 2,
        "title": "Incident 2: Updated RCA",
        "talking_point": "RCA updated — compound root cause identified.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(5)


async def incident_3_sql_self_heal(pool: asyncpg.Pool):
    """Incident 3: Dashboard panel SQL breaks and auto-heals."""
    panel_id = "panel_top_hosts"

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Dashboard Self-Heal",
        "talking_point": "Now for InsightSQL's differentiator. Watch the Panel Health section.",
    })
    await asyncio.sleep(6)

    # Break the panel — atomic transaction
    async with pool.acquire() as conn:
        async with conn.transaction():
            active = await conn.fetchrow(
                "SELECT version_no, sql_text FROM ops.panel_query_versions WHERE panel_id = $1 AND is_active = true",
                panel_id,
            )
            if not active:
                return

            broken_sql = active["sql_text"].replace("display_name", "resource_name")
            new_version = active["version_no"] + 1

            await conn.execute("UPDATE ops.panel_query_versions SET is_active = false WHERE panel_id = $1", panel_id)
            await conn.execute(
                """INSERT INTO ops.panel_query_versions (panel_id, version_no, sql_text, generated_by, is_active)
                   VALUES ($1, $2, $3, 'human', true)""",
                panel_id, new_version, broken_sql,
            )
            await conn.execute("UPDATE ops.dashboard_panels SET status = 'failed' WHERE panel_id = $1", panel_id)
            await conn.execute(
                """INSERT INTO ops.query_failures (panel_id, error_text, bad_sql)
                   VALUES ($1, 'column \"resource_name\" does not exist', $2)""",
                panel_id, broken_sql,
            )

    await manager.broadcast("panel_failed", {
        "panel_id": panel_id, "panel_name": "Top Hosts by CPU Load",
        "error": 'column "resource_name" does not exist',
        "sql": broken_sql, "version_no": new_version,
    })

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Panel Failed!",
        "talking_point": "Top Hosts panel just broke — a column was renamed. InsightSQL auto-heals it.",
    })
    await asyncio.sleep(8)

    # Heal using LLM
    await heal_panel(pool, panel_id)

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Panel Healed!",
        "talking_point": "Panel restored automatically. Zero human intervention. Zero downtime.",
    })
    await asyncio.sleep(6)


async def incident_4_capacity_drift(pool: asyncpg.Pool):
    """Incident 4: GreenLake capacity forecast breach — storage trending full."""
    now = datetime.now(timezone.utc)
    incident_id = "INC-004"

    await manager.broadcast("demo_phase", {
        "phase": "incident_4", "phase_number": 4,
        "title": "Incident 4: Capacity Forecast Breach",
        "talking_point": "New alert: Primera storage array at 89% capacity, projected full in 14 days.",
    })
    await asyncio.sleep(4)

    # Create incident
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.incidents (incident_id, title, severity, status, impact_per_min_usd)
               VALUES ($1, $2, 'warning', 'active', 0)
               ON CONFLICT (incident_id) DO UPDATE SET status = 'active', severity = 'warning'""",
            incident_id, "GreenLake storage capacity forecast breach — primera-prod-01",
        )

    await manager.broadcast("incident_created", {
        "incident_id": incident_id,
        "title": "GreenLake storage capacity forecast breach — primera-prod-01",
        "severity": "warning",
        "impact_per_min_usd": 0,
    })

    # Fire alert
    alert_payload = {
        "receiver": "InsightSQL-Incidents", "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {"alertname": "StorageCapacityHigh", "array": "primera-prod-01"},
            "annotations": {"summary": "Primera array primera-prod-01 at 89% capacity, forecast full in 14 days"},
            "startsAt": now.isoformat(),
        }],
        "groupKey": "{array=\"primera-prod-01\"}",
    }
    await normalize_alert(pool, alert_payload)
    await manager.broadcast("alert_received", {"status": "firing", "alerts": alert_payload["alerts"]})
    await asyncio.sleep(5)

    # Inject recent capacity metrics (showing current 89%)
    for i in range(6):
        ts = now - timedelta(hours=i * 4)
        pct = 89 - (i * 0.3)  # Showing recent trend
        await normalize_metrics(pool, {
            "resource_id": "array:primera-prod-01", "event_ts": ts.isoformat(),
            "metrics": {"storage.used_pct": round(pct, 1)},
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "array:primera-prod-01",
            "metrics": {"storage.used_pct": round(pct, 1)},
            "event_ts": ts.isoformat(),
        })

    await manager.broadcast("topology_update", {
        "resource_id": "array:primera-prod-01", "status": "warning",
        "summary": "Capacity 89%, forecast full in 14d",
    })
    await manager.broadcast("topology_update", {
        "resource_id": "volume:hana_backup_lun_01", "status": "warning",
        "summary": "Backup volume at 90% capacity",
    })
    await asyncio.sleep(5)

    # Investigation 1: Capacity trend
    await manager.broadcast("demo_phase", {
        "phase": "incident_4", "phase_number": 4,
        "title": "Incident 4: Capacity Trend Analysis",
        "talking_point": "InsightSQL queries 30 days of capacity history to forecast the breach.",
    })
    await investigate(pool, incident_id,
        "Show the daily average storage used percentage for the Primera array over the last 30 days, ordered by date.",
        time_range_minutes=43200)  # 30 days
    await asyncio.sleep(8)

    # Investigation 2: What's consuming space
    await manager.broadcast("demo_phase", {
        "phase": "incident_4", "phase_number": 4,
        "title": "Incident 4: Root Cause — Backup Retention",
        "talking_point": "Which volume is growing fastest? InsightSQL identifies the backup volume.",
    })
    await investigate(pool, incident_id,
        "Show the latest storage used percentage for each volume, and how many retained backups exist per SID.",
        time_range_minutes=43200)
    await asyncio.sleep(8)

    # RCA
    await manager.broadcast("demo_phase", {
        "phase": "incident_4", "phase_number": 4,
        "title": "Incident 4: Capacity RCA",
        "talking_point": "RCA: retained HANA backups on hana_backup_lun_01 driving capacity growth.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(5)

    # Remediation
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.remediation_actions (incident_id, action_type, target_resource_id, status, notes)
               VALUES ($1, 'adjust_retention', 'volume:hana_backup_lun_01', 'suggested',
                       'Reduce backup retention from 30 days to 14 days to reclaim ~25% capacity')""",
            incident_id,
        )
        await conn.execute(
            """INSERT INTO ops.remediation_actions (incident_id, action_type, target_resource_id, status, notes)
               VALUES ($1, 'expand_capacity', 'array:primera-prod-01', 'suggested',
                       'Request GreenLake capacity expansion via Consumption Analytics portal')""",
            incident_id,
        )

    await manager.broadcast("remediation_suggested", {
        "incident_id": incident_id,
        "action_type": "adjust_retention",
        "target_resource_id": "volume:hana_backup_lun_01",
        "status": "suggested",
        "notes": "Reduce backup retention from 30 days to 14 days to reclaim ~25% capacity",
    })
    await manager.broadcast("remediation_suggested", {
        "incident_id": incident_id,
        "action_type": "expand_capacity",
        "target_resource_id": "array:primera-prod-01",
        "status": "suggested",
        "notes": "Request GreenLake capacity expansion via Consumption Analytics portal",
    })

