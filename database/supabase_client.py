import logging
import time
from typing import Optional

from supabase import create_client, Client
from core.models import TokenInfo, ScoreResult, SecurityCheckResult, TokenSnapshot

logger = logging.getLogger(__name__)

# Replace with your actual project URL and service_role key
SUPABASE_URL = "https://qfknvpozbzvzflhfjdte.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFma252cG96Ynp2emZsaGZqZHRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODAxNzUyMywiZXhwIjoyMTAzNTkzNTIzfQ.h_aQjRRDQg87TwgEAKecgq7BfiVbQ9suLOHYPVoa16E"

class SupabaseManager:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized.")

    def upsert_token_state(
        self,
        token: TokenInfo,
        snapshot: TokenSnapshot,
        security: SecurityCheckResult,
        score: ScoreResult
    ):
        """
        Overwrites the single row for this token in Supabase.
        This represents the 'live' state of the token without bloating the database.
        """
        try:
            data = {
                "token_address": token.address,
                "ticker": token.symbol or "UNKNOWN",
                "discovered_at": token.discovered_at.isoformat() if token.discovered_at else None,
                "updated_at": snapshot.timestamp.isoformat(),
                "score": score.total_score,
                "price_usd": snapshot.price_usd,
                "liquidity_usd": snapshot.liquidity_usd,
                "market_cap_usd": snapshot.market_cap_usd,
                "initial_price_usd": getattr(token, 'initial_price_usd', snapshot.price_usd),
                "mint_authority_active": security.is_mintable,
                "freeze_authority_active": security.is_freezable,
                "top10_holder_pct": security.top10_holders_pct or 0.0,
                "status": token.status.value if hasattr(token.status, 'value') else token.status,
                "status_reason": score.decision_reason or ""
            }
            
            # Use upsert to insert or update the row
            self.client.table("tokens").upsert(data).execute()
            logger.info(f"[Supabase] Updated live state for {token.symbol} ({token.address})")
        except Exception as e:
            logger.error(f"[Supabase] Failed to upsert token {token.address}: {e}")

    def update_daily_stats(self, scanned: int, rejected: int, passed: int, pnl: float):
        try:
            data = {
                "id": 1,
                "scanned_today": scanned,
                "rejected_today": rejected,
                "passed_today": passed,
                "daily_pnl_usd": pnl,
                "updated_at": "now()"
            }
            self.client.table("daily_stats").upsert(data).execute()
        except Exception as e:
            logger.error(f"[Supabase] Failed to update daily stats: {e}")

    def cleanup_stale_tokens(self, hours_old: int = 24):
        """
        Garbage collection: delete tokens older than X hours to keep the DB lean.
        """
        try:
            # Delete tokens where updated_at is older than X hours
            # Supabase Python client currently doesn't easily support raw time expressions like 'now() - interval',
            # so we'll pass an ISO string of the cutoff time.
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_old)).isoformat()
            
            res = self.client.table("tokens").delete().lt("updated_at", cutoff).execute()
            deleted_count = len(res.data) if res.data else 0
            if deleted_count > 0:
                logger.info(f"[Supabase GC] Deleted {deleted_count} stale tokens older than {hours_old}h.")
        except Exception as e:
            logger.error(f"[Supabase GC] Failed to cleanup stale tokens: {e}")
