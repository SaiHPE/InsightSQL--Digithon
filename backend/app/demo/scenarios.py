"""Demo scenario scripts — 3 scripted incidents with timed injection + real LLM calls."""

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
    """Run the full 3-incident demo sequence."""
    try:
        await manager.broadcast("demo_phase", {
            "phase": "starting", "phase_number": 0,
            "title": "Demo Starting",
            "talking_point": "InsightSQL live operations dashboard initializing...",
        })
        await asyncio.sleep(2)

        await incident_1_sap_slowdown(pool)
        await asyncio.sleep(4)
        await incident_2_compute_degradation(pool)
        await asyncio.sleep(4)
        await incident_3_sql_self_heal(pool)

        await manager.broadcast("demo_phase", {
            "phase": "complete", "phase_number": 4,
            "title": "Demo Complete",
            "talking_point": "All three incidents demonstrated. InsightSQL auto-investigated, generated evidence-backed RCA, and self-healed a broken dashboard panel.",
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

    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: SAP Slowdown",
        "talking_point": "A Grafana alert fires — SAP response time spiked to 842ms, 6x the baseline.",
    })
    await asyncio.sleep(2)

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
    await asyncio.sleep(1)

    # Inject SAP + storage metrics gradually
    for i in range(10):
        ts = now + timedelta(seconds=i * 6)
        p95 = 145 + (697 * (i / 9))
        lat = 2.1 + (7.7 * (i / 9))
        iops = 8000 + (20450 * (i / 9))
        sat = 15 + (66 * (i / 9))

        await normalize_metrics(pool, {
            "resource_id": "sap_sid:PRD", "event_ts": ts.isoformat(),
            "metrics": {"sap.response.p95_ms": round(p95, 1)},
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "sap_sid:PRD",
            "metrics": {"sap.response.p95_ms": round(p95, 1)},
            "event_ts": ts.isoformat(),
        })

        await normalize_metrics(pool, {
            "resource_id": "volume:hana_log_lun_01", "event_ts": ts.isoformat(),
            "metrics": {"storage.latency.ms": round(lat, 2), "storage.iops": round(iops), "storage.saturation.score": round(sat)},
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "volume:hana_log_lun_01",
            "metrics": {"storage.latency.ms": round(lat, 2)},
            "event_ts": ts.isoformat(),
        })

        await normalize_metrics(pool, {
            "resource_id": "array:primera-prod-01", "event_ts": ts.isoformat(),
            "metrics": {"storage.latency.ms": round(lat, 2)},
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "array:primera-prod-01",
            "metrics": {"storage.latency.ms": round(lat, 2)},
            "event_ts": ts.isoformat(),
        })
        await asyncio.sleep(0.15)

    # Topology
    await manager.broadcast("topology_update", {
        "resource_id": "volume:hana_log_lun_01", "status": "critical",
        "summary": "Storage latency 9.8ms, saturation 81%",
    })
    await manager.broadcast("topology_update", {
        "resource_id": "array:primera-prod-01", "status": "warning",
        "summary": "Array latency elevated",
    })

    # Insert running backup
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.sap_backups (backup_id, sid, started_at, status, backup_type)
               VALUES ('backup-incident-001', 'PRD', $1, 'running', 'data')
               ON CONFLICT DO NOTHING""",
            now - timedelta(minutes=2),
        )
    await asyncio.sleep(1)

    # AI Investigation 1
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: AI Investigation",
        "talking_point": "InsightSQL auto-investigates. Watch the reasoning chain — schema → SQL → validate → execute.",
    })
    await asyncio.sleep(1)
    await investigate(pool, incident_id,
        "Which resource correlates most with PRD response time degradation in the last 15 minutes?",
        time_range_minutes=15)
    await asyncio.sleep(2)

    # AI Investigation 2
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: Backup Correlation",
        "talking_point": "Second query checks for backup contention.",
    })
    await investigate(pool, incident_id,
        "Was a HANA backup running during the SAP PRD slowdown? Show backup start time and status.",
        time_range_minutes=15)
    await asyncio.sleep(2)

    # RCA
    await manager.broadcast("demo_phase", {
        "phase": "incident_1", "phase_number": 1,
        "title": "Incident 1: Root Cause Analysis",
        "talking_point": "RCA names the root cause: backup I/O contention on HPE Primera log volume.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(1)

    # Remediation
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO ops.remediation_actions (incident_id, action_type, target_resource_id, status, notes)
               VALUES ('INC-001', 'reschedule_backup', 'sap_sid:PRD', 'suggested',
                       'Reschedule HANA backup to off-peak window (02:00-04:00)')""",
        )


async def incident_2_compute_degradation(pool: asyncpg.Pool):
    """Incident 2: Host thermal throttling on prd-hana-02."""
    now = datetime.now(timezone.utc)
    incident_id = "INC-001"

    await manager.broadcast("demo_phase", {
        "phase": "incident_2", "phase_number": 2,
        "title": "Incident 2: Compute Degradation",
        "talking_point": "Second issue: host prd-hana-02 reports a critical thermal event.",
    })
    await asyncio.sleep(2)

    # Compute event
    await normalize_compute_event(pool, {
        "source": "mock_hpe_compute",
        "resource_id": "host:prd-hana-02",
        "event_ts": now.isoformat(),
        "severity": "critical",
        "event_type": "server_health",
        "summary": "Thermal threshold exceeded on host prd-hana-02",
        "details": {"health_state": "Critical", "temperature_c": 72, "cpu_util_pct": 91, "fan_status": "degraded"},
    })

    # Inject host metrics
    for i in range(8):
        ts = now + timedelta(seconds=i * 6)
        temp = 40 + (32 * (i / 7))
        cpu = 45 + (46 * (i / 7))
        await normalize_metrics(pool, {
            "resource_id": "host:prd-hana-02", "event_ts": ts.isoformat(),
            "metrics": {"host.cpu.util_pct": round(cpu, 1), "host.temp.c": round(temp, 1)},
        })
        await manager.broadcast("metrics_update", {
            "resource_id": "host:prd-hana-02",
            "metrics": {"host.cpu.util_pct": round(cpu, 1), "host.temp.c": round(temp, 1)},
            "event_ts": ts.isoformat(),
        })
        await asyncio.sleep(0.15)

    await manager.broadcast("topology_update", {
        "resource_id": "host:prd-hana-02", "status": "critical",
        "summary": "Thermal threshold exceeded, fan degraded",
    })
    await asyncio.sleep(1)

    # Investigation 3
    await manager.broadcast("demo_phase", {
        "phase": "incident_2", "phase_number": 2,
        "title": "Incident 2: Re-investigation",
        "talking_point": "InsightSQL cross-correlates storage and compute metrics.",
    })
    await investigate(pool, incident_id,
        "Is the SAP PRD slowdown caused by storage contention or compute degradation? Compare storage latency with host CPU and temperature.",
        time_range_minutes=15)
    await asyncio.sleep(2)

    # Investigation 4
    await investigate(pool, incident_id,
        "Which host is degraded? Show host health events and temperature readings.",
        time_range_minutes=15)
    await asyncio.sleep(2)

    # Updated RCA
    await manager.broadcast("demo_phase", {
        "phase": "incident_2", "phase_number": 2,
        "title": "Incident 2: Updated RCA",
        "talking_point": "RCA updated — compound root cause identified.",
    })
    await generate_rca(pool, incident_id)
    await asyncio.sleep(1)


async def incident_3_sql_self_heal(pool: asyncpg.Pool):
    """Incident 3: Dashboard panel SQL breaks and auto-heals."""
    panel_id = "panel_top_hosts"

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Dashboard Self-Heal",
        "talking_point": "Now for InsightSQL's differentiator. Watch the Panel Health section.",
    })
    await asyncio.sleep(3)

    # Break the panel
    async with pool.acquire() as conn:
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
    await asyncio.sleep(3)

    # Heal using LLM
    await heal_panel(pool, panel_id)

    await manager.broadcast("demo_phase", {
        "phase": "incident_3", "phase_number": 3,
        "title": "Incident 3: Panel Healed!",
        "talking_point": "Panel restored automatically. Zero human intervention. Zero downtime.",
    })
    await asyncio.sleep(2)
