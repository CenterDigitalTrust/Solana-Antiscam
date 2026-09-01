import time
import threading
from typing import Dict, List
import datetime

from core.models import TokenInfo, TokenStatus, TokenSnapshot, ExitReason
from simulation.portfolio import PaperPortfolio
from database.db import Database

class MockDexAdapter:
    def __init__(self):
        self.mocked_price = 0.000100 # Initial price

    def get_token_snapshots_batch(self, addresses: List[str]) -> Dict[str, TokenSnapshot]:
        print(f"[Mock API] Fast Lane is requesting batch update for {addresses}...")
        return {
            "MOCK_TOKEN": TokenSnapshot(
                token_address="MOCK_TOKEN",
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                price_usd=self.mocked_price,
                liquidity_usd=50000.0,
                volume_5m_usd=1000.0,
                volume_1m_usd=200.0,
                volume_24h_usd=10000.0,
                buys_5m=10,
                sells_5m=5,
                trade_count_5m=15,
                market_cap_usd=100000.0,
                data_sources=["Mock"],
                data_quality_score=100.0,
                missing_fields=[],
            )
        }

def run_test():
    print("=== STARTING FAST LANE MOCK TEST ===\n")
    
    # 1. Setup Mock DB and Portfolio
    import tempfile
    import os
    db_file = os.path.join(tempfile.gettempdir(), "test_fast_lane.db")
    if os.path.exists(db_file):
        os.remove(db_file)
    db = Database(db_file)
    
    portfolio = PaperPortfolio(db=db, starting_capital_usd=100.0)
    mock_dex = MockDexAdapter()
    
    # 2. Open a Mock Position
    token = TokenInfo(
        address="MOCK_TOKEN",
        symbol="MOCK",
        name="Mock Token",
        pair_address="MOCK_PAIR",
        dex="raydium",
        status=TokenStatus.MONITORING,
        discovered_at=datetime.datetime.now(datetime.timezone.utc)
    )
    
    print("[Test] Opening MOCK position at price $0.000100")
    portfolio.open_virtual_position(
        token=token,
        snapshot=mock_dex.get_token_snapshots_batch(["MOCK_TOKEN"])["MOCK_TOKEN"]
    )
    
    assert "MOCK_TOKEN" in portfolio.open_positions
    print("[Test] Position opened successfully.\n")
    
    # 3. Setup Fast Lane loop logic manually to avoid full daemon startup
    stop_event = threading.Event()
    
    def fast_lane_thread():
        while not stop_event.is_set():
            with portfolio._lock:
                open_addresses = list(portfolio.open_positions.keys())
                
            if open_addresses:
                snapshots = mock_dex.get_token_snapshots_batch(open_addresses)
                closed_this_tick = []
                for addr, snap in snapshots.items():
                    closed_pos = portfolio.update_and_check_exits(snap)
                    if closed_pos:
                        closed_this_tick.append(closed_pos)
                
                if closed_this_tick:
                    print(f"\n[Fast Lane] [!] EMERGENCY EXIT: Closed {len(closed_this_tick)} position(s): {[p.symbol for p in closed_this_tick]}\n")
            
            stop_event.wait(2.0) # Run every 2 seconds for faster test

    # Start the fast lane thread
    t = threading.Thread(target=fast_lane_thread, daemon=True)
    t.start()
    
    # 4. Wait a bit, then crash the price by -30%
    print("[Test] Waiting 3 seconds (Fast Lane will see stable price)...")
    time.sleep(3.0)
    
    print("\n[Test] CRASHING PRICE BY -30% (New price: $0.000070)")
    mock_dex.mocked_price = 0.000070
    
    # 5. Wait for Fast Lane to catch it
    print("[Test] Waiting up to 5 seconds for Fast Lane to catch the crash...")
    for _ in range(10):
        if "MOCK_TOKEN" not in portfolio.open_positions:
            print("[Test] SUCCESS! Fast Lane caught the drop and closed the position.")
            break
        time.sleep(0.5)
    else:
        print("[Test] FAILED! Fast Lane did not close the position.")
        
    stop_event.set()
    t.join()
    
    # Print closed positions
    closed = portfolio.closed_positions
    if closed:
        p = closed[0]
        print(f"\n--- CLOSED POSITION STATS ---")
        print(f"Token: {p.symbol}")
        print(f"Entry: ${p.entry_price_usd:.6f}")
        print(f"Exit:  ${p.exit_price_usd:.6f}")
        print(f"P&L:   {p.net_roi_pct:+.2f}%")
        print(f"Reason: {p.exit_reason.name}")

if __name__ == "__main__":
    run_test()
