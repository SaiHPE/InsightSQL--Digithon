"""Normalize raw webhook payloads into structured database rows."""

import json
from datetime import datetime, timezone

import asyncpg


async def normalize_alert(pool: asyncpg.Pool, payload: dict) -> dict:
    """Normalize a Grafana-style alert payload into alerts_raw + events_norm."""
    async with pool.acquire() as conn:
        # Store raw payload
        alert_id = await conn.fetchval(
            """INSERT INTO ops.alerts_raw (alert_group_id, source, payload)
               VALUES ($1, $2, $3::jsonb) RETURNING alert_id""",
            payload.get("groupKey", "unknown"),
            payload.get("receiver", "grafana"),
            json.dumps(payload),
        )

        # Normalize each alert in the group into events_norm
        events = []
        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            resource_id = _resolve_resource_id(labels)

            event_id = await conn.fetchval(
                """INSERT INTO ops.events_norm
                   (source, resource_id, severity, event_type, event_ts, summary, details)
                   VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                   RETURNING event_id""",
                "grafana",
                resource_id,
                "critical" if alert.get("status") == "firing" else "info",
                "alert",
                _parse_ts(alert.get("startsAt")),
                annotations.get("summary", labels.get("alertname", "Alert")),
                json.dumps({**labels, **annotations, "values": alert.get("values", {})}),
            )
            events.append({"event_id": event_id, "resource_id": resource_id})

    return {"alert_id": alert_id, "events": events}


async def normalize_metrics(pool: asyncpg.Pool, payload: dict) -> int:
    """Normalize an HPE storage/compute metrics payload into metrics_norm."""
    resource_id = payload.get("resource_id", "unknown")
    event_ts = _parse_ts(payload.get("event_ts"))
    metrics = payload.get("metrics", {})
    labels = payload.get("labels", {})

    rows = []
    for metric_name, metric_value in metrics.items():
        unit = _infer_unit(metric_name)
        rows.append((event_ts, resource_id, metric_name, float(metric_value), unit, json.dumps(labels)))

    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO ops.metrics_norm (metric_ts, resource_id, metric_name, metric_value, unit, labels)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb)""",
            rows,
        )

    return len(rows)


async def normalize_compute_event(pool: asyncpg.Pool, payload: dict) -> int:
    """Normalize an HPE compute health event into events_norm."""
    async with pool.acquire() as conn:
        event_id = await conn.fetchval(
            """INSERT INTO ops.events_norm
               (source, resource_id, severity, event_type, event_ts, summary, details)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
               RETURNING event_id""",
            payload.get("source", "mock_hpe_compute"),
            payload.get("resource_id"),
            payload.get("severity", "warning"),
            payload.get("event_type", "server_health"),
            _parse_ts(payload.get("event_ts")),
            payload.get("summary", "Compute event"),
            json.dumps(payload.get("details", {})),
        )

    # Also insert metrics if details contain numeric values
    details = payload.get("details", {})
    metric_map = {
        "temperature_c": ("host.temp.c", "C"),
        "cpu_util_pct": ("host.cpu.util_pct", "%"),
    }
    rows = []
    for key, (metric_name, unit) in metric_map.items():
        if key in details and isinstance(details[key], (int, float)):
            rows.append((
                _parse_ts(payload.get("event_ts")),
                payload.get("resource_id"),
                metric_name,
                float(details[key]),
                unit,
                "{}",
            ))

    if rows:
        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO ops.metrics_norm (metric_ts, resource_id, metric_name, metric_value, unit, labels)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb)""",
                rows,
            )

    return event_id


def _resolve_resource_id(labels: dict) -> str | None:
    """Try to resolve a resource_id from alert labels."""
    if "sid" in labels:
        return f"sap_sid:{labels['sid']}"
    if "host" in labels:
        return f"host:{labels['host']}"
    if "volume" in labels:
        return f"volume:{labels['volume']}"
    if "array" in labels:
        return f"array:{labels['array']}"
    return None


def _parse_ts(ts_str: str | None) -> datetime:
    """Parse an ISO timestamp string, defaulting to now()."""
    if not ts_str:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _infer_unit(metric_name: str) -> str:
    """Infer unit from metric name."""
    if "ms" in metric_name or "latency" in metric_name:
        return "ms"
    if "pct" in metric_name or "score" in metric_name:
        return "%"
    if "iops" in metric_name:
        return "iops"
    if "depth" in metric_name:
        return "count"
    if "temp" in metric_name:
        return "C"
    return ""
