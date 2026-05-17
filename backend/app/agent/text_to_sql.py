"""Text-to-SQL investigation agent — generates and executes SQL to answer operational questions."""

import json
import time
import asyncpg

from app.agent.llm import generate_sql
from app.agent.prompts import (
    INVESTIGATION_SQL_SYSTEM,
    INVESTIGATION_SQL_USER,
    build_schema_map,
)
from app.validation.sqlglot_gate import validate_sql
from app.validation.executor import explain_query, execute_readonly
from app.ws.manager import manager


async def investigate(
    pool: asyncpg.Pool,
    incident_id: str,
    question: str,
    time_range_minutes: int = 30,
    max_retries: int = 3,
) -> dict:
    """Run a full Text-to-SQL investigation cycle with validation and retries.

    Steps:
    1. Build schema map from information_schema
    2. Generate SQL via LLM
    3. Validate with SQLGlot AST gate
    4. EXPLAIN dry-run
    5. Execute read-only
    6. Store in evidence_runs
    """
    start_time = time.time()

    # Step 1: Schema grounding
    await manager.broadcast("agent_step", {
        "incident_id": incident_id,
        "step": "schema_grounding",
        "status": "running",
        "detail": "Querying information_schema...",
    })

    schema_map = await build_schema_map(pool)
    table_count = schema_map.count("Table:")

    await manager.broadcast("agent_step", {
        "incident_id": incident_id,
        "step": "schema_grounding",
        "status": "complete",
        "detail": f"Found {table_count} tables in ops schema",
        "elapsed": round(time.time() - start_time, 2),
    })

    # Retry loop
    last_error = None
    for attempt in range(max_retries):
        # Step 2: SQL generation
        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "sql_generation",
            "status": "running",
            "detail": f"Generating SQL (attempt {attempt + 1})...",
        })

        system_prompt = INVESTIGATION_SQL_SYSTEM.format(schema_map=schema_map)
        user_prompt = INVESTIGATION_SQL_USER.format(
            question=question,
            time_range_minutes=time_range_minutes,
        )

        # If retrying, include the error in the prompt
        if last_error:
            user_prompt += f"\n\nPrevious attempt failed with: {last_error}\nPlease fix the SQL."

        sql_text = await generate_sql(system_prompt, user_prompt)

        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "sql_generation",
            "status": "complete",
            "detail": f"Generated {'CTE-based ' if 'WITH' in sql_text.upper() else ''}SELECT",
            "sql_preview": sql_text[:200],
            "elapsed": round(time.time() - start_time, 2),
        })

        # Step 3: AST validation
        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "ast_validation",
            "status": "running",
            "detail": "Validating SQL AST...",
        })

        validation = validate_sql(sql_text)
        if not validation.valid:
            last_error = validation.error
            await manager.broadcast("agent_step", {
                "incident_id": incident_id,
                "step": "ast_validation",
                "status": "failed",
                "detail": f"Validation failed: {validation.error}",
                "elapsed": round(time.time() - start_time, 2),
            })
            continue

        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "ast_validation",
            "status": "complete",
            "detail": f"Valid {validation.statement_type}, references {len(validation.tables or [])} tables",
            "elapsed": round(time.time() - start_time, 2),
        })

        # Step 4: EXPLAIN check
        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "explain_check",
            "status": "running",
            "detail": "Running EXPLAIN dry-run...",
        })

        explain_result = await explain_query(pool, sql_text)
        if not explain_result.success:
            last_error = explain_result.error
            await manager.broadcast("agent_step", {
                "incident_id": incident_id,
                "step": "explain_check",
                "status": "failed",
                "detail": f"EXPLAIN failed: {explain_result.error}",
                "elapsed": round(time.time() - start_time, 2),
            })
            continue

        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "explain_check",
            "status": "complete",
            "detail": f"Plan cost: {explain_result.plan_cost}",
            "elapsed": round(time.time() - start_time, 2),
        })

        # Step 5: Execute
        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "execution",
            "status": "running",
            "detail": "Executing query (read-only)...",
        })

        exec_result = await execute_readonly(pool, sql_text)
        if not exec_result.success:
            last_error = exec_result.error
            await manager.broadcast("agent_step", {
                "incident_id": incident_id,
                "step": "execution",
                "status": "failed",
                "detail": f"Execution failed: {exec_result.error}",
                "elapsed": round(time.time() - start_time, 2),
            })
            continue

        await manager.broadcast("agent_step", {
            "incident_id": incident_id,
            "step": "execution",
            "status": "complete",
            "detail": f"{exec_result.row_count} rows returned",
            "elapsed": round(time.time() - start_time, 2),
        })

        # Step 6: Store evidence
        # Truncate result for storage (max 50 rows)
        stored_rows = exec_result.rows[:50]
        result_json = json.dumps(stored_rows, default=str)

        async with pool.acquire() as conn:
            run_id = await conn.fetchval(
                """INSERT INTO ops.evidence_runs
                   (incident_id, question, sql_text, result_json, row_count, confidence)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6)
                   RETURNING run_id""",
                incident_id,
                question,
                sql_text,
                result_json,
                exec_result.row_count,
                0.8,  # Base confidence
            )

        evidence = {
            "run_id": run_id,
            "incident_id": incident_id,
            "question": question,
            "sql_text": sql_text,
            "columns": exec_result.columns,
            "rows": stored_rows[:10],  # Send first 10 rows to frontend
            "row_count": exec_result.row_count,
            "confidence": 0.8,
            "elapsed": round(time.time() - start_time, 2),
        }

        await manager.broadcast("evidence_added", evidence)
        return evidence

    # All retries exhausted
    return {
        "error": f"Failed after {max_retries} attempts: {last_error}",
        "incident_id": incident_id,
        "question": question,
    }
