import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from ..models.database import WeightItem
from ..utils.exceptions import WeightServiceError

logger = logging.getLogger(__name__)


class WeightServiceClient:
    """Client for communicating with the Weight Service."""

    def __init__(self):
        self.base_url = settings.weight_service_url
        self.timeout = settings.weight_service_timeout
        self.max_retries = settings.weight_service_retries

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict[Any, Any]]:
        """Make HTTP request to weight service with retry logic."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, **kwargs)

                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 404:
                        return None
                    else:
                        logger.warning(
                            f"Weight service returned {response.status_code} for {endpoint}"
                        )

            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1} for {endpoint}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                continue
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1} for {endpoint}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                continue

        # All retries failed
        raise WeightServiceError(
            f"Weight service unavailable after {self.max_retries} attempts"
        )

    async def get_item_details(
        self, item_id: str, from_date: str, to_date: str
    ) -> Optional[WeightItem]:
        """
        Get truck/container details from weight service.

        Args:
            item_id: Truck or container ID
            from_date: Start date in yyyymmddhhmmss format
            to_date: End date in yyyymmddhhmmss format

        Returns:
            WeightItem with tare and sessions, or None if not found
        """
        try:
            params = {"from": from_date, "to": to_date}

            response_data = await self._make_request(
                "GET", f"/item/{item_id}", params=params
            )

            if response_data is None:
                return None

            return WeightItem(
                id=response_data.get("id", item_id),
                tara=response_data.get("tara", "na"),
                sessions=response_data.get("sessions", []),
            )

        except WeightServiceError:
            raise
        except Exception as e:
            logger.error(
                f"Error parsing weight service response for item {item_id}: {e}"
            )
            raise WeightServiceError("Error processing weight service response")

    async def get_transactions(
        self, from_date: str, to_date: str, filter_directions: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get weight transactions from weight service.

        Args:
            from_date: Start date in yyyymmddhhmmss format
            to_date: End date in yyyymmddhhmmss format
            filter_directions: Comma-separated directions (in, out, none)

        Returns:
            List of transaction dictionaries
        """
        try:
            params = {"from": from_date, "to": to_date}

            if filter_directions:
                params["filter"] = filter_directions

            response_data = await self._make_request("GET", "/weight", params=params)

            if response_data is None:
                return []

            return response_data if isinstance(response_data, list) else []

        except WeightServiceError:
            raise
        except Exception as e:
            logger.error(f"Error parsing weight service transactions response: {e}")
            raise WeightServiceError("Error processing weight service response")


# Global weight service client instance
weight_client = WeightServiceClient()
