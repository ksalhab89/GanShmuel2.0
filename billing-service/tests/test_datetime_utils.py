"""Tests for datetime utility functions."""

import pytest
from freezegun import freeze_time

from src.utils.datetime_utils import get_default_date_range, validate_timestamp_format


class TestGetDefaultDateRange:
    """Test get_default_date_range function."""

    @freeze_time("2024-01-15 14:30:45")
    def test_both_dates_none(self):
        """Test default date range when both dates are None."""
        from_date, to_date = get_default_date_range(None, None)

        # from_date should be 1st of current month
        assert from_date == "20240101000000"

        # to_date should be current timestamp
        assert to_date == "20240115143045"

    @freeze_time("2024-07-20 09:15:30")
    def test_both_dates_none_different_month(self):
        """Test default date range in different month."""
        from_date, to_date = get_default_date_range(None, None)

        assert from_date == "20240701000000"
        assert to_date == "20240720091530"

    def test_custom_from_date_none_to_date(self):
        """Test with custom from_date and None to_date."""
        with freeze_time("2024-01-15 14:30:45"):
            from_date, to_date = get_default_date_range("20240110000000", None)

            assert from_date == "20240110000000"
            assert to_date == "20240115143045"

    def test_none_from_date_custom_to_date(self):
        """Test with None from_date and custom to_date."""
        with freeze_time("2024-01-15 14:30:45"):
            from_date, to_date = get_default_date_range(None, "20240131235959")

            assert from_date == "20240101000000"
            assert to_date == "20240131235959"

    def test_both_dates_custom(self):
        """Test with both dates provided."""
        from_date, to_date = get_default_date_range("20240101000000", "20240131235959")

        assert from_date == "20240101000000"
        assert to_date == "20240131235959"

    @freeze_time("2024-12-31 23:59:59")
    def test_end_of_year(self):
        """Test default dates at end of year."""
        from_date, to_date = get_default_date_range(None, None)

        assert from_date == "20241201000000"
        assert to_date == "20241231235959"

    @freeze_time("2024-02-29 12:00:00")
    def test_leap_year(self):
        """Test default dates in leap year."""
        from_date, to_date = get_default_date_range(None, None)

        assert from_date == "20240201000000"
        assert to_date == "20240229120000"

    @freeze_time("2024-01-01 00:00:00")
    def test_beginning_of_year(self):
        """Test default dates at beginning of year."""
        from_date, to_date = get_default_date_range(None, None)

        assert from_date == "20240101000000"
        assert to_date == "20240101000000"

    def test_empty_string_from_date(self):
        """Test empty string treated as None for from_date."""
        with freeze_time("2024-01-15 14:30:45"):
            from_date, to_date = get_default_date_range("", None)

            # Empty string is falsy, should use default
            assert from_date == "20240101000000"

    def test_empty_string_to_date(self):
        """Test empty string treated as None for to_date."""
        with freeze_time("2024-01-15 14:30:45"):
            from_date, to_date = get_default_date_range(None, "")

            # Empty string is falsy, should use default
            assert to_date == "20240115143045"


class TestValidateTimestampFormat:
    """Test validate_timestamp_format function."""

    def test_valid_timestamp(self):
        """Test valid timestamp format."""
        assert validate_timestamp_format("20240115143045") is True

    def test_valid_timestamp_start_of_day(self):
        """Test valid timestamp at start of day."""
        assert validate_timestamp_format("20240101000000") is True

    def test_valid_timestamp_end_of_day(self):
        """Test valid timestamp at end of day."""
        assert validate_timestamp_format("20240131235959") is True

    def test_invalid_too_short(self):
        """Test timestamp that's too short."""
        assert validate_timestamp_format("2024011514") is False

    def test_invalid_too_long(self):
        """Test timestamp that's too long."""
        assert validate_timestamp_format("202401151430450") is False

    def test_invalid_non_numeric(self):
        """Test timestamp with non-numeric characters."""
        assert validate_timestamp_format("2024-01-15 14:30") is False

    def test_invalid_letters(self):
        """Test timestamp with letters."""
        assert validate_timestamp_format("202A0115143045") is False

    def test_invalid_date_values(self):
        """Test invalid date values (e.g., month 13)."""
        assert validate_timestamp_format("20241315143045") is False

    def test_invalid_time_values(self):
        """Test invalid time values (e.g., hour 25)."""
        assert validate_timestamp_format("20240115253045") is False

    def test_invalid_february_30(self):
        """Test invalid date like February 30."""
        assert validate_timestamp_format("20240230120000") is False

    def test_invalid_minute_60(self):
        """Test invalid minute value."""
        assert validate_timestamp_format("20240115146000") is False

    def test_invalid_second_60(self):
        """Test invalid second value."""
        assert validate_timestamp_format("20240115145960") is False

    def test_valid_leap_year_date(self):
        """Test valid leap year date (Feb 29)."""
        assert validate_timestamp_format("20240229120000") is True

    def test_invalid_non_leap_year_date(self):
        """Test invalid Feb 29 on non-leap year."""
        assert validate_timestamp_format("20230229120000") is False

    def test_empty_string(self):
        """Test empty string."""
        assert validate_timestamp_format("") is False

    def test_none_input(self):
        """Test None input causes error."""
        with pytest.raises((AttributeError, TypeError)):
            validate_timestamp_format(None)

    def test_special_characters(self):
        """Test timestamp with special characters."""
        assert validate_timestamp_format("2024/01/15 14:30") is False

    def test_valid_different_years(self):
        """Test valid timestamps from different years."""
        assert validate_timestamp_format("20200101000000") is True
        assert validate_timestamp_format("20300101000000") is True
        assert validate_timestamp_format("19990101000000") is True

    def test_valid_all_months(self):
        """Test valid timestamps for all months."""
        for month in range(1, 13):
            timestamp = f"2024{month:02d}15120000"
            assert validate_timestamp_format(timestamp) is True

    def test_valid_boundary_times(self):
        """Test valid boundary time values."""
        assert validate_timestamp_format("20240115235959") is True  # Max time
        assert validate_timestamp_format("20240115000000") is True  # Min time

    def test_invalid_month_zero(self):
        """Test invalid month 0."""
        assert validate_timestamp_format("20240015120000") is False

    def test_invalid_day_zero(self):
        """Test invalid day 0."""
        assert validate_timestamp_format("20240100120000") is False

    def test_invalid_day_32(self):
        """Test invalid day 32."""
        assert validate_timestamp_format("20240132120000") is False

    def test_valid_days_per_month(self):
        """Test valid last days for different months."""
        # 31 days
        assert validate_timestamp_format("20240131120000") is True  # Jan
        assert validate_timestamp_format("20240331120000") is True  # Mar

        # 30 days
        assert validate_timestamp_format("20240430120000") is True  # Apr
        assert validate_timestamp_format("20240630120000") is True  # Jun

        # 28/29 days (leap year)
        assert validate_timestamp_format("20240229120000") is True  # Feb leap

    def test_invalid_days_per_month(self):
        """Test invalid days for months."""
        # April has 30 days, not 31
        assert validate_timestamp_format("20240431120000") is False

        # February (non-leap) has 28 days
        assert validate_timestamp_format("20230230120000") is False
