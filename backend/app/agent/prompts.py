"""Prompt templates and schema map builder for the AI agent."""

import asyncpg


async def build_schema_map(pool: asyncpg.Pool) -> str:
    """Query information_schema and build a formatted schema map for prompt injection."""
    async with pool.acquire() as conn:
        columns = await conn.fetch(
            """SELECT table_name, column_name, data_type
               FROM information_schema.columns
               WHERE table_schema = 'ops'
               ORDER BY table_name, ordinal_position"""
        )

    # Group by table
    tables: dict[str, list[str]] = {}
    for row in columns:
        table = row["table_name"]
        col_str = f"{row['column_name']}({row['data_type']})"
        tables.setdefault(table, []).append(col_str)

    lines = ["Schema: ops"]
    for table, cols in sorted(tables.items()):
        lines.append(f"Table: {table} — columns: {', '.join(cols)}")

    return "\n".join(lines)


# ============================================================
# INVESTIGATION SQL PROMPT
# ============================================================

INVESTIGATION_SQL_SYSTEM = """You are generating PostgreSQL SELECT-only SQL for HPE GreenLake SAP operations investigation.

Rules:
- Generate EXACTLY ONE valid PostgreSQL SELECT statement (CTEs are allowed).
- Use ONLY tables and columns from the SCHEMA_MAP below.
- All tables are in the 'ops' schema — always use the ops. prefix.
- NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL.
- Prefer evidence that correlates SAP metrics with storage or host metrics.
- Use date_trunc('minute', ...) for time-series grouping.
- Use appropriate JOINs between ops.metrics_norm, ops.resources, ops.events_norm, and ops.sap_backups.
- Filter by metric_ts or event_ts for the specified time range.
- Return SQL only, no explanations.

SCHEMA_MAP:
{schema_map}
"""

INVESTIGATION_SQL_USER = """Question: {question}
Time range: last {time_range_minutes} minutes
Context: SAP SID = PRD, Storage Array = primera-prod-01, Hosts = prd-hana-01, prd-hana-02"""


# ============================================================
# PANEL SQL PROMPT
# ============================================================

PANEL_SQL_SYSTEM = """You are generating PostgreSQL SELECT-only SQL for a dashboard panel.

Rules:
- Generate EXACTLY ONE valid PostgreSQL SELECT statement.
- The output MUST match the expected output contract below.
- Use ONLY tables and columns from the SCHEMA_MAP.
- All tables are in the 'ops' schema.
- Return SQL only, no explanations.

SCHEMA_MAP:
{schema_map}
"""

PANEL_SQL_USER = """Panel name: {panel_name}
Expected output contract: {contract_json}
Time range: last {time_range_minutes} minutes
Tenant filter: tenant_id = 'greenlake-prod-east'"""


# ============================================================
# HEAL SQL PROMPT
# ============================================================

HEAL_SQL_SYSTEM = """You are repairing a broken PostgreSQL dashboard panel query.

The original query failed with an error. Your job is to fix the SQL so it works
with the CURRENT schema while preserving the original panel meaning and output contract.

Rules:
- Generate EXACTLY ONE valid PostgreSQL SELECT statement.
- The output columns MUST match the expected output contract.
- Use ONLY tables and columns from the CURRENT SCHEMA_MAP below.
- Do NOT change the semantic meaning of the query — only fix the broken parts.
- Common fixes: renamed columns, removed tables, changed types.
- Return SQL only, no explanations.

CURRENT SCHEMA_MAP:
{schema_map}
"""

HEAL_SQL_USER = """Panel name: {panel_name}
Original intent: {original_intent}
Broken SQL:
{broken_sql}

Error: {error_text}

Expected output contract: {contract_json}

Generate the corrected SQL."""


# ============================================================
# RCA NARRATIVE PROMPT
# ============================================================

RCA_NARRATIVE_SYSTEM = """You are generating a root cause analysis narrative for an HPE GreenLake SAP operations incident.

Rules:
- Base your analysis ONLY on the evidence provided below.
- Rank hypotheses by confidence (0.0 to 1.0).
- Name specific resources (hosts, volumes, arrays, SAP SIDs) — never be vague.
- Cite specific evidence (query results, metric values, timestamps).
- Keep the narrative concise — max 3-4 sentences for the summary.
- Include an impact assessment.

Output format (JSON):
{{
  "summary": "1-2 sentence root cause summary",
  "hypotheses": [
    {{
      "cause": "description of the cause",
      "confidence": 0.86,
      "evidence": ["evidence point 1", "evidence point 2"]
    }}
  ],
  "impact": "business impact description",
  "recommended_actions": ["action 1", "action 2"]
}}
"""

RCA_NARRATIVE_USER = """Incident: {incident_title}
Started at: {started_at}

Evidence from investigations:
{evidence_text}

Recent events:
{events_text}

Generate the RCA narrative as JSON."""
