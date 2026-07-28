"""Plain metadata types describing query templates (no ORM)."""

from qngin.metadata.aggregate import AggregateDef
from qngin.metadata.field import FieldDef
from qngin.metadata.flow import Flow, FlowType, StorageBackend
from qngin.metadata.join import JoinConditionDef, JoinDef, OperandKind

__all__ = [
    "AggregateDef",
    "FieldDef",
    "Flow",
    "FlowType",
    "StorageBackend",
    "JoinConditionDef",
    "JoinDef",
    "OperandKind",
]
