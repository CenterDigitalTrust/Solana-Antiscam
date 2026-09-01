"""
Unit test verifying mathematical synchronization between PORTFOLIO and TRADING sections in reports.
"""

import os
import shutil
import tempfile
import unittest
from datetime import timedelta

from core.models import ExitReason, TokenInfo, TokenSnapshot, utc_now
from database.db import Database
from runner.report_generator import HourlyReportGenerator
from simulation.portfolio import PaperPortfolio


class TestPortfolioReportSync(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_sync.db")
        self.reports_dir = os.path.join(self.tmp_dir, "ОТЧЕТЫ")
        self.db = Database(db_path=self.db_path)
        self.portfolio = PaperPortfolio(starting_capital_usd=100.0, position_size_usd=2.0, db=self.db)
        self.generator = HourlyReportGenerator(
            portfolio=self.portfolio,
            db=self.db,
            output_dirs=[self.reports_dir],
        )

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_mathematical_consistency_between_portfolio_and_trading(self):
        # 1. Simulate 6 buys ($2 each)
        for i in range(6):
            t = TokenInfo(address=f"token_{i}", symbol=f"TOK{i}", name=f"Token {i}", initial_price_usd=1.0)
            s = TokenSnapshot(token_address=f"token_{i}", price_usd=1.0, liquidity_usd=20000.0)
            pos = self.portfolio.open_virtual_position(t, s)
            self.assertIsNotNone(pos)

        # 6 positions opened ($12 invested, $88 available cash)
        self.assertEqual(len(self.portfolio.open_positions), 6)
        self.assertAlmostEqual(self.portfolio.available_cash_usd, 88.0, delta=0.01)

        # 2. Simulate 4 sells (2 wins, 2 losses)
        # Winner 1: pump to 1.5 (+50%), exit on pullback
        self.portfolio.update_and_check_exits(TokenSnapshot(token_address="token_0", price_usd=1.5, liquidity_usd=20000.0))
        c1 = self.portfolio.update_and_check_exits(TokenSnapshot(token_address="token_0", price_usd=1.1, liquidity_usd=20000.0))
        self.assertIsNotNone(c1)

        # Winner 2: pump to 2.0 (+100%), exit on pullback
        self.portfolio.update_and_check_exits(TokenSnapshot(token_address="token_1", price_usd=2.0, liquidity_usd=20000.0))
        c2 = self.portfolio.update_and_check_exits(TokenSnapshot(token_address="token_1", price_usd=1.45, liquidity_usd=20000.0))
        self.assertIsNotNone(c2)

        # Loser 1: drop directly to 0.70 (-30%)
        c3 = self.portfolio.update_and_check_exits(TokenSnapshot(token_address="token_2", price_usd=0.70, liquidity_usd=20000.0))
        self.assertIsNotNone(c3)

        # Loser 2: drop directly to 0.65 (-35%)
        c4 = self.portfolio.update_and_check_exits(TokenSnapshot(token_address="token_3", price_usd=0.65, liquidity_usd=20000.0))
        self.assertIsNotNone(c4)

        # Now: 2 open positions (tokens 4 and 5) -> Invested = $4.00
        # 4 closed positions
        self.assertEqual(len(self.portfolio.open_positions), 2)
        self.assertEqual(len(self.portfolio.closed_positions), 4)

        total_realized_pnl = sum(p.net_pnl_usd for p in self.portfolio.closed_positions)
        expected_available_cash = 100.0 - (2 * 2.0) + total_realized_pnl

        # 3. Generate Report and assert mathematical consistency
        now = utc_now()
        path, report = self.generator.generate_report(now - timedelta(hours=1), now, 360, 360)

        self.assertTrue(os.path.exists(path))
        self.assertIn("Paper Buys:     6", report)
        self.assertIn("Paper Sells:    4", report)
        self.assertIn("Open:             2", report)
        self.assertIn("Closed:           4", report)
        self.assertIn("Invested:        $4.00", report)
        self.assertIn(f"Available Cash:  ${expected_available_cash:.2f}", report)
        self.assertIn(f"Realized P&L:    ${total_realized_pnl:+.4f}", report)

        # Reopen report in a new instance reading directly from DB to verify restart persistence
        portfolio2 = PaperPortfolio(starting_capital_usd=100.0, position_size_usd=2.0, db=self.db)
        gen2 = HourlyReportGenerator(portfolio=portfolio2, db=self.db, output_dirs=[self.reports_dir])
        path2, report2 = gen2.generate_report(now - timedelta(hours=1), now, 360, 360)

        self.assertIn("Paper Buys:     6", report2)
        self.assertIn("Paper Sells:    4", report2)
        self.assertIn("Invested:        $4.00", report2)
        self.assertIn(f"Available Cash:  ${expected_available_cash:.2f}", report2)
        self.assertIn(f"Realized P&L:    ${total_realized_pnl:+.4f}", report2)


if __name__ == "__main__":
    unittest.main()
