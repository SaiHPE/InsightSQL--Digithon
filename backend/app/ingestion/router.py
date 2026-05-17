"""Webhook ingestion endpoints."""

import json
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException

from app.config import get_settings
from app.db.engine import get_pool
from app.ws.manager import manager
from app.ingestion.normalizer import normalize_alert, normalize_metrics, normalize_compute_event

router = APIRouter()


def _verify_webhook(request: Request):
    """Verify webhook API key if configured."""
    settings = get_settings()
    if not settings.webhook_api_key:
        return  # No auth configured — allow (dev mode)
    api_key = request.headers.get("X-Api-Key", "")
    if not hmac.compare_digest(api_key, settings.webhook_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def _read_json(request: Request) -> dict:
    """Parse JSON body, returning 400 for malformed payloads."""
    try:
        return await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON body")


@router.post("/alerts")
async def receive_alert(request: Request):
    """Receive a Grafana-style alert webhook payload."""
    _verify_webhook(request)
    payload = await _read_json(request)
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
    _verify_webhook(request)
    payload = await _read_json(request)
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
    _verify_webhook(request)
    payload = await _read_json(request)
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
