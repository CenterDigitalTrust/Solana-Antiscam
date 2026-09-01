"""
Jupiter Adapter for Solana Meme Research Lab (Optional).
Used exclusively for quote simulation, price impact probing, and realistic execution costs.
NO REAL SWAPS, NO WALLET TRANSACTIONS.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from collectors.base import QuoteProvider
from config.settings import settings
from core.http_client import SafeHttpClient

logger = logging.getLogger("research_lab.jupiter")

SOL_MINT = "So11111111111111111111111111111111111111112"


class JupiterAdapter(QuoteProvider):
    def __init__(self, quote_url: Optional[str] = None):
        self._quote_url = quote_url or settings.JUPITER_QUOTE_URL
        self.client = SafeHttpClient(
            provider_name="Jupiter",
            requests_per_min=60,
            timeout_seconds=8.0,
        )

    @property
    def name(self) -> str:
        return "Jupiter"

    def health_check(self) -> Dict[str, Any]:
        """Test quote connectivity swapping 0.01 SOL to USDC."""
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        params = {
            "inputMint": SOL_MINT,
            "outputMint": usdc_mint,
            "amount": "10000000",  # 0.01 SOL
            "slippageBps": "50",
        }
        res = self.client.get(self._quote_url, params=params, use_cache=False)
        is_ok = res.ok and isinstance(res.data, dict) and "outAmount" in res.data
        return {
            "provider": self.name,
            "endpoint": "/v6/quote",
            "status": "OK" if is_ok else "OPTIONAL_UNAVAILABLE",
            "status_code": res.status_code,
            "latency_ms": round(res.latency_ms, 2),
            "available": is_ok,
            "error": res.error if not is_ok else None,
        }

    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount_usd: float,
        slippage_bps: int = 100,
    ) -> Dict[str, Any]:
        """Probe realistic execution price and price impact for a $2 position."""
        # Convert USD to approximate lamports (assuming SOL ~$150-$200 baseline for probe)
        lamports = int((amount_usd / 150.0) * 1e9)
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(lamports),
            "slippageBps": str(slippage_bps),
        }
        res = self.client.get(self._quote_url, params=params, use_cache=True, cache_ttl=10.0)

        if res.ok and isinstance(res.data, dict) and "outAmount" in res.data:
            data = res.data
            price_impact_pct = float(data.get("priceImpactPct") or 0.0)
            return {
                "available": True,
                "in_amount": data.get("inAmount"),
                "out_amount": data.get("outAmount"),
                "price_impact_pct": price_impact_pct,
                "route_plan_len": len(data.get("routePlan", [])),
                "source": "JUPITER_QUOTE",
            }

        return {
            "available": False,
            "price_impact_pct": 0.5,  # Theoretical default fallback
            "source": "ASSUMED_AMM_MODEL",
            "error": res.error or "No quote available",
        }
