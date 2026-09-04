"""
DEX Screener Adapter for Solana Meme Research Lab.
Uses DexScreener Public REST API (60 req/min, free, no key required).
Provides token pair discovery, volume, transactions, price changes, and liquidity.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from collectors.base import MarketDataProvider
from config.settings import settings
from core.http_client import SafeHttpClient
from core.models import TokenInfo, TokenSnapshot, TokenStatus, utc_now


class DexScreenerAdapter(MarketDataProvider):
    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url or settings.DEXSCREENER_BASE_URL
        self.client = SafeHttpClient(
            provider_name="DexScreener",
            requests_per_min=290,  # Max 300 req/min
            timeout_seconds=10.0,
        )

    @property
    def name(self) -> str:
        return "DexScreener"

    def health_check(self) -> Dict[str, Any]:
        """Check DEX Screener connectivity using native SOL address."""
        sol_address = "So11111111111111111111111111111111111111112"
        url = f"{self._base_url}/tokens/v1/solana/{sol_address}"
        res = self.client.get(url, use_cache=False)
        return {
            "provider": self.name,
            "endpoint": "/tokens/v1/solana/{address}",
            "status": "OK" if res.ok else "ERROR",
            "status_code": res.status_code,
            "latency_ms": round(res.latency_ms, 2),
            "available": res.ok,
            "error": res.error,
        }

    def discover_latest_tokens(self, limit: int = 20) -> List[TokenInfo]:
        """
        Discover latest active Solana meme pairs using latest profiles and search endpoints.
        """
        tokens: List[TokenInfo] = []
        seen_addresses = set()

        # Method 1: Token profiles endpoint
        url_profiles = f"{self._base_url}/token-profiles/latest/v1"
        res_profiles = self.client.get(url_profiles, use_cache=True, cache_ttl=15.0)

        candidate_addresses: List[str] = []
        if res_profiles.ok and isinstance(res_profiles.data, list):
            for item in res_profiles.data:
                if item.get("chainId") == "solana" and item.get("tokenAddress"):
                    candidate_addresses.append(item["tokenAddress"])

        # Method 2: Search for recent trending pairs on Solana
        url_search = f"{self._base_url}/latest/dex/search?q=solana"
        res_search = self.client.get(url_search, use_cache=True, cache_ttl=20.0)
        if res_search.ok and isinstance(res_search.data, dict) and "pairs" in res_search.data:
            for pair in res_search.data.get("pairs", []) or []:
                if pair.get("chainId") == "solana" and pair.get("baseToken", {}).get("address"):
                    candidate_addresses.append(pair["baseToken"]["address"])

        # Batch lookup candidates to get market stats
        if candidate_addresses:
            # Take up to 30 addresses to stay within limits
            unique_candidates = list(dict.fromkeys(candidate_addresses))[:30]
            # Chunk in batches of 10
            for i in range(0, len(unique_candidates), 10):
                chunk = unique_candidates[i : i + 10]
                addr_str = ",".join(chunk)
                url_batch = f"{self._base_url}/tokens/v1/solana/{addr_str}"
                res_batch = self.client.get(url_batch, use_cache=True, cache_ttl=15.0)

                if res_batch.ok and isinstance(res_batch.data, list):
                    for pair in res_batch.data:
                        base = pair.get("baseToken", {})
                        addr = base.get("address")
                        if not addr or addr in seen_addresses:
                            continue
                        seen_addresses.add(addr)

                        created_at_ms = pair.get("pairCreatedAt")
                        created_at = (
                            dt.datetime.fromtimestamp(created_at_ms / 1000.0, tz=dt.timezone.utc)
                            if created_at_ms
                            else None
                        )

                        liq = float(pair.get("liquidity", {}).get("usd") or 0.0)
                        price = float(pair.get("priceUsd") or 0.0)

                        token_info = TokenInfo(
                            address=addr,
                            symbol=base.get("symbol", "UNKNOWN"),
                            name=base.get("name", "Unknown Token"),
                            pair_address=pair.get("pairAddress"),
                            dex=pair.get("dexId", "raydium"),
                            created_at=created_at,
                            discovered_at=utc_now(),
                            initial_liquidity_usd=liq,
                            initial_price_usd=price,
                            status=TokenStatus.DISCOVERED,
                        )
                        tokens.append(token_info)

                        if len(tokens) >= limit:
                            return tokens

        return tokens

    def get_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """Fetch real-time snapshot for a specific token address."""
        url = f"{self._base_url}/tokens/v1/solana/{token_address}"
        res = self.client.get(url, use_cache=True, cache_ttl=10.0)

        if not res.ok or not isinstance(res.data, list) or len(res.data) == 0:
            return None

        # Choose the pair with highest liquidity on Solana
        pairs = sorted(
            res.data,
            key=lambda p: float(p.get("liquidity", {}).get("usd") or 0.0),
            reverse=True,
        )
        pair = pairs[0]

        liq_raw = pair.get("liquidity", {}).get("usd") if pair.get("liquidity") else None
        liq_usd: Optional[float] = float(liq_raw) if (liq_raw is not None and str(liq_raw) != "") else None

        price_raw = pair.get("priceUsd")
        price_usd: Optional[float] = float(price_raw) if (price_raw is not None and str(price_raw) != "") else None

        vol_data = pair.get("volume", {}) or {}
        txns_data = pair.get("txns", {}) or {}

        vol_5m = float(vol_data.get("m5") or 0.0)
        vol_24h = float(vol_data.get("h24") or 0.0)
        vol_1m = float(vol_data.get("m1") or (vol_5m / 5.0))

        m5_tx = txns_data.get("m5", {}) or {}
        buys_5m = int(m5_tx.get("buys") or 0)
        sells_5m = int(m5_tx.get("sells") or 0)
        trade_count_5m = buys_5m + sells_5m

        fdv_raw = pair.get("fdv") or pair.get("marketCap")
        fdv = float(fdv_raw) if fdv_raw is not None else None

        missing = []
        if liq_usd is None:
            missing.append("liquidity_usd")
        if price_usd is None:
            missing.append("price_usd")
        if fdv is None:
            missing.append("market_cap_usd")

        # Data quality score: deduct 40 if liquidity is missing, 30 if price is missing, 10 if mcap is missing
        dq_score = 100.0
        if liq_usd is None:
            dq_score -= 40.0
        if price_usd is None:
            dq_score -= 30.0
        if fdv is None:
            dq_score -= 10.0
        dq_score = max(0.0, dq_score)

        return TokenSnapshot(
            token_address=token_address,
            timestamp=utc_now(),
            price_usd=price_usd,
            liquidity_usd=liq_usd,
            volume_5m_usd=vol_5m,
            volume_1m_usd=vol_1m,
            volume_24h_usd=vol_24h,
            buys_5m=buys_5m,
            sells_5m=sells_5m,
            trade_count_5m=trade_count_5m,
            market_cap_usd=fdv,
            data_sources=[self.name],
            raw_data=pair,
            data_quality_score=dq_score,
            missing_fields=missing,
        )

    def get_token_snapshots_batch(self, token_addresses: List[str]) -> Dict[str, TokenSnapshot]:
        """Fetch real-time snapshots for multiple tokens in a single API call (max 30 per call)."""
        if not token_addresses:
            return {}
        
        result_map: Dict[str, TokenSnapshot] = {}
        
        # DexScreener allows max 30 tokens per request
        chunk_size = 30
        for i in range(0, len(token_addresses), chunk_size):
            chunk = token_addresses[i:i+chunk_size]
            addr_str = ",".join(chunk)
            url = f"{self._base_url}/tokens/v1/solana/{addr_str}"
            res = self.client.get(url, use_cache=True, cache_ttl=5.0)
            
            if not res.ok or not isinstance(res.data, list):
                continue
                
            # Group pairs by token address
            pairs_by_token = {}
            for pair in res.data:
                base_addr = pair.get("baseToken", {}).get("address")
                if not base_addr or base_addr not in chunk:
                    continue
                if base_addr not in pairs_by_token:
                    pairs_by_token[base_addr] = []
                pairs_by_token[base_addr].append(pair)
                
            # Process best pair for each token
            for addr, pairs in pairs_by_token.items():
                pairs = sorted(
                    pairs,
                    key=lambda p: float(p.get("liquidity", {}).get("usd") or 0.0),
                    reverse=True,
                )
                pair = pairs[0]
                
                liq_raw = pair.get("liquidity", {}).get("usd") if pair.get("liquidity") else None
                liq_usd = float(liq_raw) if (liq_raw is not None and str(liq_raw) != "") else None
                
                price_raw = pair.get("priceUsd")
                price_usd = float(price_raw) if (price_raw is not None and str(price_raw) != "") else None
                
                vol_data = pair.get("volume", {}) or {}
                txns_data = pair.get("txns", {}) or {}
                
                vol_5m = float(vol_data.get("m5") or 0.0)
                vol_1m = float(vol_data.get("m1") or (vol_5m / 5.0))
                
                m5_tx = txns_data.get("m5", {}) or {}
                buys_5m = int(m5_tx.get("buys") or 0)
                sells_5m = int(m5_tx.get("sells") or 0)
                
                fdv_raw = pair.get("fdv") or pair.get("marketCap")
                fdv = float(fdv_raw) if fdv_raw is not None else None
                
                dq_score = 100.0
                missing = []
                if liq_usd is None: missing.append("liquidity_usd"); dq_score -= 40.0
                if price_usd is None: missing.append("price_usd"); dq_score -= 30.0
                if fdv is None: missing.append("market_cap_usd"); dq_score -= 10.0
                
                result_map[addr] = TokenSnapshot(
                    token_address=addr,
                    timestamp=utc_now(),
                    price_usd=price_usd,
                    liquidity_usd=liq_usd,
                    volume_5m_usd=vol_5m,
                    volume_1m_usd=vol_1m,
                    volume_24h_usd=float(vol_data.get("h24") or 0.0),
                    buys_5m=buys_5m,
                    sells_5m=sells_5m,
                    trade_count_5m=buys_5m + sells_5m,
                    market_cap_usd=fdv,
                    data_sources=[self.name],
                    raw_data=pair,
                    data_quality_score=max(0.0, dq_score),
                    missing_fields=missing,
                )
                
        return result_map
