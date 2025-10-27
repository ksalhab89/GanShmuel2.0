"""Weight recording endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import DatabaseSession, get_weight_service
from ..models.schemas import WeightRequest, WeightResponse
from ..services.weight_service import WeightService
from ..utils.exceptions import (
    ContainerNotFoundError,
    InvalidWeightError,
    WeighingSequenceError,
)

router = APIRouter(tags=["Weight Operations"])


@router.post("/weight", response_model=WeightResponse)
async def record_weight(
    request: WeightRequest,
    weight_service: Annotated[WeightService, Depends(get_weight_service)],
    db: DatabaseSession,
) -> WeightResponse:
    """
    Record a weighing operation.
    
    Supports three directions:
    - **in**: New session creation, records gross weight
    - **out**: Complete existing session, calculate net weight  
    - **none**: Standalone weighing (containers only)
    
    The system enforces business rules:
    - OUT requires matching IN session (unless force=true)
    - Weight values must be positive
    - Container IDs must be properly formatted
    """
    try:
        # Record the weight operation
        result, error = await weight_service.record_weight(request)
        
        return result
        
    except WeighingSequenceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid weighing sequence: {str(e)}"
        ) from e
        
    except ContainerNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Container not found: {str(e)}"
        ) from e
        
    except InvalidWeightError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid weight value: {str(e)}"
        ) from e
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) from e