"""Custom exception classes for the Weight Service V2."""

from datetime import datetime
from typing import Dict, List, Optional, Union


# ============================================================================
# Base Exception Classes
# ============================================================================

class WeightServiceError(Exception):
    """Base exception for all Weight Service errors."""
    
    def __init__(self, message: str, code: str = "WS000", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Union[str, Dict]]:
        """Convert exception to dictionary format."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class ValidationError(WeightServiceError):
    """Base class for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None):
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        
        super().__init__(message, "WS011", details)


class BusinessLogicError(WeightServiceError):
    """Base class for business logic errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        
        super().__init__(message, "WS001", details)


class SystemError(WeightServiceError):
    """Base class for system-level errors."""
    
    def __init__(self, message: str, component: Optional[str] = None):
        details = {}
        if component:
            details["component"] = component
        
        super().__init__(message, "WS021", details)


class IntegrationError(WeightServiceError):
    """Base class for integration errors."""
    
    def __init__(self, message: str, service: Optional[str] = None):
        details = {}
        if service:
            details["service"] = service
        
        super().__init__(message, "WS031", details)


# ============================================================================
# Business Logic Errors (WS001-WS010)
# ============================================================================

class WeighingSequenceError(BusinessLogicError):
    """Exception raised for invalid weighing sequences."""
    
    def __init__(self, message: str, direction: Optional[str] = None, 
                 truck: Optional[str] = None, containers: Optional[List[str]] = None):
        details = {}
        if direction:
            details["direction"] = direction
        if truck:
            details["truck"] = truck
        if containers:
            details["containers"] = containers
        
        super().__init__(message, "weighing_sequence")
        self.details.update(details)
        self.code = "WS002"


class ContainerNotFoundError(BusinessLogicError):
    """Exception raised when containers are not registered."""
    
    def __init__(self, message: str, container_ids: Optional[List[str]] = None):
        details = {}
        if container_ids:
            details["missing_containers"] = container_ids
        
        super().__init__(message, "container_lookup")
        self.details.update(details)
        self.code = "WS003"


class InvalidWeightError(BusinessLogicError):
    """Exception raised for invalid weight values."""
    
    def __init__(self, message: str, weight: Optional[int] = None, 
                 unit: Optional[str] = None, reason: Optional[str] = None):
        details = {}
        if weight is not None:
            details["weight"] = weight
        if unit:
            details["unit"] = unit
        if reason:
            details["reason"] = reason
        
        super().__init__(message, "weight_validation")
        self.details.update(details)
        self.code = "WS004"


class SessionNotFoundError(BusinessLogicError):
    """Exception raised when session is not found."""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        details = {}
        if session_id:
            details["session_id"] = session_id
        
        super().__init__(message, "session_lookup")
        self.details.update(details)
        self.code = "WS005"


class SessionStateError(BusinessLogicError):
    """Exception raised for invalid session state operations."""
    
    def __init__(self, message: str, session_id: Optional[str] = None, 
                 current_state: Optional[str] = None, expected_state: Optional[str] = None):
        details = {}
        if session_id:
            details["session_id"] = session_id
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        
        super().__init__(message, "session_state")
        self.details.update(details)
        self.code = "WS006"


class CalculationError(BusinessLogicError):
    """Exception raised for weight calculation errors."""
    
    def __init__(self, message: str, calculation_type: Optional[str] = None, 
                 parameters: Optional[Dict] = None):
        details = {}
        if calculation_type:
            details["calculation_type"] = calculation_type
        if parameters:
            details["parameters"] = parameters
        
        super().__init__(message, "weight_calculation")
        self.details.update(details)
        self.code = "WS007"


class DuplicateTransactionError(BusinessLogicError):
    """Exception raised for duplicate transaction attempts."""
    
    def __init__(self, message: str, existing_session_id: Optional[str] = None,
                 truck: Optional[str] = None, containers: Optional[List[str]] = None):
        details = {}
        if existing_session_id:
            details["existing_session_id"] = existing_session_id
        if truck:
            details["truck"] = truck
        if containers:
            details["containers"] = containers
        
        super().__init__(message, "duplicate_check")
        self.details.update(details)
        self.code = "WS008"


# ============================================================================
# Data Validation Errors (WS011-WS020)
# ============================================================================

class ContainerValidationError(ValidationError):
    """Exception raised for container validation errors."""
    
    def __init__(self, message: str, container_id: Optional[str] = None, 
                 validation_rule: Optional[str] = None):
        details = {}
        if container_id:
            details["container_id"] = container_id
        if validation_rule:
            details["validation_rule"] = validation_rule
        
        super().__init__(message, "container", container_id)
        self.details.update(details)
        self.code = "WS012"


class TruckValidationError(ValidationError):
    """Exception raised for truck validation errors."""
    
    def __init__(self, message: str, truck_id: Optional[str] = None):
        super().__init__(message, "truck", truck_id)
        self.code = "WS013"


class WeightValidationError(ValidationError):
    """Exception raised for weight validation errors."""
    
    def __init__(self, message: str, weight: Optional[int] = None, 
                 unit: Optional[str] = None, min_value: Optional[int] = None,
                 max_value: Optional[int] = None):
        details = {}
        if weight is not None:
            details["weight"] = weight
        if unit:
            details["unit"] = unit
        if min_value is not None:
            details["min_value"] = min_value
        if max_value is not None:
            details["max_value"] = max_value
        
        super().__init__(message, "weight", str(weight) if weight else None)
        self.details.update(details)
        self.code = "WS014"


class DateTimeValidationError(ValidationError):
    """Exception raised for datetime validation errors."""
    
    def __init__(self, message: str, datetime_string: Optional[str] = None, 
                 expected_format: Optional[str] = None):
        details = {}
        if expected_format:
            details["expected_format"] = expected_format
        
        super().__init__(message, "datetime", datetime_string)
        self.details.update(details)
        self.code = "WS015"


class InvalidDateRangeError(ValidationError):
    """Exception raised for invalid date range queries."""
    
    def __init__(self, message: str, from_date: Optional[str] = None, 
                 to_date: Optional[str] = None):
        details = {}
        if from_date:
            details["from_date"] = from_date
        if to_date:
            details["to_date"] = to_date
        
        super().__init__(message, "date_range", f"{from_date} - {to_date}")
        self.details.update(details)
        self.code = "WS019"


class DirectionValidationError(ValidationError):
    """Exception raised for direction validation errors."""
    
    def __init__(self, message: str, direction: Optional[str] = None):
        super().__init__(message, "direction", direction)
        self.code = "WS016"


class ProduceValidationError(ValidationError):
    """Exception raised for produce validation errors."""
    
    def __init__(self, message: str, produce: Optional[str] = None):
        super().__init__(message, "produce", produce)
        self.code = "WS017"


class DuplicateContainerError(ValidationError):
    """Exception raised for duplicate container registration."""
    
    def __init__(self, message: str, container_id: Optional[str] = None, 
                 existing_weight: Optional[int] = None):
        details = {}
        if existing_weight is not None:
            details["existing_weight"] = existing_weight
        
        super().__init__(message, "container", container_id)
        self.details.update(details)
        self.code = "WS018"


# ============================================================================
# System Errors (WS021-WS030)
# ============================================================================

class DatabaseError(SystemError):
    """Exception raised for database operation errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 table: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        
        super().__init__(message, "database")
        self.details.update(details)
        self.code = "WS022"


class ConfigurationError(SystemError):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(message, "configuration")
        self.details.update(details)
        self.code = "WS023"


class FileProcessingError(SystemError):
    """Exception raised for file processing errors."""
    
    def __init__(self, message: str, filename: Optional[str] = None, 
                 file_type: Optional[str] = None, line_number: Optional[int] = None):
        details = {}
        if filename:
            details["filename"] = filename
        if file_type:
            details["file_type"] = file_type
        if line_number is not None:
            details["line_number"] = line_number
        
        super().__init__(message, "file_processing")
        self.details.update(details)
        self.code = "WS024"


class FileValidationError(SystemError):
    """Exception raised for file validation errors."""
    
    def __init__(self, message: str, filename: Optional[str] = None, 
                 validation_type: Optional[str] = None):
        details = {}
        if filename:
            details["filename"] = filename
        if validation_type:
            details["validation_type"] = validation_type
        
        super().__init__(message, "file_validation")
        self.details.update(details)
        self.code = "WS025"


class PermissionError(SystemError):
    """Exception raised for permission errors."""
    
    def __init__(self, message: str, resource: Optional[str] = None, 
                 required_permission: Optional[str] = None):
        details = {}
        if resource:
            details["resource"] = resource
        if required_permission:
            details["required_permission"] = required_permission
        
        super().__init__(message, "permissions")
        self.details.update(details)
        self.code = "WS026"


class ResourceLimitError(SystemError):
    """Exception raised when resource limits are exceeded."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, 
                 current_usage: Optional[int] = None, limit: Optional[int] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if current_usage is not None:
            details["current_usage"] = current_usage
        if limit is not None:
            details["limit"] = limit
        
        super().__init__(message, "resource_limits")
        self.details.update(details)
        self.code = "WS027"


# ============================================================================
# Integration Errors (WS031-WS040)
# ============================================================================

class ExternalServiceError(IntegrationError):
    """Exception raised for external service communication errors."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, 
                 endpoint: Optional[str] = None, status_code: Optional[int] = None):
        details = {}
        if endpoint:
            details["endpoint"] = endpoint
        if status_code is not None:
            details["status_code"] = status_code
        
        super().__init__(message, service_name)
        self.details.update(details)
        self.code = "WS032"


class AuthenticationError(IntegrationError):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, 
                 auth_method: Optional[str] = None):
        details = {}
        if auth_method:
            details["auth_method"] = auth_method
        
        super().__init__(message, service_name)
        self.details.update(details)
        self.code = "WS033"


class ServiceUnavailableError(IntegrationError):
    """Exception raised when external service is unavailable."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, 
                 retry_after: Optional[int] = None):
        details = {}
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after
        
        super().__init__(message, service_name)
        self.details.update(details)
        self.code = "WS034"


class DataSyncError(IntegrationError):
    """Exception raised for data synchronization errors."""
    
    def __init__(self, message: str, source_service: Optional[str] = None, 
                 target_service: Optional[str] = None, sync_type: Optional[str] = None):
        details = {}
        if target_service:
            details["target_service"] = target_service
        if sync_type:
            details["sync_type"] = sync_type
        
        super().__init__(message, source_service)
        self.details.update(details)
        self.code = "WS035"


# ============================================================================
# Exception Helper Functions
# ============================================================================

def format_error_response(exception: WeightServiceError) -> Dict[str, Union[str, Dict]]:
    """
    Format exception as API error response.
    
    Args:
        exception: Weight service exception
        
    Returns:
        Dictionary formatted for API response
    """
    return {
        "error": exception.__class__.__name__.replace("Error", "").replace("Exception", ""),
        "message": exception.message,
        "code": exception.code,
        "timestamp": exception.timestamp.isoformat(),
        "details": exception.details
    }


def create_validation_error(field: str, value: str, message: str) -> ValidationError:
    """
    Create a validation error with consistent formatting.
    
    Args:
        field: Field name that failed validation
        value: Field value that was invalid
        message: Human-readable error message
        
    Returns:
        ValidationError instance
    """
    return ValidationError(message, field, value)


def create_business_logic_error(operation: str, message: str, **kwargs) -> BusinessLogicError:
    """
    Create a business logic error with additional context.
    
    Args:
        operation: Business operation that failed
        message: Human-readable error message
        **kwargs: Additional context details
        
    Returns:
        BusinessLogicError instance
    """
    error = BusinessLogicError(message, operation)
    error.details.update(kwargs)
    return error


def is_recoverable_error(exception: Exception) -> bool:
    """
    Determine if an error is recoverable (should retry).
    
    Args:
        exception: Exception to check
        
    Returns:
        True if error is potentially recoverable
    """
    recoverable_errors = (
        DatabaseError,
        ExternalServiceError,
        ServiceUnavailableError,
        ResourceLimitError
    )
    
    return isinstance(exception, recoverable_errors)


def get_error_category(exception: Exception) -> str:
    """
    Get error category for logging and monitoring.
    
    Args:
        exception: Exception to categorize
        
    Returns:
        Error category string
    """
    if isinstance(exception, ValidationError):
        return "validation"
    elif isinstance(exception, BusinessLogicError):
        return "business_logic"
    elif isinstance(exception, SystemError):
        return "system"
    elif isinstance(exception, IntegrationError):
        return "integration"
    elif isinstance(exception, WeightServiceError):
        return "weight_service"
    else:
        return "unknown"