"""
Configurable Fee Model for Solana Meme Research Lab.
Explicitly distinguishes ACTUAL known pool fees from ASSUMED defaults.
Accurately models base network fee, priority fee, and DEX fee.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class FeeSource(str, Enum):
    ACTUAL = "ACTUAL"
    ASSUMED = "ASSUMED"


@dataclass
class DexFeeConfig:
    venue: str
    pool_fee_pct: float
    fee_source: FeeSource = FeeSource.ASSUMED
    notes: str = ""


class FeeModel:
    """Calculates granular execution fees for trades on Solana DEXes."""

    DEFAULT_VENUE_FEES: Dict[str, float] = {
        "raydium": 0.25,    # 0.25% standard AMM fee
        "raydium_clmm": 0.20,
        "meteora": 0.15,
        "orca": 0.30,
        "pumpfun": 1.00,   # 1.0% Pump.fun bonding curve fee
    }

    def __init__(
        self,
        base_network_fee_sol: float = 0.000005,  # 5,000 lamports standard tx fee
        priority_fee_sol: float = 0.00005,      # 50,000 lamports priority fee
        sol_price_usd: float = 160.0,
    ):
        self.base_network_fee_sol = base_network_fee_sol
        self.priority_fee_sol = priority_fee_sol
        self.sol_price_usd = sol_price_usd

    def get_dex_fee(self, venue: str = "raydium", actual_fee_pct: Optional[float] = None) -> DexFeeConfig:
        if actual_fee_pct is not None:
            return DexFeeConfig(
                venue=venue.lower(),
                pool_fee_pct=actual_fee_pct,
                fee_source=FeeSource.ACTUAL,
                notes="Pool metadata verified fee",
            )

        venue_key = venue.lower()
        fee_pct = self.DEFAULT_VENUE_FEES.get(venue_key, 0.25)
        return DexFeeConfig(
            venue=venue_key,
            pool_fee_pct=fee_pct,
            fee_source=FeeSource.ASSUMED,
            notes=f"Configurable assumption for {venue_key}",
        )

    def calculate_fixed_costs_usd(self) -> Dict[str, float]:
        network_usd = self.base_network_fee_sol * self.sol_price_usd
        priority_usd = self.priority_fee_sol * self.sol_price_usd
        return {
            "network_fee_usd": round(network_usd, 5),
            "priority_fee_usd": round(priority_usd, 5),
            "total_fixed_fee_usd": round(network_usd + priority_usd, 5),
        }
