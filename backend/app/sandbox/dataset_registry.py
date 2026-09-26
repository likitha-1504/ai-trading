"""Reproducible Dataset Registry for Phase 35 Research Sandbox.

Manages cryptographically fingerprinted, versioned datasets ensuring exact
deterministic replay and mathematical reproducibility for strategy experiments.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone

from app.sandbox.models import (
    DatasetSplit,
    ReproducibleDataset,
    SandboxBar,
)


def compute_bars_sha256(bars: list[SandboxBar], seed: int = 42) -> str:
    """Computes a deterministic SHA-256 hash across canonical serialized bars."""
    hasher = hashlib.sha256()
    hasher.update(f"seed:{seed}".encode("utf-8"))
    for bar in bars:
        payload = (
            f"{bar.timestamp.isoformat()}|{bar.open:.4f}|{bar.high:.4f}|"
            f"{bar.low:.4f}|{bar.close:.4f}|{bar.volume}"
        )
        hasher.update(payload.encode("utf-8"))
    return hasher.hexdigest()


class ReproducibleDatasetRegistry:
    """Registry managing versioned, cryptographically hashed reproducible datasets."""

    def __init__(self) -> None:
        self._registry: dict[str, ReproducibleDataset] = {}
        self._initialize_seed_datasets()

    def _initialize_seed_datasets(self) -> None:
        """Seeds baseline reproducible datasets with deterministic synthetic Nifty bars."""
        # 1. Baseline Training Dataset (100 bars)
        train_bars = self.generate_synthetic_bars(
            seed=42,
            count=100,
            base_price=24500.0,
            start_time=datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc),
        )
        train_hash = compute_bars_sha256(train_bars, seed=42)
        train_ds = ReproducibleDataset(
            dataset_id="DATASET-NIFTY-MICRO-2026-TRAIN",
            name="Nifty Micro Intraday 1M (Train)",
            version="1.0.0",
            record_count=len(train_bars),
            sha256_hash=train_hash,
            seed=42,
            start_time=train_bars[0].timestamp,
            end_time=train_bars[-1].timestamp,
            split=DatasetSplit.TRAIN,
            metadata={"instrument": "NIFTY50", "interval": "1m", "volatility_regime": "NORMAL"},
            bars=train_bars,
        )
        self._registry[train_ds.dataset_id] = train_ds

        # 2. Baseline Test Dataset (100 bars)
        test_bars = self.generate_synthetic_bars(
            seed=101,
            count=100,
            base_price=24650.0,
            start_time=datetime(2026, 9, 15, 9, 15, tzinfo=timezone.utc),
        )
        test_hash = compute_bars_sha256(test_bars, seed=101)
        test_ds = ReproducibleDataset(
            dataset_id="DATASET-NIFTY-MICRO-2026-TEST",
            name="Nifty Micro Intraday 1M (Test)",
            version="1.0.0",
            record_count=len(test_bars),
            sha256_hash=test_hash,
            seed=101,
            start_time=test_bars[0].timestamp,
            end_time=test_bars[-1].timestamp,
            split=DatasetSplit.TEST,
            metadata={"instrument": "NIFTY50", "interval": "1m", "volatility_regime": "EXPANSION"},
            bars=test_bars,
        )
        self._registry[test_ds.dataset_id] = test_ds

    @staticmethod
    def generate_synthetic_bars(
        seed: int,
        count: int,
        base_price: float = 24500.0,
        start_time: datetime | None = None,
    ) -> list[SandboxBar]:
        """Generates deterministic pseudo-random market bars using sinusoidal + PRNG walk."""
        import random

        rng = random.Random(seed)
        start = start_time or datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
        current_time = start
        current_price = base_price
        bars: list[SandboxBar] = []

        for i in range(count):
            cycle = math.sin(i / 10.0) * 15.0
            drift = rng.uniform(-10.0, 10.0) + (0.5 if i % 3 == 0 else -0.4)
            open_p = round(current_price, 2)
            delta = drift + cycle
            close_p = round(max(100.0, open_p + delta), 2)
            high_p = round(max(open_p, close_p) + rng.uniform(2.0, 8.0), 2)
            low_p = round(min(open_p, close_p) - rng.uniform(2.0, 8.0), 2)
            vol = rng.randint(500, 5000)

            bars.append(
                SandboxBar(
                    timestamp=current_time,
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=vol,
                )
            )
            current_price = close_p
            current_time += timedelta(minutes=1)

        return bars

    def register_dataset(self, dataset: ReproducibleDataset) -> ReproducibleDataset:
        """Registers a reproducible dataset, enforcing immutability."""
        if dataset.dataset_id in self._registry:
            raise ValueError(f"Dataset '{dataset.dataset_id}' already registered and is immutable.")

        # Verify hash integrity before storing
        computed_hash = compute_bars_sha256(dataset.bars, seed=dataset.seed)
        if computed_hash != dataset.sha256_hash:
            raise ValueError(
                f"Dataset hash mismatch: declared '{dataset.sha256_hash}' != computed '{computed_hash}'"
            )

        self._registry[dataset.dataset_id] = dataset
        return dataset

    def get_dataset(self, dataset_id: str) -> ReproducibleDataset:
        """Retrieves a dataset by ID."""
        if dataset_id not in self._registry:
            raise KeyError(f"Dataset '{dataset_id}' not found in registry.")
        return self._registry[dataset_id]

    def list_datasets(self) -> list[ReproducibleDataset]:
        """Returns all registered datasets."""
        return list(self._registry.values())

    def verify_integrity(self, dataset_id: str) -> tuple[bool, str]:
        """Validates that stored dataset bars have not suffered mutation or corruption."""
        if dataset_id not in self._registry:
            return False, f"Dataset '{dataset_id}' not found."
        ds = self._registry[dataset_id]
        computed = compute_bars_sha256(ds.bars, seed=ds.seed)
        if computed == ds.sha256_hash:
            return True, f"Dataset '{dataset_id}' SHA-256 integrity verified ({len(ds.bars)} bars)."
        return False, f"Integrity compromised: expected {ds.sha256_hash}, calculated {computed}."
