"""
Unified Robust HTTP and JSON-RPC Client for Solana Meme Research Lab.
Zero third-party dependency (uses standard library urllib.request + json).
Includes rate limiting, exponential backoff, retry, and latency instrumentation.
"""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from core.cache import TTLCache
from core.rate_limiter import ProviderRateLimitManager

logger = logging.getLogger("research_lab.http")


class HttpResponse:
    def __init__(self, status_code: int, data: Any, latency_ms: float, error: Optional[str] = None):
        self.status_code = status_code
        self.data = data
        self.latency_ms = latency_ms
        self.error = error
        self.ok = (200 <= status_code < 300) and (error is None)


class SafeHttpClient:
    """Safe HTTP client with rate limiting, retries, and metrics."""

    def __init__(self, provider_name: str, requests_per_min: int = 60, timeout_seconds: float = 10.0):
        self.provider_name = provider_name
        self.rate_limiter = ProviderRateLimitManager.get_limiter(provider_name, requests_per_min)
        self.timeout = timeout_seconds
        self.cache = TTLCache(default_ttl_seconds=30.0)

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[float] = None,
        max_retries: int = 3,
    ) -> HttpResponse:
        """Perform HTTP GET request with retries and backoff."""
        if params:
            query = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        if use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                return HttpResponse(status_code=200, data=cached, latency_ms=0.1)

        req_headers = {
            "User-Agent": "SolanaMemeResearchLab/1.0",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers, method="GET")
        return self._execute_request(req, max_retries=max_retries, cache_key=url if use_cache else None, cache_ttl=cache_ttl)

    def post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> HttpResponse:
        """Perform HTTP POST request with JSON payload."""
        req_headers = {
            "User-Agent": "SolanaMemeResearchLab/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
        return self._execute_request(req, max_retries=max_retries)

    def _execute_request(
        self,
        req: urllib.request.Request,
        max_retries: int = 3,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[float] = None,
    ) -> HttpResponse:
        backoff = 0.5
        ctx = ssl.create_default_context()

        for attempt in range(1, max_retries + 1):
            if not self.rate_limiter.acquire(block=True, timeout=self.timeout):
                return HttpResponse(
                    status_code=429,
                    data=None,
                    latency_ms=0.0,
                    error=f"Rate limit exceeded for provider {self.provider_name}",
                )

            start = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                    latency = (time.monotonic() - start) * 1000.0
                    raw_data = response.read().decode("utf-8", errors="replace")
                    status_code = response.status

                    try:
                        parsed_json = json.loads(raw_data)
                    except Exception:
                        parsed_json = {"raw": raw_data}

                    if cache_key:
                        self.cache.set(cache_key, parsed_json, ttl_seconds=cache_ttl)

                    return HttpResponse(status_code=status_code, data=parsed_json, latency_ms=latency)

            except urllib.error.HTTPError as e:
                latency = (time.monotonic() - start) * 1000.0
                raw_err = ""
                try:
                    raw_err = e.read().decode("utf-8", errors="replace")
                    parsed_err = json.loads(raw_err)
                except Exception:
                    parsed_err = raw_err

                if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue

                return HttpResponse(
                    status_code=e.code,
                    data=parsed_err,
                    latency_ms=latency,
                    error=f"HTTPError {e.code}: {e.reason}",
                )

            except urllib.error.URLError as e:
                latency = (time.monotonic() - start) * 1000.0
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                return HttpResponse(status_code=503, data=None, latency_ms=latency, error=f"URLError: {e.reason}")

            except Exception as e:
                latency = (time.monotonic() - start) * 1000.0
                return HttpResponse(status_code=500, data=None, latency_ms=latency, error=str(e))

        return HttpResponse(status_code=504, data=None, latency_ms=0.0, error="Max retries exhausted")
