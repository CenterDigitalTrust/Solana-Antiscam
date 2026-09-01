"""
Paper Portfolio for Solana Meme Research Lab.
Manages $100 starting capital, $2 positions (max 50 simultaneous), and tracks P&L, win rate, and dynamic trailing stop exits.
NO FIXED TAKE PROFIT: Strictly trailing stop -25% from highest achieved price peak.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional

from core.models import ExitReason, PaperPosition, TokenInfo, TokenSnapshot, utc_now
from simulation.execution_simulator import ExecutionSimulator


class PaperPortfolio:
    def __init__(
        self,
        starting_capital_usd: float = 100.0,
        position_size_usd: float = 2.0,
        max_positions: int = 50,
        trailing_stop_pct: float = 25.0,
        execution_simulator: Optional[ExecutionSimulator] = None,
        db: Optional[Any] = None,
    ):
        self.starting_capital_usd = starting_capital_usd
        self.available_cash_usd = starting_capital_usd
        self.position_size_usd = position_size_usd
        self.max_positions = max_positions
        self.trailing_stop_pct = trailing_stop_pct
        self.execution_simulator = execution_simulator or ExecutionSimulator()
        self.db = db

        self.open_positions: Dict[str, PaperPosition] = {}
        self.closed_positions: List[PaperPosition] = []
        self._lock = threading.Lock()

        if self.db:
            self.reload_from_db()

    def reload_from_db(self) -> None:
        if not self.db:
            return
        loaded_open = self.db.list_paper_positions(is_open=True)
        self.open_positions = {p.token_address: p for p in loaded_open}
        self.closed_positions = self.db.list_paper_positions(is_open=False)
        invested = sum(p.amount_usd for p in self.open_positions.values())
        realized = sum(p.net_pnl_usd for p in self.closed_positions)
        self.available_cash_usd = self.starting_capital_usd - invested + realized

    def can_open_position(self) -> bool:
        with self._lock:
            return (
                len(self.open_positions) < self.max_positions
                and self.available_cash_usd >= (self.position_size_usd + 0.05) # Add $0.05 buffer for network/priority fees
            )

    def open_virtual_position(
        self,
        token: TokenInfo,
        snapshot: TokenSnapshot,
        venue: str = "raydium",
        score_result: Optional[Any] = None,
    ) -> Optional[PaperPosition]:
        if not self.can_open_position() or snapshot.price_usd is None:
            return None

        sim = self.execution_simulator.simulate_buy(
            token_address=token.address,
            market_price_usd=snapshot.price_usd,
            position_size_usd=self.position_size_usd,
            snapshot=snapshot,
            venue=venue,
        )

        pos_id = str(uuid.uuid4())[:8]
        entry_price = sim.effective_entry_price_usd
        # Trailing stop starts at -25% below entry price
        initial_stop_price = entry_price * (1.0 - (self.trailing_stop_pct / 100.0))

        initial_p = token.initial_price_usd or entry_price
        price_growth_at_entry = ((entry_price - initial_p) / initial_p * 100.0) if initial_p > 0 else 0.0

        pos = PaperPosition(
            position_id=pos_id,
            token_address=token.address,
            symbol=token.symbol,
            entry_timestamp=utc_now(),
            entry_price_usd=entry_price,
            amount_usd=self.position_size_usd,
            tokens_amount=sim.tokens_acquired,
            estimated_slippage_pct=sim.estimated_slippage_pct,
            estimated_price_impact_pct=sim.estimated_price_impact_pct,
            network_fee_usd=sim.network_fee_usd,
            priority_fee_usd=sim.priority_fee_usd,
            dex_fee_usd=sim.dex_fee_usd,
            total_entry_cost_usd=self.position_size_usd + sim.network_fee_usd + sim.priority_fee_usd,
            current_price_usd=entry_price,
            highest_price_usd=entry_price,  # Peak starts at entry price
            stop_loss_price_usd=initial_stop_price,
            is_open=True,
            initial_discovery_price_usd=initial_p,
            price_growth_at_entry_pct=price_growth_at_entry,
            score_at_entry=score_result.total_score if score_result else (token.current_score or 0.0),
            score_at_t0=token.initial_score,
            score_at_t5=token.quarantine_score,
            max_gain_from_t0_pct=price_growth_at_entry,
            max_gain_from_entry_pct=0.0,
            max_drawdown_pct=0.0,
            data_age_at_entry_seconds=snapshot.data_age_seconds if snapshot else 0.0,
        )

        with self._lock:
            self.available_cash_usd -= pos.total_entry_cost_usd
            self.open_positions[token.address] = pos
        if self.db:
            self.db.save_paper_position(pos)
        return pos

    def update_and_check_exits(self, snapshot: TokenSnapshot) -> Optional[PaperPosition]:
        """
        Dynamically updates the price peak and checks trailing stop condition:
        if price > highest_price:
            highest_price = price
            stop_loss_price = highest_price * 0.75
        if price <= stop_loss_price:
            close_position(reason=TRAILING_STOP)
        """
        token_addr = snapshot.token_address
        with self._lock:
            if token_addr not in self.open_positions or snapshot.price_usd is None:
                return None
            pos = self.open_positions[token_addr]
        
        current_price = snapshot.price_usd
        pos.current_price_usd = current_price

        # Update peak and ratchet up trailing stop
        if current_price > pos.highest_price_usd:
            pos.highest_price_usd = current_price
            pos.stop_loss_price_usd = pos.highest_price_usd * (1.0 - (self.trailing_stop_pct / 100.0))

        # Update analytical research metrics
        if pos.initial_discovery_price_usd > 0:
            gain_from_t0 = ((current_price - pos.initial_discovery_price_usd) / pos.initial_discovery_price_usd) * 100.0
            pos.max_gain_from_t0_pct = max(pos.max_gain_from_t0_pct, gain_from_t0)

        if pos.entry_price_usd > 0:
            gain_from_entry = ((current_price - pos.entry_price_usd) / pos.entry_price_usd) * 100.0
            pos.max_gain_from_entry_pct = max(pos.max_gain_from_entry_pct, gain_from_entry)

        if pos.highest_price_usd > 0:
            drawdown = ((pos.highest_price_usd - current_price) / pos.highest_price_usd) * 100.0
            pos.max_drawdown_pct = max(pos.max_drawdown_pct, drawdown)

        # Check Trailing Stop Trigger (-25% from highest recorded peak)
        if current_price <= pos.stop_loss_price_usd:
            return self._close_position(pos, exit_price=current_price, reason=ExitReason.TRAILING_STOP, snapshot=snapshot)

        # Check Liquidity Collapse Emergency Exit (< $1000)
        if snapshot.liquidity_usd is not None and snapshot.liquidity_usd < 1000.0:
            return self._close_position(pos, exit_price=current_price, reason=ExitReason.LIQUIDITY_COLLAPSE, snapshot=snapshot)

        if self.db:
            self.db.save_paper_position(pos)
        return None

    def _close_position(
        self,
        pos: PaperPosition,
        exit_price: float,
        reason: ExitReason,
        snapshot: Optional[TokenSnapshot] = None,
    ) -> PaperPosition:
        pos.is_open = False
        pos.exit_timestamp = utc_now()
        pos.exit_price_usd = exit_price
        pos.exit_reason = reason
        pos.holding_time_seconds = (pos.exit_timestamp - pos.entry_timestamp).total_seconds()
        if snapshot:
            pos.data_age_at_exit_seconds = snapshot.data_age_seconds

        gross_val = pos.tokens_amount * exit_price
        fixed_costs = self.execution_simulator.fee_model.calculate_fixed_costs_usd()
        exit_fees = fixed_costs["total_fixed_fee_usd"] + (gross_val * 0.0025)
        net_returned = max(0.0, gross_val - exit_fees)

        pos.gross_pnl_usd = gross_val - pos.amount_usd
        pos.net_pnl_usd = net_returned - pos.total_entry_cost_usd
        pos.net_roi_pct = (pos.net_pnl_usd / pos.total_entry_cost_usd) * 100.0

        with self._lock:
            self.available_cash_usd += net_returned
            if pos.token_address in self.open_positions:
                del self.open_positions[pos.token_address]
            self.closed_positions.append(pos)
            
        if self.db:
            self.db.save_paper_position(pos)
        return pos

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total_pnl = sum(p.net_pnl_usd for p in self.closed_positions)
            wins = [p for p in self.closed_positions if p.net_pnl_usd > 0]
            losses = [p for p in self.closed_positions if p.net_pnl_usd <= 0]
            win_rate = (len(wins) / len(self.closed_positions) * 100.0) if self.closed_positions else 0.0

            open_market_val = sum(p.tokens_amount * p.current_price_usd for p in self.open_positions.values())
            invested_cap = len(self.open_positions) * self.position_size_usd
            unrealized_pnl = sum((p.tokens_amount * p.current_price_usd) - p.total_entry_cost_usd for p in self.open_positions.values())
            total_equity = self.available_cash_usd + open_market_val

            return {
                "starting_capital_usd": self.starting_capital_usd,
                "available_cash_usd": round(self.available_cash_usd, 2),
                "invested_capital_usd": round(invested_cap, 2),
                "open_positions_value_usd": round(open_market_val, 2),
                "unrealized_pnl_usd": round(unrealized_pnl, 4),
                "total_equity_usd": round(total_equity, 2),
                "open_positions_count": len(self.open_positions),
                "closed_positions_count": len(self.closed_positions),
                "total_closed_net_pnl_usd": round(total_pnl, 4),
                "win_rate_pct": round(win_rate, 1),
                "wins_count": len(wins),
                "losses_count": len(losses),
            }
