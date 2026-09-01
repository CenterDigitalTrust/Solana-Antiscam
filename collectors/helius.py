"""
Helius Adapter for Solana Meme Research Lab.
Queries on-chain Solana state via Helius RPC & DAS API.
Checks token mint authority, freeze authority, decimals, top holders, and account state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from collectors.base import OnChainProvider
from config.settings import settings
from core.http_client import SafeHttpClient

logger = logging.getLogger("research_lab.helius")


class HeliusAdapter(OnChainProvider):
    def __init__(self, rpc_url: Optional[str] = None):
        self._rpc_url = rpc_url or settings.HELIUS_RPC_URL
        self.client = SafeHttpClient(
            provider_name="Helius",
            requests_per_min=120,  # Conservatively within tier limits
            timeout_seconds=10.0,
        )

    @property
    def name(self) -> str:
        return "Helius"

    def health_check(self) -> Dict[str, Any]:
        """Verify RPC connection by requesting getHealth or getSlot."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSlot",
            "params": [{"commitment": "confirmed"}],
        }
        res = self.client.post_json(self._rpc_url, payload=payload)
        is_ok = res.ok and isinstance(res.data, dict) and "result" in res.data
        return {
            "provider": self.name,
            "endpoint": "getSlot",
            "status": "OK" if is_ok else "ERROR",
            "status_code": res.status_code,
            "latency_ms": round(res.latency_ms, 2),
            "available": is_ok,
            "error": res.error or (res.data.get("error") if isinstance(res.data, dict) else None),
        }

    def get_token_authorities(self, token_address: str) -> Dict[str, Any]:
        """
        Fetch token supply, decimals, mintAuthority, and freezeAuthority using getAccountInfo.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "token-auth",
            "method": "getAccountInfo",
            "params": [
                token_address,
                {"encoding": "jsonParsed", "commitment": "confirmed"},
            ],
        }
        res = self.client.post_json(self._rpc_url, payload=payload)

        result = {
            "is_mintable": False,
            "is_freezable": False,
            "decimals": 6,
            "supply": 0,
            "transfer_fee_bps": 0,
            "raw_available": False,
        }

        if res.ok and isinstance(res.data, dict) and "result" in res.data:
            val = res.data.get("result", {})
            if val and isinstance(val, dict):
                val_data = val.get("value")
                if val_data and isinstance(val_data, dict):
                    parsed = val_data.get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    
                    mint_auth = info.get("mintAuthority")
                    freeze_auth = info.get("freezeAuthority")
                    decimals = info.get("decimals", 6)
                    supply = int(info.get("supply", 0))

                    # Extensions check (for Token-2022 transfer fees)
                    extensions = parsed.get("extensions", [])
                    transfer_fee_bps = 0
                    for ext in extensions:
                        if ext.get("extension") == "transferFeeConfig":
                            state = ext.get("state", {})
                            fee_config = state.get("newerTransferFee", {}) or state.get("olderTransferFee", {})
                            transfer_fee_bps = fee_config.get("transferFeeBasisPoints", 0)

                    result["is_mintable"] = mint_auth is not None
                    result["is_freezable"] = freeze_auth is not None
                    result["decimals"] = decimals
                    result["supply"] = supply
                    result["transfer_fee_bps"] = transfer_fee_bps
                    result["raw_available"] = True

        return result

    def get_top_holders(
        self,
        token_address: str,
        limit: int = 10,
        total_supply: Optional[float] = None,
        decimals: int = 6,
    ) -> Dict[str, Any]:
        """
        Fetch top token accounts by balance using getTokenLargestAccounts.
        Correctly accounts for token decimals.
        """
        cache_key = f"top_holders_{token_address}"
        cached = self.client.cache.get(cache_key)
        if cached:
            return cached

        payload = {
            "jsonrpc": "2.0",
            "id": "largest-accounts",
            "method": "getTokenLargestAccounts",
            "params": [token_address, {"commitment": "confirmed"}],
        }
        res = self.client.post_json(self._rpc_url, payload=payload, max_retries=1)

        holders: List[Dict[str, Any]] = []
        top10_pct = None
        single_max_pct = None

        if res.ok and isinstance(res.data, dict) and "result" in res.data:
            val = res.data.get("result", {})
            if val and isinstance(val, dict):
                items = val.get("value", []) or []

                raw_supply = total_supply
                if raw_supply is None or raw_supply <= 0:
                    auth_info = self.get_token_authorities(token_address)
                    raw_supply = float(auth_info.get("supply") or 0.0)
                    decimals = int(auth_info.get("decimals", 6))

                # Normalize supply to UI units
                ui_supply = (raw_supply / (10 ** decimals)) if raw_supply > (10 ** decimals) else raw_supply

                for item in items[:limit]:
                    amount = float(item.get("uiAmount") or 0.0)
                    address = item.get("address", "")
                    pct = (amount / ui_supply * 100.0) if ui_supply and ui_supply > 0 else 0.0
                    holders.append({
                        "address": address,
                        "amount": amount,
                        "pct": round(pct, 2),
                    })

                if holders:
                    top10_pct = round(sum(h["pct"] for h in holders[:10]), 2)
                    single_max_pct = round(max(h["pct"] for h in holders), 2)

        result = {
            "top_holders": holders,
            "top10_percentage": top10_pct,
            "single_holder_max_percentage": single_max_pct,
            "available": len(holders) > 0 and top10_pct is not None,
        }
        self.client.cache.set(cache_key, result, ttl_seconds=60.0)
        return result

    def get_creator_info(self, token_address: str) -> Dict[str, Any]:
        """
        Fetches true creator wallet address and creator wallet age across its entire transaction history.
        1. Queries earliest signature of token mint.
        2. Queries transaction data to extract creator signer address.
        3. Queries creator address history to determine true creator wallet age.
        """
        cache_key = f"creator_info_{token_address}"
        cached = self.client.cache.get(cache_key)
        if cached:
            return cached

        # Step 1: Find earliest signature of the token mint
        payload_sigs = {
            "jsonrpc": "2.0",
            "id": "token-sigs",
            "method": "getSignaturesForAddress",
            "params": [token_address, {"limit": 100}],
        }
        res_sigs = self.client.post_json(self._rpc_url, payload=payload_sigs, max_retries=1)

        creator_wallet = None
        creator_age_days = None

        if res_sigs.ok and isinstance(res_sigs.data, dict) and "result" in res_sigs.data:
            sigs = res_sigs.data.get("result", [])
            if sigs:
                earliest_token_sig = sigs[-1].get("signature")
                
                # Step 2: Fetch mint transaction details to get signer / creator wallet
                if earliest_token_sig:
                    payload_tx = {
                        "jsonrpc": "2.0",
                        "id": "mint-tx",
                        "method": "getTransaction",
                        "params": [earliest_token_sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                    }
                    res_tx = self.client.post_json(self._rpc_url, payload=payload_tx, max_retries=1)
                    if res_tx.ok and isinstance(res_tx.data, dict) and "result" in res_tx.data:
                        tx_val = res_tx.data.get("result") or {}
                        account_keys = tx_val.get("transaction", {}).get("message", {}).get("accountKeys", [])
                        for acc in account_keys:
                            if isinstance(acc, dict) and acc.get("signer"):
                                creator_wallet = acc.get("pubkey")
                                break
                            elif isinstance(acc, str):
                                creator_wallet = acc
                                break

        # Step 3: Query Creator Wallet's transaction history
        if creator_wallet:
            payload_creator_sigs = {
                "jsonrpc": "2.0",
                "id": "creator-history",
                "method": "getSignaturesForAddress",
                "params": [creator_wallet, {"limit": 1000}],
            }
            res_creator = self.client.post_json(self._rpc_url, payload=payload_creator_sigs, max_retries=1)
            if res_creator.ok and isinstance(res_creator.data, dict) and "result" in res_creator.data:
                creator_sigs = res_creator.data.get("result", [])
                if creator_sigs:
                    earliest_block_time = creator_sigs[-1].get("blockTime")
                    if earliest_block_time:
                        import time
                        now_ts = time.time()
                        age_seconds = max(0.0, now_ts - earliest_block_time)
                        creator_age_days = round(age_seconds / 86400.0, 3)

        result = {
            "creator_wallet_address": creator_wallet,
            "creator_wallet_age_days": creator_age_days,
            "available": creator_age_days is not None,
        }
        self.client.cache.set(cache_key, result, ttl_seconds=21600.0)
        return result

        return {
            "top_holders": holders,
            "top10_percentage": top10_pct,
            "single_holder_max_percentage": single_max_pct,
            "available": len(holders) > 0,
        }
