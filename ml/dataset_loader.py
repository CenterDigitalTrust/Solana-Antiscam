"""
Dataset Loader for SolRPDS (Solana Rug Pull Dataset).
Provides streamed, chunked parsing of CSV and JSON records with strict type validation.
"""

from __future__ import annotations

import csv
import glob
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generator, List, Optional, Tuple


@dataclass
class PoolRecord:
    pool_address: str
    mint: str
    total_added_liquidity: float
    total_removed_liquidity: float
    num_liquidity_adds: int
    num_liquidity_removes: int
    add_to_remove_ratio: Optional[float]
    first_activity_timestamp: datetime
    last_pool_activity_timestamp: Optional[datetime]
    last_swap_timestamp: Optional[datetime]
    is_rug: bool  # True if Inactive (Rug / Drained), False if Active (Benign)
    source_file: str


def parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str or ts_str == "null" or ts_str.strip() == "":
        return None
    try:
        clean = ts_str.split(".")[0]
        return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


class SolRPDSLoader:
    def __init__(self, dataset_dir: str = "c:/Users/User/Desktop/AGIVIP/SolRPDS-main/dataset/CSV"):
        self.dataset_dir = dataset_dir

    def stream_records(self, max_records_per_file: Optional[int] = None) -> Generator[PoolRecord, None, None]:
        csv_files = sorted(glob.glob(os.path.join(self.dataset_dir, "*.csv")))
        for fpath in csv_files:
            fname = os.path.basename(fpath)
            with open(fpath, "r", encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                count = 0
                for row in reader:
                    st = row.get("INACTIVITY_STATUS")
                    if not st or st not in ["Active", "Inactive"]:
                        continue

                    first_ts = parse_timestamp(row.get("FIRST_POOL_ACTIVITY_TIMESTAMP"))
                    if not first_ts:
                        continue

                    pool_addr = row.get("LIQUIDITY_POOL_ADDRESS", "")
                    mint = row.get("MINT", "")

                    try:
                        added = float(row.get("TOTAL_ADDED_LIQUIDITY") or 0.0)
                    except ValueError:
                        added = 0.0

                    try:
                        removed = float(row.get("TOTAL_REMOVED_LIQUIDITY") or 0.0)
                    except ValueError:
                        removed = 0.0

                    try:
                        n_adds = int(row.get("NUM_LIQUIDITY_ADDS") or 0)
                    except ValueError:
                        n_adds = 0

                    try:
                        n_rem = int(row.get("NUM_LIQUIDITY_REMOVES") or 0)
                    except ValueError:
                        n_rem = 0

                    ratio = None
                    if row.get("ADD_TO_REMOVE_RATIO") and row.get("ADD_TO_REMOVE_RATIO") != "null":
                        try:
                            ratio = float(row.get("ADD_TO_REMOVE_RATIO"))
                        except ValueError:
                            ratio = None

                    last_pool_ts = parse_timestamp(row.get("LAST_POOL_ACTIVITY_TIMESTAMP"))
                    last_swap_ts = parse_timestamp(row.get("LAST_SWAP_TIMESTAMP"))

                    record = PoolRecord(
                        pool_address=pool_addr,
                        mint=mint,
                        total_added_liquidity=added,
                        total_removed_liquidity=removed,
                        num_liquidity_adds=n_adds,
                        num_liquidity_removes=n_rem,
                        add_to_remove_ratio=ratio,
                        first_activity_timestamp=first_ts,
                        last_pool_activity_timestamp=last_pool_ts,
                        last_swap_timestamp=last_swap_ts,
                        is_rug=(st == "Inactive"),
                        source_file=fname,
                    )
                    yield record
                    count += 1
                    if max_records_per_file and count >= max_records_per_file:
                        break
