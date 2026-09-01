"""
Thread-safe Token Bucket and Sliding Window Rate Limiters for Provider APIs.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Optional


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(0.1, window_seconds)
        self.tokens = float(self.max_requests)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        if elapsed > 0:
            added_tokens = elapsed * (self.max_requests / self.window_seconds)
            self.tokens = min(float(self.max_requests), self.tokens + added_tokens)
            self.last_refill = now

    def acquire(self, block: bool = True, timeout: float = 10.0) -> bool:
        start_time = time.monotonic()
        while True:
            with self.lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                
                if not block:
                    return False
                
                needed = 1.0 - self.tokens
                wait_time = needed * (self.window_seconds / self.max_requests)
            
            if (time.monotonic() - start_time) + wait_time > timeout:
                return False
            
            time.sleep(min(wait_time, 0.2))


class ProviderRateLimitManager:
    """Manages rate limiters across different API providers."""

    _limiters: Dict[str, RateLimiter] = {}
    _lock = threading.Lock()

    @classmethod
    def get_limiter(cls, provider: str, max_requests_per_min: int = 60) -> RateLimiter:
        with cls._lock:
            if provider not in cls._limiters:
                cls._limiters[provider] = RateLimiter(
                    max_requests=max_requests_per_min,
                    window_seconds=60.0
                )
            return cls._limiters[provider]
