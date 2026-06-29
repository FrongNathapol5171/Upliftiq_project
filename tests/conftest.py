"""Shared fixtures — a fast seeded synthetic dataset + trained models."""
import numpy as np
import pytest
from sklearn.model_selection import train_test_split

from pipeline import decision, evaluate
from pipeline.data import make_synthetic
from pipeline.models import BaseRateModel, build_learner


@pytest.fixture(scope="session")
def synth():
    return make_synthetic(n=6000, seed=7)


@pytest.fixture(scope="session")
def scored(synth):
    """Train the best learner on a split and produce a holdout score table."""
    b = synth
    idx = np.arange(b.n)
    tr, ho = train_test_split(idx, test_size=0.3, random_state=7,
                              stratify=b.treatment.to_numpy())
    Xtr, Xho = b.X.iloc[tr], b.X.iloc[ho]
    Ttr, Tho = b.treatment.iloc[tr].to_numpy(), b.treatment.iloc[ho].to_numpy()
    Ytr, Yho = b.outcome.iloc[tr].to_numpy(), b.outcome.iloc[ho].to_numpy()

    model = build_learner("s_learner", seed=7).fit(Xtr, Ttr, Ytr)
    uplift = model.predict_uplift(Xho)
    base = BaseRateModel(seed=7).fit(Xtr, Ytr).predict(Xho)
    th = decision.segment_thresholds(uplift, base)
    seg = decision.assign_segments(uplift, base, **th)

    import pandas as pd
    df = pd.DataFrame({
        "id": np.arange(len(ho)), "uplift": uplift, "base_rate": base,
        "segment": seg, "T": Tho, "Y": Yho,
        "value": b.outcome_value.iloc[ho].to_numpy(),
    })
    return {"scores": df, "y": Yho, "t": Tho, "uplift": uplift}
