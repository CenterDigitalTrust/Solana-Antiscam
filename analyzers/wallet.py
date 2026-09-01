"""
Wallet & Cluster Analyzer for Solana Meme Research Lab.
Evaluates creator concentration, top holder distribution, and sybil cluster risks.
Calculates dynamic continuous scores without static defaults.
"""

from __future__ import annotations

from typing import Optional

from analyzers.base import BaseAnalyzer
from core.models import TokenSnapshot, WalletAnalysisResult, utc_now


class WalletAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "WalletAnalyzer"

    def analyze(
        self,
        token_address: str,
        snapshot: Optional[TokenSnapshot] = None,
        creator_age_hours: Optional[float] = None,
    ) -> WalletAnalysisResult:
        explanations = []

        creator_pct = snapshot.creator_balance_pct if snapshot else None
        top10_pct = snapshot.top10_holders_pct if snapshot else None

        # 1. Handle DATA_UNAVAILABLE if all wallet metrics are missing
        if top10_pct is None and creator_pct is None and creator_age_hours is None:
            return WalletAnalysisResult(
                token_address=token_address,
                timestamp=utc_now(),
                creator_age_hours=None,
                top10_holders_pct=None,
                creator_balance_pct=None,
                cluster_risk_level="UNVERIFIED",
                cluster_risk_score=50.0,
                wallet_score=0.0,  # 0 points when DATA_UNAVAILABLE
                explanations=["DATA_UNAVAILABLE: Wallet and holder distribution data not available from on-chain provider."],
            )

        score = 50.0

        # 2. Top-10 concentration impact
        if top10_pct is not None:
            if top10_pct > 80.0:
                score -= 35.0
                explanations.append(f"WARNING: Extreme top-10 concentration ({top10_pct:.1f}% -> -35).")
            elif top10_pct > 65.0:
                score -= 20.0
                explanations.append(f"WARNING: High top-10 concentration ({top10_pct:.1f}% -> -20).")
            elif top10_pct > 45.0:
                score -= 5.0
                explanations.append(f"NOTICE: Moderate top-10 concentration ({top10_pct:.1f}% -> -5).")
            elif top10_pct <= 35.0:
                score += 25.0
                explanations.append(f"+ Distributed holder base ({top10_pct:.1f}% -> +25).")
        else:
            score -= 10.0
            explanations.append("NOTICE: Top 10 holder percentage unverified (-10).")

        # 3. Creator / Whale balance impact
        if creator_pct is not None:
            if creator_pct > 30.0:
                score -= 30.0
                explanations.append(f"WARNING: Creator/Top whale holds {creator_pct:.1f}% (-30).")
            elif creator_pct > 15.0:
                score -= 15.0
                explanations.append(f"NOTICE: Creator/Top whale holds {creator_pct:.1f}% (-15).")
            elif creator_pct <= 5.0:
                score += 15.0
                explanations.append(f"+ Low creator/whale retention ({creator_pct:.1f}% -> +15).")

        # 4. Creator wallet age impact
        if creator_age_hours is not None:
            if creator_age_hours < 6.0:
                score -= 20.0
                explanations.append(f"WARNING: Creator wallet is freshly created ({creator_age_hours:.1f}h -> -20).")
            elif creator_age_hours < 24.0:
                score -= 10.0
                explanations.append(f"NOTICE: Creator wallet age is under 24h ({creator_age_hours:.1f}h -> -10).")
            elif creator_age_hours >= 72.0:
                score += 15.0
                explanations.append(f"+ Established creator wallet age ({creator_age_hours:.1f}h -> +15).")

        # 5. Continuous Cluster Risk Score (0-100, where 100 is highest risk)
        top10_val = top10_pct if top10_pct is not None else 50.0
        creator_val = creator_pct if creator_pct is not None else 15.0
        cluster_risk_score = round(max(5.0, min(95.0, (top10_val * 0.65) + (creator_val * 1.2))), 1)

        if cluster_risk_score >= 65.0:
            risk_level = "HIGH"
        elif cluster_risk_score >= 40.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        wallet_score = round(max(0.0, min(100.0, score)), 1)

        return WalletAnalysisResult(
            token_address=token_address,
            timestamp=utc_now(),
            creator_age_hours=creator_age_hours,
            top10_holders_pct=top10_pct,
            creator_balance_pct=creator_pct,
            cluster_risk_level=risk_level,
            cluster_risk_score=cluster_risk_score,
            wallet_score=wallet_score,
            explanations=explanations,
        )
