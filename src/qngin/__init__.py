"""Framework-agnostic query engine: Flow metadata + payload → SQL → rows."""

from qngin.engine import QueryEngine
from qngin.metadata import (
    AggregateDef,
    FieldDef,
    Flow,
    FlowType,
    JoinConditionDef,
    JoinDef,
    OperandKind,
    StorageBackend,
)
from qngin.dialects import ClickHouseDialect, PostgresDialect
from qngin.domain.entities import (
    AggregateField,
    Condition,
    ConditionGroup,
    Field,
    JoinCondition,
    JoinNode,
    Literal,
    QueryModel,
    TableRef,
)
from qngin.executors import DbapiExecutor

__all__ = [
    "QueryEngine",
    "Flow",
    "FieldDef",
    "JoinDef",
    "JoinConditionDef",
    "AggregateDef",
    "FlowType",
    "StorageBackend",
    "OperandKind",
    "PostgresDialect",
    "ClickHouseDialect",
    "DbapiExecutor",
    "QueryModel",
    "Field",
    "Condition",
    "ConditionGroup",
    "JoinNode",
    "JoinCondition",
    "TableRef",
    "AggregateField",
    "Literal",
]

__version__ = "0.1.0"
