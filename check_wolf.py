import sqlite3
import urllib.request
import json

conn = sqlite3.connect('data/research_lab.db')
cur = conn.cursor()
cur.execute("SELECT address, symbol, initial_price_usd FROM tokens WHERE symbol='WOLF' ORDER BY discovered_at DESC LIMIT 1")
row = cur.fetchone()

if row:
    addr = row[0]
    symbol = row[1]
    initial_p = row[2]
    print(f'Found {symbol} in DB: Address={addr}, Initial Price=${initial_p}')
    
    url = f'https://api.dexscreener.com/latest/dex/tokens/{addr}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        pairs = data.get('pairs', [])
        if pairs:
            best_pair = pairs[0]
            current_p = float(best_pair.get('priceUsd', 0))
            liquidity = best_pair.get('liquidity', {}).get('usd', 0)
            fdv = best_pair.get('fdv', 0)
            growth = ((current_p / initial_p) - 1.0) * 100 if initial_p > 0 else 0
            print(f'Current Price: ${current_p} (Growth: {growth:+.1f}%)')
            print(f'Liquidity: ${liquidity}')
            print(f'FDV: ${fdv}')
        else:
            print('No pairs found on DexScreener.')
    except Exception as e:
        print('Error fetching DexScreener:', e)
else:
    print('Token WOLF not found in database.')
