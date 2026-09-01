import csv
import glob
import os

files = glob.glob("c:/Users/User/Desktop/AGIVIP/SolRPDS-main/dataset/CSV/*.csv")
for f in sorted(files):
    fname = os.path.basename(f)
    with open(f, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        statuses = {}
        count = 0
        earliest = None
        latest = None
        for row in reader:
            count += 1
            st = row.get("INACTIVITY_STATUS", "UNKNOWN")
            statuses[st] = statuses.get(st, 0) + 1
            first_ts = row.get("FIRST_POOL_ACTIVITY_TIMESTAMP")
            last_ts = row.get("LAST_SWAP_TIMESTAMP")
            if first_ts:
                if earliest is None or first_ts < earliest:
                    earliest = first_ts
            if last_ts:
                if latest is None or last_ts > latest:
                    latest = last_ts
        print(f"File: {fname} | Total Pools: {count}")
        print(f"  Statuses: {statuses}")
        print(f"  Date Range: {earliest} -> {latest}")
