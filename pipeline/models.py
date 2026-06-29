"""FR-A3/A4 — Uplift meta-learners behind one common interface.

Every learner implements:
    fit(X, T, Y) -> self
    predict_uplift(X) -> np.ndarray          (per-customer CATE estimate)

Plus a shared BaseRateModel (P(Y=1 | X)) used for the propensity baseline and
the Sure-Thing / Lost-Cause segment split.

Base learners are LightGBM (listed in the stack); all seeded for
reproducibility (FR-D3). Implementations follow the standard definitions:
S-/T-/X-learner (Künzel et al. 2019) and R-learner (Nie & Wager 2021).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor

from . import config

# Compact, fast, deterministic base learners. Quiet LightGBM logging.
_LGBM_KW = dict(
    n_estimators=200,
    num_leaves=31,
    learning_rate=0.05,
    min_child_samples=50,
    subsample=0.9,
    colsample_bytree=0.9,
    n_jobs=-1,
    verbosity=-1,
)


def _clf(seed: int) -> LGBMClassifier:
    return LGBMClassifier(random_state=seed, **_LGBM_KW)


def _reg(seed: int) -> LGBMRegressor:
    return LGBMRegressor(random_state=seed, **_LGBM_KW)


def _proba1(model, X) -> np.ndarray:
    """P(class==1) robust to single-class training folds."""
    p = model.predict_proba(X)
    classes = list(model.classes_)
    if 1 in classes:
        return p[:, classes.index(1)]
    # Degenerate fold saw only class 0.
    return np.zeros(len(X))


# ── Base rate (propensity-to-convert) ──────────────────────────────────────
class BaseRateModel:
    """P(Y=1 | X) ignoring treatment — drives the propensity baseline."""

    def __init__(self, seed: int = config.SEED):
        self.seed = seed
        self.model = _clf(seed)

    def fit(self, X, Y) -> "BaseRateModel":
        self.model.fit(X, np.asarray(Y))
        return self

    def predict(self, X) -> np.ndarray:
        return _proba1(self.model, X)


# ── Uplift learners ─────────────────────────────────────────────────────────
class UpliftLearner(ABC):
    name: str = "base"

    def __init__(self, seed: int = config.SEED):
        self.seed = seed

    @abstractmethod
    def fit(self, X, T, Y) -> "UpliftLearner": ...

    @abstractmethod
    def predict_uplift(self, X) -> np.ndarray: ...


class SLearner(UpliftLearner):
    """Single model with treatment as a feature; uplift = f(X,1) - f(X,0)."""

    name = "s_learner"

    def fit(self, X, T, Y):
        X = pd.DataFrame(X).reset_index(drop=True)
        self.feat_ = list(X.columns)
        Xt = X.copy()
        Xt["_treatment"] = np.asarray(T)
        self.model_ = _clf(self.seed).fit(Xt, np.asarray(Y))
        return self

    def predict_uplift(self, X):
        X = pd.DataFrame(X)[self.feat_].copy()
        X1, X0 = X.copy(), X.copy()
        X1["_treatment"] = 1
        X0["_treatment"] = 0
        return _proba1(self.model_, X1) - _proba1(self.model_, X0)


class TLearner(UpliftLearner):
    """Separate treated/control models; uplift = mu1(X) - mu0(X)."""

    name = "t_learner"

    def fit(self, X, T, Y):
        X = pd.DataFrame(X).reset_index(drop=True)
        T = np.asarray(T)
        Y = np.asarray(Y)
        self.m1_ = _clf(self.seed).fit(X[T == 1], Y[T == 1])
        self.m0_ = _clf(self.seed).fit(X[T == 0], Y[T == 0])
        return self

    def predict_uplift(self, X):
        X = pd.DataFrame(X)
        return _proba1(self.m1_, X) - _proba1(self.m0_, X)


class XLearner(UpliftLearner):
    """X-learner (Künzel 2019) — impute individual effects, model, then
    combine via propensity weighting. Robust to treatment imbalance."""

    name = "x_learner"

    def fit(self, X, T, Y):
        X = pd.DataFrame(X).reset_index(drop=True)
        T = np.asarray(T)
        Y = np.asarray(Y).astype(float)
        Xt, Xc = X[T == 1], X[T == 0]
        Yt, Yc = Y[T == 1], Y[T == 0]

        # Stage 1: outcome models.
        self.m1_ = _clf(self.seed).fit(Xt, Yt.astype(int))
        self.m0_ = _clf(self.seed).fit(Xc, Yc.astype(int))

        # Imputed treatment effects.
        d1 = Yt - _proba1(self.m0_, Xt)          # treated: Y - mu0(X)
        d0 = _proba1(self.m1_, Xc) - Yc          # control: mu1(X) - Y

        # Stage 2: effect models.
        self.tau1_ = _reg(self.seed).fit(Xt, d1)
        self.tau0_ = _reg(self.seed).fit(Xc, d0)

        # Propensity e(X).
        self.e_ = _clf(self.seed).fit(X, T)
        return self

    def predict_uplift(self, X):
        X = pd.DataFrame(X)
        e = np.clip(_proba1(self.e_, X), 1e-3, 1 - 1e-3)
        return e * self.tau0_.predict(X) + (1 - e) * self.tau1_.predict(X)


class RLearner(UpliftLearner):
    """R-learner (Nie & Wager 2021) — orthogonalise outcome & treatment with
    cross-fitting, then fit tau(X) on the residual pseudo-outcome. This is the
    advanced estimator (RO-2) implemented without heavyweight deps."""

    name = "r_learner"

    def __init__(self, seed: int = config.SEED, n_folds: int = 3):
        super().__init__(seed)
        self.n_folds = n_folds

    def fit(self, X, T, Y):
        from sklearn.model_selection import KFold

        X = pd.DataFrame(X).reset_index(drop=True)
        T = np.asarray(T).astype(float)
        Y = np.asarray(Y).astype(float)
        n = len(X)
        m_hat = np.zeros(n)   # E[Y|X]
        e_hat = np.zeros(n)   # E[T|X]

        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=self.seed)
        for tr, te in kf.split(X):
            m = _clf(self.seed).fit(X.iloc[tr], Y[tr].astype(int))
            e = _clf(self.seed).fit(X.iloc[tr], T[tr].astype(int))
            m_hat[te] = _proba1(m, X.iloc[te])
            e_hat[te] = _proba1(e, X.iloc[te])

        t_res = T - e_hat
        y_res = Y - m_hat
        eps = 1e-6
        pseudo = y_res / np.where(np.abs(t_res) < eps, eps, t_res)
        weights = t_res ** 2

        self.tau_ = _reg(self.seed).fit(X, pseudo, sample_weight=weights)
        return self

    def predict_uplift(self, X):
        return self.tau_.predict(pd.DataFrame(X))


LEARNERS: dict[str, type[UpliftLearner]] = {
    "s_learner": SLearner,
    "t_learner": TLearner,
    "x_learner": XLearner,
    "r_learner": RLearner,
}


def build_learner(name: str, seed: int = config.SEED) -> UpliftLearner:
    if name not in LEARNERS:
        raise ValueError(f"Unknown learner '{name}'. Options: {list(LEARNERS)}")
    return LEARNERS[name](seed=seed)
