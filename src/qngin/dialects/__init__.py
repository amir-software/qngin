"""SQL dialect translators: QueryModel → CompiledQuery."""

from qngin.dialects.clickhouse import ClickHouseDialect
from qngin.dialects.postgres import PostgresDialect
from qngin.dialects.compiled import CompiledQuery

__all__ = ["PostgresDialect", "ClickHouseDialect", "CompiledQuery"]
