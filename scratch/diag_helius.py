import sys
sys.path.append(".")
from collectors.helius import HeliusAdapter
from collectors.dexscreener import DexScreenerAdapter

dex = DexScreenerAdapter()
helius = HeliusAdapter()

tokens = dex.discover_latest_tokens(limit=3)
for t in tokens:
    print(f"Token: {t.symbol} ({t.address})")
    auth = helius.get_token_authorities(t.address)
    print(f"  Authorities: {auth}")
    top = helius.get_top_holders(t.address, total_supply=auth.get('supply'))
    print(f"  Top Holders: {top}")
