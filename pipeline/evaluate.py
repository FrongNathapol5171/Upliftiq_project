"""FR-A5 — Uplift-appropriate evaluation on a randomized holdout.

Uplift cannot be scored with accuracy/AUC: we never observe both potential
outcomes for one customer, so there is no per-row ground truth (FR-D1). We
evaluate ranking quality at the group level on a randomized holdout:

    • Qini curve + Qini coefficient
    • Uplift curve + AUUC (area under uplift curve)
    • Uplift-by-decile table (does the model rank uplift correctly?)
    • Calibration of predicted vs observed uplift by bin

Backed by scikit-uplift's reference metric implementations.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklift.metrics import (
    qini_auc_score,
    qini_curve,
    uplift_auc_score,
    uplift_by_percentile,
    uplift_curve,
)

WHY_NOT_ACCURACY = (
    "Accuracy/AUC measure outcome prediction, not treatment effect. Under the "
    "fundamental problem of causal inference only one potential outcome is "
    "observed per customer, so individual uplift has no ground-truth label. "
    "Uplift is therefore evaluated at the group level on a randomized holdout "
    "via Qini/AUUC, never accuracy/AUC (FR-D1)."
)


def core_metrics(y_true, uplift, treatment) -> dict:
    """Qini coefficient + AUUC for one model on the holdout."""
    y_true = np.asarray(y_true)
    uplift = np.asarray(uplift)
    treatment = np.asarray(treatment)
    return {
        "qini": float(qini_auc_score(y_true, uplift, treatment)),
        "auuc": float(uplift_auc_score(y_true, uplift, treatment)),
    }


def decile_table(y_true, uplift, treatment, bins: int = 10) -> pd.DataFrame:
    """Uplift-by-decile: rank by predicted uplift, show ACTUAL incremental
    response per bin. Top deciles should beat bottom deciles (AC-2)."""
    df = uplift_by_percentile(
        np.asarray(y_true), np.asarray(uplift), np.asarray(treatment),
        strategy="overall", bins=bins, std=False,
    )
    return df.reset_index().rename(columns={"index": "percentile"})


def calibration_table(y_true, uplift, treatment, bins: int = 10) -> pd.DataFrame:
    """Predicted vs observed uplift per bin of predicted uplift."""
    y_true = np.asarray(y_true, dtype=float)
    uplift = np.asarray(uplift, dtype=float)
    treatment = np.asarray(treatment)
    order = np.argsort(-uplift)
    groups = np.array_split(order, bins)
    rows = []
    for i, g in enumerate(groups):
        yt, tt, ut = y_true[g], treatment[g], uplift[g]
        treated, control = yt[tt == 1], yt[tt == 0]
        obs = (treated.mean() if len(treated) else np.nan) - (
            control.mean() if len(control) else np.nan
        )
        rows.append(
            {
                "bin": i + 1,
                "n": int(len(g)),
                "predicted_uplift": float(np.mean(ut)),
                "observed_uplift": float(obs) if not np.isnan(obs) else None,
            }
        )
    return pd.DataFrame(rows)


def qini_points(y_true, uplift, treatment, max_points: int = 200) -> dict:
    """Downsampled Qini & uplift curve points for charts / API (NFR-2)."""
    y_true = np.asarray(y_true)
    uplift = np.asarray(uplift)
    treatment = np.asarray(treatment)
    qx, qy = qini_curve(y_true, uplift, treatment)
    ux, uy = uplift_curve(y_true, uplift, treatment)

    def _ds(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        if len(x) <= max_points:
            idx = np.arange(len(x))
        else:
            idx = np.linspace(0, len(x) - 1, max_points).astype(int)
        # Normalise x to a 0..1 fraction of population for chart readability.
        xmax = x[-1] if x[-1] else 1.0
        return [{"x": float(x[i] / xmax), "y": float(y[i])} for i in idx]

    return {"qini": _ds(qx, qy), "uplift": _ds(ux, uy)}


def evaluate_model(y_true, uplift, treatment) -> dict:
    """Full evaluation bundle for one model on the holdout."""
    metrics = core_metrics(y_true, uplift, treatment)
    deciles = decile_table(y_true, uplift, treatment)
    calib = calibration_table(y_true, uplift, treatment)
    # AC-2 ranking sanity: top decile actual uplift vs bottom decile.
    resp = deciles["uplift"].to_numpy(dtype=float)
    metrics["top_decile_uplift"] = float(resp[0])
    metrics["bottom_decile_uplift"] = float(resp[-1])
    metrics["ranks_correctly"] = bool(resp[0] > resp[-1])
    return {
        "metrics": metrics,
        "deciles": deciles,
        "calibration": calib,
    }
