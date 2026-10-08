"""Unit tests for metrics adapters and request-context propagation."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from pg_mcp.observability.logging import configure_logging
from pg_mcp.observability.metrics import MetricsCollector
from pg_mcp.observability.tracing import (
    clear_request_id,
    get_request_id,
    request_context,
    set_request_id,
)


def test_configure_logging_uses_stderr_for_stdio_protocol() -> None:
    """Application logs must not corrupt MCP JSON-RPC messages on stdout."""
    root_logger = MagicMock()
    root_logger.handlers = []

    with (
        patch("pg_mcp.observability.logging.logging.getLogger", return_value=root_logger),
        patch("pg_mcp.observability.logging.logging.StreamHandler") as stream_handler,
    ):
        configure_logging()

    stream_handler.assert_called_once_with(sys.stderr)


def test_metrics_collector_forwards_business_events() -> None:
    """Metrics helper methods must update their corresponding Prometheus metric."""
    collector = MetricsCollector()
    query_requests = MagicMock()
    llm_calls = MagicMock()
    llm_latency = MagicMock()
    db_duration = MagicMock()
    sql_rejected = MagicMock()

    with (
        patch.object(collector, "query_requests", query_requests),
        patch.object(collector, "llm_calls", llm_calls),
        patch.object(collector, "llm_latency", llm_latency),
        patch.object(collector, "db_query_duration", db_duration),
        patch.object(collector, "sql_rejected", sql_rejected),
    ):
        collector.increment_query_request("success", "analytics")
        collector.increment_llm_call("generate_sql")
        collector.observe_llm_latency("generate_sql", 0.25)
        collector.observe_db_query_duration(0.1)
        collector.increment_sql_rejected("SecurityViolationError")

    query_requests.labels.assert_called_once_with(status="success", database="analytics")
    query_requests.labels.return_value.inc.assert_called_once_with()
    llm_calls.labels.return_value.inc.assert_called_once_with()
    llm_latency.labels.return_value.observe.assert_called_once_with(0.25)
    db_duration.observe.assert_called_once_with(0.1)
    sql_rejected.labels.return_value.inc.assert_called_once_with()


@pytest.mark.asyncio
async def test_request_context_propagates_and_restores_request_id() -> None:
    """Request IDs must be visible inside a request and restored afterwards."""
    clear_request_id()
    assert get_request_id() is None

    set_request_id("outer")
    async with request_context("inner") as request_id:
        assert request_id == "inner"
        assert get_request_id() == "inner"

    assert get_request_id() == "outer"
    clear_request_id()
