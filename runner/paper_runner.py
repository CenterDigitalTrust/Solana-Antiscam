"""
Autonomous Paper Runner Engine for Solana Meme Research Lab.
Manages:
- $100 virtual bankroll with $2 slots (max 50 concurrent)
- 5-Minute Quarantine -> Continuous Monitoring -> +50% Price Trigger -> Paper Buy
- Trailing Stop -25% from peak, Emergency Liquidity Exit (<$1000)
- Clean state machine: DISCOVERED -> QUARANTINE -> MONITORING -> READY_TO_ENTER -> OPEN -> CLOSED / EXPIRED
- Persistent output to TXT, CSV, and SQLite in runtime/results/, ОТЧЕТЫ/, reports/
"""

from __future__ import annotations

import csv
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from analyzers.liquidity import LiquidityAnalyzer
from analyzers.momentum import MomentumAnalyzer
from analyzers.security import SecurityAnalyzer
from analyzers.wallet import WalletAnalyzer
from collectors.dexscreener import DexScreenerAdapter
from collectors.helius import HeliusAdapter
from config.settings import settings
from core.models import (
    EntryBlockReason,
    ExitReason,
    PaperPosition,
    TokenInfo,
    TokenSnapshot,
    TokenState,
    TokenStatus,
    TradeAction,
    utc_now,
)
from database.db import Database
from database.supabase_client import SupabaseManager
from discovery.service import TokenDiscoveryService
from features.store import FeatureStore
from ledger.decision_ledger import DecisionLedger
from quarantine.manager import QuarantineManager
from runner.report_generator import HourlyReportGenerator, REPORTS_DIR_NAME
from scoring.engine import ScoreEngine
from simulation.execution_simulator import ExecutionSimulator
from simulation.portfolio import PaperPortfolio

logger = logging.getLogger(__name__)

class AutonomousPaperRunner:
    def __init__(
        self,
        db: Optional[Database] = None,
        runtime_dir: str = "runtime",
        trailing_stop_pct: float = 25.0,
        emergency_liq_threshold_usd: float = 1000.0,
        monitoring_timeout_minutes: float = 60.0,
    ):
        self.runtime_dir = runtime_dir
        self.results_dir = os.path.join(runtime_dir, "results")
        self.logs_dir = os.path.join(runtime_dir, "logs")
        self.state_dir = os.path.join(runtime_dir, "state")

        for d in [self.results_dir, self.logs_dir, self.state_dir, "reports", REPORTS_DIR_NAME]:
            os.makedirs(d, exist_ok=True)

        self.db = db or Database()
        self.supabase = SupabaseManager()
        self.dex_adapter = DexScreenerAdapter()
        self.helius_adapter = HeliusAdapter()
        self.exec_sim = ExecutionSimulator()

        self.trailing_stop_pct = trailing_stop_pct
        self.emergency_liq_threshold_usd = emergency_liq_threshold_usd
        self.monitoring_timeout_minutes = monitoring_timeout_minutes

        self.portfolio = PaperPortfolio(
            starting_capital_usd=100.0,
            position_size_usd=2.0,
            max_positions=50,
            trailing_stop_pct=trailing_stop_pct,
            execution_simulator=self.exec_sim,
            db=self.db,
        )

        self.quarantine_mgr = QuarantineManager(default_quarantine_minutes=0.0)

        # Threading for Fast Lane
        self._fast_lane_stop_event = threading.Event()
        self._fast_lane_thread = None

        self.discovery_service = TokenDiscoveryService(
            market_provider=self.dex_adapter,
            db=self.db,
            quarantine_manager=self.quarantine_mgr,
        )

        self.sec_analyzer = SecurityAnalyzer(onchain_provider=self.helius_adapter)
        self.liq_analyzer = LiquidityAnalyzer()
        self.mom_analyzer = MomentumAnalyzer()
        self.wal_analyzer = WalletAnalyzer()
        self.score_engine = ScoreEngine()
        self.feature_store = FeatureStore(db=self.db)
        self.decision_ledger = DecisionLedger(db=self.db)

        # File paths
        self.portfolio_txt_path = os.path.join(self.results_dir, "portfolio.txt")
        self.trades_txt_path = os.path.join(self.results_dir, "trades.txt")
        self.daily_txt_path = os.path.join(self.results_dir, "daily_result.txt")
        self.positions_txt_path = os.path.join(self.results_dir, "open_positions.txt")
        self.trades_csv_path = os.path.join(self.results_dir, "paper_trades.csv")
        self.snapshots_csv_path = os.path.join(self.results_dir, "portfolio_snapshots.csv")

        # Report Generators
        from reports.baseline_reporter import BaselineReporter
        self.baseline_reporter = BaselineReporter(output_dir=os.path.join(self.results_dir, "baseline_reports"))
        self.report_generator = HourlyReportGenerator(
            portfolio=self.portfolio,
            db=self.db,
            output_dirs=[REPORTS_DIR_NAME],  # Сохраняем только в папку ОТЧЕТЫ
        )

        self._init_csv_headers()

    def _init_csv_headers(self) -> None:
        if not os.path.exists(self.trades_csv_path):
            with open(self.trades_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "trade_id", "token_address", "symbol", "action", "timestamp",
                    "price_usd", "amount_tokens", "cost_usd", "proceeds_usd",
                    "fees_usd", "net_pnl_usd", "roi_pct", "exit_reason", "decision_score"
                ])

        if not os.path.exists(self.snapshots_csv_path):
            with open(self.snapshots_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "available_cash", "open_positions_count", "open_positions_value",
                    "total_equity", "realized_pnl", "unrealized_pnl", "wins_count", "losses_count", "win_rate_pct"
                ])

    def run_discovery_and_eval(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Executes full time-aware evaluation cycle:
        1. Discover tokens -> establish initial T0 snapshot & initial price/liquidity/score
        2. Quarantine 5m -> collect observations, extract temporal features (no look-ahead)
        3. Post-Quarantine -> transition to MONITORING
        4. Continuous Monitoring -> on every cycle check:
           - current_score >= 70.0
           - current_price >= initial_price * 1.50 (+50% continuous price trigger)
           - security_verified == True
           - liquidity_health == PASS
           - available_cash >= $2.00
           - open_positions < 50
           - not already open
        5. If all met -> READY_TO_ENTER -> PAPER BUY $2.00
        6. If monitoring > 60m without entry -> EXPIRED
        """
        # Cleanup old tokens from Supabase to stay under 500MB free tier
        self.supabase.cleanup_stale_tokens(hours_old=24)
        
        new_tokens = self.discovery_service.discover_and_register(limit=limit)
        
        # Получаем ВСЕ токены из базы, которые все еще находятся в карантине или мониторинге
        active_tokens = self.db.get_active_tokens()
        
        # Объединяем списки без дубликатов по адресу
        token_map = {t.address: t for t in active_tokens}
        for t in new_tokens:
            token_map[t.address] = t
            
        tokens = list(token_map.values())
        
        results = []
        cycle_time = utc_now()

        # Batch fetch snapshots for all tokens
        token_addresses = [t.address for t in tokens]
        snapshots_dict = self.dex_adapter.get_token_snapshots_batch(token_addresses)

        for token in tokens:
            snapshot = snapshots_dict.get(token.address)
            if not snapshot:
                continue

            # Establish initial T0 metrics if missing
            is_initial = (not token.initial_price_usd or token.initial_price_usd <= 0.0)
            if is_initial and snapshot.price_usd:
                token.initial_price_usd = snapshot.price_usd
                token.initial_liquidity_usd = snapshot.liquidity_usd or 0.0
                token.initial_volume_usd = snapshot.volume_5m_usd or 0.0
                token.initial_market_cap_usd = snapshot.market_cap_usd
                token.monitoring_until = token.discovered_at + timedelta(minutes=self.monitoring_timeout_minutes)
                self.db.save_token(token)

            authorities = self.helius_adapter.get_token_authorities(token.address)
            decimals = authorities.get("decimals", 6)
            raw_supply = float(authorities.get("supply") or 0.0)

            holders_data = self.helius_adapter.get_top_holders(token.address, total_supply=raw_supply, decimals=decimals)
            creator_data = self.helius_adapter.get_creator_info(token.address)

            top10_pct = holders_data.get("top10_percentage")
            single_max_pct = holders_data.get("single_holder_max_percentage")
            creator_age_days = creator_data.get("creator_wallet_age_days")
            creator_age_hours = (creator_age_days * 24.0) if creator_age_days is not None else None

            snapshot.top10_holders_pct = top10_pct
            snapshot.creator_balance_pct = single_max_pct
            snapshot.holders_count = len(holders_data.get("top_holders", []))

            self.db.save_snapshot(snapshot)
            history = self.db.get_snapshots(token.address, limit=20)
            security = self.sec_analyzer.analyze(token.address, snapshot=snapshot, authorities_override=authorities)
            self.db.save_security_check(security)
            liquidity = self.liq_analyzer.analyze(token.address, current_snapshot=snapshot, historical_snapshots=history)
            momentum = self.mom_analyzer.analyze(token.address, current_snapshot=snapshot, historical_snapshots=history, token_age_minutes=token.age_minutes())
            wallet = self.wal_analyzer.analyze(token.address, snapshot=snapshot, creator_age_hours=creator_age_hours)

            score = self.score_engine.calculate_score(token, snapshot, security, liquidity, momentum, wallet)
            self.db.save_score(score)

            token.current_score = score.total_score
            if is_initial:
                token.initial_score = score.total_score

            features = self.feature_store.extract_features(token, snapshot, security, liquidity, momentum, score, wallet, history=history)
            self.feature_store.save_features(features)
            
            # Sync to Supabase for the Patrol MD Website
            self.supabase.upsert_token_state(token, snapshot, security, score)

            # === STATE MACHINE TRANSITIONS ===
            current_p = snapshot.price_usd or 0.0
            initial_p = token.initial_price_usd or current_p
            price_growth_pct = ((current_p - initial_p) / initial_p * 100.0) if initial_p > 0 else 0.0

            in_quarantine = not self.quarantine_mgr.is_quarantine_complete(token)
            age_min = token.age_minutes(cycle_time)
            is_expired = token.monitoring_until and (cycle_time > token.monitoring_until)

            decision_action = TradeAction.HOLD
            block_reason = EntryBlockReason.NONE
            decision_str = "MONITORING"

            if token.address in self.portfolio.open_positions:
                token.state = TokenState.OPEN
                token.status = TokenState.OPEN
                block_reason = EntryBlockReason.ALREADY_OPEN
                decision_str = "OPEN_POSITION"
            elif is_expired:
                token.state = TokenState.EXPIRED
                token.status = TokenState.EXPIRED
                token.entry_block_reason = EntryBlockReason.MONITORING_TIMEOUT
                decision_action = TradeAction.EXPIRE
                decision_str = "EXPIRED"
            elif security.is_hard_reject:
                token.state = TokenState.SECURITY_BLOCKED
                token.status = TokenState.SECURITY_BLOCKED
                token.entry_block_reason = EntryBlockReason.SECURITY_UNVERIFIED
                decision_action = TradeAction.REJECT
                decision_str = f"SECURITY_BLOCKED: {score.decision_reason}"
            elif in_quarantine:
                token.state = TokenState.QUARANTINE
                token.status = TokenState.QUARANTINE
                token.entry_block_reason = EntryBlockReason.QUARANTINE_ACTIVE
                remaining_sec = self.quarantine_mgr.remaining_quarantine_seconds(token)
                decision_action = TradeAction.QUARANTINE_TICK
                decision_str = f"QUARANTINE ({remaining_sec:.0f}s left)"
            else:
                # Quarantine Complete -> State is MONITORING / Check Entry
                token.state = TokenState.MONITORING
                token.status = TokenState.MONITORING
                if not token.quarantine_score:
                    token.quarantine_score = score.total_score

                # Evaluate Entry Conditions
                score_ok = (score.total_score is not None and score.total_score >= 70.0)
                price_ok = (current_p >= (initial_p * 2.60))
                security_ok = security.security_verified
                liquidity_ok = (not liquidity.is_data_unavailable) and (snapshot.liquidity_usd and snapshot.liquidity_usd >= 1000.0)
                capacity_ok = (len(self.portfolio.open_positions) < 50)
                cash_ok = (self.portfolio.available_cash_usd >= 2.0)

                if not security_ok:
                    block_reason = EntryBlockReason.SECURITY_UNVERIFIED
                    decision_str = f"MONITORING (SECURITY_UNVERIFIED)"
                elif not liquidity_ok:
                    block_reason = EntryBlockReason.LIQUIDITY_RISK
                    decision_str = f"MONITORING (LIQUIDITY_RISK)"
                elif not score_ok:
                    block_reason = EntryBlockReason.WAITING_FOR_SCORE
                    if score.total_score is None:
                        decision_str = "MONITORING (Score is None)"
                        import logging
                        logging.getLogger("paper_runner").warning(f"Token {token.address}: score unavailable (None), skipping.")
                    else:
                        decision_str = f"MONITORING (Score {score.total_score:.1f} < 70)"
                elif not price_ok:
                    block_reason = EntryBlockReason.WAITING_FOR_PRICE
                    decision_str = f"MONITORING ({price_growth_pct:+.1f}% < +160.0%)"
                    pass
                elif not capacity_ok:
                    block_reason = EntryBlockReason.CAPACITY_FULL
                    decision_str = "SKIPPED_CAPACITY_FULL (50/50)"
                elif not cash_ok:
                    block_reason = EntryBlockReason.INSUFFICIENT_CASH
                    decision_str = f"SKIPPED_CASH (${self.portfolio.available_cash_usd:.2f} < $2.00)"
                else:
                    # All gates PASSED -> READY_TO_ENTER
                    token.state = TokenState.READY_TO_ENTER
                    token.status = TokenState.READY_TO_ENTER
                    token.entry_block_reason = EntryBlockReason.NONE
                    decision_action = TradeAction.HOLD
                    decision_str = "READY_TO_ENTER_QUEUE"

            token.entry_block_reason = block_reason
            self.db.save_token(token)

            self.decision_ledger.record_decision(
                token=token,
                snapshot=snapshot,
                security=security,
                score=score,
                action=decision_action,
            )

            # Store the evaluation result for this token
            eval_result = {
                "token_obj": token,
                "snapshot": snapshot,
                "score": score,
                "security": security,
                "token": token.symbol,
                "address": token.address,
                "score_val": score.total_score,
                "price": current_p,
                "growth": price_growth_pct,
                "state": token.state.value,
                "action": decision_action.value,
                "status": decision_str,
                "block_reason": block_reason.value,
            }
            results.append(eval_result)
            
            # Log event to Baseline Reporter
            self.baseline_reporter.log_event(
                token_address=token.address,
                symbol=token.symbol,
                state=token.state.value,
                score=score.total_score if score.total_score is not None else 0.0,
                price=current_p,
                reason=decision_str
            )

        # === DETERMINISTIC ENTRY QUEUE ===
        ready_tokens = [r for r in results if r["state"] == TokenState.READY_TO_ENTER.value]
        # Sort by Score (desc), Momentum (desc), Timestamp (asc)
        ready_tokens.sort(key=lambda x: (
            x["score_val"], 
            x["score"].momentum_score, 
            -x["token_obj"].discovered_at.timestamp()
        ), reverse=True)

        for item in ready_tokens:
            token = item["token_obj"]
            snapshot = item["snapshot"]
            score = item["score"]
            security = item["security"]
            
            capacity_ok = (len(self.portfolio.open_positions) < 50)
            cash_ok = (self.portfolio.available_cash_usd >= 2.05) # Need buffer for fees

            if not capacity_ok:
                token.entry_block_reason = EntryBlockReason.CAPACITY_FULL
                item["status"] = "SKIPPED_CAPACITY_FULL"
                self.db.save_token(token)
                continue
            
            if not cash_ok:
                token.entry_block_reason = EntryBlockReason.INSUFFICIENT_CASH
                item["status"] = "SKIPPED_CASH"
                self.db.save_token(token)
                continue

            # We have capacity and cash -> BUY!
            item["action"] = TradeAction.PAPER_BUY.value
            pos = self.portfolio.open_virtual_position(token, snapshot, venue=token.dex, score_result=score)
            if pos:
                token.state = TokenState.OPEN
                token.status = TokenState.OPEN
                item["state"] = TokenState.OPEN.value
                item["status"] = "PAPER_BUY"
                self.db.save_token(token)
                self._log_trade_buy(pos, score)
                
                # Re-record decision since action changed
                self.decision_ledger.record_decision(
                    token=token,
                    snapshot=snapshot,
                    security=security,
                    score=score,
                    action=TradeAction.PAPER_BUY,
                )

        # Cleanup results dictionary to strip internal objects before returning
        clean_results = []
        for r in results:
            clean_r = r.copy()
            clean_r.pop("token_obj", None)
            clean_r.pop("snapshot", None)
            clean_r.pop("score", None)
            clean_r.pop("security", None)
            clean_results.append(clean_r)

        self.write_all_outputs()

        # Log portfolio to Baseline Reporter
        summary = self.portfolio.get_summary()
        self.baseline_reporter.log_portfolio(
            cash=summary["available_cash_usd"],
            open_positions_value=summary["open_positions_value_usd"],
            total_equity=summary["total_equity_usd"],
            realized_pnl=summary["total_closed_net_pnl_usd"],
            unrealized_pnl=summary["unrealized_pnl_usd"],
            fees=0.0, # Approximate, could calculate from closed positions later
            drawdown=0.0
        )

        return clean_results

    def monitor_and_update_positions(self) -> List[PaperPosition]:
        """
        Polls market data for active open positions and checks exit triggers:
        1. TRAILING STOP: current_price <= highest_price_from_entry * 0.75
        2. EMERGENCY LIQUIDITY EXIT: liquidity < $1000 or liquidity collapse
        """
        closed_in_cycle: List[PaperPosition] = []
        open_tokens = list(self.portfolio.open_positions.keys())

        if not open_tokens:
            return closed_in_cycle

        snapshots_dict = self.dex_adapter.get_token_snapshots_batch(open_tokens)

        for token_addr in open_tokens:
            if token_addr not in self.portfolio.open_positions:
                continue

            snapshot = snapshots_dict.get(token_addr)
            if not snapshot or snapshot.price_usd is None:
                continue

            closed = self.portfolio.update_and_check_exits(snapshot)
            if closed:
                closed_in_cycle.append(closed)
                token = self.db.get_token(token_addr)
                if token:
                    token.state = TokenState.CLOSED
                    token.status = TokenState.CLOSED
                    self.db.save_token(token)
                self._log_trade_sell(closed)
                self._append_trade_csv(closed)

        if closed_in_cycle:
            self.write_all_outputs()

        return closed_in_cycle

    def _fast_lane_loop(self):
        """
        Independent thread that wakes up every 10 seconds to check OPEN positions.
        This guarantees trailing stops fire immediately, regardless of Helius rate limits.
        
        ANSWER TO 'FAST LANE SYNC QUESTION':
        Synchronization between the Fast Lane and the Main Scanner is handled by `self.portfolio._lock` 
        (a threading.Lock instance) inside `portfolio.py`. 
        When `self.portfolio.update_and_check_exits(snapshot)` is called, it acquires the lock before checking
        or modifying the `PaperPosition` state, ensuring that only one thread (Fast Lane OR Main Scanner) 
        can close a position or modify its P&L at any exact millisecond.
        Furthermore, `open_positions` dict is protected by the same lock during iteration or deletion.
        """
        logger.info("[Fast Lane] Started background thread for OPEN positions.")
        while not self._fast_lane_stop_event.is_set():
            try:
                # 1. Take a quick snapshot of currently open positions
                with self.portfolio._lock:
                    open_addresses = list(self.portfolio.open_positions.keys())
                
                if not open_addresses:
                    # Sleep if no open positions
                    self._fast_lane_stop_event.wait(10.0)
                    continue

                closed_this_tick = []
                
                # Fetch all snapshots in batches of 30
                snapshots = self.dex_adapter.get_token_snapshots_batch(open_addresses)
                
                for address, snapshot in snapshots.items():
                    if self._fast_lane_stop_event.is_set():
                        break
                        
                    closed_pos = self.portfolio.update_and_check_exits(snapshot)
                    if closed_pos:
                        closed_this_tick.append(closed_pos)
                
                if closed_this_tick:
                    print(f"\n[Fast Lane] [!] EMERGENCY EXIT: Closed {len(closed_this_tick)} position(s): {[p.symbol for p in closed_this_tick]}\n")
                
            except Exception as e:
                logger.error("[Fast Lane] Error in fast lane loop: %s", e, exc_info=True)
                
            # Sleep 10 seconds before next fast-lane check
            self._fast_lane_stop_event.wait(10.0)

    def _log_trade_buy(self, pos: PaperPosition, score: Any) -> None:
        with open(self.trades_txt_path, "a", encoding="utf-8") as fp:
            fp.write("-" * 50 + "\n")
            fp.write("PAPER BUY\n\n")
            fp.write(f"Time:        {pos.entry_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            fp.write(f"Token:       {pos.symbol}\n")
            fp.write(f"Address:     {pos.token_address}\n\n")
            fp.write(f"Investment:  ${pos.amount_usd:.2f}\n")
            fp.write(f"Entry Price: ${pos.entry_price_usd:.6f}\n")
            fp.write(f"Score:       {score.total_score:.1f}\n")
            fp.write(f"Growth @ In: {pos.price_growth_at_entry_pct:+.1f}%\n")
            fp.write(f"Reason:      ENTRY_CONFIRMED (Score>=70 & Price>=+50% & Security Verified)\n")
            fp.write("-" * 50 + "\n\n")

    def _log_trade_sell(self, pos: PaperPosition) -> None:
        exit_time = pos.exit_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if pos.exit_timestamp else "N/A"
        hold_min = (pos.holding_time_seconds / 60.0) if pos.holding_time_seconds else 0.0
        with open(self.trades_txt_path, "a", encoding="utf-8") as fp:
            fp.write("-" * 50 + "\n")
            fp.write("PAPER SELL\n\n")
            fp.write(f"Time:        {exit_time}\n")
            fp.write(f"Token:       {pos.symbol}\n\n")
            fp.write(f"Investment:  ${pos.amount_usd:.2f}\n")
            fp.write(f"Entry:       ${pos.entry_price_usd:.6f}\n")
            fp.write(f"Peak:        ${pos.highest_price_usd:.6f}\n")
            fp.write(f"Exit:        ${pos.exit_price_usd:.6f}\n\n")
            fp.write(f"Gross P&L:   ${pos.gross_pnl_usd:+.4f}\n")
            fp.write(f"NET P&L:     ${pos.net_pnl_usd:+.4f}\n")
            fp.write(f"Return:      {pos.net_roi_pct:+.2f}%\n")
            fp.write(f"Hold Time:   {hold_min:.1f} min\n")
            fp.write(f"Exit Reason: {pos.exit_reason.value if pos.exit_reason else 'MANUAL'}\n")
            fp.write("-" * 50 + "\n\n")
            
        balance_before = self.portfolio.available_cash_usd - pos.net_pnl_usd
        balance_after = self.portfolio.available_cash_usd
        self.baseline_reporter.log_trade(pos, balance_before, balance_after)
        
        token = self.db.get_token(pos.token_address)
        if token:
            self.baseline_reporter.log_investor_ledger(pos, token)

    def _append_trade_csv(self, pos: PaperPosition) -> None:
        with open(self.trades_csv_path, "a", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow([
                pos.position_id,
                pos.token_address,
                pos.symbol,
                pos.entry_timestamp.isoformat(),
                pos.entry_price_usd,
                pos.amount_usd,
                pos.tokens_amount,
                pos.exit_timestamp.isoformat() if pos.exit_timestamp else "",
                pos.exit_price_usd or 0.0,
                pos.exit_reason.value if pos.exit_reason else "",
                pos.gross_pnl_usd,
                pos.net_pnl_usd,
                pos.net_roi_pct,
                pos.network_fee_usd,
                pos.priority_fee_usd,
                pos.dex_fee_usd,
                pos.estimated_slippage_pct,
                pos.estimated_price_impact_pct,
            ])

    def write_all_outputs(self) -> None:
        summary = self.portfolio.get_summary()
        open_pos = list(self.portfolio.open_positions.values())
        closed_pos = self.portfolio.closed_positions

        total_fees = sum(p.network_fee_usd + p.priority_fee_usd + p.dex_fee_usd for p in closed_pos + open_pos)
        total_slippage = sum((p.estimated_slippage_pct / 100.0) * p.amount_usd for p in open_pos + closed_pos)
        now_str = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Write portfolio.txt
        with open(self.portfolio_txt_path, "w", encoding="utf-8") as fp:
            fp.write("SOLANA MEME PAPER PORTFOLIO\n\n")
            fp.write(f"Initial Capital:   $100.00\n")
            fp.write(f"Available Cash:    ${summary['available_cash_usd']:.2f}\n")
            fp.write(f"Invested:          ${summary['invested_capital_usd']:.2f}\n")
            fp.write(f"Open Positions:    {len(open_pos)} / 50\n\n")
            fp.write(f"Realized P&L:      ${summary['total_closed_net_pnl_usd']:+.4f}\n")
            fp.write(f"Unrealized P&L:    ${summary['unrealized_pnl_usd']:+.4f}\n")
            fp.write(f"Total Equity:      ${summary['total_equity_usd']:.2f}\n\n")
            fp.write(f"Fees:              ${total_fees:.4f}\n")
            fp.write(f"Slippage:          ${total_slippage:.4f}\n\n")
            fp.write(f"Wins:              {summary['wins_count']}\n")
            fp.write(f"Losses:            {summary['losses_count']}\n")
            fp.write(f"Win Rate:          {summary['win_rate_pct']:.1f}%\n\n")
            fp.write(f"Last Update:\n{now_str}\n")

        # 2. Write open_positions.txt
        with open(self.positions_txt_path, "w", encoding="utf-8") as fp:
            fmt = "{:<8} | {:<20} | {:<12} | {:<12} | {:<10} | {:<12} | {:<10} | {:<8} | {:<6} | {:<8}\n"
            fp.write(fmt.format(
                "TOKEN", "ENTRY TIME", "ENTRY PRICE", "CURR PRICE", "INVESTMENT", "CURR VALUE", "P&L ($)", "P&L (%)", "SCORE", "STATUS"
            ))
            fp.write("-" * 130 + "\n")
            for p in open_pos:
                c_val = p.tokens_amount * p.current_price_usd
                pnl = c_val - p.amount_usd
                pnl_pct = (pnl / p.amount_usd) * 100.0 if p.amount_usd > 0 else 0.0
                fp.write(fmt.format(
                    p.symbol[:8],
                    p.entry_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    f"${p.entry_price_usd:.6f}",
                    f"${p.current_price_usd:.6f}",
                    f"${p.amount_usd:.2f}",
                    f"${c_val:.2f}",
                    f"${pnl:+.4f}",
                    f"{pnl_pct:+.1f}%",
                    f"{p.score_at_entry:.1f}",
                    "OPEN"
                ))
                
        # 3. Write Strategy Summary via Baseline Reporter
        db_tokens = self.db.list_tokens(limit=1000)
        state_counts = {}
        for t in db_tokens:
            s = t.state.value if hasattr(t.state, 'value') else str(t.state)
            state_counts[s] = state_counts.get(s, 0) + 1
            
        largest_win = max([p.net_pnl_usd for p in closed_pos if p.net_pnl_usd > 0], default=0.0)
        largest_loss = min([p.net_pnl_usd for p in closed_pos if p.net_pnl_usd < 0], default=0.0)
        avg_win = (sum([p.net_pnl_usd for p in closed_pos if p.net_pnl_usd > 0]) / summary['wins_count']) if summary['wins_count'] > 0 else 0.0
        avg_loss = (sum([p.net_pnl_usd for p in closed_pos if p.net_pnl_usd < 0]) / summary['losses_count']) if summary['losses_count'] > 0 else 0.0

        self.baseline_reporter.write_strategy_summary(
            current_balance=summary['available_cash_usd'],
            net_pnl=summary['total_closed_net_pnl_usd'],
            roi=(summary['total_closed_net_pnl_usd'] / 100.0) * 100.0,
            total_trades=len(closed_pos),
            wins=summary['wins_count'],
            losses=summary['losses_count'],
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown=0.0,
            open_count=len(open_pos),
            monitoring_count=state_counts.get(TokenState.MONITORING.value, 0),
            expired_count=state_counts.get(TokenState.EXPIRED.value, 0),
            rejected_count=state_counts.get(TokenState.SECURITY_BLOCKED.value, 0),
            security_unverified_count=state_counts.get(TokenState.SECURITY_BLOCKED.value, 0)
        )

        # 3. Append snapshot to portfolio_snapshots.csv
        with open(self.snapshots_csv_path, "a", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow([
                now_str,
                f"{summary['available_cash_usd']:.2f}",
                f"{len(open_pos)}",
                f"{summary['open_positions_value_usd']:.2f}",
                f"{summary['total_equity_usd']:.2f}",
                f"{summary['total_closed_net_pnl_usd']:.4f}",
                f"{summary['unrealized_pnl_usd']:.4f}",
                summary['wins_count'],
                summary['losses_count'],
                f"{summary['win_rate_pct']:.1f}",
            ])

    def generate_hourly_report(
        self,
        start_time: datetime,
        end_time: datetime,
        successful_cycles: int = 0,
        expected_cycles: int = 0,
    ) -> tuple[str, str]:
        return self.report_generator.generate_report(
            start_time=start_time,
            end_time=end_time,
            successful_cycles=successful_cycles,
            expected_cycles=expected_cycles,
        )

    def _update_supabase_stats(self) -> None:
        """Pushes real-time 24h stats to Supabase for the Next.js UI"""
        try:
            db_tokens = self.db.list_tokens(limit=10000)
            now = utc_now()
            today_tokens = [t for t in db_tokens if t.discovered_at and (now - t.discovered_at).total_seconds() < 86400]
            
            scanned = len(today_tokens)
            passed = len([t for t in today_tokens if t.status.value == "SUCCESS"])
            rejected = scanned - passed
            
            summary = self.portfolio.get_summary()
            total_pnl = summary.get("total_closed_net_pnl_usd", 0.0)
            
            self.supabase.update_daily_stats(scanned, rejected, passed, total_pnl)
        except Exception as e:
            pass

    def print_live_console_status(self, results: List[Dict[str, Any]]) -> None:
        """
        Renders clean live console view matching Section 30 requirements.
        """
        summary = self.portfolio.get_summary()
        print("\n" + "-" * 50)
        print(" SOLANA MEME PAPER LAB")
        print("-" * 50)
        print(f" CASH:           ${summary['available_cash_usd']:.2f}")
        print(f" EQUITY:         ${summary['total_equity_usd']:.2f}")
        print(f" OPEN POSITIONS: {summary['open_positions_count']} / 50")
        print(f" REALIZED P&L:   ${summary['total_closed_net_pnl_usd']:+.4f}")
        print(f" UNREALIZED P&L: ${summary['unrealized_pnl_usd']:+.4f}")
        print("-" * 50)

        # Show candidate/monitoring highlights
        monitoring_samples = [r for r in results if r["state"] in ("MONITORING", "READY_TO_ENTER", "QUARANTINE")][:3]
        for s in monitoring_samples:
            print(f" TOKEN:       {s['token']}")
            print(f" STATE:       {s['state']}")
            print(f" SCORE:       {s['score_val']:.1f}")
            print(f" PRICE (P0):  {s['growth']:+.1f}%")
            print(f" STATUS:      {s['status']}")
            print("-" * 50)

        # Show active open position highlights
        for pos in list(self.portfolio.open_positions.values())[:3]:
            pnl_pct = ((pos.current_price_usd - pos.entry_price_usd) / pos.entry_price_usd * 100.0) if pos.entry_price_usd > 0 else 0.0
            dd_pct = ((pos.highest_price_usd - pos.current_price_usd) / pos.highest_price_usd * 100.0) if pos.highest_price_usd > 0 else 0.0
            print(f" {pos.symbol} (OPEN)")
            print(f" ENTRY:       ${pos.entry_price_usd:.6f}")
            print(f" CURRENT:     ${pos.current_price_usd:.6f}")
            print(f" PEAK:        ${pos.highest_price_usd:.6f}")
            print(f" P&L:         {pnl_pct:>+6.2f}%")
            print(f" DD:          {dd_pct:>5.2f}%")
            print("-" * 50)

    def run_daemon(
        self,
        interval_sec: float = 15.0,
        report_interval_min: float = 60.0,
        limit: int = 10,
    ) -> None:
        """
        Runs continuously as a persistent background daemon:
        - Scans and evaluates candidates every interval_sec
        - Monitors active positions and updates dynamic trailing stops
        - Generates structured analytical report every report_interval_min into 'ОТЧЕТЫ/' and 'reports/'
        - Handles graceful termination on KeyboardInterrupt
        """
        print(f"[*] Starting Solana Meme Lab Daemon Mode...")
        print(f"    - Scan interval:        {interval_sec}s")
        print(f"    - Report interval:      {report_interval_min} minutes")
        print(f"    - Reports directory:    ОТЧЕТЫ/")
        print(f"    - Position Slot:        $2.00 Fixed")
        print(f"    - Max Concurrent Slots: 50")
        print(f"    - Strategy Rules:       Quarantine 0m -> Score>=70 & Price>=+160% -> Trailing Stop (-25% from peak)")
        print(f"[*] Press Ctrl+C to terminate.\n")

        period_start = utc_now()
        successful_cycles = 0
        expected_cycles = int((report_interval_min * 60.0) / max(1.0, interval_sec))

        # Start Fast Lane Thread
        self._fast_lane_stop_event.clear()
        self._fast_lane_thread = threading.Thread(target=self._fast_lane_loop, daemon=True)
        self._fast_lane_thread.start()

        try:
            while True:
                cycle_start = utc_now()
                cycle_id = f"cycle_{int(cycle_start.timestamp())}_{uuid.uuid4().hex[:6]}"
                discovered_cnt = 0
                analyzed_cnt = 0
                error_str = None

                try:
                    # 1. Discovery & Scoring
                    results = self.run_discovery_and_eval(limit=limit)
                    discovered_cnt = len(results)
                    analyzed_cnt = len(results)
                    successful_cycles += 1
                except Exception as e:
                    error_str = str(e)
                    print(f"[{cycle_start.strftime('%H:%M:%S')}] Discovery error: {e}")
                    results = []

                try:
                    # 2. Monitor Active Positions
                    closed = self.monitor_and_update_positions()
                    if closed:
                        print(f"[{cycle_start.strftime('%H:%M:%S')}] [!] Closed {len(closed)} position(s): {[p.symbol for p in closed]}")
                except Exception as e:
                    print(f"[{cycle_start.strftime('%H:%M:%S')}] Position monitor error: {e}")

                cycle_end = utc_now()
                dur_sec = (cycle_end - cycle_start).total_seconds()
                self.db.record_scan_cycle(
                    cycle_id=cycle_id,
                    started_at=cycle_start,
                    completed_at=cycle_end,
                    duration_sec=dur_sec,
                    tokens_discovered=discovered_cnt,
                    tokens_analyzed=analyzed_cnt,
                    error=error_str,
                )

                # Status heart-beat in console
                self.print_live_console_status(results)
                
                # Push daily stats to Supabase for the frontend UI
                self._update_supabase_stats()

                # 3. Check Hourly Report Trigger
                elapsed_sec = (utc_now() - period_start).total_seconds()
                if elapsed_sec >= report_interval_min * 60.0:
                    period_end = utc_now()
                    try:
                        report_file, _ = self.generate_hourly_report(
                            start_time=period_start,
                            end_time=period_end,
                            successful_cycles=successful_cycles,
                            expected_cycles=expected_cycles,
                        )
                        print(f"\n[+] Сформирован аналитический отчёт: {report_file}")
                    except Exception as e:
                        print(f"\n[!] Ошибка при генерации отчета: {e}")
                    
                    period_start = period_end
                    successful_cycles = 0
                    print("[*] Продолжаю непрерывное сканирование рынка...\n")

                time.sleep(interval_sec)

        except (KeyboardInterrupt, SystemExit):
            print("\n[!] Получен сигнал остановки. Остановка Fast Lane...")
            self._fast_lane_stop_event.set()
            if self._fast_lane_thread and self._fast_lane_thread.is_alive():
                self._fast_lane_thread.join(timeout=2.0)
            
            print("[!] Формирование финального отчёта...")
            period_end = utc_now()
            report_file, _ = self.generate_hourly_report(
                start_time=period_start,
                end_time=period_end,
                successful_cycles=successful_cycles,
                expected_cycles=expected_cycles,
            )
            print(f"[+] Финальный отчёт сохранён в {report_file}")
            print("[+] Завершение работы.")
