"""Base Strategy abstract interface."""

from abc import ABC, abstractmethod

from app.models.contracts import Candidate, FeatureSnapshot, StrategyType


class BaseStrategy(ABC):
    """Abstract base class for all deterministic BUY strategies."""

    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """Return the unique StrategyType identifier."""
        ...

    @abstractmethod
    def evaluate(self, snapshot: FeatureSnapshot) -> Candidate | None:
        """Evaluate a FeatureSnapshot deterministically.

        Returns:
            Candidate instance if all entry criteria are satisfied, else None.
        """
        ...
