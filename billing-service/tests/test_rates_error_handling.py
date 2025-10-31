"""Tests for rates API error handling and exception paths."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.utils.exceptions import FileError


class TestRatesAPIErrorHandling:
    """Test error handling in rates endpoints."""

    @pytest.mark.asyncio
    async def test_upload_rates_generic_exception(
        self, test_client: AsyncClient, mock_upload_file
    ):
        """Test that generic exceptions in upload_rates return 500."""
        # Mock the read_rates_from_file to raise a generic exception
        with patch(
            "src.routers.rates.read_rates_from_file",
            side_effect=Exception("Database error"),
        ):
            response = await test_client.post(
                "/rates",
                files={
                    "file": (
                        "rates.xlsx",
                        b"fake content",
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_rates_from_directory_generic_exception(self, test_client: AsyncClient):
        """Test that generic exceptions in upload_rates_from_directory return 500."""
        # Mock read_rates_from_excel to raise a generic exception
        with patch("src.routers.rates.read_rates_from_excel", side_effect=Exception("Database error")):
            response = await test_client.post(
                "/rates/from-directory",
                json={"file": "rates.xlsx"}
            )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_rates_from_directory_file_error(self, test_client: AsyncClient):
        """Test that FileError in upload_rates_from_directory returns 400."""
        # Mock read_rates_from_excel to raise FileError
        with patch("src.routers.rates.read_rates_from_excel", side_effect=FileError("File not found")):
            response = await test_client.post(
                "/rates/from-directory",
                json={"file": "nonexistent.xlsx"}
            )

        assert response.status_code == 400
        assert "File not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_rates_generic_exception(self, test_client: AsyncClient, clean_database):
        """Test that generic exceptions in get_rates return 500."""
        # Mock rate_repo.get_all to raise a generic exception
        with patch("src.routers.rates.rate_repo.get_all", side_effect=Exception("Database error")):
            response = await test_client.get("/rates?format=json")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_rates_excel_generic_exception(self, test_client: AsyncClient, clean_database):
        """Test that generic exceptions in get_rates with Excel format return 500."""
        # Mock rate_repo.get_all to raise exception
        with patch("src.routers.rates.rate_repo.get_all", side_effect=Exception("Database error")):
            response = await test_client.get("/rates?format=excel")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_rates_from_directory_success(self, test_client: AsyncClient, clean_database):
        """Test successful upload from directory (covers lines 67-71)."""
        from src.models.schemas import Rate

        # Mock read_rates_from_excel to return test rates
        test_rates = [
            Rate(product_id="Apples", rate=150, scope="ALL"),
            Rate(product_id="Oranges", rate=200, scope="ALL"),
        ]
        with patch("src.routers.rates.read_rates_from_excel", return_value=test_rates):
            response = await test_client.post(
                "/rates/from-directory",
                json={"file": "rates.xlsx"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "Successfully uploaded 2 rates" in data["message"]
