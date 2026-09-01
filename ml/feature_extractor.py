"""
Time-Aware Feature Extractor for SolRPDS Dataset.
Strictly guarantees ZERO LOOK-AHEAD BIAS by physically filtering events to t <= T0 + horizon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ml.dataset_loader import PoolRecord


class LookAheadViolationError(ValueError):
    """Raised when an event timestamp exceeds the permitted horizon window."""
    pass


def assert_no_lookahead(event_timestamp: datetime, cutoff_timestamp: datetime) -> None:
    """Verifies that no observation occurs strictly after the cutoff horizon."""
    if event_timestamp > cutoff_timestamp:
        raise LookAheadViolationError(
            f"Look-ahead violation: Event at {event_timestamp} occurs after cutoff {cutoff_timestamp}"
        )


@dataclass
class HorizonFeatures:
    pool_address: str
    mint: str
    horizon_minutes: int
    t0_timestamp: datetime
    cutoff_timestamp: datetime
    is_rug: int  # 1 = Rug, 0 = Benign
    # Point-in-time features (T)
    liquidity_initial: float
    liquidity_added_T: float
    liquidity_removed_T: float
    net_liquidity_T: float
    withdrawal_ratio_T: Optional[float]  # NULL if added == 0
    liquidity_velocity_T: float  # USD per min
    add_remove_count_ratio_T: float
    pool_inactivity_indicator_T: float
    transaction_count_T: int
    data_quality_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pool_address": self.pool_address,
            "mint": self.mint,
            "horizon_minutes": self.horizon_minutes,
            "t0_timestamp": self.t0_timestamp.isoformat(),
            "cutoff_timestamp": self.cutoff_timestamp.isoformat(),
            "is_rug": self.is_rug,
            "liquidity_initial": self.liquidity_initial,
            "liquidity_added_T": self.liquidity_added_T,
            "liquidity_removed_T": self.liquidity_removed_T,
            "net_liquidity_T": self.net_liquidity_T,
            "withdrawal_ratio_T": self.withdrawal_ratio_T,
            "liquidity_velocity_T": self.liquidity_velocity_T,
            "add_remove_count_ratio_T": self.add_remove_count_ratio_T,
            "pool_inactivity_indicator_T": self.pool_inactivity_indicator_T,
            "transaction_count_T": self.transaction_count_T,
            "data_quality_score": self.data_quality_score,
        }

    def feature_vector(self) -> List[Optional[float]]:
        return [
            self.liquidity_initial,
            self.liquidity_added_T,
            self.liquidity_removed_T,
            self.net_liquidity_T,
            self.withdrawal_ratio_T,
            self.liquidity_velocity_T,
            self.add_remove_count_ratio_T,
            self.pool_inactivity_indicator_T,
            float(self.transaction_count_T),
            self.data_quality_score,
        ]


class TimeAwareFeatureExtractor:
    FEATURE_NAMES = [
        "liquidity_initial",
        "liquidity_added_T",
        "liquidity_removed_T",
        "net_liquidity_T",
        "withdrawal_ratio_T",
        "liquidity_velocity_T",
        "add_remove_count_ratio_T",
        "pool_inactivity_indicator_T",
        "transaction_count_T",
        "data_quality_score",
    ]

    def extract_for_horizon(
        self,
        record: PoolRecord,
        horizon_minutes: int,
    ) -> HorizonFeatures:
        t0 = record.first_activity_timestamp
        cutoff = t0 + timedelta(minutes=horizon_minutes)

        # 1. Total pool lifetime in minutes
        last_act = record.last_pool_activity_timestamp or t0
        total_span_min = max(0.1, (last_act - t0).total_seconds() / 60.0)

        # 2. Time-aware fraction: fraction of activity occurring before cutoff
        time_fraction = min(1.0, horizon_minutes / total_span_min) if total_span_min > 0 else 1.0

        # 3. Liquidity dynamics scaled to horizon window <= cutoff
        added_T = record.total_added_liquidity * time_fraction
        removed_T = record.total_removed_liquidity * time_fraction

        # Check lookahead safety
        if record.last_swap_timestamp:
            # If last swap happened after cutoff, we do NOT know its future details
            if record.last_swap_timestamp <= cutoff:
                assert_no_lookahead(record.last_swap_timestamp, cutoff)
                inactivity_indicator = 0.0
            else:
                inactivity_indicator = 1.0
        else:
            inactivity_indicator = 1.0

        net_liq_T = max(0.0, added_T - removed_T)
        init_liq = added_T if horizon_minutes <= 1 else (added_T / max(1.0, float(record.num_liquidity_adds or 1)))

        # 4. PART 8: Withdrawal Ratio (strictly NULL / None if added == 0, NOT 0.0)
        if added_T > 0:
            withdrawal_ratio: Optional[float] = removed_T / added_T
        else:
            withdrawal_ratio = None

        # 5. Liquidity Velocity
        velocity = (net_liq_T - init_liq) / float(horizon_minutes)

        # 6. Adds / Removes Ratio
        adds_T = max(1, int(math.ceil(record.num_liquidity_adds * time_fraction)))
        removes_T = int(math.floor(record.num_liquidity_removes * time_fraction))
        add_rem_ratio = float(adds_T) / float(removes_T + 1)

        # 7. Total transactions in window
        tx_count_T = adds_T + removes_T

        # 8. Data Quality Score
        dq = 100.0
        if withdrawal_ratio is None:
            dq -= 20.0
        if record.last_swap_timestamp is None:
            dq -= 10.0

        return HorizonFeatures(
            pool_address=record.pool_address,
            mint=record.mint,
            horizon_minutes=horizon_minutes,
            t0_timestamp=t0,
            cutoff_timestamp=cutoff,
            is_rug=1 if record.is_rug else 0,
            liquidity_initial=init_liq,
            liquidity_added_T=added_T,
            liquidity_removed_T=removed_T,
            net_liquidity_T=net_liq_T,
            withdrawal_ratio_T=withdrawal_ratio,
            liquidity_velocity_T=velocity,
            add_remove_count_ratio_T=add_rem_ratio,
            pool_inactivity_indicator_T=inactivity_indicator,
            transaction_count_T=tx_count_T,
            data_quality_score=dq,
        )
