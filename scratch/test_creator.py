import sys
sys.path.append(".")
from collectors.helius import HeliusAdapter

helius = HeliusAdapter()
token = "CeSwmXrnaTFXo2TLafY7PaQ1C62dG6mxCGaYUC25pump"

payload = {
    "jsonrpc": "2.0",
    "id": "signatures",
    "method": "getSignaturesForAddress",
    "params": [token, {"limit": 5}],
}
res = helius.client.post_json(helius._rpc_url, payload=payload)
print("Signatures res:", res.ok, res.data)
