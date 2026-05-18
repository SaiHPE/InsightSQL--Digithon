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
