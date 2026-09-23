"""Tests validating Pydantic v2 data contracts across pipeline boundaries."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.models.contracts import (
    ApprovalMode,
    FrictionBreakdown,
    MarketSource,
    NormalizedMarketEvent,
    TradePlan,
    TradeSide,
)
from pydantic import ValidationError


def test_normalized_market_event_valid():
    """Verify valid normalized event creation."""
    event = NormalizedMarketEvent(
        symbol="RELIANCE",
        source=MarketSource.PAPER,
        exchange_timestamp=datetime.now(timezone.utc),
        last_price=Decimal("2500.50"),
        volume=1000,
        bid_price=Decimal("2500.40"),
        ask_price=Decimal("2500.60"),
        bid_quantity=50,
        ask_quantity=80,
        spread_pct=Decimal("0.00008"),
    )
    assert event.symbol == "RELIANCE"
    assert event.spread_pct == Decimal("0.00008")
    assert not event.is_stale


def test_normalized_market_event_negative_spread_rejected():
    """Verify negative spread is rejected by validator."""
    with pytest.raises(ValidationError):
        NormalizedMarketEvent(
            symbol="TCS",
            source=MarketSource.PAPER,
            exchange_timestamp=datetime.now(timezone.utc),
            last_price=Decimal("3500.00"),
            volume=500,
            bid_price=Decimal("3500.00"),
            ask_price=Decimal("3499.00"),
            bid_quantity=10,
            ask_quantity=10,
            spread_pct=Decimal("-0.01"),  # Invalid negative
        )


def test_trade_plan_zero_quantity_rejected():
    """Verify trade plan rejects zero or negative quantity."""
    friction = FrictionBreakdown(
        brokerage=Decimal("0.05"),
        stt=Decimal("0.10"),
        exchange_charges=Decimal("0.02"),
        sebi_charges=Decimal("0.001"),
        stamp_duty=Decimal("0.015"),
        gst=Decimal("0.012"),
        expected_slippage=Decimal("0.05"),
        total_friction=Decimal("0.247"),
    )

    with pytest.raises(ValidationError):
        TradePlan(
            plan_id="plan-001",
            candidate_id="cand-001",
            created_at=datetime.now(timezone.utc),
            symbol="INFY",
            side=TradeSide.BUY,
            quantity=0,  # Invalid quantity
            entry_price_target=Decimal("150.00"),
            hard_stop_price=Decimal("148.00"),
            expected_gross_edge=Decimal("2.00"),
            friction=friction,
            expected_net_edge=Decimal("1.753"),
            decision_reason="Valid momentum breakout",
            approval_mode=ApprovalMode.AUTONOMOUS,
        )
