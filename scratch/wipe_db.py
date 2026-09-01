import sqlite3
import os
import shutil

db_path = 'data/research_lab.db'

# 1. Clean Database
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    tables = [
        'tokens', 'token_snapshots', 'scores', 'security_checks', 
        'features', 'paper_positions', 'decision_ledger', 'scan_cycles'
    ]
    
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table}")
            print(f"Cleared table: {table}")
        except Exception as e:
            print(f"Error clearing {table}: {e}")
            
    cur.execute("VACUUM") # Reclaim space
    conn.commit()
    conn.close()
    print("Database wiped and vacuumed successfully.")

# 2. Delete all results and reports
dirs_to_clean = ['results', 'ОТЧЕТЫ', 'runtime/results']
for d in dirs_to_clean:
    if os.path.exists(d):
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.txt') or file.endswith('.csv'):
                    os.remove(os.path.join(root, file))
        print(f"Cleared reports/CSVs in directory: {d}")

print("Reset complete! Portfolio will start fresh with $100.00 on next run.")
