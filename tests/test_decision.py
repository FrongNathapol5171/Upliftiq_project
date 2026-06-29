"""Decision-layer tests (spec §14) — the headline guarantee."""
import numpy as np

from pipeline import decision


def test_uplift_beats_baselines_on_profit(scored):
    """AC-3: at a fixed budget, uplift targeting profit >= propensity & random."""
    scores = scored["scores"]
    policies = decision.build_policies(scores)
    budget = int(0.3 * policies["n"])
    s = decision.simulate(scores, budget, cost_per_contact=0.1,
                          value_per_conversion=10.0, policies=policies)
    assert s["uplift"]["incremental_profit"] >= s["propensity"]["incremental_profit"]
    assert s["uplift"]["incremental_profit"] >= s["random"]["incremental_profit"]
    assert s["profit_lift_vs_propensity"] >= 0


def test_budget_clamped_to_population(scored):
    scores = scored["scores"]
    s = decision.simulate(scores, budget=10**9, cost_per_contact=0.1, value_per_conversion=10.0)
    assert s["budget"] == s["population"]


def test_segments_cover_all_customers(scored):
    scores = scored["scores"]
    counts = decision.segment_counts(scores["segment"].to_numpy())
    assert sum(counts.values()) == len(scores)
    assert set(counts) == set(decision.SEGMENTS)


def test_selected_are_persuadable_first(scored):
    """Top-budget selection (ranked by uplift) is dominated by Persuadables."""
    scores = scored["scores"]
    policies = decision.build_policies(scores)
    budget = int(0.2 * policies["n"])
    s = decision.simulate(scores, budget, 0.1, 10.0, policies)
    assert s["selected_segments"]["Persuadable"] > 0


def test_profit_sweep_monotone_budget(scored):
    sweep = decision.profit_sweep(scored["scores"], 0.1, 10.0)
    budgets = [p["budget"] for p in sweep]
    assert budgets == sorted(budgets)
    assert len(sweep) > 5
