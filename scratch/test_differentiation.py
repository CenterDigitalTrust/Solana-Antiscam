import sys
sys.path.append(".")
from collectors.helius import HeliusAdapter
from collectors.dexscreener import DexScreenerAdapter
from analyzers.security import SecurityAnalyzer
from analyzers.wallet import WalletAnalyzer

dex = DexScreenerAdapter()
helius = HeliusAdapter()
sec_analyzer = SecurityAnalyzer(onchain_provider=helius)
wal_analyzer = WalletAnalyzer()

tokens = dex.discover_latest_tokens(limit=5)
print("=== TESTING RAW ON-CHAIN METRICS & SCORES ===")
for t in tokens:
    auth = helius.get_token_authorities(t.address)
    decimals = auth.get("decimals", 6)
    raw_supply = auth.get("supply", 0)
    ui_supply = raw_supply / (10 ** decimals) if raw_supply > 10**decimals else raw_supply

    holders_info = helius.get_top_holders(t.address, total_supply=ui_supply)
    top10_pct = holders_info.get("top10_percentage")
    single_max_pct = holders_info.get("single_holder_max_percentage")

    # Creator age & cluster
    sec_res = sec_analyzer.analyze(t.address, authorities_override=auth)
    # inject the fixed top10_pct
    sec_res_diff = sec_analyzer.analyze(
        t.address,
        authorities_override=auth,
        snapshot=type('obj', (object,), {
            'top10_holders_pct': top10_pct,
            'creator_balance_pct': single_max_pct,
            'liquidity_usd': 15000.0,
        })()
    )
    print(f"Token: {t.symbol[:8]} | UI Supply: {ui_supply:,.0f} | Top10: {top10_pct:.2f}% | Max: {single_max_pct:.2f}% | SEC: {sec_res_diff.soft_security_score:.1f}")
