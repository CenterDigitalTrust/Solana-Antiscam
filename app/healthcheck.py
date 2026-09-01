"""
Provider Capability Test for Solana Meme Research Lab.
Performs safe, live health checks on all adapters without exposing secrets.
"""

from __future__ import annotations

import sys
from typing import List, Dict, Any

from collectors.birdeye import BirdeyeAdapter
from collectors.dexscreener import DexScreenerAdapter
from collectors.helius import HeliusAdapter
from collectors.jupiter import JupiterAdapter
from config.settings import settings


def run_healthcheck() -> List[Dict[str, Any]]:
    results = []

    # 1. Helius
    helius = HeliusAdapter()
    h_res = helius.health_check()
    h_res["auth"] = "API_KEY_PRESENT" if settings.has_helius() else "MISSING"
    h_res["rate_limit"] = "120 RPM"
    results.append(h_res)

    # 2. DexScreener
    dex = DexScreenerAdapter()
    d_res = dex.health_check()
    d_res["auth"] = "NONE_REQUIRED"
    d_res["rate_limit"] = "60 RPM"
    results.append(d_res)

    # 3. Birdeye
    bird = BirdeyeAdapter()
    b_res = bird.health_check()
    b_res["auth"] = "API_KEY_PRESENT" if settings.has_birdeye() else "MISSING"
    b_res["rate_limit"] = "60 RPM"
    results.append(b_res)

    # 4. Jupiter
    jup = JupiterAdapter()
    j_res = jup.health_check()
    j_res["auth"] = "OPTIONAL"
    j_res["rate_limit"] = "60 RPM"
    results.append(j_res)

    return results


def print_table(results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 96)
    print("SOLANA MEME RESEARCH LAB — PROVIDER CAPABILITY & HEALTH CHECK")
    print("=" * 96)
    fmt = "{:<14} | {:<16} | {:<22} | {:<10} | {:<10} | {:<10}"
    print(fmt.format("PROVIDER", "AUTH", "ENDPOINT", "STATUS", "LATENCY", "AVAILABLE"))
    print("-" * 96)
    for r in results:
        status_str = r.get("status", "UNKNOWN")
        avail_str = "YES" if r.get("available") else "NO"
        lat_str = f"{r.get('latency_ms', 0):.1f}ms"
        print(fmt.format(
            r.get("provider", ""),
            r.get("auth", ""),
            r.get("endpoint", "")[:22],
            status_str,
            lat_str,
            avail_str,
        ))
    print("=" * 96 + "\n")


if __name__ == "__main__":
    results = run_healthcheck()
    print_table(results)
