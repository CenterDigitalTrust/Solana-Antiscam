"""
Configurable Scoring Engine for Solana Meme Research Lab.
Computes explainable composite research score across 6 distinct dimensions:
1. Security (25%)
2. Liquidity (20%)
3. Wallet (15%)
4. Market (15%)
5. Momentum (20%)
6. Data Quality (5%)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from core.models import (
    LiquidityMetrics,
    MomentumMetrics,
    ScoreResult,
    SecurityCheckResult,
    TokenInfo,
    TokenSnapshot,
    TokenStatus,
    WalletAnalysisResult,
    utc_now,
)


@dataclass
class ScoreWeights:
    security: float = 0.25
    liquidity: float = 0.20
    wallet: float = 0.15
    market: float = 0.15
    momentum: float = 0.20
    data_quality: float = 0.05

    def normalize(self) -> None:
        total = self.security + self.liquidity + self.wallet + self.market + self.momentum + self.data_quality
        if total > 0:
            self.security /= total
            self.liquidity /= total
            self.wallet /= total
            self.market /= total
            self.momentum /= total
            self.data_quality /= total


class ScoreEngine:
    def __init__(
        self,
        weights: Optional[ScoreWeights] = None,
        candidate_threshold: float = 70.0,
        reject_threshold: float = 40.0,
    ):
        self.weights = weights or ScoreWeights()
        self.weights.normalize()
        self.candidate_threshold = candidate_threshold
        self.reject_threshold = reject_threshold

    def calculate_score(
        self,
        token: TokenInfo,
        snapshot: TokenSnapshot,
        security: SecurityCheckResult,
        liquidity: LiquidityMetrics,
        momentum: MomentumMetrics,
        wallet: Optional[WalletAnalysisResult] = None,
    ) -> ScoreResult:
        # 1. Market Subscore (15% weight)
        market_score = 50.0
        if snapshot.volume_24h_usd == 0 and snapshot.volume_5m_usd == 0:
            market_score = 10.0  # Zero trading volume
        elif snapshot.volume_5m_usd >= 5000:
            market_score = 85.0
        elif snapshot.volume_5m_usd >= 1000:
            market_score = 70.0
        elif snapshot.volume_5m_usd >= 200:
            market_score = 50.0
        else:
            market_score = 30.0

        if snapshot.market_cap_usd and snapshot.liquidity_usd and snapshot.liquidity_usd > 0:
            mcap_liq_ratio = snapshot.market_cap_usd / snapshot.liquidity_usd
            if 1.5 <= mcap_liq_ratio <= 10.0:
                market_score = min(100.0, market_score + 15.0)
            elif mcap_liq_ratio > 40.0:
                market_score = max(0.0, market_score - 20.0)

        market_score = round(max(0.0, min(100.0, market_score)), 1)

        # 2. Extract Subscores
        sec_score = round(security.soft_security_score, 1) if security.soft_security_score is not None else None
        liq_score = round(liquidity.liquidity_score, 1)
        mom_score = round(momentum.momentum_score, 1)
        wal_score = round(wallet.wallet_score if wallet else 60.0, 1)
        dq_score = round(snapshot.data_quality_score, 1)

        # 3. Composite Weighted Calculation
        status = TokenStatus.WATCH
        decision_reason = ""
        explanations: List[str] = []

        if sec_score is None:
            # Cannot score an unverified or blocked token
            total_score = None
            status = TokenStatus.REJECT
            decision_reason = "SECURITY_UNVERIFIED"
            explanations.append("GUARDRAIL: Token cannot qualify without verified security data.")
        else:
            total = (
                (sec_score * self.weights.security)
                + (liq_score * self.weights.liquidity)
                + (wal_score * self.weights.wallet)
                + (market_score * self.weights.market)
                + (mom_score * self.weights.momentum)
                + (dq_score * self.weights.data_quality)
            )
            total_score = round(max(0.0, min(100.0, total)), 1)
            
            # 4. Status Determination with Guardrails
            if security.is_hard_reject:
                status = TokenStatus.REJECT
                decision_reason = f"HARD REJECT: {', '.join(security.hard_reject_reasons)}"
                explanations.extend(security.explanations)
            elif liquidity.is_data_unavailable:
                status = TokenStatus.REJECT
                decision_reason = f"Liquidity data unavailable"
                explanations.append("GUARDRAIL: Token cannot qualify without verified liquidity data.")
            elif momentum.is_activity_stale:
                status = TokenStatus.REJECT
                decision_reason = f"Stale/dead trading activity"
                explanations.append("GUARDRAIL: Token cannot qualify with stale trading activity.")
            elif total_score < self.reject_threshold:
                status = TokenStatus.REJECT
                decision_reason = f"Low composite score ({total_score:.1f} < {self.reject_threshold})"
            elif total_score >= self.candidate_threshold:
                status = TokenStatus.CANDIDATE
                decision_reason = f"Candidate threshold met ({total_score:.1f} >= {self.candidate_threshold})"
            else:
                status = TokenStatus.WATCH
                decision_reason = f"Monitoring in progress ({total_score:.1f})"

        if security.explanations and not security.is_hard_reject:
            explanations.extend(security.explanations)
        explanations.extend(liquidity.explanations)
        explanations.extend(momentum.explanations)

        breakdown = {
            "security": sec_score if sec_score is not None else 0.0,
            "liquidity": liq_score,
            "wallet": wal_score,
            "market": market_score,
            "momentum": mom_score,
            "data_quality": dq_score,
            "total": total_score if total_score is not None else 0.0,
        }

        return ScoreResult(
            token_address=token.address,
            timestamp=utc_now(),
            total_score=total_score,
            security_score=sec_score,
            liquidity_score=liq_score,
            wallet_score=wal_score,
            market_score=market_score,
            momentum_score=mom_score,
            data_quality_score=dq_score,
            status=status,
            decision_reason=decision_reason,
            breakdown=breakdown,
            explanations=explanations,
        )
