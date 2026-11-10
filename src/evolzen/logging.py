"""Repo-wide structured logging.

Every subsystem calls `configure_logging()` once at process start so that logs from a run
touching several subsystems at once are consistently formatted and greppable by phase.
"""
from __future__ import annotations

import sys

from loguru import logger

_CONFIGURED = False


def configure_logging(*, level: str = "INFO", phase: str | None = None) -> None:
    """Configure the shared loguru logger.

    Args:
        level: standard logging level name.
        phase: optional phase tag (e.g. ``"1.4"``) bound into every log line from this
            process, so logs from a multi-phase run can be filtered by phase.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    logger.remove()
    fmt = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
    if phase:
        fmt += f"<cyan>phase={phase}</cyan> | "
    fmt += "<level>{message}</level>"
    logger.add(sys.stderr, level=level, format=fmt, colorize=True)
    _CONFIGURED = True


__all__ = ["configure_logging", "logger"]
