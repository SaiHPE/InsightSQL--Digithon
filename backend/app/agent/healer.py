"""SQL healing engine — repairs broken dashboard panel queries using LLM + schema introspection."""

import json
import time
import asyncpg

from app.agent.llm import generate_sql
from app.agent.prompts import HEAL_SQL_SYSTEM, HEAL_SQL_USER, build_schema_map
from app.validation.sqlglot_gate import validate_sql, extract_columns
from app.validation.executor import explain_query, execute_readonly
from app.ws.manager import manager


async def heal_panel(pool: asyncpg.Pool, panel_id: str) -> dict:
    """Attempt to heal a broken panel query."""
    start_time = time.time()

    await manager.broadcast("panel_healing", {
        "panel_id": panel_id, "step": "loading", "status": "running",
        "detail": "Loading panel and broken query...",
    })

    async with pool.acquire() as conn:
        panel = await conn.fetchrow(
            "SELECT panel_id, panel_name, contract_json, status FROM ops.dashboard_panels WHERE panel_id = $1",
            panel_id,
        )
        if not panel:
            return {"error": f"Panel {panel_id} not found"}

        active_query = await conn.fetchrow(
            "SELECT version_no, sql_text, generated_by FROM ops.panel_query_versions WHERE panel_id = $1 AND is_active = true",
            panel_id,
        )
        if not active_query:
            return {"error": f"No active query for panel {panel_id}"}

    broken_sql = active_query["sql_text"]
    contract_json = json.dumps(json.loads(panel["contract_json"]), indent=2) if isinstance(panel["contract_json"], str) else json.dumps(panel["contract_json"], indent=2)

    # Parse expected columns from contract
    try:
        contract = json.loads(panel["contract_json"]) if isinstance(panel["contract_json"], str) else panel["contract_json"]
        expected_columns = [c["name"] for c in contract.get("columns", [])]
    except Exception:
        expected_columns = []

    # Step 2: Get error — validate broken SQL first, then EXPLAIN
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "diagnosing", "status": "running", "detail": "Running EXPLAIN to capture error..."})
    broken_validation = validate_sql(broken_sql)
    if not broken_validation.valid:
        error_text = broken_validation.error or "Unknown AST error"
    else:
        explain_result = await explain_query(pool, broken_sql)
        error_text = explain_result.error or "Unknown error"
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "diagnosing", "status": "complete", "detail": f"Error: {error_text}", "elapsed": round(time.time() - start_time, 2)})

    # Step 3: Schema map
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "schema_lookup", "status": "running", "detail": "Querying current schema..."})
    schema_map = await build_schema_map(pool)
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "schema_lookup", "status": "complete", "detail": "Schema map built", "elapsed": round(time.time() - start_time, 2)})

    # Step 4: LLM generates fix
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "generating_fix", "status": "running", "detail": "Generating corrected SQL..."})
    system_prompt = HEAL_SQL_SYSTEM.format(schema_map=schema_map)
    user_prompt = HEAL_SQL_USER.format(panel_name=panel["panel_name"], original_intent=panel["panel_name"], broken_sql=broken_sql, error_text=error_text, contract_json=contract_json)
    healed_sql = await generate_sql(system_prompt, user_prompt)
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "generating_fix", "status": "complete", "detail": "Healed SQL generated", "old_sql": broken_sql, "new_sql": healed_sql, "elapsed": round(time.time() - start_time, 2)})

    # Step 5: Validate
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "validating_fix", "status": "running", "detail": "Validating healed SQL..."})

    validation = validate_sql(healed_sql)
    if not validation.valid:
        await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "validating_fix", "status": "failed", "detail": f"AST validation failed: {validation.error}"})
        return {"error": f"Healed SQL failed AST validation: {validation.error}"}

    explain_healed = await explain_query(pool, healed_sql)
    if not explain_healed.success:
        await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "validating_fix", "status": "failed", "detail": f"EXPLAIN failed: {explain_healed.error}"})
        return {"error": f"Healed SQL failed EXPLAIN: {explain_healed.error}"}

    shadow_result = await execute_readonly(pool, healed_sql)
    if not shadow_result.success:
        await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "validating_fix", "status": "failed", "detail": f"Shadow run failed: {shadow_result.error}"})
        return {"error": f"Healed SQL shadow run failed: {shadow_result.error}"}

    # Contract column check
    if expected_columns and shadow_result.columns:
        missing = set(expected_columns) - set(shadow_result.columns)
        if missing:
            await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "validating_fix", "status": "failed", "detail": f"Result shape mismatch: missing columns {missing}"})
            return {"error": f"Healed SQL result missing expected columns: {missing}"}

    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "validating_fix", "status": "complete", "detail": f"Shadow run: {shadow_result.row_count} rows, plan cost {explain_healed.plan_cost}", "elapsed": round(time.time() - start_time, 2)})

    # Step 6: Promote — atomic transaction with row-level lock
    await manager.broadcast("panel_healing", {"panel_id": panel_id, "step": "promoting", "status": "running", "detail": "Inserting healed version..."})

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.fetchrow("SELECT panel_id FROM ops.dashboard_panels WHERE panel_id = $1 FOR UPDATE", panel_id)
            # Re-check active version to avoid promoting a stale fix
            current_active = await conn.fetchrow("SELECT version_no, sql_text FROM ops.panel_query_versions WHERE panel_id = $1 AND is_active = true FOR UPDATE", panel_id)
            if not current_active or current_active["version_no"] != active_query["version_no"]:
                return {"error": f"Panel {panel_id} changed while healing; retry"}
            max_version = await conn.fetchval("SELECT COALESCE(MAX(version_no), 0) FROM ops.panel_query_versions WHERE panel_id = $1", panel_id)
            new_version = max_version + 1
            await conn.execute("UPDATE ops.panel_query_versions SET is_active = false WHERE panel_id = $1", panel_id)
            await conn.execute("INSERT INTO ops.panel_query_versions (panel_id, version_no, sql_text, generated_by, is_active, healed_from_version) VALUES ($1, $2, $3, 'healer', true, $4)", panel_id, new_version, healed_sql, current_active["version_no"])
            await conn.execute("UPDATE ops.dashboard_panels SET status = 'healed' WHERE panel_id = $1", panel_id)

    result = {"panel_id": panel_id, "status": "healed", "old_sql": broken_sql, "new_sql": healed_sql, "error_fixed": error_text, "old_version": active_query["version_no"], "new_version": new_version, "shadow_rows": shadow_result.row_count, "elapsed": round(time.time() - start_time, 2)}
    await manager.broadcast("panel_healed", result)
    return result
