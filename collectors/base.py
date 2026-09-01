"""
Abstract Base Provider Interfaces for Solana Meme Research Lab.
All data queries in analyzers go through these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.models import SecurityCheckResult, TokenInfo, TokenSnapshot


class DataProvider(ABC):
    """Base provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform a safe capability check without leaks."""
        pass


class MarketDataProvider(DataProvider):
    """Interface for market data, pairs, OHLCV, and discovery."""

    @abstractmethod
    def get_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        pass

    @abstractmethod
    def discover_latest_tokens(self, limit: int = 20) -> List[TokenInfo]:
        pass


class OnChainProvider(DataProvider):
    """Interface for Solana RPC, accounts, balances, and authorities."""

    @abstractmethod
    def get_token_authorities(self, token_address: str) -> Dict[str, Any]:
        """Retrieve mint_authority, freeze_authority, decimals, supply."""
        pass

    @abstractmethod
    def get_top_holders(self, token_address: str, limit: int = 10) -> Dict[str, Any]:
        """Retrieve top holders and concentration."""
        pass


class SecurityProvider(DataProvider):
    """Interface for security checks."""

    @abstractmethod
    def check_token_security(self, token_address: str) -> SecurityCheckResult:
        pass


class QuoteProvider(DataProvider):
    """Interface for quotes and execution simulations (Optional)."""

    @abstractmethod
    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount_usd: float,
        slippage_bps: int = 100,
    ) -> Dict[str, Any]:
        pass
