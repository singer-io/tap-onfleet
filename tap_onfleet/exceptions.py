"""Custom exceptions for tap-onfleet."""


class OnfleetForbiddenError(Exception):
    """Raised when the Onfleet API returns HTTP 403 Forbidden."""


class OnfleetUnauthorizedError(Exception):
    """Raised when the Onfleet API returns HTTP 401 Unauthorized (invalid credentials)."""
