"""Shared QueryModel → SQL translation with bind parameters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from qngin.dialects.compiled import CompiledQuery
from qngin.domain.entities.aggregate import AggregateField
from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.join_definition import JoinNode
from qngin.domain.entities.literal import Literal
from qngin.domain.entities.query import QueryModel
from qngin.domain.entities.table_ref import TableRef
from qngin.domain.entities.where_group import ConditionGroup


class BaseDialect(ABC):
    """
    Alias-aware SQL translator.

    Values are emitted as ``%s`` placeholders and collected in ``params``.
    """

    placeholder: str = "%s"

    def translate(self, query: QueryModel) -> CompiledQuery:
        self._params: list[Any] = []
        self._table_aliases = self._collect_aliases(query)

        sql_parts: list[str] = []
        sql_parts.append(self._build_select(query))
        sql_parts.append(f"FROM {self._render_table(query.from_table)}")

        if query.joins:
            sql_parts.append(self._build_joins(query.joins))

        where_clause = None
        if query.where:
            where_clause = self._format_where_node(query.where)

        mod_filter = self._build_modification_filter(query)
        if mod_filter:
            where_clause = (
                f"({where_clause}) AND {mod_filter}"
                if where_clause
                else mod_filter
            )

        if where_clause:
            sql_parts.append("WHERE " + where_clause)

        if query.group_by:
            sql_parts.append(self._build_group_by(query.group_by))

        if query.having:
            sql_parts.append(self._build_having(query.having, query))

        if query.order_by:
            sql_parts.append(self._build_order_by(query.order_by))

        sql_parts.append(self._build_pagination(query.limit, query.offset))

        sql = " ".join(p for p in sql_parts if p)
        return CompiledQuery(sql=sql, params=tuple(self._params))

    def _bind(self, value: Any) -> str:
        self._params.append(value)
        return self.placeholder

    def _collect_aliases(self, query: QueryModel) -> dict[str, str]:
        aliases: dict[str, str] = {}
        t = query.from_table
        aliases[t.name] = t.alias or t.name

        def walk(joins: list[JoinNode]) -> None:
            for j in joins:
                aliases[j.table.name] = j.table.alias or j.table.name
                walk(j.joins)

        walk(query.joins)
        return aliases

    def _resolve_column(self, ref: str) -> str:
        if "." not in ref:
            return self._quote_identifier(ref) if self._quote_columns else ref

        table, column = ref.split(".", 1)
        resolved = self._table_aliases.get(table, table)
        return f"{self._quote_identifier(resolved)}.{self._quote_identifier(column)}"

    _quote_columns: bool = False

    def _quote_identifier(self, name: str) -> str:
        return name

    def _render_table(self, table: TableRef) -> str:
        name = self._quote_identifier(table.name)
        if table.alias:
            return f"{name} {self._quote_identifier(table.alias)}"
        return name

    def _build_select(self, query: QueryModel) -> str:
        parts: list[str] = []

        for f in query.select:
            col = self._resolve_column(f.name)
            if f.data_type:
                col = self._apply_cast(col, f.data_type)
            if f.alias:
                parts.append(f"{col} AS {self._quote_identifier(f.alias)}")
            else:
                parts.append(col)

        for a in query.aggregates:
            parts.append(self._render_aggregate(a))

        if not parts:
            raise ValueError(
                "SELECT clause cannot be empty; include 'select' in payload"
            )

        distinct_sql = "DISTINCT " if query.distinct else ""
        return "SELECT " + distinct_sql + ", ".join(parts)

    def _render_aggregate(self, a: AggregateField) -> str:
        if a.field:
            field = self._resolve_column(a.field)
            expr = f"{a.function.upper()}({field})"
        else:
            expr = f"{a.function.upper()}(*)"
        if a.alias:
            expr += f" AS {self._quote_identifier(a.alias)}"
        return expr

    @abstractmethod
    def _apply_cast(self, column: str, data_type: str) -> str:
        ...

    def _build_joins(self, joins: list[JoinNode]) -> str:
        join_clauses: list[str] = []
        for join in joins:
            on_clause = self._build_on(join.on)
            join_clauses.append(
                f"{join.join_type.upper()} JOIN "
                f"{self._render_table(join.table)} "
                f"ON {on_clause}"
            )
            if join.joins:
                join_clauses.append(self._build_joins(join.joins))
        return " ".join(join_clauses)

    def _render_join_operand(self, operand) -> str:
        if isinstance(operand, Literal):
            if operand.value is None:
                return "NULL"
            return self._bind(operand.value)
        return self._resolve_column(operand)

    def _build_on(self, conditions) -> str:
        parts = []
        for cond in conditions:
            left = self._render_join_operand(cond.left)
            right = self._render_join_operand(cond.right)
            parts.append(f"{left} {cond.operator} {right}")
        return " AND ".join(parts)

    def _format_condition_with_resolver(self, cond: Condition, resolver) -> str:
        left = resolver(cond.left)

        if cond.operator in ("IN", "NOT_IN"):
            values = list(cond.right or [])
            if not values:
                raise ValueError("IN / NOT_IN requires a non-empty list")
            placeholders = ", ".join(self._bind(v) for v in values)
            sql_operator = "IN" if cond.operator == "IN" else "NOT IN"
            return f"{left} {sql_operator} ({placeholders})"

        if cond.operator in {"CONTAINS", "STARTS_WITH", "ENDS_WITH"}:
            if cond.operator == "CONTAINS":
                pattern = f"%{cond.right}%"
            elif cond.operator == "STARTS_WITH":
                pattern = f"{cond.right}%"
            else:
                pattern = f"%{cond.right}"
            return f"{left} {self._like_operator} {self._bind(pattern)}"

        if cond.operator in {"IS_NULL", "IS_NOT_NULL"}:
            sql_operator = "IS NULL" if cond.operator == "IS_NULL" else "IS NOT NULL"
            return f"{left} {sql_operator}"

        if cond.right is None:
            return f"{left} {cond.operator} NULL"

        return f"{left} {cond.operator} {self._bind(cond.right)}"

    _like_operator: str = "LIKE"

    def _format_condition(self, cond: Condition) -> str:
        return self._format_condition_with_resolver(cond, self._resolve_column)

    def _format_where_node(self, node: Condition | ConditionGroup) -> str:
        if isinstance(node, Condition):
            return self._format_condition(node)
        if isinstance(node, ConditionGroup):
            parts = [self._format_where_node(child) for child in node.conditions]
            joined = f" {node.operator} ".join(parts)
            return f"({joined})"
        raise TypeError(f"Unsupported WHERE node: {type(node)}")

    def _build_group_by(self, group_fields: list[str]) -> str:
        cols = [self._resolve_column(f) for f in group_fields]
        return "GROUP BY " + ", ".join(cols)

    def _build_order_by(self, order_fields: list[str]) -> str:
        if not order_fields:
            return ""
        return "ORDER BY " + ", ".join(order_fields)

    def _build_pagination(self, limit: int | None, offset: int | None) -> str:
        parts = []
        if limit is not None:
            parts.append(f"LIMIT {self._bind(limit)}")
        if offset is not None:
            parts.append(f"OFFSET {self._bind(offset)}")
        return " ".join(parts)

    def _build_modification_filter(self, query: QueryModel) -> str | None:
        if not getattr(query, "modification_filter", None):
            return None

        date_from = query.modification_filter["date_from"]
        date_to = query.modification_filter["date_to"]
        mode = query.modification_filter.get("mode", "GREATEST")
        tables = query.get_all_tables()
        if not tables:
            return None

        if mode == "GREATEST":
            fields = [
                f"COALESCE({t.alias or t.name}.modification_date, {self._bind('1970-01-01')})"
                for t in tables
            ]
            return (
                f"GREATEST({', '.join(fields)}) "
                f"BETWEEN {self._bind(date_from)} AND {self._bind(date_to)}"
            )

        conditions = [
            f"{t.alias or t.name}.modification_date "
            f"BETWEEN {self._bind(date_from)} AND {self._bind(date_to)}"
            for t in tables
        ]
        return "(" + " OR ".join(conditions) + ")"

    def _format_having_node(
        self,
        node: Condition | ConditionGroup,
        query: QueryModel,
    ) -> str:
        if isinstance(node, Condition):
            return self._format_condition_with_resolver(
                cond=node,
                resolver=lambda x: self._resolve_aggregate_expression(x, query),
            )
        if isinstance(node, ConditionGroup):
            parts = [
                self._format_having_node(child, query) for child in node.conditions
            ]
            return f"({f' {node.operator} '.join(parts)})"
        raise TypeError(f"Unsupported node: {type(node)}")

    def _build_having(self, root, query: QueryModel) -> str:
        return "HAVING " + self._format_having_node(root, query)

    def _resolve_aggregate_expression(
        self,
        aggregate_alias: str,
        query: QueryModel,
    ) -> str:
        aggregate = next(
            (a for a in query.aggregates if a.alias == aggregate_alias),
            None,
        )
        if not aggregate:
            raise ValueError(f"Aggregate '{aggregate_alias}' not found in query")
        if aggregate.field:
            return f"{aggregate.function.upper()}({self._resolve_column(aggregate.field)})"
        return f"{aggregate.function.upper()}(*)"

    def translate_count(self, compiled: CompiledQuery) -> CompiledQuery:
        """Wrap a compiled SELECT as ``SELECT COUNT(*) FROM (...)``."""
        import re

        sql = compiled.sql
        params = list(compiled.params)
        ph = re.escape(self.placeholder)

        if re.search(rf"\s+LIMIT\s+{ph}\s+OFFSET\s+{ph}\s*$", sql, re.I):
            sql = re.sub(
                rf"\s+LIMIT\s+{ph}\s+OFFSET\s+{ph}\s*$", "", sql, flags=re.I
            )
            params = params[:-2]
        elif re.search(rf"\s+LIMIT\s+{ph}\s*$", sql, re.I):
            sql = re.sub(rf"\s+LIMIT\s+{ph}\s*$", "", sql, flags=re.I)
            params = params[:-1]

        count_sql = f"SELECT COUNT(*) AS total FROM ({sql}) AS qngin_count_subq"
        return CompiledQuery(sql=count_sql, params=tuple(params))
