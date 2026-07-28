"""Public QueryEngine façade."""

from __future__ import annotations

from typing import Any, Iterator, Mapping

from qngin.builders import get_builder
from qngin.dialects.base import BaseDialect
from qngin.dialects.compiled import CompiledQuery
from qngin.dialects.postgres import PostgresDialect
from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.query import QueryModel
from qngin.domain.services.validator import QueryValidator
from qngin.executors.protocol import Executor
from qngin.exporters.json_exporter import JsonExporter
from qngin.metadata.flow import Flow
from qngin.parsing import SimpleJSONParser


class QueryEngine:
    """
    Compile and optionally execute queries from Flow metadata + payload.

    Example::

        engine = QueryEngine(dialect=PostgresDialect())
        compiled = engine.compile(flow, {"select": ["id"], "limit": 10})
        rows = list(engine.execute(flow, payload, executor=DbapiExecutor(conn)))
    """

    def __init__(self, dialect: BaseDialect | None = None):
        self.dialect = dialect or PostgresDialect()
        self._parser = SimpleJSONParser()

    def build(
        self,
        flow: Flow,
        payload: dict,
        *,
        extra_where: Condition | dict | None = None,
    ) -> QueryModel:
        """Resolve business payload against flow metadata into a QueryModel."""
        builder = get_builder(flow)
        return builder.build(payload, extra_where=extra_where)

    def translate(self, query: QueryModel) -> CompiledQuery:
        """Validate and translate a QueryModel to SQL + bind params."""
        QueryValidator.validate(query)
        return self.dialect.translate(query)

    def compile(
        self,
        flow: Flow,
        payload: dict,
        *,
        extra_where: Condition | dict | None = None,
    ) -> CompiledQuery:
        """build + translate. Returns :class:`CompiledQuery` (sql, params)."""
        model = self.build(flow, payload, extra_where=extra_where)
        return self.translate(model)

    def compile_count(
        self,
        flow: Flow,
        payload: dict,
        *,
        extra_where: Condition | dict | None = None,
    ) -> CompiledQuery:
        """Compile a COUNT(*) wrapper around the main query (sans LIMIT/OFFSET)."""
        compiled = self.compile(flow, payload, extra_where=extra_where)
        return self.dialect.translate_count(compiled)

    def compile_raw(self, raw: dict) -> CompiledQuery:
        """Compile a physical-JSON payload (no Flow)."""
        model = self._parser.parse(raw)
        return self.translate(model)

    def execute(
        self,
        flow: Flow,
        payload: dict,
        *,
        executor: Executor,
        extra_where: Condition | dict | None = None,
    ) -> Iterator[Mapping[str, Any]]:
        """Compile and run; yields row dicts."""
        compiled = self.compile(flow, payload, extra_where=extra_where)
        return executor.execute(compiled.sql, compiled.params)

    def export(
        self,
        flow: Flow,
        payload: dict,
        *,
        executor: Executor,
        exporter=None,
        extra_where: Condition | dict | None = None,
        export_options: dict | None = None,
    ):
        """Compile, execute, and export rows."""
        exporter = exporter or JsonExporter()
        rows = self.execute(
            flow, payload, executor=executor, extra_where=extra_where
        )
        return exporter.export(rows, export_options or {})
