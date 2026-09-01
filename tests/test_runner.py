import os
import tempfile
import unittest
from core.models import TokenInfo, TokenSnapshot, TokenStatus, ExitReason
from runner.paper_runner import AutonomousPaperRunner
from database.db import Database


class TestPaperRunner(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="paper_test_")
        self.db = Database(db_path=os.path.join(self.tmp_dir, "test.db"))
        self.runner = AutonomousPaperRunner(db=self.db, runtime_dir=self.tmp_dir)

    def test_initial_capital_accounting(self):
        self.assertEqual(self.runner.portfolio.starting_capital_usd, 100.0)
        self.assertEqual(self.runner.portfolio.available_cash_usd, 100.0)
        self.assertEqual(len(self.runner.portfolio.open_positions), 0)

    def test_paper_buy_and_capacity(self):
        token = TokenInfo(address="tok1", symbol="TOK1", name="Tok 1")
        snap = TokenSnapshot(token_address="tok1", price_usd=0.001, liquidity_usd=20000.0)

        pos = self.runner.portfolio.open_virtual_position(token, snap)
        self.assertIsNotNone(pos)
        self.assertEqual(len(self.runner.portfolio.open_positions), 1)
        self.assertEqual(self.runner.portfolio.available_cash_usd, 98.0)

    def test_max_50_positions_limit(self):
        for i in range(50):
            t = TokenInfo(address=f"addr_{i}", symbol=f"T{i}", name=f"Token {i}")
            s = TokenSnapshot(token_address=f"addr_{i}", price_usd=0.01, liquidity_usd=15000.0)
            p = self.runner.portfolio.open_virtual_position(t, s)
            self.assertIsNotNone(p)

        self.assertEqual(len(self.runner.portfolio.open_positions), 50)
        self.assertEqual(self.runner.portfolio.available_cash_usd, 0.0)
        self.assertFalse(self.runner.portfolio.can_open_position())

        # 51st position must be rejected
        t51 = TokenInfo(address="addr_51", symbol="T51", name="Token 51")
        s51 = TokenSnapshot(token_address="addr_51", price_usd=0.01, liquidity_usd=15000.0)
        p51 = self.runner.portfolio.open_virtual_position(t51, s51)
        self.assertIsNone(p51)

    def test_capital_reuse_after_exit(self):
        # Open 1 position ($2)
        t = TokenInfo(address="reuse_tok", symbol="REUSE", name="Reuse Token")
        s = TokenSnapshot(token_address="reuse_tok", price_usd=1.0, liquidity_usd=25000.0)
        pos = self.runner.portfolio.open_virtual_position(t, s)
        self.assertEqual(self.runner.portfolio.available_cash_usd, 98.0)

        # Price rises to 2.0x, then pulls back by -30% to 1.4x (triggering TRAILING_STOP)
        snap_up = TokenSnapshot(token_address="reuse_tok", price_usd=2.0, liquidity_usd=25000.0)
        self.runner.portfolio.update_and_check_exits(snap_up)
        self.assertEqual(len(self.runner.portfolio.open_positions), 1)

        snap_drop = TokenSnapshot(token_address="reuse_tok", price_usd=1.4, liquidity_usd=25000.0)
        closed = self.runner.portfolio.update_and_check_exits(snap_drop)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.exit_reason, ExitReason.TRAILING_STOP)
        self.assertEqual(len(self.runner.portfolio.open_positions), 0)
        # Cash should be refunded > $98.0 (original $98 + ~$2.76 returned proceeds)
        self.assertGreater(self.runner.portfolio.available_cash_usd, 100.0)
        self.assertEqual(len(self.runner.portfolio.closed_positions), 1)

    def test_persistence_and_recovery(self):
        # Open a position in first instance
        t = TokenInfo(address="persist_tok", symbol="PST", name="Persist")
        s = TokenSnapshot(token_address="persist_tok", price_usd=0.05, liquidity_usd=30000.0)
        self.runner.portfolio.open_virtual_position(t, s)

        # Create new runner instance pointing to same DB
        runner2 = AutonomousPaperRunner(db=self.db, runtime_dir=self.tmp_dir)
        self.assertEqual(len(runner2.portfolio.open_positions), 1)
        self.assertEqual(runner2.portfolio.available_cash_usd, 98.0)
        self.assertIn("persist_tok", runner2.portfolio.open_positions)


if __name__ == "__main__":
    unittest.main()
