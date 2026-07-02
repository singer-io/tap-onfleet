
#
# Module dependencies.
#


class OnfleetForbiddenError(Exception):
    """Raised when the Onfleet API returns an HTTP 403 Forbidden response."""
    pass
