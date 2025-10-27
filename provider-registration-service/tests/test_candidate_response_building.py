"""
Test CandidateResponse building helper method
Ensures DRY refactoring doesn't break functionality
"""
import pytest
from uuid import uuid4
from datetime import datetime
import json
from unittest.mock import Mock

from src.services.candidate_service import CandidateService
from src.models.schemas import CandidateResponse

pytestmark = pytest.mark.asyncio


class TestCandidateResponseBuilder:
    """Test _build_response helper method for DRY code"""

    def test_build_response_with_all_fields(self):
        """
        DRY TEST: Helper builds complete response with all fields
        """
        # Create mock database row
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.status = "pending"
        mock_row.company_name = "Test Company"
        mock_row.contact_email = "test@example.com"
        mock_row.phone = "123-456-7890"
        mock_row.products = ["apples", "oranges"]  # Already deserialized
        mock_row.truck_count = 5
        mock_row.capacity_tons_per_day = 100
        mock_row.location = "Test City"
        mock_row.created_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_row.updated_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_row.provider_id = None
        mock_row.version = 1

        # Create service instance
        service = CandidateService(Mock())

        # Build response
        response = service._build_response(mock_row)

        # Verify all fields
        assert isinstance(response, CandidateResponse)
        assert response.candidate_id == mock_row.id
        assert response.status == "pending"
        assert response.company_name == "Test Company"
        assert response.contact_email == "test@example.com"
        assert response.phone == "123-456-7890"
        assert response.products == ["apples", "oranges"]
        assert response.truck_count == 5
        assert response.capacity_tons_per_day == 100
        assert response.location == "Test City"
        assert response.created_at == mock_row.created_at
        assert response.updated_at == mock_row.updated_at
        assert response.provider_id is None
        assert response.version == 1

    def test_build_response_handles_jsonb_as_string(self):
        """
        DRY TEST: Helper handles JSONB as JSON string
        Some database drivers return JSONB as string
        """
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.status = "pending"
        mock_row.company_name = "JSONB Test"
        mock_row.contact_email = "jsonb@test.com"
        mock_row.phone = None
        mock_row.products = '["apples", "oranges"]'  # JSON string, not list
        mock_row.truck_count = 3
        mock_row.capacity_tons_per_day = 50
        mock_row.location = "JSONB City"
        mock_row.created_at = datetime.now()
        mock_row.updated_at = datetime.now()
        mock_row.provider_id = None
        mock_row.version = 1

        service = CandidateService(Mock())
        response = service._build_response(mock_row)

        # Should deserialize JSON string to list
        assert response.products == ["apples", "oranges"]
        assert isinstance(response.products, list)

    def test_build_response_handles_null_products(self):
        """
        DRY TEST: Helper handles NULL products gracefully
        """
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.status = "pending"
        mock_row.company_name = "Null Products Test"
        mock_row.contact_email = "null@test.com"
        mock_row.phone = None
        mock_row.products = None  # NULL in database
        mock_row.truck_count = 1
        mock_row.capacity_tons_per_day = 10
        mock_row.location = None
        mock_row.created_at = datetime.now()
        mock_row.updated_at = datetime.now()
        mock_row.provider_id = None
        mock_row.version = 1

        service = CandidateService(Mock())
        response = service._build_response(mock_row)

        # Should return empty list for null products
        assert response.products == []

    def test_build_response_with_approved_candidate(self):
        """
        DRY TEST: Helper works for approved candidates (with provider_id)
        """
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.status = "approved"
        mock_row.company_name = "Approved Company"
        mock_row.contact_email = "approved@test.com"
        mock_row.phone = "555-0100"
        mock_row.products = ["grapes"]
        mock_row.truck_count = 10
        mock_row.capacity_tons_per_day = 200
        mock_row.location = "Approved City"
        mock_row.created_at = datetime.now()
        mock_row.updated_at = datetime.now()
        mock_row.provider_id = 12345  # Has provider ID
        mock_row.version = 2  # Version incremented after approval

        service = CandidateService(Mock())
        response = service._build_response(mock_row)

        assert response.status == "approved"
        assert response.provider_id == 12345
        assert response.version == 2

    def test_all_methods_use_build_response(self):
        """
        DRY TEST: Verify all service methods use _build_response helper
        This ensures code duplication is eliminated
        """
        import inspect
        from src.services.candidate_service import CandidateService

        source = inspect.getsource(CandidateService)

        # Count occurrences of CandidateResponse constructor
        # Should only appear in _build_response method
        direct_constructions = source.count("return CandidateResponse(")

        # Should be exactly 1 (only in _build_response)
        # All other methods should use self._build_response(row)
        assert direct_constructions == 1, \
            f"Found {direct_constructions} CandidateResponse constructions, expected 1 (only in _build_response)"

        # Verify _build_response is called in other methods
        assert "self._build_response(row)" in source or \
               "self._build_response(r)" in source, \
               "_build_response helper not being used"
