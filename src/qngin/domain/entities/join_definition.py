"""JOIN tree nodes."""

from __future__ import annotations

from qngin.domain.entities.table_ref import TableRef


class JoinCondition:
    """Single ON predicate. Operands are column ``str`` or :class:`Literal`."""

    def __init__(self, left, operator: str, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __repr__(self) -> str:
        return f"{self.left} {self.operator} {self.right}"


class JoinNode:
    """JOIN definition with optional nested joins."""

    def __init__(
        self,
        table: TableRef,
        join_type: str,
        on: list[JoinCondition],
        joins: list[JoinNode] | None = None,
    ):
        self.table = table
        self.join_type = join_type
        self.on = on
        self.joins = joins or []

    def __repr__(self) -> str:
        return (
            f"JoinNode(table={self.table}, type={self.join_type}, "
            f"conditions={len(self.on)}, joins={len(self.joins)})"
        )
