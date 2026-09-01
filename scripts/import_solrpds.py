"""
SolRPDS Importer and Time-Aware Feature Extractor Preparation (for Phase 2).
Prepares historical ground truth datasets without look-ahead bias.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_solrpds_sample(csv_path: Path, max_rows: int = 500) -> List[Dict[str, str]]:
    """Parse SolRPDS pool records for historical ML preparation."""
    records = []
    if not csv_path.exists():
        print(f"[-] Dataset file not found: {csv_path}")
        return records

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            records.append(row)

    print(f"[+] Loaded {len(records)} historical records from {csv_path.name}")
    return records


if __name__ == "__main__":
    solrpds_dir = PROJECT_ROOT.parent / "SolRPDS-main" / "dataset" / "CSV"
    target_csv = solrpds_dir / "2021.csv"
    sample = parse_solrpds_sample(target_csv, max_rows=10)
    if sample:
        print("[*] Sample record fields:")
        for k, v in list(sample[0].items())[:8]:
            print(f"    {k}: {v}")
