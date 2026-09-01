"""
Realistic Execution Simulator for Solana Meme Research Lab.
Evaluates cost drag, price impact, slippage, and net trade economics for $2 positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from collectors.base import QuoteProvider
from core.models import TokenSnapshot
from simulation.fee_model import FeeModel, FeeSource


@dataclass
class SimulatedExecution:
    requested_amount_usd: float
    market_price_usd: float
    effective_entry_price_usd: float
    tokens_acquired: float
    estimated_slippage_pct: float
    estimated_price_impact_pct: float
    network_fee_usd: float
    priority_fee_usd: float
    dex_fee_usd: float
    total_friction_cost_usd: float
    friction_cost_pct: float
    fee_source: FeeSource
    notes: str


class ExecutionSimulator:
    def __init__(
        self,
        fee_model: Optional[FeeModel] = None,
        quote_provider: Optional[QuoteProvider] = None,
        default_slippage_pct: float = 1.0,
    ):
        self.fee_model = fee_model or FeeModel()
        self.quote_provider = quote_provider
        self.default_slippage_pct = default_slippage_pct

    def simulate_buy(
        self,
        token_address: str,
        market_price_usd: float,
        position_size_usd: float = 2.0,
        snapshot: Optional[TokenSnapshot] = None,
        venue: str = "raydium",
    ) -> SimulatedExecution:
        if market_price_usd <= 0:
            market_price_usd = 0.000001

        # 1. Price Impact Estimation
        price_impact_pct = 0.5  # default conservative baseline
        if snapshot and snapshot.liquidity_usd > 0:
            # Constant product AMM impact approximation: dx / (x + dx)
            # Pool liquidity is 2 * X_usd in standard pools
            half_pool_liq = snapshot.liquidity_usd / 2.0
            price_impact_pct = min(15.0, (position_size_usd / half_pool_liq) * 100.0)

        # 2. Fixed Fees (Solana network + priority)
        fixed_costs = self.fee_model.calculate_fixed_costs_usd()
        network_fee_usd = fixed_costs["network_fee_usd"]
        priority_fee_usd = fixed_costs["priority_fee_usd"]

        # 3. DEX Variable Fee
        dex_fee_cfg = self.fee_model.get_dex_fee(venue=venue)
        dex_fee_usd = position_size_usd * (dex_fee_cfg.pool_fee_pct / 100.0)

        # 4. Total Fees & Slippage
        slippage_pct = self.default_slippage_pct
        total_price_markup_pct = (price_impact_pct + slippage_pct) / 100.0
        effective_price = market_price_usd * (1.0 + total_price_markup_pct)

        # Capital after variable fee
        net_capital_for_tokens = max(0.0, position_size_usd - dex_fee_usd)
        tokens_acquired = net_capital_for_tokens / effective_price if effective_price > 0 else 0.0

        total_friction_usd = network_fee_usd + priority_fee_usd + dex_fee_usd + (position_size_usd * total_price_markup_pct)
        friction_pct = (total_friction_usd / position_size_usd) * 100.0

        return SimulatedExecution(
            requested_amount_usd=position_size_usd,
            market_price_usd=market_price_usd,
            effective_entry_price_usd=effective_price,
            tokens_acquired=tokens_acquired,
            estimated_slippage_pct=slippage_pct,
            estimated_price_impact_pct=price_impact_pct,
            network_fee_usd=network_fee_usd,
            priority_fee_usd=priority_fee_usd,
            dex_fee_usd=dex_fee_usd,
            total_friction_cost_usd=round(total_friction_usd, 5),
            friction_cost_pct=round(friction_pct, 2),
            fee_source=dex_fee_cfg.fee_source,
            notes=f"Simulated {venue} entry for $2 slot",
        )
