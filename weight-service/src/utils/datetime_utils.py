"""DateTime parsing and formatting utilities for the Weight Service V2."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import re


# ============================================================================
# DateTime Parsing Functions
# ============================================================================

def parse_datetime_string(datetime_str: str) -> Optional[datetime]:
    """Parse datetime string in yyyymmddhhmmss format.
    
    Args:
        datetime_str: DateTime string to parse
        
    Returns:
        Parsed datetime object or None if invalid
    """
    if not datetime_str or not re.match(r'^\d{14}$', datetime_str):
        return None
    
    try:
        return datetime.strptime(datetime_str, "%Y%m%d%H%M%S")
    except ValueError:
        return None


def datetime_to_string(dt: datetime) -> str:
    """Convert datetime object to yyyymmddhhmmss string format.
    
    Args:
        dt: DateTime object to convert
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime("%Y%m%d%H%M%S")


def parse_date_range(
    from_time: Optional[str],
    to_time: Optional[str]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse date range strings into datetime objects.
    
    Args:
        from_time: Start time string (optional)
        to_time: End time string (optional)
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start_dt = None
    end_dt = None
    
    if from_time:
        start_dt = parse_datetime_string(from_time)
    
    if to_time:
        end_dt = parse_datetime_string(to_time)
    
    return start_dt, end_dt


# ============================================================================
# Default Date Range Logic
# ============================================================================

def get_default_date_range() -> Tuple[datetime, datetime]:
    """Get default date range for queries (last 30 days).
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.now()
    start_date = now - timedelta(days=30)
    
    # Set to beginning of day for start, end of day for end
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_date, end_date


def get_today_range() -> Tuple[datetime, datetime]:
    """Get date range for today.
    
    Returns:
        Tuple of (start_of_today, end_of_today)
    """
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_of_day, end_of_day


def get_week_range() -> Tuple[datetime, datetime]:
    """Get date range for the current week (Monday to Sunday).
    
    Returns:
        Tuple of (start_of_week, end_of_week)
    """
    now = datetime.now()
    
    # Calculate start of week (Monday)
    days_since_monday = now.weekday()
    start_of_week = now - timedelta(days=days_since_monday)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate end of week (Sunday)
    end_of_week = start_of_week + timedelta(days=6)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_of_week, end_of_week


def get_month_range() -> Tuple[datetime, datetime]:
    """Get date range for the current month.
    
    Returns:
        Tuple of (start_of_month, end_of_month)
    """
    now = datetime.now()
    
    # Start of month
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # End of month
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    
    end_of_month = next_month - timedelta(microseconds=1)
    
    return start_of_month, end_of_month


# ============================================================================
# Date Range Validation and Processing
# ============================================================================

def validate_and_process_date_range(
    from_time: Optional[str],
    to_time: Optional[str],
    default_range_days: int = 30
) -> Tuple[datetime, datetime, List[str]]:
    """Validate and process date range parameters with defaults.
    
    Args:
        from_time: Start time string (optional)
        to_time: End time string (optional)
        default_range_days: Default range in days if no parameters provided
        
    Returns:
        Tuple of (start_datetime, end_datetime, error_messages)
    """
    errors = []
    start_dt = None
    end_dt = None
    
    # Parse from_time
    if from_time:
        start_dt = parse_datetime_string(from_time)
        if start_dt is None:
            errors.append(f"Invalid from_time format: {from_time}")
    
    # Parse to_time
    if to_time:
        end_dt = parse_datetime_string(to_time)
        if end_dt is None:
            errors.append(f"Invalid to_time format: {to_time}")
    
    # Validate range if both are provided
    if start_dt and end_dt and start_dt >= end_dt:
        errors.append("from_time must be before to_time")
    
    # Apply defaults if needed
    if not start_dt or not end_dt:
        now = datetime.now()
        
        if not start_dt:
            start_dt = now - timedelta(days=default_range_days)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if not end_dt:
            end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_dt, end_dt, errors


# ============================================================================
# Timezone Utilities
# ============================================================================

def get_server_timezone_offset() -> int:
    """Get server timezone offset in hours from UTC.
    
    Returns:
        Timezone offset in hours (e.g., -5 for EST, +2 for CEST)
    """
    now = datetime.now()
    utc_now = datetime.utcnow()
    offset_seconds = (now - utc_now).total_seconds()
    return int(offset_seconds / 3600)


def to_utc(dt: datetime) -> datetime:
    """Convert local datetime to UTC (basic implementation).
    
    Args:
        dt: Local datetime
        
    Returns:
        UTC datetime
    """
    offset_hours = get_server_timezone_offset()
    return dt - timedelta(hours=offset_hours)


def from_utc(dt: datetime) -> datetime:
    """Convert UTC datetime to local time (basic implementation).
    
    Args:
        dt: UTC datetime
        
    Returns:
        Local datetime
    """
    offset_hours = get_server_timezone_offset()
    return dt + timedelta(hours=offset_hours)


# ============================================================================
# Formatting Utilities
# ============================================================================

def format_datetime_for_display(dt: datetime) -> str:
    """Format datetime for human-readable display.
    
    Args:
        dt: DateTime to format
        
    Returns:
        Formatted datetime string (e.g., "2024-01-15 14:30:00")
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date_for_display(dt: datetime) -> str:
    """Format date for human-readable display.
    
    Args:
        dt: DateTime to format
        
    Returns:
        Formatted date string (e.g., "2024-01-15")
    """
    return dt.strftime("%Y-%m-%d")


def format_time_for_display(dt: datetime) -> str:
    """Format time for human-readable display.
    
    Args:
        dt: DateTime to format
        
    Returns:
        Formatted time string (e.g., "14:30:00")
    """
    return dt.strftime("%H:%M:%S")


# ============================================================================
# Session and Query Utilities
# ============================================================================

def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """Check if two datetimes are on the same day.
    
    Args:
        dt1: First datetime
        dt2: Second datetime
        
    Returns:
        True if both datetimes are on the same day
    """
    return dt1.date() == dt2.date()


def is_within_hours(dt: datetime, hours: int) -> bool:
    """Check if datetime is within the specified number of hours from now.
    
    Args:
        dt: DateTime to check
        hours: Number of hours
        
    Returns:
        True if datetime is within the specified hours
    """
    now = datetime.now()
    time_diff = abs((now - dt).total_seconds() / 3600)
    return time_diff <= hours


def get_age_in_hours(dt: datetime) -> float:
    """Get age of datetime in hours from now.
    
    Args:
        dt: DateTime to calculate age for
        
    Returns:
        Age in hours (can be negative for future dates)
    """
    now = datetime.now()
    return (now - dt).total_seconds() / 3600


def get_business_hours_range(date: datetime) -> Tuple[datetime, datetime]:
    """Get business hours range for a given date (8 AM to 6 PM).
    
    Args:
        date: Date to get business hours for
        
    Returns:
        Tuple of (business_start, business_end)
    """
    business_start = date.replace(hour=8, minute=0, second=0, microsecond=0)
    business_end = date.replace(hour=18, minute=0, second=0, microsecond=0)
    
    return business_start, business_end