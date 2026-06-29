"""FR-A1 — Data ingestion & normalisation.

Every dataset is normalised to one common frame so the rest of the pipeline is
dataset-agnostic:

    f_*            feature columns (numeric, model-ready)
    treatment      binary (1 = treated/contacted, 0 = control)
    outcome        binary primary label (e.g. visit / conversion)
    outcome_value  numeric value for profit (e.g. spend); 0 when unknown

Loaders cache the normalised frame to Parquet under DATA_HOME so re-runs are
fast and offline. A synthetic generator backs tests and offline demos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config


def _clean_columns(cols) -> list[str]:
    """Make column names safe for LightGBM (no special JSON chars)."""
    out, seen = [], {}
    for c in cols:
        s = re.sub(r"[^0-9a-zA-Z]+", "_", str(c)).strip("_").lower()
        s = s or "f"
        if s in seen:
            seen[s] += 1
            s = f"{s}_{seen[s]}"
        else:
            seen[s] = 0
        out.append(s)
    return out


@dataclass
class DatasetBundle:
    """Normalised dataset ready for the pipeline."""

    name: str
    X: pd.DataFrame                       # feature matrix (f_* columns)
    treatment: pd.Series                  # 0/1
    outcome: pd.Series                    # 0/1
    outcome_value: pd.Series              # numeric (spend etc.)
    feature_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.feature_names = list(self.X.columns)

    @property
    def n(self) -> int:
        return len(self.X)

    def frame(self) -> pd.DataFrame:
        df = self.X.copy()
        df["treatment"] = self.treatment.values
        df["outcome"] = self.outcome.values
        df["outcome_value"] = self.outcome_value.values
        return df


# ── Hillstrom ──────────────────────────────────────────────────────────────
_HILLSTROM_CATEGORICAL = ["history_segment", "zip_code", "channel"]


def _normalise_hillstrom(
    data: pd.DataFrame, visit: pd.Series, treatment_raw: pd.Series, spend: pd.Series
) -> DatasetBundle:
    """Map the 3-arm Hillstrom experiment to the common binary frame.

    treated = received any email (Men's or Women's), control = No E-Mail.
    Categorical features one-hot encoded deterministically.
    """
    X = data.copy()
    # One-hot the categoricals; keep numerics as-is.
    X = pd.get_dummies(X, columns=_HILLSTROM_CATEGORICAL, prefix=_HILLSTROM_CATEGORICAL)
    # Cast bool dummies to int and prefix every feature with f_.
    X = X.astype({c: "int64" for c in X.columns if X[c].dtype == bool})
    X.columns = [f"f_{c}" for c in _clean_columns(X.columns)]

    treatment = (treatment_raw != "No E-Mail").astype("int64")
    outcome = visit.astype("int64")
    outcome_value = spend.astype("float64")
    return DatasetBundle(
        name="hillstrom",
        X=X.reset_index(drop=True),
        treatment=treatment.reset_index(drop=True),
        outcome=outcome.reset_index(drop=True),
        outcome_value=outcome_value.reset_index(drop=True),
    )


def load_hillstrom(use_cache: bool = True) -> DatasetBundle:
    """Load + normalise Hillstrom via scikit-uplift, cached to Parquet."""
    cache = config.DATA_HOME / "hillstrom_normalised.parquet"
    if use_cache and cache.exists():
        return _from_cache("hillstrom", cache)

    from sklift.datasets import fetch_hillstrom

    # Outcome = visit (rich uplift signal); value = spend.
    visit_ds = fetch_hillstrom(data_home=str(config.DATA_HOME), target_col="visit")
    spend = fetch_hillstrom(data_home=str(config.DATA_HOME), target_col="spend").target
    bundle = _normalise_hillstrom(
        data=visit_ds.data,
        visit=visit_ds.target,
        treatment_raw=visit_ds.treatment,
        spend=spend,
    )
    _to_cache(bundle, cache)
    return bundle


# ── Criteo (scale dataset, NFR-3) ──────────────────────────────────────────
def load_criteo(use_cache: bool = True, subsample: int | None = 200_000) -> DatasetBundle:
    """Load + normalise Criteo Uplift v2.1 via scikit-uplift.

    `subsample` keeps development fast; pass None for the full ~14M-row run.
    Stratified by treatment to preserve the ~0.85 treatment ratio.
    """
    cache = config.DATA_HOME / f"criteo_normalised_{subsample or 'full'}.parquet"
    if use_cache and cache.exists():
        return _from_cache("criteo", cache)

    from sklift.datasets import fetch_criteo

    ds = fetch_criteo(data_home=str(config.DATA_HOME), target_col="visit", treatment_col="treatment")
    X = ds.data.copy()
    X.columns = [f"f_{c}" for c in X.columns]
    treatment = ds.treatment.astype("int64")
    outcome = ds.target.astype("int64")
    bundle = DatasetBundle(
        name="criteo",
        X=X.reset_index(drop=True),
        treatment=treatment.reset_index(drop=True),
        outcome=outcome.reset_index(drop=True),
        outcome_value=pd.Series(np.zeros(len(X)), name="outcome_value"),
    )
    if subsample and subsample < bundle.n:
        bundle = _stratified_subsample(bundle, subsample, seed=config.SEED)
    _to_cache(bundle, cache)
    return bundle


# ── Synthetic (offline tests / demos) ──────────────────────────────────────
def make_synthetic(n: int = 8000, seed: int = 42) -> DatasetBundle:
    """Randomized synthetic uplift data with a known persuadable structure.

    Builds features, a randomized treatment, and an outcome whose treatment
    effect varies with x0/x1 so uplift models have real signal to find.
    """
    rng = np.random.default_rng(seed)
    k = 6
    X = rng.normal(size=(n, k))
    cols = [f"f_x{i}" for i in range(k)]
    Xdf = pd.DataFrame(X, columns=cols)

    treatment = rng.integers(0, 2, size=n)  # randomized 50/50

    # Base conversion propensity (logit) — driven by x2, x3.
    base_logit = -0.5 + 0.8 * X[:, 2] - 0.6 * X[:, 3]
    # Heterogeneous treatment effect (uplift) — driven by x0, x1.
    tau = 0.35 * X[:, 0] - 0.25 * X[:, 1] + 0.15
    logit = base_logit + treatment * tau
    p = 1.0 / (1.0 + np.exp(-logit))
    outcome = (rng.random(n) < p).astype("int64")
    value = outcome * rng.uniform(40, 120, size=n)

    return DatasetBundle(
        name="synthetic",
        X=Xdf,
        treatment=pd.Series(treatment, name="treatment").astype("int64"),
        outcome=pd.Series(outcome, name="outcome"),
        outcome_value=pd.Series(value, name="outcome_value"),
    )


# ── helpers ────────────────────────────────────────────────────────────────
def _stratified_subsample(b: DatasetBundle, n: int, seed: int) -> DatasetBundle:
    rng = np.random.default_rng(seed)
    idx = (
        b.treatment.to_frame("t")
        .groupby("t", group_keys=False)
        .apply(lambda g: g.sample(n=int(round(n * len(g) / len(b.treatment))), random_state=seed))
        .index
    )
    idx = rng.permutation(idx.to_numpy())
    return DatasetBundle(
        name=b.name,
        X=b.X.iloc[idx].reset_index(drop=True),
        treatment=b.treatment.iloc[idx].reset_index(drop=True),
        outcome=b.outcome.iloc[idx].reset_index(drop=True),
        outcome_value=b.outcome_value.iloc[idx].reset_index(drop=True),
    )


def _to_cache(b: DatasetBundle, path) -> None:
    b.frame().to_parquet(path, index=False)


def _from_cache(name: str, path) -> DatasetBundle:
    df = pd.read_parquet(path)
    feats = [c for c in df.columns if c.startswith("f_")]
    return DatasetBundle(
        name=name,
        X=df[feats],
        treatment=df["treatment"],
        outcome=df["outcome"],
        outcome_value=df["outcome_value"],
    )


_LOADERS = {
    "hillstrom": load_hillstrom,
    "criteo": load_criteo,
    "synthetic": make_synthetic,
}


def load_dataset(name: str, **kwargs) -> DatasetBundle:
    name = name.lower()
    if name not in _LOADERS:
        raise ValueError(f"Unknown dataset '{name}'. Options: {list(_LOADERS)}")
    if name == "synthetic":
        return make_synthetic(seed=kwargs.get("seed", config.SEED))
    return _LOADERS[name](use_cache=kwargs.get("use_cache", True))
