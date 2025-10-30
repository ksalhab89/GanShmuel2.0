"""Comprehensive tests for FileService."""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.file_service import (
    FileService,
    FileProcessingError,
    FileValidationError
)
from src.models.schemas import ContainerWeightData


class TestFileService:
    """Test cases for FileService."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def file_service(self, mock_session, temp_dir):
        """Create FileService instance with mocked dependencies."""
        service = FileService(mock_session, upload_dir=temp_dir)
        service.container_service = AsyncMock()
        return service

    # ========================================================================
    # Test Initialization
    # ========================================================================

    @pytest.mark.asyncio
    async def test_init_creates_upload_dir(self, mock_session):
        """Test that FileService creates upload directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = os.path.join(tmpdir, "new_upload_dir")
            assert not os.path.exists(upload_dir)

            service = FileService(mock_session, upload_dir=upload_dir)

            assert os.path.exists(upload_dir)
            assert service.upload_dir == upload_dir

    @pytest.mark.asyncio
    async def test_init_default_upload_dir(self, mock_session):
        """Test that FileService uses default /in directory."""
        with patch('pathlib.Path.mkdir'):
            service = FileService(mock_session)
            assert service.upload_dir == "/in"

    # ========================================================================
    # Test CSV File Processing
    # ========================================================================

    @pytest.mark.asyncio
    async def test_parse_csv_file_two_columns_kg(self, file_service, temp_dir):
        """Test parsing CSV with 2 columns (id,weight) - kg detection."""
        csv_content = "C001,50\nC002,100\nC003,45"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        assert len(result) == 3
        assert result[0].id == "C001"
        assert result[0].weight == 50
        assert result[0].unit == "kg"
        assert result[1].id == "C002"
        assert result[1].weight == 100
        assert result[1].unit == "kg"

    @pytest.mark.asyncio
    async def test_parse_csv_file_two_columns_lbs_detection(self, file_service, temp_dir):
        """Test parsing CSV with 2 columns - lbs auto-detection for heavy weights."""
        csv_content = "C001,600\nC002,1000"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        assert len(result) == 2
        assert result[0].unit == "lbs"  # > 500 triggers lbs
        assert result[1].unit == "lbs"

    @pytest.mark.asyncio
    async def test_parse_csv_file_three_columns_with_unit(self, file_service, temp_dir):
        """Test parsing CSV with 3 columns (id,weight,unit)."""
        csv_content = "C001,50,kg\nC002,110,lbs\nC003,45,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        assert len(result) == 3
        assert result[0].unit == "kg"
        assert result[1].unit == "lbs"
        assert result[2].unit == "kg"

    @pytest.mark.asyncio
    async def test_parse_csv_file_with_header(self, file_service, temp_dir):
        """Test parsing CSV with header row."""
        csv_content = "container_id,weight,unit\nC001,50,kg\nC002,110,lbs"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        assert len(result) == 2
        assert result[0].id == "C001"
        assert result[1].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_file_skip_empty_rows(self, file_service, temp_dir):
        """Test that empty rows are skipped."""
        csv_content = "C001,50,kg\n\n  \n\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        assert len(result) == 2
        assert result[0].id == "C001"
        assert result[1].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_file_empty_container_id(self, file_service, temp_dir):
        """Test handling of empty container ID."""
        csv_content = ",50,kg\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        # Should skip invalid row and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_file_invalid_weight(self, file_service, temp_dir):
        """Test handling of invalid weight values."""
        csv_content = "C001,abc,kg\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        # Should skip invalid row and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_file_invalid_unit(self, file_service, temp_dir):
        """Test handling of invalid unit values."""
        csv_content = "C001,50,xyz\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        # Should skip invalid row and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_file_invalid_column_count(self, file_service, temp_dir):
        """Test handling of rows with invalid column count."""
        csv_content = "C001,50,kg,extra\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        # Should skip invalid row and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_file_not_found(self, file_service, temp_dir):
        """Test handling of non-existent CSV file."""
        csv_path = os.path.join(temp_dir, "nonexistent.csv")

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_csv_file(csv_path)

        assert "CSV file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_csv_file_empty_file(self, file_service, temp_dir):
        """Test handling of empty CSV file with header only."""
        csv_content = "container_id,weight,unit\n"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Empty file with header returns empty list
        result = await file_service._parse_csv_file(csv_path)
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_csv_file_all_invalid_rows(self, file_service, temp_dir):
        """Test handling when all rows are invalid."""
        csv_content = "C001,abc,kg\nC002,xyz,lbs\n,50,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_csv_file(csv_path)

        assert "No valid data found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_csv_file_validation_error(self, file_service, temp_dir):
        """Test handling of validation errors in CSV."""
        csv_content = "C001,0,kg\nC002,60,kg"  # 0 weight is invalid
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        # Should skip invalid row and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_csv_with_whitespace(self, file_service, temp_dir):
        """Test parsing CSV with whitespace in values."""
        csv_content = " C001 , 50 , kg \n C002 , 60 , lbs "
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service._parse_csv_file(csv_path)

        assert len(result) == 2
        assert result[0].id == "C001"
        assert result[0].weight == 50

    @pytest.mark.asyncio
    async def test_parse_csv_file_truly_empty_with_header(self, file_service, temp_dir):
        """Test handling of CSV file with header only (next returns None)."""
        # This edge case covers line 123
        csv_content = ""
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Empty file returns empty list
        result = await file_service._parse_csv_file(csv_path)
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_csv_unexpected_row_error(self, file_service, temp_dir):
        """Test handling of unexpected errors during CSV row processing."""
        csv_content = "C001,50,kg\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Mock validate to raise unexpected exception to trigger line 191-192
        original_validate = file_service._validate_csv_container_data
        def mock_validate(cid, weight, unit):
            if cid == "C001":
                raise RuntimeError("Unexpected validation error")
            original_validate(cid, weight, unit)

        file_service._validate_csv_container_data = mock_validate

        result = await file_service._parse_csv_file(csv_path)

        # Should skip the errored row and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

        # Restore original
        file_service._validate_csv_container_data = original_validate

    # ========================================================================
    # Test JSON File Processing
    # ========================================================================

    @pytest.mark.asyncio
    async def test_parse_json_file_valid(self, file_service, temp_dir):
        """Test parsing valid JSON file."""
        json_data = [
            {"id": "C001", "weight": 50, "unit": "kg"},
            {"id": "C002", "weight": 110, "unit": "lbs"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        assert len(result) == 2
        assert result[0].id == "C001"
        assert result[0].weight == 50
        assert result[0].unit == "kg"
        assert result[1].id == "C002"
        assert result[1].weight == 110
        assert result[1].unit == "lbs"

    @pytest.mark.asyncio
    async def test_parse_json_file_default_unit(self, file_service, temp_dir):
        """Test parsing JSON file with default unit (kg)."""
        json_data = [
            {"id": "C001", "weight": 50},  # No unit specified
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        assert len(result) == 2
        assert result[0].unit == "kg"  # Default

    @pytest.mark.asyncio
    async def test_parse_json_file_not_array(self, file_service, temp_dir):
        """Test handling of JSON that is not an array."""
        json_data = {"id": "C001", "weight": 50}
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_json_file(json_path)

        assert "must contain an array" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_json_file_item_not_object(self, file_service, temp_dir):
        """Test handling of JSON array with non-object items."""
        json_data = ["C001", "C002"]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_json_file(json_path)

        assert "No valid data found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_json_file_missing_id(self, file_service, temp_dir):
        """Test handling of JSON items missing 'id' field."""
        json_data = [
            {"weight": 50, "unit": "kg"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        # Should skip invalid item and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_json_file_missing_weight(self, file_service, temp_dir):
        """Test handling of JSON items missing 'weight' field."""
        json_data = [
            {"id": "C001", "unit": "kg"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        # Should skip invalid item and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_json_file_invalid_weight(self, file_service, temp_dir):
        """Test handling of JSON items with invalid weight."""
        json_data = [
            {"id": "C001", "weight": "abc", "unit": "kg"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        # Should skip invalid item and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_json_file_invalid_unit(self, file_service, temp_dir):
        """Test handling of JSON items with invalid unit."""
        json_data = [
            {"id": "C001", "weight": 50, "unit": "xyz"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        # Should skip invalid item and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_json_file_not_found(self, file_service, temp_dir):
        """Test handling of non-existent JSON file."""
        json_path = os.path.join(temp_dir, "nonexistent.json")

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_json_file(json_path)

        assert "JSON file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_json_file_invalid_json(self, file_service, temp_dir):
        """Test handling of invalid JSON format."""
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_json_file(json_path)

        assert "Invalid JSON format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_json_file_all_invalid_items(self, file_service, temp_dir):
        """Test handling when all JSON items are invalid."""
        json_data = [
            {"weight": 50},  # Missing id
            {"id": "C002"},  # Missing weight
            {"id": "C003", "weight": "abc"}  # Invalid weight
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service._parse_json_file(json_path)

        assert "No valid data found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_json_file_validation_error(self, file_service, temp_dir):
        """Test handling of validation errors in JSON."""
        json_data = [
            {"id": "C001", "weight": 0, "unit": "kg"},  # 0 weight is invalid
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service._parse_json_file(json_path)

        # Should skip invalid item and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

    @pytest.mark.asyncio
    async def test_parse_json_unexpected_item_error(self, file_service, temp_dir):
        """Test handling of unexpected errors during JSON item processing."""
        json_data = [
            {"id": "C001", "weight": 50, "unit": "kg"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        # Mock validate to raise unexpected exception to trigger line 281-282
        original_validate = file_service._validate_json_container_data
        def mock_validate(cid, weight, unit):
            if cid == "C001":
                raise RuntimeError("Unexpected validation error")
            original_validate(cid, weight, unit)

        file_service._validate_json_container_data = mock_validate

        result = await file_service._parse_json_file(json_path)

        # Should skip the errored item and process valid one
        assert len(result) == 1
        assert result[0].id == "C002"

        # Restore original
        file_service._validate_json_container_data = original_validate

    # ========================================================================
    # Test File Validation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_file_format_not_found(self, file_service, temp_dir):
        """Test validation of non-existent file."""
        file_path = os.path.join(temp_dir, "nonexistent.csv")

        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_file_format(file_path)

        assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_format_not_readable(self, file_service, temp_dir):
        """Test validation of non-readable file."""
        file_path = os.path.join(temp_dir, "test.csv")

        with open(file_path, 'w') as f:
            f.write("test")

        # Make file non-readable
        os.chmod(file_path, 0o000)

        try:
            with pytest.raises(FileValidationError) as exc_info:
                file_service._validate_file_format(file_path)

            assert "File not readable" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            os.chmod(file_path, 0o644)

    @pytest.mark.asyncio
    async def test_validate_file_format_too_large(self, file_service, temp_dir):
        """Test validation of file that exceeds size limit."""
        file_path = os.path.join(temp_dir, "large.csv")

        # Create a file larger than 10MB
        with open(file_path, 'wb') as f:
            f.write(b'0' * (11 * 1024 * 1024))  # 11MB

        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_file_format(file_path)

        assert "File too large" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_format_invalid_extension(self, file_service, temp_dir):
        """Test validation of file with invalid extension."""
        file_path = os.path.join(temp_dir, "test.txt")

        with open(file_path, 'w') as f:
            f.write("test")

        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_file_format(file_path)

        assert "Invalid file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_format_path_traversal(self, file_service, temp_dir):
        """Test validation prevents path traversal attacks."""
        file_path = "../../../etc/passwd"

        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_file_format(file_path)

        # Could be either not found or security violation depending on path check order
        assert "security violation" in str(exc_info.value) or "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_format_absolute_path_outside_upload_dir(self, file_service, temp_dir):
        """Test validation prevents absolute paths outside upload directory."""
        # Create a file outside temp_dir
        outside_file = "/tmp/outside.csv"
        try:
            with open(outside_file, 'w') as f:
                f.write("test")

            with pytest.raises(FileValidationError) as exc_info:
                file_service._validate_file_format(outside_file)

            assert "security violation" in str(exc_info.value)
        finally:
            # Cleanup
            if os.path.exists(outside_file):
                os.remove(outside_file)

    @pytest.mark.asyncio
    async def test_validate_file_format_valid_csv(self, file_service, temp_dir):
        """Test validation of valid CSV file."""
        file_path = os.path.join(temp_dir, "test.csv")

        with open(file_path, 'w') as f:
            f.write("C001,50,kg")

        # Should not raise exception
        file_service._validate_file_format(file_path)

    @pytest.mark.asyncio
    async def test_validate_file_format_valid_json(self, file_service, temp_dir):
        """Test validation of valid JSON file."""
        file_path = os.path.join(temp_dir, "test.json")

        with open(file_path, 'w') as f:
            f.write('[]')

        # Should not raise exception
        file_service._validate_file_format(file_path)

    # ========================================================================
    # Test Container Data Validation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_invalid_id_empty(self, file_service):
        """Test validation of empty container ID."""
        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_csv_container_data("", 50, "kg")

        assert "Invalid container ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_invalid_id_too_long(self, file_service):
        """Test validation of container ID that is too long."""
        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_csv_container_data("C" * 16, 50, "kg")

        assert "Invalid container ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_invalid_characters(self, file_service):
        """Test validation of container ID with invalid characters."""
        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_csv_container_data("C@01!", 50, "kg")

        assert "invalid characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_negative_weight(self, file_service):
        """Test validation of negative weight."""
        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_csv_container_data("C001", -50, "kg")

        assert "must be positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_zero_weight(self, file_service):
        """Test validation of zero weight."""
        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_csv_container_data("C001", 0, "kg")

        assert "must be positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_out_of_range(self, file_service):
        """Test validation of weight out of valid range."""
        with pytest.raises(FileValidationError) as exc_info:
            file_service._validate_csv_container_data("C001", 999999, "kg")

        assert "out of valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_csv_container_data_valid(self, file_service):
        """Test validation of valid container data."""
        # Should not raise exception
        file_service._validate_csv_container_data("C001", 50, "kg")
        file_service._validate_csv_container_data("C-001", 100, "lbs")
        file_service._validate_csv_container_data("C_001", 75, "kg")

    @pytest.mark.asyncio
    async def test_validate_json_container_data_delegates_to_csv(self, file_service):
        """Test that JSON validation delegates to CSV validation."""
        # Should behave the same as CSV validation
        with pytest.raises(FileValidationError):
            file_service._validate_json_container_data("", 50, "kg")

    # ========================================================================
    # Test Batch Processing
    # ========================================================================

    @pytest.mark.asyncio
    async def test_process_batch_file_csv_success(self, file_service, temp_dir):
        """Test successful processing of CSV file."""
        csv_content = "C001,50,kg\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Mock batch registration
        file_service.container_service.batch_register_containers.return_value = {
            "processed": 2,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }

        result = await file_service.process_batch_file("test.csv")

        assert result.processed_count == 2
        assert result.skipped_count == 0
        assert len(result.errors) == 0
        assert "Successfully processed 2 containers" in result.message

    @pytest.mark.asyncio
    async def test_process_batch_file_json_success(self, file_service, temp_dir):
        """Test successful processing of JSON file."""
        json_data = [
            {"id": "C001", "weight": 50, "unit": "kg"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        # Mock batch registration
        file_service.container_service.batch_register_containers.return_value = {
            "processed": 2,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }

        result = await file_service.process_batch_file("test.json")

        assert result.processed_count == 2
        assert result.skipped_count == 0

    @pytest.mark.asyncio
    async def test_process_batch_file_with_updates(self, file_service, temp_dir):
        """Test processing with updates."""
        csv_content = "C001,50,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Mock batch registration with updates
        file_service.container_service.batch_register_containers.return_value = {
            "processed": 0,
            "updated": 1,
            "skipped": 0,
            "errors": []
        }

        result = await file_service.process_batch_file("test.csv", allow_updates=True)

        assert result.processed_count == 1

    @pytest.mark.asyncio
    async def test_process_batch_file_with_skipped(self, file_service, temp_dir):
        """Test processing with skipped duplicates."""
        csv_content = "C001,50,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Mock batch registration with skipped
        file_service.container_service.batch_register_containers.return_value = {
            "processed": 1,
            "updated": 0,
            "skipped": 1,
            "errors": []
        }

        result = await file_service.process_batch_file("test.csv", skip_duplicates=True)

        assert result.skipped_count == 1
        assert "skipped 1 duplicates" in result.message

    @pytest.mark.asyncio
    async def test_process_batch_file_with_errors(self, file_service, temp_dir):
        """Test processing with errors."""
        csv_content = "C001,50,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Mock batch registration with errors
        file_service.container_service.batch_register_containers.return_value = {
            "processed": 1,
            "updated": 0,
            "skipped": 0,
            "errors": ["Error 1", "Error 2"]
        }

        result = await file_service.process_batch_file("test.csv")

        assert len(result.errors) == 2
        assert "with 2 errors" in result.message

    @pytest.mark.asyncio
    async def test_process_batch_file_unsupported_format(self, file_service, temp_dir):
        """Test processing of unsupported file format."""
        txt_path = os.path.join(temp_dir, "test.txt")

        with open(txt_path, 'w') as f:
            f.write("test")

        # File validation happens first and rejects invalid extension
        with pytest.raises(FileValidationError) as exc_info:
            await file_service.process_batch_file("test.txt")

        assert "Invalid file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_batch_file_validation_error(self, file_service, temp_dir):
        """Test processing when file validation fails."""
        with pytest.raises(FileValidationError):
            await file_service.process_batch_file("nonexistent.csv")

    @pytest.mark.asyncio
    async def test_process_batch_file_exception_handling(self, file_service, temp_dir):
        """Test generic exception handling during batch processing."""
        csv_path = os.path.join(temp_dir, "test.csv")
        with open(csv_path, 'w') as f:
            f.write("C001,50,kg")

        # Mock batch_register_containers to raise an exception
        file_service.container_service.batch_register_containers.side_effect = Exception("Database error")

        with pytest.raises(FileProcessingError) as exc_info:
            await file_service.process_batch_file("test.csv")

        assert "Failed to process file" in str(exc_info.value)
        assert "Database error" in str(exc_info.value)

    # ========================================================================
    # Test Format Message
    # ========================================================================

    @pytest.mark.asyncio
    async def test_format_batch_message_success(self, file_service):
        """Test formatting success message."""
        results = {"processed": 5, "updated": 0, "skipped": 0, "errors": []}
        message = file_service._format_batch_message(results)
        assert message == "Successfully processed 5 containers"

    @pytest.mark.asyncio
    async def test_format_batch_message_with_skipped(self, file_service):
        """Test formatting message with skipped containers."""
        results = {"processed": 5, "updated": 0, "skipped": 3, "errors": []}
        message = file_service._format_batch_message(results)
        assert message == "Processed 5 containers, skipped 3 duplicates"

    @pytest.mark.asyncio
    async def test_format_batch_message_with_errors(self, file_service):
        """Test formatting message with errors."""
        results = {"processed": 5, "updated": 0, "skipped": 0, "errors": ["Error 1", "Error 2"]}
        message = file_service._format_batch_message(results)
        assert message == "Processed 5 containers with 2 errors"

    # ========================================================================
    # Test Validate File Content
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_file_content_valid_csv(self, file_service, temp_dir):
        """Test content validation of valid CSV file."""
        csv_content = "C001,50,kg\nC002,60,kg"
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service.validate_file_content("test.csv")

        assert result["valid"] is True
        assert result["container_count"] == 2
        assert len(result["containers"]) == 2

    @pytest.mark.asyncio
    async def test_validate_file_content_valid_json(self, file_service, temp_dir):
        """Test content validation of valid JSON file."""
        json_data = [
            {"id": "C001", "weight": 50, "unit": "kg"},
            {"id": "C002", "weight": 60, "unit": "kg"}
        ]
        json_path = os.path.join(temp_dir, "test.json")

        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        result = await file_service.validate_file_content("test.json")

        assert result["valid"] is True
        assert result["container_count"] == 2

    @pytest.mark.asyncio
    async def test_validate_file_content_preview_limit(self, file_service, temp_dir):
        """Test that content validation previews only first 10 containers."""
        # Create 15 containers
        csv_content = "\n".join([f"C{i:03d},50,kg" for i in range(15)])
        csv_path = os.path.join(temp_dir, "test.csv")

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        result = await file_service.validate_file_content("test.csv")

        assert result["valid"] is True
        assert result["container_count"] == 15
        assert len(result["containers"]) == 10  # Preview limit

    @pytest.mark.asyncio
    async def test_validate_file_content_unsupported_format(self, file_service, temp_dir):
        """Test content validation of unsupported format."""
        # Create the file first so validation checks the format
        txt_path = os.path.join(temp_dir, "test.txt")
        with open(txt_path, 'w') as f:
            f.write("test")

        result = await file_service.validate_file_content("test.txt")

        assert result["valid"] is False
        assert "error" in result
        assert result["container_count"] == 0

    @pytest.mark.asyncio
    async def test_validate_file_content_error(self, file_service):
        """Test content validation with error."""
        result = await file_service.validate_file_content("nonexistent.csv")

        assert result["valid"] is False
        assert "error" in result
        assert result["container_count"] == 0

    # ========================================================================
    # Test Get Supported Formats
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_supported_formats(self, file_service):
        """Test getting supported formats information."""
        result = await file_service.get_supported_formats()

        assert "csv" in result
        assert "json" in result
        assert "limits" in result
        assert result["limits"]["max_file_size"] == "10MB"
        assert "kg" in result["limits"]["supported_units"]
        assert "lbs" in result["limits"]["supported_units"]

    # ========================================================================
    # Test Cleanup
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cleanup_uploaded_file_success(self, file_service, temp_dir):
        """Test successful file cleanup."""
        file_path = os.path.join(temp_dir, "test.csv")

        with open(file_path, 'w') as f:
            f.write("test")

        result = file_service.cleanup_uploaded_file("test.csv")

        assert result is True
        assert not os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_cleanup_uploaded_file_not_found(self, file_service):
        """Test cleanup of non-existent file."""
        result = file_service.cleanup_uploaded_file("nonexistent.csv")

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_uploaded_file_error(self, file_service, temp_dir):
        """Test cleanup with permission error."""
        file_path = os.path.join(temp_dir, "test.csv")

        with open(file_path, 'w') as f:
            f.write("test")

        # Mock os.remove to raise exception
        with patch('os.remove', side_effect=Exception("Permission denied")):
            result = file_service.cleanup_uploaded_file("test.csv")
            assert result is False
