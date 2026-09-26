"""Clock abstractions for real-time play and deterministic tests."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:
        """Return the current game time in seconds."""


class SystemClock:
    def now(self) -> float:
        return time.time()
