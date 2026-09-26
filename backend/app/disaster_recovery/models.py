"""Disaster Recovery Models, Enums, and Audit Schemas for Phase 33.

Covers:
- Crash / Restart Recovery States
- Broker Disconnect & Reconnect Telemetry
- Stale Market Data Tracking & Thresholds
- Persistent Order Idempotency Records
- Cross-Ledger State Reconstruction & Reconciliation
- Safe Resume Attestations & Multi-Scenario Drill Results
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.contracts import ReconciliationReport


class DisasterScenarioType(str, Enum):
    """Types of simulated or runtime disaster events."""

    PROCESS_CRASH = "PROCESS_CRASH"
    BROKER_DISCONNECT = "BROKER_DISCONNECT"
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    DUPLICATE_ORDER_ATTACK = "DUPLICATE_ORDER_ATTACK"
    STATE_DIVERGENCE = "STATE_DIVERGENCE"


class SystemRecoveryStatus(str, Enum):
    """High-level system continuity state."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    SAFE_HALTED = "SAFE_HALTED"
    RESUMED = "RESUMED"


class StaleDataThresholds(BaseModel):
    """Threshold settings for market quote freshness."""

    max_quote_age_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=60.0,
        description="Maximum permissible quote age before data is considered stale",
    )
    max_feed_gap_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=120.0,
        description="Maximum permissible gap between feed heartbeats",
    )


class QuoteFreshnessReport(BaseModel):
    """Telemetry report assessing symbol quote freshness."""

    symbol: str
    quote_timestamp: datetime
    current_timestamp: datetime
    age_seconds: float
    is_stale: bool
    status: str
    message: str


class IdempotencyRecord(BaseModel):
    """Persistent idempotency record ensuring zero duplicate order dispatch."""

    client_order_id: str
    order_fingerprint: str
    plan_id: str
    symbol: str
    side: str
    quantity: int
    price_level: Decimal | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "RECORDED"


class BrokerDisconnectTelemetry(BaseModel):
    """Telemetry tracking broker disconnection, retry backoff, and reconnection."""

    disconnected_at: datetime
    reconnected_at: datetime | None = None
    downtime_seconds: float = 0.0
    retry_attempts: int = 0
    reconnected_cleanly: bool = False
    reconciled_orders_count: int = 0
    reconciled_positions_count: int = 0
    status: str = "DISCONNECTED"


class DatabaseHealthReport(BaseModel):
    """Health and integrity evaluation of SQLite WAL storage."""

    db_path: str
    integrity_ok: bool
    wal_journal_mode: str
    foreign_keys_enabled: bool
    active_connections_ok: bool
    backup_file_available: bool
    last_checkpoint_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: str = "HEALTHY"


class StateReconstructionReport(BaseModel):
    """Cross-ledger reconciliation between database state and broker state."""

    reconstructed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    db_positions_count: int
    broker_positions_count: int
    matched_positions_count: int
    orphaned_positions: list[str] = Field(default_factory=list)
    phantom_positions: list[str] = Field(default_factory=list)
    reconciled_equity: Decimal
    broker_cash_balance: Decimal
    cash_divergence: Decimal
    is_divergent: bool
    reconstruction_action: str
    reconciliation_details: ReconciliationReport | None = None


class SafeResumeAttestation(BaseModel):
    """Formal audit attestation granting permission to resume active operations."""

    attestation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    operator_token: str
    db_integrity_verified: bool
    broker_connected: bool
    state_reconciled: bool
    market_data_fresh: bool
    active_positions_count: int
    resumption_approved: bool
    operational_mode: str
    notes: list[str] = Field(default_factory=list)


class ScenarioDrillResult(BaseModel):
    """Outcome of a single simulated disaster recovery test."""

    scenario: DisasterScenarioType
    passed: bool
    latency_ms: float
    description: str
    verification_evidence: str
    details: dict[str, Any] = Field(default_factory=dict)


class DisasterRecoveryAuditResult(BaseModel):
    """Comprehensive summary of all Phase 33 disaster recovery drills."""

    audit_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scenarios_tested: int
    scenarios_passed: int
    all_passed: bool
    drill_results: list[ScenarioDrillResult] = Field(default_factory=list)
    system_status: SystemRecoveryStatus
    attestation: SafeResumeAttestation | None = None
