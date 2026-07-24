"""Serialize operations that temporarily modify process-wide state."""

from __future__ import annotations

from threading import RLock

INPUT_MODEL_LOCK = RLock()
PROCESS_STATE_LOCK = RLock()
