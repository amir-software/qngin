"""Validate QueryModel structure before SQL translation."""

from __future__ import annotations

from qngin.domain.entities.filter_condition import Condition
from qngin.domain.entities.join_definition import JoinNode
from qngin.domain.entities.query import QueryModel
from qngin.domain.entities.table_ref import TableRef
from qngin.domain.entities.where_group import ConditionGroup
from qngin.domain.services.exception import QueryValidationError


class QueryValidator:
    @staticmethod
    def validate(query: QueryModel) -> None:
        AliasValidator.validate(query)
        JoinValidator.validate(query)
        FieldValidator.validate(query)


class AliasValidator:
    @staticmethod
    def validate(query: QueryModel) -> None:
        aliases: dict[str, str] = {}

        def collect(table: TableRef) -> None:
            if table.alias:
                if table.alias in aliases:
                    raise QueryValidationError(
                        f"Duplicate table alias detected: '{table.alias}'"
                    )
                aliases[table.alias] = table.name

        collect(query.from_table)

        def walk_joins(joins: list[JoinNode]) -> None:
            for join in joins:
                collect(join.table)
                if join.joins:
                    walk_joins(join.joins)

        walk_joins(query.joins)


class JoinValidator:
    ALLOWED_JOIN_TYPES = {"inner", "left", "right", "full"}

    @staticmethod
    def validate(query: QueryModel) -> None:
        visited_tables: set[str] = set()

        def walk(joins: list[JoinNode]) -> None:
            for join in joins:
                if join.join_type not in JoinValidator.ALLOWED_JOIN_TYPES:
                    raise QueryValidationError(
                        f"Invalid join type: '{join.join_type}'"
                    )
                if not join.on:
                    raise QueryValidationError(
                        f"JOIN on table '{join.table.name}' must have ON conditions"
                    )
                table_id = join.table.alias or join.table.name
                if table_id in visited_tables:
                    raise QueryValidationError(
                        f"Join cycle detected on table '{table_id}'"
                    )
                visited_tables.add(table_id)
                if join.joins:
                    walk(join.joins)

        root_id = query.from_table.alias or query.from_table.name
        visited_tables.add(root_id)
        walk(query.joins)


class FieldValidator:
    @staticmethod
    def validate(query: QueryModel) -> None:
        aliases = FieldValidator._collect_aliases(query)
        multiple_tables = len(aliases) > 1

        for field in query.select:
            FieldValidator._validate_field(field.name, aliases, multiple_tables)

        FieldValidator._walk_conditions(query.where, aliases, multiple_tables)

        for field in query.group_by:
            FieldValidator._validate_field(field, aliases, multiple_tables)

        for field in query.order_by:
            # order_by may include "col ASC" — validate the column part only
            col = field.split()[0] if field else field
            if "." in col or not multiple_tables:
                FieldValidator._validate_field(col, aliases, multiple_tables)

    @staticmethod
    def _walk_conditions(node, aliases: set[str], multiple_tables: bool) -> None:
        if node is None:
            return
        if isinstance(node, Condition):
            FieldValidator._validate_field(node.left, aliases, multiple_tables)
            return
        if isinstance(node, ConditionGroup):
            for child in node.conditions:
                FieldValidator._walk_conditions(child, aliases, multiple_tables)

    @staticmethod
    def _collect_aliases(query: QueryModel) -> set[str]:
        aliases: set[str] = set()

        def collect(table: TableRef) -> None:
            aliases.add(table.alias or table.name)

        collect(query.from_table)

        def walk(joins: list[JoinNode]) -> None:
            for join in joins:
                collect(join.table)
                if join.joins:
                    walk(join.joins)

        walk(query.joins)
        return aliases

    @staticmethod
    def _validate_field(field: str, aliases: set[str], multiple_tables: bool) -> None:
        if "." in field:
            alias, _ = field.split(".", 1)
            if alias not in aliases:
                raise QueryValidationError(
                    f"Unknown table alias in field reference: '{alias}'"
                )
        elif multiple_tables:
            raise QueryValidationError(
                f"Ambiguous field '{field}'. Use table alias."
            )
