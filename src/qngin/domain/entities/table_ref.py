"""Table reference with optional alias."""


class TableRef:
    def __init__(self, name: str, alias: str | None = None):
        self.name = name
        self.alias = alias

    def __repr__(self) -> str:
        return f"TableRef(name={self.name!r}, alias={self.alias!r})"
