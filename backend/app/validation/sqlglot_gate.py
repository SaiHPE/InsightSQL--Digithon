"""SQLGlot-based AST validation gate for generated SQL."""

from dataclasses import dataclass
import sqlglot
from sqlglot import exp


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None
    tables: list[str] | None = None
    statement_type: str | None = None


def validate_sql(sql_text: str) -> ValidationResult:
    """Parse SQL with SQLGlot, reject non-SELECT statements, extract referenced tables."""
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

    # Extract referenced tables
    tables = []
    for table in statement.find_all(exp.Table):
        table_name = table.name
        if table.db:
            table_name = f"{table.db}.{table_name}"
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
    for expr in parsed.find_all(exp.Alias):
        columns.append(expr.alias)

    return columns
