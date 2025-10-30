import os
from io import BytesIO
from typing import List

import pandas as pd
from fastapi import UploadFile

from ..config import settings
from ..models.database import Rate
from ..utils.exceptions import FileError


def read_rates_from_excel(filename: str) -> List[Rate]:
    """
    Read rates from Excel file in the upload directory.

    Args:
        filename: Name of the Excel file

    Returns:
        List of Rate objects

    Raises:
        FileError: If file not found or invalid format
    """
    file_path = os.path.join(settings.upload_directory, filename)

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileError(f"File {filename} not found in /in directory")

    # Check file extension
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise FileError("File must be Excel format")

    try:
        # Read Excel file
        df = pd.read_excel(file_path)

        # Check required columns
        required_columns = ["Product", "Rate", "Scope"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise FileError(f"Excel file must contain columns: {required_columns}")

        # Convert to Rate objects
        rates = []
        for _, row in df.iterrows():
            rates.append(
                Rate(
                    product_id=str(row["Product"]).strip(),
                    rate=int(row["Rate"]),
                    scope=str(row["Scope"]).strip(),
                )
            )

        return rates

    except pd.errors.EmptyDataError:
        raise FileError("Excel file is empty")
    except pd.errors.ParserError as e:
        raise FileError(f"Error parsing Excel file: {str(e)}")
    except ValueError as e:
        raise FileError(f"Invalid data in Excel file: {str(e)}")
    except Exception as e:
        raise FileError(f"Error reading Excel file: {str(e)}")


async def read_rates_from_file(file: UploadFile) -> List[Rate]:
    """
    Read rates from uploaded Excel file.

    Args:
        file: FastAPI UploadFile object

    Returns:
        List of Rate objects

    Raises:
        FileError: If file is invalid format or contains errors
    """
    try:
        # Read file content
        content = await file.read()

        # Check file extension
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise FileError("File must be Excel format")

        # Read Excel file from memory
        df = pd.read_excel(BytesIO(content))

        # Check required columns
        required_columns = ["Product", "Rate", "Scope"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise FileError(f"Excel file must contain columns: {required_columns}")

        # Convert to Rate objects
        rates = []
        for _, row in df.iterrows():
            try:
                # Ensure all values are properly converted and cleaned
                product_id = str(row["Product"]).strip()
                rate = int(float(row["Rate"]))  # Handle potential float values
                scope = str(row["Scope"]).strip()

                # Validate that strings don't contain problematic characters
                if not product_id or not scope:
                    continue  # Skip empty rows

                rates.append(Rate(product_id=product_id, rate=rate, scope=scope))
            except (ValueError, TypeError) as e:
                raise FileError(f"Invalid data in row {len(rates) + 1}: {str(e)}")

        return rates

    except pd.errors.EmptyDataError:
        raise FileError("Excel file is empty")
    except pd.errors.ParserError as e:
        raise FileError(f"Error parsing Excel file: {str(e)}")
    except ValueError as e:
        raise FileError(f"Invalid data in Excel file: {str(e)}")
    except Exception as e:
        raise FileError(f"Error reading Excel file: {str(e)}")


def create_rates_excel(rates: List[Rate]) -> BytesIO:
    """
    Create Excel file from rates data.

    Args:
        rates: List of Rate objects

    Returns:
        BytesIO object containing Excel file data
    """
    # Convert rates to DataFrame
    data = []
    for rate in rates:
        data.append(
            {"Product": rate.product_id, "Rate": rate.rate, "Scope": rate.scope}
        )

    df = pd.DataFrame(data)

    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rates")

    output.seek(0)
    return output
