"""Tests for bill service core business logic - CRITICAL for financial calculations."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.bill_service import BillService
from src.models.database import Provider, Truck, Rate
from src.utils.exceptions import NotFoundError


class TestBillServiceCalculations:
    """Test core billing calculation logic."""

    @pytest.mark.asyncio
    async def test_calculate_bill_with_provider_specific_rate(
        self, mock_weight_service, sample_provider, sample_truck, sample_provider_rate
    ):
        """
        CRITICAL: Verify bill = neto × provider_rate when provider rate exists.
        Provider rate MUST override general rate.
        """
        # Setup mock data
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": 1500, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_provider_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Provider rate is 6, total neto is 2500kg
        # Expected: 2500 × 6 = 15000
        assert bill.total == 15000, "Provider rate should be used for calculation"
        assert bill.id == str(sample_provider.id)
        assert len(bill.products) == 1
        assert bill.products[0].product == "apples"
        assert bill.products[0].amount == 2500
        assert bill.products[0].rate == 6
        assert bill.products[0].pay == 15000

    @pytest.mark.asyncio
    async def test_calculate_bill_with_general_rate(
        self, mock_weight_service, sample_provider, sample_truck, sample_rate
    ):
        """
        CRITICAL: Verify bill uses general rate when no provider-specific rate exists.
        """
        # Setup mock data
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 2000, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # General rate is 5, total neto is 2000kg
        # Expected: 2000 × 5 = 10000
        assert bill.total == 10000, "General rate should be used when no provider rate"
        assert bill.products[0].rate == 5

    @pytest.mark.asyncio
    async def test_rate_precedence_provider_over_general(
        self, sample_provider, sample_rate, sample_provider_rate
    ):
        """
        CRITICAL: Verify provider rate takes precedence over general rate.
        This is a core business rule for billing.
        """
        service = BillService()

        # Both rates exist
        all_rates = [sample_rate, sample_provider_rate]

        # Find applicable rate
        rate = service._find_applicable_rate(all_rates, "apples", sample_provider.id)

        assert rate is not None, "Rate should be found"
        assert rate.rate == 6, "Provider rate (6) should override general rate (5)"
        assert rate.scope == str(sample_provider.id)

    @pytest.mark.asyncio
    async def test_calculate_bill_multiple_products(
        self, mock_weight_service, sample_provider, sample_truck, multiple_rates
    ):
        """
        Test bill calculation with multiple products.
        Each product should have separate totals.
        """
        # Setup mock data with multiple products
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": 1500, "produce": "apples"},
            {"truck": "ABC123", "neto": 2000, "produce": "oranges"},
            {"truck": "ABC123", "neto": 1000, "produce": "oranges"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=multiple_rates)

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Verify we have 2 products
        assert len(bill.products) == 2

        # Find apples and oranges in products
        apples = next(p for p in bill.products if p.product == "apples")
        oranges = next(p for p in bill.products if p.product == "oranges")

        # Apples: 2500kg × 6 (provider rate) = 15000
        assert apples.amount == 2500
        assert apples.rate == 6
        assert apples.pay == 15000

        # Oranges: 3000kg × 5 (provider rate) = 15000
        assert oranges.amount == 3000
        assert oranges.rate == 5
        assert oranges.pay == 15000

        # Total: 30000
        assert bill.total == 30000

    @pytest.mark.asyncio
    async def test_calculate_bill_multiple_trucks(
        self, mock_weight_service, sample_provider, sample_truck, sample_truck_2, sample_rate
    ):
        """
        Test bill calculation for provider with multiple trucks.
        All trucks should be included in the bill.
        """
        # Setup mock data for multiple trucks
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "XYZ789", "neto": 2000, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(
            return_value=[sample_truck, sample_truck_2]
        )
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Both trucks should be counted
        assert bill.truckCount == 2
        assert bill.sessionCount == 2
        # Total: 3000kg × 5 = 15000
        assert bill.total == 15000

    @pytest.mark.asyncio
    async def test_calculate_bill_filters_other_provider_trucks(
        self, mock_weight_service, sample_provider, sample_provider_2, sample_truck, sample_rate
    ):
        """
        CRITICAL: Verify bill only includes transactions for provider's own trucks.
        Must not include other providers' transactions.
        """
        # Create truck for another provider
        other_truck = Truck(id="OTHER123", provider_id=sample_provider_2.id)

        # Setup mock data with both providers' trucks
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},  # Our provider
            {"truck": "OTHER123", "neto": 5000, "produce": "apples"},  # Other provider
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should only include our provider's truck
        assert bill.sessionCount == 1
        # Total: 1000kg × 5 = 5000 (NOT 6000 from other truck)
        assert bill.total == 5000

    @pytest.mark.asyncio
    async def test_calculate_bill_skips_transactions_with_na_neto(
        self, mock_weight_service, sample_provider, sample_truck, sample_rate
    ):
        """
        Test that transactions with neto='na' are skipped in calculations.
        """
        # Setup mock data with 'na' neto values
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": "na", "produce": "apples"},  # Should skip
            {"truck": "ABC123", "neto": 2000, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should only count 2 sessions (skip 'na')
        assert bill.sessionCount == 2
        # Total: 3000kg × 5 = 15000 (not including 'na' transaction)
        assert bill.total == 15000

    @pytest.mark.asyncio
    async def test_calculate_bill_skips_transactions_with_na_produce(
        self, mock_weight_service, sample_provider, sample_truck, sample_rate
    ):
        """
        Test that transactions with produce='na' are skipped in calculations.
        """
        # Setup mock data with 'na' produce values
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": 2000, "produce": "na"},  # Should skip
            {"truck": "ABC123", "neto": 1500, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should only count apples (skip 'na' produce)
        assert bill.sessionCount == 2
        # Total: 2500kg × 5 = 12500
        assert bill.total == 12500

    @pytest.mark.asyncio
    async def test_calculate_bill_skips_transactions_without_rate(
        self, mock_weight_service, sample_provider, sample_truck
    ):
        """
        Test that transactions for products without rates are skipped.
        """
        # Setup mock data with product that has no rate
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": 2000, "produce": "bananas"},  # No rate
        ])

        # Only apples rate
        apples_rate = Rate(product_id="apples", rate=5, scope="ALL")

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[apples_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should only count apples (bananas has no rate)
        assert bill.sessionCount == 1
        assert len(bill.products) == 1
        assert bill.products[0].product == "apples"
        # Total: 1000kg × 5 = 5000
        assert bill.total == 5000

    @pytest.mark.asyncio
    async def test_calculate_bill_empty_transactions(
        self, mock_weight_service, sample_provider, sample_truck, sample_rate
    ):
        """
        Test bill calculation when no transactions exist for the date range.
        """
        # Setup mock data with no transactions
        mock_weight_service.set_transactions([])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20250101235959"
            )

        # Should have zero values
        assert bill.sessionCount == 0
        assert len(bill.products) == 0
        assert bill.total == 0

    @pytest.mark.asyncio
    async def test_generate_bill_provider_not_found(self):
        """
        Test that NotFoundError is raised when provider doesn't exist.
        """
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError, match="Provider not found"):
            await service.generate_bill(
                provider_id=999,
                from_date="20250101000000",
                to_date="20251231235959"
            )

    @pytest.mark.asyncio
    async def test_calculate_bill_handles_weight_service_error(
        self, sample_provider, sample_truck, sample_rate
    ):
        """
        Test that bill generation handles weight service errors gracefully.
        """
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Mock weight client to raise exception
        mock_client = AsyncMock()
        mock_client.get_transactions = AsyncMock(side_effect=Exception("Service unavailable"))

        with patch.object(service, 'weight_client', mock_client):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should return empty bill
        assert bill.sessionCount == 0
        assert bill.total == 0


class TestBillServiceRateLogic:
    """Test rate finding and precedence logic."""

    def test_find_applicable_rate_case_insensitive_product(self, sample_provider):
        """
        Test that product matching is case-insensitive.
        """
        service = BillService()

        rates = [
            Rate(product_id="Apples", rate=5, scope="ALL"),
        ]

        # Should find rate regardless of case
        rate = service._find_applicable_rate(rates, "apples", sample_provider.id)
        assert rate is not None
        assert rate.rate == 5

        rate = service._find_applicable_rate(rates, "APPLES", sample_provider.id)
        assert rate is not None
        assert rate.rate == 5

    def test_find_applicable_rate_no_match(self, sample_provider):
        """
        Test that None is returned when no rate matches the product.
        """
        service = BillService()

        rates = [
            Rate(product_id="apples", rate=5, scope="ALL"),
        ]

        rate = service._find_applicable_rate(rates, "bananas", sample_provider.id)
        assert rate is None

    def test_find_applicable_rate_all_scope_case_insensitive(self, sample_provider):
        """
        Test that scope 'ALL' matching is case-insensitive.
        """
        service = BillService()

        rates = [
            Rate(product_id="apples", rate=5, scope="all"),  # lowercase
        ]

        rate = service._find_applicable_rate(rates, "apples", sample_provider.id)
        assert rate is not None
        assert rate.rate == 5


class TestBillServiceFiltering:
    """Test transaction filtering logic."""

    def test_filter_provider_transactions_includes_only_provider_trucks(self):
        """
        Test that filtering only includes transactions for provider's trucks.
        """
        service = BillService()

        transactions = [
            {"truck": "ABC123", "neto": 1000},
            {"truck": "XYZ789", "neto": 2000},
            {"truck": "OTHER", "neto": 3000},
        ]

        truck_ids = ["ABC123", "XYZ789"]

        filtered = service._filter_provider_transactions(transactions, truck_ids)

        assert len(filtered) == 2
        assert filtered[0]["truck"] == "ABC123"
        assert filtered[1]["truck"] == "XYZ789"

    def test_filter_provider_transactions_handles_missing_truck_field(self):
        """
        Test that filtering handles transactions without truck field.
        """
        service = BillService()

        transactions = [
            {"truck": "ABC123", "neto": 1000},
            {"neto": 2000},  # No truck field
            {"truck": None, "neto": 3000},  # None truck
        ]

        truck_ids = ["ABC123"]

        filtered = service._filter_provider_transactions(transactions, truck_ids)

        assert len(filtered) == 1
        assert filtered[0]["truck"] == "ABC123"


class TestBillServiceProductSummary:
    """Test product summary aggregation."""

    @pytest.mark.asyncio
    async def test_product_summary_count_format(
        self, mock_weight_service, sample_provider, sample_truck, sample_rate
    ):
        """
        Test that product count is returned as string as per API spec.
        """
        # Setup mock data
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": 1500, "produce": "apples"},
            {"truck": "ABC123", "neto": 2000, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Count should be string "3"
        assert bill.products[0].count == "3"
        assert isinstance(bill.products[0].count, str)

    @pytest.mark.asyncio
    async def test_product_summary_aggregation(
        self, mock_weight_service, sample_provider, sample_truck, sample_rate
    ):
        """
        Test that product summary correctly aggregates multiple transactions.
        """
        # Setup mock data
        mock_weight_service.set_transactions([
            {"truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"truck": "ABC123", "neto": 1500, "produce": "apples"},
            {"truck": "ABC123", "neto": 2500, "produce": "apples"},
        ])

        # Mock repositories
        service = BillService()
        service.provider_repo.get_by_id = AsyncMock(return_value=sample_provider)
        service.truck_repo.get_by_provider = AsyncMock(return_value=[sample_truck])
        service.rate_repo.get_all = AsyncMock(return_value=[sample_rate])

        # Patch weight client
        with patch.object(service, 'weight_client', mock_weight_service):
            bill = await service.generate_bill(
                provider_id=sample_provider.id,
                from_date="20250101000000",
                to_date="20251231235959"
            )

        product = bill.products[0]
        assert product.count == "3"
        assert product.amount == 5000  # 1000 + 1500 + 2500
        assert product.rate == 5
        assert product.pay == 25000  # 5000 × 5
