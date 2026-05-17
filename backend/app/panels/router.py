"""Dashboard panel management and self-healing endpoints."""

import json
import asyncpg
from fastapi import APIRouter, HTTPException

from app.db.engine import get_pool
from app.ws.manager import manager

router = APIRouter()


@router.get("")
async def list_panels():
    """List all dashboard panels with their health status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        panels = await conn.fetch(
            """SELECT p.panel_id, p.panel_name, p.status, p.contract_json,
                      v.version_no, v.generated_by, v.sql_text, v.created_at AS version_created
               FROM ops.dashboard_panels p
               LEFT JOIN ops.panel_query_versions v
                 ON v.panel_id = p.panel_id AND v.is_active = true
               ORDER BY p.panel_id"""
        )
    return [dict(r) for r in panels]


@router.get("/{panel_id}/versions")
async def get_panel_versions(panel_id: str):
    """Get version history for a panel."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        versions = await conn.fetch(
            """SELECT version_no, sql_text, generated_by, is_active, healed_from_version, created_at
               FROM ops.panel_query_versions
               WHERE panel_id = $1
               ORDER BY version_no DESC""",
            panel_id,
        )
        failures = await conn.fetch(
            """SELECT failure_id, failed_at, sqlstate, error_text, bad_sql
               FROM ops.query_failures
               WHERE panel_id = $1
               ORDER BY failed_at DESC
               LIMIT 10""",
            panel_id,
        )
    return {
        "panel_id": panel_id,
        "versions": [dict(v) for v in versions],
        "failures": [dict(f) for f in failures],
    }


@router.post("/{panel_id}/execute")
async def execute_panel(panel_id: str):
    """Execute the active SQL for a panel and return results."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT v.sql_text, p.contract_json
               FROM ops.panel_query_versions v
               JOIN ops.dashboard_panels p ON p.panel_id = v.panel_id
               WHERE v.panel_id = $1 AND v.is_active = true""",
            panel_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="No active query for panel")

        try:
            async with conn.transaction():
                await conn.execute("SET TRANSACTION READ ONLY")
                results = await conn.fetch(row["sql_text"])
            return {
                "panel_id": panel_id,
                "status": "ok",
                "rows": [dict(r) for r in results],
                "row_count": len(results),
            }
        except asyncpg.PostgresError as e:
            # Record failure
            await conn.execute(
                """INSERT INTO ops.query_failures (panel_id, error_text, bad_sql)
                   VALUES ($1, $2, $3)""",
                panel_id, str(e), row["sql_text"],
            )
            await conn.execute(
                "UPDATE ops.dashboard_panels SET status = 'failed' WHERE panel_id = $1",
                panel_id,
            )
            await manager.broadcast("panel_failed", {
                "panel_id": panel_id,
                "error": str(e),
                "sql": row["sql_text"],
            })
            return {"panel_id": panel_id, "status": "failed", "error": str(e)}


@router.post("/{panel_id}/heal")
async def heal_panel(panel_id: str):
    """Trigger SQL healing for a broken panel."""
    from app.agent.healer import heal_panel as do_heal

    pool = await get_pool()
    result = await do_heal(pool, panel_id)
    return result


@router.post("/{panel_id}/break")
async def break_panel(panel_id: str):
    """Intentionally break a panel for demo purposes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get current active SQL
        row = await conn.fetchrow(
            """SELECT sql_text, version_no FROM ops.panel_query_versions
               WHERE panel_id = $1 AND is_active = true""",
            panel_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="No active query found")

        # Break it by replacing display_name with resource_name
        broken_sql = row["sql_text"].replace("display_name", "resource_name")
        if broken_sql == row["sql_text"]:
            # Try another break pattern
            broken_sql = row["sql_text"].replace("resource_id", "resource_uuid")

        new_version = row["version_no"] + 1

        # Atomic version switch — deactivate old, insert broken, update panel in one transaction
        async with conn.transaction():
            await conn.execute(
                """UPDATE ops.panel_query_versions SET is_active = false
                   WHERE panel_id = $1 AND version_no = $2""",
                panel_id, row["version_no"],
            )
            await conn.execute(
                """INSERT INTO ops.panel_query_versions
                   (panel_id, version_no, sql_text, generated_by, is_active)
                   VALUES ($1, $2, $3, 'human', true)""",
                panel_id, new_version, broken_sql,
            )
            await conn.execute(
                "UPDATE ops.dashboard_panels SET status = 'failed' WHERE panel_id = $1",
                panel_id,
            )

    await manager.broadcast("panel_failed", {
        "panel_id": panel_id,
        "error": "column \"resource_name\" does not exist",
        "sql": broken_sql,
        "version_no": new_version,
    })

    return {"status": "broken", "panel_id": panel_id, "broken_sql": broken_sql}
