"""Prometheus metrics for monitoring"""

from prometheus_client import Counter, Gauge, generate_latest

# Service uptime metric (1 = up, 0 = down)
SERVICE_UP = Gauge(
    'provider_service_up',
    'Service is up and running (1 = up, 0 = down)'
)

# Request counter with labels
REQUEST_COUNT = Counter(
    'provider_service_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code']
)

# Initialize service as up
SERVICE_UP.set(1)


def record_request_metrics(method: str, endpoint: str, status_code: int):
    """Record request metrics for Prometheus"""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()


def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest()
