"""ClickHouse dialect."""

from __future__ import annotations

from qngin.dialects.base import BaseDialect


class ClickHouseDialect(BaseDialect):
    """Translate :class:`~qngin.domain.entities.query.QueryModel` to ClickHouse SQL."""

    _like_operator = "ILIKE"
    _quote_columns = True

    def _quote_identifier(self, name: str) -> str:
        if name.startswith("`") and name.endswith("`"):
            return name
        return f"`{name}`"

    def _apply_cast(self, column: str, data_type: str) -> str:
        cast_map = {
            "STRING": "toString",
            "INTEGER": "toInt64",
            "FLOAT": "toFloat64",
            "BOOL": "toUInt8",
            "DATE": "toDate",
            "DATETIME": "toDateTime",
            "JALALI_DATE": "toString",
            "TIME": "toString",
            "NUMCHAR": "toString",
            "FK": "toInt64",
        }
        cast_fn = cast_map.get(data_type)
        if not cast_fn:
            return column
        return f"{cast_fn}({column})"
