"""FR-A2 — Experiment validation / covariate balance.

Randomization quality is checked via the standardized mean difference (SMD)
of every feature between treatment and control groups. For a clean randomized
experiment SMDs should be near zero; |SMD| > 0.1 is the conventional flag.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import DatasetBundle

SMD_FLAG = 0.10  # conventional imbalance threshold


def standardized_mean_diff(x: pd.Series, t: pd.Series) -> float:
    """SMD = (mean_treated - mean_control) / pooled_sd."""
    xt, xc = x[t == 1], x[t == 0]
    mt, mc = xt.mean(), xc.mean()
    vt, vc = xt.var(ddof=1), xc.var(ddof=1)
    pooled = np.sqrt((vt + vc) / 2.0)
    if pooled == 0 or np.isnan(pooled):
        return 0.0
    return float((mt - mc) / pooled)


def balance_report(b: DatasetBundle) -> pd.DataFrame:
    """Per-feature balance table sorted by absolute imbalance."""
    rows = []
    for col in b.feature_names:
        smd = standardized_mean_diff(b.X[col], b.treatment)
        rows.append(
            {
                "feature": col,
                "mean_treated": float(b.X[col][b.treatment == 1].mean()),
                "mean_control": float(b.X[col][b.treatment == 0].mean()),
                "smd": smd,
                "abs_smd": abs(smd),
                "flagged": abs(smd) > SMD_FLAG,
            }
        )
    df = pd.DataFrame(rows).sort_values("abs_smd", ascending=False).reset_index(drop=True)
    return df


def balance_summary(b: DatasetBundle) -> dict:
    df = balance_report(b)
    return {
        "n_features": int(len(df)),
        "n_flagged": int(df["flagged"].sum()),
        "max_abs_smd": float(df["abs_smd"].max()),
        "mean_abs_smd": float(df["abs_smd"].mean()),
        "treatment_ratio": float(b.treatment.mean()),
        "passed": bool(df["flagged"].sum() == 0),
    }
