"""Domain-level exceptions."""


class QueryValidationError(Exception):
    """Raised when a QueryModel violates domain rules."""


class PolicyViolationError(Exception):
    """Raised when a host-level policy blocks a query."""
