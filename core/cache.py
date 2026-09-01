"""
In-Memory TTL Cache with thread safety and namespace support.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    def __init__(self, default_ttl_seconds: float = 60.0):
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            val, expiry = self._store[key]
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        with self._lock:
            expiry = time.monotonic() + ttl
            self._store[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def cleanup_expired(self) -> int:
        now = time.monotonic()
        count = 0
        with self._lock:
            expired_keys = [k for k, (_, expiry) in self._store.items() if now > expiry]
            for k in expired_keys:
                del self._store[k]
                count += 1
        return count
