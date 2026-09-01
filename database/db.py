"""
Database Repository for SQLite operations in Solana Meme Research Lab.
Thread-safe operations with structured models.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings
from core.models import (
    DecisionRecord,
    ExitReason,
    HardRejectReason,
    PaperPosition,
    ScoreResult,
    SecurityCheckResult,
    TokenInfo,
    TokenSnapshot,
    TokenStatus,
    TradeAction,
    utc_now,
)
from database.schema import SCHEMA_SQL


class Database:
    def __init__(self, db_path: Optional[Any] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = settings.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=20.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def save_token(self, token: TokenInfo) -> None:
        with self._lock, self._get_connection() as conn:
            created_str = token.created_at.isoformat() if token.created_at else None
            disc_str = token.discovered_at.isoformat()
            quar_str = token.quarantine_until.isoformat() if token.quarantine_until else None

            conn.execute(
                """
                INSERT INTO tokens (address, symbol, name, pair_address, dex, created_at, discovered_at,
                                    initial_liquidity_usd, initial_price_usd, status, quarantine_until, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(address) DO UPDATE SET
                    symbol=excluded.symbol,
                    name=excluded.name,
                    pair_address=coalesce(excluded.pair_address, tokens.pair_address),
                    status=coalesce(excluded.status, tokens.status),
                    updated_at=excluded.updated_at
                """,
                (
                    token.address,
                    token.symbol,
                    token.name,
                    token.pair_address,
                    token.dex,
                    created_str,
                    disc_str,
                    token.initial_liquidity_usd,
                    token.initial_price_usd,
                    token.status.value,
                    quar_str,
                    utc_now().isoformat(),
                ),
            )
            conn.commit()

    def save_security_check(self, sec) -> None:
        """Saves a SecurityCheckResult into the database."""
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO security_checks (
                    token_address, timestamp, is_mintable, is_freezable, is_mutable,
                    transfer_fee_bps, top10_holders_pct, creator_balance_pct, single_holder_max_pct,
                    is_liquidity_locked, is_hard_reject, hard_reject_reasons, soft_security_score,
                    security_verified, security_status, score_breakdown, explanations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sec.token_address,
                    sec.timestamp.isoformat(),
                    sec.is_mintable,
                    sec.is_freezable,
                    sec.is_mutable,
                    sec.transfer_fee_bps,
                    sec.top10_holders_pct,
                    sec.creator_balance_pct,
                    sec.single_holder_max_pct,
                    sec.is_liquidity_locked,
                    sec.is_hard_reject,
                    json.dumps(sec.hard_reject_reasons),
                    sec.soft_security_score,
                    sec.security_verified,
                    sec.security_status,
                    json.dumps(sec.score_breakdown),
                    json.dumps(sec.explanations)
                )
            )
            conn.commit()


    def get_token(self, token_address: str) -> Optional[TokenInfo]:
        with self._lock, self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM tokens WHERE address = ?", (token_address,))
            row = cur.fetchone()
            if not row:
                return None
            
            created_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
            disc_at = datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else utc_now()
            quar_at = datetime.fromisoformat(row["quarantine_until"]) if row["quarantine_until"] else None

            return TokenInfo(
                address=row["address"],
                symbol=row["symbol"],
                name=row["name"],
                pair_address=row["pair_address"],
                dex=row["dex"],
                created_at=created_at,
                discovered_at=disc_at,
                initial_liquidity_usd=row["initial_liquidity_usd"],
                initial_price_usd=row["initial_price_usd"],
                status=TokenStatus(row["status"]),
                quarantine_until=quar_at,
            )

    def list_tokens(self, limit: int = 50) -> List[TokenInfo]:
        with self._lock, self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM tokens ORDER BY discovered_at DESC LIMIT ?", (limit,))
            tokens = []
            for row in cur.fetchall():
                created_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                disc_at = datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else utc_now()
                quar_at = datetime.fromisoformat(row["quarantine_until"]) if row["quarantine_until"] else None
                tokens.append(
                    TokenInfo(
                        address=row["address"],
                        symbol=row["symbol"],
                        name=row["name"],
                        pair_address=row["pair_address"],
                        dex=row["dex"],
                        created_at=created_at,
                        discovered_at=disc_at,
                        initial_liquidity_usd=row["initial_liquidity_usd"],
                        initial_price_usd=row["initial_price_usd"],
                        status=TokenStatus(row["status"]),
                        quarantine_until=quar_at,
                    )
                )
            return tokens

    def get_active_tokens(self) -> List[TokenInfo]:
        with self._lock, self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM tokens WHERE status IN ('QUARANTINE', 'MONITORING', 'WATCH')")
            tokens = []
            for row in cur.fetchall():
                created_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                disc_at = datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else utc_now()
                quar_at = datetime.fromisoformat(row["quarantine_until"]) if row["quarantine_until"] else None
                tokens.append(
                    TokenInfo(
                        address=row["address"],
                        symbol=row["symbol"],
                        name=row["name"],
                        pair_address=row["pair_address"],
                        dex=row["dex"],
                        created_at=created_at,
                        discovered_at=disc_at,
                        initial_liquidity_usd=row["initial_liquidity_usd"],
                        initial_price_usd=row["initial_price_usd"],
                        status=TokenStatus(row["status"]),
                        quarantine_until=quar_at,
                    )
                )
            return tokens

    def save_snapshot(self, snapshot: TokenSnapshot) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO token_snapshots (token_address, timestamp, price_usd, liquidity_usd, volume_5m_usd,
                                            volume_1m_usd, volume_24h_usd, buys_5m, sells_5m, trade_count_5m,
                                            market_cap_usd, holders_count, top10_holders_pct, creator_balance_pct,
                                            data_sources, data_quality_score, missing_fields)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.token_address,
                    snapshot.timestamp.isoformat(),
                    snapshot.price_usd,
                    snapshot.liquidity_usd,
                    snapshot.volume_5m_usd,
                    snapshot.volume_1m_usd,
                    snapshot.volume_24h_usd,
                    snapshot.buys_5m,
                    snapshot.sells_5m,
                    snapshot.trade_count_5m,
                    snapshot.market_cap_usd,
                    snapshot.holders_count,
                    snapshot.top10_holders_pct,
                    snapshot.creator_balance_pct,
                    json.dumps(snapshot.data_sources),
                    snapshot.data_quality_score,
                    json.dumps(snapshot.missing_fields),
                ),
            )
            conn.commit()

    def get_snapshots(self, token_address: str, limit: int = 20) -> List[TokenSnapshot]:
        with self._lock, self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM token_snapshots WHERE token_address = ? ORDER BY timestamp ASC LIMIT ?",
                (token_address, limit),
            )
            snapshots = []
            for row in cur.fetchall():
                ts = datetime.fromisoformat(row["timestamp"])
                snapshots.append(
                    TokenSnapshot(
                        token_address=row["token_address"],
                        timestamp=ts,
                        price_usd=row["price_usd"],
                        liquidity_usd=row["liquidity_usd"],
                        volume_5m_usd=row["volume_5m_usd"],
                        volume_1m_usd=row["volume_1m_usd"],
                        volume_24h_usd=row["volume_24h_usd"],
                        buys_5m=row["buys_5m"],
                        sells_5m=row["sells_5m"],
                        trade_count_5m=row["trade_count_5m"],
                        market_cap_usd=row["market_cap_usd"],
                        holders_count=row["holders_count"],
                        top10_holders_pct=row["top10_holders_pct"],
                        creator_balance_pct=row["creator_balance_pct"],
                        data_sources=json.loads(row["data_sources"] or "[]"),
                        data_quality_score=row["data_quality_score"],
                        missing_fields=json.loads(row["missing_fields"] or "[]"),
                    )
                )
            return snapshots

    def save_security_check(self, check: SecurityCheckResult) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO security_checks (token_address, timestamp, is_mintable, is_freezable, is_mutable,
                                            transfer_fee_bps, top10_holders_pct, creator_balance_pct,
                                            single_holder_max_pct, is_liquidity_locked, is_hard_reject,
                                            hard_reject_reasons, soft_security_score, explanations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check.token_address,
                    check.timestamp.isoformat(),
                    1 if check.is_mintable else 0,
                    1 if check.is_freezable else 0,
                    1 if check.is_mutable else 0,
                    check.transfer_fee_bps,
                    check.top10_holders_pct,
                    check.creator_balance_pct,
                    check.single_holder_max_pct,
                    1 if check.is_liquidity_locked else 0,
                    1 if check.is_hard_reject else 0,
                    json.dumps(check.hard_reject_reasons),
                    check.soft_security_score,
                    json.dumps(check.explanations),
                ),
            )
            conn.commit()

    def save_score(self, score: ScoreResult) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scores (token_address, timestamp, total_score, security_score, liquidity_score,
                                    wallet_score, market_score, momentum_score, data_quality_score,
                                    status, decision_reason, breakdown, explanations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.token_address,
                    score.timestamp.isoformat(),
                    score.total_score,
                    score.security_score,
                    score.liquidity_score,
                    score.wallet_score,
                    score.market_score,
                    score.momentum_score,
                    score.data_quality_score,
                    score.status.value,
                    score.decision_reason,
                    json.dumps(score.breakdown),
                    json.dumps(score.explanations),
                ),
            )
            conn.commit()

    def save_decision(self, decision: DecisionRecord) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO decision_ledger (token_address, timestamp, action, status, total_score,
                                            security_score, liquidity_score, momentum_score, wallet_score,
                                            data_quality_score, primary_reason, reasons, features_version, data_sources)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.token_address,
                    decision.timestamp.isoformat(),
                    decision.action.value,
                    decision.status.value,
                    decision.total_score,
                    decision.security_score,
                    decision.liquidity_score,
                    decision.momentum_score,
                    decision.wallet_score,
                    decision.data_quality_score,
                    decision.primary_reason,
                    json.dumps(decision.reasons),
                    decision.features_version,
                    json.dumps(decision.data_sources),
                ),
            )
            conn.commit()

    def save_paper_position(self, pos: PaperPosition) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_positions (
                    position_id, token_address, symbol, entry_timestamp, entry_price_usd, amount_usd,
                    tokens_amount, estimated_slippage_pct, estimated_price_impact_pct, network_fee_usd,
                    priority_fee_usd, dex_fee_usd, total_entry_cost_usd, current_price_usd, highest_price_usd,
                    stop_loss_price_usd, is_open, exit_timestamp, exit_price_usd,
                    exit_reason, gross_pnl_usd, net_pnl_usd, net_roi_pct,
                    initial_discovery_price_usd, price_growth_at_entry_pct, score_at_entry,
                    score_at_t0, score_at_t5, max_gain_from_t0_pct, max_gain_from_entry_pct,
                    max_drawdown_pct, holding_time_seconds
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(position_id) DO UPDATE SET
                    current_price_usd=excluded.current_price_usd,
                    highest_price_usd=excluded.highest_price_usd,
                    is_open=excluded.is_open,
                    exit_timestamp=excluded.exit_timestamp,
                    exit_price_usd=excluded.exit_price_usd,
                    exit_reason=excluded.exit_reason,
                    gross_pnl_usd=excluded.gross_pnl_usd,
                    net_pnl_usd=excluded.net_pnl_usd,
                    net_roi_pct=excluded.net_roi_pct,
                    highest_price_usd=excluded.highest_price_usd,
                    stop_loss_price_usd=excluded.stop_loss_price_usd,
                    max_drawdown_pct=excluded.max_drawdown_pct,
                    max_gain_from_entry_pct=excluded.max_gain_from_entry_pct,
                    max_gain_from_t0_pct=excluded.max_gain_from_t0_pct,
                    holding_time_seconds=excluded.holding_time_seconds
                """,
                (
                    pos.position_id,
                    pos.token_address,
                    pos.symbol,
                    pos.entry_timestamp.isoformat(),
                    pos.entry_price_usd,
                    pos.amount_usd,
                    pos.tokens_amount,
                    pos.estimated_slippage_pct,
                    pos.estimated_price_impact_pct,
                    pos.network_fee_usd,
                    pos.priority_fee_usd,
                    pos.dex_fee_usd,
                    pos.total_entry_cost_usd,
                    pos.current_price_usd,
                    pos.highest_price_usd,
                    pos.stop_loss_price_usd,
                    1 if pos.is_open else 0,
                    pos.exit_timestamp.isoformat() if pos.exit_timestamp else None,
                    pos.exit_price_usd,
                    pos.exit_reason.value if pos.exit_reason else None,
                    pos.gross_pnl_usd,
                    pos.net_pnl_usd,
                    pos.net_roi_pct,
                    pos.initial_discovery_price_usd,
                    pos.price_growth_at_entry_pct,
                    pos.score_at_entry,
                    pos.score_at_t0,
                    pos.score_at_t5,
                    pos.max_gain_from_t0_pct,
                    pos.max_gain_from_entry_pct,
                    pos.max_drawdown_pct,
                    pos.holding_time_seconds,
                ),
            )
            conn.commit()

    def list_paper_positions(self, is_open: Optional[bool] = None) -> List[PaperPosition]:
        with self._lock, self._get_connection() as conn:
            query = "SELECT * FROM paper_positions"
            params = []
            if is_open is not None:
                query += " WHERE is_open = ?"
                params.append(1 if is_open else 0)
            query += " ORDER BY entry_timestamp DESC"

            cur = conn.execute(query, params)
            positions = []
            for row in cur.fetchall():
                positions.append(
                    PaperPosition(
                        position_id=row["position_id"],
                        token_address=row["token_address"],
                        symbol=row["symbol"],
                        entry_timestamp=datetime.fromisoformat(row["entry_timestamp"]),
                        entry_price_usd=row["entry_price_usd"],
                        amount_usd=row["amount_usd"],
                        tokens_amount=row["tokens_amount"],
                        estimated_slippage_pct=row["estimated_slippage_pct"],
                        estimated_price_impact_pct=row["estimated_price_impact_pct"],
                        network_fee_usd=row["network_fee_usd"],
                        priority_fee_usd=row["priority_fee_usd"],
                        dex_fee_usd=row["dex_fee_usd"],
                        total_entry_cost_usd=row["total_entry_cost_usd"],
                        current_price_usd=row["current_price_usd"],
                        highest_price_usd=row["highest_price_usd"],
                        stop_loss_price_usd=row["stop_loss_price_usd"],
                        is_open=bool(row["is_open"]),
                        exit_timestamp=datetime.fromisoformat(row["exit_timestamp"]) if row["exit_timestamp"] else None,
                        exit_price_usd=row["exit_price_usd"],
                        exit_reason=ExitReason(row["exit_reason"]) if row["exit_reason"] else None,
                        gross_pnl_usd=row["gross_pnl_usd"],
                        net_pnl_usd=row["net_pnl_usd"],
                        net_roi_pct=row["net_roi_pct"],
                        initial_discovery_price_usd=row["initial_discovery_price_usd"] or 0.0,
                        price_growth_at_entry_pct=row["price_growth_at_entry_pct"] or 0.0,
                        score_at_entry=row["score_at_entry"] or 0.0,
                        score_at_t0=row["score_at_t0"],
                        score_at_t5=row["score_at_t5"],
                        max_gain_from_t0_pct=row["max_gain_from_t0_pct"] or 0.0,
                        max_gain_from_entry_pct=row["max_gain_from_entry_pct"] or 0.0,
                        max_drawdown_pct=row["max_drawdown_pct"] or 0.0,
                        holding_time_seconds=row["holding_time_seconds"] or 0.0,
                    )
                )
            return positions

    def list_decisions(self, limit: int = 50) -> List[DecisionRecord]:
        with self._lock, self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM decision_ledger ORDER BY timestamp DESC LIMIT ?", (limit,))
            decisions = []
            for row in cur.fetchall():
                decisions.append(
                    DecisionRecord(
                        token_address=row["token_address"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        action=TradeAction(row["action"]),
                        status=TokenStatus(row["status"]),
                        total_score=row["total_score"],
                        security_score=row["security_score"],
                        liquidity_score=row["liquidity_score"],
                        momentum_score=row["momentum_score"],
                        wallet_score=row["wallet_score"],
                        data_quality_score=row["data_quality_score"],
                        primary_reason=row["primary_reason"] or "",
                        reasons=json.loads(row["reasons"] or "[]"),
                        features_version=row["features_version"],
                        data_sources=json.loads(row["data_sources"] or "[]"),
                    )
                )
            return decisions

    def record_scan_cycle(
        self,
        cycle_id: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        duration_sec: float = 0.0,
        tokens_discovered: int = 0,
        tokens_analyzed: int = 0,
        error: Optional[str] = None,
    ) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scan_cycles (cycle_id, started_at, completed_at, duration_sec, tokens_discovered, tokens_analyzed, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cycle_id) DO UPDATE SET
                    completed_at=coalesce(excluded.completed_at, scan_cycles.completed_at),
                    duration_sec=coalesce(excluded.duration_sec, scan_cycles.duration_sec),
                    tokens_discovered=coalesce(excluded.tokens_discovered, scan_cycles.tokens_discovered),
                    tokens_analyzed=coalesce(excluded.tokens_analyzed, scan_cycles.tokens_analyzed),
                    error=coalesce(excluded.error, scan_cycles.error)
                """,
                (
                    cycle_id,
                    started_at.isoformat(),
                    completed_at.isoformat() if completed_at else None,
                    duration_sec,
                    tokens_discovered,
                    tokens_analyzed,
                    error,
                ),
            )
            conn.commit()

    def get_scan_cycles_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        with self._lock, self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT count(*) as total,
                       sum(case when completed_at is not null and error is null then 1 else 0 end) as completed,
                       sum(case when error is not null then 1 else 0 end) as failed,
                       sum(tokens_discovered) as discovered,
                       sum(tokens_analyzed) as analyzed
                FROM scan_cycles
                WHERE started_at >= ? AND started_at <= ?
                """,
                (start_time.isoformat(), end_time.isoformat()),
            )
            row = cur.fetchone()
            if row:
                return {
                    "started_cycles": row["total"] or 0,
                    "completed_cycles": row["completed"] or 0,
                    "failed_cycles": row["failed"] or 0,
                    "tokens_discovered": row["discovered"] or 0,
                    "tokens_analyzed": row["analyzed"] or 0,
                }
            return {"started_cycles": 0, "completed_cycles": 0, "failed_cycles": 0, "tokens_discovered": 0, "tokens_analyzed": 0}
