"""
Feature Store for Solana Meme Research Lab.
Extracts standard feature records according to FEATURE_CATALOG.md.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings
from core.models import (
    LiquidityMetrics,
    MomentumMetrics,
    ScoreResult,
    SecurityCheckResult,
    TokenInfo,
    TokenSnapshot,
    WalletAnalysisResult,
    utc_now,
)
from database.db import Database


@dataclass
class FeatureRecord:
    token_address: str
    feature_name: str
    feature_value: Optional[float]
    feature_str_value: Optional[str]
    timestamp: datetime
    source: str
    calculation_version: str = "v1.0"


class FeatureStore:
    def __init__(self, db: Database, parquet_path: Optional[Path] = None):
        self.db = db
        self.parquet_path = parquet_path or settings.FEATURE_STORE_PATH

    def extract_features(
        self,
        token: TokenInfo,
        snapshot: TokenSnapshot,
        security: SecurityCheckResult,
        liquidity: LiquidityMetrics,
        momentum: MomentumMetrics,
        score: ScoreResult,
        wallet: Optional[WalletAnalysisResult] = None,
        history: Optional[List[TokenSnapshot]] = None,
    ) -> List[FeatureRecord]:
        now = snapshot.timestamp or utc_now()
        version = "v1.0"
        records: List[FeatureRecord] = []

        # Strict Look-Ahead Guard: Filter history strictly to <= snapshot.timestamp
        valid_history = [
            s for s in (history or [])
            if s.token_address == token.address and s.timestamp <= now
        ]
        valid_history.sort(key=lambda s: s.timestamp)

        # 1. Security Features
        records.append(FeatureRecord(token.address, "mint_authority_disabled", 1.0 if not security.is_mintable else 0.0, None, now, "Helius", version))
        records.append(FeatureRecord(token.address, "freeze_authority_disabled", 1.0 if not security.is_freezable else 0.0, None, now, "Helius", version))
        records.append(FeatureRecord(token.address, "is_metadata_mutable", 1.0 if security.is_mutable else 0.0, None, now, "Helius", version))
        records.append(FeatureRecord(token.address, "transfer_fee_basis_points", float(security.transfer_fee_bps), None, now, "Helius", version))
        records.append(FeatureRecord(token.address, "top10_holders_pct", security.top10_holders_pct, None, now, "Helius", version))
        records.append(FeatureRecord(token.address, "creator_balance_pct", security.creator_balance_pct, None, now, "Helius", version))
        records.append(FeatureRecord(token.address, "security_verified", 1.0 if security.security_verified else 0.0, None, now, "SecurityAnalyzer", version))

        # 2. Liquidity Features
        records.append(FeatureRecord(token.address, "liquidity_usd", snapshot.liquidity_usd, None, now, "DexScreener", version))
        records.append(FeatureRecord(token.address, "liquidity_velocity_5m", liquidity.liquidity_velocity_usd_per_min, None, now, "SnapshotDiff", version))
        records.append(FeatureRecord(token.address, "liquidity_acceleration_5m", liquidity.liquidity_acceleration, None, now, "SnapshotDiff", version))
        records.append(FeatureRecord(token.address, "volume_to_liquidity_ratio", liquidity.volume_to_liquidity_ratio, None, now, "Calc", version))

        # 3. Momentum & Flow Features
        records.append(FeatureRecord(token.address, "heat_1m_5m", momentum.heat_1m_5m, None, now, "DexScreener", version))
        records.append(FeatureRecord(token.address, "volume_5m_usd", snapshot.volume_5m_usd, None, now, "DexScreener", version))
        records.append(FeatureRecord(token.address, "buy_count_5m", float(snapshot.buys_5m), None, now, "DexScreener", version))
        records.append(FeatureRecord(token.address, "sell_count_5m", float(snapshot.sells_5m), None, now, "DexScreener", version))
        records.append(FeatureRecord(token.address, "buy_pressure_ratio", momentum.buy_pressure_ratio, None, now, "Calc", version))
        records.append(FeatureRecord(token.address, "trade_count_5m", float(snapshot.trade_count_5m), None, now, "DexScreener", version))

        # 4. Temporal Multi-Horizon Growth Features (1m, 3m, 5m)
        cur_p = snapshot.price_usd or 0.0
        cur_liq = snapshot.liquidity_usd or 0.0
        cur_vol = snapshot.volume_5m_usd or 0.0

        p_growth_1m = None
        p_growth_3m = None
        p_growth_5m = None
        liq_change_5m = None
        liq_drop_5m = 0.0

        for h in valid_history:
            delta_min = (now - h.timestamp).total_seconds() / 60.0
            if delta_min >= 0.8 and delta_min <= 1.5 and p_growth_1m is None and h.price_usd and h.price_usd > 0:
                p_growth_1m = ((cur_p - h.price_usd) / h.price_usd) * 100.0
            if delta_min >= 2.5 and delta_min <= 3.5 and p_growth_3m is None and h.price_usd and h.price_usd > 0:
                p_growth_3m = ((cur_p - h.price_usd) / h.price_usd) * 100.0
            if delta_min >= 4.5 and delta_min <= 6.0 and p_growth_5m is None and h.price_usd and h.price_usd > 0:
                p_growth_5m = ((cur_p - h.price_usd) / h.price_usd) * 100.0
                if h.liquidity_usd and h.liquidity_usd > 0:
                    liq_change_5m = cur_liq - h.liquidity_usd
                    if cur_liq < h.liquidity_usd:
                        liq_drop_5m = ((h.liquidity_usd - cur_liq) / h.liquidity_usd) * 100.0

        records.append(FeatureRecord(token.address, "price_growth_1m", p_growth_1m, None, now, "TimeDiff", version))
        records.append(FeatureRecord(token.address, "price_growth_3m", p_growth_3m, None, now, "TimeDiff", version))
        records.append(FeatureRecord(token.address, "price_growth_5m", p_growth_5m, None, now, "TimeDiff", version))
        records.append(FeatureRecord(token.address, "liquidity_change_5m", liq_change_5m, None, now, "TimeDiff", version))
        records.append(FeatureRecord(token.address, "liquidity_drop_5m", liq_drop_5m, None, now, "TimeDiff", version))

        # 5. Scores
        records.append(FeatureRecord(token.address, "security_score", security.soft_security_score, None, now, "SecurityAnalyzer", version))
        records.append(FeatureRecord(token.address, "liquidity_score", liquidity.liquidity_score, None, now, "LiquidityAnalyzer", version))
        records.append(FeatureRecord(token.address, "momentum_score", momentum.momentum_score, None, now, "MomentumAnalyzer", version))
        records.append(FeatureRecord(token.address, "data_quality_score", snapshot.data_quality_score, None, now, "ScoreEngine", version))
        records.append(FeatureRecord(token.address, "total_score", score.total_score, None, now, "ScoreEngine", version))

        return records

    def save_features(self, features: List[FeatureRecord]) -> None:
        with self.db._lock, self.db._get_connection() as conn:
            for f in features:
                conn.execute(
                    """
                    INSERT INTO features (token_address, feature_name, feature_value, feature_str_value, timestamp, source, calculation_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f.token_address,
                        f.feature_name,
                        f.feature_value,
                        f.feature_str_value,
                        f.timestamp.isoformat(),
                        f.source,
                        f.calculation_version,
                    ),
                )
            conn.commit()
