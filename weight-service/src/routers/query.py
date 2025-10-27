"""Query and reporting endpoints."""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..dependencies import DatabaseSession, get_query_service, get_session_service, get_container_service
from ..models.schemas import (
    ItemResponse,
    SessionResponse,
    TransactionResponse,
    WeightQueryParams,
)
from ..services.query_service import QueryService
from ..services.session_service import SessionService
from ..services.container_service import ContainerService
from ..utils.exceptions import InvalidDateRangeError

router = APIRouter(tags=["Query Operations"])


@router.get("/weight", response_model=List[TransactionResponse])
async def query_weighings(
    from_datetime: Annotated[Optional[str], Query(alias="from")] = None,
    to_datetime: Annotated[Optional[str], Query(alias="to")] = None,
    filter_directions: Annotated[Optional[str], Query(alias="filter")] = None,
    query_service: Annotated[QueryService, Depends(get_query_service)] = ...,
    db: DatabaseSession = ...,
) -> List[TransactionResponse]:
    """
    Query weighing transactions with optional filters.
    
    **Parameters:**
    - **from**: Start datetime in yyyymmddhhmmss format (default: today 000000)
    - **to**: End datetime in yyyymmddhhmmss format (default: now)
    - **filter**: Comma-separated directions (in,out,none)
    
    **Returns:** List of transactions sorted by datetime
    
    **Date Format:** All dates must be in yyyymmddhhmmss format (e.g., 20241201120000)
    """
    try:
        # Create query parameters
        params = WeightQueryParams(
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            filter_directions=filter_directions,
        )
        
        # Execute query
        transactions = await query_service.query_transactions(params)
        
        return transactions
        
    except InvalidDateRangeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date range: {str(e)}"
        ) from e
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid query parameters: {str(e)}"
        ) from e
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get("/item/{item_id}", response_model=ItemResponse)
async def get_item_details(
    item_id: str,
    from_datetime: Annotated[Optional[str], Query(alias="from")] = None,
    to_datetime: Annotated[Optional[str], Query(alias="to")] = None,
    query_service: Annotated[QueryService, Depends(get_query_service)] = ...,
    db: DatabaseSession = ...,
) -> ItemResponse:
    """
    Get details for a specific truck or container.
    
    **Parameters:**
    - **item_id**: Truck license or container ID
    - **from**: Start datetime for session history (optional)
    - **to**: End datetime for session history (optional)
    
    **Returns:** Item information with session history and last known tare weight
    
    The system automatically detects if the ID is a truck or container.
    """
    try:
        # Get item information
        item_info = await query_service.get_item_info(
            item_id=item_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )
        
        if not item_info:
            raise HTTPException(
                status_code=404,
                detail=f"Item '{item_id}' not found"
            )
        
        return item_info
        
    except InvalidDateRangeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date range: {str(e)}"
        ) from e
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)] = ...,
    db: DatabaseSession = ...,
) -> SessionResponse:
    """
    Get details for a specific weighing session.
    
    **Parameters:**
    - **session_id**: UUID of the weighing session
    
    **Returns:** Session information including:
    - Session ID and associated truck
    - Gross weight (bruto) information
    - Truck tare weight (for OUT sessions)
    - Net weight calculation (for completed sessions)
    """
    try:
        # Get session details
        session_info = await session_service.get_session_details(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' not found"
            )
        
        return session_info
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session ID format: {str(e)}"
        ) from e
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get("/unknown", response_model=List[str])
async def list_unknown_containers(
    container_service: Annotated[ContainerService, Depends(get_container_service)] = ...,
    db: DatabaseSession = ...,
) -> List[str]:
    """
    List containers that appear in transactions but are not registered.
    
    **Returns:** Array of unknown container IDs
    
    This endpoint scans all transaction container lists and cross-references
    with registered containers to identify containers that need weight registration.
    """
    try:
        # Find unknown containers
        unknown_containers = await container_service.find_unknown_containers()
        
        return unknown_containers
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) from e