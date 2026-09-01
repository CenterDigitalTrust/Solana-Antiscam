"""
Liquidity Analyzer for Solana Meme Research Lab.
Maintains L(t) time series and calculates liquidity velocity, acceleration, and withdrawal ratios.
Correctly handles DATA_UNAVAILABLE without awarding default scores.
"""

from __future__ import annotations

from typing import List, Optional

from analyzers.base import BaseAnalyzer
from core.models import LiquidityMetrics, TokenSnapshot, utc_now


class LiquidityAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "LiquidityAnalyzer"

    def analyze(
        self,
        token_address: str,
        current_snapshot: TokenSnapshot,
        historical_snapshots: Optional[List[TokenSnapshot]] = None,
    ) -> LiquidityMetrics:
        cur_liq = current_snapshot.liquidity_usd

        # 1. Handle DATA_UNAVAILABLE
        if cur_liq is None:
            return LiquidityMetrics(
                token_address=token_address,
                timestamp=utc_now(),
                current_liquidity_usd=None,
                delta_liquidity_5m=None,
                liquidity_velocity_usd_per_min=None,
                liquidity_acceleration=None,
                withdrawal_ratio=None,
                volume_to_liquidity_ratio=None,
                liquidity_score=0.0,  # 0 points when DATA_UNAVAILABLE
                has_sufficient_history=False,
                is_data_unavailable=True,
                explanations=["DATA_UNAVAILABLE: Liquidity not available from providers (Score=0.0)."],
            )

        # 2. Handle Measured Zero Liquidity ($0 measured)
        if cur_liq <= 0.0:
            return LiquidityMetrics(
                token_address=token_address,
                timestamp=utc_now(),
                current_liquidity_usd=0.0,
                delta_liquidity_5m=None,
                liquidity_velocity_usd_per_min=None,
                liquidity_acceleration=None,
                withdrawal_ratio=1.0,
                volume_to_liquidity_ratio=None,
                liquidity_score=0.0,
                has_sufficient_history=False,
                is_data_unavailable=False,
                explanations=["CRITICAL: Measured liquidity is $0.0 (Liquidity drained / uninitialized)."],
            )

        vol_5m = current_snapshot.volume_5m_usd
        v_l_ratio = (vol_5m / cur_liq) if cur_liq > 0 else 0.0

        history = sorted(
            [s for s in (historical_snapshots or []) if s.token_address == token_address and s.liquidity_usd is not None],
            key=lambda s: s.timestamp,
        )

        all_snaps = history + [current_snapshot]

        if len(all_snaps) < 2:
            # Baseline scoring for single valid snapshot
            score = 40.0
            if cur_liq >= 50000:
                score = 80.0
            elif cur_liq >= 20000:
                score = 70.0
            elif cur_liq >= 10000:
                score = 60.0
            elif cur_liq >= 3000:
                score = 50.0
            elif cur_liq < 1000:
                score = 20.0

            return LiquidityMetrics(
                token_address=token_address,
                timestamp=utc_now(),
                current_liquidity_usd=cur_liq,
                delta_liquidity_5m=None,
                liquidity_velocity_usd_per_min=None,
                liquidity_acceleration=None,
                withdrawal_ratio=None,
                volume_to_liquidity_ratio=v_l_ratio,
                liquidity_score=score,
                has_sufficient_history=False,
                is_data_unavailable=False,
                explanations=[f"Single snapshot baseline: Pool liquidity is ${cur_liq:,.0f} (INSUFFICIENT_HISTORY for velocity)."],
            )

        # Multi-snapshot time series calculation
        prev = all_snaps[-2]
        prev_liq = prev.liquidity_usd or 0.0
        time_diff_min = max(0.1, (current_snapshot.timestamp - prev.timestamp).total_seconds() / 60.0)
        delta_liq = cur_liq - prev_liq
        velocity = delta_liq / time_diff_min  # USD per minute

        acceleration: Optional[float] = None
        if len(all_snaps) >= 3:
            prev_prev = all_snaps[-3]
            prev_prev_liq = prev_prev.liquidity_usd or 0.0
            t_prev_min = max(0.1, (prev.timestamp - prev_prev.timestamp).total_seconds() / 60.0)
            prev_velocity = (prev_liq - prev_prev_liq) / t_prev_min
            acceleration = (velocity - prev_velocity) / time_diff_min

        explanations = []
        score = 60.0

        if cur_liq >= 30000:
            score += 20.0
            explanations.append(f"+ Deep liquidity pool (${cur_liq:,.0f}).")
        elif cur_liq >= 10000:
            score += 10.0
            explanations.append(f"+ Healthy liquidity pool (${cur_liq:,.0f}).")
        elif cur_liq < 2000:
            score -= 30.0
            explanations.append(f"WARNING: Shallow liquidity (${cur_liq:,.0f}).")

        if velocity < -500.0:
            score -= 35.0
            explanations.append(f"CRITICAL WARNING: Fast liquidity drain (${velocity:.1f}/min).")
        elif velocity < 0:
            score -= 10.0
            explanations.append(f"NOTICE: Negative liquidity velocity (${velocity:.1f}/min).")
        elif velocity > 200.0:
            score += 10.0
            explanations.append(f"+ Strong positive liquidity addition (${velocity:.1f}/min).")

        withdrawal_ratio = max(0.0, -delta_liq / prev_liq) if prev_liq > 0 and delta_liq < 0 else 0.0
        if withdrawal_ratio > 0.3:
            score -= 25.0
            explanations.append(f"WARNING: Substantial liquidity reduction ({withdrawal_ratio*100:.1f}%).")

        liquidity_score = max(0.0, min(100.0, score))

        return LiquidityMetrics(
            token_address=token_address,
            timestamp=utc_now(),
            current_liquidity_usd=cur_liq,
            delta_liquidity_5m=delta_liq,
            liquidity_velocity_usd_per_min=velocity,
            liquidity_acceleration=acceleration,
            withdrawal_ratio=withdrawal_ratio,
            volume_to_liquidity_ratio=v_l_ratio,
            liquidity_score=liquidity_score,
            has_sufficient_history=True,
            is_data_unavailable=False,
            explanations=explanations,
        )
