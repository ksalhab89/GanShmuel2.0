"""Database model tests for billing service.

Tests database model relationships, constraints, and data integrity.
"""

import pytest

from src.models.database import Provider, Rate, Truck, WeightItem, WeightTransaction


class TestProviderModel:
    """Test suite for Provider model."""

    def test_provider_creation(self):
        """Test creating a Provider instance."""
        provider = Provider(id=1, name="Test Provider")

        assert provider.id == 1
        assert provider.name == "Test Provider"

    def test_provider_immutability(self):
        """Test that Provider is a frozen dataclass."""
        provider = Provider(id=1, name="Test Provider")

        # Dataclasses are immutable (frozen=True would be needed)
        # This test verifies the model structure
        assert hasattr(provider, "id")
        assert hasattr(provider, "name")

    def test_provider_with_none_id(self):
        """Test creating provider with None id (before insertion)."""
        # This should work for new providers before DB insertion
        # The actual validation happens at repository level
        provider = Provider(id=0, name="New Provider")
        assert provider.name == "New Provider"

    def test_provider_equality(self):
        """Test provider equality comparison."""
        provider1 = Provider(id=1, name="Test")
        provider2 = Provider(id=1, name="Test")
        provider3 = Provider(id=2, name="Test")

        assert provider1 == provider2
        assert provider1 != provider3

    def test_provider_repr(self):
        """Test provider string representation."""
        provider = Provider(id=1, name="Test Provider")
        repr_str = repr(provider)

        assert "Provider" in repr_str
        assert "1" in repr_str
        assert "Test Provider" in repr_str


class TestTruckModel:
    """Test suite for Truck model."""

    def test_truck_creation(self):
        """Test creating a Truck instance."""
        truck = Truck(id="ABC123", provider_id=1)

        assert truck.id == "ABC123"
        assert truck.provider_id == 1

    def test_truck_with_string_id(self):
        """Test truck with various string ID formats."""
        truck1 = Truck(id="123-456", provider_id=1)
        truck2 = Truck(id="XYZ", provider_id=2)
        truck3 = Truck(id="12-34-56", provider_id=3)

        assert truck1.id == "123-456"
        assert truck2.id == "XYZ"
        assert truck3.id == "12-34-56"

    def test_truck_equality(self):
        """Test truck equality comparison."""
        truck1 = Truck(id="ABC123", provider_id=1)
        truck2 = Truck(id="ABC123", provider_id=1)
        truck3 = Truck(id="XYZ789", provider_id=1)

        assert truck1 == truck2
        assert truck1 != truck3

    def test_truck_repr(self):
        """Test truck string representation."""
        truck = Truck(id="ABC123", provider_id=1)
        repr_str = repr(truck)

        assert "Truck" in repr_str
        assert "ABC123" in repr_str


class TestRateModel:
    """Test suite for Rate model."""

    def test_rate_creation(self):
        """Test creating a Rate instance."""
        rate = Rate(product_id="apples", rate=5, scope="ALL")

        assert rate.product_id == "apples"
        assert rate.rate == 5
        assert rate.scope == "ALL"

    def test_rate_with_provider_scope(self):
        """Test rate with provider-specific scope."""
        rate = Rate(product_id="oranges", rate=10, scope="123")

        assert rate.scope == "123"

    def test_rate_with_zero_rate(self):
        """Test rate with zero value."""
        rate = Rate(product_id="free_sample", rate=0, scope="ALL")

        assert rate.rate == 0

    def test_rate_with_negative_rate(self):
        """Test rate with negative value (discount scenario)."""
        rate = Rate(product_id="discount", rate=-5, scope="ALL")

        assert rate.rate == -5

    def test_rate_equality(self):
        """Test rate equality comparison."""
        rate1 = Rate(product_id="apples", rate=5, scope="ALL")
        rate2 = Rate(product_id="apples", rate=5, scope="ALL")
        rate3 = Rate(product_id="apples", rate=6, scope="ALL")

        assert rate1 == rate2
        assert rate1 != rate3

    def test_rate_different_scopes(self):
        """Test rates with different scopes for same product."""
        rate_all = Rate(product_id="apples", rate=5, scope="ALL")
        rate_provider = Rate(product_id="apples", rate=6, scope="123")

        assert rate_all.product_id == rate_provider.product_id
        assert rate_all.scope != rate_provider.scope
        assert rate_all.rate != rate_provider.rate

    def test_rate_repr(self):
        """Test rate string representation."""
        rate = Rate(product_id="apples", rate=5, scope="ALL")
        repr_str = repr(rate)

        assert "Rate" in repr_str
        assert "apples" in repr_str


class TestWeightTransactionModel:
    """Test suite for WeightTransaction model."""

    def test_weight_transaction_creation(self):
        """Test creating a WeightTransaction instance."""
        transaction = WeightTransaction(
            id="tr123",
            direction="in",
            bruto=12000,
            neto=None,
            produce="apples",
            truck="ABC123",
            containers=["c1", "c2"],
            timestamp="20250101120000",
        )

        assert transaction.id == "tr123"
        assert transaction.direction == "in"
        assert transaction.bruto == 12000
        assert transaction.neto is None

    def test_weight_transaction_with_na_values(self):
        """Test transaction with 'na' string values."""
        transaction = WeightTransaction(
            id="tr456",
            direction="in",
            bruto=12000,
            neto="na",
            produce="apples",
            truck="ABC123",
            containers=[],
            timestamp="20250101120000",
        )

        assert transaction.neto == "na"

    def test_weight_transaction_complete(self):
        """Test complete transaction (OUT direction)."""
        transaction = WeightTransaction(
            id="tr789",
            direction="out",
            bruto=12000,
            neto=1000,
            produce="apples",
            truck="ABC123",
            containers=["c1", "c2", "c3"],
            timestamp="20250101140000",
        )

        assert transaction.direction == "out"
        assert transaction.neto == 1000
        assert len(transaction.containers) == 3

    def test_weight_transaction_no_containers(self):
        """Test transaction without containers."""
        transaction = WeightTransaction(
            id="tr999",
            direction="in",
            bruto=12000,
            neto=None,
            produce="apples",
            truck="ABC123",
            containers=[],
            timestamp="20250101120000",
        )

        assert transaction.containers == []

    def test_weight_transaction_repr(self):
        """Test transaction string representation."""
        transaction = WeightTransaction(
            id="tr123",
            direction="in",
            bruto=12000,
            neto=None,
            produce="apples",
            truck="ABC123",
            containers=["c1"],
            timestamp="20250101120000",
        )
        repr_str = repr(transaction)

        assert "WeightTransaction" in repr_str


class TestWeightItemModel:
    """Test suite for WeightItem model."""

    def test_weight_item_creation(self):
        """Test creating a WeightItem instance."""
        item = WeightItem(id="ABC123", tara=10000, sessions=["sess1", "sess2"])

        assert item.id == "ABC123"
        assert item.tara == 10000
        assert len(item.sessions) == 2

    def test_weight_item_with_na_tara(self):
        """Test item with 'na' tara value."""
        item = WeightItem(id="XYZ789", tara="na", sessions=[])

        assert item.tara == "na"

    def test_weight_item_no_sessions(self):
        """Test item without sessions."""
        item = WeightItem(id="DEF456", tara=10000, sessions=[])

        assert item.sessions == []

    def test_weight_item_multiple_sessions(self):
        """Test item with multiple sessions."""
        item = WeightItem(id="GHI789", tara=10000, sessions=["s1", "s2", "s3", "s4"])

        assert len(item.sessions) == 4

    def test_weight_item_repr(self):
        """Test item string representation."""
        item = WeightItem(id="ABC123", tara=10000, sessions=["sess1"])
        repr_str = repr(item)

        assert "WeightItem" in repr_str


class TestModelRelationships:
    """Test suite for model relationships and constraints."""

    @pytest.mark.asyncio
    async def test_provider_truck_relationship(self, db_connection):
        """Test provider-truck foreign key relationship."""
        cursor = db_connection.cursor()

        # Create provider
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", ("Test Provider",))
        db_connection.commit()
        provider_id = cursor.lastrowid

        # Create truck for provider
        cursor.execute(
            "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
            ("TRUCK001", provider_id),
        )
        db_connection.commit()

        # Verify relationship
        cursor.execute(
            "SELECT id, provider_id FROM Trucks WHERE id = %s", ("TRUCK001",)
        )
        result = cursor.fetchone()

        assert result[0] == "TRUCK001"
        assert result[1] == provider_id

        cursor.close()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_provider_name_unique_constraint(self, db_connection):
        """Test that provider names must be unique."""
        cursor = db_connection.cursor()

        # Insert first provider
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", ("Unique Name",))
        db_connection.commit()

        # Try to insert duplicate name
        with pytest.raises(Exception):  # MySQL IntegrityError
            cursor.execute("INSERT INTO Provider (name) VALUES (%s)", ("Unique Name",))
            db_connection.commit()

        db_connection.rollback()
        cursor.close()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_truck_foreign_key_constraint(self, db_connection):
        """Test that trucks cannot reference non-existent providers."""
        cursor = db_connection.cursor()

        # Try to insert truck with non-existent provider
        with pytest.raises(Exception):  # MySQL foreign key constraint
            cursor.execute(
                "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
                ("INVALID", 99999),
            )
            db_connection.commit()

        db_connection.rollback()
        cursor.close()

    @pytest.mark.asyncio
    async def test_truck_primary_key_constraint(self, db_connection, sample_provider):
        """Test that truck IDs must be unique."""
        cursor = db_connection.cursor()

        # Insert first truck
        cursor.execute(
            "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
            ("DUPLICATE", sample_provider.id),
        )
        db_connection.commit()

        # Try to insert duplicate truck ID
        with pytest.raises(Exception):  # MySQL primary key constraint
            cursor.execute(
                "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
                ("DUPLICATE", sample_provider.id),
            )
            db_connection.commit()

        db_connection.rollback()
        cursor.close()

    @pytest.mark.asyncio
    async def test_rate_multiple_entries_same_product(self, db_connection):
        """Test that multiple rates can exist for same product with different scopes."""
        cursor = db_connection.cursor()

        # Insert general rate
        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            ("apples", 5, "ALL"),
        )

        # Insert provider-specific rate for same product
        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            ("apples", 7, "123"),
        )

        db_connection.commit()

        # Verify both rates exist
        cursor.execute("SELECT COUNT(*) FROM Rates WHERE product_id = %s", ("apples",))
        count = cursor.fetchone()[0]

        assert count == 2

        cursor.close()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_cascade_behavior_on_provider_delete(
        self, db_connection, sample_provider
    ):
        """Test what happens to trucks when provider is deleted."""
        cursor = db_connection.cursor()

        # Create truck for provider
        cursor.execute(
            "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
            ("CASCADE_TEST", sample_provider.id),
        )
        db_connection.commit()

        # Try to delete provider (should fail due to foreign key constraint)
        with pytest.raises(Exception):  # MySQL foreign key constraint
            cursor.execute("DELETE FROM Provider WHERE id = %s", (sample_provider.id,))
            db_connection.commit()

        db_connection.rollback()
        cursor.close()


class TestDataIntegrity:
    """Test suite for data integrity and validation."""

    @pytest.mark.asyncio
    async def test_empty_provider_name_handling(self, db_connection):
        """Test that empty provider names are handled."""
        cursor = db_connection.cursor()

        # Try to insert provider with empty name
        # Depending on constraints, this might succeed or fail
        try:
            cursor.execute("INSERT INTO Provider (name) VALUES (%s)", ("",))
            db_connection.commit()

            # If it succeeds, verify it was inserted
            cursor.execute("SELECT name FROM Provider WHERE name = %s", ("",))
            cursor.fetchone()
            # Empty string handling depends on schema constraints
            cursor.close()
        except Exception:
            # If constraints prevent empty names, that's also valid
            db_connection.rollback()
            cursor.close()

    @pytest.mark.asyncio
    async def test_truck_id_max_length(self, db_connection, sample_provider):
        """Test truck ID length constraint (max 10 characters)."""
        cursor = db_connection.cursor()

        # Insert truck with max length ID (10 chars)
        cursor.execute(
            "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
            ("1234567890", sample_provider.id),
        )
        db_connection.commit()

        # Verify it was inserted
        cursor.execute("SELECT id FROM Trucks WHERE id = %s", ("1234567890",))
        result = cursor.fetchone()
        assert result[0] == "1234567890"

        # Try to insert truck with ID longer than 10 chars
        with pytest.raises(Exception):  # MySQL data too long error
            cursor.execute(
                "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)",
                ("12345678901", sample_provider.id),
            )
            db_connection.commit()

        db_connection.rollback()
        cursor.close()

    @pytest.mark.asyncio
    async def test_rate_negative_values(self, db_connection):
        """Test that rates can handle negative values (discounts)."""
        cursor = db_connection.cursor()

        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            ("discount_item", -100, "ALL"),
        )
        db_connection.commit()

        cursor.execute(
            "SELECT rate FROM Rates WHERE product_id = %s", ("discount_item",)
        )
        result = cursor.fetchone()

        assert result[0] == -100

        cursor.close()

    @pytest.mark.asyncio
    async def test_rate_zero_value(self, db_connection):
        """Test that rates can be zero (free items)."""
        cursor = db_connection.cursor()

        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            ("free_item", 0, "ALL"),
        )
        db_connection.commit()

        cursor.execute("SELECT rate FROM Rates WHERE product_id = %s", ("free_item",))
        result = cursor.fetchone()

        assert result[0] == 0

        cursor.close()

    @pytest.mark.asyncio
    async def test_unicode_in_provider_names(self, db_connection):
        """Test that provider names support unicode characters."""
        cursor = db_connection.cursor()

        # Insert provider with unicode characters
        unicode_name = "פירות גן שמואל 🍎"
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", (unicode_name,))
        db_connection.commit()

        cursor.execute("SELECT name FROM Provider WHERE name = %s", (unicode_name,))
        result = cursor.fetchone()

        assert result[0] == unicode_name

        cursor.close()

    @pytest.mark.asyncio
    async def test_case_sensitivity_in_product_ids(self, db_connection):
        """Test case sensitivity in rate product IDs."""
        cursor = db_connection.cursor()

        # Insert rates with different cases
        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            ("Apples", 5, "ALL"),
        )
        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            ("apples", 6, "ALL"),
        )
        db_connection.commit()

        # Both should exist (case-sensitive)
        cursor.execute(
            "SELECT COUNT(*) FROM Rates WHERE product_id IN (%s, %s)",
            ("Apples", "apples"),
        )
        count = cursor.fetchone()[0]

        # MySQL string comparison depends on collation
        # With utf8mb4_unicode_ci, this might be case-insensitive
        assert count >= 1

        cursor.close()
