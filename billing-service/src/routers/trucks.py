import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models.repositories import TruckRepository
from ..models.schemas import TruckCreate, TruckDetails, TruckResponse, TruckUpdate
from ..services.weight_client import weight_client
from ..utils.datetime_utils import get_default_date_range
from ..utils.exceptions import NotFoundError, WeightServiceError

logger = logging.getLogger(__name__)
router = APIRouter()
truck_repo = TruckRepository()


@router.post("/truck", response_model=TruckResponse, status_code=201)
async def register_truck(truck_data: TruckCreate):
    """
    Register truck with provider (upsert operation).

    - **id**: Truck ID (max 10 characters)
    - **provider_id**: ID of the provider to associate with

    If truck already exists, updates the provider assignment.
    """
    try:
        truck = await truck_repo.create_or_update(truck_data.id, truck_data.provider_id)
        return TruckResponse(id=truck.id, provider_id=truck.provider_id)

    except NotFoundError as e:
        logger.warning(
            f"Attempt to register truck {truck_data.id} with non-existent provider {truck_data.provider_id}"
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering truck: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/truck/{truck_id}", response_model=TruckResponse)
async def update_truck(truck_id: str, truck_data: TruckUpdate):
    """
    Update truck's provider assignment.

    - **truck_id**: ID of the truck to update
    - **provider_id**: New provider ID to assign
    """
    try:
        truck = await truck_repo.update(truck_id, truck_data.provider_id)
        return TruckResponse(id=truck.id, provider_id=truck.provider_id)

    except NotFoundError as e:
        logger.warning(f"Attempt to update truck {truck_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating truck {truck_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/truck/{truck_id}", response_model=TruckDetails)
async def get_truck_details(
    truck_id: str, from_: Optional[str] = None, to: Optional[str] = None
):
    """
    Get truck details and sessions from Weight Service.

    - **truck_id**: ID of the truck to retrieve
    - **from**: Start date in yyyymmddhhmmss format (default: 1st of month 000000)
    - **to**: End date in yyyymmddhhmmss format (default: now)

    Returns truck tare weight and associated session UUIDs.
    """
    try:
        # Check if truck exists in billing database
        truck = await truck_repo.get_by_id(truck_id)
        if not truck:
            raise HTTPException(status_code=404, detail="Truck not found")

        # Get default date range
        from_date, to_date = get_default_date_range(from_, to)

        # Get truck details from weight service
        try:
            weight_item = await weight_client.get_item_details(
                truck_id, from_date, to_date
            )

            if weight_item is None:
                raise HTTPException(
                    status_code=404, detail="Truck not found in weight service"
                )

            return TruckDetails(
                id=weight_item.id, tara=weight_item.tara, sessions=weight_item.sessions
            )

        except HTTPException:
            # Re-raise HTTPExceptions (like 404)
            raise
        except WeightServiceError as e:
            logger.error(f"Weight service error for truck {truck_id}: {e}")
            raise HTTPException(status_code=503, detail="Weight service unavailable")
        except Exception as e:
            logger.error(f"Error fetching truck details from weight service: {e}")
            raise HTTPException(status_code=503, detail="Weight service unavailable")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting truck details for {truck_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
