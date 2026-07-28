"""Leaf predicate for WHERE / HAVING clauses."""


class Condition:
    """Represents a filter condition (WHERE / HAVING leaf)."""

    def __init__(
        self,
        left: str,
        operator: str,
        right: str | int | float | list | None,
    ):
        self.left = left
        self.operator = operator
        self.right = right

    def __repr__(self) -> str:
        return f"Condition({self.left} {self.operator} {self.right!r})"
