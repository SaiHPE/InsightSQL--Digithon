"""Demo control endpoints — start, reset, status."""

import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.db.engine import get_pool
from app.db.seed import seed_all
from app.ws.manager import manager
from app.demo.scenarios import run_full_demo

router = APIRouter()

# In-memory demo state
_demo_state = {
    "running": False,
    "phase": "idle",
    "task": None,
}

_demo_lock = asyncio.Lock()


@router.post("/start")
async def start_demo(background_tasks: BackgroundTasks):
    """Start the full 3-incident demo sequence."""
    async with _demo_lock:
        if _demo_state["running"]:
            raise HTTPException(status_code=409, detail="Demo already running")

        pool = await get_pool()
        _demo_state["running"] = True
        _demo_state["phase"] = "starting"

        async def _run():
            try:
                await run_full_demo(pool)
            finally:
                _demo_state["running"] = False
                _demo_state["phase"] = "idle"

        # Run in background
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

    await manager.broadcast("demo_phase", {
        "phase": "idle",
        "phase_number": 0,
        "title": "Ready",
        "talking_point": "Dashboard reset. Click Run Demo to begin.",
    })

    return {"status": "reset"}


@router.get("/status")
async def demo_status():
    """Get current demo status."""
    return {
        "running": _demo_state["running"],
        "phase": _demo_state["phase"],
    }
