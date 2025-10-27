from fastapi import APIRouter, HTTPException
from ..models.schemas import ProviderCreate, ProviderUpdate, ProviderResponse
from ..models.repositories import ProviderRepository
from ..utils.exceptions import NotFoundError, DuplicateError
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
provider_repo = ProviderRepository()


@router.post("/provider", response_model=ProviderResponse, status_code=201)
async def create_provider(provider_data: ProviderCreate):
    """
    Create a new provider.
    
    - **name**: Provider name (required, must be unique)
    
    Returns the created provider with ID and name.
    """
    try:
        provider = await provider_repo.create(provider_data.name)
        return ProviderResponse(id=provider.id, name=provider.name)
        
    except DuplicateError as e:
        logger.warning(f"Attempt to create duplicate provider: {provider_data.name}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating provider: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/provider/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: int, provider_data: ProviderUpdate):
    """
    Update an existing provider's name.
    
    - **provider_id**: ID of the provider to update
    - **name**: New provider name (required, must be unique)
    
    Returns the updated provider with ID and name.
    """
    try:
        provider = await provider_repo.update(provider_id, provider_data.name)
        return ProviderResponse(id=provider.id, name=provider.name)
        
    except NotFoundError as e:
        logger.warning(f"Attempt to update non-existent provider: {provider_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateError as e:
        logger.warning(f"Attempt to update provider {provider_id} with duplicate name: {provider_data.name}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")