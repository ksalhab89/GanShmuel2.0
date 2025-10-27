"""Batch upload endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import DatabaseSession, get_file_service
from ..models.schemas import BatchWeightRequest, BatchUploadResponse
from ..services.file_service import FileService
from ..utils.exceptions import FileProcessingError

router = APIRouter(tags=["Batch Operations"])


@router.post("/batch-weight", response_model=BatchUploadResponse)
async def upload_batch_weights(
    request: BatchWeightRequest,
    file_service: Annotated[FileService, Depends(get_file_service)],
    db: DatabaseSession,
) -> BatchUploadResponse:
    """
    Upload container weights from CSV or JSON file.
    
    Supported file formats:
    - **CSV**: id,kg or id,lbs format with optional headers
    - **JSON**: [{"id":"C001","weight":50,"unit":"kg"}] format
    
    The file must exist in the `/in` directory and have valid format.
    Processing supports partial success - invalid rows are skipped with detailed error reporting.
    
    **Security**: File paths are validated to prevent directory traversal attacks.
    """
    try:
        # Process the batch file
        result = await file_service.process_batch_file(
            filename=request.file
        )
        
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail=f"File not found: {str(e)}"
        ) from e
        
    except FileProcessingError as e:
        raise HTTPException(
            status_code=422,
            detail=f"File processing error: {str(e)}"
        ) from e
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format: {str(e)}"
        ) from e
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) from e