"""
Decision Ledger for Solana Meme Research Lab.
Records immutable audit trail for every candidate evaluation.
"""

from __future__ import annotations

from typing import List, Optional

from core.models import (
    DecisionRecord,
    ScoreResult,
    SecurityCheckResult,
    TokenInfo,
    TokenSnapshot,
    TokenStatus,
    TradeAction,
    utc_now,
)
from database.db import Database


class DecisionLedger:
    def __init__(self, db: Database):
        self.db = db

    def record_decision(
        self,
        token: TokenInfo,
        snapshot: TokenSnapshot,
        security: SecurityCheckResult,
        score: ScoreResult,
        action: TradeAction,
    ) -> DecisionRecord:
        reasons = list(score.explanations)
        if security.is_hard_reject:
            reasons.insert(0, f"HARD REJECT: {', '.join(security.hard_reject_reasons)}")

        decision = DecisionRecord(
            token_address=token.address,
            timestamp=utc_now(),
            action=action,
            status=score.status,
            total_score=score.total_score,
            security_score=score.security_score,
            liquidity_score=score.liquidity_score,
            momentum_score=score.momentum_score,
            wallet_score=score.wallet_score,
            data_quality_score=score.data_quality_score,
            primary_reason=score.decision_reason,
            reasons=reasons,
            features_version="v1.0",
            data_sources=snapshot.data_sources,
        )

        self.db.save_decision(decision)
        return decision

    def get_recent_decisions(self, limit: int = 50) -> List[DecisionRecord]:
        return self.db.list_decisions(limit=limit)
