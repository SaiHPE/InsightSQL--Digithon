"""Read-only SQL execution with EXPLAIN dry-run."""

from dataclasses import dataclass, field
import asyncpg
import json


@dataclass
class ExecutionResult:
    success: bool
    rows: list[dict] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    error: str | None = None
    plan_cost: float | None = None


async def explain_query(pool: asyncpg.Pool, sql: str) -> ExecutionResult:
    """Run EXPLAIN on a query to check validity without executing."""
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                await conn.execute("SET TRANSACTION READ ONLY")
                plan_rows = await conn.fetch(f"EXPLAIN (FORMAT JSON) {sql}")
                plan = json.loads(plan_rows[0]["QUERY PLAN"])
                cost = plan[0].get("Plan", {}).get("Total Cost", 0)
                return ExecutionResult(success=True, plan_cost=cost)
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


async def execute_readonly(pool: asyncpg.Pool, sql: str) -> ExecutionResult:
    """Execute a query in a read-only transaction."""
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                await conn.execute("SET TRANSACTION READ ONLY")
                rows = await conn.fetch(sql)

                if not rows:
                    return ExecutionResult(success=True, rows=[], columns=[], row_count=0)

                columns = list(rows[0].keys())
                result_rows = [dict(r) for r in rows]

                return ExecutionResult(
                    success=True,
                    rows=result_rows,
                    columns=columns,
                    row_count=len(result_rows),
                )
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
