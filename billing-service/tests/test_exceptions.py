"""Tests for custom exceptions."""

import pytest

from src.utils.exceptions import (
    BillingServiceException,
    DatabaseError,
    DuplicateError,
    FileError,
    NotFoundError,
    ValidationError,
    WeightServiceError,
)


class TestBillingServiceException:
    """Test base BillingServiceException."""

    def test_raise_base_exception(self):
        """Test raising base exception."""
        with pytest.raises(BillingServiceException) as exc_info:
            raise BillingServiceException("Base error")

        assert str(exc_info.value) == "Base error"

    def test_base_exception_is_exception(self):
        """Test base exception inherits from Exception."""
        assert issubclass(BillingServiceException, Exception)

    def test_base_exception_without_message(self):
        """Test base exception without message."""
        with pytest.raises(BillingServiceException):
            raise BillingServiceException()

    def test_base_exception_with_multiple_args(self):
        """Test base exception with multiple arguments."""
        with pytest.raises(BillingServiceException) as exc_info:
            raise BillingServiceException("Error", "Details")

        assert "Error" in str(exc_info.value)


class TestDatabaseError:
    """Test DatabaseError exception."""

    def test_raise_database_error(self):
        """Test raising database error."""
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("Connection failed")

        assert str(exc_info.value) == "Connection failed"

    def test_database_error_inherits_from_base(self):
        """Test DatabaseError inherits from BillingServiceException."""
        assert issubclass(DatabaseError, BillingServiceException)

    def test_catch_as_base_exception(self):
        """Test catching DatabaseError as base exception."""
        with pytest.raises(BillingServiceException):
            raise DatabaseError("Database error")

    def test_database_error_long_message(self):
        """Test database error with long message."""
        long_message = "Database connection failed: " + "x" * 500
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError(long_message)

        assert len(str(exc_info.value)) > 500


class TestValidationError:
    """Test ValidationError exception."""

    def test_raise_validation_error(self):
        """Test raising validation error."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid data format")

        assert str(exc_info.value) == "Invalid data format"

    def test_validation_error_inherits_from_base(self):
        """Test ValidationError inherits from BillingServiceException."""
        assert issubclass(ValidationError, BillingServiceException)

    def test_validation_error_with_field_info(self):
        """Test validation error with field information."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Field 'name' is required")

        assert "name" in str(exc_info.value)

    def test_catch_specific_validation_error(self):
        """Test catching specific ValidationError."""
        try:
            raise ValidationError("Validation failed")
        except ValidationError as e:
            assert str(e) == "Validation failed"
        except Exception:
            pytest.fail("Should catch ValidationError specifically")


class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_raise_not_found_error(self):
        """Test raising not found error."""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("Resource not found")

        assert str(exc_info.value) == "Resource not found"

    def test_not_found_error_inherits_from_base(self):
        """Test NotFoundError inherits from BillingServiceException."""
        assert issubclass(NotFoundError, BillingServiceException)

    def test_not_found_error_with_id(self):
        """Test not found error with resource ID."""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("Provider with ID 123 not found")

        assert "123" in str(exc_info.value)

    def test_not_found_error_empty_message(self):
        """Test not found error with empty message."""
        with pytest.raises(NotFoundError):
            raise NotFoundError("")


class TestDuplicateError:
    """Test DuplicateError exception."""

    def test_raise_duplicate_error(self):
        """Test raising duplicate error."""
        with pytest.raises(DuplicateError) as exc_info:
            raise DuplicateError("Resource already exists")

        assert str(exc_info.value) == "Resource already exists"

    def test_duplicate_error_inherits_from_base(self):
        """Test DuplicateError inherits from BillingServiceException."""
        assert issubclass(DuplicateError, BillingServiceException)

    def test_duplicate_error_with_key(self):
        """Test duplicate error with key information."""
        with pytest.raises(DuplicateError) as exc_info:
            raise DuplicateError("Truck with ID 'ABC123' already exists")

        assert "ABC123" in str(exc_info.value)


class TestWeightServiceError:
    """Test WeightServiceError exception."""

    def test_raise_weight_service_error(self):
        """Test raising weight service error."""
        with pytest.raises(WeightServiceError) as exc_info:
            raise WeightServiceError("Weight service unavailable")

        assert str(exc_info.value) == "Weight service unavailable"

    def test_weight_service_error_inherits_from_base(self):
        """Test WeightServiceError inherits from BillingServiceException."""
        assert issubclass(WeightServiceError, BillingServiceException)

    def test_weight_service_error_with_status_code(self):
        """Test weight service error with HTTP status code."""
        with pytest.raises(WeightServiceError) as exc_info:
            raise WeightServiceError("Weight service returned 503")

        assert "503" in str(exc_info.value)

    def test_weight_service_error_timeout(self):
        """Test weight service error for timeout."""
        with pytest.raises(WeightServiceError) as exc_info:
            raise WeightServiceError("Weight service timeout after 30s")

        assert "timeout" in str(exc_info.value).lower()


class TestFileError:
    """Test FileError exception."""

    def test_raise_file_error(self):
        """Test raising file error."""
        with pytest.raises(FileError) as exc_info:
            raise FileError("File not found")

        assert str(exc_info.value) == "File not found"

    def test_file_error_inherits_from_base(self):
        """Test FileError inherits from BillingServiceException."""
        assert issubclass(FileError, BillingServiceException)

    def test_file_error_with_path(self):
        """Test file error with file path."""
        with pytest.raises(FileError) as exc_info:
            raise FileError("File /in/rates.xlsx not found")

        assert "/in/rates.xlsx" in str(exc_info.value)

    def test_file_error_invalid_format(self):
        """Test file error for invalid format."""
        with pytest.raises(FileError) as exc_info:
            raise FileError("Excel file must contain columns: Product, Rate, Scope")

        assert "columns" in str(exc_info.value).lower()


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test all custom exceptions inherit from base."""
        exceptions = [
            DatabaseError,
            ValidationError,
            NotFoundError,
            DuplicateError,
            WeightServiceError,
            FileError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, BillingServiceException)

    def test_catch_all_with_base_exception(self):
        """Test catching all custom exceptions with base exception."""
        exceptions = [
            DatabaseError("DB error"),
            ValidationError("Validation error"),
            NotFoundError("Not found"),
            DuplicateError("Duplicate"),
            WeightServiceError("Service error"),
            FileError("File error"),
        ]

        for exc in exceptions:
            with pytest.raises(BillingServiceException):
                raise exc

    def test_exception_type_checking(self):
        """Test type checking for different exceptions."""
        db_error = DatabaseError("Error")
        validation_error = ValidationError("Error")

        assert isinstance(db_error, BillingServiceException)
        assert isinstance(db_error, DatabaseError)
        assert not isinstance(db_error, ValidationError)

        assert isinstance(validation_error, BillingServiceException)
        assert isinstance(validation_error, ValidationError)
        assert not isinstance(validation_error, DatabaseError)

    def test_exception_string_representation(self):
        """Test string representation of exceptions."""
        exceptions_with_messages = [
            (DatabaseError("DB failed"), "DB failed"),
            (ValidationError("Invalid"), "Invalid"),
            (NotFoundError("Missing"), "Missing"),
            (DuplicateError("Exists"), "Exists"),
            (WeightServiceError("Unavailable"), "Unavailable"),
            (FileError("Not found"), "Not found"),
        ]

        for exc, expected_message in exceptions_with_messages:
            assert str(exc) == expected_message


class TestExceptionInRealScenarios:
    """Test exceptions in realistic scenarios."""

    def test_database_connection_failure_scenario(self):
        """Test database connection failure scenario."""

        def connect_to_database():
            raise DatabaseError("Cannot connect to MySQL on port 3307")

        with pytest.raises(DatabaseError) as exc_info:
            connect_to_database()

        assert "3307" in str(exc_info.value)

    def test_provider_not_found_scenario(self):
        """Test provider not found scenario."""

        def get_provider(provider_id):
            raise NotFoundError(f"Provider {provider_id} not found")

        with pytest.raises(NotFoundError) as exc_info:
            get_provider(999)

        assert "999" in str(exc_info.value)

    def test_duplicate_truck_scenario(self):
        """Test duplicate truck registration scenario."""

        def register_truck(truck_id):
            raise DuplicateError(f"Truck {truck_id} already registered")

        with pytest.raises(DuplicateError) as exc_info:
            register_truck("ABC123")

        assert "ABC123" in str(exc_info.value)

    def test_excel_file_validation_scenario(self):
        """Test Excel file validation scenario."""

        def validate_excel_file(filename):
            raise FileError("Excel file must contain columns: Product, Rate, Scope")

        with pytest.raises(FileError) as exc_info:
            validate_excel_file("rates.xlsx")

        assert "columns" in str(exc_info.value).lower()

    def test_weight_service_timeout_scenario(self):
        """Test weight service timeout scenario."""

        def fetch_weights():
            raise WeightServiceError("Weight service timeout after 30 seconds")

        with pytest.raises(WeightServiceError) as exc_info:
            fetch_weights()

        assert "timeout" in str(exc_info.value).lower()
