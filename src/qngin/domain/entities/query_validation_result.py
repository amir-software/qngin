from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class QueryValidationResult:
    """Result of validating generated SQL (e.g. via EXPLAIN)."""

    is_valid: bool
    error: Optional[str] = None
    explain_plan: Optional[Any] = None
