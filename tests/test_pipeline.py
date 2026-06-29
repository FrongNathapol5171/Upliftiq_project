"""Pipeline correctness tests (spec §14)."""
import numpy as np

from pipeline import evaluate
from pipeline.balance import balance_summary
from pipeline.data import make_synthetic
from pipeline.models import LEARNERS, build_learner


def test_synthetic_is_randomized():
    b = make_synthetic(n=4000, seed=1)
    summ = balance_summary(b)
    # Randomized treatment -> good covariate balance.
    assert summ["max_abs_smd"] < 0.15
    assert 0.4 < summ["treatment_ratio"] < 0.6


def test_all_learners_fit_and_predict(synth):
    b = synth
    for name in LEARNERS:
        m = build_learner(name, seed=7).fit(b.X, b.treatment.to_numpy(), b.outcome.to_numpy())
        up = m.predict_uplift(b.X)
        assert up.shape == (b.n,)
        assert np.isfinite(up).all()


def test_seeded_run_is_reproducible(synth):
    """AC-5: identical seed -> identical uplift predictions."""
    b = synth
    a = build_learner("s_learner", seed=7).fit(b.X, b.treatment.to_numpy(), b.outcome.to_numpy()).predict_uplift(b.X)
    c = build_learner("s_learner", seed=7).fit(b.X, b.treatment.to_numpy(), b.outcome.to_numpy()).predict_uplift(b.X)
    assert np.allclose(a, c)


def test_uplift_metrics_positive_on_signal(scored):
    """A model with real signal should beat random (Qini > 0)."""
    m = evaluate.core_metrics(scored["y"], scored["uplift"], scored["t"])
    assert m["qini"] > 0
    assert m["auuc"] > 0


def test_top_decile_beats_bottom(scored):
    """AC-2: model ranks uplift -> top decile actual response > bottom."""
    ev = evaluate.evaluate_model(scored["y"], scored["uplift"], scored["t"])
    assert ev["metrics"]["ranks_correctly"]
    assert ev["metrics"]["top_decile_uplift"] > ev["metrics"]["bottom_decile_uplift"]


def test_evaluation_never_uses_accuracy():
    """FR-D1: the report must explain why accuracy/AUC are inappropriate."""
    assert "accuracy" in evaluate.WHY_NOT_ACCURACY.lower()
    assert "qini" in evaluate.WHY_NOT_ACCURACY.lower()
