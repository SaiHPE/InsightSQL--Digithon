"""Webhook ingestion endpoints."""

from fastapi import APIRouter, Request

from app.db.engine import get_pool
from app.ws.manager import manager
from app.ingestion.normalizer import normalize_alert, normalize_metrics, normalize_compute_event

router = APIRouter()


@router.post("/alerts")
async def receive_alert(request: Request):
    """Receive a Grafana-style alert webhook payload."""
    payload = await request.json()
    pool = await get_pool()

    result = normalize_alert(pool, payload)
    result = await result

    # Broadcast to dashboard
    await manager.broadcast("alert_received", {
        "alert_id": result["alert_id"],
        "events": result["events"],
        "status": payload.get("status", "firing"),
        "alerts": payload.get("alerts", []),
    })

    return {"status": "ok", "alert_id": result["alert_id"], "events_created": len(result["events"])}


@router.post("/metrics")
async def receive_metrics(request: Request):
    """Receive HPE storage/compute metrics payload."""
    payload = await request.json()
    pool = await get_pool()

    count = await normalize_metrics(pool, payload)

    # Broadcast to dashboard
    await manager.broadcast("metrics_update", {
        "resource_id": payload.get("resource_id"),
        "metrics": payload.get("metrics", {}),
        "event_ts": payload.get("event_ts"),
    })

    return {"status": "ok", "metrics_inserted": count}


@router.post("/events")
async def receive_compute_event(request: Request):
    """Receive HPE compute health event."""
    payload = await request.json()
    pool = await get_pool()

    event_id = await normalize_compute_event(pool, payload)

    # Broadcast to dashboard
    await manager.broadcast("alert_received", {
        "event_id": event_id,
        "resource_id": payload.get("resource_id"),
        "severity": payload.get("severity"),
        "summary": payload.get("summary"),
        "event_type": payload.get("event_type"),
    })

    return {"status": "ok", "event_id": event_id}
