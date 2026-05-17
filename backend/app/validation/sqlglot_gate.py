"""SQLGlot-based AST validation gate for generated SQL."""

from dataclasses import dataclass
import sqlglot
from sqlglot import exp

# Only allow queries against tables in the ops schema
ALLOWED_SCHEMAS = {"ops"}


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None
    tables: list[str] | None = None
    statement_type: str | None = None


def validate_sql(sql_text: str) -> ValidationResult:
    """Parse SQL with SQLGlot, reject non-SELECT statements, extract and enforce referenced tables."""
    try:
        parsed = sqlglot.parse(sql_text, dialect="postgres")
    except sqlglot.errors.ParseError as e:
        return ValidationResult(valid=False, error=f"Parse error: {e}")

    if not parsed or parsed[0] is None:
        return ValidationResult(valid=False, error="Empty or unparseable SQL")

    # Check we have exactly one statement
    if len(parsed) > 1:
        return ValidationResult(valid=False, error=f"Expected 1 statement, got {len(parsed)}")

    statement = parsed[0]
    stmt_type = type(statement).__name__

    # Allow SELECT and CTEs (which are also Select nodes)
    if not isinstance(statement, exp.Select):
        return ValidationResult(
            valid=False,
            error=f"Only SELECT allowed, got {stmt_type}",
            statement_type=stmt_type,
        )

    # Extract referenced tables and enforce schema allowlist
    tables = []
    for table in statement.find_all(exp.Table):
        table_name = table.name
        schema = table.db or None
        if schema:
            table_name = f"{schema}.{table_name}"

        # Reject tables outside the allowed schemas
        if schema and schema not in ALLOWED_SCHEMAS:
            return ValidationResult(
                valid=False,
                error=f"Table '{table_name}' is outside allowed schemas {ALLOWED_SCHEMAS}",
                tables=[table_name],
                statement_type="SELECT",
            )
        # If no schema specified, it could be a CTE alias or implicit public — allow cautiously
        tables.append(table_name)

    return ValidationResult(
        valid=True,
        tables=tables,
        statement_type="SELECT",
    )


def extract_columns(sql_text: str) -> list[str]:
    """Extract output column names/aliases from a SELECT statement."""
    try:
        parsed = sqlglot.parse_one(sql_text, dialect="postgres")
    except Exception:
        return []

    columns = []
    select_node = parsed.find(exp.Select)
    if not select_node:
        return columns

    for expr in select_node.expressions:
        if isinstance(expr, exp.Alias):
            columns.append(expr.alias)
        elif isinstance(expr, exp.Column):
            columns.append(expr.name)
        elif hasattr(expr, "name") and expr.name:
            columns.append(expr.name)
        else:
            # Fallback: use the SQL representation
            columns.append(str(expr))

    return columns
