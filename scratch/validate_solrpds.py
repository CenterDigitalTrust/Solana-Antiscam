import csv
import json
import glob
import os
from datetime import datetime

csv_files = sorted(glob.glob("c:/Users/User/Desktop/AGIVIP/SolRPDS-main/dataset/CSV/*.csv"))
total_records = 0
unique_pools = set()
unique_mints = set()
status_counts = {}
field_names = []
min_date = None
max_date = None
file_breakdowns = {}
missing_counts = {}

for f in csv_files:
    fname = os.path.basename(f)
    with open(f, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        field_names = reader.fieldnames or []
        f_records = 0
        f_statuses = {}
        for row in reader:
            f_records += 1
            total_records += 1
            pool = row.get("LIQUIDITY_POOL_ADDRESS")
            mint = row.get("MINT")
            if pool:
                unique_pools.add(pool)
            if mint:
                unique_mints.add(mint)
            
            st = row.get("INACTIVITY_STATUS", "UNKNOWN")
            f_statuses[st] = f_statuses.get(st, 0) + 1
            status_counts[st] = status_counts.get(st, 0) + 1
            
            # Check missing
            for k, v in row.items():
                if v is None or v == "" or v == "null":
                    missing_counts[k] = missing_counts.get(k, 0) + 1
            
            # Timestamps
            first_ts = row.get("FIRST_POOL_ACTIVITY_TIMESTAMP")
            last_ts = row.get("LAST_SWAP_TIMESTAMP")
            last_pool_ts = row.get("LAST_POOL_ACTIVITY_TIMESTAMP")
            
            for ts_str in [first_ts, last_pool_ts, last_ts]:
                if ts_str and ts_str != "null" and ts_str != "":
                    try:
                        clean_ts = ts_str.split(".")[0]
                        dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                        if min_date is None or dt < min_date:
                            min_date = dt
                        if max_date is None or dt > max_date:
                            max_date = dt
                    except Exception:
                        pass
        file_breakdowns[fname] = {
            "records": f_records,
            "statuses": f_statuses
        }

print("=== SolRPDS DATASET VALIDATION ===")
print(f"Total CSV Files: {len(csv_files)}")
print(f"Total Records: {total_records}")
print(f"Unique Liquidity Pools: {len(unique_pools)}")
print(f"Unique Mints: {len(unique_mints)}")
print(f"Date Range: {min_date} -> {max_date}")
print(f"Fields: {field_names}")
print(f"Status Counts: {status_counts}")
print(f"Missing Values per field: {missing_counts}")
print("\nFile Breakdowns:")
for fn, fb in file_breakdowns.items():
    print(f"  {fn}: {fb['records']} records, Statuses: {fb['statuses']}")
