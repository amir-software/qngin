"""Selectable column reference in a query."""


class Field:
    """Represents a selectable field (physical ``table.column`` name)."""

    def __init__(
        self,
        name: str,
        alias: str | None = None,
        data_type: str | None = None,
    ):
        self.name = name
        self.alias = alias
        self.data_type = data_type

    def __repr__(self) -> str:
        return f"Field(name={self.name!r}, alias={self.alias!r})"
