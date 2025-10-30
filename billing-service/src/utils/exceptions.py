class BillingServiceException(Exception):
    """Base exception for billing service."""


class DatabaseError(BillingServiceException):
    """Database operation error."""


class ValidationError(BillingServiceException):
    """Data validation error."""


class NotFoundError(BillingServiceException):
    """Resource not found error."""


class DuplicateError(BillingServiceException):
    """Duplicate resource error."""


class WeightServiceError(BillingServiceException):
    """Weight service integration error."""


class FileError(BillingServiceException):
    """File operation error."""
