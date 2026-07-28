"""DB-API 2.0 executor for any compliant connection."""

from __future__ import annotations

from typing import Any, Iterator, Mapping, Sequence


class DbapiExecutor:
    """
    Run SQL through a DB-API 2.0 connection.

    Works with psycopg / psycopg2 (``%s`` placeholders), and other drivers
    that accept the same paramstyle. For SQLite, prefer converting
    placeholders or wrapping the connection.
    """

    def __init__(self, connection):
        self.connection = connection

    def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> Iterator[Mapping[str, Any]]:
        cursor = self.connection.cursor()
        try:
            if params is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, params)
            if cursor.description is None:
                rows: list = []
                columns: list = []
            else:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
        finally:
            cursor.close()
        for row in rows:
            yield dict(zip(columns, row))
