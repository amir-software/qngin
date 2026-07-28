"""AND/OR groups of conditions."""

from __future__ import annotations

from typing import List, Literal, Union

from qngin.domain.entities.filter_condition import Condition

LogicalOperator = Literal["AND", "OR"]


class ConditionGroup:
    """Group of conditions joined by AND / OR (owns parentheses)."""

    def __init__(
        self,
        operator: LogicalOperator,
        conditions: List[Union[Condition, ConditionGroup]],
    ):
        self.operator = operator
        self.conditions = conditions

    def __repr__(self) -> str:
        return f"ConditionGroup({self.operator}, {self.conditions})"
