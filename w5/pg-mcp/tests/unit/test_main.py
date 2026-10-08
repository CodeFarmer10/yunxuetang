"""Unit tests for the pg-mcp command-line entry point."""

from unittest.mock import patch

from pg_mcp.__main__ import main


def test_main_treats_keyboard_interrupt_as_normal_shutdown() -> None:
    """Ctrl+C should stop the local server without printing a traceback."""
    with patch("pg_mcp.__main__.anyio.run", side_effect=KeyboardInterrupt):
        main()
