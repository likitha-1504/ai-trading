"""Sanity test verifying test framework and configuration loads cleanly."""

from app.core.config import settings


def test_configuration_sanity():
    """Verify that configuration settings load and capital limits are enforced."""
    assert settings.PROJECT_NAME == "AI Micro-Trading Agent"
    assert settings.INITIAL_CAPITAL == 100.0
    assert settings.AUTONOMOUS_CAPITAL_THRESHOLD == 300.0
    assert settings.IS_PAPER_TRADING is True
