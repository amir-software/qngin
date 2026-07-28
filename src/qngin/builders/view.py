"""Build QueryModel from a view-based Flow."""

from __future__ import annotations

from qngin.builders.common import build_where_tree, merge_where
from qngin.domain.entities.field import Field
from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.query import QueryModel
from qngin.domain.entities.table_ref import TableRef
from qngin.metadata.field import FieldDef
from qngin.metadata.flow import Flow


class ViewQueryModelBuilder:
    """
    Build :class:`QueryModel` from a view / materialized-view :class:`Flow`.

    FROM = ``flow.view_name``. No joins or aggregates.
    """

    def __init__(self, flow: Flow):
        if not flow.view_name:
            raise ValueError("view-based flows require view_name")
        self.flow = flow
        self._field_map: dict[str, FieldDef] = {}
        for f in flow.fields:
            self._field_map[f.code] = f
            if f.alias:
                self._field_map[f.alias] = f

    def build(
        self,
        user_request: dict,
        *,
        extra_where: Condition | dict | None = None,
    ) -> QueryModel:
        where = merge_where(
            self._build_where(user_request.get("where")),
            self._coerce_extra_where(extra_where),
        )
        return QueryModel(
            from_table=TableRef(
                name=self.flow.view_name,
                alias=self.flow.view_name,
            ),
            select=self._build_select(user_request.get("select", [])),
            where=where,
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

    def _column(self, meta: FieldDef) -> str:
        col = meta.view_column or meta.column
        return f"{self.flow.view_name}.{col}"

    def _build_select(self, items: list[str]) -> list[Field]:
        if not items:
            if not self.flow.fields:
                raise ValueError(
                    "payload must include a non-empty 'select' field list"
                )
            items = [f.code for f in self.flow.fields if f.selectable]

        fields: list[Field] = []
        for key in items:
            meta = self._get_field(key, selectable=True)
            fields.append(
                Field(
                    name=self._column(meta),
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
            return Condition(
                left=self._column(meta),
                operator=n["op"].upper(),
                right=n.get("value"),
            )

        return build_where_tree(node, leaf)

    def _build_order_by(self, items: list[str]) -> list[str]:
        resolved = []
        for raw in items:
            direction = "ASC"
            field_name = raw
            if raw.startswith("-"):
                direction = "DESC"
                field_name = raw[1:]
            meta = self._get_field(field_name)
            resolved.append(f"{self._column(meta)} {direction}")
        return resolved

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
