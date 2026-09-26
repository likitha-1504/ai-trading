"""FastAPI Endpoints for Phase 35 Research Sandbox & Governed Promotion."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.sandbox.dataset_registry import ReproducibleDatasetRegistry
from app.sandbox.isolation_guard import SandboxIsolationGuard
from app.sandbox.models import (
    DatasetReproducibilityError,
    ProductionIsolationError,
    PromotionGateError,
    PromotionRequest,
    PromotionResult,
    SandboxExecutionResult,
    SilentPromotionError,
    VersionedExperimentConfig,
)
from app.sandbox.promotion_gate import ExplicitPromotionGate
from app.sandbox.sandbox_engine import ResearchSandboxEngine
from app.sandbox.versioned_config import VersionedConfigManager

router = APIRouter(prefix="/sandbox", tags=["Research Sandbox"])

# Singleton instances for sandbox subsystem
_datasets = ReproducibleDatasetRegistry()
_configs = VersionedConfigManager()
_isolation = SandboxIsolationGuard()
_engine = ResearchSandboxEngine(
    dataset_registry=_datasets,
    config_manager=_configs,
    isolation_guard=_isolation,
)
_promotion_gate = ExplicitPromotionGate(engine=_engine)


@router.get("/status", response_model=dict[str, Any])
def get_sandbox_status() -> dict[str, Any]:
    """Retrieves sandbox quarantine and isolation boundary health status."""
    audit = _isolation.audit_isolation()
    audit["registered_datasets_count"] = len(_datasets.list_datasets())
    audit["registered_configs_count"] = len(_configs.list_configs())
    audit["completed_runs_count"] = len(_engine.list_runs())
    audit["promoted_strategies_count"] = len(_promotion_gate.list_promoted_strategies())
    return audit


@router.get("/datasets", response_model=list[dict[str, Any]])
def list_datasets() -> list[dict[str, Any]]:
    """Lists all registered reproducible datasets with their cryptographic hashes."""
    datasets = _datasets.list_datasets()
    return [
        {
            "dataset_id": ds.dataset_id,
            "name": ds.name,
            "version": ds.version,
            "record_count": ds.record_count,
            "sha256_hash": ds.sha256_hash,
            "seed": ds.seed,
            "split": ds.split.value,
            "start_time": ds.start_time.isoformat(),
            "end_time": ds.end_time.isoformat(),
            "metadata": ds.metadata,
        }
        for ds in datasets
    ]


@router.get("/datasets/{dataset_id}/verify", response_model=dict[str, Any])
def verify_dataset(dataset_id: str) -> dict[str, Any]:
    """Cryptographically verifies dataset integrity against its SHA-256 fingerprint."""
    try:
        valid, msg = _datasets.verify_integrity(dataset_id)
        return {"dataset_id": dataset_id, "integrity_valid": valid, "message": msg}
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )


@router.get("/experiments", response_model=list[VersionedExperimentConfig])
def list_experiment_configs() -> list[VersionedExperimentConfig]:
    """Lists all registered versioned experiment configurations."""
    return _configs.list_configs()


@router.post("/experiments/run", response_model=SandboxExecutionResult)
def run_sandbox_simulation(
    experiment_id: str = Query(..., description="ID of versioned experiment configuration"),
    dataset_id: str | None = Query(None, description="Optional target dataset override"),
) -> SandboxExecutionResult:
    """Executes a strategy simulation inside isolated sandbox quarantine."""
    try:
        return _engine.run_simulation(experiment_id=experiment_id, dataset_id=dataset_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProductionIsolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/experiments/verify-reproducibility", response_model=dict[str, Any])
def verify_simulation_reproducibility(
    experiment_id: str = Query(..., description="ID of experiment configuration"),
    dataset_id: str | None = Query(None, description="Optional target dataset override"),
) -> dict[str, Any]:
    """Runs consecutive independent simulations and verifies exact cryptographic reproduction."""
    try:
        valid, result, message = _engine.verify_reproducibility(experiment_id, dataset_id)
        return {
            "reproducibility_verified": valid,
            "execution_hash": result.execution_hash,
            "message": message,
            "metrics": result.metrics.model_dump(),
        }
    except DatasetReproducibilityError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/promote", response_model=PromotionResult)
def promote_sandbox_candidate(request: PromotionRequest) -> PromotionResult:
    """Submits candidate strategy for promotion out of the sandbox into candidate stage."""
    try:
        return _promotion_gate.process_promotion_request(request)
    except SilentPromotionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PromotionGateError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
