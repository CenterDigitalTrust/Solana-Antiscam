import unittest
from datetime import datetime, timezone, timedelta
from core.models import TokenSnapshot, HardRejectReason
from analyzers.security import SecurityAnalyzer
from analyzers.liquidity import LiquidityAnalyzer
from analyzers.momentum import MomentumAnalyzer
from analyzers.wallet import WalletAnalyzer


class TestAnalyzers(unittest.TestCase):
    def test_security_hard_reject_freeze_authority(self):
        analyzer = SecurityAnalyzer()
        res = analyzer.analyze("token1", authorities_override={"is_freezable": True, "is_mintable": False})
        self.assertTrue(res.is_hard_reject)
        self.assertIn(HardRejectReason.FREEZE_AUTHORITY_ENABLED.value, res.hard_reject_reasons)

    def test_security_score_differentiation_realistic_profiles(self):
        analyzer = SecurityAnalyzer()
        # Profile 1: Well-distributed holders (top10=28%, max_whale=6%)
        snap1 = TokenSnapshot(token_address="token1", top10_holders_pct=28.0, creator_balance_pct=6.0)
        res1 = analyzer.analyze("token1", snapshot=snap1, authorities_override={"is_freezable": False, "is_mintable": False, "is_mutable": True})

        # Profile 2: High concentration (top10=68%, max_whale=32%)
        snap2 = TokenSnapshot(token_address="token2", top10_holders_pct=68.0, creator_balance_pct=32.0)
        res2 = analyzer.analyze("token2", snapshot=snap2, authorities_override={"is_freezable": False, "is_mintable": False, "is_mutable": True})

        # Profile 3: Extreme concentration (top10=86%, max_whale=45%)
        snap3 = TokenSnapshot(token_address="token3", top10_holders_pct=86.0, creator_balance_pct=45.0)
        res3 = analyzer.analyze("token3", snapshot=snap3, authorities_override={"is_freezable": False, "is_mintable": False, "is_mutable": True})

        # Scores must be strictly differentiated: res1 > res2 > res3
        self.assertGreater(res1.soft_security_score, res2.soft_security_score)
        self.assertGreater(res2.soft_security_score, res3.soft_security_score)
        self.assertNotEqual(res1.soft_security_score, res2.soft_security_score)

    def test_wallet_score_differentiation_realistic_profiles(self):
        analyzer = WalletAnalyzer()
        # Profile A: Established wallet (7 days old), distributed holders (top10=30%)
        snap_a = TokenSnapshot(token_address="tokA", top10_holders_pct=30.0, creator_balance_pct=4.0)
        res_a = analyzer.analyze("tokA", snapshot=snap_a, creator_age_hours=168.0)

        # Profile B: Fresh wallet (1h old), high concentration (top10=75%, creator=25%)
        snap_b = TokenSnapshot(token_address="tokB", top10_holders_pct=75.0, creator_balance_pct=25.0)
        res_b = analyzer.analyze("tokB", snapshot=snap_b, creator_age_hours=1.0)

        self.assertGreater(res_a.wallet_score, res_b.wallet_score)
        self.assertEqual(res_a.cluster_risk_level, "LOW")
        self.assertEqual(res_b.cluster_risk_level, "HIGH")

    def test_liquidity_data_unavailable_yields_zero(self):
        analyzer = LiquidityAnalyzer()
        snap = TokenSnapshot(token_address="token_no_liq", liquidity_usd=None, volume_5m_usd=500.0)
        res = analyzer.analyze("token_no_liq", current_snapshot=snap, historical_snapshots=[])
        self.assertTrue(res.is_data_unavailable)
        self.assertEqual(res.liquidity_score, 0.0)
        self.assertIn("DATA_UNAVAILABLE", res.explanations[0])

    def test_liquidity_velocity_calculation(self):
        analyzer = LiquidityAnalyzer()
        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        s0 = TokenSnapshot(token_address="token3", timestamp=t0, liquidity_usd=10000.0)
        s1 = TokenSnapshot(token_address="token3", timestamp=t1, liquidity_usd=12500.0)
        res = analyzer.analyze("token3", current_snapshot=s1, historical_snapshots=[s0])
        self.assertTrue(res.has_sufficient_history)
        self.assertEqual(res.delta_liquidity_5m, 2500.0)
        self.assertEqual(res.liquidity_velocity_usd_per_min, 500.0)

    def test_momentum_dead_activity_filter(self):
        analyzer = MomentumAnalyzer()
        snap_dead = TokenSnapshot(
            token_address="dead_token",
            volume_5m_usd=0.0,
            volume_1m_usd=0.0,
            buys_5m=0,
            sells_5m=0,
        )
        res = analyzer.analyze("dead_token", current_snapshot=snap_dead)
        self.assertTrue(res.is_activity_stale)
        self.assertEqual(res.momentum_score, 0.0)


if __name__ == "__main__":
    unittest.main()
