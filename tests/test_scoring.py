import unittest
from core.models import TokenInfo, TokenSnapshot, SecurityCheckResult, LiquidityMetrics, MomentumMetrics, TokenStatus
from scoring.engine import ScoreEngine, ScoreWeights


class TestScoring(unittest.TestCase):
    def test_candidate_qualification_with_verified_metrics(self):
        engine = ScoreEngine(candidate_threshold=75.0, reject_threshold=40.0)
        token = TokenInfo(address="addr1", symbol="MEME", name="Meme")
        snapshot = TokenSnapshot(token_address="addr1", price_usd=0.05, liquidity_usd=50000.0, volume_5m_usd=5000.0, volume_24h_usd=60000.0, top10_holders_pct=25.0)
        security = SecurityCheckResult(token_address="addr1", soft_security_score=85.0, is_hard_reject=False, top10_holders_pct=25.0, security_verified=True)
        liquidity = LiquidityMetrics(token_address="addr1", liquidity_score=85.0)
        momentum = MomentumMetrics(token_address="addr1", momentum_score=80.0, trade_count_5m=25)

        score = engine.calculate_score(token, snapshot, security, liquidity, momentum)
        self.assertGreaterEqual(score.total_score, 75.0)
        self.assertEqual(score.status, TokenStatus.CANDIDATE)

    def test_unverified_holder_guardrail_prevents_candidate(self):
        engine = ScoreEngine(candidate_threshold=75.0, reject_threshold=40.0)
        token = TokenInfo(address="addr1", symbol="MEME", name="Meme")
        snapshot = TokenSnapshot(token_address="addr1", price_usd=0.05, liquidity_usd=50000.0, volume_5m_usd=5000.0, volume_24h_usd=60000.0)
        # security without top10_holders_pct (None)
        security = SecurityCheckResult(token_address="addr1", soft_security_score=95.0, is_hard_reject=False, top10_holders_pct=None)
        liquidity = LiquidityMetrics(token_address="addr1", liquidity_score=85.0)
        momentum = MomentumMetrics(token_address="addr1", momentum_score=80.0, trade_count_5m=25)

        score = engine.calculate_score(token, snapshot, security, liquidity, momentum)
        # Even with high score, status must remain WATCH because holder distribution is unverified
        self.assertEqual(score.status, TokenStatus.WATCH)
        self.assertIn("unverified", score.decision_reason.lower())

    def test_hard_reject_overrides_score(self):
        engine = ScoreEngine()
        token = TokenInfo(address="addr2", symbol="RUG", name="Rug")
        snapshot = TokenSnapshot(token_address="addr2", price_usd=0.01, liquidity_usd=10000.0)
        security = SecurityCheckResult(
            token_address="addr2",
            soft_security_score=90.0,
            is_hard_reject=True,
            hard_reject_reasons=["FREEZE_AUTHORITY_ENABLED"]
        )
        liquidity = LiquidityMetrics(token_address="addr2", liquidity_score=80.0)
        momentum = MomentumMetrics(token_address="addr2", momentum_score=80.0)

        score = engine.calculate_score(token, snapshot, security, liquidity, momentum)
        self.assertEqual(score.status, TokenStatus.REJECT)
        self.assertIn("HARD REJECT", score.decision_reason)


if __name__ == "__main__":
    unittest.main()
