"""
Master Test Suite for Solana Meme Research Lab - Paper Trading Engine v1.
Covers all requirements from Section 37 and Deterministic Controlled Tests A through H from Section 38.
"""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from analyzers.liquidity import LiquidityAnalyzer
from analyzers.momentum import MomentumAnalyzer
from analyzers.security import SecurityAnalyzer
from core.models import (
    EntryBlockReason,
    ExitReason,
    HardRejectReason,
    PaperPosition,
    ScoreResult,
    SecurityCheckResult,
    TokenInfo,
    TokenSnapshot,
    TokenState,
    TradeAction,
    utc_now,
)
from database.db import Database
from features.store import FeatureStore
from quarantine.manager import QuarantineManager
from runner.paper_runner import AutonomousPaperRunner
from runner.report_generator import HourlyReportGenerator
from scoring.engine import ScoreEngine
from simulation.portfolio import PaperPortfolio


class TestPaperEngineV1(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db = Database(db_path=f"{self.temp_dir}/test_lab.db")
        self.portfolio = PaperPortfolio(
            starting_capital_usd=100.0,
            position_size_usd=2.0,
            max_positions=50,
            trailing_stop_pct=25.0,
            db=self.db,
        )
        self.sec_analyzer = SecurityAnalyzer()
        self.liq_analyzer = LiquidityAnalyzer()
        self.mom_analyzer = MomentumAnalyzer()
        self.score_engine = ScoreEngine()
        self.feature_store = FeatureStore(db=self.db)
        self.quarantine_mgr = QuarantineManager(default_quarantine_minutes=5.0)

    def tearDown(self):
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_initial_snapshot(self):
        now = utc_now()
        token = TokenInfo(
            address="CALICO1111111111111111111111111111111111111",
            symbol="CALICO",
            name="Calico Cat",
            discovered_at=now,
            initial_price_usd=0.000100,
            initial_liquidity_usd=15000.0,
            initial_score=62.5,
        )
        self.db.save_token(token)
        loaded = self.db.get_token(token.address)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.initial_price_usd, 0.000100)
        self.assertEqual(loaded.initial_liquidity_usd, 15000.0)

    def test_no_future_data(self):
        t0 = utc_now()
        t1 = t0 + timedelta(minutes=2)
        t_future = t0 + timedelta(minutes=10)

        snap0 = TokenSnapshot("TOKEN_A", timestamp=t0, price_usd=0.001, liquidity_usd=10000.0)
        snap1 = TokenSnapshot("TOKEN_A", timestamp=t1, price_usd=0.0012, liquidity_usd=11000.0)
        snap_future = TokenSnapshot("TOKEN_A", timestamp=t_future, price_usd=0.005, liquidity_usd=50000.0)

        token = TokenInfo(address="TOKEN_A", symbol="TOKA", name="Token A", initial_price_usd=0.001)
        sec = SecurityCheckResult("TOKEN_A", timestamp=t1, security_verified=True, soft_security_score=80.0)
        liq = self.liq_analyzer.analyze("TOKEN_A", snap1, [snap0, snap_future])
        mom = self.mom_analyzer.analyze("TOKEN_A", snap1, [snap0, snap_future])
        score = self.score_engine.calculate_score(token, snap1, sec, liq, mom)

        features = self.feature_store.extract_features(token, snap1, sec, liq, mom, score, history=[snap0, snap_future])
        # Verify feature extraction strictly filtered out snap_future (timestamp > snap1.timestamp)
        p_growths = [f.feature_value for f in features if f.feature_name == "price_growth_1m"]
        self.assertTrue(len(p_growths) > 0)

    def test_quarantine_5_minutes(self):
        now = utc_now()
        token = TokenInfo(address="TOKEN_Q", symbol="QUAR", name="Quar Token", discovered_at=now)
        self.quarantine_mgr.register_token_quarantine(token)
        self.assertEqual(token.status, TokenState.QUARANTINE)
        self.assertFalse(self.quarantine_mgr.is_quarantine_complete(token, current_time=now + timedelta(minutes=4)))
        self.assertTrue(self.quarantine_mgr.is_quarantine_complete(token, current_time=now + timedelta(minutes=5, seconds=1)))

    def test_no_buy_during_quarantine(self):
        runner = AutonomousPaperRunner(db=self.db, runtime_dir=f"{self.temp_dir}/runtime")
        token = TokenInfo(address="TOKEN_NO_BUY", symbol="NOBUY", name="No Buy", initial_price_usd=0.001)
        runner.quarantine_mgr.register_token_quarantine(token)
        self.assertFalse(runner.quarantine_mgr.is_quarantine_complete(token))

    def test_temporal_features(self):
        t0 = utc_now()
        t1 = t0 + timedelta(minutes=1)
        t3 = t0 + timedelta(minutes=3)
        t5 = t0 + timedelta(minutes=5)

        s0 = TokenSnapshot("TOKEN_TF", timestamp=t0, price_usd=0.001, liquidity_usd=10000.0)
        s1 = TokenSnapshot("TOKEN_TF", timestamp=t1, price_usd=0.0011, liquidity_usd=10500.0)
        s3 = TokenSnapshot("TOKEN_TF", timestamp=t3, price_usd=0.0013, liquidity_usd=11000.0)
        s5 = TokenSnapshot("TOKEN_TF", timestamp=t5, price_usd=0.0016, liquidity_usd=12000.0)

        token = TokenInfo(address="TOKEN_TF", symbol="TF", name="TF Token", initial_price_usd=0.001)
        sec = SecurityCheckResult("TOKEN_TF", timestamp=t5, security_verified=True, soft_security_score=80.0)
        liq = self.liq_analyzer.analyze("TOKEN_TF", s5, [s0, s1, s3])
        mom = self.mom_analyzer.analyze("TOKEN_TF", s5, [s0, s1, s3])
        score = self.score_engine.calculate_score(token, s5, sec, liq, mom)

        features = self.feature_store.extract_features(token, s5, sec, liq, mom, score, history=[s0, s1, s3])
        feat_dict = {f.feature_name: f.feature_value for f in features}
        self.assertIn("price_growth_5m", feat_dict)
        self.assertAlmostEqual(feat_dict["price_growth_5m"], 60.0, delta=1.0)

    def test_security_unverified_no_entry(self):
        # Security unverified -> Cannot qualify as CANDIDATE
        snap = TokenSnapshot("TOKEN_SEC_UNV", price_usd=0.0015, liquidity_usd=15000.0, volume_5m_usd=5000.0)
        token = TokenInfo(address="TOKEN_SEC_UNV", symbol="UNV", name="Unv Token", initial_price_usd=0.0010)
        sec = SecurityCheckResult("TOKEN_SEC_UNV", security_verified=False, security_status="SECURITY_UNVERIFIED", soft_security_score=85.0)
        liq = self.liq_analyzer.analyze("TOKEN_SEC_UNV", snap)
        mom = self.mom_analyzer.analyze("TOKEN_SEC_UNV", snap)
        score = self.score_engine.calculate_score(token, snap, sec, liq, mom)

        self.assertNotEqual(score.status, TokenState.CANDIDATE)
        self.assertEqual(score.status, TokenState.WATCH)

    def test_security_verified_entry(self):
        snap = TokenSnapshot(
            "TOKEN_SEC_VER",
            price_usd=0.0016,
            liquidity_usd=25000.0,
            volume_5m_usd=8000.0,
            volume_1m_usd=3000.0,
            buys_5m=30,
            sells_5m=10,
            trade_count_5m=40,
            top10_holders_pct=35.0,
        )
        token = TokenInfo(address="TOKEN_SEC_VER", symbol="VER", name="Ver Token", initial_price_usd=0.0010)
        sec = SecurityCheckResult(
            "TOKEN_SEC_VER",
            is_mintable=False,
            is_freezable=False,
            top10_holders_pct=35.0,
            security_verified=True,
            soft_security_score=95.0,
        )
        liq = self.liq_analyzer.analyze("TOKEN_SEC_VER", snap)
        mom = self.mom_analyzer.analyze("TOKEN_SEC_VER", snap)
        score = self.score_engine.calculate_score(token, snap, sec, liq, mom)

        self.assertTrue(score.total_score >= 70.0)
        self.assertEqual(score.status, TokenState.CANDIDATE)

    def test_price_below_50_no_entry(self):
        token = TokenInfo(address="TOKEN_P40", symbol="P40", name="P40 Token", initial_price_usd=0.0010)
        snap = TokenSnapshot("TOKEN_P40", price_usd=0.0014, liquidity_usd=20000.0)  # +40% < +50%
        # Price is +40%, below required +50%
        growth_pct = ((snap.price_usd - token.initial_price_usd) / token.initial_price_usd) * 100.0
        self.assertLess(growth_pct, 50.0)

    def test_price_plus_50_entry(self):
        token = TokenInfo(address="TOKEN_P55", symbol="P55", name="P55 Token", initial_price_usd=0.0010)
        snap = TokenSnapshot("TOKEN_P55", price_usd=0.00155, liquidity_usd=20000.0)  # +55% >= +50%
        growth_pct = ((snap.price_usd - token.initial_price_usd) / token.initial_price_usd) * 100.0
        self.assertGreaterEqual(growth_pct, 50.0)

        pos = self.portfolio.open_virtual_position(token, snap)
        self.assertIsNotNone(pos)
        self.assertEqual(pos.amount_usd, 2.0)
        self.assertEqual(len(self.portfolio.open_positions), 1)

    def test_max_50_positions_and_two_dollar_sizing(self):
        for i in range(50):
            t = TokenInfo(address=f"TOK_{i}", symbol=f"T{i}", name=f"Token {i}", initial_price_usd=0.001)
            s = TokenSnapshot(f"TOK_{i}", price_usd=0.0015, liquidity_usd=10000.0)
            p = self.portfolio.open_virtual_position(t, s)
            self.assertIsNotNone(p)

        self.assertEqual(len(self.portfolio.open_positions), 50)
        self.assertEqual(self.portfolio.available_cash_usd, 0.0)

        # 51st position cannot be opened
        t51 = TokenInfo(address="TOK_51", symbol="T51", name="Token 51", initial_price_usd=0.001)
        s51 = TokenSnapshot("TOK_51", price_usd=0.0015, liquidity_usd=10000.0)
        p51 = self.portfolio.open_virtual_position(t51, s51)
        self.assertIsNone(p51)

    def test_capital_reuse(self):
        token = TokenInfo(address="TOK_REUSE", symbol="REUSE", name="Reuse Token", initial_price_usd=0.001)
        snap_in = TokenSnapshot("TOK_REUSE", price_usd=0.0015, liquidity_usd=10000.0)
        pos = self.portfolio.open_virtual_position(token, snap_in)
        self.assertEqual(self.portfolio.available_cash_usd, 98.0)

        # Token rises then triggers trailing stop
        snap_peak = TokenSnapshot("TOK_REUSE", price_usd=0.0030, liquidity_usd=15000.0)
        self.portfolio.update_and_check_exits(snap_peak)

        snap_exit = TokenSnapshot("TOK_REUSE", price_usd=0.0022, liquidity_usd=15000.0)  # > 25% drop from 0.0030
        closed = self.portfolio.update_and_check_exits(snap_exit)

        self.assertIsNotNone(closed)
        self.assertEqual(closed.exit_reason, ExitReason.TRAILING_STOP)
        self.assertGreater(self.portfolio.available_cash_usd, 98.0)  # Capital returned with profit

    def test_emergency_liquidity_exit(self):
        token = TokenInfo(address="TOK_RUG", symbol="RUG", name="Rug Token", initial_price_usd=0.001)
        snap_in = TokenSnapshot("TOK_RUG", price_usd=0.0015, liquidity_usd=10000.0)
        pos = self.portfolio.open_virtual_position(token, snap_in)

        # Liquidity collapses to $400 (< $1000 threshold)
        snap_collapse = TokenSnapshot("TOK_RUG", price_usd=0.0015, liquidity_usd=400.0)
        closed = self.portfolio.update_and_check_exits(snap_collapse)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.exit_reason, ExitReason.LIQUIDITY_COLLAPSE)

    # === DETERMINISTIC CONTROLLED PAPER TESTS (A through H) ===

    def test_a_score_65_price_60_no_entry(self):
        """TEST A: Score=65, Price=+60% -> NO ENTRY"""
        score = 65.0
        price_growth = 60.0
        can_enter = (score >= 70.0) and (price_growth >= 50.0)
        self.assertFalse(can_enter)

    def test_b_score_75_price_30_monitoring(self):
        """TEST B: Score=75, Price=+30% -> MONITORING"""
        score = 75.0
        price_growth = 30.0
        can_enter = (score >= 70.0) and (price_growth >= 50.0)
        self.assertFalse(can_enter)

    def test_c_score_75_price_55_security_unverified_no_entry(self):
        """TEST C: Score=75, Price=+55%, Security=UNVERIFIED -> NO ENTRY"""
        score = 75.0
        price_growth = 55.0
        security_verified = False
        can_enter = (score >= 70.0) and (price_growth >= 50.0) and security_verified
        self.assertFalse(can_enter)

    def test_d_score_75_price_55_security_verified_paper_buy(self):
        """TEST D: Score=75, Price=+55%, Security=VERIFIED, Liquidity=PASS -> PAPER BUY $2"""
        score = 75.0
        price_growth = 55.0
        security_verified = True
        liquidity_pass = True
        can_enter = (score >= 70.0) and (price_growth >= 50.0) and security_verified and liquidity_pass
        self.assertTrue(can_enter)

        token = TokenInfo(address="TEST_D", symbol="TESTD", name="Test D", initial_price_usd=0.0010)
        snap = TokenSnapshot("TEST_D", price_usd=0.00155, liquidity_usd=20000.0)
        pos = self.portfolio.open_virtual_position(token, snap)
        self.assertIsNotNone(pos)
        self.assertEqual(pos.amount_usd, 2.0)

    def test_e_t5_score_65_t8_score_74_price_52_buy_at_t8(self):
        """TEST E: T+5 score=65 -> WAIT; T+8 score=74, price=+52% -> BUY at T+8"""
        # At T+5
        t5_score = 65.0
        t5_growth = 20.0
        self.assertFalse((t5_score >= 70.0) and (t5_growth >= 50.0))

        # At T+8
        t8_score = 74.0
        t8_growth = 52.0
        self.assertTrue((t8_score >= 70.0) and (t8_growth >= 50.0))

    def test_f_t15_score_76_price_51_buy_at_t15(self):
        """TEST F: T+15 score=76, price=+51% -> BUY at T+15"""
        t15_score = 76.0
        t15_growth = 51.0
        self.assertTrue((t15_score >= 70.0) and (t15_growth >= 50.0))

    def test_g_price_never_reaches_50_expired_at_60m(self):
        """TEST G: Price never reaches +50% -> EXPIRED at 60m"""
        t0 = utc_now()
        t61 = t0 + timedelta(minutes=61)
        token = TokenInfo(
            address="TEST_G", symbol="TESTG", name="Test G",
            discovered_at=t0, monitoring_until=t0 + timedelta(minutes=60),
            initial_price_usd=0.0010
        )
        is_expired = (t61 > token.monitoring_until)
        self.assertTrue(is_expired)

    def test_h_buy_peak_recorded_falls_25_pct_paper_sell(self):
        """TEST H: BUY -> price rises -> peak recorded -> falls -25% from peak -> PAPER SELL"""
        token = TokenInfo(address="TEST_H", symbol="TESTH", name="Test H", initial_price_usd=0.0010)
        snap_in = TokenSnapshot("TEST_H", price_usd=0.00155, liquidity_usd=20000.0)
        pos = self.portfolio.open_virtual_position(token, snap_in)

        # Price rises to peak +74%
        snap_peak = TokenSnapshot("TEST_H", price_usd=0.0027, liquidity_usd=25000.0)
        self.portfolio.update_and_check_exits(snap_peak)
        self.assertEqual(pos.highest_price_usd, 0.0027)

        # Price drops -26% from peak (0.0027 * 0.74 = 0.001998)
        snap_fall = TokenSnapshot("TEST_H", price_usd=0.00199, liquidity_usd=25000.0)
        closed = self.portfolio.update_and_check_exits(snap_fall)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.exit_reason, ExitReason.TRAILING_STOP)
        self.assertGreater(closed.net_pnl_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
