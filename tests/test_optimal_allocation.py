import json
import unittest

from Stage_CarbonTrading import calculate_optimal_allowance_allocation
from configs.config import config
from utils.shared_utils import calculate_player_production_benchmarks


class DummyPlayer:
    def __init__(self, market_price, marginal_cost, emission_per_unit, max_production):
        self.market_price = market_price
        self.marginal_cost_coefficient = marginal_cost
        self.carbon_emission_per_unit = emission_per_unit
        self.max_production = max_production
        self.disturbance_values = json.dumps([0.0] * max_production)


class OptimalAllowanceAllocationTests(unittest.TestCase):
    def test_cap_matches_tax_benchmark_emissions(self):
        market_price = 35
        carbon_multiplier = 1.0
        players = [
            DummyPlayer(market_price, marginal_cost=3, emission_per_unit=2, max_production=10),
            DummyPlayer(market_price, marginal_cost=5, emission_per_unit=3, max_production=10),
        ]

        allocation = calculate_optimal_allowance_allocation(
            players,
            market_price=market_price,
            carbon_multiplier=carbon_multiplier,
            allocation_method="equal",
        )

        social_cost = config.carbon_trading_social_cost_per_unit_carbon
        tax_rate = carbon_multiplier * social_cost

        expected_totals = 0
        for player, firm_details in zip(players, allocation["firm_details"]):
            benchmarks = calculate_player_production_benchmarks(
                player,
                social_cost_per_unit_carbon=social_cost,
                tax_rate=tax_rate,
            )
            self.assertEqual(firm_details["q_subopt"], benchmarks["q_tax"])
            self.assertEqual(firm_details["TE_subopt"], benchmarks["e_tax"])
            self.assertGreaterEqual(firm_details["q_subopt"], 0)
            self.assertLessEqual(firm_details["q_subopt"], player.max_production)
            self.assertGreaterEqual(firm_details["TE_subopt"], 0)
            self.assertLessEqual(
                firm_details["TE_subopt"],
                int(round(player.carbon_emission_per_unit * player.max_production)),
            )
            expected_totals += benchmarks["e_tax"]

        self.assertEqual(allocation["TE_tax_total"], expected_totals)
        self.assertEqual(allocation["cap_total"], allocation["TE_tax_total"])


if __name__ == "__main__":
    unittest.main()
