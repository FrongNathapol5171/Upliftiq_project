"""FR-B1–B4 — Decision layer.

Pure functions over the scored randomized holdout. Incremental conversions for
a targeting policy are estimated with the standard uplift-curve estimator
(scikit-uplift), which correctly reweights the randomized treated/control
groups — so the comparison of uplift vs propensity vs random targeting is
honest and policy-fair (FR-D2), not just "the model grading its own homework".

    expected_incremental_profit = inc_conversions * value - N * cost
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklift.metrics import uplift_curve

SEGMENTS = ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"]


# ── Segments (FR-B4) ────────────────────────────────────────────────────────
def segment_thresholds(
    uplift: np.ndarray, base_rate: np.ndarray, persuadable_q: float = 0.60
) -> dict:
    """Dataset-level thresholds for the four-segment view.

    Persuadable = clearly positive responders (uplift above the `persuadable_q`
    quantile, and strictly > 0); Sleeping Dog = negative predicted uplift; the
    near-zero middle splits Sure Thing / Lost Cause by base rate. Thresholds are
    computed once on the holdout and persisted so single-row scoring is
    consistent. (The decision layer ranks by *continuous* uplift — segments are
    a visualization heuristic, not the basis of targeting.)
    """
    uplift = np.asarray(uplift, dtype=float)
    base_rate = np.asarray(base_rate, dtype=float)
    pos = max(float(np.quantile(uplift, persuadable_q)), 1e-9)
    return {
        "pos_thresh": pos,
        "neg_thresh": 0.0,
        "base_thresh": float(np.median(base_rate)),
    }


def assign_segments(
    uplift: np.ndarray,
    base_rate: np.ndarray,
    pos_thresh: float | None = None,
    neg_thresh: float = 0.0,
    base_thresh: float | None = None,
) -> np.ndarray:
    """Label four uplift segments given thresholds (see `segment_thresholds`)."""
    uplift = np.asarray(uplift, dtype=float)
    base_rate = np.asarray(base_rate, dtype=float)
    if pos_thresh is None or base_thresh is None:
        th = segment_thresholds(uplift, base_rate)
        pos_thresh = th["pos_thresh"] if pos_thresh is None else pos_thresh
        base_thresh = th["base_thresh"] if base_thresh is None else base_thresh
    out = np.empty(len(uplift), dtype=object)
    persuadable = uplift >= pos_thresh
    sleeping = uplift < neg_thresh
    middle = ~(persuadable | sleeping)
    out[persuadable] = "Persuadable"
    out[sleeping] = "Sleeping Dog"
    out[middle & (base_rate >= base_thresh)] = "Sure Thing"
    out[middle & (base_rate < base_thresh)] = "Lost Cause"
    return out


def segment_counts(segments: np.ndarray) -> dict[str, int]:
    s = pd.Series(segments)
    return {seg: int((s == seg).sum()) for seg in SEGMENTS}


# ── Incremental-conversions estimator ──────────────────────────────────────
class PolicyCurve:
    """Cumulative incremental conversions vs number targeted, for one ranking.

    Precomputed once so the simulator can interpolate any budget instantly
    (NFR-2). x = number targeted (0..N), y = estimated incremental conversions.
    """

    def __init__(self, y_true, score, treatment):
        x, y = uplift_curve(np.asarray(y_true), np.asarray(score), np.asarray(treatment))
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.n = int(self.x[-1]) if len(self.x) else 0
        self.total = float(self.y[-1]) if len(self.y) else 0.0

    def incremental_at(self, budget: int) -> float:
        budget = max(0, min(int(budget), self.n))
        return float(np.interp(budget, self.x, self.y))


def random_incremental(total: float, budget: int, n: int) -> float:
    """Random targeting captures incremental gain proportional to budget."""
    if n == 0:
        return 0.0
    return total * (min(budget, n) / n)


# ── Simulation (FR-B1–B3) ──────────────────────────────────────────────────
def build_policies(scores: pd.DataFrame) -> dict:
    """Precompute uplift & propensity policy curves from a score table.

    `scores` must have columns: uplift, base_rate, T, Y.
    """
    y, t = scores["Y"].to_numpy(), scores["T"].to_numpy()
    uplift_pol = PolicyCurve(y, scores["uplift"].to_numpy(), t)
    prop_pol = PolicyCurve(y, scores["base_rate"].to_numpy(), t)
    return {"uplift": uplift_pol, "propensity": prop_pol, "n": uplift_pol.n}


def simulate(
    scores: pd.DataFrame,
    budget: int,
    cost_per_contact: float,
    value_per_conversion: float,
    policies: dict | None = None,
) -> dict:
    """Budget-constrained selection + incremental profit vs baselines."""
    policies = policies or build_policies(scores)
    up: PolicyCurve = policies["uplift"]
    pr: PolicyCurve = policies["propensity"]
    n = up.n
    budget = max(0, min(int(budget), n))

    def profit(inc: float) -> float:
        return inc * value_per_conversion - budget * cost_per_contact

    inc_uplift = up.incremental_at(budget)
    inc_prop = pr.incremental_at(budget)
    inc_random = random_incremental(up.total, budget, n)

    p_uplift, p_prop, p_random = profit(inc_uplift), profit(inc_prop), profit(inc_random)

    # Segment mix of the SELECTED (top-budget by uplift).
    order = np.argsort(-scores["uplift"].to_numpy())
    selected_idx = order[:budget]
    seg_selected = segment_counts(scores["segment"].to_numpy()[selected_idx])

    return {
        "budget": budget,
        "population": n,
        "cost_per_contact": cost_per_contact,
        "value_per_conversion": value_per_conversion,
        "uplift": {
            "incremental_conversions": inc_uplift,
            "incremental_profit": p_uplift,
        },
        "propensity": {
            "incremental_conversions": inc_prop,
            "incremental_profit": p_prop,
        },
        "random": {
            "incremental_conversions": inc_random,
            "incremental_profit": p_random,
        },
        # Headline number (AC-3): uplift profit lift over propensity targeting.
        "profit_lift_vs_propensity": p_uplift - p_prop,
        "profit_lift_vs_random": p_uplift - p_random,
        "selected_segments": seg_selected,
    }


def profit_sweep(
    scores: pd.DataFrame,
    cost_per_contact: float,
    value_per_conversion: float,
    n_points: int = 50,
    policies: dict | None = None,
) -> list[dict]:
    """Profit-vs-budget curve for uplift / propensity / random (the headline
    exhibit, AC-3). Returns points across the budget range."""
    policies = policies or build_policies(scores)
    n = policies["n"]
    budgets = np.unique(np.linspace(0, n, n_points).astype(int))
    out = []
    for b in budgets:
        s = simulate(scores, int(b), cost_per_contact, value_per_conversion, policies)
        out.append(
            {
                "budget": int(b),
                "uplift": s["uplift"]["incremental_profit"],
                "propensity": s["propensity"]["incremental_profit"],
                "random": s["random"]["incremental_profit"],
            }
        )
    return out
