"""Unit tests for result-validator provider configuration."""

from unittest.mock import patch

from pydantic import SecretStr

from pg_mcp.config.settings import OpenAIConfig, ValidationConfig
from pg_mcp.services.result_validator import ResultValidator


def test_custom_openai_compatible_endpoint_is_used() -> None:
    """Test that result validation uses the same custom provider endpoint."""
    openai_config = OpenAIConfig(
        api_key=SecretStr("volcengine-key"),
        base_url="https://ark.cn-beijing.volces.com/api/coding/v3",
        model="ark-code-latest",
    )

    with patch("pg_mcp.services.result_validator.AsyncOpenAI") as mock_client:
        ResultValidator(openai_config, ValidationConfig())

    mock_client.assert_called_once_with(
        api_key="volcengine-key",
        base_url="https://ark.cn-beijing.volces.com/api/coding/v3",
        timeout=10.0,
    )
