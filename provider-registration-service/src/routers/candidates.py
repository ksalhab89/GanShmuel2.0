"""API endpoints for candidate management"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ..models.schemas import CandidateCreate, CandidateResponse, CandidateList, ApprovalResponse, RejectionRequest, RejectionResponse
from ..services.candidate_service import CandidateService, ConcurrentModificationError
from ..services.billing_client import BillingClient, BillingServiceError
from ..database import get_db
from ..auth.jwt_handler import require_admin

router = APIRouter()


def get_candidate_service(db: AsyncSession = Depends(get_db)) -> CandidateService:
    """Dependency for getting candidate service"""
    return CandidateService(db)


def get_billing_client() -> BillingClient:
    """Dependency for getting billing client"""
    return BillingClient()


@router.post("/candidates", response_model=CandidateResponse, status_code=201)
async def create_candidate(
    candidate: CandidateCreate,
    service: CandidateService = Depends(get_candidate_service)
) -> CandidateResponse:
    """
    Register a new provider candidate

    Creates a new candidate with status='pending'.
    Validates that products are in allowed list and truck_count/capacity > 0.
    """
    try:
        return await service.create_candidate(candidate)
    except IntegrityError as e:
        # Handle duplicate email constraint violation
        if "contact_email" in str(e):
            raise HTTPException(
                status_code=409,
                detail="A candidate with this email already exists"
            )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/candidates", response_model=CandidateList)
async def list_candidates(
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected)"),
    product: Optional[str] = Query(None, description="Filter by product"),
    # Support both page/page_size (frontend) and limit/offset (direct API usage)
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Results per page"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Number of results per page (legacy)"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip (legacy)"),
    service: CandidateService = Depends(get_candidate_service)
) -> CandidateList:
    """
    List candidates with filtering and pagination

    Supports filtering by:
    - status: pending, approved, or rejected
    - product: filter candidates who supply this product

    Supports two pagination formats:
    1. page + page_size (recommended for frontend)
    2. limit + offset (legacy, direct API usage)

    Returns paginated results with total count.
    """
    # Convert page/page_size to limit/offset if provided
    if page is not None and page_size is not None:
        actual_limit = page_size
        actual_offset = (page - 1) * page_size
    else:
        # Use limit/offset (with defaults)
        actual_limit = limit if limit is not None else 20
        actual_offset = offset if offset is not None else 0

    candidates, total = await service.list_candidates(status, product, actual_limit, actual_offset)
    return CandidateList(
        candidates=candidates,
        pagination={"total": total, "limit": actual_limit, "offset": actual_offset}
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: UUID,
    service: CandidateService = Depends(get_candidate_service)
) -> CandidateResponse:
    """
    Get a single candidate by ID

    Returns candidate details including:
    - candidate_id, company_name, contact info
    - products, capacity, location
    - status and provider_id (if approved)
    """
    candidate = await service.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.post("/candidates/{candidate_id}/approve", response_model=ApprovalResponse)
async def approve_candidate(
    candidate_id: UUID,
    service: CandidateService = Depends(get_candidate_service),
    billing_client: BillingClient = Depends(get_billing_client),
    current_user: dict = Depends(require_admin)
) -> ApprovalResponse:
    """
    Approve candidate and create provider in billing service (with optimistic locking) - ADMIN ONLY

    Workflow:
    1. Get candidate from database (including version)
    2. Verify candidate exists and is pending
    3. Create provider in billing service
    4. Update candidate status to approved with provider_id (optimistic lock check)
    5. Return approval response

    Returns:
        ApprovalResponse with candidate_id, status, and provider_id

    Raises:
        404: Candidate not found
        400: Candidate already approved/rejected
        409: Concurrent modification detected (optimistic lock failure)
        502: Billing service error
    """
    # 1. Get candidate with current version
    candidate = await service.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.status != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Candidate already {candidate.status}"
        )

    # 2. Create provider in billing service
    try:
        provider_id = await billing_client.create_provider(candidate.company_name)
    except BillingServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to create provider: {str(e)}")

    # 3. Update candidate with version check (optimistic locking)
    try:
        updated = await service.approve_candidate(
            candidate_id,
            provider_id,
            expected_version=candidate.version
        )

        return ApprovalResponse(
            candidate_id=updated.candidate_id,
            status=updated.status,
            provider_id=updated.provider_id
        )

    except ConcurrentModificationError:
        # Concurrent modification detected - another process changed the candidate
        raise HTTPException(
            status_code=409,
            detail="Candidate was modified by another process. Please retry."
        )


@router.post("/candidates/{candidate_id}/reject", response_model=RejectionResponse)
async def reject_candidate(
    candidate_id: UUID,
    rejection_data: RejectionRequest,
    service: CandidateService = Depends(get_candidate_service),
    current_user: dict = Depends(require_admin)
) -> RejectionResponse:
    """
    Reject candidate with optimistic locking - ADMIN ONLY

    Workflow:
    1. Get candidate from database (including version)
    2. Verify candidate exists and is pending
    3. Update candidate status to rejected with optional reason (optimistic lock check)
    4. Return rejection response

    Returns:
        RejectionResponse with candidate_id, status, and rejection_reason

    Raises:
        404: Candidate not found
        400: Candidate already approved/rejected
        409: Concurrent modification detected (optimistic lock failure)
        403: Not admin (handled by require_admin dependency)
        401: Not authenticated (handled by require_admin dependency)
    """
    # 1. Get candidate with current version
    candidate = await service.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.status != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Candidate already {candidate.status}"
        )

    # 2. Update candidate with version check (optimistic locking)
    try:
        updated = await service.reject_candidate(
            candidate_id,
            rejection_reason=rejection_data.reason,
            expected_version=candidate.version
        )

        return RejectionResponse(
            candidate_id=updated.candidate_id,
            status=updated.status,
            rejection_reason=updated.rejection_reason
        )

    except ConcurrentModificationError:
        # Concurrent modification detected - another process changed the candidate
        raise HTTPException(
            status_code=409,
            detail="Candidate was modified by another process. Please retry."
        )
