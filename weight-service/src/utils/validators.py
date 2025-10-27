"""Custom validation functions for the Weight Service V2."""

import re
from datetime import datetime
from typing import List, Optional, Tuple


# ============================================================================
# Container ID Validation
# ============================================================================

def validate_container_id_format(container_id: str) -> Tuple[bool, Optional[str]]:
    """Validate container ID format.
    
    Args:
        container_id: Container identifier to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not container_id:
        return False, "Container ID cannot be empty"
    
    if len(container_id) > 15:
        return False, f"Container ID '{container_id}' exceeds 15 character limit"
    
    # Allow alphanumeric characters, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\-_]+$', container_id):
        return False, f"Container ID '{container_id}' contains invalid characters (only alphanumeric, -, _ allowed)"
    
    # Prevent reserved IDs
    reserved_ids = {"na", "none", "null", "undefined", "empty"}
    if container_id.lower() in reserved_ids:
        return False, f"Container ID '{container_id}' is a reserved identifier"
    
    return True, None


def validate_container_list(containers_str: str) -> Tuple[bool, List[str], List[str]]:
    """Validate comma-separated container ID list.
    
    Args:
        containers_str: Comma-separated container IDs
        
    Returns:
        Tuple of (is_valid, container_ids, error_messages)
    """
    if not containers_str or containers_str.strip() == "":
        return False, [], ["Container list cannot be empty"]
    
    # Parse container IDs
    container_ids = [c.strip() for c in containers_str.split(",") if c.strip()]
    
    if not container_ids:
        return False, [], ["Container list cannot be empty after parsing"]
    
    # Check for duplicates
    if len(container_ids) != len(set(container_ids)):
        duplicates = [c for c in container_ids if container_ids.count(c) > 1]
        return False, container_ids, [f"Duplicate container IDs found: {', '.join(set(duplicates))}"]
    
    # Validate each container ID
    errors = []
    for container_id in container_ids:
        is_valid, error_msg = validate_container_id_format(container_id)
        if not is_valid:
            errors.append(error_msg)
    
    return len(errors) == 0, container_ids, errors


# ============================================================================
# Truck License Validation
# ============================================================================

def validate_truck_license(truck: str) -> Tuple[bool, Optional[str]]:
    """Validate truck license plate format.
    
    Args:
        truck: Truck license plate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not truck or truck == "na":
        return True, None  # Empty or 'na' is valid
    
    if len(truck) > 20:
        return False, "Truck license exceeds 20 character limit"
    
    # Allow alphanumeric characters, spaces, and hyphens (common in license plates)
    if not re.match(r'^[a-zA-Z0-9\-\s]+$', truck):
        return False, "Truck license contains invalid characters (only alphanumeric, -, space allowed)"
    
    # Ensure it's not just spaces
    if truck.strip() == "":
        return False, "Truck license cannot be only spaces"
    
    return True, None


# ============================================================================
# Weight Value Validation
# ============================================================================

def validate_weight_value(weight: int, unit: str = "kg") -> Tuple[bool, Optional[str]]:
    """Validate weight value and unit.
    
    Args:
        weight: Weight value
        unit: Weight unit ('kg' or 'lbs')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if weight <= 0:
        return False, "Weight must be a positive value"
    
    if unit not in ["kg", "lbs"]:
        return False, f"Invalid weight unit '{unit}' (must be 'kg' or 'lbs')"
    
    # Convert to kg for range validation
    weight_kg = weight
    if unit == "lbs":
        weight_kg = int(weight * 0.453592)
    
    # Reasonable weight range: 1kg to 100,000kg (100 tons)
    if weight_kg < 1:
        return False, f"Weight too small: {weight_kg}kg (minimum 1kg)"
    
    if weight_kg > 100_000:
        return False, f"Weight too large: {weight_kg}kg (maximum 100,000kg)"
    
    return True, None


def validate_direction(direction: str) -> Tuple[bool, Optional[str]]:
    """Validate weighing direction.
    
    Args:
        direction: Weighing direction
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_directions = {"in", "out", "none"}
    
    if direction not in valid_directions:
        return False, f"Invalid direction '{direction}' (must be one of: {', '.join(valid_directions)})"
    
    return True, None


# ============================================================================
# DateTime Validation
# ============================================================================

def validate_datetime_string(datetime_str: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
    """Validate datetime string in yyyymmddhhmmss format.
    
    Args:
        datetime_str: DateTime string to validate
        
    Returns:
        Tuple of (is_valid, parsed_datetime, error_message)
    """
    if not datetime_str:
        return False, None, "DateTime string cannot be empty"
    
    # Check format
    if not re.match(r'^\d{14}$', datetime_str):
        return False, None, "DateTime must be exactly 14 digits in yyyymmddhhmmss format"
    
    # Try to parse
    try:
        parsed_dt = datetime.strptime(datetime_str, "%Y%m%d%H%M%S")
    except ValueError as e:
        return False, None, f"Invalid datetime value: {e}"
    
    # Check reasonable range (not too far in the past or future)
    now = datetime.now()
    min_date = datetime(2000, 1, 1)  # Not before year 2000
    max_date = datetime(now.year + 10, 12, 31)  # Not more than 10 years in future
    
    if parsed_dt < min_date:
        return False, None, f"DateTime too far in the past (before {min_date.year})"
    
    if parsed_dt > max_date:
        return False, None, f"DateTime too far in the future (after {max_date.year})"
    
    return True, parsed_dt, None


def validate_date_range(from_time: Optional[str], to_time: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate date range parameters.
    
    Args:
        from_time: Start datetime string
        to_time: End datetime string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    from_dt = None
    to_dt = None
    
    if from_time:
        is_valid, from_dt, error_msg = validate_datetime_string(from_time)
        if not is_valid:
            return False, f"Invalid from_time: {error_msg}"
    
    if to_time:
        is_valid, to_dt, error_msg = validate_datetime_string(to_time)
        if not is_valid:
            return False, f"Invalid to_time: {error_msg}"
    
    # Check that from_time is before to_time
    if from_dt and to_dt and from_dt >= to_dt:
        return False, "from_time must be before to_time"
    
    return True, None


# ============================================================================
# File Validation
# ============================================================================

def validate_filename(filename: str) -> Tuple[bool, Optional[str]]:
    """Validate uploaded filename for security.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename cannot be empty"
    
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Filename contains invalid path characters"
    
    # Check length
    if len(filename) > 255:
        return False, "Filename too long (maximum 255 characters)"
    
    # Check for valid extension
    valid_extensions = [".csv", ".json"]
    if not any(filename.lower().endswith(ext) for ext in valid_extensions):
        return False, f"Invalid file extension (must be one of: {', '.join(valid_extensions)})"
    
    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9\-_\.\s]+$', filename):
        return False, "Filename contains invalid characters"
    
    return True, None


# ============================================================================
# Business Rule Validation
# ============================================================================

def validate_session_sequence(direction: str, existing_directions: List[str]) -> Tuple[bool, Optional[str]]:
    """Validate weighing sequence business rules.
    
    Args:
        direction: New transaction direction
        existing_directions: List of existing directions for this session
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if direction == "none":
        return True, None  # 'none' direction is always allowed
    
    if direction == "out":
        # OUT requires a previous IN transaction
        if "in" not in existing_directions:
            return False, "OUT transaction requires a previous IN transaction"
        
        # Prevent multiple OUT transactions
        if "out" in existing_directions:
            return False, "Multiple OUT transactions not allowed for the same session"
    
    elif direction == "in":
        # Prevent multiple IN transactions unless force is used
        if "in" in existing_directions:
            return False, "Multiple IN transactions not allowed (use force=true to override)"
    
    return True, None


def validate_produce_type(produce: str) -> Tuple[bool, Optional[str]]:
    """Validate produce type value.
    
    Args:
        produce: Produce type string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not produce or produce == "na":
        return True, None  # Empty or 'na' is valid
    
    if len(produce) > 50:
        return False, "Produce type exceeds 50 character limit"
    
    # Allow alphanumeric characters, spaces, and common punctuation
    if not re.match(r'^[a-zA-Z0-9\s\-_\.\,]+$', produce):
        return False, "Produce type contains invalid characters"
    
    # Ensure it's not just spaces
    if produce.strip() == "":
        return False, "Produce type cannot be only spaces"
    
    return True, None


# ============================================================================
# Filter Validation
# ============================================================================

def validate_direction_filter(filter_str: str) -> Tuple[bool, List[str], Optional[str]]:
    """Validate direction filter string.
    
    Args:
        filter_str: Comma-separated direction filter
        
    Returns:
        Tuple of (is_valid, filter_list, error_message)
    """
    if not filter_str:
        return False, [], "Filter cannot be empty"
    
    valid_directions = {"in", "out", "none"}
    filter_parts = [f.strip().lower() for f in filter_str.split(",") if f.strip()]
    
    if not filter_parts:
        return False, [], "Filter cannot be empty after parsing"
    
    invalid_parts = [part for part in filter_parts if part not in valid_directions]
    if invalid_parts:
        return False, filter_parts, f"Invalid filter directions: {', '.join(invalid_parts)}"
    
    # Remove duplicates while preserving order
    unique_filters = []
    for part in filter_parts:
        if part not in unique_filters:
            unique_filters.append(part)
    
    return True, unique_filters, None