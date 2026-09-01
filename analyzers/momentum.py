"""
Momentum Analyzer for Solana Meme Research Lab.
Computes volume acceleration (Heat), buy pressure, trade flow, and price dynamics.
Strictly filters out dead/stale tokens (e.g. 0 trades or negligible volume).
"""

from __future__ import annotations

from typing import List, Optional

from analyzers.base import BaseAnalyzer
from core.models import MomentumMetrics, TokenSnapshot, utc_now


class MomentumAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "MomentumAnalyzer"

    def analyze(
        self,
        token_address: str,
        current_snapshot: TokenSnapshot,
        historical_snapshots: Optional[List[TokenSnapshot]] = None,
        token_age_minutes: Optional[float] = None,
    ) -> MomentumMetrics:
        vol_5m = current_snapshot.volume_5m_usd
        vol_1m = current_snapshot.volume_1m_usd
        buys = current_snapshot.buys_5m
        sells = current_snapshot.sells_5m
        total_trades = current_snapshot.trade_count_5m or (buys + sells)

        # 1. Check for Dead / Stale Activity (BABYANSE-case filter)
        is_stale = False
        explanations = []

        if total_trades == 0 or vol_5m < 10.0:
            is_stale = True
            explanations.append("DEAD_ACTIVITY: Zero or negligible trading volume (<$10) in last 5m (Score=0.0).")
            return MomentumMetrics(
                token_address=token_address,
                timestamp=utc_now(),
                price_change_5m_pct=0.0,
                volume_5m_usd=vol_5m,
                heat_1m_5m=0.0,
                buy_pressure_ratio=0.5,
                buy_count_5m=buys,
                sell_count_5m=sells,
                trade_count_5m=total_trades,
                average_trade_size_usd=0.0,
                price_step_count=0,
                large_swap_count=0,
                is_activity_stale=True,
                momentum_score=0.0,  # 0 points for dead trading
                explanations=explanations,
            )

        if total_trades < 3 or vol_5m < 100.0:
            is_stale = True
            explanations.append(f"STALE_ACTIVITY: Low trade count ({total_trades} txns / ${vol_5m:.0f} in 5m) - Momentum capped.")

        # 2. Heat Index: (Vol 1m / Vol 5m) * 100
        heat = ((vol_1m / vol_5m) * 100.0) if vol_5m > 0 else 0.0

        # 3. Buy Pressure: Buys / Total Trades
        buy_pressure = (buys / total_trades) if total_trades > 0 else 0.5

        # 4. Average Trade Size
        avg_trade_size = (vol_5m / total_trades) if total_trades > 0 else 0.0

        # 5. Price Change
        price_change_pct = 0.0
        if historical_snapshots and current_snapshot.price_usd is not None:
            prev_snaps = [s for s in historical_snapshots if s.token_address == token_address and s.price_usd is not None]
            if prev_snaps:
                earliest_price = prev_snaps[0].price_usd or 0.0
                if earliest_price > 0:
                    price_change_pct = ((current_snapshot.price_usd - earliest_price) / earliest_price) * 100.0

        # Base scoring
        score = 30.0

        if is_stale:
            score = 15.0
        else:
            # Heat assessment
            if 33.0 <= heat <= 85.0:
                score += 30.0
                explanations.append(f"+ Building/Hot momentum heat ({heat:.1f}%).")
            elif heat > 85.0:
                score += 15.0
                explanations.append(f"NOTICE: High heat index ({heat:.1f}%) - possible exhaustion spike.")
            elif heat > 0:
                score += 5.0
                explanations.append(f"NOTICE: Low heat ({heat:.1f}%).")

            # Buy Pressure assessment
            if buy_pressure >= 0.70:
                score += 25.0
                explanations.append(f"+ Strong buy pressure ({buy_pressure*100:.1f}% buys).")
            elif buy_pressure >= 0.55:
                score += 15.0
                explanations.append(f"+ Moderate buy pressure ({buy_pressure*100:.1f}% buys).")
            elif buy_pressure < 0.40:
                score -= 20.0
                explanations.append(f"WARNING: Sell pressure dominant ({buy_pressure*100:.1f}% buys).")

            # Trade Count activity
            if total_trades >= 50:
                score += 15.0
                explanations.append(f"+ High transaction frequency ({total_trades} txns / 5m).")
            elif total_trades >= 15:
                score += 10.0
                explanations.append(f"+ Active trading ({total_trades} txns / 5m).")

        momentum_score = max(0.0, min(100.0, score))

        return MomentumMetrics(
            token_address=token_address,
            timestamp=utc_now(),
            price_change_5m_pct=price_change_pct,
            volume_5m_usd=vol_5m,
            heat_1m_5m=heat,
            buy_pressure_ratio=buy_pressure,
            buy_count_5m=buys,
            sell_count_5m=sells,
            trade_count_5m=total_trades,
            average_trade_size_usd=avg_trade_size,
            price_step_count=max(0, buys // 5),
            large_swap_count=max(0, int(vol_5m // 1000)),
            is_activity_stale=is_stale,
            momentum_score=momentum_score,
            explanations=explanations,
        )
