import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from core.models import PaperPosition, TokenInfo, TokenSnapshot, TokenStatus, ScoreResult

class BaselineReporter:
    def __init__(self, output_dir: str = "data/reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self._init_investor_ledger()

    def _get_filepath(self, filename: str) -> str:
        return os.path.join(self.output_dir, filename)
        
    def _init_investor_ledger(self):
        filepath = self._get_filepath(f"investor_ledger_{self.date_str}.txt")
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                header = (
                    f"{'AMOUNT ($)':<12} | {'TOKEN':<12} | {'DISCOVERY DATE':<20} | "
                    f"{'QUARANTINE TIME (MIN)':<22} | {'PURCHASE DATE':<20} | "
                    f"{'PEAK GROWTH (%)':<16} | {'MAX DRAWDOWN (%)':<17} | "
                    f"{'EXIT REASON':<15} | {'P&L ($)':<10} | {'EXIT DATE':<20}\n"
                )
                f.write(header)
                f.write("-" * len(header) + "\n")
                
    def log_investor_ledger(self, pos: PaperPosition, token: TokenInfo):
        filepath = self._get_filepath(f"investor_ledger_{self.date_str}.txt")
        
        disc_date = token.discovered_at.strftime("%Y-%m-%d %H:%M:%S")
        entry_date = pos.entry_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        exit_date = pos.exit_timestamp.strftime("%Y-%m-%d %H:%M:%S") if pos.exit_timestamp else "N/A"
        quarantine_time = token.age_minutes(pos.entry_timestamp)
        exit_reason = pos.exit_reason.value if pos.exit_reason else "N/A"
        
        peak_growth = pos.max_gain_from_entry_pct
        max_dd = pos.max_drawdown_pct
        
        with open(filepath, "a", encoding="utf-8") as f:
            row = (
                f"${pos.amount_usd:<11.2f} | {pos.symbol:<12} | {disc_date:<20} | "
                f"{quarantine_time:<22.1f} | {entry_date:<20} | "
                f"{peak_growth:<16.2f} | {max_dd:<17.2f} | "
                f"{exit_reason:<15} | ${pos.net_pnl_usd:<9.2f} | {exit_date:<20}\n"
            )
            f.write(row)

    def log_event(self, token_address: str, symbol: str, state: str, score: float, price: float, reason: str = ""):
        filepath = self._get_filepath(f"events_{self.date_str}.txt")
        now = datetime.now().isoformat()
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"[{now}] TOKEN: {symbol} ({token_address}) | STATE: {state} | SCORE: {score:.1f} | PRICE: {price:.6f} | REASON: {reason}\n")

    def log_portfolio(self, cash: float, open_positions_value: float, total_equity: float, realized_pnl: float, unrealized_pnl: float, fees: float, drawdown: float):
        filepath = self._get_filepath(f"portfolio_{self.date_str}.txt")
        now = datetime.now().isoformat()
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{now} | CASH: ${cash:.2f} | OPEN: ${open_positions_value:.2f} | EQUITY: ${total_equity:.2f} | REALIZED_PNL: ${realized_pnl:.2f} | UNREALIZED_PNL: ${unrealized_pnl:.2f} | FEES: ${fees:.4f} | DD: {drawdown:.2f}%\n")

    def log_trade(self, pos: PaperPosition, balance_before: float, balance_after: float):
        filepath = self._get_filepath(f"trades_{self.date_str}.txt")
        
        exit_time = pos.exit_timestamp.isoformat() if pos.exit_timestamp else "N/A"
        exit_price = f"{pos.exit_price_usd:.6f}" if pos.exit_price_usd else "N/A"
        exit_reason = pos.exit_reason.value if pos.exit_reason else "N/A"

        content = f"""
==================================================
TRADE ID: {pos.position_id}
TOKEN: {pos.symbol} ({pos.token_address})
DISCOVERY TIME: N/A
ENTRY TIME: {pos.entry_timestamp.isoformat()}
EXIT TIME: {exit_time}

P0: {pos.initial_discovery_price_usd:.6f}
ENTRY PRICE: {pos.entry_price_usd:.6f}
PEAK PRICE: {pos.highest_price_usd:.6f}
EXIT PRICE: {exit_price}

SCORE AT ENTRY: {pos.score_at_entry:.1f}
MOMENTUM AT ENTRY: {pos.price_growth_at_entry_pct:.1f}%

POSITION SIZE: ${pos.amount_usd:.2f}

GROSS PNL: ${pos.gross_pnl_usd:.4f}
FEES: ${pos.network_fee_usd + pos.priority_fee_usd + pos.dex_fee_usd:.4f}
SLIPPAGE: {pos.estimated_slippage_pct:.2f}%
NET PNL: ${pos.net_pnl_usd:.4f}
RETURN: {pos.net_roi_pct:.2f}%

EXIT REASON: {exit_reason}

DATA AGE AT ENTRY: {pos.data_age_at_entry_seconds:.1f}s
DATA AGE AT EXIT: {pos.data_age_at_exit_seconds:.1f}s

BALANCE BEFORE: ${balance_before:.2f}
BALANCE AFTER: ${balance_after:.2f}
==================================================
"""
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(content)

    def write_strategy_summary(
        self,
        current_balance: float,
        net_pnl: float,
        roi: float,
        total_trades: int,
        wins: int,
        losses: int,
        avg_win: float,
        avg_loss: float,
        largest_win: float,
        largest_loss: float,
        max_drawdown: float,
        open_count: int,
        monitoring_count: int,
        expired_count: int,
        rejected_count: int,
        security_unverified_count: int
    ):
        filepath = self._get_filepath("strategy_summary.txt")
        win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

        content = f"""SOLANA MEME RESEARCH LAB
PAPER TRADING BASELINE

Initial Capital: $100.00
Position Size: $2.00
Max Positions: 50

Quarantine: 5m
Monitoring: 60m
Entry Score: >=70
Entry Momentum: +50%
Exit: -25% Trailing

----------------------------

Current Balance: ${current_balance:.2f}
Net PnL: ${net_pnl:.2f}
ROI: {roi:.2f}%

Total Trades: {total_trades}
Wins: {wins}
Losses: {losses}
Win Rate: {win_rate:.1f}%

Average Win: ${avg_win:.2f}
Average Loss: ${avg_loss:.2f}

Largest Win: ${largest_win:.2f}
Largest Loss: ${largest_loss:.2f}

Max Drawdown: {max_drawdown:.2f}%

Open Positions: {open_count}
Monitoring: {monitoring_count}
Expired: {expired_count}
Rejected: {rejected_count}
Security Unverified: {security_unverified_count}

----------------------------
Last Updated: {datetime.now().isoformat()}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
