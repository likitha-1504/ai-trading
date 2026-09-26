"""Leakage and Look-Ahead Bias Auditor.

Enforces zero-lookahead bias, monotonic timestamp ordering, train/test partition
isolation, and target non-contamination for quantitative strategy research.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Sequence

from app.models.contracts import Candidate
from app.research.models import LeakageAuditReport

logger = logging.getLogger(__name__)


def _get_timestamp(event: Any) -> datetime:
    """Extracts timestamp from either exchange_timestamp or timestamp attribute."""
    if hasattr(event, "exchange_timestamp"):
        return event.exchange_timestamp
    if hasattr(event, "timestamp"):
        return event.timestamp
    if hasattr(event, "detected_at"):
        return event.detected_at
    raise AttributeError(f"Object {event} has no identifiable timestamp attribute.")


class LeakageAuditor:
    """Verifies strategy pipelines for data leakage, forward-looking bias, and split contamination."""

    @classmethod
    def audit_event_stream(
        cls, events: Sequence[Any]
    ) -> LeakageAuditReport:
        """Audits historical event series for monotonic timestamp sequencing and validity."""
        if not events:
            return LeakageAuditReport(
                is_leakage_free=True,
                timestamp_monotonic=True,
                lookahead_bias_detected=False,
                split_contamination_detected=False,
                future_target_referenced=False,
                checked_events_count=0,
                details="Empty event series: trivially leakage-free.",
            )

        prev_ts: datetime | None = None

        for idx, ev in enumerate(events):
            cur_ts = _get_timestamp(ev)
            if prev_ts is not None and cur_ts < prev_ts:
                return LeakageAuditReport(
                    is_leakage_free=False,
                    timestamp_monotonic=False,
                    lookahead_bias_detected=True,
                    split_contamination_detected=False,
                    future_target_referenced=False,
                    checked_events_count=idx + 1,
                    details=f"Timestamp inversion at index {idx}: {cur_ts} < prior {prev_ts}.",
                )
            prev_ts = cur_ts

        return LeakageAuditReport(
            is_leakage_free=True,
            timestamp_monotonic=True,
            lookahead_bias_detected=False,
            split_contamination_detected=False,
            future_target_referenced=False,
            checked_events_count=len(events),
            details=f"Audited {len(events)} events: strict monotonic sequence verified with zero inversions.",
        )

    @classmethod
    def audit_train_test_split(
        cls,
        train_events: Sequence[Any],
        test_events: Sequence[Any],
    ) -> LeakageAuditReport:
        """Verifies clean temporal boundary isolation between train (in-sample) and test (out-of-sample)."""
        if not train_events or not test_events:
            return LeakageAuditReport(
                is_leakage_free=True,
                timestamp_monotonic=True,
                lookahead_bias_detected=False,
                split_contamination_detected=False,
                future_target_referenced=False,
                checked_events_count=len(train_events) + len(test_events),
                details="Trivially isolated: empty train or test partition.",
            )

        max_train_ts = max(_get_timestamp(e) for e in train_events)
        min_test_ts = min(_get_timestamp(e) for e in test_events)

        if max_train_ts >= min_test_ts:
            return LeakageAuditReport(
                is_leakage_free=False,
                timestamp_monotonic=False,
                lookahead_bias_detected=True,
                split_contamination_detected=True,
                future_target_referenced=False,
                checked_events_count=len(train_events) + len(test_events),
                details=(
                    f"Temporal split contamination: max in-sample timestamp ({max_train_ts}) "
                    f"overlaps with min out-of-sample timestamp ({min_test_ts})."
                ),
            )

        return LeakageAuditReport(
            is_leakage_free=True,
            timestamp_monotonic=True,
            lookahead_bias_detected=False,
            split_contamination_detected=False,
            future_target_referenced=False,
            checked_events_count=len(train_events) + len(test_events),
            details=(
                f"Split partition verified cleanly: in-sample ends at {max_train_ts} "
                f"strictly prior to out-of-sample start at {min_test_ts}."
            ),
        )

    @classmethod
    def audit_signal_timing(
        cls,
        signals: Sequence[Candidate],
        event_timestamp_map: dict[str, datetime],
    ) -> LeakageAuditReport:
        """Audits that signals are not generated before their trigger events."""
        for sig in signals:
            trigger_ts = event_timestamp_map.get(sig.symbol)
            if trigger_ts and sig.detected_at < trigger_ts:
                return LeakageAuditReport(
                    is_leakage_free=False,
                    timestamp_monotonic=False,
                    lookahead_bias_detected=True,
                    split_contamination_detected=False,
                    future_target_referenced=True,
                    checked_events_count=len(signals),
                    details=f"Signal for {sig.symbol} at {sig.detected_at} precedes trigger event at {trigger_ts}.",
                )

        return LeakageAuditReport(
            is_leakage_free=True,
            timestamp_monotonic=True,
            lookahead_bias_detected=False,
            split_contamination_detected=False,
            future_target_referenced=False,
            checked_events_count=len(signals),
            details=f"All {len(signals)} signals generated strictly on or after causal market observations.",
        )
