"""
Quarantine Manager for Solana Meme Research Lab.
Controls token lifecycle and testing windows (3m, 5m, 7m, 10m, 15m).
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from core.models import TokenInfo, TokenStatus, utc_now


class QuarantineManager:
    def __init__(self, default_quarantine_minutes: float = 0.0):
        self.default_quarantine_minutes = default_quarantine_minutes

    def register_token_quarantine(
        self,
        token: TokenInfo,
        duration_minutes: Optional[float] = None,
    ) -> TokenInfo:
        duration = duration_minutes if duration_minutes is not None else self.default_quarantine_minutes
        now = utc_now()
        token.quarantine_until = now + dt.timedelta(minutes=duration)
        token.status = TokenStatus.QUARANTINE
        return token

    def is_quarantine_complete(
        self,
        token: TokenInfo,
        current_time: Optional[dt.datetime] = None,
    ) -> bool:
        now = current_time or utc_now()
        if not token.quarantine_until:
            return True
        return now >= token.quarantine_until

    def remaining_quarantine_seconds(
        self,
        token: TokenInfo,
        current_time: Optional[dt.datetime] = None,
    ) -> float:
        now = current_time or utc_now()
        if not token.quarantine_until:
            return 0.0
        delta = (token.quarantine_until - now).total_seconds()
        return max(0.0, delta)
