class BillingServiceException(Exception):
    """Base exception for billing service."""
    pass


class DatabaseError(BillingServiceException):
    """Database operation error."""
    pass


class ValidationError(BillingServiceException):
    """Data validation error."""
    pass


class NotFoundError(BillingServiceException):
    """Resource not found error."""
    pass


class DuplicateError(BillingServiceException):
    """Duplicate resource error."""
    pass


class WeightServiceError(BillingServiceException):
    """Weight service integration error."""
    pass


class FileError(BillingServiceException):
    """File operation error."""
    pass