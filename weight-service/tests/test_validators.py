"""Tests for custom validation functions."""

import pytest
from datetime import datetime
from src.utils.validators import (
    validate_container_id_format,
    validate_container_list,
    validate_truck_license,
    validate_weight_value,
    validate_direction,
    validate_datetime_string,
    validate_date_range,
    validate_filename,
    validate_session_sequence,
    validate_produce_type,
    validate_direction_filter,
)


# ============================================================================
# Container ID Validation Tests
# ============================================================================

class TestContainerIdValidation:
    """Test container ID format validation."""

    def test_valid_container_ids(self):
        """Test valid container ID formats."""
        valid_ids = [
            "C001",
            "CONTAINER-123",
            "C_001",
            "ABC-123_XYZ",
            "1234567890",
            "a" * 15,  # Max length
        ]
        for container_id in valid_ids:
            is_valid, error = validate_container_id_format(container_id)
            assert is_valid, f"Expected '{container_id}' to be valid, got error: {error}"
            assert error is None

    def test_empty_container_id(self):
        """Test empty container ID."""
        is_valid, error = validate_container_id_format("")
        assert not is_valid
        assert "cannot be empty" in error

    def test_container_id_too_long(self):
        """Test container ID exceeding 15 characters."""
        is_valid, error = validate_container_id_format("A" * 16)
        assert not is_valid
        assert "exceeds 15 character" in error

    def test_container_id_invalid_characters(self):
        """Test container ID with invalid characters."""
        invalid_ids = [
            "C@001",
            "C#001",
            "C 001",
            "C.001",
            "C/001",
            "C\\001",
        ]
        for container_id in invalid_ids:
            is_valid, error = validate_container_id_format(container_id)
            assert not is_valid, f"Expected '{container_id}' to be invalid"
            assert "invalid characters" in error

    def test_reserved_container_ids(self):
        """Test reserved container IDs."""
        reserved = ["na", "NA", "none", "NONE", "null", "NULL", "undefined", "empty"]
        for container_id in reserved:
            is_valid, error = validate_container_id_format(container_id)
            assert not is_valid, f"Expected '{container_id}' to be rejected as reserved"
            assert "reserved identifier" in error


class TestContainerListValidation:
    """Test container list validation."""

    def test_valid_container_list(self):
        """Test valid container list."""
        is_valid, containers, errors = validate_container_list("C001,C002,C003")
        assert is_valid
        assert containers == ["C001", "C002", "C003"]
        assert errors == []

    def test_container_list_with_whitespace(self):
        """Test container list with extra whitespace."""
        is_valid, containers, errors = validate_container_list(" C001 , C002 , C003 ")
        assert is_valid
        assert containers == ["C001", "C002", "C003"]
        assert errors == []

    def test_empty_container_list(self):
        """Test empty container list."""
        is_valid, containers, errors = validate_container_list("")
        assert not is_valid
        assert containers == []
        assert "cannot be empty" in errors[0]

    def test_container_list_only_whitespace(self):
        """Test container list with only whitespace."""
        is_valid, containers, errors = validate_container_list("   ")
        assert not is_valid
        assert "cannot be empty" in errors[0]

    def test_container_list_only_commas_and_whitespace(self):
        """Test container list with only commas and whitespace."""
        is_valid, containers, errors = validate_container_list("  ,  ,  ")
        assert not is_valid
        assert containers == []
        assert "cannot be empty after parsing" in errors[0]

    def test_container_list_with_duplicates(self):
        """Test container list with duplicate IDs."""
        is_valid, containers, errors = validate_container_list("C001,C002,C001")
        assert not is_valid
        assert "Duplicate" in errors[0]
        assert "C001" in errors[0]

    def test_container_list_with_invalid_id(self):
        """Test container list with invalid container ID."""
        is_valid, containers, errors = validate_container_list("C001,C@002,C003")
        assert not is_valid
        assert len(errors) > 0
        assert "invalid characters" in errors[0]

    def test_single_container(self):
        """Test single container in list."""
        is_valid, containers, errors = validate_container_list("C001")
        assert is_valid
        assert containers == ["C001"]
        assert errors == []


# ============================================================================
# Truck License Validation Tests
# ============================================================================

class TestTruckLicenseValidation:
    """Test truck license validation."""

    def test_valid_truck_licenses(self):
        """Test valid truck license formats."""
        valid_licenses = [
            "ABC123",
            "12-345",
            "AB 123 CD",
            "ABC-123-DEF",
            "1234567890",
        ]
        for license_plate in valid_licenses:
            is_valid, error = validate_truck_license(license_plate)
            assert is_valid, f"Expected '{license_plate}' to be valid, got error: {error}"
            assert error is None

    def test_na_truck_license(self):
        """Test 'na' is valid for truck license."""
        is_valid, error = validate_truck_license("na")
        assert is_valid
        assert error is None

    def test_empty_truck_license(self):
        """Test empty truck license is valid."""
        is_valid, error = validate_truck_license("")
        assert is_valid
        assert error is None

    def test_truck_license_too_long(self):
        """Test truck license exceeding 20 characters."""
        is_valid, error = validate_truck_license("A" * 21)
        assert not is_valid
        assert "exceeds 20 character" in error

    def test_truck_license_invalid_characters(self):
        """Test truck license with invalid characters."""
        invalid_licenses = [
            "AB@123",
            "AB#123",
            "AB.123",
            "AB/123",
            "AB\\123",
            "AB_123",  # Underscore not allowed
        ]
        for license_plate in invalid_licenses:
            is_valid, error = validate_truck_license(license_plate)
            assert not is_valid, f"Expected '{license_plate}' to be invalid"
            assert "invalid characters" in error

    def test_truck_license_only_spaces(self):
        """Test truck license with only spaces."""
        is_valid, error = validate_truck_license("   ")
        assert not is_valid
        assert "cannot be only spaces" in error


# ============================================================================
# Weight Value Validation Tests
# ============================================================================

class TestWeightValueValidation:
    """Test weight value validation."""

    def test_valid_weights_kg(self):
        """Test valid weights in kg."""
        valid_weights = [1, 100, 5000, 50000, 100000]
        for weight in valid_weights:
            is_valid, error = validate_weight_value(weight, "kg")
            assert is_valid, f"Expected {weight}kg to be valid, got error: {error}"
            assert error is None

    def test_valid_weights_lbs(self):
        """Test valid weights in lbs."""
        valid_weights = [10, 500, 11000, 220000]  # Up to ~100,000kg
        for weight in valid_weights:
            is_valid, error = validate_weight_value(weight, "lbs")
            assert is_valid, f"Expected {weight}lbs to be valid, got error: {error}"
            assert error is None

    def test_zero_weight(self):
        """Test zero weight is invalid."""
        is_valid, error = validate_weight_value(0, "kg")
        assert not is_valid
        assert "positive value" in error

    def test_negative_weight(self):
        """Test negative weight is invalid."""
        is_valid, error = validate_weight_value(-100, "kg")
        assert not is_valid
        assert "positive value" in error

    def test_invalid_unit(self):
        """Test invalid weight unit."""
        is_valid, error = validate_weight_value(1000, "grams")
        assert not is_valid
        assert "Invalid weight unit" in error

    def test_weight_too_large(self):
        """Test weight exceeding maximum."""
        is_valid, error = validate_weight_value(100001, "kg")
        assert not is_valid
        assert "too large" in error

    def test_weight_too_small_after_conversion(self):
        """Test weight too small after conversion."""
        is_valid, error = validate_weight_value(1, "lbs")  # 0.45kg rounds to 0
        assert not is_valid
        assert "too small" in error


# ============================================================================
# Direction Validation Tests
# ============================================================================

class TestDirectionValidation:
    """Test direction validation."""

    def test_valid_directions(self):
        """Test valid directions."""
        valid_directions = ["in", "out", "none"]
        for direction in valid_directions:
            is_valid, error = validate_direction(direction)
            assert is_valid, f"Expected '{direction}' to be valid, got error: {error}"
            assert error is None

    def test_invalid_directions(self):
        """Test invalid directions."""
        invalid_directions = ["IN", "OUT", "enter", "exit", ""]
        for direction in invalid_directions:
            is_valid, error = validate_direction(direction)
            assert not is_valid, f"Expected '{direction}' to be invalid"
            assert "Invalid direction" in error


# ============================================================================
# DateTime Validation Tests
# ============================================================================

class TestDateTimeValidation:
    """Test datetime string validation."""

    def test_valid_datetime_strings(self):
        """Test valid datetime strings."""
        valid_datetimes = [
            "20241201120000",
            "20230101000000",
            "20251231235959",
        ]
        for dt_str in valid_datetimes:
            is_valid, parsed, error = validate_datetime_string(dt_str)
            assert is_valid, f"Expected '{dt_str}' to be valid, got error: {error}"
            assert parsed is not None
            assert error is None

    def test_empty_datetime_string(self):
        """Test empty datetime string."""
        is_valid, parsed, error = validate_datetime_string("")
        assert not is_valid
        assert parsed is None
        assert "cannot be empty" in error

    def test_invalid_datetime_format(self):
        """Test invalid datetime format."""
        invalid_formats = [
            "2024-12-01",
            "20241201",
            "202412011200",
            "2024120112000",  # 13 digits
            "202412011200000",  # 15 digits
            "abcd1201120000",
        ]
        for dt_str in invalid_formats:
            is_valid, parsed, error = validate_datetime_string(dt_str)
            assert not is_valid, f"Expected '{dt_str}' to be invalid"
            assert parsed is None

    def test_invalid_datetime_value(self):
        """Test invalid datetime values."""
        invalid_dates = [
            "20241301120000",  # Invalid month
            "20240001120000",  # Invalid month
            "20241232120000",  # Invalid day
            "20241200120000",  # Invalid day
            "20241201250000",  # Invalid hour
            "20241201126000",  # Invalid minute
            "20241201120060",  # Invalid second
        ]
        for dt_str in invalid_dates:
            is_valid, parsed, error = validate_datetime_string(dt_str)
            assert not is_valid, f"Expected '{dt_str}' to be invalid"
            assert parsed is None

    def test_datetime_too_far_past(self):
        """Test datetime too far in the past."""
        is_valid, parsed, error = validate_datetime_string("19991231235959")
        assert not is_valid
        assert "too far in the past" in error

    def test_datetime_too_far_future(self):
        """Test datetime too far in the future."""
        current_year = datetime.now().year
        future_year = current_year + 20
        is_valid, parsed, error = validate_datetime_string(f"{future_year}1231235959")
        assert not is_valid
        assert "too far in the future" in error


class TestDateRangeValidation:
    """Test date range validation."""

    def test_valid_date_range(self):
        """Test valid date range."""
        is_valid, error = validate_date_range("20241201000000", "20241231235959")
        assert is_valid
        assert error is None

    def test_none_date_range(self):
        """Test None values in date range."""
        is_valid, error = validate_date_range(None, None)
        assert is_valid
        assert error is None

    def test_only_from_time(self):
        """Test only from_time specified."""
        is_valid, error = validate_date_range("20241201000000", None)
        assert is_valid
        assert error is None

    def test_only_to_time(self):
        """Test only to_time specified."""
        is_valid, error = validate_date_range(None, "20241231235959")
        assert is_valid
        assert error is None

    def test_invalid_from_time(self):
        """Test invalid from_time."""
        is_valid, error = validate_date_range("invalid", "20241231235959")
        assert not is_valid
        assert "Invalid from_time" in error

    def test_invalid_to_time(self):
        """Test invalid to_time."""
        is_valid, error = validate_date_range("20241201000000", "invalid")
        assert not is_valid
        assert "Invalid to_time" in error

    def test_from_time_after_to_time(self):
        """Test from_time after to_time."""
        is_valid, error = validate_date_range("20241231235959", "20241201000000")
        assert not is_valid
        assert "must be before" in error

    def test_from_time_equal_to_time(self):
        """Test from_time equal to to_time."""
        same_time = "20241215120000"
        is_valid, error = validate_date_range(same_time, same_time)
        assert not is_valid
        assert "must be before" in error


# ============================================================================
# Filename Validation Tests
# ============================================================================

class TestFilenameValidation:
    """Test filename validation."""

    def test_valid_filenames(self):
        """Test valid filenames."""
        valid_filenames = [
            "data.csv",
            "containers.json",
            "batch-upload.csv",
            "file_name.json",
            "file name with spaces.csv",
            "123.csv",
        ]
        for filename in valid_filenames:
            is_valid, error = validate_filename(filename)
            assert is_valid, f"Expected '{filename}' to be valid, got error: {error}"
            assert error is None

    def test_empty_filename(self):
        """Test empty filename."""
        is_valid, error = validate_filename("")
        assert not is_valid
        assert "cannot be empty" in error

    def test_path_traversal_attempts(self):
        """Test path traversal attempts."""
        malicious_filenames = [
            "../etc/passwd",
            "..\\windows\\system32",
            "data/../passwords.csv",
            "path/to/file.csv",
            "path\\to\\file.csv",
        ]
        for filename in malicious_filenames:
            is_valid, error = validate_filename(filename)
            assert not is_valid, f"Expected '{filename}' to be blocked"
            assert "invalid path characters" in error

    def test_filename_too_long(self):
        """Test filename exceeding 255 characters."""
        long_filename = "a" * 252 + ".csv"  # 252 + 4 = 256 chars (exceeds 255)
        is_valid, error = validate_filename(long_filename)
        assert not is_valid
        assert "too long" in error

    def test_invalid_file_extension(self):
        """Test invalid file extensions."""
        invalid_extensions = [
            "data.txt",
            "data.xml",
            "data.exe",
            "data",
        ]
        for filename in invalid_extensions:
            is_valid, error = validate_filename(filename)
            assert not is_valid, f"Expected '{filename}' to be invalid"
            assert "Invalid file extension" in error

    def test_filename_invalid_characters(self):
        """Test filename with invalid characters."""
        invalid_filenames = [
            "data@file.csv",
            "data#file.csv",
            "data$file.csv",
            "data&file.csv",
        ]
        for filename in invalid_filenames:
            is_valid, error = validate_filename(filename)
            assert not is_valid, f"Expected '{filename}' to be invalid"
            assert "invalid characters" in error


# ============================================================================
# Session Sequence Validation Tests
# ============================================================================

class TestSessionSequenceValidation:
    """Test session sequence validation."""

    def test_first_in_transaction(self):
        """Test first IN transaction is valid."""
        is_valid, error = validate_session_sequence("in", [])
        assert is_valid
        assert error is None

    def test_out_after_in(self):
        """Test OUT after IN is valid."""
        is_valid, error = validate_session_sequence("out", ["in"])
        assert is_valid
        assert error is None

    def test_out_without_in(self):
        """Test OUT without IN is invalid."""
        is_valid, error = validate_session_sequence("out", [])
        assert not is_valid
        assert "requires a previous IN" in error

    def test_duplicate_out(self):
        """Test duplicate OUT transaction."""
        is_valid, error = validate_session_sequence("out", ["in", "out"])
        assert not is_valid
        assert "Multiple OUT" in error

    def test_duplicate_in(self):
        """Test duplicate IN transaction."""
        is_valid, error = validate_session_sequence("in", ["in"])
        assert not is_valid
        assert "Multiple IN" in error

    def test_none_direction_always_valid(self):
        """Test 'none' direction is always valid."""
        is_valid, error = validate_session_sequence("none", [])
        assert is_valid
        assert error is None

        is_valid, error = validate_session_sequence("none", ["in", "out"])
        assert is_valid
        assert error is None


# ============================================================================
# Produce Type Validation Tests
# ============================================================================

class TestProduceTypeValidation:
    """Test produce type validation."""

    def test_valid_produce_types(self):
        """Test valid produce types."""
        valid_produces = [
            "apples",
            "oranges",
            "red-delicious",
            "gala_apples",
            "Fuji Apples, Grade A",
            "123",
        ]
        for produce in valid_produces:
            is_valid, error = validate_produce_type(produce)
            assert is_valid, f"Expected '{produce}' to be valid, got error: {error}"
            assert error is None

    def test_na_produce(self):
        """Test 'na' is valid for produce."""
        is_valid, error = validate_produce_type("na")
        assert is_valid
        assert error is None

    def test_empty_produce(self):
        """Test empty produce is valid."""
        is_valid, error = validate_produce_type("")
        assert is_valid
        assert error is None

    def test_produce_too_long(self):
        """Test produce type exceeding 50 characters."""
        is_valid, error = validate_produce_type("a" * 51)
        assert not is_valid
        assert "exceeds 50 character" in error

    def test_produce_invalid_characters(self):
        """Test produce with invalid characters."""
        invalid_produces = [
            "apples@home",
            "apples#1",
            "apples$100",
            "apples&oranges",
        ]
        for produce in invalid_produces:
            is_valid, error = validate_produce_type(produce)
            assert not is_valid, f"Expected '{produce}' to be invalid"
            assert "invalid characters" in error

    def test_produce_only_spaces(self):
        """Test produce with only spaces."""
        is_valid, error = validate_produce_type("   ")
        assert not is_valid
        assert "cannot be only spaces" in error


# ============================================================================
# Direction Filter Validation Tests
# ============================================================================

class TestDirectionFilterValidation:
    """Test direction filter validation."""

    def test_valid_direction_filters(self):
        """Test valid direction filters."""
        is_valid, filters, error = validate_direction_filter("in,out,none")
        assert is_valid
        assert filters == ["in", "out", "none"]
        assert error is None

    def test_single_direction_filter(self):
        """Test single direction filter."""
        is_valid, filters, error = validate_direction_filter("in")
        assert is_valid
        assert filters == ["in"]
        assert error is None

    def test_filter_with_whitespace(self):
        """Test filter with extra whitespace."""
        is_valid, filters, error = validate_direction_filter(" in , out , none ")
        assert is_valid
        assert filters == ["in", "out", "none"]
        assert error is None

    def test_filter_case_insensitive(self):
        """Test filter is case-insensitive."""
        is_valid, filters, error = validate_direction_filter("IN,OUT,NONE")
        assert is_valid
        assert filters == ["in", "out", "none"]
        assert error is None

    def test_empty_filter(self):
        """Test empty filter string."""
        is_valid, filters, error = validate_direction_filter("")
        assert not is_valid
        assert filters == []
        assert "cannot be empty" in error

    def test_filter_only_whitespace(self):
        """Test filter with only whitespace."""
        is_valid, filters, error = validate_direction_filter("   ")
        assert not is_valid
        assert "cannot be empty" in error

    def test_invalid_direction_in_filter(self):
        """Test invalid direction in filter."""
        is_valid, filters, error = validate_direction_filter("in,invalid,out")
        assert not is_valid
        assert "Invalid filter directions" in error
        assert "invalid" in error

    def test_filter_removes_duplicates(self):
        """Test filter removes duplicates."""
        is_valid, filters, error = validate_direction_filter("in,out,in,none,out")
        assert is_valid
        assert filters == ["in", "out", "none"]
        assert error is None
