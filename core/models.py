"""
Domain Data Models for Solana Meme Research Lab.
Includes Token, Snapshot, Security, Liquidity, Momentum, Score, and Paper Simulation entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TokenState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUARANTINE = "QUARANTINE"
    MONITORING = "MONITORING"
    READY_TO_ENTER = "READY_TO_ENTER"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"
    EXPIRED = "EXPIRED"
    WATCH = "WATCH"
    CANDIDATE = "CANDIDATE"
    REJECT = "REJECT"


# Backward compatibility alias
TokenStatus = TokenState


class EntryBlockReason(str, Enum):
    NONE = "NONE"
    WAITING_FOR_SCORE = "WAITING_FOR_SCORE"
    WAITING_FOR_PRICE = "WAITING_FOR_PRICE"
    SECURITY_UNVERIFIED = "SECURITY_UNVERIFIED"
    LIQUIDITY_RISK = "LIQUIDITY_RISK"
    CAPACITY_FULL = "CAPACITY_FULL"
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    QUARANTINE_ACTIVE = "QUARANTINE_ACTIVE"
    MONITORING_TIMEOUT = "MONITORING_TIMEOUT"
    ALREADY_OPEN = "ALREADY_OPEN"


class HardRejectReason(str, Enum):
    MINT_AUTHORITY_ENABLED = "MINT_AUTHORITY_ENABLED"
    FREEZE_AUTHORITY_ENABLED = "FREEZE_AUTHORITY_ENABLED"
    TRANSFER_FEE_HONEYPOT = "TRANSFER_FEE_HONEYPOT"
    EXTREME_HOLDER_CONCENTRATION = "EXTREME_HOLDER_CONCENTRATION"
    CRITICAL_LIQUIDITY_REMOVAL = "CRITICAL_LIQUIDITY_REMOVAL"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
    MUTABLE_UNVERIFIED_TOKEN = "MUTABLE_UNVERIFIED_TOKEN"


class TradeAction(str, Enum):
    DISCOVER = "DISCOVER"
    QUARANTINE_TICK = "QUARANTINE_TICK"
    POST_QUARANTINE_EVAL = "POST_QUARANTINE_EVAL"
    SCORE_UPDATE = "SCORE_UPDATE"
    PAPER_BUY = "PAPER_BUY"
    PEAK_UPDATE = "PEAK_UPDATE"
    PAPER_SELL = "PAPER_SELL"
    EXPIRE = "EXPIRE"
    BLOCK = "BLOCK"
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REJECT = "REJECT"


class ExitReason(str, Enum):
    STOP_LOSS_25 = "STOP_LOSS_25"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    LIQUIDITY_COLLAPSE = "LIQUIDITY_COLLAPSE"
    MAX_HOLD_TIMEOUT = "MAX_HOLD_TIMEOUT"
    MANUAL_CLOSE = "MANUAL_CLOSE"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TokenInfo:
    address: str
    symbol: str
    name: str
    pair_address: Optional[str] = None
    dex: str = "raydium"
    created_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=utc_now)
    initial_liquidity_usd: float = 0.0
    initial_price_usd: float = 0.0
    initial_volume_usd: float = 0.0
    initial_market_cap_usd: Optional[float] = None
    initial_score: Optional[float] = None
    quarantine_score: Optional[float] = None
    current_score: Optional[float] = None
    status: TokenState = TokenState.DISCOVERED
    state: TokenState = TokenState.DISCOVERED
    quarantine_until: Optional[datetime] = None
    monitoring_until: Optional[datetime] = None
    entry_block_reason: EntryBlockReason = EntryBlockReason.NONE

    def age_minutes(self, reference_time: Optional[datetime] = None) -> float:
        ref = reference_time or utc_now()
        start = self.created_at or self.discovered_at
        delta = (ref - start).total_seconds() / 60.0
        return max(0.0, delta)


@dataclass
class TokenSnapshot:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    price_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_5m_usd: float = 0.0
    volume_1m_usd: float = 0.0
    volume_24h_usd: float = 0.0
    buys_5m: int = 0
    sells_5m: int = 0
    trade_count_5m: int = 0
    market_cap_usd: Optional[float] = None
    holders_count: Optional[int] = None
    top10_holders_pct: Optional[float] = None
    creator_balance_pct: Optional[float] = None
    data_sources: List[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    data_quality_score: float = 100.0
    missing_fields: List[str] = field(default_factory=list)
    data_timestamp: Optional[datetime] = None
    data_age_seconds: float = 0.0


@dataclass
class SecurityCheckResult:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    is_mintable: bool = False
    is_freezable: bool = False
    is_mutable: bool = True
    transfer_fee_bps: int = 0
    top10_holders_pct: Optional[float] = None
    creator_balance_pct: Optional[float] = None
    single_holder_max_pct: Optional[float] = None
    is_liquidity_locked: bool = False
    is_hard_reject: bool = False
    hard_reject_reasons: List[str] = field(default_factory=list)
    soft_security_score: Optional[float] = None  # 0 to 100 or None if unverified
    security_verified: bool = False
    security_status: str = "SECURITY_UNVERIFIED"
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    explanations: List[str] = field(default_factory=list)


@dataclass
class LiquidityMetrics:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    current_liquidity_usd: Optional[float] = None
    delta_liquidity_5m: Optional[float] = None
    liquidity_velocity_usd_per_min: Optional[float] = None
    liquidity_acceleration: Optional[float] = None
    withdrawal_ratio: Optional[float] = None
    volume_to_liquidity_ratio: Optional[float] = None
    liquidity_score: float = 0.0  # 0 to 100 (0 if DATA_UNAVAILABLE)
    has_sufficient_history: bool = False
    is_data_unavailable: bool = False
    explanations: List[str] = field(default_factory=list)


@dataclass
class MomentumMetrics:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    price_change_5m_pct: float = 0.0
    volume_5m_usd: float = 0.0
    heat_1m_5m: float = 0.0  # (Vol 1m / Vol 5m) * 100
    buy_pressure_ratio: float = 0.5  # Buys / (Buys + Sells)
    buy_count_5m: int = 0
    sell_count_5m: int = 0
    trade_count_5m: int = 0
    average_trade_size_usd: float = 0.0
    price_step_count: int = 0
    large_swap_count: int = 0
    is_activity_stale: bool = False
    momentum_score: float = 0.0  # 0 to 100
    explanations: List[str] = field(default_factory=list)


@dataclass
class WalletAnalysisResult:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    creator_age_hours: Optional[float] = None
    top10_holders_pct: Optional[float] = None
    creator_balance_pct: Optional[float] = None
    cluster_risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, POSSIBLY_RELATED
    cluster_risk_score: float = 10.0  # 0 to 100
    wallet_score: float = 70.0  # 0 to 100
    explanations: List[str] = field(default_factory=list)


@dataclass
class ScoreResult:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    total_score: Optional[float] = 0.0
    security_score: Optional[float] = 0.0
    liquidity_score: float = 0.0
    wallet_score: float = 0.0
    market_score: float = 0.0
    momentum_score: float = 0.0
    data_quality_score: float = 100.0
    status: TokenStatus = TokenStatus.WATCH
    decision_reason: str = ""
    breakdown: Dict[str, float] = field(default_factory=dict)
    explanations: List[str] = field(default_factory=list)


@dataclass
class DecisionRecord:
    token_address: str
    timestamp: datetime = field(default_factory=utc_now)
    action: TradeAction = TradeAction.HOLD
    status: TokenStatus = TokenStatus.WATCH
    total_score: Optional[float] = 0.0
    security_score: Optional[float] = 0.0
    liquidity_score: float = 0.0
    wallet_score: float = 0.0
    market_score: float = 0.0
    momentum_score: float = 0.0
    data_quality_score: float = 100.0
    primary_reason: str = ""
    reasons: List[str] = field(default_factory=list)
    features_version: str = "v1.0"
    data_sources: List[str] = field(default_factory=list)


@dataclass
class PaperPosition:
    position_id: str
    token_address: str
    symbol: str
    entry_timestamp: datetime = field(default_factory=utc_now)
    entry_price_usd: float = 0.0
    amount_usd: float = 2.0  # Fixed $2 research slot
    tokens_amount: float = 0.0
    estimated_slippage_pct: float = 1.0
    estimated_price_impact_pct: float = 0.5
    network_fee_usd: float = 0.0008
    priority_fee_usd: float = 0.0080
    dex_fee_usd: float = 0.0050
    total_entry_cost_usd: float = 2.0138
    current_price_usd: float = 0.0
    highest_price_usd: float = 0.0  # Peak price tracker
    stop_loss_price_usd: float = 0.0  # Trailing stop (-25% from highest_price_usd)
    is_open: bool = True
    exit_timestamp: Optional[datetime] = None
    exit_price_usd: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    gross_pnl_usd: float = 0.0
    net_pnl_usd: float = 0.0
    net_roi_pct: float = 0.0
    # Analytical Research Metrics
    initial_discovery_price_usd: float = 0.0
    price_growth_at_entry_pct: float = 0.0
    score_at_entry: float = 0.0
    score_at_t0: Optional[float] = None
    score_at_t5: Optional[float] = None
    max_gain_from_t0_pct: float = 0.0
    max_gain_from_entry_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    data_age_at_entry_seconds: float = 0.0
    data_age_at_exit_seconds: float = 0.0
    holding_time_seconds: float = 0.0
