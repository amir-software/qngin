"""Flow template: tables, fields, joins, and static filters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from qngin.metadata.aggregate import AggregateDef
from qngin.metadata.field import FieldDef
from qngin.metadata.join import JoinDef


class FlowType(str, Enum):
    METADATA = "metadata"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"


class StorageBackend(str, Enum):
    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"


@dataclass
class Flow:
    """
    Query template owned by the host application.

    Persist and load these objects however you like (JSON, DB, etc.).
    Physical table/column names live on nested defs — no external metadata ORM.
    """

    code: str
    flow_type: FlowType = FlowType.METADATA
    base_table: str | None = None
    """Base table for metadata flows."""

    view_name: str | None = None
    """Database view / matview name for view-based flows."""

    title: str | None = None
    storage_backend: StorageBackend = StorageBackend.POSTGRES
    static_where: dict | None = None
    distinct: bool = False
    fields: list[FieldDef] = field(default_factory=list)
    joins: list[JoinDef] = field(default_factory=list)
    aggregates: list[AggregateDef] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.flow_type, str):
            self.flow_type = FlowType(self.flow_type)
        if isinstance(self.storage_backend, str):
            self.storage_backend = StorageBackend(self.storage_backend)
