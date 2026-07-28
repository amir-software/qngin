"""Parse a physical-JSON payload into QueryModel."""

from __future__ import annotations

from qngin.domain.entities.field import Field
from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.join_definition import JoinCondition, JoinNode
from qngin.domain.entities.query import QueryModel
from qngin.domain.entities.table_ref import TableRef
from qngin.domain.entities.where_group import ConditionGroup


class SimpleJSONParser:
    """
    Lower-level parser: physical table/column JSON → :class:`QueryModel`.

    Prefer :class:`~qngin.engine.QueryEngine` with a :class:`~qngin.metadata.Flow`
    for business-level field codes.
    """

    def parse_join(self, j: dict) -> JoinNode:
        joins = [self.parse_join(child) for child in j.get("joins", [])]
        table_obj = j.get("table")
        table_ref = TableRef(table_obj.get("table_name"), table_obj.get("alias"))
        on_raw = j.get("on", [])
        on = []
        for cond in on_raw:
            if isinstance(cond, dict):
                on.append(
                    JoinCondition(
                        left=cond["left"],
                        operator=cond.get("operator", "="),
                        right=cond["right"],
                    )
                )
            else:
                on.append(cond)
        return JoinNode(
            table=table_ref,
            join_type=j.get("type", "inner"),
            on=on,
            joins=joins,
        )

    def _parse_where(self, raw) -> Condition | ConditionGroup | None:
        if not raw:
            return None
        if isinstance(raw, dict):
            if "logic" in raw:
                return ConditionGroup(
                    operator=raw["logic"].upper(),
                    conditions=[
                        self._parse_where(child) for child in raw.get("items", [])
                    ],
                )
            return Condition(raw["left"], raw["operator"], raw.get("right"))
        if isinstance(raw, list):
            conditions = [
                Condition(w["left"], w["operator"], w["right"]) for w in raw
            ]
            if len(conditions) == 1:
                return conditions[0]
            return ConditionGroup(operator="AND", conditions=conditions)
        raise ValueError(f"Unsupported where payload: {raw!r}")

    def parse(self, raw: dict) -> QueryModel:
        from_table_obj = raw.get("from") or raw.get("table") or raw["from_table"]
        from_obj = TableRef(
            from_table_obj.get("table_name"),
            from_table_obj.get("alias"),
        )

        select = []
        for s in raw.get("select", []):
            if isinstance(s, str):
                select.append(Field(s))
            elif isinstance(s, dict):
                select.append(Field(s["field"], alias=s.get("alias")))
            else:
                raise ValueError(f"Invalid select item: {s!r}")

        joins = [self.parse_join(j) for j in raw.get("joins", [])]
        where = self._parse_where(raw.get("where"))

        return QueryModel(
            from_table=from_obj,
            select=select,
            joins=joins,
            where=where,
            group_by=raw.get("group_by", []),
            order_by=raw.get("order_by", []),
            limit=raw.get("limit"),
            offset=raw.get("offset"),
            distinct=bool(raw.get("distinct", False)),
        )
