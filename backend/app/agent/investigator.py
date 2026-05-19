"""Autonomous AI investigation agent — generates its own investigation questions from incident context."""

import json
import logging
import asyncpg

from app.agent.llm import generate_json
from app.agent.text_to_sql import investigate
from app.agent.prompts import build_schema_map
from app.ws.manager import manager

logger = logging.getLogger(__name__)

INVESTIGATION_PLAN_SYSTEM = """You are an SRE AI agent investigating an infrastructure incident for HPE GreenLake SAP operations.

Given the incident context below, generate exactly 2 investigation questions that can each be answered with a single PostgreSQL SELECT query.

Rules:
- Each question should target a different aspect of the incident (e.g., one for metrics, one for events/backups).
- Questions should reference specific resources and metric names from the context.
- Be specific enough that a text-to-SQL engine can generate accurate queries.
- Do NOT ask for visualizations or graphs — ask for data.

Available metric names: sap.response.p95_ms, host.cpu.util_pct, host.temp.c, host.memory.util_pct, storage.latency.ms, storage.iops, storage.queue_depth, storage.saturation.score, storage.used_pct
Available resources: sap_sid:PRD, host:prd-hana-01, host:prd-hana-02, array:primera-prod-01, volume:hana_log_lun_01, volume:hana_data_lun_01, volume:hana_backup_lun_01
Backup table: ops.sap_backups (sid column uses bare SID like 'PRD')

Output format (JSON):
{
  "questions": [
    {"question": "...", "time_range_minutes": 15},
    {"question": "...", "time_range_minutes": 30}
  ]
}
"""

INVESTIGATION_PLAN_USER = """Incident: {title}
Severity: {severity}
Hint: {hint}

Recent events/alerts:
{events_summary}

Generate 2 investigation questions as JSON."""


async def autonomous_investigate(
    pool: asyncpg.Pool,
    incident_id: str,
    hint: str = "",
    title: str = "",
    severity: str = "critical",
) -> list[dict]:
    """Let the LLM decide what to investigate, then run each question through the SQL pipeline.

    Args:
        pool: Database connection pool
        incident_id: The incident being investigated
        hint: High-level guidance (e.g. "check storage and backup correlation")
        title: Incident title for context
        severity: Incident severity

    Returns:
        List of evidence results from each investigation
    """
    # Get recent events for context
    events_summary = "No recent events."
    try:
        async with pool.acquire() as conn:
            events = await conn.fetch(
                """SELECT resource_id, severity, summary, event_ts
                   FROM ops.events_norm
                   WHERE event_ts >= now() - interval '30 minutes'
                   ORDER BY event_ts DESC LIMIT 5"""
            )
            if events:
                events_summary = "\n".join(
                    f"- [{e['severity']}] {e['resource_id']}: {e['summary']} ({e['event_ts']})"
                    for e in events
                )
    except Exception:
        logger.debug("Failed to fetch recent events for investigation plan")

    # Ask LLM to generate investigation questions
    user_prompt = INVESTIGATION_PLAN_USER.format(
        title=title or f"Incident {incident_id}",
        severity=severity,
        hint=hint or "Investigate the root cause",
        events_summary=events_summary,
    )

    try:
        raw = await generate_json(INVESTIGATION_PLAN_SYSTEM, user_prompt, temperature=0.2)
        plan = json.loads(raw)
        questions = plan.get("questions", [])
    except Exception as e:
        logger.warning("LLM investigation plan failed, using hint as fallback: %s", e)
        # Fallback: use the hint as a single question
        questions = [{"question": hint, "time_range_minutes": 15}]

    if not questions:
        questions = [{"question": hint, "time_range_minutes": 15}]

    # Run each question through the text-to-SQL pipeline
    results = []
    for i, q in enumerate(questions[:3]):  # Cap at 3 questions
        question = q.get("question", "")
        time_range = q.get("time_range_minutes", 15)
        if not question:
            continue

        logger.info("[INVESTIGATE] Q%d: %s (range=%dm)", i + 1, question, time_range)
        result = await investigate(pool, incident_id, question, time_range_minutes=time_range)
        results.append(result)

    return results
