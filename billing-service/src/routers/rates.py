import logging
from typing import List, Union

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from ..models.repositories import RateRepository
from ..models.schemas import Rate, RateUpload, RateUploadResponse
from ..utils.excel_handler import (
    create_rates_excel,
    read_rates_from_excel,
    read_rates_from_file,
)
from ..utils.exceptions import FileError

logger = logging.getLogger(__name__)
router = APIRouter()
rate_repo = RateRepository()


@router.post("/rates", response_model=RateUploadResponse)
async def upload_rates(file: UploadFile = File(...)):
    """
    Upload rates from Excel file.

    - **file**: Excel file with rates data

    Excel format should have columns: Product, Rate, Scope

    This operation clears existing rates and inserts new ones from the file.
    """
    try:
        # Read rates from uploaded Excel file
        rates = await read_rates_from_file(file)

        # Clear existing rates and insert new ones
        await rate_repo.clear_all()
        count = await rate_repo.create_batch(rates)

        logger.info(f"Successfully uploaded {count} rates from {file.filename}")
        return RateUploadResponse(message=f"Successfully uploaded {count} rates")

    except FileError as e:
        logger.warning(f"File error during rate upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading rates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/rates/from-directory", response_model=RateUploadResponse)
async def upload_rates_from_directory(rate_upload: RateUpload):
    """
    Upload rates from Excel file in /in directory.

    - **file**: Filename of Excel file in /in directory

    Excel format should have columns: Product, Rate, Scope

    This operation clears existing rates and inserts new ones from the file.
    """
    try:
        # Read rates from Excel file
        rates = read_rates_from_excel(rate_upload.file)

        # Clear existing rates and insert new ones
        await rate_repo.clear_all()
        count = await rate_repo.create_batch(rates)

        logger.info(f"Successfully uploaded {count} rates from {rate_upload.file}")
        return RateUploadResponse(message=f"Successfully uploaded {count} rates")

    except FileError as e:
        logger.warning(f"File error during rate upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading rates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/rates", response_model=Union[List[Rate], None])
async def get_rates(
    format: str = Query("excel", description="Response format: 'json' or 'excel'")
):
    """
    Get current rates in JSON format or download as Excel file.

    - **format**: Response format - 'json' for JSON list, 'excel' for Excel download (default: excel)

    JSON format returns:
    [
        {
            "product_id": "Apples",
            "rate": 150,
            "scope": "ALL"
        }
    ]

    Excel format returns an Excel file download with columns: Product, Rate, Scope
    """
    try:
        # Get all rates from database
        rates = await rate_repo.get_all()

        if format.lower() == "json":
            # Return JSON response
            logger.info(f"Returning {len(rates)} rates as JSON")
            return rates
        else:
            # Default to Excel format
            # Create Excel file
            excel_file = create_rates_excel(rates)

            logger.info(f"Generated Excel file with {len(rates)} rates")

            # Return as file download
            return StreamingResponse(
                iter([excel_file.read()]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=rates.xlsx"},
            )

    except Exception as e:
        logger.error(f"Error getting rates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
