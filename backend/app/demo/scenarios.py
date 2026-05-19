"""Demo scenario scripts — 3 incidents with real data injection and autonomous AI investigation."""

import asyncio
from datetime import datetime, timedelta, timezone

import asyncpg

from app.ws.manager import manager
from app.ingestion.normalizer import normalize_alert, normalize_metrics
from app.agent.investigator import autonomous_investigate
from app.agent.rca import generate_rca
from app.agent.healer import heal_panel


async def _inject_and_broadcast(pool, resource_id, metrics, ts=None):
    """Single data path: insert metrics to DB + broadcast to frontend.

    This is the ONLY way scenario data enters the system.
    Both the dashboard panel refresh loop and the AI agent will see this data.
    """
    if ts is None:
        ts = datetime.now(timezone.utc)

    await normalize_metrics(pool, {
        "resource_id": resource_id,
        "event_ts": ts.isoformat(),
        "metrics": metrics,
    })
    await manager.broadcast("metrics_update", {
        "resource_id": resource_id,
        "metrics": metrics,
        "event_ts": ts.isoformat(),
    })


async def run_full_demo(pool: asyncpg.Pool):
    """Run the full 4-incident demo sequence."""
    try:
        await manager.broadcast("demo_phase", {
            "phase": "starting", "phase_number": 0,
            "title": "Demo Starting",
            "talking_point": "InsightSQL live operations dashboard initializing...",
        })
        await asyncio.sleep(8)

        await incident_1_sap_slowdown(pool)
        await asyncio.sleep(15)
        await incident_3_sql_self_heal(pool)
        await asyncio.sleep(15)
        await incident_4_capacity_drift(pool)

        await manager.broadcast("demo_phase", {
            "phase": "complete", "phase_number": 3,
            "title": "Demo Complete",
            "talking_point": "All three incidents demonstrated. InsightSQL auto-investigated, generated evidence-backed RCA, self-healed a broken dashboard panel, and forecast capacity risk.",
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

    # ── Insert backup (root cause) ──────────────────────────────────────
    backup_start = now - timedelta(minutes=5)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.sap_backups (backup_id, sid, started_at, status, backup_type)
               VALUES ('backup-incident-001', 'PRD', $1, 'running', 'data')
               ON CONFLICT DO NOTHING""",
            backup_start,
        )

    # ── Announce incident ───────────────────────────────────────────────
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
    await asyncio.sleep(3)

    # ── Stream metrics — single data path via _inject_and_broadcast ─────
    # Each iteration: insert to DB + broadcast to frontend.
    # Panel refresh loop will pick these up on the next 10s cycle.
    for i in range(12):
        progress = i / 11
        # Ramp from baseline → spike
        p95 = 145 + (697 * progress)       # 145 → 842 ms
        lat = 2.1 + (7.7 * progress)       # 2.1 → 9.8 ms
        iops = 8000 + (20450 * progress)
        sat = 15 + (66 * progress)

        ts = datetime.now(timezone.utc)
        await _inject_and_broadcast(pool, "sap_sid:PRD",
            {"sap.response.p95_ms": round(p95, 1)}, ts)
        await _inject_and_broadcast(pool, "volume:hana_log_lun_01",
            {"storage.latency.ms": round(lat, 2), "storage.iops": round(iops), "storage.saturation.score": round(sat)}, ts)
        await _inject_and_broadcast(pool, "array:primera-prod-01",
            {"storage.latency.ms": round(lat, 2)}, ts)
        await asyncio.sleep(1.5)

    # Topology status
    await manager.broadcast("topology_update", {
        "resource_id": "volume:hana_log_lun_01", "status": "critical",
        "summary": "Storage latency 9.8ms, saturation 81%",
    })
    await manager.broadcast("topology_update", {
        "resource_id": "array:primera-prod-01", "status": "warning",
        "summary": "Array latency elevated",
    })

    await asyncio.sleep(8)

    # ── AI Investigation (autonomous) ──────────────────────────────────
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: AI Investigation",
        "talking_point": "InsightSQL auto-investigates. Watch the reasoning chain — schema → SQL → validate → execute.",
    })
    await asyncio.sleep(3)

    await autonomous_investigate(pool, incident_id,
        hint="SAP PRD response time spiked. Check storage latency on the log volume and whether a HANA backup is running.",
        title="SAP SID PRD response time degradation",
        severity="critical",
    )
    await asyncio.sleep(8)

    # ── RCA ─────────────────────────────────────────────────────────────
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: Root Cause Analysis",
        "talking_point": "RCA names the root cause: backup I/O contention on HPE Primera log volume.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(8)

    # ── Remediation ────────────────────────────────────────────────────
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.remediation_actions (incident_id, action_type, target_resource_id, status, notes)
               VALUES ('INC-001', 'reschedule_backup', 'sap_sid:PRD', 'suggested',
                       'Reschedule HANA backup to off-peak window (02:00-04:00)')""",
        )

    await manager.broadcast("remediation_suggested", {
        "incident_id": "INC-001",
        "action_type": "reschedule_backup",
        "target_resource_id": "sap_sid:PRD",
        "status": "suggested",
        "notes": "Reschedule HANA backup to off-peak window (02:00-04:00)",
    })




async def incident_3_sql_self_heal(pool: asyncpg.Pool):
    """Incident 3: Dashboard panel SQL breaks and auto-heals."""
    panel_id = "panel_top_hosts"

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Dashboard Self-Heal",
        "talking_point": "Now for InsightSQL's differentiator. Watch the Panel Health section.",
    })
    await asyncio.sleep(8)

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
    await asyncio.sleep(10)

    # Heal using LLM
    await heal_panel(pool, panel_id)

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Panel Healed!",
        "talking_point": "Panel restored automatically. Zero human intervention. Zero downtime.",
    })
    await asyncio.sleep(8)


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
    await asyncio.sleep(4)

    # ── Stream capacity metrics — single data path ─────────────────────
    for i in range(6):
        ts = now - timedelta(hours=i * 4)
        pct = 89 - (i * 0.3)
        await _inject_and_broadcast(pool, "array:primera-prod-01",
            {"storage.used_pct": round(pct, 1)}, ts)

    await manager.broadcast("topology_update", {
        "resource_id": "array:primera-prod-01", "status": "warning",
        "summary": "Capacity 89%, forecast full in 14d",
    })
    await manager.broadcast("topology_update", {
        "resource_id": "volume:hana_backup_lun_01", "status": "warning",
        "summary": "Backup volume at 90% capacity",
    })
    await asyncio.sleep(6)

    # ── AI Investigation (autonomous) ──────────────────────────────────
    await manager.broadcast("demo_phase", {
        "phase": "incident_4", "phase_number": 4,
        "title": "Incident 4: Capacity Trend Analysis",
        "talking_point": "InsightSQL queries 30 days of capacity history to forecast the breach.",
    })

    await autonomous_investigate(pool, incident_id,
        hint="Storage array primera-prod-01 at 89% capacity. Check 30-day capacity trend and which volumes are growing fastest. Check backup retention.",
        title="GreenLake storage capacity forecast breach — primera-prod-01",
        severity="warning",
    )
    await asyncio.sleep(8)

    # ── RCA ─────────────────────────────────────────────────────────────
    await manager.broadcast("demo_phase", {
        "phase": "incident_4", "phase_number": 4,
        "title": "Incident 4: Capacity RCA",
        "talking_point": "RCA: retained HANA backups on hana_backup_lun_01 driving capacity growth.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(5)

    # ── Remediation ────────────────────────────────────────────────────
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
