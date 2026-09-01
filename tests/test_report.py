import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from core.models import ExitReason, PaperPosition, TokenInfo, TokenSnapshot, utc_now
from database.db import Database
from runner.report_generator import HourlyReportGenerator
from simulation.portfolio import PaperPortfolio


class TestHourlyReport(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test.db")
        self.reports_dir = os.path.join(self.tmp_dir, "ОТЧЕТЫ")
        self.results_dir = os.path.join(self.tmp_dir, "results")
        self.db = Database(db_path=self.db_path)
        self.portfolio = PaperPortfolio(starting_capital_usd=100.0, position_size_usd=2.0, db=self.db)
        self.generator = HourlyReportGenerator(
            portfolio=self.portfolio,
            db=self.db,
            output_dirs=[self.reports_dir, self.results_dir],
        )

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_report_generation_empty_period(self):
        start = utc_now() - timedelta(hours=1)
        end = utc_now()
        path, content = self.generator.generate_report(start, end, successful_cycles=4, expected_cycles=4)

        self.assertTrue(os.path.exists(path))
        self.assertIn("SOLANA MEME PAPER TRADING REPORT", content)
        self.assertIn("Starting Cash:   $100.00", content)
        self.assertIn("Available Cash:  $100.00", content)
        self.assertIn("Open:             0", content)
        self.assertIn("Closed:           0", content)

    def test_report_generation_with_trades_and_drawdown(self):
        # 1. Open a position with >15% drawdown
        t1 = TokenInfo(address="addr_dd", symbol="DUMP", name="Dump Coin")
        s1 = TokenSnapshot(token_address="addr_dd", price_usd=1.0, liquidity_usd=20000.0)
        pos1 = self.portfolio.open_virtual_position(t1, s1)
        # Pump to $2.00, then drop to $1.60 (-20% drawdown from $2.00 peak)
        self.portfolio.update_and_check_exits(TokenSnapshot(token_address="addr_dd", price_usd=2.0, liquidity_usd=20000.0))
        self.portfolio.update_and_check_exits(TokenSnapshot(token_address="addr_dd", price_usd=1.60, liquidity_usd=20000.0))

        # 2. Open another position and close it via trailing stop
        t2 = TokenInfo(address="addr_win", symbol="WINNER", name="Winner Coin")
        s2 = TokenSnapshot(token_address="addr_win", price_usd=1.0, liquidity_usd=30000.0)
        pos2 = self.portfolio.open_virtual_position(t2, s2)
        # Pump to $3.00, then pullback to $2.20 (-26.6% from peak -> closes)
        self.portfolio.update_and_check_exits(TokenSnapshot(token_address="addr_win", price_usd=3.0, liquidity_usd=30000.0))
        closed = self.portfolio.update_and_check_exits(TokenSnapshot(token_address="addr_win", price_usd=2.20, liquidity_usd=30000.0))
        self.assertIsNotNone(closed)

        start = utc_now() - timedelta(minutes=30)
        end = utc_now() + timedelta(minutes=5)
        path, content = self.generator.generate_report(start, end, successful_cycles=10, expected_cycles=10)

        self.assertTrue(os.path.exists(path))
        # Verify DUMP is in open positions
        self.assertIn("DUMP", content)
        # Verify WINNER is in closed positions
        self.assertIn("WINNER", content)
        self.assertIn("TRAILING_STOP", content)
        # Verify both target folders received the file
        self.assertTrue(os.path.exists(os.path.join(self.reports_dir, os.path.basename(path))))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, os.path.basename(path))))


if __name__ == "__main__":
    unittest.main()
