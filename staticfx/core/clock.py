"""Frame pacing."""

from __future__ import annotations

import time

# A frame that took longer than this (a suspend, a debugger pause, a slow
# terminal) is treated as if it took this long, so simulations never take
# one enormous step.
MAX_STEP = 0.25


class FrameClock:
    def __init__(self, fps: float) -> None:
        self.interval = 1.0 / max(1.0, fps)
        self._last = time.perf_counter()
        self._frame_start = self._last

    def tick(self) -> float:
        """Start a frame; returns the seconds since the previous one."""
        now = time.perf_counter()
        dt = min(MAX_STEP, max(0.0, now - self._last))
        self._last = self._frame_start = now
        return dt

    def wait(self) -> None:
        """Sleep off whatever is left of this frame's time budget."""
        remaining = self.interval - (time.perf_counter() - self._frame_start)
        if remaining > 0:
            time.sleep(remaining)
