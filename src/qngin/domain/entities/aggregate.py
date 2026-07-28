"""Aggregation expression in SELECT."""


class AggregateField:
    def __init__(
        self,
        function: str,
        field: str | None,
        alias: str | None = None,
    ):
        self.function = function
        self.field = field
        self.alias = alias

    def __repr__(self) -> str:
        return f"Aggregate({self.function}({self.field}) AS {self.alias})"
