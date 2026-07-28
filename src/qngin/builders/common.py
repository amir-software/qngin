"""Helpers shared by query-model builders."""

from __future__ import annotations

from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.where_group import ConditionGroup


def merge_where(*nodes):
    """AND-merge non-None where nodes."""
    present = [n for n in nodes if n is not None]
    if not present:
        return None
    if len(present) == 1:
        return present[0]
    return ConditionGroup(operator="AND", conditions=list(present))


def build_where_tree(node: dict | None, resolve_leaf) -> Condition | ConditionGroup | None:
    """
    Parse a where/having payload tree.

    Leaf nodes: ``{"field": "...", "op": "=", "value": ...}``
    Groups: ``{"logic": "AND"|"OR", "items": [...]}``
    """
    if not node:
        return None

    if "items" in node and "logic" not in node:
        raise ValueError(
            "Where clause logical group requires 'logic' key (AND/OR)"
        )

    if "logic" in node:
        return ConditionGroup(
            operator=node["logic"].upper(),
            conditions=[
                build_where_tree(child, resolve_leaf) for child in node["items"]
            ],
        )

    return resolve_leaf(node)
