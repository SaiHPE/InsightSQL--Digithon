"""RCA narrative generator — produces ranked root cause analysis from evidence."""

import json
import asyncpg

from app.agent.llm import generate_json
from app.agent.prompts import RCA_NARRATIVE_SYSTEM, RCA_NARRATIVE_USER
from app.ws.manager import manager


async def generate_rca(pool: asyncpg.Pool, incident_id: str) -> dict:
    """Generate a root cause analysis narrative from collected evidence."""

    async with pool.acquire() as conn:
        # Get incident
        incident = await conn.fetchrow(
            "SELECT * FROM ops.incidents WHERE incident_id = $1", incident_id
        )
        if not incident:
            return {"error": f"Incident {incident_id} not found"}

        # Get all evidence runs
        evidence_rows = await conn.fetch(
            """SELECT question, sql_text, result_json, row_count, confidence
               FROM ops.evidence_runs
               WHERE incident_id = $1
               ORDER BY created_at""",
            incident_id,
        )

        # Get recent events for context
        events = await conn.fetch(
            """SELECT resource_id, severity, event_type, event_ts, summary
               FROM ops.events_norm
               WHERE event_ts >= now() - interval '30 minutes'
                 AND severity IN ('critical', 'warning')
               ORDER BY event_ts DESC
               LIMIT 20"""
        )

    # Format evidence for prompt
    evidence_parts = []
    for e in evidence_rows:
        result_preview = ""
        if e["result_json"]:
            try:
                rows = json.loads(e["result_json"]) if isinstance(e["result_json"], str) else e["result_json"]
                result_preview = json.dumps(rows[:5], default=str, indent=2)
            except Exception:
                result_preview = str(e["result_json"])[:500]

        evidence_parts.append(
            f"Question: {e['question']}\n"
            f"SQL: {e['sql_text'][:300]}\n"
            f"Rows returned: {e['row_count']}\n"
            f"Result preview:\n{result_preview}"
        )
    evidence_text = "\n\n---\n\n".join(evidence_parts) if evidence_parts else "No evidence collected yet."

    # Format events
    events_text = "\n".join(
        f"[{e['event_ts']}] {e['severity'].upper()} on {e['resource_id']}: {e['summary']}"
        for e in events
    ) if events else "No recent events."

    # Generate RCA
    user_prompt = RCA_NARRATIVE_USER.format(
        incident_title=incident["title"],
        started_at=str(incident["started_at"]),
        evidence_text=evidence_text,
        events_text=events_text,
    )

    rca_json_str = await generate_json(RCA_NARRATIVE_SYSTEM, user_prompt)

    try:
        rca = json.loads(rca_json_str)
    except json.JSONDecodeError:
        rca = {
            "summary": rca_json_str,
            "hypotheses": [],
            "impact": "Unable to parse structured RCA",
            "recommended_actions": [],
        }

    # Get top confidence
    top_confidence = 0.0
    if rca.get("hypotheses"):
        top_confidence = max(h.get("confidence", 0) for h in rca["hypotheses"])

    # Update incident with RCA
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE ops.incidents
               SET root_cause = $2, confidence = $3
               WHERE incident_id = $1""",
            incident_id,
            rca.get("summary", ""),
            top_confidence,
        )

    result = {
        "incident_id": incident_id,
        "rca": rca,
        "confidence": top_confidence,
    }

    await manager.broadcast("rca_generated", result)
    return result
