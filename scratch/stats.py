import sqlite3
import pandas as pd

db_path = 'data/research_lab.db'

try:
    conn = sqlite3.connect(db_path, timeout=20.0)
    
    # 1. Total tokens
    total_tokens = pd.read_sql("SELECT count(*) as count FROM tokens", conn).iloc[0]['count']
    
    # 2. Token Status
    status_df = pd.read_sql("SELECT status, count(*) as count FROM tokens GROUP BY status", conn)
    status_dict = dict(zip(status_df['status'], status_df['count']))
    
    # 3. Security Rejects (Hard Rejects)
    sec_df = pd.read_sql("SELECT security_status, count(*) as count FROM security_checks GROUP BY security_status", conn)
    sec_dict = dict(zip(sec_df['security_status'], sec_df['count']))
    
    # 4. Entry Block Reasons
    block_df = pd.read_sql("SELECT entry_block_reason, count(*) as count FROM tokens GROUP BY entry_block_reason", conn)
    block_dict = dict(zip(block_df['entry_block_reason'], block_df['count']))

    with open('scratch/current_stats.txt', 'w', encoding='utf-8') as f:
        f.write(f"--- АНАЛИТИКА ОТВЕРГНУТЫХ ТОКЕНОВ ---\n")
        f.write(f"Всего токенов найдено сегодня: {total_tokens}\n\n")
        
        f.write(f"--- СТАТУСЫ ТОКЕНОВ ---\n")
        for k, v in status_dict.items():
            f.write(f"- {k}: {v}\n")
            
        f.write(f"\n--- ПРОВЕРКИ БЕЗОПАСНОСТИ (Honeypots) ---\n")
        for k, v in sec_dict.items():
            f.write(f"- {k}: {v}\n")
            
        f.write(f"\n--- ПРИЧИНЫ БЛОКИРОВКИ ПОКУПКИ ---\n")
        for k, v in block_dict.items():
            f.write(f"- {k}: {v}\n")
            
    conn.close()
    print("Done")
except Exception as e:
    with open('scratch/current_stats.txt', 'w', encoding='utf-8') as f:
        f.write(f"Error: {e}")
