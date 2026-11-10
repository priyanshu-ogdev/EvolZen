"""Pluggable experiment tracking.

Every training and evaluation loop (Phase 1.2's population fitness, Phase 2.1's planner
training, Phase 2.3's recognition-model ablation matrix, Phase 2.4's held-out RHAE scores) needs
to log metrics somewhere. Callers depend on the `ExperimentTracker` protocol below and
construct whichever concrete implementation fits the run — `NoOpTracker` by default (always
available, zero extra dependencies), `WandbTracker` when the `tracking` extra is installed.
"""
from __future__ import annotations

from typing import Any, Protocol


class ExperimentTracker(Protocol):
    """Protocol satisfied by any concrete tracking backend."""

    def log(self, metrics: dict[str, float], *, step: int | None = None) -> None:
        """Log a batch of scalar metrics, optionally tagged with a step number."""
        ...

    def log_params(self, params: dict[str, Any]) -> None:
        """Log run configuration/hyperparameters once, at the start of a run."""
        ...

    def finish(self) -> None:
        """Flush and close the run. Safe to call multiple times."""
        ...


class NoOpTracker:
    """Default tracker: satisfies the protocol, logs nothing, no extra dependencies."""

    def log(self, metrics: dict[str, float], *, step: int | None = None) -> None:
        return None

    def log_params(self, params: dict[str, Any]) -> None:
        return None

    def finish(self) -> None:
        return None


class WandbTracker:
    """Weights & Biases-backed tracker. Requires the `evolzen[tracking]` optional extra.

    Import of `wandb` is deferred to `__init__` so importing this module never requires the
    extra — only *constructing* a `WandbTracker` does.
    """

    def __init__(self, project: str, run_name: str | None = None) -> None:
        try:
            import wandb
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError(
                "WandbTracker requires the 'tracking' extra: uv sync --extra tracking"
            ) from exc
        self._run: Any = wandb.init(project=project, name=run_name)

    def log(self, metrics: dict[str, float], *, step: int | None = None) -> None:
        self._run.log(metrics, step=step)

    def log_params(self, params: dict[str, Any]) -> None:
        self._run.config.update(params)

    def finish(self) -> None:
        self._run.finish()
