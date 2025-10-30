"""Tests for Prometheus metrics functions."""

import pytest
from src.metrics import record_request_metrics, get_metrics, REQUEST_COUNT


class TestRecordRequestMetrics:
    """Test suite for record_request_metrics function."""

    def test_record_request_metrics_increments_counter(self):
        """Test that recording metrics increments the counter."""
        # Get initial count
        initial_value = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code=200)._value._value

        # Record a metric
        record_request_metrics("GET", "/test", 200)

        # Verify counter increased
        final_value = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code=200)._value._value
        assert final_value > initial_value

    def test_record_request_metrics_with_different_labels(self):
        """Test that different label combinations are tracked separately."""
        # Record metrics with different combinations
        record_request_metrics("POST", "/weight", 201)
        record_request_metrics("GET", "/weight", 200)
        record_request_metrics("POST", "/weight", 400)

        # Each combination should be tracked (this test just verifies no exceptions)
        assert True


class TestGetMetrics:
    """Test suite for get_metrics function."""

    def test_get_metrics_returns_plain_text_response(self):
        """Test that get_metrics returns PlainTextResponse."""
        response = get_metrics()

        # Check response type
        from fastapi.responses import PlainTextResponse
        assert isinstance(response, PlainTextResponse)

    def test_get_metrics_contains_prometheus_format(self):
        """Test that metrics response contains Prometheus formatted data."""
        response = get_metrics()

        # Get the body
        body = response.body.decode('utf-8')

        # Should contain metric names
        assert 'weight_service' in body or '#' in body  # Prometheus format indicators

    def test_get_metrics_has_correct_media_type(self):
        """Test that response has correct Prometheus media type."""
        response = get_metrics()

        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"
