"""PostgreSQL dialect."""

from __future__ import annotations

from qngin.dialects.base import BaseDialect


class PostgresDialect(BaseDialect):
    """Translate :class:`~qngin.domain.entities.query.QueryModel` to PostgreSQL SQL."""

    _like_operator = "ILIKE"
    _quote_columns = False

    def _apply_cast(self, column: str, data_type: str) -> str:
        cast_map = {
            "STRING": "TEXT",
            "INTEGER": "INTEGER",
            "FLOAT": "FLOAT",
            "BOOL": "BOOLEAN",
            "DATE": "DATE",
            "DATETIME": "TIMESTAMP",
            "JALALI_DATE": "TEXT",
            "TIME": "TIME",
            "NUMCHAR": "TEXT",
            "FK": "INTEGER",
        }
        sql_type = cast_map.get(data_type)
        if not sql_type:
            return column
        return f"CAST({column} AS {sql_type})"

    def _resolve_column(self, ref: str) -> str:
        if "." not in ref:
            return ref
        table, column = ref.split(".", 1)
        resolved = self._table_aliases.get(table, table)
        return f"{resolved}.{column}"

    def _render_table(self, table) -> str:
        if table.alias:
            return f"{table.name} {table.alias}"
        return table.name

    def _quote_identifier(self, name: str) -> str:
        return name
