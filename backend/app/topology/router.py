"""Topology graph endpoint for the dashboard."""

from fastapi import APIRouter

from app.db.engine import get_pool

router = APIRouter()


@router.get("")
async def get_topology():
    """Get full resource topology graph (nodes + edges) with live status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get all resources as nodes
        resources = await conn.fetch(
            """SELECT resource_id, resource_type, vendor, product, display_name, site, labels
               FROM ops.resources
               ORDER BY resource_type, display_name"""
        )

        # Get all edges
        edges = await conn.fetch(
            """SELECT src_resource_id, dst_resource_id, edge_type, confidence
               FROM ops.resource_edges"""
        )

        # Get latest health status per resource from recent events
        health = await conn.fetch(
            """SELECT DISTINCT ON (resource_id)
                      resource_id, severity, summary
               FROM ops.events_norm
               WHERE event_ts >= now() - interval '30 minutes'
                 AND severity IN ('critical', 'warning')
               ORDER BY resource_id, event_ts DESC"""
        )

    health_map = {r["resource_id"]: {"severity": r["severity"], "summary": r["summary"]} for r in health}

    nodes = []
    for r in resources:
        node = dict(r)
        node["status"] = health_map.get(r["resource_id"], {}).get("severity", "ok")
        node["status_summary"] = health_map.get(r["resource_id"], {}).get("summary", "")
        nodes.append(node)

    return {
        "nodes": nodes,
        "edges": [dict(e) for e in edges],
    }


@router.get("/metrics-baseline")
async def get_metrics_baseline():
    """Return recent baseline metrics for initial dashboard population."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Last 2 hours of key metrics for chart + KPI cards
        rows = await conn.fetch(
            """SELECT metric_ts, resource_id, metric_name, metric_value
               FROM ops.metrics_norm
               WHERE metric_ts >= now() - interval '2 hours'
               ORDER BY metric_ts
               LIMIT 5000"""
        )

    # Group into timeline format the frontend expects
    timeline = []
    latest = {}
    for r in rows:
        key = f"{r['resource_id']}:{r['metric_name']}"
        latest[key] = {"value": float(r["metric_value"]), "ts": r["metric_ts"].isoformat()}
        timeline.append({
            "ts": r["metric_ts"].isoformat(),
            "resource_id": r["resource_id"],
            r["metric_name"]: float(r["metric_value"]),
        })

    return {"timeline": timeline, "latest": latest}
