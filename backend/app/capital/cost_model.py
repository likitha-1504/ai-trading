"""Indian market transaction-cost and friction calculation model.

Calculates realistic trading friction comprising brokerage, STT, exchange charges,
SEBI turnover charges, stamp duty, GST, and dynamic slippage without any hardcoded fees.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.capital.config import CostModelConfig
from app.models.contracts import FrictionBreakdown


class IndianMarketCostModel:
    """Calculates comprehensive transaction friction and net edge for Indian equities."""

    def __init__(self, config: CostModelConfig | None = None) -> None:
        self.config = config or CostModelConfig()

    def calculate_friction(
        self,
        quantity: int,
        buy_price: Decimal,
        sell_price: Decimal,
        is_intraday: bool | None = None,
    ) -> FrictionBreakdown:
        """Compute exhaustive transaction friction across entry and exit legs.

        Includes:
        - Brokerage (percentage subject to flat cap per order leg)
        - STT (Securities Transaction Tax)
        - Exchange transaction charges (NSE)
        - SEBI turnover charges
        - Stamp duty (on BUY leg)
        - GST (18% on Brokerage + Exchange + SEBI)
        - Expected tick slippage on both execution legs
        """
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")

        qty_dec = Decimal(quantity)
        buy_turnover = qty_dec * buy_price
        sell_turnover = qty_dec * sell_price
        total_turnover = buy_turnover + sell_turnover

        use_intraday = self.config.is_intraday if is_intraday is None else is_intraday

        # 1. Brokerage: buy leg + sell leg (both capped by flat cap)
        buy_brokerage = min(
            buy_turnover * self.config.brokerage_rate, self.config.brokerage_flat_cap
        )
        sell_brokerage = min(
            sell_turnover * self.config.brokerage_rate, self.config.brokerage_flat_cap
        )
        brokerage = (buy_brokerage + sell_brokerage).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # 2. STT (Securities Transaction Tax)
        if use_intraday:
            # Intraday equity: charged on SELL leg only
            stt = (sell_turnover * self.config.stt_intraday_rate).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        else:
            # Delivery equity: charged on both legs
            stt = (total_turnover * self.config.stt_delivery_rate).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )

        # 3. Exchange transaction charges (NSE)
        exchange_charges = (
            total_turnover * self.config.exchange_txn_charge_rate
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # 4. SEBI turnover charges
        sebi_charges = (
            total_turnover * self.config.sebi_turnover_charge_rate
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # 5. Stamp duty (charged strictly on BUY leg)
        stamp_rate = (
            self.config.stamp_duty_intraday_rate
            if use_intraday
            else self.config.stamp_duty_delivery_rate
        )
        stamp_duty = (buy_turnover * stamp_rate).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # 6. GST (18% on Brokerage + Exchange + SEBI)
        taxable_services = brokerage + exchange_charges + sebi_charges
        gst = (taxable_services * self.config.gst_rate).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # 7. Expected slippage: 2 execution legs (entry buy + exit sell)
        slippage_per_share = (
            self.config.tick_size * Decimal(self.config.slippage_ticks) * Decimal(2)
        )
        expected_slippage = (qty_dec * slippage_per_share).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # 8. Total friction
        total_friction = (
            brokerage
            + stt
            + exchange_charges
            + sebi_charges
            + stamp_duty
            + gst
            + expected_slippage
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        return FrictionBreakdown(
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            sebi_charges=sebi_charges,
            stamp_duty=stamp_duty,
            gst=gst,
            expected_slippage=expected_slippage,
            total_friction=total_friction,
        )

    def calculate_breakeven_price(
        self,
        quantity: int,
        buy_price: Decimal,
        is_intraday: bool | None = None,
        max_iterations: int = 10,
    ) -> Decimal:
        """Numerically find the exit price where gross profit covers total friction."""
        candidate_price = buy_price + (self.config.tick_size * Decimal(2))
        for _ in range(max_iterations):
            friction = self.calculate_friction(
                quantity=quantity,
                buy_price=buy_price,
                sell_price=candidate_price,
                is_intraday=is_intraday,
            )
            required_gross = friction.total_friction
            candidate_price = buy_price + (required_gross / Decimal(quantity))

        return candidate_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def evaluate_net_edge(
        self,
        expected_gross_gain: Decimal,
        potential_loss: Decimal,
        p_win: Decimal,
        friction: FrictionBreakdown,
        hurdle_rate: Decimal = Decimal("0.0"),
    ) -> tuple[Decimal, Decimal, bool]:
        """Evaluate expected statistical edge after deducting all frictional costs.

        Formula:
            Expected Gross Edge = (Target Gain * P(Win)) - (Stop Loss * (1 - P(Win)))
            Expected Net Edge   = Expected Gross Edge - Total Friction
            Passes              = Expected Net Edge >= Hurdle Rate

        Returns:
            tuple[Decimal, Decimal, bool]: (expected_gross_edge, expected_net_edge, passes_hurdle)
        """
        p_loss = Decimal("1.0") - p_win
        expected_gross_edge = (expected_gross_gain * p_win) - (potential_loss * p_loss)
        expected_net_edge = expected_gross_edge - friction.total_friction
        passes_hurdle = expected_net_edge >= hurdle_rate

        return (
            expected_gross_edge.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            expected_net_edge.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            passes_hurdle,
        )
