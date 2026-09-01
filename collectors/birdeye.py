"""
Birdeye Adapter for Solana Meme Research Lab.
Queries Birdeye DeFi API for price, overview, security stats, and trade history.
Handles rate limits and auth headers safely.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from collectors.base import DataProvider
from config.settings import settings
from core.http_client import SafeHttpClient

logger = logging.getLogger("research_lab.birdeye")


class BirdeyeAdapter(DataProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._api_key = api_key or settings.BIRDEYE_API_KEY
        self._base_url = base_url or settings.BIRDEYE_BASE_URL
        self.client = SafeHttpClient(
            provider_name="Birdeye",
            requests_per_min=60,
            timeout_seconds=10.0,
        )

    @property
    def name(self) -> str:
        return "Birdeye"

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["X-API-KEY"] = self._api_key
            headers["x-chain"] = "solana"
        return headers

    def health_check(self) -> Dict[str, Any]:
        """Check Birdeye connectivity using price endpoint for SOL."""
        if not self._api_key:
            return {
                "provider": self.name,
                "endpoint": "/defi/price",
                "status": "UNAVAILABLE",
                "status_code": 0,
                "latency_ms": 0.0,
                "available": False,
                "error": "No BIRDEYE_API_KEY provided in environment",
            }

        sol_address = "So11111111111111111111111111111111111111112"
        url = f"{self._base_url}/defi/price"
        res = self.client.get(
            url,
            headers=self._headers(),
            params={"address": sol_address},
            use_cache=False,
        )

        is_ok = res.ok and isinstance(res.data, dict) and res.data.get("success", False)
        return {
            "provider": self.name,
            "endpoint": "/defi/price",
            "status": "OK" if is_ok else "ERROR",
            "status_code": res.status_code,
            "latency_ms": round(res.latency_ms, 2),
            "available": is_ok,
            "error": res.error or (res.data.get("message") if isinstance(res.data, dict) and not is_ok else None),
        }

    def get_token_security(self, token_address: str) -> Dict[str, Any]:
        """Fetch Birdeye token security report if available."""
        if not self._api_key:
            return {"available": False, "error": "No API key"}

        url = f"{self._base_url}/defi/token_security"
        res = self.client.get(
            url,
            headers=self._headers(),
            params={"address": token_address},
            use_cache=True,
            cache_ttl=60.0,
        )

        if res.ok and isinstance(res.data, dict) and res.data.get("success"):
            return {
                "available": True,
                "data": res.data.get("data", {}),
            }
        return {"available": False, "error": res.error or "Endpoint failed"}
