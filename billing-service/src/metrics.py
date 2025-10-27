"""Basic Prometheus metrics for billing service."""

from prometheus_client import Counter, Gauge, generate_latest
from fastapi.responses import PlainTextResponse


# Basic uptime and health metrics
REQUEST_COUNT = Counter(
    'billing_service_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code']
)

SERVICE_UP = Gauge(
    'billing_service_up',
    'Service is up and running (1 = up, 0 = down)'
)

# Set service as up when module is loaded
SERVICE_UP.set(1)


def record_request_metrics(method: str, endpoint: str, status_code: int):
    """Record basic request metrics."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()


def get_metrics() -> PlainTextResponse:
    """Return Prometheus metrics."""
    return PlainTextResponse(
        generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )