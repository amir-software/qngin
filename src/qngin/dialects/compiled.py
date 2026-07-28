"""Compiled SQL plus bound parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class CompiledQuery:
    """SQL string with positional placeholders (``%s``) and bind values."""

    sql: str
    params: Sequence[Any] = field(default_factory=tuple)

    def __iter__(self):
        yield self.sql
        yield self.params
