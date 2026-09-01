import unittest
import tempfile
import os
from pathlib import Path
from database.db import Database
from ledger.decision_ledger import DecisionLedger
from core.models import TokenInfo, TokenSnapshot, SecurityCheckResult, ScoreResult, TradeAction, TokenStatus


class TestDecisionLedger(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_ledger.db"
        self.db = Database(db_path=self.db_path)
        self.ledger = DecisionLedger(db=self.db)

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_record_and_retrieve_decision(self):
        token = TokenInfo(address="token_d1", symbol="DEC", name="Decision Test")
        self.db.save_token(token)
        snapshot = TokenSnapshot(token_address="token_d1", price_usd=0.01, liquidity_usd=25000.0, data_sources=["DexScreener"])
        security = SecurityCheckResult(token_address="token_d1", soft_security_score=85.0)
        score = ScoreResult(
            token_address="token_d1",
            total_score=82.0,
            security_score=85.0,
            liquidity_score=80.0,
            momentum_score=80.0,
            status=TokenStatus.CANDIDATE,
            decision_reason="Candidate threshold met",
            explanations=["Solid fundamentals"],
        )

        rec = self.ledger.record_decision(token, snapshot, security, score, action=TradeAction.BUY)
        self.assertEqual(rec.action, TradeAction.BUY)
        self.assertEqual(rec.total_score, 82.0)

        decisions = self.ledger.get_recent_decisions(limit=10)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].token_address, "token_d1")
        self.assertEqual(decisions[0].primary_reason, "Candidate threshold met")


if __name__ == "__main__":
    unittest.main()
