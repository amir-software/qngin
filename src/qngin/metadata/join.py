"""Join definitions for metadata flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OperandKind(str, Enum):
    FIELD = "field"
    VALUE = "value"


@dataclass
class JoinConditionDef:
    """ON clause operand pair for a join."""

    left: str
    """Column ref (``table.col``) or literal string when ``left_kind`` is VALUE."""

    operator: str = "="
    right: str = ""
    left_kind: OperandKind = OperandKind.FIELD
    right_kind: OperandKind = OperandKind.FIELD


@dataclass
class JoinDef:
    """Joined table with optional nested child joins."""

    table: str
    alias: str
    join_type: str = "inner"
    conditions: list[JoinConditionDef] = field(default_factory=list)
    children: list[JoinDef] = field(default_factory=list)
