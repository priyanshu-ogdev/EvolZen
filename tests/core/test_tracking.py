"""Phase 0 sanity tests: the tracking protocol's always-available default implementation."""
from evolzen.tracking import ExperimentTracker, NoOpTracker


def test_noop_tracker_satisfies_protocol() -> None:
    tracker: ExperimentTracker = NoOpTracker()
    tracker.log({"reward": 1.0}, step=1)
    tracker.log_params({"lr": 3e-4})
    tracker.finish()
    tracker.finish()  # safe to call twice


def test_wandb_tracker_import_does_not_require_extra() -> None:
    from evolzen.tracking import WandbTracker  # noqa: F401
