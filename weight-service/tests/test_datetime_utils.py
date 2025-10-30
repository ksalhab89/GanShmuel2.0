"""Tests for datetime utility functions."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from src.utils.datetime_utils import (
    parse_datetime_string,
    datetime_to_string,
    parse_date_range,
    get_default_date_range,
    get_today_range,
    get_week_range,
    get_month_range,
    validate_and_process_date_range,
    get_server_timezone_offset,
    to_utc,
    from_utc,
    format_datetime_for_display,
    format_date_for_display,
    format_time_for_display,
    is_same_day,
    is_within_hours,
    get_age_in_hours,
    get_business_hours_range,
)


class TestDateTimeParsing:
    """Test datetime parsing functions."""

    def test_parse_valid_datetime_string(self):
        """Test parsing valid datetime string."""
        dt = parse_datetime_string("20241215143000")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 12
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.second == 0

    def test_parse_datetime_string_empty(self):
        """Test parsing empty string returns None."""
        assert parse_datetime_string("") is None
        assert parse_datetime_string(None) is None

    def test_parse_datetime_string_invalid_format(self):
        """Test parsing invalid format returns None."""
        assert parse_datetime_string("2024-12-15") is None
        assert parse_datetime_string("20241215") is None  # Missing time
        assert parse_datetime_string("abcd") is None

    def test_parse_datetime_string_invalid_date(self):
        """Test parsing invalid date returns None."""
        assert parse_datetime_string("20241332000000") is None  # Month 13
        assert parse_datetime_string("20240230143000") is None  # Feb 30

    def test_datetime_to_string(self):
        """Test converting datetime to string."""
        dt = datetime(2024, 12, 15, 14, 30, 0)
        result = datetime_to_string(dt)
        assert result == "20241215143000"

    def test_parse_date_range_both_valid(self):
        """Test parsing date range with both valid."""
        start, end = parse_date_range("20241201000000", "20241231235959")
        assert start is not None
        assert end is not None
        assert start.day == 1
        assert end.day == 31

    def test_parse_date_range_only_start(self):
        """Test parsing date range with only start."""
        start, end = parse_date_range("20241201000000", None)
        assert start is not None
        assert end is None

    def test_parse_date_range_only_end(self):
        """Test parsing date range with only end."""
        start, end = parse_date_range(None, "20241231235959")
        assert start is None
        assert end is not None

    def test_parse_date_range_both_none(self):
        """Test parsing date range with both None."""
        start, end = parse_date_range(None, None)
        assert start is None
        assert end is None


class TestDefaultDateRanges:
    """Test default date range functions."""

    def test_get_default_date_range(self):
        """Test getting default 30-day range."""
        start, end = get_default_date_range()
        assert start < end
        assert (end - start).days >= 29  # At least 29 days
        assert start.hour == 0
        assert start.minute == 0
        assert end.hour == 23
        assert end.minute == 59

    def test_get_today_range(self):
        """Test getting today's range."""
        start, end = get_today_range()
        assert is_same_day(start, end)
        assert start.hour == 0
        assert start.minute == 0
        assert end.hour == 23
        assert end.minute == 59

    def test_get_week_range(self):
        """Test getting current week range."""
        start, end = get_week_range()
        assert start.weekday() == 0  # Monday
        assert (end - start).days == 6  # 7 days total
        assert start.hour == 0
        assert end.hour == 23

    def test_get_month_range(self):
        """Test getting current month range."""
        start, end = get_month_range()
        assert start.day == 1
        assert start.hour == 0
        # End should be end of month (last microsecond, which might be day 1 of next month)
        # Check that range is at least 27 days (covers Feb in leap year)
        assert (end - start).days >= 27
        # Start should be current month, end should be current or next month
        assert start.month == datetime.now().month


class TestDateRangeValidation:
    """Test date range validation functions."""

    def test_validate_both_valid(self):
        """Test validation with both valid dates."""
        start, end, errors = validate_and_process_date_range(
            "20241201000000", "20241231235959"
        )
        assert len(errors) == 0
        assert start.day == 1
        assert end.day == 31

    def test_validate_invalid_from_format(self):
        """Test validation with invalid from format."""
        start, end, errors = validate_and_process_date_range(
            "invalid", "20241231235959"
        )
        assert len(errors) > 0
        assert "Invalid from_time format" in errors[0]

    def test_validate_invalid_to_format(self):
        """Test validation with invalid to format."""
        start, end, errors = validate_and_process_date_range(
            "20241201000000", "invalid"
        )
        assert len(errors) > 0
        assert "Invalid to_time format" in errors[0]

    def test_validate_from_after_to(self):
        """Test validation when from is after to."""
        start, end, errors = validate_and_process_date_range(
            "20241231000000", "20241201000000"
        )
        assert len(errors) > 0
        assert "must be before" in errors[0]

    def test_validate_apply_defaults_none(self):
        """Test validation applies defaults when both None."""
        start, end, errors = validate_and_process_date_range(None, None)
        assert len(errors) == 0
        assert start is not None
        assert end is not None
        assert start < end

    def test_validate_apply_default_start(self):
        """Test validation applies default start."""
        # Use future end date to ensure default start (30 days ago) is before it
        start, end, errors = validate_and_process_date_range(
            None, "20261231235959"
        )
        assert len(errors) == 0
        assert start is not None
        assert start < end

    def test_validate_apply_default_end(self):
        """Test validation applies default end."""
        start, end, errors = validate_and_process_date_range(
            "20241201000000", None
        )
        assert len(errors) == 0
        assert end is not None
        assert start < end


class TestTimezoneUtilities:
    """Test timezone utility functions."""

    def test_get_server_timezone_offset(self):
        """Test getting server timezone offset."""
        offset = get_server_timezone_offset()
        assert isinstance(offset, int)
        assert -12 <= offset <= 14  # Valid timezone range

    def test_to_utc_and_back(self):
        """Test converting to UTC and back."""
        local_dt = datetime.now().replace(microsecond=0)
        utc_dt = to_utc(local_dt)
        back_to_local = from_utc(utc_dt)

        # Should be close (within a few seconds due to execution time)
        diff = abs((back_to_local - local_dt).total_seconds())
        assert diff < 5


class TestFormattingUtilities:
    """Test datetime formatting functions."""

    def test_format_datetime_for_display(self):
        """Test formatting datetime for display."""
        dt = datetime(2024, 12, 15, 14, 30, 45)
        result = format_datetime_for_display(dt)
        assert result == "2024-12-15 14:30:45"

    def test_format_date_for_display(self):
        """Test formatting date for display."""
        dt = datetime(2024, 12, 15, 14, 30, 45)
        result = format_date_for_display(dt)
        assert result == "2024-12-15"

    def test_format_time_for_display(self):
        """Test formatting time for display."""
        dt = datetime(2024, 12, 15, 14, 30, 45)
        result = format_time_for_display(dt)
        assert result == "14:30:45"


class TestSessionUtilities:
    """Test session and query utility functions."""

    def test_is_same_day_true(self):
        """Test is_same_day returns True for same day."""
        dt1 = datetime(2024, 12, 15, 10, 0, 0)
        dt2 = datetime(2024, 12, 15, 18, 30, 0)
        assert is_same_day(dt1, dt2) is True

    def test_is_same_day_false(self):
        """Test is_same_day returns False for different days."""
        dt1 = datetime(2024, 12, 15, 23, 59, 0)
        dt2 = datetime(2024, 12, 16, 0, 1, 0)
        assert is_same_day(dt1, dt2) is False

    def test_is_within_hours_true(self):
        """Test is_within_hours returns True when within range."""
        dt = datetime.now() - timedelta(hours=2)
        assert is_within_hours(dt, 3) is True

    def test_is_within_hours_false(self):
        """Test is_within_hours returns False when outside range."""
        dt = datetime.now() - timedelta(hours=5)
        assert is_within_hours(dt, 3) is False

    def test_is_within_hours_future(self):
        """Test is_within_hours works with future dates."""
        dt = datetime.now() + timedelta(hours=2)
        assert is_within_hours(dt, 3) is True

    def test_get_age_in_hours_past(self):
        """Test get_age_in_hours for past datetime."""
        dt = datetime.now() - timedelta(hours=5)
        age = get_age_in_hours(dt)
        assert 4.9 < age < 5.1  # Allow small margin

    def test_get_age_in_hours_future(self):
        """Test get_age_in_hours for future datetime."""
        dt = datetime.now() + timedelta(hours=3)
        age = get_age_in_hours(dt)
        assert -3.1 < age < -2.9  # Negative for future

    def test_get_business_hours_range(self):
        """Test getting business hours range."""
        date = datetime(2024, 12, 15, 12, 0, 0)
        start, end = get_business_hours_range(date)

        assert start.hour == 8
        assert start.minute == 0
        assert end.hour == 18
        assert end.minute == 0
        assert start.day == date.day
        assert end.day == date.day


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parse_datetime_at_midnight(self):
        """Test parsing datetime at midnight."""
        dt = parse_datetime_string("20241215000000")
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0

    def test_parse_datetime_at_max_time(self):
        """Test parsing datetime at end of day."""
        dt = parse_datetime_string("20241215235959")
        assert dt.hour == 23
        assert dt.minute == 59
        assert dt.second == 59

    def test_validate_same_from_and_to(self):
        """Test validation when from equals to."""
        start, end, errors = validate_and_process_date_range(
            "20241215120000", "20241215120000"
        )
        # From must be before to, so this should error
        assert len(errors) > 0

    def test_age_in_hours_zero(self):
        """Test age in hours for current moment."""
        dt = datetime.now()
        age = get_age_in_hours(dt)
        assert abs(age) < 0.01  # Very close to zero
