import random
import time
import sys
import os
import string
from datetime import datetime, timezone
from database.supabase_client import SupabaseManager

def run_sim():
    print("Starting ADVANCED market simulation...")
    try:
        sb = SupabaseManager()
    except Exception as e:
        print(f"Failed to init SupabaseManager: {e}")
        return
        
    current_scanned = 4812
    current_rejected = 4398
    current_passed = 414
    current_pnl = 22.24

    while True:
        try:
            res = sb.client.table('tokens').select('*').execute()
            tokens = res.data
            
            # Increment stats
            new_scans = random.randint(3, 12)
            new_passed = 1 if random.random() < 0.2 else 0
            new_rejected = new_scans - new_passed
            
            current_scanned += new_scans
            current_rejected += new_rejected
            current_passed += new_passed
            
            # Keep PnL realistic (fluctuate up to $30)
            pnl_delta = random.uniform(-0.5, 1.2)
            current_pnl = max(0.0, min(29.99, current_pnl + pnl_delta))
            
            sb.update_daily_stats(current_scanned, current_rejected, current_passed, current_pnl)
            
            # Update random tokens
            if tokens:
                for t in tokens:
                    if random.random() < 0.4:
                        old_price = float(t.get('price_usd') or 0.001)
                        if old_price == 0: old_price = random.uniform(0.0001, 0.05)
                        
                        change = old_price * random.uniform(-0.05, 0.08)
                        new_price = max(0.000001, old_price + change)
                        
                        updates = {'price_usd': new_price}
                        
                        # Sometimes refresh discovered_at for QUARANTINED tokens so they jump to top
                        if t.get('status') == 'QUARANTINED' and random.random() < 0.2:
                            updates['discovered_at'] = datetime.now(timezone.utc).isoformat()
                            
                        # Sometimes promote to SUCCESS
                        if t.get('status') == 'QUARANTINED' and random.random() < 0.05:
                            updates['status'] = 'SUCCESS'
                            
                        sb.client.table('tokens').update(updates).eq('token_address', t.get('token_address')).execute()
            
            # Occasionally add a brand new token to QUARANTINED
            if random.random() < 0.3:
                name = ''.join(random.choices(string.ascii_uppercase, k=4))
                address = ''.join(random.choices(string.ascii_letters + string.digits, k=43))
                new_token = {
                    'token_address': address,
                    'ticker': name,
                    'name': name + ' COIN',
                    'discovered_at': datetime.now(timezone.utc).isoformat(),
                    'price_usd': random.uniform(0.0001, 0.01),
                    'initial_price_usd': random.uniform(0.0001, 0.01),
                    'volume_24h_usd': random.uniform(1000, 50000),
                    'score': random.uniform(10, 45),
                    'status': 'QUARANTINED'
                }
                sb.client.table('tokens').insert(new_token).execute()

            time.sleep(4)
            
        except Exception as e:
            time.sleep(2)

if __name__ == '__main__':
    run_sim()
