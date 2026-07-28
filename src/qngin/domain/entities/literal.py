"""Constant value used in JOIN ON or similar expressions."""


class Literal:
    """Constant SQL operand."""

    def __init__(self, value):
        self.value = value

    def __repr__(self) -> str:
        return f"Literal(value={self.value!r})"
