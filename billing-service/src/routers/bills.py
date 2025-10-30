import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import BillResponse
from ..services.bill_service import bill_service
from ..utils.datetime_utils import get_default_date_range
from ..utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/bill/{provider_id}", response_model=BillResponse)
async def generate_bill(
    provider_id: int,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
):
    """
    Generate provider invoice (MAIN BUSINESS LOGIC).

    - **provider_id**: ID of the provider (required)
    - **from**: Start date in yyyymmddhhmmss format (default: 1st of month 000000)
    - **to**: End date in yyyymmddhhmmss format (default: now)

    Calculates bill based on:
    1. Provider's registered trucks
    2. Weight transactions for those trucks in date range
    3. Rate precedence (provider-specific > ALL scope)
    4. Net weight calculations and payment totals

    Returns detailed bill with product breakdown and totals.
    """
    try:
        # Get default date range if not provided
        from_date, to_date = get_default_date_range(from_, to)

        # Generate bill using the bill service
        bill = await bill_service.generate_bill(provider_id, from_date, to_date)

        logger.info(
            f"Generated bill for provider {provider_id}: {bill.total} agorot total"
        )
        return bill

    except NotFoundError as e:
        logger.warning(
            f"Attempt to generate bill for non-existent provider: {provider_id}"
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating bill for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
