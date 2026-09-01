"""
Token Discovery Service for Solana Meme Research Lab.
Discovers new Solana meme tokens from market sources and registers them in the database.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from collectors.base import MarketDataProvider
from core.models import TokenInfo, TokenStatus, utc_now
from database.db import Database
from quarantine.manager import QuarantineManager

logger = logging.getLogger("research_lab.discovery")


class TokenDiscoveryService:
    def __init__(
        self,
        market_provider: MarketDataProvider,
        db: Database,
        quarantine_manager: Optional[QuarantineManager] = None,
    ):
        self.market_provider = market_provider
        self.db = db
        self.quarantine_manager = quarantine_manager or QuarantineManager()

    def discover_and_register(self, limit: int = 20) -> List[TokenInfo]:
        """Fetch candidates from market provider, register new ones with quarantine."""
        discovered = self.market_provider.discover_latest_tokens(limit=limit)
        registered: List[TokenInfo] = []

        for token in discovered:
            existing = self.db.get_token(token.address)
            if not existing:
                # Apply quarantine window (default 3m)
                self.quarantine_manager.register_token_quarantine(token)
                self.db.save_token(token)
                registered.append(token)
            else:
                registered.append(existing)

        return registered
