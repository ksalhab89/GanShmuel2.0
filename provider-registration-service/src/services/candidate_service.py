"""Business logic for candidate management"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, bindparam, String
from typing import List, Tuple, Optional
from uuid import UUID
from ..models.schemas import CandidateCreate, CandidateResponse
import json


class ConcurrentModificationError(Exception):
    """Raised when optimistic locking detects concurrent modification"""
    pass


class CandidateService:
    """Service for managing provider candidates"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_response(self, row) -> CandidateResponse:
        """Build CandidateResponse from database row (DRY helper)"""
        products = (
            row.products
            if isinstance(row.products, list)
            else (json.loads(row.products) if row.products else [])
        )

        return CandidateResponse(
            candidate_id=row.id,
            status=row.status,
            company_name=row.company_name,
            contact_email=row.contact_email,
            phone=row.phone,
            products=products,
            truck_count=row.truck_count,
            capacity_tons_per_day=row.capacity_tons_per_day,
            location=row.location,
            created_at=row.created_at,
            updated_at=row.updated_at,
            provider_id=row.provider_id,
            version=row.version,
            rejection_reason=row.rejection_reason if hasattr(row, 'rejection_reason') else None
        )

    async def create_candidate(self, data: CandidateCreate) -> CandidateResponse:
        """Create a new candidate in the database"""
        query = text("""
            INSERT INTO candidates (company_name, contact_email, phone, products, truck_count, capacity_tons_per_day, location)
            VALUES (:company_name, :contact_email, :phone, :products, :truck_count, :capacity_tons_per_day, :location)
            RETURNING id, status, company_name, contact_email, phone, products, truck_count, capacity_tons_per_day, location, created_at, updated_at, provider_id, version, rejection_reason
        """)

        result = await self.db.execute(
            query,
            {
                "company_name": data.company_name,
                "contact_email": data.contact_email,
                "phone": data.phone,
                "products": json.dumps(data.products),
                "truck_count": data.truck_count,
                "capacity_tons_per_day": data.capacity_tons_per_day,
                "location": data.location
            }
        )
        await self.db.commit()

        row = result.fetchone()
        return self._build_response(row)

    async def list_candidates(
        self,
        status: Optional[str],
        product: Optional[str],
        limit: int,
        offset: int
    ) -> Tuple[List[CandidateResponse], int]:
        """
        List candidates with SAFE parameterized queries

        SECURITY FIX: Uses NULL-safe conditions instead of dynamic WHERE clause
        No string interpolation - all values passed as parameters

        Args:
            status: Optional status filter (pending, approved, rejected)
            product: Optional product filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of candidates, total count)
        """

        # SAFE: Use NULL-safe conditions with proper parameter binding and explicit types
        # All filtering logic is INSIDE the SQL query, not built dynamically
        # FIXED: Use bindparam with explicit String type to prevent AmbiguousParameterError
        query = text("""
            SELECT id, status, company_name, contact_email, phone, products,
                   truck_count, capacity_tons_per_day, location, created_at, updated_at,
                   provider_id, version, rejection_reason
            FROM candidates
            WHERE (:status IS NULL OR status = :status)
              AND (:product IS NULL OR products @> CAST(:product AS jsonb))
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """).bindparams(
            bindparam("status", type_=String),
            bindparam("product", type_=String)
        )

        # All parameters passed separately - SAFE
        params = {
            "status": status,
            "product": json.dumps([product]) if product else None,
            "limit": limit,
            "offset": offset
        }

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        # SAFE: Count query with same NULL-safe pattern and explicit types
        count_query = text("""
            SELECT COUNT(*) FROM candidates
            WHERE (:status IS NULL OR status = :status)
              AND (:product IS NULL OR products @> CAST(:product AS jsonb))
        """).bindparams(
            bindparam("status", type_=String),
            bindparam("product", type_=String)
        )

        count_params = {
            "status": status,
            "product": json.dumps([product]) if product else None
        }

        total = (await self.db.execute(count_query, count_params)).scalar()

        # Build responses using DRY helper
        candidates = [self._build_response(row) for row in rows]

        return candidates, total

    async def get_candidate(self, candidate_id: UUID) -> Optional[CandidateResponse]:
        """Get a single candidate by ID"""
        query = text("""
            SELECT id, status, company_name, contact_email, phone, products, truck_count, capacity_tons_per_day, location, created_at, updated_at, provider_id, version, rejection_reason
            FROM candidates WHERE id = :id
        """)
        result = await self.db.execute(query, {"id": candidate_id})
        row = result.fetchone()

        if not row:
            return None

        return self._build_response(row)

    async def approve_candidate(
        self,
        candidate_id: UUID,
        provider_id: int,
        expected_version: int
    ) -> CandidateResponse:
        """
        Approve candidate with optimistic locking

        Args:
            candidate_id: UUID of candidate to approve
            provider_id: Provider ID from billing service
            expected_version: Current version for optimistic locking

        Returns:
            Updated candidate response

        Raises:
            ConcurrentModificationError: If version changed (concurrent modification detected)
        """
        query = text("""
            UPDATE candidates
            SET status = 'approved',
                provider_id = :provider_id,
                version = version + 1
            WHERE id = :id
              AND status = 'pending'
              AND version = :expected_version
            RETURNING id, status, company_name, contact_email, phone, products,
                      truck_count, capacity_tons_per_day, location, created_at, updated_at,
                      provider_id, version, rejection_reason
        """)

        result = await self.db.execute(query, {
            "id": candidate_id,
            "provider_id": provider_id,
            "expected_version": expected_version
        })
        await self.db.commit()

        row = result.fetchone()

        if not row:
            # Either: 1) candidate doesn't exist, 2) not pending, or 3) version mismatch
            raise ConcurrentModificationError(
                "Candidate was modified by another process or is no longer pending"
            )

        return self._build_response(row)

    async def reject_candidate(
        self,
        candidate_id: UUID,
        rejection_reason: Optional[str],
        expected_version: int
    ) -> CandidateResponse:
        """
        Reject candidate with optimistic locking

        Args:
            candidate_id: UUID of candidate to reject
            rejection_reason: Optional reason for rejection
            expected_version: Current version for optimistic locking

        Returns:
            Updated candidate response

        Raises:
            ConcurrentModificationError: If version changed (concurrent modification detected)
        """
        query = text("""
            UPDATE candidates
            SET status = 'rejected',
                rejection_reason = :rejection_reason,
                version = version + 1
            WHERE id = :id
              AND status = 'pending'
              AND version = :expected_version
            RETURNING id, status, company_name, contact_email, phone, products,
                      truck_count, capacity_tons_per_day, location, created_at, updated_at,
                      provider_id, version, rejection_reason
        """)

        result = await self.db.execute(query, {
            "id": candidate_id,
            "rejection_reason": rejection_reason,
            "expected_version": expected_version
        })
        await self.db.commit()

        row = result.fetchone()

        if not row:
            # Either: 1) candidate doesn't exist, 2) not pending, or 3) version mismatch
            raise ConcurrentModificationError(
                "Candidate was modified by another process or is no longer pending"
            )

        return self._build_response(row)
