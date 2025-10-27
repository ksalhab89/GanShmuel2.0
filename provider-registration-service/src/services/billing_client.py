"""
Billing service client with production-grade retry logic
Implements exponential backoff and resilience patterns
"""
import httpx
from httpx import Timeout
from typing import Optional
import structlog
import asyncio

from ..config import settings

# Structured logging
logger = structlog.get_logger()


class BillingServiceError(Exception):
    """Exception raised when billing service communication fails"""
    pass


class BillingClient:
    """
    HTTP client for billing service integration with automatic retries

    Features:
    - Exponential backoff (0.5s, 1s, 2s delays)
    - Respects Retry-After headers
    - Retries on 5xx errors and timeouts
    - Does NOT retry on 4xx errors (client mistakes)
    - Structured logging for observability
    """

    def __init__(self):
        self.base_url = settings.billing_service_url
        self.max_retries = 3
        self.backoff_factor = 0.5
        self.retryable_status_codes = {408, 429, 500, 502, 503, 504}

    async def _make_request_with_retry(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries + 1):  # Initial + retries
            try:
                response = await client.request(method, url, **kwargs)

                # Check if we should retry based on status code
                if response.status_code not in self.retryable_status_codes:
                    return response

                # If this is the last attempt, return the response (don't retry further)
                if attempt >= self.max_retries:
                    return response

                # Check for Retry-After header
                retry_after = response.headers.get("retry-after")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        # If not a number, use exponential backoff
                        delay = self.backoff_factor * (2 ** attempt)
                else:
                    # Exponential backoff: 0.5s, 1s, 2s, ...
                    delay = self.backoff_factor * (2 ** attempt)

                logger.info(
                    "billing_service_retry",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    status_code=response.status_code,
                    delay=delay,
                    url=url
                )

                await asyncio.sleep(delay)
                continue

            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = e

                # If this is the last attempt, raise the exception
                if attempt >= self.max_retries:
                    raise

                # Exponential backoff
                delay = self.backoff_factor * (2 ** attempt)

                logger.info(
                    "billing_service_retry_exception",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    exception=type(e).__name__,
                    delay=delay,
                    url=url
                )

                await asyncio.sleep(delay)
                continue

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        return response

    async def create_provider(self, company_name: str) -> int:
        """
        Create provider in billing service with automatic retries

        Args:
            company_name: Name of the provider company

        Returns:
            Provider ID from billing service

        Raises:
            BillingServiceError: If billing service call fails after retries

        Retry Behavior:
        - Retries on 5xx errors (server issues)
        - Retries on timeouts and connection errors
        - Does NOT retry on 4xx errors (client mistakes)
        - Exponential backoff: 0.5s, 1s, 2s between retries
        - Respects server's Retry-After header (for rate limiting)
        """
        url = f"{self.base_url}/provider"

        logger.info(
            "billing_service_request",
            action="create_provider",
            company=company_name
        )

        async with httpx.AsyncClient(
            timeout=Timeout(10.0, connect=5.0)  # 10s total, 5s connect
        ) as client:
            try:
                response = await self._make_request_with_retry(
                    client, "POST", url, json={"name": company_name}
                )

                if response.status_code == 201:
                    data = response.json()
                    provider_id = data["id"]

                    logger.info(
                        "billing_service_success",
                        action="create_provider",
                        provider_id=provider_id,
                        company=company_name
                    )

                    return provider_id
                else:
                    logger.error(
                        "billing_service_error",
                        action="create_provider",
                        status=response.status_code,
                        body=response.text,
                        company=company_name
                    )

                    raise BillingServiceError(
                        f"Billing service returned {response.status_code}: {response.text}"
                    )

            except httpx.TimeoutException as e:
                logger.error(
                    "billing_service_timeout",
                    action="create_provider",
                    error=str(e),
                    company=company_name
                )
                raise BillingServiceError(
                    f"Billing service timeout after retries: {e}"
                )

            except httpx.ConnectError as e:
                logger.error(
                    "billing_service_connection_error",
                    action="create_provider",
                    error=str(e),
                    company=company_name
                )
                raise BillingServiceError(
                    f"Failed to connect to billing service after retries: {e}"
                )

            except httpx.RequestError as e:
                logger.error(
                    "billing_service_request_error",
                    action="create_provider",
                    error=str(e),
                    company=company_name
                )
                raise BillingServiceError(
                    f"Billing service request error: {e}"
                )
