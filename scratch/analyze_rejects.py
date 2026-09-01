import sqlite3
import pandas as pd

db_path = 'data/research_lab.db'

try:
    conn = sqlite3.connect(db_path)
    
    # Total tokens
    total_tokens = pd.read_sql("SELECT count(*) as count FROM tokens", conn).iloc[0]['count']
    
    # Status breakdown
    status_counts = pd.read_sql("SELECT status, count(*) as count FROM tokens GROUP BY status", conn)
    
    # Hard rejects reasons
    reject_reasons = pd.read_sql("SELECT security_status, count(*) as count FROM security_checks GROUP BY security_status", conn)
    
    # Decision ledger stats (What actions were taken)
    decisions = pd.read_sql("SELECT action, count(*) as count FROM decision_ledger GROUP BY action", conn)
    
    # Entry Block reasons
    blocks = pd.read_sql("SELECT entry_block_reason, count(*) as count FROM tokens GROUP BY entry_block_reason", conn)

    print(f"--- TOTAL TOKENS DISCOVERED: {total_tokens} ---")
    print("\n--- TOKEN STATUSES ---")
    print(status_counts.to_string(index=False))
    
    print("\n--- SECURITY CHECKS ---")
    print(reject_reasons.to_string(index=False))
    
    print("\n--- DECISION LEDGER (Evaluations) ---")
    print(decisions.to_string(index=False))
    
    print("\n--- WHY DID WE NOT BUY? (Current Block Reasons) ---")
    print(blocks.to_string(index=False))
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
