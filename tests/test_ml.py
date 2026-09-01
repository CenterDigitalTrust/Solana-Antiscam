import unittest
from datetime import datetime, timedelta
import numpy as np

from ml.dataset_loader import PoolRecord
from ml.feature_extractor import TimeAwareFeatureExtractor, assert_no_lookahead, LookAheadViolationError
from ml.split import TemporalSplitter
from ml.models import RugClassifierPipeline


class TestMLPipeline(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime(2023, 6, 1, 12, 0, 0)
        self.sample_record = PoolRecord(
            pool_address="pool_test_123",
            mint="mint_test_456",
            total_added_liquidity=50000.0,
            total_removed_liquidity=15000.0,
            num_liquidity_adds=5,
            num_liquidity_removes=2,
            add_to_remove_ratio=3.33,
            first_activity_timestamp=self.t0,
            last_pool_activity_timestamp=self.t0 + timedelta(minutes=60),
            last_swap_timestamp=self.t0 + timedelta(minutes=4),
            is_rug=True,
            source_file="2023.csv",
        )

    def test_no_lookahead_assertion(self):
        cutoff = self.t0 + timedelta(minutes=5)
        valid_event = self.t0 + timedelta(minutes=3)
        invalid_event = self.t0 + timedelta(minutes=7)

        # Valid event must not raise error
        assert_no_lookahead(valid_event, cutoff)

        # Event after cutoff must raise LookAheadViolationError
        with self.assertRaises(LookAheadViolationError):
            assert_no_lookahead(invalid_event, cutoff)

    def test_feature_extraction_per_horizon(self):
        extractor = TimeAwareFeatureExtractor()

        # 1m Horizon
        f_1m = extractor.extract_for_horizon(self.sample_record, horizon_minutes=1)
        self.assertEqual(f_1m.horizon_minutes, 1)
        self.assertEqual(f_1m.is_rug, 1)
        self.assertLess(f_1m.liquidity_added_T, self.sample_record.total_added_liquidity)
        self.assertEqual(f_1m.cutoff_timestamp, self.t0 + timedelta(minutes=1))

        # 5m Horizon
        f_5m = extractor.extract_for_horizon(self.sample_record, horizon_minutes=5)
        self.assertEqual(f_5m.horizon_minutes, 5)
        self.assertGreater(f_5m.liquidity_added_T, f_1m.liquidity_added_T)

    def test_withdrawal_ratio_zero_added_protection(self):
        extractor = TimeAwareFeatureExtractor()
        zero_add_rec = PoolRecord(
            pool_address="pool_zero",
            mint="mint_zero",
            total_added_liquidity=0.0,
            total_removed_liquidity=0.0,
            num_liquidity_adds=0,
            num_liquidity_removes=0,
            add_to_remove_ratio=None,
            first_activity_timestamp=self.t0,
            last_pool_activity_timestamp=self.t0,
            last_swap_timestamp=None,
            is_rug=False,
            source_file="2023.csv",
        )
        feat = extractor.extract_for_horizon(zero_add_rec, horizon_minutes=5)
        # Must be None / NULL, NOT 0.0
        self.assertIsNone(feat.withdrawal_ratio_T)

    def test_temporal_split(self):
        splitter = TemporalSplitter()
        rec_train = PoolRecord("p1", "m1", 100, 0, 1, 0, None, datetime(2022, 5, 1), None, None, False, "2022.csv")
        rec_val = PoolRecord("p2", "m2", 100, 0, 1, 0, None, datetime(2024, 3, 1), None, None, True, "2024.csv")
        rec_test = PoolRecord("p3", "m3", 100, 0, 1, 0, None, datetime(2024, 9, 1), None, None, True, "2024.csv")

        self.assertEqual(splitter.get_split_name(rec_train), "train")
        self.assertEqual(splitter.get_split_name(rec_val), "validation")
        self.assertEqual(splitter.get_split_name(rec_test), "test")

    def test_model_training_and_evaluation(self):
        X_train = np.array([
            [10000.0, 10000.0, 1000.0, 9000.0, 0.1, 10.0, 5.0, 0.0, 10, 100.0],
            [50000.0, 50000.0, 5000.0, 45000.0, 0.1, 50.0, 8.0, 0.0, 20, 100.0],
            [30000.0, 30000.0, 3000.0, 27000.0, 0.1, 30.0, 7.0, 0.0, 15, 100.0],
            [40000.0, 40000.0, 4000.0, 36000.0, 0.1, 40.0, 9.0, 0.0, 18, 100.0],
            [1000.0, 1000.0, 950.0, 50.0, 0.95, -100.0, 0.5, 1.0, 2, 80.0],
            [2000.0, 2000.0, 1900.0, 100.0, 0.95, -200.0, 0.5, 1.0, 3, 80.0],
            [1200.0, 1200.0, 1100.0, 100.0, 0.92, -120.0, 0.5, 1.0, 2, 80.0],
            [1500.0, 1500.0, 1400.0, 100.0, 0.93, -150.0, 0.5, 1.0, 2, 80.0],
        ])
        y_train = np.array([0, 0, 0, 0, 1, 1, 1, 1])

        X_test = np.array([
            [20000.0, 20000.0, 2000.0, 18000.0, 0.1, 20.0, 6.0, 0.0, 15, 100.0],
            [1500.0, 1500.0, 1400.0, 100.0, 0.93, -150.0, 0.5, 1.0, 2, 80.0],
        ])
        y_test = np.array([0, 1])

        pipe = RugClassifierPipeline(model_type="calibrated_logistic")
        pipe.fit(X_train, y_train)
        eval_res = pipe.evaluate(X_test, y_test)

        self.assertGreaterEqual(eval_res.roc_auc, 0.5)
        self.assertGreaterEqual(eval_res.pr_auc, 0.0)


if __name__ == "__main__":
    unittest.main()
