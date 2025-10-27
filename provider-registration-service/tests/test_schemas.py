"""Schema validation tests."""
import pytest
from pydantic import ValidationError
from datetime import datetime
from uuid import UUID, uuid4
from src.models.schemas import (
    CandidateCreate,
    CandidateResponse,
    CandidateList,
    ApprovalResponse
)


class TestCandidateCreateSchema:
    """Test suite for CandidateCreate schema validation"""

    def test_valid_candidate_data(self):
        """Test valid candidate creation."""
        data = {
            "company_name": "Test Company",
            "contact_email": "test@company.com",
            "phone": "123-456-7890",
            "products": ["apples", "oranges"],
            "truck_count": 5,
            "capacity_tons_per_day": 100,
            "location": "Test City"
        }
        candidate = CandidateCreate(**data)
        assert candidate.company_name == "Test Company"
        assert len(candidate.products) == 2
        assert candidate.truck_count == 5
        assert candidate.capacity_tons_per_day == 100

    def test_minimal_valid_data(self):
        """Test candidate with only required fields."""
        data = {
            "company_name": "Minimal Company",
            "contact_email": "minimal@company.com",
            "products": ["apples"],
            "truck_count": 1,
            "capacity_tons_per_day": 10
        }
        candidate = CandidateCreate(**data)
        assert candidate.company_name == "Minimal Company"
        assert candidate.phone is None
        assert candidate.location is None

    def test_email_validation(self):
        """Test email format validation."""
        data = {
            "company_name": "Test",
            "contact_email": "not-an-email",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError) as exc:
            CandidateCreate(**data)
        assert "email" in str(exc.value).lower()

    def test_products_whitelist(self):
        """Test product whitelist validation."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": ["invalid_product"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError) as exc:
            CandidateCreate(**data)
        assert "invalid_product" in str(exc.value).lower()

    def test_valid_products(self):
        """Test all valid products are accepted."""
        valid_products = ['apples', 'oranges', 'grapes', 'bananas', 'mangoes']
        for product in valid_products:
            data = {
                "company_name": "Test",
                "contact_email": "test@test.com",
                "products": [product],
                "truck_count": 5,
                "capacity_tons_per_day": 100
            }
            candidate = CandidateCreate(**data)
            assert candidate.products == [product]

    def test_multiple_valid_products(self):
        """Test multiple valid products."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": ["apples", "oranges", "grapes"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        candidate = CandidateCreate(**data)
        assert len(candidate.products) == 3

    def test_negative_truck_count(self):
        """Test truck_count validation."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": ["apples"],
            "truck_count": -1,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_zero_truck_count(self):
        """Test zero truck_count is invalid."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": ["apples"],
            "truck_count": 0,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_zero_capacity(self):
        """Test capacity validation."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 0
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_negative_capacity(self):
        """Test negative capacity is invalid."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": -50
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_empty_company_name(self):
        """Test empty company name is invalid."""
        data = {
            "company_name": "",
            "contact_email": "test@test.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_empty_products_list(self):
        """Test empty products list is invalid."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "products": [],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_long_company_name(self):
        """Test company name length limit."""
        data = {
            "company_name": "A" * 256,  # Exceeds max length
            "contact_email": "test@test.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)

    def test_long_phone_number(self):
        """Test phone number length limit."""
        data = {
            "company_name": "Test",
            "contact_email": "test@test.com",
            "phone": "1" * 51,  # Exceeds max length
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        with pytest.raises(ValidationError):
            CandidateCreate(**data)


class TestCandidateResponseSchema:
    """Test suite for CandidateResponse schema"""

    def test_candidate_response_creation(self):
        """Test creating a CandidateResponse."""
        response = CandidateResponse(
            candidate_id=uuid4(),
            status="pending",
            company_name="Test Company",
            contact_email="test@company.com",
            products=["apples"],
            truck_count=5,
            capacity_tons_per_day=100,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1
        )
        assert response.status == "pending"
        assert response.provider_id is None

    def test_candidate_response_with_provider_id(self):
        """Test CandidateResponse with provider_id."""
        response = CandidateResponse(
            candidate_id=uuid4(),
            status="approved",
            company_name="Test Company",
            contact_email="test@company.com",
            products=["apples"],
            truck_count=5,
            capacity_tons_per_day=100,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1,
            provider_id=123
        )
        assert response.status == "approved"
        assert response.provider_id == 123


class TestCandidateListSchema:
    """Test suite for CandidateList schema"""

    def test_empty_candidate_list(self):
        """Test empty candidate list."""
        candidate_list = CandidateList(
            candidates=[],
            pagination={"total": 0, "limit": 20, "offset": 0}
        )
        assert len(candidate_list.candidates) == 0
        assert candidate_list.pagination["total"] == 0

    def test_candidate_list_with_items(self):
        """Test candidate list with items."""
        candidates = [
            CandidateResponse(
                candidate_id=uuid4(),
                status="pending",
                company_name=f"Company {i}",
                contact_email=f"test{i}@company.com",
                products=["apples"],
                truck_count=5,
                capacity_tons_per_day=100,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                version=1
            )
            for i in range(5)
        ]
        candidate_list = CandidateList(
            candidates=candidates,
            pagination={"total": 5, "limit": 20, "offset": 0}
        )
        assert len(candidate_list.candidates) == 5
        assert candidate_list.pagination["total"] == 5


class TestApprovalResponseSchema:
    """Test suite for ApprovalResponse schema"""

    def test_approval_response_creation(self):
        """Test creating an ApprovalResponse."""
        response = ApprovalResponse(
            candidate_id=uuid4(),
            status="approved",
            provider_id=123
        )
        assert response.status == "approved"
        assert response.provider_id == 123
        assert isinstance(response.candidate_id, UUID)

    def test_approval_response_validation(self):
        """Test ApprovalResponse requires all fields."""
        with pytest.raises(ValidationError):
            ApprovalResponse(
                candidate_id=uuid4(),
                status="approved"
                # Missing provider_id
            )
