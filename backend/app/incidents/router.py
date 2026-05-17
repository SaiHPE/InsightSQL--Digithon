"""Incident management endpoints."""

import json
from fastapi import APIRouter, HTTPException

from app.db.engine import get_pool
from app.ws.manager import manager

router = APIRouter()


@router.get("")
async def list_incidents():
    """List all incidents."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT incident_id, title, severity, status, started_at, resolved_at,
                      root_cause, confidence, impact_per_min_usd, details
               FROM ops.incidents
               ORDER BY started_at DESC"""
        )
    return [dict(r) for r in rows]


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get full incident detail with evidence and RCA."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        incident = await conn.fetchrow(
            "SELECT * FROM ops.incidents WHERE incident_id = $1", incident_id
        )
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        evidence = await conn.fetch(
            """SELECT run_id, question, sql_text, result_json, row_count, confidence, created_at
               FROM ops.evidence_runs
               WHERE incident_id = $1
               ORDER BY created_at""",
            incident_id,
        )

        actions = await conn.fetch(
            """SELECT action_id, action_type, target_resource_id, status, notes, created_at
               FROM ops.remediation_actions
               WHERE incident_id = $1
               ORDER BY created_at""",
            incident_id,
        )

    return {
        "incident": dict(incident),
        "evidence": [dict(e) for e in evidence],
        "actions": [dict(a) for a in actions],
    }


@router.post("/{incident_id}/ask")
async def ask_question(incident_id: str, body: dict):
    """Trigger an ad-hoc Text-to-SQL investigation question."""
    from app.agent.text_to_sql import investigate

    question = body.get("question", "")
    if not question:
        raise HTTPException(status_code=422, detail="question is required")

    pool = await get_pool()
    result = await investigate(pool, incident_id, question)
    return result
