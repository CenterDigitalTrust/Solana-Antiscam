"""
Token Discovery CLI for Solana Meme Research Lab.
Discovers and lists latest active tokens on Solana.
"""

from __future__ import annotations

from collectors.dexscreener import DexScreenerAdapter
from database.db import Database
from discovery.service import TokenDiscoveryService


def main():
    db = Database()
    dex_adapter = DexScreenerAdapter()
    discovery_service = TokenDiscoveryService(market_provider=dex_adapter, db=db)

    print("\n[*] Running Solana Meme Token Discovery...")
    tokens = discovery_service.discover_and_register(limit=20)
    print(f"[+] Discovered & Registered {len(tokens)} tokens in database.\n")

    fmt = "{:<12} | {:<44} | {:<10} | {:<12}"
    print(fmt.format("SYMBOL", "ADDRESS", "DEX", "INITIAL LIQ"))
    print("-" * 84)
    for t in tokens:
        print(fmt.format(
            t.symbol[:12],
            t.address,
            t.dex[:10],
            f"${t.initial_liquidity_usd:,.0f}",
        ))
    print("-" * 84 + "\n")


if __name__ == "__main__":
    main()
