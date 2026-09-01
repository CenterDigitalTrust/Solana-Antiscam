"""
Analytical Hourly Report Generator for Solana Meme Research Lab.
Generates human-readable, professional analytical reports according to Section 29 specifications,
saving them to 'ОТЧЕТЫ', 'reports/', and 'runtime/results/'.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
from typing import Any, Dict, List, Optional

from core.models import EntryBlockReason, ExitReason, PaperPosition, TokenInfo, TokenState, TradeAction, utc_now
from database.db import Database
from simulation.portfolio import PaperPortfolio

REPORTS_DIR_NAME = "\u041e\u0422\u0427\u0415\u0422\u042b"  # ОТЧЕТЫ


class HourlyReportGenerator:
    def __init__(
        self,
        portfolio: PaperPortfolio,
        db: Database,
        output_dirs: Optional[List[str]] = None,
    ):
        self.portfolio = portfolio
        self.db = db
        self.output_dirs = output_dirs or [
            REPORTS_DIR_NAME,
            "reports",
            os.path.join("runtime", "results", REPORTS_DIR_NAME),
            os.path.join("runtime", "results"),
        ]
        for d in self.output_dirs:
            Path(d).mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
        successful_cycles: int = 0,
        expected_cycles: int = 0,
    ) -> tuple[str, str]:
        """
        Builds the structured analytical report for the specified time window.
        Returns (filepath_saved, report_text).
        """
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        file_ts_std = end_time.strftime("%Y-%m-%d_%H-%M")
        file_ts_compact = end_time.strftime("%Y%m%d_%H%M")

        # 1. Scanner cycle accounting
        cycle_summary = self.db.get_scan_cycles_summary(start_time, end_time)
        started_c = cycle_summary.get("started_cycles", 0) or successful_cycles
        completed_c = cycle_summary.get("completed_cycles", 0) or successful_cycles
        failed_c = cycle_summary.get("failed_cycles", 0)
        exp_c = expected_cycles if expected_cycles > 0 else max(360, started_c)

        # 2. Synchronize Portfolio state
        if hasattr(self.portfolio, "reload_from_db"):
            self.portfolio.reload_from_db()

        # 3. Token counts by explicit State
        token_counts = self._get_token_counts()

        # 4. Security gate counts
        sec_counts = self._get_security_gate_counts(start_time, end_time)

        # 5. Portfolio & Trading Summary (Guaranteed single source of truth)
        all_open = list(self.portfolio.open_positions.values())
        raw_closed = list(self.portfolio.closed_positions)
        if not raw_closed and self.db:
            raw_closed = self.db.list_paper_positions(is_open=False)
        all_closed = [p for p in raw_closed if p.exit_timestamp and start_time <= p.exit_timestamp <= end_time]

        wins = [p for p in all_closed if p.net_pnl_usd > 0]
        losses = [p for p in all_closed if p.net_pnl_usd <= 0]
        win_rate = (len(wins) / len(all_closed) * 100.0) if all_closed else 0.0

        starting_cash = self.portfolio.starting_capital_usd
        invested_cash = len(all_open) * self.portfolio.position_size_usd
        realized_pnl = sum(p.net_pnl_usd for p in all_closed)  # PnL for this specific period
        available_cash = self.portfolio.available_cash_usd

        open_market_val = sum(p.tokens_amount * p.current_price_usd for p in all_open)
        unrealized_pnl = sum((p.tokens_amount * p.current_price_usd) - p.total_entry_cost_usd for p in all_open)
        total_equity = available_cash + open_market_val

        # Total paper buys / sells lifetime
        lifetime_buys = len(all_open) + len(all_closed)
        lifetime_sells = len(all_closed)

        # Fee calculations
        total_dex_fees = sum(p.dex_fee_usd for p in all_closed) + sum(p.dex_fee_usd for p in all_open)
        total_net_fees = sum(p.network_fee_usd for p in all_closed) + sum(p.network_fee_usd for p in all_open)
        total_prio_fees = sum(p.priority_fee_usd for p in all_closed) + sum(p.priority_fee_usd for p in all_open)
        total_slippage = sum(p.amount_usd * (p.estimated_slippage_pct / 100.0) for p in all_closed + all_open)

        # Best / Worst Trades
        best_trade_str = "None"
        worst_trade_str = "None"
        if all_closed:
            best_pos = max(all_closed, key=lambda p: p.net_pnl_usd)
            worst_pos = min(all_closed, key=lambda p: p.net_pnl_usd)
            best_trade_str = f"{best_pos.symbol} ({best_pos.net_roi_pct:+.1f}%, ${best_pos.net_pnl_usd:+.4f})"
            worst_trade_str = f"{worst_pos.symbol} ({worst_pos.net_roi_pct:+.1f}%, ${worst_pos.net_pnl_usd:+.4f})"

        # Strategy Analytics
        strat_metrics = self._calculate_strategy_analytics(all_closed)

        # --- BUILD REPORT TEXT ---
        lines: List[str] = []
        lines.append("=" * 75)
        lines.append("SOLANA MEME PAPER TRADING REPORT")
        lines.append("=" * 75)
        lines.append("")
        lines.append("PERIOD")
        lines.append(f"Start: {start_str}")
        lines.append(f"End:   {end_str}")
        lines.append("")
        lines.append("SCANNER")
        lines.append(f"Expected cycles: {exp_c}")
        lines.append(f"Started:         {started_c}")
        lines.append(f"Completed:       {completed_c}")
        lines.append(f"Failed:          {failed_c}")
        lines.append("")
        lines.append("TOKENS")
        lines.append(f"Discovered:       {token_counts['discovered']}")
        lines.append(f"Analyzed:         {token_counts['analyzed']}")
        lines.append(f"Quarantine:       {token_counts['quarantine']}")
        lines.append(f"Monitoring:       {token_counts['monitoring']}")
        lines.append(f"Ready:            {token_counts['ready']}")
        lines.append(f"Open:             {len(all_open)}")
        lines.append(f"Closed:           {len(all_closed)}")
        lines.append(f"Rejected:         {token_counts['rejected']}")
        lines.append(f"Security blocked: {token_counts['security_blocked']}")
        lines.append(f"Expired:          {token_counts['expired']}")
        lines.append("")
        lines.append("SECURITY")
        lines.append(f"Checks performed:         {sec_counts['checks_performed']}")
        lines.append(f"Unique tokens verified:   {sec_counts['unique_verified']}")
        lines.append(f"Unique tokens unverified: {sec_counts['unique_unverified']}")
        lines.append("")
        lines.append("PORTFOLIO")
        lines.append(f"Starting Cash:   ${starting_cash:.2f}")
        lines.append(f"Available Cash:  ${available_cash:.2f}")
        lines.append(f"Invested:        ${invested_cash:.2f}")
        lines.append(f"Realized P&L:    ${realized_pnl:+.4f}")
        lines.append(f"Unrealized P&L:  ${unrealized_pnl:+.4f}")
        lines.append(f"Total Equity:    ${total_equity:.2f}")
        lines.append("")
        lines.append("TRADING")
        lines.append(f"Paper Buys:     {lifetime_buys}")
        lines.append(f"Paper Sells:    {lifetime_sells}")
        lines.append(f"Winning Trades: {len(wins)}")
        lines.append(f"Losing Trades:  {len(losses)}")
        lines.append(f"Win Rate:       {win_rate:.1f}%")
        lines.append("")
        lines.append("FEES")
        lines.append(f"DEX Fees:      ${total_dex_fees:.4f}")
        lines.append(f"Network Fees:  ${total_net_fees:.4f}")
        lines.append(f"Priority Fees: ${total_prio_fees:.4f}")
        lines.append(f"Slippage:      ${total_slippage:.4f}")
        lines.append("")
        lines.append(f"BEST TRADE:  {best_trade_str}")
        lines.append(f"WORST TRADE: {worst_trade_str}")
        lines.append("")

        # Section: OPEN POSITIONS
        lines.append("=" * 75)
        lines.append("OPEN POSITIONS")
        lines.append("=" * 75)
        if not self.portfolio.open_positions:
            lines.append("Открытых позиций нет.\n")
        else:
            lines.append(f"{'TOKEN':<10} | {'ENTRY':<11} | {'CURRENT':<11} | {'PEAK':<11} | {'P&L %':<9} | {'DD %':<8} | {'SCORE':<6} | {'AGE'}")
            lines.append("-" * 80)
            now = utc_now()
            for p in self.portfolio.open_positions.values():
                age_min = (now - p.entry_timestamp).total_seconds() / 60.0
                cur_pnl_pct = ((p.current_price_usd - p.entry_price_usd) / p.entry_price_usd * 100.0) if p.entry_price_usd > 0 else 0.0
                dd_pct = ((p.highest_price_usd - p.current_price_usd) / p.highest_price_usd * 100.0) if p.highest_price_usd > 0 else 0.0
                lines.append(
                    f"{p.symbol:<10} | ${p.entry_price_usd:<10.6f} | ${p.current_price_usd:<10.6f} | ${p.highest_price_usd:<10.6f} | {cur_pnl_pct:>+6.2f}% | {dd_pct:>5.2f}%  | {p.score_at_entry:<5.1f} | {age_min:.1f}m"
                )
            lines.append("")

        # Section: CLOSED POSITIONS
        lines.append("=" * 75)
        lines.append("CLOSED POSITIONS")
        lines.append("=" * 75)
        if not all_closed:
            lines.append("Закрытых позиций нет.\n")
        else:
            lines.append(f"{'TOKEN':<10} | {'ENTRY':<11} | {'EXIT':<11} | {'P&L $':<10} | {'P&L %':<9} | {'EXIT REASON':<18} | {'HOLD TIME'}")
            lines.append("-" * 90)
            for p in all_closed:
                hold_min = p.holding_time_seconds / 60.0 if p.holding_time_seconds else 0.0
                lines.append(
                    f"{p.symbol:<10} | ${p.entry_price_usd:<10.6f} | ${p.exit_price_usd or 0.0:<10.6f} | {p.net_pnl_usd:>+7.4f}$ | {p.net_roi_pct:>+6.2f}% | {str(p.exit_reason.value if p.exit_reason else 'MANUAL'):<18} | {hold_min:.1f}m"
                )
            lines.append("")

        # Section: MONITORING
        lines.append("=" * 75)
        lines.append("MONITORING (Кандидаты после 5м карантина)")
        lines.append("=" * 75)
        monitoring_tokens = self._get_active_monitoring_tokens()
        if not monitoring_tokens:
            lines.append("В активном мониторинге токенов нет.\n")
        else:
            lines.append(f"{'TOKEN':<10} | {'SCORE':<6} | {'PRICE FROM P0':<15} | {'SECURITY':<19} | {'LIQUIDITY':<11} | {'BLOCK REASON'}")
            lines.append("-" * 90)
            for m in monitoring_tokens:
                lines.append(
                    f"{m['symbol']:<10} | {m['score']:<6.1f} | {m['price_growth']:<15} | {m['security']:<19} | {m['liquidity']:<11} | {m['block_reason']}"
                )
            lines.append("")

        # Section: STRATEGY ANALYTICS
        lines.append("=" * 75)
        lines.append("STRATEGY ANALYTICS")
        lines.append("=" * 75)
        lines.append(f"Average entry score:           {strat_metrics['avg_entry_score']:.1f}")
        lines.append(f"Average price growth at entry: {strat_metrics['avg_growth_at_entry']:+.1f}%")
        lines.append(f"Average holding time:          {strat_metrics['avg_holding_time_min']:.1f} min")
        lines.append(f"Average P&L:                   ${strat_metrics['avg_pnl']:+.4f}")
        lines.append(f"Median P&L:                    ${strat_metrics['median_pnl']:+.4f}")
        lines.append(f"Maximum drawdown:              {strat_metrics['max_drawdown']:+.1f}%")
        lines.append(f"Maximum gain:                  {strat_metrics['max_gain']:+.1f}%")
        lines.append("=" * 75)

        report_content = "\n".join(lines) + "\n"

        # Save to standard and compact filenames across all directories
        primary_path = os.path.join(self.output_dirs[0], f"hourly_report_{file_ts_std}.txt")

        for d in self.output_dirs:
            if "report" in d.lower() and "result" not in d.lower() and "отчет" not in d.lower():
                fn = f"hourly_{file_ts_compact}.txt"
            else:
                fn = f"hourly_report_{file_ts_std}.txt"
            out_file = os.path.join(d, fn)
            with open(out_file, "w", encoding="utf-8") as fp:
                fp.write(report_content)

        return primary_path, report_content

    def _get_token_counts(self) -> Dict[str, int]:
        counts = {
            "discovered": 0, "analyzed": 0, "quarantine": 0, "monitoring": 0,
            "ready": 0, "rejected": 0, "security_blocked": 0, "expired": 0
        }
        try:
            with self.db._lock, self.db._get_connection() as conn:
                cur = conn.execute("SELECT count(*) as cnt FROM tokens")
                counts["discovered"] = cur.fetchone()["cnt"]

                cur = conn.execute("SELECT count(DISTINCT token_address) as cnt FROM decision_ledger")
                counts["analyzed"] = cur.fetchone()["cnt"]

                cur = conn.execute("SELECT status, count(*) as cnt FROM tokens GROUP BY status")
                for row in cur.fetchall():
                    s = str(row["status"]).upper()
                    if s == "QUARANTINE":
                        counts["quarantine"] = row["cnt"]
                    elif s == "MONITORING":
                        counts["monitoring"] = row["cnt"]
                    elif s == "READY_TO_ENTER":
                        counts["ready"] = row["cnt"]
                    elif s in ("REJECT", "REJECTED"):
                        counts["rejected"] = row["cnt"]
                    elif s == "SECURITY_BLOCKED":
                        counts["security_blocked"] = row["cnt"]
                    elif s == "EXPIRED":
                        counts["expired"] = row["cnt"]
        except Exception as e:
            logger.error("Error in _get_token_counts: %s", e, exc_info=True)
        return counts

    def _get_security_gate_counts(self, start_time: datetime, end_time: datetime) -> Dict[str, int]:
        res = {"checks_performed": 0, "unique_verified": 0, "unique_unverified": 0}
        try:
            with self.db._lock, self.db._get_connection() as conn:
                cur = conn.execute(
                    "SELECT count(*) as cnt FROM security_checks WHERE timestamp >= ? AND timestamp <= ?",
                    (start_time.isoformat(), end_time.isoformat())
                )
                res["checks_performed"] = cur.fetchone()["cnt"]

                cur = conn.execute(
                    """
                    SELECT token_address, is_mintable, is_freezable, top10_holders_pct, is_hard_reject
                    FROM security_checks
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY token_address
                    HAVING max(timestamp)
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                )
                for row in cur.fetchall():
                    is_ver = (not row["is_mintable"]) and (not row["is_freezable"]) and (row["top10_holders_pct"] is not None) and (not row["is_hard_reject"])
                    if is_ver:
                        res["unique_verified"] += 1
                    else:
                        res["unique_unverified"] += 1
        except Exception as e:
            logger.error("Error in _get_security_gate_counts: %s", e, exc_info=True)
        return res

    def _get_active_monitoring_tokens(self) -> List[Dict[str, Any]]:
        tokens: List[Dict[str, Any]] = []
        try:
            with self.db._lock, self.db._get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT t.symbol, t.initial_price_usd, sc_s.total_score, s.price_usd, s.liquidity_usd,
                           sc.soft_security_score, sc.is_mintable, sc.is_freezable, sc.top10_holders_pct, sc.is_hard_reject,
                           dl.primary_reason
                    FROM tokens t
                    LEFT JOIN (SELECT *, max(timestamp) FROM token_snapshots GROUP BY token_address) s ON t.address = s.token_address
                    LEFT JOIN (SELECT *, max(timestamp) FROM scores GROUP BY token_address) sc_s ON t.address = sc_s.token_address
                    LEFT JOIN (SELECT *, max(timestamp) FROM security_checks GROUP BY token_address) sc ON t.address = sc.token_address
                    LEFT JOIN (SELECT *, max(timestamp) FROM decision_ledger GROUP BY token_address) dl ON t.address = dl.token_address
                    WHERE t.status IN ('MONITORING', 'WATCH')
                    LIMIT 20
                    """
                )
                for r in cur.fetchall():
                    init_p = r["initial_price_usd"] or 0.0
                    cur_p = r["price_usd"] or 0.0
                    growth = ((cur_p - init_p) / init_p * 100.0) if init_p > 0 else 0.0
                    is_sec_ver = (not r["is_mintable"]) and (not r["is_freezable"]) and (r["top10_holders_pct"] is not None) and (not r["is_hard_reject"])
                    tokens.append({
                        "symbol": r["symbol"],
                        "score": r["total_score"] or 0.0,
                        "price_growth": f"{growth:+.1f}%",
                        "security": "VERIFIED" if is_sec_ver else "UNVERIFIED",
                        "liquidity": f"${r['liquidity_usd']:.0f}" if r["liquidity_usd"] else "PASS",
                        "block_reason": r["primary_reason"] or "WAITING_FOR_PRICE",
                    })
        except Exception as e:
            logger.error("Error in _get_active_monitoring_tokens: %s", e, exc_info=True)
        return tokens

    def _calculate_strategy_analytics(self, all_closed: List[PaperPosition]) -> Dict[str, Any]:
        if not all_closed:
            return {
                "avg_entry_score": 0.0,
                "avg_growth_at_entry": 0.0,
                "avg_holding_time_min": 0.0,
                "avg_pnl": 0.0,
                "median_pnl": 0.0,
                "max_drawdown": 0.0,
                "max_gain": 0.0,
            }

        scores = [p.score_at_entry for p in all_closed if p.score_at_entry > 0]
        growths = [p.price_growth_at_entry_pct for p in all_closed]
        hold_times = [(p.holding_time_seconds / 60.0) for p in all_closed if p.holding_time_seconds]
        pnls = sorted([p.net_pnl_usd for p in all_closed])
        drawdowns = [p.max_drawdown_pct for p in all_closed]
        gains = [p.max_gain_from_entry_pct for p in all_closed]

        avg_score = sum(scores) / len(scores) if scores else 70.0
        avg_growth = sum(growths) / len(growths) if growths else 50.0
        avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0.0
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        med_pnl = pnls[len(pnls) // 2] if pnls else 0.0
        max_dd = max(drawdowns) if drawdowns else 25.0
        max_g = max(gains) if gains else 0.0

        return {
            "avg_entry_score": avg_score,
            "avg_growth_at_entry": avg_growth,
            "avg_holding_time_min": avg_hold,
            "avg_pnl": avg_pnl,
            "median_pnl": med_pnl,
            "max_drawdown": -abs(max_dd),
            "max_gain": max_g,
        }
