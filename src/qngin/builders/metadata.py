"""Build QueryModel from a metadata-based Flow."""

from __future__ import annotations

from qngin.builders.common import build_where_tree, merge_where
from qngin.domain.entities.aggregate import AggregateField
from qngin.domain.entities.field import Field
from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.join_definition import JoinCondition, JoinNode
from qngin.domain.entities.literal import Literal
from qngin.domain.entities.query import QueryModel
from qngin.domain.entities.table_ref import TableRef
from qngin.metadata.field import FieldDef
from qngin.metadata.flow import Flow
from qngin.metadata.join import JoinDef, OperandKind


class MetadataQueryModelBuilder:
    """
    Build :class:`QueryModel` from a metadata :class:`Flow` + user request.

    Physical ``table`` / ``column`` values are taken from :class:`FieldDef`
    and :class:`JoinDef` — hosts map their own catalog into those dataclasses.
    """

    def __init__(self, flow: Flow):
        if not flow.base_table:
            raise ValueError("metadata flows require base_table")

        self.flow = flow
        self._field_map: dict[str, FieldDef] = {}
        for f in sorted(flow.fields, key=lambda x: x.display_order):
            self._field_map[f.code] = f
            if f.alias:
                self._field_map[f.alias] = f

        self._mandatory_codes = [f.code for f in flow.fields if f.is_mandatory]

        self._aggregate_map = {}
        for a in flow.aggregates:
            self._aggregate_map[a.code] = a
            if a.alias:
                self._aggregate_map[a.alias] = a

        # table name / alias → known aliases for that physical table
        self._table_aliases: dict[str, list[str]] = {
            flow.base_table: [flow.base_table],
        }
        self._index_join_aliases(flow.joins)

    def _index_join_aliases(self, joins: list[JoinDef]) -> None:
        for j in joins:
            alias = j.alias or j.table
            self._table_aliases.setdefault(j.table, []).append(alias)
            if j.children:
                self._index_join_aliases(j.children)

    def build(
        self,
        user_request: dict,
        *,
        extra_where: Condition | dict | None = None,
    ) -> QueryModel:
        select_keys = user_request.get("select", [])
        agg_keys = user_request.get("aggregates", [])
        group_by = self._derive_group_by(select_keys, agg_keys)

        incoming_where = self._build_where(user_request.get("where"))
        static_where = self._build_where(self.flow.static_where)
        host_where = self._coerce_extra_where(extra_where)

        where = merge_where(static_where, incoming_where, host_where)

        return QueryModel(
            from_table=TableRef(name=self.flow.base_table, alias=self.flow.base_table),
            select=self._build_select(select_keys),
            aggregates=self._build_aggregates(agg_keys),
            joins=self._build_joins(self.flow.joins),
            where=where,
            having=self._build_having(user_request.get("having")),
            group_by=group_by,
            order_by=self._build_order_by(user_request.get("order_by", [])),
            limit=user_request.get("limit"),
            offset=user_request.get("offset"),
            distinct=self.flow.distinct,
        )

    def _coerce_extra_where(self, extra_where):
        if extra_where is None:
            return None
        if isinstance(extra_where, dict):
            return self._build_where(extra_where)
        return extra_where

    def _derive_group_by(self, select_fields, aggregates) -> list[str]:
        if not aggregates:
            return []
        return [field.name for field in self._build_select(select_fields)]

    def _physical_name(self, meta: FieldDef) -> str:
        table = meta.table or self.flow.base_table
        return f"{table}.{meta.column}"

    def _build_select(self, select_items: list[str]) -> list[Field]:
        if not select_items:
            if not self._field_map:
                raise ValueError(
                    "payload must include a non-empty 'select' field list"
                )
            # default: all selectable unique codes
            seen = set()
            select_items = []
            for f in self.flow.fields:
                if f.code not in seen and f.selectable:
                    seen.add(f.code)
                    select_items.append(f.code)

        if self._mandatory_codes:
            missing = set(self._mandatory_codes) - set(select_items)
            if missing:
                raise ValueError(
                    f"The following mandatory fields are missing: "
                    f"{', '.join(sorted(missing))}"
                )

        fields: list[Field] = []
        for key in select_items:
            meta = self._get_field(key, selectable=True)
            fields.append(
                Field(
                    name=self._physical_name(meta),
                    alias=meta.alias or meta.code,
                    data_type=meta.data_type,
                )
            )
        return fields

    def _build_where(self, node: dict | None):
        def leaf(n: dict) -> Condition:
            if "field" not in n:
                raise ValueError(
                    "Where clause condition requires 'field', 'op', and 'value'"
                )
            meta = self._get_field(n["field"], filterable=True)
            left = self._physical_name(meta)
            op = n["op"].upper()
            if op in {"IS_NULL", "IS_NOT_NULL"}:
                return Condition(left=left, operator=op, right=None)
            value = n.get("value")
            if op in ("IN", "NOT_IN"):
                if not isinstance(value, list) or not value:
                    raise ValueError("IN operator requires a non-empty list value")
            return Condition(left=left, operator=op, right=value)

        return build_where_tree(node, leaf)

    def _build_having(self, node: dict | None):
        def leaf(n: dict) -> Condition:
            field_name = n["field"]
            if field_name not in self._aggregate_map:
                raise ValueError(f"Aggregate '{field_name}' not found")
            op = n["op"].upper()
            if op in {"IS_NULL", "IS_NOT_NULL"}:
                return Condition(left=field_name, operator=op, right=None)
            value = n.get("value")
            if op in ("IN", "NOT_IN"):
                if not isinstance(value, list) or not value:
                    raise ValueError("IN operator requires non-empty list")
            return Condition(left=field_name, operator=op, right=value)

        return build_where_tree(node, leaf)

    def _build_order_by(self, items: list[str]) -> list[str]:
        resolved = []
        for raw in items:
            direction = "ASC"
            field_name = raw
            if raw.startswith("-"):
                direction = "DESC"
                field_name = raw[1:]
            field = self._get_field(field_name)
            column = self._physical_name(field)
            resolved.append(f"{column} {direction}")
        return resolved

    def _build_joins(self, joins: list[JoinDef]) -> list[JoinNode]:
        return [self._build_join_node(j) for j in joins]

    def _resolve_operand(self, kind: OperandKind, value: str):
        if kind == OperandKind.VALUE:
            return Literal(value)
        return value

    def _build_join_node(self, join_meta: JoinDef) -> JoinNode:
        alias = join_meta.alias or join_meta.table
        on_conditions = [
            JoinCondition(
                left=self._resolve_operand(c.left_kind, c.left),
                operator=c.operator,
                right=self._resolve_operand(c.right_kind, c.right),
            )
            for c in join_meta.conditions
        ]
        return JoinNode(
            table=TableRef(name=join_meta.table, alias=alias),
            join_type=join_meta.join_type,
            on=on_conditions,
            joins=self._build_joins(join_meta.children),
        )

    def _get_field(
        self,
        key: str,
        *,
        selectable: bool = False,
        filterable: bool = False,
    ) -> FieldDef:
        if key not in self._field_map:
            raise ValueError(f"Field '{key}' is not exposed in this flow")
        meta = self._field_map[key]
        if selectable and not meta.selectable:
            raise ValueError(f"Field '{key}' is not selectable")
        if filterable and not meta.filterable:
            raise ValueError(f"Field '{key}' is not filterable")
        return meta

    def _build_aggregates(self, items: list[str]) -> list[AggregateField]:
        aggregates: list[AggregateField] = []
        for key in items:
            if key not in self._aggregate_map:
                raise ValueError(
                    f"Aggregate field '{key}' is not defined for this flow"
                )
            meta = self._aggregate_map[key]
            if meta.function == "count" and meta.column is None:
                resolved_field = None
            else:
                if meta.column and meta.table:
                    resolved_field = f"{meta.table}.{meta.column}"
                elif meta.column:
                    resolved_field = meta.column
                else:
                    raise ValueError(
                        f"Aggregate '{key}' requires column (or count with no column)"
                    )
            aggregates.append(
                AggregateField(
                    function=meta.function,
                    field=resolved_field,
                    alias=meta.alias or meta.code,
                )
            )
        return aggregates
