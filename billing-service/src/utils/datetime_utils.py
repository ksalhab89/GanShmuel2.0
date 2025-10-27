from datetime import datetime
from typing import Optional


def get_default_date_range(from_date: Optional[str], to_date: Optional[str]) -> tuple[str, str]:
    """
    Get default date range for API calls.
    
    Args:
        from_date: Optional start date in yyyymmddhhmmss format
        to_date: Optional end date in yyyymmddhhmmss format
        
    Returns:
        Tuple of (from_date, to_date) in yyyymmddhhmmss format
    """
    now = datetime.now()
    
    # Default from_date: 1st of current month at 000000
    if not from_date:
        from_date = now.strftime('%Y%m01000000')
    
    # Default to_date: current timestamp
    if not to_date:
        to_date = now.strftime('%Y%m%d%H%M%S')
    
    return from_date, to_date


def validate_timestamp_format(timestamp: str) -> bool:
    """
    Validate timestamp format (yyyymmddhhmmss).
    
    Args:
        timestamp: Timestamp string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if len(timestamp) != 14:
        return False
    
    try:
        datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        return True
    except ValueError:
        return False