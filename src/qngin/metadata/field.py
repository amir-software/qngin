"""Field exposure on a Flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FieldDef:
    """Business-level field mapped to a physical column."""

    code: str
    column: str
    table: str | None = None
    """Physical table/alias for metadata flows; unused for view columns."""

    alias: str | None = None
    view_column: str | None = None
    """Column name inside a database view (view-based flows)."""

    data_type: str | None = None
    selectable: bool = True
    filterable: bool = False
    orderable: bool = False
    is_mandatory: bool = False
    display_order: int = 1
    verbose_title: str | None = None
    description: str | None = None
