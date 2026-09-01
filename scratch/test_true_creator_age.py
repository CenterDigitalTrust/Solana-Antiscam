import sys
sys.path.append(".")
from collectors.helius import HeliusAdapter
import time

helius = HeliusAdapter()
token = "CeSwmXrnaTFXo2TLafY7PaQ1C62dG6mxCGaYUC25pump"

# 1. Get earliest signature of token mint
payload_sigs = {
    "jsonrpc": "2.0",
    "id": "sigs",
    "method": "getSignaturesForAddress",
    "params": [token, {"limit": 100}],
}
res_sigs = helius.client.post_json(helius._rpc_url, payload=payload_sigs)
earliest_sig = res_sigs.data["result"][-1]["signature"]
print(f"Earliest token mint signature: {earliest_sig}")

# 2. Get transaction details to extract the fee payer / creator signer wallet
payload_tx = {
    "jsonrpc": "2.0",
    "id": "tx",
    "method": "getTransaction",
    "params": [earliest_sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
}
res_tx = helius.client.post_json(helius._rpc_url, payload=payload_tx)
tx_data = res_tx.data.get("result", {})
account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
print(f"Account keys in mint tx: {account_keys[:3]}")

# Fee payer / creator is typically the first signer (accountKeys[0])
creator_wallet = None
for acc in account_keys:
    if isinstance(acc, dict) and acc.get("signer"):
        creator_wallet = acc.get("pubkey")
        break
    elif isinstance(acc, str):
        creator_wallet = acc
        break

print(f"Identified Creator Wallet: {creator_wallet}")

# 3. Now check true age of the CREATOR WALLET
if creator_wallet:
    payload_creator_sigs = {
        "jsonrpc": "2.0",
        "id": "creator_sigs",
        "method": "getSignaturesForAddress",
        "params": [creator_wallet, {"limit": 1000}],
    }
    res_creator = helius.client.post_json(helius._rpc_url, payload=payload_creator_sigs)
    creator_sigs = res_creator.data.get("result", [])
    if creator_sigs:
        earliest_creator_time = creator_sigs[-1].get("blockTime")
        now_ts = time.time()
        age_days = (now_ts - earliest_creator_time) / 86400.0 if earliest_creator_time else 0.0
        print(f"Creator Wallet First Activity: {time.ctime(earliest_creator_time)}")
        print(f"Total Transactions in history: {len(creator_sigs)}")
        print(f"True Creator Wallet Age: {age_days:.2f} days")
