"""Demo control endpoints — start individual incidents, reset, status."""

import asyncio
from fastapi import APIRouter, HTTPException

from app.db.engine import get_pool
from app.db.seed import seed_all
from app.ws.manager import manager
from app.demo.scenarios import (
    run_full_demo,
    incident_1_sap_slowdown,
    incident_3_sql_self_heal,
    incident_4_capacity_drift,
)

router = APIRouter()

# In-memory demo state
_demo_state = {
    "running": False,
    "phase": "idle",
    "task": None,
    "completed": set(),   # track which incidents have run
}

_demo_lock = asyncio.Lock()

# Map incident number → function + metadata
_INCIDENTS = {
    1: {"fn": incident_1_sap_slowdown, "title": "SAP Slowdown"},
    2: {"fn": incident_3_sql_self_heal, "title": "SQL Self-Heal"},
    3: {"fn": incident_4_capacity_drift, "title": "Capacity Drift"},
}


@router.post("/incident/{incident_num}")
async def trigger_incident(incident_num: int):
    """Trigger a single incident by number (1-3)."""
    if incident_num not in _INCIDENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid incident number: {incident_num}. Must be 1-3.",
        )

    async with _demo_lock:
        if _demo_state["running"]:
            raise HTTPException(status_code=409, detail="An incident is already running")

        pool = await get_pool()
        meta = _INCIDENTS[incident_num]
        _demo_state["running"] = True
        _demo_state["phase"] = f"incident_{incident_num}"

        async def _run():
            try:
                await meta["fn"](pool)
                _demo_state["completed"].add(incident_num)
            finally:
                _demo_state["running"] = False
                _demo_state["phase"] = "idle"

        _demo_state["task"] = asyncio.create_task(_run())

    return {"status": "started", "incident": incident_num, "title": meta["title"]}


@router.post("/start")
async def start_demo():
    """Start the full 3-incident demo sequence (auto-sequenced)."""
    async with _demo_lock:
        if _demo_state["running"]:
            raise HTTPException(status_code=409, detail="Demo already running")

        pool = await get_pool()
        _demo_state["running"] = True
        _demo_state["phase"] = "starting"

        async def _run():
            try:
                await run_full_demo(pool)
                _demo_state["completed"] = {1, 2, 3}
            finally:
                _demo_state["running"] = False
                _demo_state["phase"] = "idle"

        _demo_state["task"] = asyncio.create_task(_run())

    return {"status": "started"}


@router.post("/reset")
async def reset_demo():
    """Reset the database to clean state and re-seed."""
    # Cancel running demo if any and await completion
    if _demo_state["task"] and not _demo_state["task"].done():
        _demo_state["task"].cancel()
        try:
            await _demo_state["task"]
        except asyncio.CancelledError:
            pass
        _demo_state["running"] = False

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Truncate all telemetry and state tables (order matters for FK constraints)
        async with conn.transaction():
            await conn.execute("DELETE FROM ops.remediation_actions")
            await conn.execute("DELETE FROM ops.evidence_runs")
            await conn.execute("DELETE FROM ops.incidents")
            await conn.execute("DELETE FROM ops.query_failures")
            await conn.execute("DELETE FROM ops.panel_query_versions")
            await conn.execute("DELETE FROM ops.dashboard_panels")
            await conn.execute("DELETE FROM ops.sap_alerts")
            await conn.execute("DELETE FROM ops.sap_backups")
            await conn.execute("DELETE FROM ops.events_norm")
            await conn.execute("DELETE FROM ops.alerts_raw")
            await conn.execute("DELETE FROM ops.metrics_norm")
            await conn.execute("DELETE FROM ops.resource_edges")
            await conn.execute("DELETE FROM ops.resources")

    # Re-seed
    await seed_all(pool)

    _demo_state["phase"] = "idle"
    _demo_state["running"] = False
    _demo_state["completed"] = set()

    await manager.broadcast("demo_phase", {
        "phase": "idle",
        "phase_number": 0,
        "title": "Ready",
        "talking_point": "Dashboard reset. Trigger an incident to begin.",
    })

    return {"status": "reset", "completed": []}


@router.get("/status")
async def demo_status():
    """Get current demo status."""
    return {
        "running": _demo_state["running"],
        "phase": _demo_state["phase"],
        "completed": sorted(_demo_state["completed"]),
    }
