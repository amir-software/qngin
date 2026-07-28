"""Aggregate field definitions exposed by a Flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AggregateDef:
    """Named aggregation available to clients."""

    code: str
    function: str
    """One of: count, sum, avg, min, max."""

    column: str | None = None
    """Physical ``table.column``; ``None`` with count means ``COUNT(*)``."""

    table: str | None = None
    alias: str | None = None
    requires_group_by: bool = True
    selectable: bool = True
    filterable: bool = False
    orderable: bool = False
    is_mandatory: bool = False
    data_type: str | None = None
    verbose_title: str | None = None
    description: str | None = None
