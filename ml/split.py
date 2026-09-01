"""
Walk-Forward Temporal Splitter for SolRPDS Dataset.
Partitions records strictly by epoch:
- TRAIN: 2021-02-14 to 2023-12-31
- VALIDATION: 2024-01-01 to 2024-06-30
- TEST: 2024-07-01 to 2024-11-01
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from ml.dataset_loader import PoolRecord


class TemporalSplitter:
    def __init__(
        self,
        train_end: datetime = datetime(2024, 1, 1),
        val_end: datetime = datetime(2024, 7, 1),
    ):
        self.train_end = train_end
        self.val_end = val_end

    def get_split_name(self, record: PoolRecord) -> str:
        t0 = record.first_activity_timestamp
        if t0 < self.train_end:
            return "train"
        elif t0 < self.val_end:
            return "validation"
        else:
            return "test"

    def split_records(
        self, records: List[PoolRecord]
    ) -> Dict[str, List[PoolRecord]]:
        splits: Dict[str, List[PoolRecord]] = {
            "train": [],
            "validation": [],
            "test": [],
        }
        for rec in records:
            split_name = self.get_split_name(rec)
            splits[split_name].append(rec)
        return splits
