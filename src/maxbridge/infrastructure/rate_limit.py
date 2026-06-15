from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from maxbridge.application.ports import RateLimiter
from maxbridge.domain.exceptions import RateLimitExceeded


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, *, window_seconds: float, max_messages: int) -> None:
        self._window_seconds = window_seconds
        self._max_messages = max_messages
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        now = time.monotonic()
        async with self._lock:
            events = self._events[key]
            while events and now - events[0] >= self._window_seconds:
                events.popleft()
            if len(events) >= self._max_messages:
                raise RateLimitExceeded("Rate limit exceeded.")
            events.append(now)
