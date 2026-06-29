"""Serve-plane data access — score table, model artifacts, metrics.

Source of truth for scores is Supabase when configured, else the local Parquet
written by the pipeline. Policy curves are cached per dataset so /simulate is
instant (NFR-2).
"""
from __future__ import annotations

import json
import pickle
from functools import lru_cache

import pandas as pd

from pipeline import config, decision, supabase_store


class DatasetNotReady(Exception):
    """Raised when a dataset has no scores yet (pipeline not run)."""


@lru_cache(maxsize=8)
def load_scores(dataset: str) -> pd.DataFrame:
    """Score table: prefer Supabase, fall back to local Parquet."""
    df = supabase_store.fetch_scores(dataset)
    if df is None:
        path = config.scores_path(dataset)
        if not path.exists():
            raise DatasetNotReady(
                f"No scores for '{dataset}'. Run: python -m pipeline.run --dataset {dataset}"
            )
        df = pd.read_parquet(path)
    # Normalise dtypes coming back from Supabase JSON.
    for col in ("uplift", "base_rate", "value"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("T", "Y"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("int64")
    return df.reset_index(drop=True)


@lru_cache(maxsize=8)
def load_policies(dataset: str) -> dict:
    return decision.build_policies(load_scores(dataset))


@lru_cache(maxsize=8)
def load_meta(dataset: str) -> dict:
    path = config.model_path(dataset, "meta").with_suffix(".json")
    if not path.exists():
        raise DatasetNotReady(f"No model metadata for '{dataset}'. Run the pipeline first.")
    return json.loads(path.read_text())


@lru_cache(maxsize=8)
def load_models(dataset: str):
    """Return (uplift_model, base_rate_model, feature_names)."""
    meta = load_meta(dataset)
    best = meta["best_learner"]
    with open(config.model_path(dataset, best), "rb") as f:
        uplift_model = pickle.load(f)
    with open(config.model_path(dataset, "base_rate"), "rb") as f:
        base_model = pickle.load(f)
    return uplift_model, base_model, meta["feature_names"]


@lru_cache(maxsize=8)
def load_metrics(dataset: str) -> dict:
    path = config.report_dir(dataset) / "metrics.json"
    if not path.exists():
        raise DatasetNotReady(f"No metrics for '{dataset}'. Run the pipeline first.")
    return json.loads(path.read_text())


def available_datasets() -> list[str]:
    found = set()
    for p in config.SCORES_DIR.glob("*.parquet"):
        found.add(p.stem)
    return sorted(found)


def clear_caches() -> None:
    for fn in (load_scores, load_policies, load_meta, load_models, load_metrics):
        fn.cache_clear()
