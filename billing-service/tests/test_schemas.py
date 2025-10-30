"""Tests for Pydantic schemas and validation."""

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    BillResponse,
    ErrorResponse,
    HealthResponse,
    ProductSummary,
    ProviderCreate,
    ProviderResponse,
    ProviderUpdate,
    Rate,
    RateUpload,
    RateUploadResponse,
    TruckCreate,
    TruckDetails,
    TruckResponse,
    TruckUpdate,
)


class TestErrorResponse:
    """Test ErrorResponse schema."""

    def test_valid_error_response(self):
        """Test valid error response."""
        error = ErrorResponse(error="Not found")
        assert error.error == "Not found"
        assert error.detail is None

    def test_error_response_with_detail(self):
        """Test error response with detail."""
        error = ErrorResponse(error="Validation failed", detail="Missing field: name")
        assert error.error == "Validation failed"
        assert error.detail == "Missing field: name"

    def test_error_response_serialization(self):
        """Test error response serialization."""
        error = ErrorResponse(error="Error", detail="Details")
        data = error.model_dump()
        assert data == {"error": "Error", "detail": "Details"}


class TestHealthResponse:
    """Test HealthResponse schema."""

    def test_valid_health_response(self):
        """Test valid health response."""
        health = HealthResponse(status="healthy", service="billing", version="1.0.0")
        assert health.status == "healthy"
        assert health.service == "billing"
        assert health.version == "1.0.0"

    def test_health_response_serialization(self):
        """Test health response serialization."""
        health = HealthResponse(status="healthy", service="billing", version="1.0.0")
        data = health.model_dump()
        assert data["status"] == "healthy"


class TestProviderSchemas:
    """Test Provider-related schemas."""

    def test_provider_create_valid(self):
        """Test valid provider creation."""
        provider = ProviderCreate(name="Test Provider")
        assert provider.name == "Test Provider"

    def test_provider_create_empty_name(self):
        """Test provider with empty name fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderCreate(name="")

        errors = exc_info.value.errors()
        assert any("min_length" in str(error) for error in errors)

    def test_provider_create_long_name(self):
        """Test provider with name exceeding max length."""
        long_name = "A" * 256
        with pytest.raises(ValidationError) as exc_info:
            ProviderCreate(name=long_name)

        errors = exc_info.value.errors()
        assert any("max_length" in str(error) for error in errors)

    def test_provider_create_max_valid_length(self):
        """Test provider with maximum valid name length."""
        max_name = "A" * 255
        provider = ProviderCreate(name=max_name)
        assert provider.name == max_name

    def test_provider_update_valid(self):
        """Test valid provider update."""
        provider = ProviderUpdate(name="Updated Provider")
        assert provider.name == "Updated Provider"

    def test_provider_update_empty_name(self):
        """Test provider update with empty name fails."""
        with pytest.raises(ValidationError):
            ProviderUpdate(name="")

    def test_provider_response_valid(self):
        """Test valid provider response."""
        provider = ProviderResponse(id=1, name="Test Provider")
        assert provider.id == 1
        assert provider.name == "Test Provider"

    def test_provider_response_serialization(self):
        """Test provider response serialization."""
        provider = ProviderResponse(id=1, name="Test Provider")
        data = provider.model_dump()
        assert data == {"id": 1, "name": "Test Provider"}


class TestRateSchemas:
    """Test Rate-related schemas."""

    def test_rate_upload_valid(self):
        """Test valid rate upload request."""
        upload = RateUpload(file="rates.xlsx")
        assert upload.file == "rates.xlsx"

    def test_rate_upload_response_valid(self):
        """Test valid rate upload response."""
        response = RateUploadResponse(message="Successfully uploaded")
        assert response.message == "Successfully uploaded"

    def test_rate_valid(self):
        """Test valid rate schema."""
        rate = Rate(product_id="apples", rate=100, scope="general")
        assert rate.product_id == "apples"
        assert rate.rate == 100
        assert rate.scope == "general"

    def test_rate_serialization(self):
        """Test rate serialization."""
        rate = Rate(product_id="oranges", rate=150, scope="provider_1")
        data = rate.model_dump()
        assert data == {"product_id": "oranges", "rate": 150, "scope": "provider_1"}

    def test_rate_with_special_characters(self):
        """Test rate with special characters in product_id."""
        rate = Rate(product_id="apples & oranges", rate=100, scope="general")
        assert rate.product_id == "apples & oranges"


class TestTruckSchemas:
    """Test Truck-related schemas."""

    def test_truck_create_valid(self):
        """Test valid truck creation."""
        truck = TruckCreate(id="ABC123", provider_id=1)
        assert truck.id == "ABC123"
        assert truck.provider_id == 1

    def test_truck_create_max_length(self):
        """Test truck ID with maximum length."""
        truck = TruckCreate(id="1234567890", provider_id=1)
        assert truck.id == "1234567890"

    def test_truck_create_exceeds_max_length(self):
        """Test truck ID exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            TruckCreate(id="12345678901", provider_id=1)

        errors = exc_info.value.errors()
        assert any("max_length" in str(error) for error in errors)

    def test_truck_update_valid(self):
        """Test valid truck update."""
        truck = TruckUpdate(provider_id=2)
        assert truck.provider_id == 2

    def test_truck_response_valid(self):
        """Test valid truck response."""
        truck = TruckResponse(id="ABC123", provider_id=1)
        assert truck.id == "ABC123"
        assert truck.provider_id == 1

    def test_truck_details_with_integer_tara(self):
        """Test truck details with integer tara."""
        truck = TruckDetails(id="ABC123", tara=5000, sessions=["session1", "session2"])
        assert truck.id == "ABC123"
        assert truck.tara == 5000
        assert len(truck.sessions) == 2

    def test_truck_details_with_na_tara(self):
        """Test truck details with 'na' tara."""
        truck = TruckDetails(id="ABC123", tara="na", sessions=[])
        assert truck.tara == "na"
        assert truck.sessions == []

    def test_truck_details_serialization(self):
        """Test truck details serialization."""
        truck = TruckDetails(id="ABC123", tara=5000, sessions=["s1"])
        data = truck.model_dump()
        assert data["id"] == "ABC123"
        assert data["tara"] == 5000
        assert data["sessions"] == ["s1"]


class TestProductSummary:
    """Test ProductSummary schema."""

    def test_product_summary_valid(self):
        """Test valid product summary."""
        summary = ProductSummary(
            product="apples", count="5", amount=1000, rate=100, pay=100000
        )
        assert summary.product == "apples"
        assert summary.count == "5"
        assert summary.amount == 1000
        assert summary.rate == 100
        assert summary.pay == 100000

    def test_product_summary_count_as_string(self):
        """Test product summary count is string."""
        summary = ProductSummary(
            product="oranges", count="10", amount=2000, rate=150, pay=300000
        )
        assert isinstance(summary.count, str)
        assert summary.count == "10"

    def test_product_summary_serialization(self):
        """Test product summary serialization."""
        summary = ProductSummary(
            product="grapes", count="3", amount=500, rate=200, pay=100000
        )
        data = summary.model_dump()
        assert data["product"] == "grapes"
        assert data["count"] == "3"
        assert data["amount"] == 500


class TestBillResponse:
    """Test BillResponse schema."""

    def test_bill_response_valid(self):
        """Test valid bill response."""
        products = [
            ProductSummary(
                product="apples", count="5", amount=1000, rate=100, pay=100000
            )
        ]

        bill = BillResponse(
            id="1",
            name="Test Provider",
            from_="20240101000000",
            to="20240131235959",
            truckCount=3,
            sessionCount=10,
            products=products,
            total=100000,
        )

        assert bill.id == "1"
        assert bill.name == "Test Provider"
        assert bill.from_ == "20240101000000"
        assert bill.to == "20240131235959"
        assert bill.truckCount == 3
        assert bill.sessionCount == 10
        assert len(bill.products) == 1
        assert bill.total == 100000

    def test_bill_response_field_alias(self):
        """Test bill response 'from' field alias."""
        bill = BillResponse(
            id="1",
            name="Provider",
            from_="20240101000000",
            to="20240131235959",
            truckCount=1,
            sessionCount=1,
            products=[],
            total=0,
        )

        # Test that alias works in serialization
        data = bill.model_dump(by_alias=True)
        assert "from" in data
        assert data["from"] == "20240101000000"

    def test_bill_response_multiple_products(self):
        """Test bill response with multiple products."""
        products = [
            ProductSummary(
                product="apples", count="5", amount=1000, rate=100, pay=100000
            ),
            ProductSummary(
                product="oranges", count="3", amount=600, rate=150, pay=90000
            ),
            ProductSummary(
                product="grapes", count="2", amount=400, rate=200, pay=80000
            ),
        ]

        bill = BillResponse(
            id="1",
            name="Provider",
            from_="20240101000000",
            to="20240131235959",
            truckCount=5,
            sessionCount=15,
            products=products,
            total=270000,
        )

        assert len(bill.products) == 3
        assert bill.total == 270000

    def test_bill_response_empty_products(self):
        """Test bill response with no products."""
        bill = BillResponse(
            id="1",
            name="Provider",
            from_="20240101000000",
            to="20240131235959",
            truckCount=0,
            sessionCount=0,
            products=[],
            total=0,
        )

        assert len(bill.products) == 0
        assert bill.total == 0

    def test_bill_response_serialization_complete(self):
        """Test complete bill response serialization."""
        products = [
            ProductSummary(
                product="apples", count="5", amount=1000, rate=100, pay=100000
            )
        ]

        bill = BillResponse(
            id="1",
            name="Test Provider",
            from_="20240101000000",
            to="20240131235959",
            truckCount=3,
            sessionCount=10,
            products=products,
            total=100000,
        )

        data = bill.model_dump(by_alias=True)

        assert data["id"] == "1"
        assert data["name"] == "Test Provider"
        assert data["from"] == "20240101000000"
        assert data["to"] == "20240131235959"
        assert data["truckCount"] == 3
        assert data["sessionCount"] == 10
        assert len(data["products"]) == 1
        assert data["total"] == 100000

    def test_bill_response_json_serialization(self):
        """Test bill response JSON serialization."""
        products = [
            ProductSummary(product="apples", count="2", amount=500, rate=100, pay=50000)
        ]

        bill = BillResponse(
            id="2",
            name="Provider Two",
            from_="20240201000000",
            to="20240229235959",
            truckCount=2,
            sessionCount=5,
            products=products,
            total=50000,
        )

        json_str = bill.model_dump_json(by_alias=True)
        assert isinstance(json_str, str)
        assert "Provider Two" in json_str
        assert "from" in json_str
