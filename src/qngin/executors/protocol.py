"""Executor protocol."""

from __future__ import annotations

from typing import Any, Iterator, Mapping, Protocol, Sequence


class Executor(Protocol):
    """Execute parameterized SQL and yield row mappings."""

    def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> Iterator[Mapping[str, Any]]:
        ...
