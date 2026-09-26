"""Versioned Code & Configuration Manager for Phase 35 Research Sandbox.

Enforces deterministic cryptographic fingerprinting of experiment parameters,
strategy code hashes, and dataset bindings.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.sandbox.models import VersionedExperimentConfig


def compute_config_hash(
    strategy_name: str,
    parameters: dict[str, Any],
    risk_limits: dict[str, float],
    code_hash: str,
    dataset_hash: str,
) -> str:
    """Computes deterministic SHA-256 hash across canonical sorted configuration inputs."""
    hasher = hashlib.sha256()
    payload = {
        "strategy": strategy_name,
        "parameters": parameters,
        "risk_limits": risk_limits,
        "code_hash": code_hash,
        "dataset_hash": dataset_hash,
    }
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hasher.update(canonical_json.encode("utf-8"))
    return hasher.hexdigest()


class VersionedConfigManager:
    """Manages immutable, versioned configurations for research sandbox experiments."""

    def __init__(self) -> None:
        self._configs: dict[str, VersionedExperimentConfig] = {}
        self._initialize_seed_configs()

    def _initialize_seed_configs(self) -> None:
        """Initializes canonical baseline sandbox experiment configurations."""
        # 1. EMA Pullback Sandbox Experiment
        ema_params = {"ema_fast": 9, "ema_slow": 21, "atr_period": 14, "risk_per_trade_pct": 0.01}
        ema_risk = {"max_drawdown_pct": 2.0, "max_capital_inr": 100.0}
        code_h = hashlib.sha256(b"def ema_pullback_v1(): return True").hexdigest()
        # Seeded against train dataset
        dummy_ds_hash = "a41762cba1860e6c52a0a2df339247ebce6058dbbda27eebc5d6428c5040ca64"

        ema_cfg_hash = compute_config_hash(
            strategy_name="EMA_PULLBACK",
            parameters=ema_params,
            risk_limits=ema_risk,
            code_hash=code_h,
            dataset_hash=dummy_ds_hash,
        )

        cfg1 = VersionedExperimentConfig(
            experiment_id="EXP-SANDBOX-EMA-V1",
            strategy_name="EMA_PULLBACK",
            version="1.0.0-sandbox",
            parameters=ema_params,
            risk_limits=ema_risk,
            code_hash=code_h,
            dataset_id="DATASET-NIFTY-MICRO-2026-TRAIN",
            dataset_hash=dummy_ds_hash,
            config_hash=ema_cfg_hash,
            description="EMA 9/21 Dynamic Pullback Intraday Strategy with 1% risk cap",
        )
        self._configs[cfg1.experiment_id] = cfg1

        # 2. Opening Range Breakout (ORB) Sandbox Experiment
        orb_params = {"range_minutes": 15, "breakout_threshold_ticks": 2, "trail_ticks": 10}
        orb_risk = {"max_drawdown_pct": 2.5, "max_capital_inr": 100.0}
        orb_code_h = hashlib.sha256(b"def orb_v1(): return True").hexdigest()

        orb_cfg_hash = compute_config_hash(
            strategy_name="ORB_INTRADAY",
            parameters=orb_params,
            risk_limits=orb_risk,
            code_hash=orb_code_h,
            dataset_hash=dummy_ds_hash,
        )

        cfg2 = VersionedExperimentConfig(
            experiment_id="EXP-SANDBOX-ORB-V1",
            strategy_name="ORB_INTRADAY",
            version="1.0.0-sandbox",
            parameters=orb_params,
            risk_limits=orb_risk,
            code_hash=orb_code_h,
            dataset_id="DATASET-NIFTY-MICRO-2026-TRAIN",
            dataset_hash=dummy_ds_hash,
            config_hash=orb_cfg_hash,
            description="Opening Range Breakout 15-Minute Strategy with 2-tick confirmation",
        )
        self._configs[cfg2.experiment_id] = cfg2

    def register_config(self, config: VersionedExperimentConfig) -> VersionedExperimentConfig:
        """Registers a versioned configuration, enforcing immutability."""
        if config.experiment_id in self._configs:
            raise ValueError(f"Configuration '{config.experiment_id}' already registered.")

        # Re-compute and verify config_hash
        expected_hash = compute_config_hash(
            strategy_name=config.strategy_name,
            parameters=config.parameters,
            risk_limits=config.risk_limits,
            code_hash=config.code_hash,
            dataset_hash=config.dataset_hash,
        )
        if expected_hash != config.config_hash:
            raise ValueError(
                f"Config hash mismatch: declared '{config.config_hash}' != calculated '{expected_hash}'"
            )

        self._configs[config.experiment_id] = config
        return config

    def get_config(self, experiment_id: str) -> VersionedExperimentConfig:
        """Retrieves an experiment configuration by ID."""
        if experiment_id not in self._configs:
            raise KeyError(f"Experiment config '{experiment_id}' not found.")
        return self._configs[experiment_id]

    def list_configs(self) -> list[VersionedExperimentConfig]:
        """Returns all registered versioned experiment configurations."""
        return list(self._configs.values())
