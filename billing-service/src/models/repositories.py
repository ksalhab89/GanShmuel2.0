from typing import List, Optional

from ..database import execute_query
from ..utils.exceptions import DuplicateError, NotFoundError
from .database import Provider, Rate, Truck


class ProviderRepository:
    """Repository for Provider database operations."""

    async def create(self, name: str) -> Provider:
        """Create a new provider."""
        # Check if provider already exists
        existing = await execute_query(
            "SELECT id FROM Provider WHERE name = %s", (name,), fetch_one=True
        )
        if existing:
            raise DuplicateError("Provider name must be unique")

        # Insert new provider
        result = await execute_query("INSERT INTO Provider (name) VALUES (%s)", (name,))

        return Provider(id=result["last_insert_id"], name=name)

    async def get_by_id(self, provider_id: int) -> Optional[Provider]:
        """Get provider by ID."""
        result = await execute_query(
            "SELECT id, name FROM Provider WHERE id = %s",
            (provider_id,),
            fetch_one=True,
        )
        if result:
            return Provider(**result)
        return None

    async def update(self, provider_id: int, name: str) -> Provider:
        """Update provider name."""
        # Check if provider exists
        existing = await self.get_by_id(provider_id)
        if not existing:
            raise NotFoundError("Provider not found")

        # Check if new name conflicts with another provider
        conflicting = await execute_query(
            "SELECT id FROM Provider WHERE name = %s AND id != %s",
            (name, provider_id),
            fetch_one=True,
        )
        if conflicting:
            raise DuplicateError("Provider name must be unique")

        # Update provider
        await execute_query(
            "UPDATE Provider SET name = %s WHERE id = %s", (name, provider_id)
        )

        return Provider(id=provider_id, name=name)


class RateRepository:
    """Repository for Rate database operations."""

    async def clear_all(self) -> None:
        """Clear all existing rates."""
        await execute_query("DELETE FROM Rates")

    async def create_batch(self, rates: List[Rate]) -> int:
        """Create multiple rates in batch."""
        count = 0
        for rate in rates:
            await execute_query(
                "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
                (rate.product_id, rate.rate, rate.scope),
            )
            count += 1
        return count

    async def get_all(self) -> List[Rate]:
        """Get all rates."""
        results = await execute_query(
            "SELECT product_id, rate, scope FROM Rates", fetch_all=True
        )
        return [Rate(**result) for result in (results or [])]


class TruckRepository:
    """Repository for Truck database operations."""

    async def create_or_update(self, truck_id: str, provider_id: int) -> Truck:
        """Create or update truck registration (upsert)."""
        # Check if provider exists
        provider_exists = await execute_query(
            "SELECT id FROM Provider WHERE id = %s", (provider_id,), fetch_one=True
        )
        if not provider_exists:
            raise NotFoundError("Provider not found")

        # Insert or update truck
        await execute_query(
            "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE provider_id = %s",
            (truck_id, provider_id, provider_id),
        )

        return Truck(id=truck_id, provider_id=provider_id)

    async def get_by_id(self, truck_id: str) -> Optional[Truck]:
        """Get truck by ID."""
        result = await execute_query(
            "SELECT id, provider_id FROM Trucks WHERE id = %s",
            (truck_id,),
            fetch_one=True,
        )
        if result:
            return Truck(**result)
        return None

    async def update(self, truck_id: str, provider_id: int) -> Truck:
        """Update truck's provider assignment."""
        # Check if truck exists
        existing = await self.get_by_id(truck_id)
        if not existing:
            raise NotFoundError("Truck not found")

        # Check if provider exists
        provider_exists = await execute_query(
            "SELECT id FROM Provider WHERE id = %s", (provider_id,), fetch_one=True
        )
        if not provider_exists:
            raise NotFoundError("Provider not found")

        # Update truck
        await execute_query(
            "UPDATE Trucks SET provider_id = %s WHERE id = %s", (provider_id, truck_id)
        )

        return Truck(id=truck_id, provider_id=provider_id)

    async def get_by_provider(self, provider_id: int) -> List[Truck]:
        """Get all trucks for a provider."""
        results = await execute_query(
            "SELECT id, provider_id FROM Trucks WHERE provider_id = %s",
            (provider_id,),
            fetch_all=True,
        )
        return [Truck(**result) for result in (results or [])]
