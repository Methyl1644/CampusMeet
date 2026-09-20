"""In-process sliding-window limiter.

The project runs a single API process, so a process-local window is enough to
blunt upload-ticket abuse without adding a Redis dependency. It is deliberately
not a distributed limiter: behind multiple workers each process keeps its own
budget.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, *, limit: int, window_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        cutoff = moment - self.window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(moment)
            self._evict(cutoff)
            return True

    def retry_after_seconds(self, key: str, *, now: float | None = None) -> int:
        """Seconds until `key` may retry; 0 when it is not currently blocked."""
        moment = time.monotonic() if now is None else now
        with self._lock:
            events = self._events.get(key)
            if not events or len(events) < self.limit:
                return 0
            return max(1, int(round(self.window_seconds - (moment - events[0]))))

    def reset(self) -> None:
        with self._lock:
            self._events.clear()

    def _evict(self, cutoff: float) -> None:
        if len(self._events) <= 2048:
            return
        for key in [key for key, events in self._events.items() if not events or events[-1] <= cutoff]:
            self._events.pop(key, None)


UPLOAD_TICKETS_PER_WINDOW = 30
UPLOAD_TICKET_WINDOW_SECONDS = 300

upload_ticket_limiter = SlidingWindowLimiter(
    limit=UPLOAD_TICKETS_PER_WINDOW, window_seconds=UPLOAD_TICKET_WINDOW_SECONDS
)
