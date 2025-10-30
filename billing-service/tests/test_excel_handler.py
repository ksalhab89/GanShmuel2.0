"""Tests for Excel file handling utilities."""

from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from fastapi import UploadFile

from src.models.database import Rate
from src.utils.excel_handler import (
    create_rates_excel,
    read_rates_from_excel,
    read_rates_from_file,
)
from src.utils.exceptions import FileError


class TestReadRatesFromExcel:
    """Test reading rates from Excel file in upload directory."""

    @patch("src.utils.excel_handler.os.path.exists")
    @patch("src.utils.excel_handler.pd.read_excel")
    def test_read_rates_valid_file(self, mock_read_excel, mock_exists):
        """Test reading valid Excel file with correct format."""
        mock_exists.return_value = True

        # Create sample DataFrame
        mock_df = pd.DataFrame(
            {
                "Product": ["apples", "oranges", "grapes"],
                "Rate": [100, 150, 200],
                "Scope": ["general", "general", "provider_1"],
            }
        )
        mock_read_excel.return_value = mock_df

        rates = read_rates_from_excel("test_rates.xlsx")

        assert len(rates) == 3
        assert rates[0].product_id == "apples"
        assert rates[0].rate == 100
        assert rates[0].scope == "general"
        assert rates[2].scope == "provider_1"

    @patch("src.utils.excel_handler.os.path.exists")
    def test_read_rates_file_not_found(self, mock_exists):
        """Test error when file doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(FileError) as exc_info:
            read_rates_from_excel("nonexistent.xlsx")

        assert "not found" in str(exc_info.value).lower()

    @patch("src.utils.excel_handler.os.path.exists")
    def test_read_rates_invalid_extension(self, mock_exists):
        """Test error for non-Excel file extension."""
        mock_exists.return_value = True

        with pytest.raises(FileError) as exc_info:
            read_rates_from_excel("rates.csv")

        assert "excel format" in str(exc_info.value).lower()

    @patch("src.utils.excel_handler.os.path.exists")
    @patch("src.utils.excel_handler.pd.read_excel")
    def test_read_rates_missing_columns(self, mock_read_excel, mock_exists):
        """Test error when required columns are missing."""
        mock_exists.return_value = True

        # Create DataFrame missing 'Rate' column
        mock_df = pd.DataFrame({"Product": ["apples"], "Scope": ["general"]})
        mock_read_excel.return_value = mock_df

        with pytest.raises(FileError) as exc_info:
            read_rates_from_excel("test_rates.xlsx")

        assert "columns" in str(exc_info.value).lower()

    @patch("src.utils.excel_handler.os.path.exists")
    @patch("src.utils.excel_handler.pd.read_excel")
    def test_read_rates_empty_file(self, mock_read_excel, mock_exists):
        """Test error when Excel file is empty."""
        mock_exists.return_value = True
        mock_read_excel.side_effect = pd.errors.EmptyDataError()

        with pytest.raises(FileError) as exc_info:
            read_rates_from_excel("empty.xlsx")

        assert "empty" in str(exc_info.value).lower()

    @patch("src.utils.excel_handler.os.path.exists")
    @patch("src.utils.excel_handler.pd.read_excel")
    def test_read_rates_parser_error(self, mock_read_excel, mock_exists):
        """Test error when Excel parsing fails."""
        mock_exists.return_value = True
        mock_read_excel.side_effect = pd.errors.ParserError("Invalid Excel")

        with pytest.raises(FileError) as exc_info:
            read_rates_from_excel("corrupt.xlsx")

        assert "parsing" in str(exc_info.value).lower()

    @patch("src.utils.excel_handler.os.path.exists")
    @patch("src.utils.excel_handler.pd.read_excel")
    def test_read_rates_with_whitespace(self, mock_read_excel, mock_exists):
        """Test trimming whitespace from product and scope."""
        mock_exists.return_value = True

        mock_df = pd.DataFrame(
            {
                "Product": ["  apples  ", " oranges"],
                "Rate": [100, 150],
                "Scope": ["general  ", "  provider_1"],
            }
        )
        mock_read_excel.return_value = mock_df

        rates = read_rates_from_excel("test_rates.xlsx")

        assert rates[0].product_id == "apples"
        assert rates[0].scope == "general"
        assert rates[1].product_id == "oranges"
        assert rates[1].scope == "provider_1"

    @patch("src.utils.excel_handler.os.path.exists")
    @patch("src.utils.excel_handler.pd.read_excel")
    def test_read_rates_large_file(self, mock_read_excel, mock_exists):
        """Test reading large Excel file with many rows."""
        mock_exists.return_value = True

        # Create large DataFrame
        products = [f"product_{i}" for i in range(100)]
        rates_list = [100 + i for i in range(100)]
        scopes = ["general" if i % 2 == 0 else "provider_1" for i in range(100)]

        mock_df = pd.DataFrame(
            {"Product": products, "Rate": rates_list, "Scope": scopes}
        )
        mock_read_excel.return_value = mock_df

        rates = read_rates_from_excel("large_rates.xlsx")

        assert len(rates) == 100
        assert rates[0].product_id == "product_0"
        assert rates[99].rate == 199


class TestReadRatesFromFile:
    """Test reading rates from uploaded file."""

    @pytest.mark.asyncio
    async def test_read_from_upload_file_valid(self):
        """Test reading valid uploaded Excel file."""
        # Create Excel file in memory
        df = pd.DataFrame(
            {
                "Product": ["apples", "oranges"],
                "Rate": [100, 150],
                "Scope": ["general", "general"],
            }
        )

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)

        # Create mock UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.xlsx"
        mock_file.read = AsyncMock(return_value=excel_buffer.read())

        rates = await read_rates_from_file(mock_file)

        assert len(rates) == 2
        assert rates[0].product_id == "apples"
        assert rates[1].rate == 150

    @pytest.mark.asyncio
    async def test_read_from_upload_file_invalid_extension(self):
        """Test error for non-Excel file extension."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.txt"
        mock_file.read = AsyncMock(return_value=b"")

        with pytest.raises(FileError) as exc_info:
            await read_rates_from_file(mock_file)

        assert "excel format" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_read_from_upload_file_missing_columns(self):
        """Test error when columns are missing."""
        # Create Excel with missing columns
        df = pd.DataFrame(
            {
                "Product": ["apples"],
                "Rate": [100],
                # Missing 'Scope' column
            }
        )

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.xlsx"
        mock_file.read = AsyncMock(return_value=excel_buffer.read())

        with pytest.raises(FileError) as exc_info:
            await read_rates_from_file(mock_file)

        assert "columns" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_read_from_upload_file_with_valid_data(self):
        """Test handling of valid Excel data with multiple products."""
        # Create Excel with valid data
        df = pd.DataFrame(
            {
                "Product": ["apples", "bananas", "oranges"],
                "Rate": [100, 150, 200],
                "Scope": ["general", "general", "provider_1"],
            }
        )

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.xlsx"
        mock_file.read = AsyncMock(return_value=excel_buffer.read())

        rates = await read_rates_from_file(mock_file)

        # Should read all valid rows
        assert len(rates) == 3
        assert rates[0].product_id == "apples"
        assert rates[1].product_id == "bananas"
        assert rates[2].product_id == "oranges"

    @pytest.mark.asyncio
    async def test_read_from_upload_file_float_rates(self):
        """Test handling of float rate values (should convert to int)."""
        df = pd.DataFrame(
            {
                "Product": ["apples", "oranges"],
                "Rate": [100.5, 150.9],
                "Scope": ["general", "general"],
            }
        )

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.xlsx"
        mock_file.read = AsyncMock(return_value=excel_buffer.read())

        rates = await read_rates_from_file(mock_file)

        assert rates[0].rate == 100
        assert rates[1].rate == 150

    @pytest.mark.asyncio
    async def test_read_from_upload_file_invalid_data_type(self):
        """Test error when rate is not numeric."""
        df = pd.DataFrame(
            {"Product": ["apples"], "Rate": ["invalid"], "Scope": ["general"]}
        )

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.xlsx"
        mock_file.read = AsyncMock(return_value=excel_buffer.read())

        with pytest.raises(FileError) as exc_info:
            await read_rates_from_file(mock_file)

        assert "invalid data" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_read_from_upload_file_xls_extension(self):
        """Test reading .xls file (older Excel format)."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "rates.xls"

        # Create minimal Excel content
        df = pd.DataFrame({"Product": ["apples"], "Rate": [100], "Scope": ["general"]})
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)

        mock_file.read = AsyncMock(return_value=excel_buffer.read())

        rates = await read_rates_from_file(mock_file)

        assert len(rates) == 1


class TestCreateRatesExcel:
    """Test creating Excel file from rates."""

    def test_create_excel_from_rates(self):
        """Test creating Excel file from rate objects."""
        rates = [
            Rate(product_id="apples", rate=100, scope="general"),
            Rate(product_id="oranges", rate=150, scope="general"),
            Rate(product_id="grapes", rate=200, scope="provider_1"),
        ]

        excel_data = create_rates_excel(rates)

        assert isinstance(excel_data, BytesIO)
        assert excel_data.tell() == 0  # Should be at beginning

        # Verify content by reading back
        df = pd.read_excel(excel_data)
        assert len(df) == 3
        assert list(df.columns) == ["Product", "Rate", "Scope"]
        assert df.iloc[0]["Product"] == "apples"
        assert df.iloc[0]["Rate"] == 100
        assert df.iloc[2]["Scope"] == "provider_1"

    def test_create_excel_empty_rates(self):
        """Test creating Excel from empty rates list."""
        rates = []

        excel_data = create_rates_excel(rates)

        assert isinstance(excel_data, BytesIO)
        df = pd.read_excel(excel_data)
        assert len(df) == 0

    def test_create_excel_single_rate(self):
        """Test creating Excel from single rate."""
        rates = [Rate(product_id="apples", rate=100, scope="general")]

        excel_data = create_rates_excel(rates)

        df = pd.read_excel(excel_data)
        assert len(df) == 1
        assert df.iloc[0]["Product"] == "apples"

    def test_create_excel_large_dataset(self):
        """Test creating Excel from large number of rates."""
        rates = [
            Rate(product_id=f"product_{i}", rate=100 + i, scope="general")
            for i in range(100)
        ]

        excel_data = create_rates_excel(rates)

        df = pd.read_excel(excel_data)
        assert len(df) == 100
        assert df.iloc[0]["Product"] == "product_0"
        assert df.iloc[99]["Rate"] == 199

    def test_create_excel_special_characters(self):
        """Test creating Excel with special characters in data."""
        rates = [
            Rate(product_id="apples & oranges", rate=100, scope="provider_1"),
            Rate(product_id="grapes (red)", rate=150, scope="general"),
        ]

        excel_data = create_rates_excel(rates)

        df = pd.read_excel(excel_data)
        assert df.iloc[0]["Product"] == "apples & oranges"
        assert df.iloc[1]["Product"] == "grapes (red)"

    def test_create_excel_readability(self):
        """Test that created Excel can be read back correctly."""
        original_rates = [
            Rate(product_id="apples", rate=100, scope="general"),
            Rate(product_id="oranges", rate=150, scope="provider_1"),
        ]

        # Create Excel
        excel_data = create_rates_excel(original_rates)

        # Read back
        df = pd.read_excel(excel_data)

        # Verify all data is intact
        assert len(df) == 2
        assert df.iloc[0]["Product"] == original_rates[0].product_id
        assert df.iloc[0]["Rate"] == original_rates[0].rate
        assert df.iloc[0]["Scope"] == original_rates[0].scope
        assert df.iloc[1]["Product"] == original_rates[1].product_id

    def test_create_excel_sheet_name(self):
        """Test that Excel has correct sheet name."""
        rates = [Rate(product_id="apples", rate=100, scope="general")]

        excel_data = create_rates_excel(rates)

        # Read with sheet name
        df = pd.read_excel(excel_data, sheet_name="Rates")
        assert len(df) == 1
