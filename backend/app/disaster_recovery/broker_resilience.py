"""Broker Connection Resilience and Auto-Reconnect Manager for Phase 33.

Handles broker session dropouts, exponential reconnect backoff, order book resynchronization,
and post-reconnect position audits.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.adapters.broker_base import BrokerAdapter
from app.disaster_recovery.models import BrokerDisconnectTelemetry
from app.models.contracts import OrderEvent, PositionSnapshot

logger = logging.getLogger(__name__)


class BrokerResilienceManager:
    """Monitors broker connectivity, conducts graceful reconnection, and resynchronizes state."""

    def __init__(
        self,
        broker_adapter: BrokerAdapter,
        max_reconnect_retries: int = 3,
        initial_backoff_seconds: float = 0.1,
    ) -> None:
        self.broker = broker_adapter
        self.max_retries = max_reconnect_retries
        self.initial_backoff = initial_backoff_seconds
        self._disconnect_history: list[BrokerDisconnectTelemetry] = []

    def check_connection(self) -> bool:
        """Check whether broker gateway is currently reachable."""
        try:
            return bool(self.broker.is_connected)
        except Exception as e:  # noqa: BLE001
            logger.error("Error probing broker connection: %s", e)
            return False

    def handle_disconnect_and_recover(
        self,
        local_pending_orders: dict[str, Any] | None = None,
        local_positions: list[PositionSnapshot] | None = None,
    ) -> BrokerDisconnectTelemetry:
        """Execute automated recovery protocol: backoff reconnect followed by state resync."""
        now = datetime.now(timezone.utc)
        telemetry = BrokerDisconnectTelemetry(
            disconnected_at=now,
            status="RECOVERING",
        )

        logger.warning("Broker disconnection detected. Initiating resilient reconnect backoff...")

        # 1. Backoff Retry Loop
        attempt = 0
        connected = False
        delay = self.initial_backoff

        while attempt < self.max_retries and not connected:
            attempt += 1
            logger.info("Broker reconnect attempt %d/%d (delay: %.2fs)...", attempt, self.max_retries, delay)
            try:
                time.sleep(delay)
                connected = self.broker.connect()
            except Exception as e:  # noqa: BLE001
                logger.warning("Reconnect attempt %d failed: %s", attempt, e)
                connected = False

            delay *= 2.0

        telemetry.retry_attempts = attempt
        reconnected_now = datetime.now(timezone.utc)
        telemetry.reconnected_at = reconnected_now
        telemetry.downtime_seconds = round((reconnected_now - now).total_seconds(), 3)
        telemetry.reconnected_cleanly = connected

        if not connected:
            telemetry.status = "FAILED_DISCONNECTED"
            logger.critical("Broker reconnection failed after %d retries. Halting trading.", attempt)
            self._disconnect_history.append(telemetry)
            return telemetry

        # 2. Resynchronize Active Orders
        reconciled_orders = 0
        if local_pending_orders:
            try:
                broker_orders = self.broker.get_orders()
                broker_orders_by_id = {o.client_order_id: o for o in broker_orders}
                for client_id in local_pending_orders:
                    if client_id in broker_orders_by_id:
                        broker_ev: OrderEvent = broker_orders_by_id[client_id]
                        reconciled_orders += 1
                        logger.info(
                            "Reconnected sync: Order %s matched with broker status %s",
                            client_id,
                            broker_ev.status,
                        )
            except Exception as e:  # noqa: BLE001
                logger.error("Error resynchronizing orders with broker: %s", e)

        telemetry.reconciled_orders_count = reconciled_orders

        # 3. Audit Local Positions Against Broker
        reconciled_positions = 0
        if local_positions is not None:
            try:
                recon_report = self.broker.reconcile(local_positions)
                reconciled_positions = max(0, recon_report.positions_checked - len(recon_report.mismatches))
                logger.info(
                    "Reconnected position audit: %d checked, %d mismatches, clean: %s",
                    recon_report.positions_checked,
                    len(recon_report.mismatches),
                    recon_report.is_clean,
                )
            except Exception as e:  # noqa: BLE001
                logger.error("Error during post-reconnect position audit: %s", e)

        telemetry.reconciled_positions_count = reconciled_positions
        telemetry.status = "RECONNECTED_AND_RECONCILED"
        self._disconnect_history.append(telemetry)
        return telemetry

    def simulate_disconnect_drill(self) -> BrokerDisconnectTelemetry:
        """Simulate broker disconnection and automated reconnection for testing."""
        self.broker.disconnect()
        return self.handle_disconnect_and_recover()
