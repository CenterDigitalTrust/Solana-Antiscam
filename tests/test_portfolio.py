import unittest
from core.models import TokenInfo, TokenSnapshot, ExitReason
from simulation.portfolio import PaperPortfolio


class TestPortfolio(unittest.TestCase):
    def test_open_position_and_trailing_stop_from_peak(self):
        portfolio = PaperPortfolio(starting_capital_usd=100.0, position_size_usd=2.0, trailing_stop_pct=25.0)
        token = TokenInfo(address="token_p1", symbol="P1", name="Portfolio Test")
        snap_entry = TokenSnapshot(token_address="token_p1", price_usd=1.0, liquidity_usd=50000.0)

        pos = portfolio.open_virtual_position(token, snap_entry)
        self.assertIsNotNone(pos)
        self.assertEqual(len(portfolio.open_positions), 1)
        self.assertEqual(portfolio.available_cash_usd, 98.0)
        entry_price = pos.entry_price_usd

        # 1. Price increases by +100% -> peak updates to 2 * entry_price
        snap_pump = TokenSnapshot(token_address="token_p1", price_usd=entry_price * 2.0, liquidity_usd=60000.0)
        portfolio.update_and_check_exits(snap_pump)
        self.assertEqual(pos.highest_price_usd, entry_price * 2.0)
        # Stop loss is now trailed to peak * 0.75 (i.e. entry * 1.5)
        self.assertAlmostEqual(pos.stop_loss_price_usd, entry_price * 2.0 * 0.75, places=4)
        self.assertTrue(pos.is_open)

        # 2. Price drops to entry * 1.4 (< entry * 1.5) -> triggers TRAILING_STOP
        snap_pullback = TokenSnapshot(token_address="token_p1", price_usd=entry_price * 1.4, liquidity_usd=55000.0)
        closed_pos = portfolio.update_and_check_exits(snap_pullback)

        self.assertIsNotNone(closed_pos)
        self.assertEqual(closed_pos.exit_reason, ExitReason.TRAILING_STOP)
        self.assertEqual(len(portfolio.open_positions), 0)
        self.assertEqual(len(portfolio.closed_positions), 1)
        # Even after the 25% pullback from 2x peak, trade closed in net profit!
        self.assertGreater(closed_pos.net_pnl_usd, 0.0)

    def test_no_fixed_take_profit_and_exponential_gains_stay_open(self):
        """
        Guarantees that a position that grows +25%, +100%, +500% NEVER closes
        on a fixed take profit threshold, and stays open indefinitely until
        a -25% drawdown from the all-time peak occurs.
        """
        portfolio = PaperPortfolio(starting_capital_usd=100.0, position_size_usd=2.0, trailing_stop_pct=25.0)
        token = TokenInfo(address="token_moon", symbol="MOON", name="Moonshot Token")
        snap_entry = TokenSnapshot(token_address="token_moon", price_usd=1.0, liquidity_usd=100000.0)

        pos = portfolio.open_virtual_position(token, snap_entry)
        self.assertIsNotNone(pos)
        entry_price = pos.entry_price_usd

        # +25% gain -> MUST REMAIN OPEN (No fixed TP at +25%)
        closed_25 = portfolio.update_and_check_exits(
            TokenSnapshot(token_address="token_moon", price_usd=entry_price * 1.25, liquidity_usd=100000.0)
        )
        self.assertIsNone(closed_25)
        self.assertTrue(pos.is_open)
        self.assertEqual(pos.highest_price_usd, entry_price * 1.25)

        # +100% gain -> MUST REMAIN OPEN (No fixed TP at +100%)
        closed_100 = portfolio.update_and_check_exits(
            TokenSnapshot(token_address="token_moon", price_usd=entry_price * 2.00, liquidity_usd=120000.0)
        )
        self.assertIsNone(closed_100)
        self.assertTrue(pos.is_open)
        self.assertEqual(pos.highest_price_usd, entry_price * 2.00)

        # +500% gain -> MUST REMAIN OPEN (No fixed TP at +500%)
        closed_500 = portfolio.update_and_check_exits(
            TokenSnapshot(token_address="token_moon", price_usd=entry_price * 6.00, liquidity_usd=200000.0)
        )
        self.assertIsNone(closed_500)
        self.assertTrue(pos.is_open)
        self.assertEqual(pos.highest_price_usd, entry_price * 6.00)
        self.assertAlmostEqual(pos.stop_loss_price_usd, entry_price * 6.00 * 0.75, places=4)  # $4.50

        # -20% pullback from $6.00 peak -> $4.80 (> $4.50 stop) -> MUST REMAIN OPEN
        closed_pullback = portfolio.update_and_check_exits(
            TokenSnapshot(token_address="token_moon", price_usd=entry_price * 4.80, liquidity_usd=180000.0)
        )
        self.assertIsNone(closed_pullback)
        self.assertTrue(pos.is_open)

        # -25.8% pullback from $6.00 peak -> $4.45 (<= $4.50 stop) -> MUST CLOSE with TRAILING_STOP
        closed_final = portfolio.update_and_check_exits(
            TokenSnapshot(token_address="token_moon", price_usd=entry_price * 4.45, liquidity_usd=170000.0)
        )
        self.assertIsNotNone(closed_final)
        self.assertFalse(pos.is_open)
        self.assertEqual(closed_final.exit_reason, ExitReason.TRAILING_STOP)
        # Verify large net profit captured: > $6.50 profit on $2.00 position
        self.assertGreater(closed_final.net_pnl_usd, 6.50)


if __name__ == "__main__":
    unittest.main()
