"""Dialect-independent query model."""

from __future__ import annotations

from typing import List

from qngin.domain.entities.aggregate import AggregateField
from qngin.domain.entities.field import Field
from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.join_definition import JoinNode
from qngin.domain.entities.table_ref import TableRef
from qngin.domain.entities.where_group import ConditionGroup


class QueryModel:
    """Domain representation of a user query (independent of SQL translation)."""

    def __init__(
        self,
        from_table: TableRef,
        select: List[Field],
        joins: List[JoinNode] | None = None,
        where: Condition | ConditionGroup | None = None,
        having: Condition | ConditionGroup | None = None,
        group_by: List[str] | None = None,
        aggregates: list[AggregateField] | None = None,
        order_by: List[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        distinct: bool = False,
    ):
        self.from_table = from_table
        self.select = select
        self.joins = joins or []
        self.where = where
        self.having = having
        self.group_by = group_by or []
        self.aggregates = aggregates or []
        self.order_by = order_by or []
        self.limit = limit
        self.offset = offset
        self.distinct = distinct
        self.modification_filter: dict | None = None

    def __repr__(self) -> str:
        return (
            f"QueryModel(from={self.from_table}, select={len(self.select)}, "
            f"joins={len(self.joins)})"
        )

    def get_all_tables(self) -> list[TableRef]:
        """Collect FROM + all nested join tables."""
        tables = [self.from_table]

        def walk(joins: list[JoinNode]) -> None:
            for j in joins:
                tables.append(j.table)
                if j.joins:
                    walk(j.joins)

        walk(self.joins)
        return tables
