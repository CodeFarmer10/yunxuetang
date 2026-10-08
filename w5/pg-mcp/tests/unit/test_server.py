"""Unit tests for server wiring and the public MCP query entry point."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pg_mcp.server as server
from pg_mcp.config.settings import (
    DatabaseConfig,
    ObservabilityConfig,
    OpenAIConfig,
    SecurityConfig,
    Settings,
)
from pg_mcp.models.query import QueryResponse
from pg_mcp.models.schema import DatabaseSchema


@pytest.mark.asyncio
async def test_lifespan_wires_multiple_databases_and_security_policy() -> None:
    """Startup must create one executor per database and inject runtime controls."""
    settings = Settings(
        openai=OpenAIConfig(api_key="sk-test"),
        databases=[
            DatabaseConfig(name="analytics"),
            DatabaseConfig(name="operations"),
        ],
        security=SecurityConfig(
            blocked_tables=["secrets"],
            blocked_columns=["users.password"],
            allow_explain=True,
        ),
        observability=ObservabilityConfig(metrics_enabled=False),
    )
    pools = [MagicMock(name="analytics_pool"), MagicMock(name="operations_pool")]
    create_pool = AsyncMock(side_effect=pools)
    close_pools = AsyncMock()
    cache = MagicMock()
    cache.load = AsyncMock(
        side_effect=[
            DatabaseSchema(database_name="analytics"),
            DatabaseSchema(database_name="operations"),
        ]
    )
    cache.stop_auto_refresh = AsyncMock()
    validator = MagicMock()
    sql_validator = MagicMock(return_value=validator)
    executors = [MagicMock(name="analytics_executor"), MagicMock(name="operations_executor")]
    sql_executor = MagicMock(side_effect=executors)
    orchestrator = MagicMock()
    orchestrator_factory = MagicMock(return_value=orchestrator)
    metrics = MagicMock()

    with (
        patch.object(server, "Settings", return_value=settings),
        patch.object(server, "create_pool", create_pool),
        patch.object(server, "close_pools", close_pools),
        patch.object(server, "SchemaCache", return_value=cache),
        patch.object(server, "SQLGenerator", return_value=MagicMock()),
        patch.object(server, "SQLValidator", sql_validator),
        patch.object(server, "SQLExecutor", sql_executor),
        patch.object(server, "ResultValidator", return_value=MagicMock()),
        patch.object(server, "QueryOrchestrator", orchestrator_factory),
        patch.object(server, "MetricsCollector", return_value=metrics),
    ):
        async with server.lifespan(server.mcp):
            assert server._orchestrator is orchestrator

    assert create_pool.await_count == 2
    assert cache.load.await_count == 2
    sql_validator.assert_called_once_with(
        config=settings.security,
        blocked_tables=["secrets"],
        blocked_columns=["users.password"],
        allow_explain=True,
    )
    assert sql_executor.call_count == 2
    call = orchestrator_factory.call_args.kwargs
    assert call["sql_executors"] == {
        "analytics": executors[0],
        "operations": executors[1],
    }
    assert call["rate_limiter"] is server._rate_limiter
    assert call["metrics"] is metrics
    close_pools.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_returns_stable_response_from_orchestrator() -> None:
    """The public tool must serialize the orchestrator response consistently."""
    orchestrator = MagicMock()
    orchestrator.execute_query = AsyncMock(
        return_value=QueryResponse(success=True, generated_sql="SELECT 1")
    )
    server._orchestrator = orchestrator

    result = await server.query("Return one", database="analytics", return_type="sql")

    assert result["success"] is True
    assert result["generated_sql"] == "SELECT 1"
    assert result["tokens_used"] == 0


@pytest.mark.asyncio
async def test_query_rejects_invalid_inputs_and_uninitialized_server() -> None:
    """Entry-point validation errors must be structured and must not raise."""
    server._orchestrator = None
    uninitialized = await server.query("Return one")
    assert uninitialized["error"]["code"] == "SERVER_NOT_INITIALIZED"

    server._orchestrator = MagicMock()
    invalid_type = await server.query("Return one", return_type="csv")
    assert invalid_type["error"]["code"] == "INVALID_PARAMETER"

    invalid_request = await server.query("   ")
    assert invalid_request["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_query_converts_unexpected_orchestrator_error() -> None:
    """Unexpected orchestration failures must remain inside the MCP response contract."""
    orchestrator = MagicMock()
    orchestrator.execute_query = AsyncMock(side_effect=RuntimeError("boom"))
    server._orchestrator = orchestrator

    result = await server.query("Return one")

    assert result["success"] is False
    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert result["tokens_used"] == 0
