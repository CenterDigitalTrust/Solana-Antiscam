import unittest
from simulation.execution_simulator import ExecutionSimulator
from simulation.fee_model import FeeModel, FeeSource
from core.models import TokenSnapshot


class TestExecutionSimulator(unittest.TestCase):
    def test_2_dollar_position_economics(self):
        fee_model = FeeModel(
            base_network_fee_sol=0.000005,
            priority_fee_sol=0.00005,
            sol_price_usd=160.0,
        )
        sim = ExecutionSimulator(fee_model=fee_model, default_slippage_pct=1.0)

        # Pool with $20,000 liquidity
        snapshot = TokenSnapshot(token_address="test_token", price_usd=0.01, liquidity_usd=20000.0)

        result = sim.simulate_buy(
            token_address="test_token",
            market_price_usd=0.01,
            position_size_usd=2.0,
            snapshot=snapshot,
            venue="raydium",
        )

        self.assertEqual(result.requested_amount_usd, 2.0)
        self.assertGreater(result.effective_entry_price_usd, 0.01)
        self.assertEqual(result.fee_source, FeeSource.ASSUMED)
        self.assertGreater(result.total_friction_cost_usd, 0.0)

        # Ensure network + priority fee is accurately accounted for
        expected_fixed = (0.000005 + 0.00005) * 160.0  # ~$0.0088
        self.assertAlmostEqual(result.network_fee_usd + result.priority_fee_usd, expected_fixed, places=4)

    def test_low_liquidity_price_impact_escalation(self):
        sim = ExecutionSimulator()
        # Pool with only $1,000 liquidity
        shallow_snapshot = TokenSnapshot(token_address="shallow_token", price_usd=0.01, liquidity_usd=1000.0)
        deep_snapshot = TokenSnapshot(token_address="deep_token", price_usd=0.01, liquidity_usd=100000.0)

        res_shallow = sim.simulate_buy("shallow_token", 0.01, 2.0, snapshot=shallow_snapshot)
        res_deep = sim.simulate_buy("deep_token", 0.01, 2.0, snapshot=deep_snapshot)

        # Price impact on $1,000 pool must be significantly higher than $100,000 pool
        self.assertGreater(res_shallow.estimated_price_impact_pct, res_deep.estimated_price_impact_pct)


if __name__ == "__main__":
    unittest.main()
