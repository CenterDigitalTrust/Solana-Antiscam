import csv
import glob
import json
import os
from datetime import datetime

csv_files = sorted(glob.glob("c:/Users/User/Desktop/AGIVIP/SolRPDS-main/dataset/CSV/*.csv"))

train_pools = set()
val_pools = set()
test_pools = set()

train_records = 0
val_records = 0
test_records = 0

train_rugs = 0
val_rugs = 0
test_rugs = 0

total_records = 0
all_rugs = 0
all_benign = 0

min_date = None
max_date = None

for f in csv_files:
    with open(f, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            st = row.get("INACTIVITY_STATUS")
            if not st or st not in ["Active", "Inactive"]:
                continue
            
            is_rug = (st == "Inactive")
            if is_rug:
                all_rugs += 1
            else:
                all_benign += 1
            total_records += 1
            
            first_ts_str = row.get("FIRST_POOL_ACTIVITY_TIMESTAMP")
            if not first_ts_str or first_ts_str == "null":
                continue
            
            clean_ts = first_ts_str.split(".")[0]
            dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
            
            if min_date is None or dt < min_date:
                min_date = dt
            if max_date is None or dt > max_date:
                max_date = dt
                
            pool_addr = row.get("LIQUIDITY_POOL_ADDRESS")
            
            # Temporal partition:
            # Train: < 2024-01-01
            # Validation: 2024-01-01 to 2024-06-30
            # Test: >= 2024-07-01
            if dt < datetime(2024, 1, 1):
                train_records += 1
                if is_rug:
                    train_rugs += 1
                if pool_addr:
                    train_pools.add(pool_addr)
            elif dt < datetime(2024, 7, 1):
                val_records += 1
                if is_rug:
                    val_rugs += 1
                if pool_addr:
                    val_pools.add(pool_addr)
            else:
                test_records += 1
                if is_rug:
                    test_rugs += 1
                if pool_addr:
                    test_pools.add(pool_addr)

unique_total_pools = len(train_pools | val_pools | test_pools)

report = {
    "dataset_name": "SolRPDS",
    "total_records": total_records,
    "total_unique_pools": unique_total_pools,
    "date_min": min_date.strftime("%Y-%m-%d %H:%M:%S") if min_date else None,
    "date_max": max_date.strftime("%Y-%m-%d %H:%M:%S") if max_date else None,
    "rug_pools_total": all_rugs,
    "benign_pools_total": all_benign,
    "rug_rate_overall_pct": round((all_rugs / total_records) * 100.0, 2),
    "splits": {
        "train": {
            "epoch": "2021-02-14 to 2023-12-31",
            "records": train_records,
            "unique_pools": len(train_pools),
            "rug_count": train_rugs,
            "benign_count": train_records - train_rugs,
            "rug_rate_pct": round((train_rugs / train_records) * 100.0, 2) if train_records else 0,
        },
        "validation": {
            "epoch": "2024-01-01 to 2024-06-30 (Q1-Q2 2024)",
            "records": val_records,
            "unique_pools": len(val_pools),
            "rug_count": val_rugs,
            "benign_count": val_records - val_rugs,
            "rug_rate_pct": round((val_rugs / val_records) * 100.0, 2) if val_records else 0,
        },
        "test": {
            "epoch": "2024-07-01 to 2024-11-01 (Q3-Q4 2024 Out-Of-Time)",
            "records": test_records,
            "unique_pools": len(test_pools),
            "rug_count": test_rugs,
            "benign_count": test_records - test_rugs,
            "rug_rate_pct": round((test_rugs / test_records) * 100.0, 2) if test_records else 0,
        }
    }
}

os.makedirs("ml", exist_ok=True)
with open("ml/dataset_report.json", "w", encoding="utf-8") as fp:
    json.dump(report, fp, indent=4)

print("Generated ml/dataset_report.json:")
print(json.dumps(report, indent=2))
