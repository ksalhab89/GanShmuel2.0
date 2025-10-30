import logging
from typing import Any, Dict, List, Optional

from ..models.database import Rate
from ..models.repositories import ProviderRepository, RateRepository, TruckRepository
from ..models.schemas import BillResponse, ProductSummary
from ..services.weight_client import weight_client
from ..utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class BillService:
    """Service for generating provider bills."""

    def __init__(self):
        self.provider_repo = ProviderRepository()
        self.truck_repo = TruckRepository()
        self.rate_repo = RateRepository()
        self.weight_client = weight_client

    async def generate_bill(
        self, provider_id: int, from_date: str, to_date: str
    ) -> BillResponse:
        """
        Generate bill for provider based on weight transactions.

        Args:
            provider_id: ID of the provider
            from_date: Start date in yyyymmddhhmmss format
            to_date: End date in yyyymmddhhmmss format

        Returns:
            BillResponse with calculated totals

        Raises:
            NotFoundError: If provider not found
        """
        # Get provider information
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise NotFoundError("Provider not found")

        # Get trucks for this provider
        trucks = await self.truck_repo.get_by_provider(provider_id)
        truck_ids = [truck.id for truck in trucks]

        # Get all rates for calculation
        all_rates = await self.rate_repo.get_all()

        # Get weight transactions from weight service
        try:
            transactions = await self.weight_client.get_transactions(from_date, to_date)
        except Exception as e:
            logger.warning(f"Could not fetch transactions from weight service: {e}")
            transactions = []

        # Filter transactions for trucks belonging to this provider
        provider_transactions = self._filter_provider_transactions(
            transactions, truck_ids
        )

        # Calculate bill totals
        products_summary, session_count, total_amount = self._calculate_bill_totals(
            provider_transactions, all_rates, provider_id
        )

        return BillResponse(
            id=str(provider_id),
            name=provider.name,
            **{"from": from_date},  # Use dict unpacking for 'from' field
            to=to_date,
            truckCount=len(truck_ids),
            sessionCount=session_count,
            products=products_summary,
            total=total_amount,
        )

    def _filter_provider_transactions(
        self, transactions: List[Dict[str, Any]], truck_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter transactions for trucks belonging to provider."""
        provider_transactions = []

        for transaction in transactions:
            # Check if transaction has truck field and it belongs to this provider
            truck_field = transaction.get("truck")
            if truck_field and truck_field in truck_ids:
                provider_transactions.append(transaction)

        return provider_transactions

    def _calculate_bill_totals(
        self,
        transactions: List[Dict[str, Any]],
        all_rates: List[Rate],
        provider_id: int,
    ) -> tuple[List[ProductSummary], int, int]:
        """
        Calculate bill totals from transactions.

        Returns:
            Tuple of (products_summary, session_count, total_amount)
        """
        products_data = {}
        session_count = 0

        for transaction in transactions:
            product = transaction.get("produce", "na")
            if product == "na":
                continue

            neto = transaction.get("neto")
            if neto == "na" or not neto:
                continue

            # Convert neto to int if it's a string number
            try:
                neto = int(neto) if isinstance(neto, str) else neto
            except (ValueError, TypeError):
                continue

            # Find applicable rate
            rate_info = self._find_applicable_rate(all_rates, product, provider_id)
            if not rate_info:
                continue

            rate = rate_info.rate
            pay = neto * rate

            if product not in products_data:
                products_data[product] = {
                    "product": product,
                    "count": 0,
                    "amount": 0,
                    "rate": rate,
                    "pay": 0,
                }

            products_data[product]["count"] += 1
            products_data[product]["amount"] += neto
            products_data[product]["pay"] += pay
            session_count += 1

        # Convert to ProductSummary objects
        products_summary = [
            ProductSummary(
                product=p["product"],
                count=str(p["count"]),  # API spec requires string
                amount=p["amount"],
                rate=p["rate"],
                pay=p["pay"],
            )
            for p in products_data.values()
        ]

        total_amount = sum(p["pay"] for p in products_data.values())

        return products_summary, session_count, total_amount

    def _find_applicable_rate(
        self, rates: List[Rate], product: str, provider_id: int
    ) -> Optional[Rate]:
        """
        Find applicable rate with precedence rules.

        Provider-specific rates (scope = provider_id) override ALL scope rates.
        """
        provider_rate = None
        all_rate = None

        for rate in rates:
            # Case-insensitive product matching
            if rate.product_id.lower() == product.lower():
                if rate.scope == str(provider_id):
                    provider_rate = rate
                elif rate.scope.upper() == "ALL":
                    all_rate = rate

        # Return provider-specific rate if found, otherwise ALL rate
        return provider_rate or all_rate


# Global bill service instance
bill_service = BillService()
