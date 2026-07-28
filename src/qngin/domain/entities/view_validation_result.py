from dataclasses import dataclass
from typing import Optional


@dataclass
class ViewValidationResult:
    """Result of validating that a database view exists / is usable."""

    is_valid: bool
    error: Optional[str] = None
