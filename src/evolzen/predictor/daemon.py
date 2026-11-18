"""Autonomous background training daemon (Phase 2.1).

Continuously ingests newly committed transition records from the DuckDB TransitionLogStore,
maintains online training state across the WorldDynamicsPredictor, CLEAR RehearsalBuffer,
GRPO Planner, and GroundedJEPAEncoder, and runs concurrently as an infrastructure service
or standalone CLI process.

Cites:
- CLaaS (arXiv:2606.05559) for continual learning as an infrastructure service;
- CLEAR (Rolnick et al., NeurIPS 2019, arXiv:1811.11682) for mixed on-policy / off-policy rehearsal;
- Wang et al. (2024, IEEE TPAMI, DOI:10.1109/TPAMI.2024.3367329) for continual learning representation principles;
- LeJEPA (arXiv:2511.08544) and Assran et al. (I-JEPA, CVPR 2023, arXiv:2301.08243) for self-supervised latent representation learning;
- DeepSeekMath / GRPO (Shao et al., arXiv:2402.03300) for group-relative policy optimization;
- Tycho (arXiv:2607.28287) for verified transition stream ingestion.

All empirical online training throughput and representation stability metrics remain
untested until Phase 2.1 benchmarks are executed on target hardware (AGENTS.md Rules #4 and #5).
"""
from __future__ import annotations

import contextlib
import threading
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any

import numpy as np

from evolzen.logging import logger
from evolzen.predictor.dynamics import WorldDynamicsPredictor
from evolzen.predictor.planner import Planner
from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.recognition.jepa import GroundedJEPAEncoder
from evolzen.schemas.transition import Transition
from evolzen.storage.transition_log import TransitionLogStore

if TYPE_CHECKING:
    from evolzen.economy.manuals import ManualStore
    from evolzen.library.rule_library import RuleLibrary
    from evolzen.predictor.data_coordinator import ContinualRLDataCoordinator


class OnlineTrainingDaemon:
    """Autonomous background training daemon ingesting transitions from DuckDB.

    Maintains instances of WorldDynamicsPredictor, RehearsalBuffer, Planner, and
    GroundedJEPAEncoder, executing joint updates on newly committed transition streams.
    """

    def __init__(
        self,
        db_path: Path,
        batch_size: int = 8,
        replay_ratio: float = 0.5,
        poll_interval: float = 0.5,
        seed: int = 42,
        *,
        buffer_capacity: int = 1000,
        max_steps: int | None = None,
        last_seq_no: int = 0,
        rule_library: RuleLibrary | None = None,
        manual_store: ManualStore | None = None,
        coordinator: ContinualRLDataCoordinator | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.batch_size = max(1, batch_size)
        self.replay_ratio = max(0.0, min(1.0, replay_ratio))
        self.poll_interval = max(0.01, float(poll_interval))
        self.seed = seed
        self.max_steps = max_steps

        self._predictor = WorldDynamicsPredictor()
        self._rehearsal_buffer = RehearsalBuffer(capacity=buffer_capacity)
        self._planner = Planner(rehearsal_buffer=self._rehearsal_buffer, dynamics=self._predictor)
        self._jepa = GroundedJEPAEncoder(seed=seed)

        self._rule_library = rule_library
        self._manual_store = manual_store
        self._coordinator = coordinator

        self._last_seq_no: int = max(0, last_seq_no)
        self._update_count: int = 0
        self._policy_entropy: float = 0.0
        self._jepa_variance: float = 0.0
        self._active_dimensions: int = 0
        self._latest_summary: dict[str, Any] | None = None

        self._store: TransitionLogStore | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def predictor(self) -> WorldDynamicsPredictor:
        """The internal WorldDynamicsPredictor instance."""
        return self._predictor

    @property
    def rehearsal_buffer(self) -> RehearsalBuffer:
        """The internal RehearsalBuffer instance."""
        return self._rehearsal_buffer

    @property
    def planner(self) -> Planner:
        """The internal Planner instance."""
        return self._planner

    @property
    def jepa(self) -> GroundedJEPAEncoder:
        """The internal GroundedJEPAEncoder instance."""
        return self._jepa

    @property
    def rule_library(self) -> RuleLibrary | None:
        """The internal RuleLibrary instance, if attached."""
        return self._rule_library

    @property
    def coordinator(self) -> ContinualRLDataCoordinator | None:
        """The internal ContinualRLDataCoordinator instance, if attached or initialized."""
        if self._coordinator is None and self._rule_library is not None:
            store = self._get_or_create_store()
            if store is not None:
                from evolzen.predictor.data_coordinator import ContinualRLDataCoordinator

                self._coordinator = ContinualRLDataCoordinator(
                    store=store,
                    rehearsal_buffer=self._rehearsal_buffer,
                    rule_library=self._rule_library,
                    manual_store=self._manual_store,
                )
        return self._coordinator

    @property
    def last_seq_no(self) -> int:
        """Highest transition sequence number ingested so far."""
        return self._last_seq_no

    @property
    def update_count(self) -> int:
        """Total number of joint training updates executed."""
        return self._update_count

    @property
    def policy_entropy(self) -> float:
        """Latest GRPO policy entropy metric."""
        return self._policy_entropy

    @property
    def jepa_variance(self) -> float:
        """Latest Grounded JEPA latent representation variance across dimensions."""
        return self._jepa_variance

    @property
    def active_dimensions(self) -> int:
        """Number of non-collapsed active JEPA embedding dimensions (variance > 1e-4)."""
        return self._active_dimensions

    @property
    def latest_summary(self) -> dict[str, Any] | None:
        """Summary metrics from the most recent training step, if any."""
        return self._latest_summary

    @property
    def is_running(self) -> bool:
        """Whether the background daemon worker thread is actively executing."""
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _get_or_create_store(self) -> TransitionLogStore | None:
        """Open or return existing TransitionLogStore connection."""
        if not self.db_path.exists():
            return None
        if self._store is None:
            self._store = TransitionLogStore(self.db_path)
        return self._store

    def step_once(self, *, allow_partial: bool = False) -> dict[str, Any] | None:
        """Read newly available transitions and execute one joint training step.

        Reads transitions with sequence number > `last_seq_no` from TransitionLogStore.
        If at least `batch_size` transitions are available (or `allow_partial=True` with
        at least 1 transition), executes joint updates across Planner, JEPA, and Predictor.

        Returns:
            Summary dictionary of step metrics, or None if insufficient transitions exist.
        """
        with self._lock:
            try:
                store = self._get_or_create_store()
            except Exception as exc:
                logger.debug("Daemon could not connect to {}: {}", self.db_path, exc)
                return None

            if store is None:
                return None

            try:
                rows = store.list_transitions_with_seq(
                    from_seq=self._last_seq_no,
                    limit=self.batch_size,
                )
            except Exception as exc:
                logger.debug("Daemon error reading transitions: {}", exc)
                return None

            if not rows:
                return None

            if not allow_partial and len(rows) < self.batch_size:
                return None

            batch: list[Transition] = [t for _, t in rows]
            self._last_seq_no = rows[-1][0]

            # 1. Joint updates across Planner, Predictor, and JEPA
            planner_metrics = self._planner.train_step(batch, replay_ratio=self.replay_ratio)
            dyn_metrics = self._predictor.train_batch(batch)
            jepa_metrics = self._jepa.train_step([t.state for t in batch])

            self._update_count += 1
            self._policy_entropy = float(planner_metrics.get("policy_entropy", 0.0))

            # 2. Compute representation variance and dimension health across batch states
            states = [t.state for t in batch]
            if len(states) > 1:
                encoded = np.asarray([self._jepa.encode(s) for s in states], dtype=np.float32)
                dim_vars = np.var(encoded, axis=0)
                self._jepa_variance = float(np.mean(dim_vars))
                self._active_dimensions = int(np.sum(dim_vars > 1e-4))
            else:
                self._jepa_variance = 0.0
                self._active_dimensions = 0

            if self._rule_library is not None:
                for t in batch:
                    with contextlib.suppress(Exception):
                        self._rule_library.regression_bank.ingest_transition(t)

            summary: dict[str, Any] = {
                "update_count": self._update_count,
                "last_seq_no": self._last_seq_no,
                "batch_size": len(batch),
                "loss": float(planner_metrics.get("loss", dyn_metrics.get("loss", 0.0))),
                "policy_entropy": self._policy_entropy,
                "jepa_loss": float(jepa_metrics.get("loss", 0.0)),
                "jepa_invariance_loss": float(jepa_metrics.get("invariance_loss", 0.0)),
                "jepa_variance_loss": float(jepa_metrics.get("variance_loss", 0.0)),
                "jepa_rep_variance": self._jepa_variance,
                "active_dimensions": self._active_dimensions,
                "total_dimensions": self._jepa.embedding_dim,
                "rehearsal_buffer_size": len(self._rehearsal_buffer),
            }

            coord = self.coordinator
            if coord is not None:
                score = max(0.0, min(1.0, 1.0 - summary["loss"]))
                coord.metrics_tracker.record_eval(self._update_count, self._update_count, score)
                summary["bwt"] = coord.metrics_tracker.backward_transfer()
                summary["fwt"] = coord.metrics_tracker.forward_transfer()
                summary["forgetting"] = coord.metrics_tracker.average_forgetting()
                summary["active_capabilities"] = (
                    self._rule_library.active_capability_count() if self._rule_library else 0
                )

            self._latest_summary = summary
            return summary

    def _run_loop(self) -> None:
        """Internal daemon polling and ingestion loop."""
        while not self._stop_event.is_set():
            if self.max_steps is not None and self._update_count >= self.max_steps:
                break

            try:
                res = self.step_once()
            except Exception as exc:
                logger.debug("Daemon step_once failed: {}", exc)
                res = None

            if res is None:
                self._stop_event.wait(self.poll_interval)
            else:
                # Brief yield so we don't monopolize CPU while queue drains
                self._stop_event.wait(min(0.01, self.poll_interval))

    def start(self) -> None:
        """Start the background daemon ingestion loop in a dedicated daemon thread."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="OnlineTrainingDaemon",
            )
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background daemon loop, wait for completion, and close database handles."""
        self._stop_event.set()
        with self._lock:
            thread = self._thread
            self._thread = None
        if thread is not None:
            thread.join(timeout=timeout)
        with self._lock:
            if self._store is not None:
                try:
                    self._store.close()
                except Exception as exc:
                    logger.debug("Error closing daemon TransitionLogStore: {}", exc)
                self._store = None

    def __enter__(self) -> OnlineTrainingDaemon:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()
