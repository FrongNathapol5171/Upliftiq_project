"""Central configuration — reads .env, exposes typed settings + paths.

Everything is optional. With no .env present the defaults give a fully working
local run (Parquet score store, templated explainer). Keys upgrade behaviour.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = parent of this file's directory (pipeline/ -> repo root)
ROOT = Path(__file__).resolve().parents[1]

# Load .env from repo root if present (does not override real env vars).
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# ── Reproducibility ────────────────────────────────────────────────────────
SEED = int(_get("SEED", "42"))
DEFAULT_DATASET = _get("DEFAULT_DATASET", "hillstrom")

# ── Paths ──────────────────────────────────────────────────────────────────
DATA_HOME = Path(_get("DATA_HOME", str(ROOT / ".uplift_data"))).expanduser()
MODELS_DIR = ROOT / "models"
SCORES_DIR = ROOT / "scores"
REPORTS_DIR = ROOT / "reports"

for _d in (DATA_HOME, MODELS_DIR, SCORES_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Gemini (optional) ──────────────────────────────────────────────────────
GEMINI_API_KEY = _get("GEMINI_API_KEY")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-2.0-flash")

# ── Supabase (optional) ────────────────────────────────────────────────────
SUPABASE_URL = _get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = _get("SUPABASE_SERVICE_KEY")
SUPABASE_SCORES_TABLE = _get("SUPABASE_SCORES_TABLE", "uplift_scores")

# ── Serving ────────────────────────────────────────────────────────────────
APP_ORIGIN = _get("APP_ORIGIN", "http://localhost:3000")


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def gemini_enabled() -> bool:
    return bool(GEMINI_API_KEY)


def scores_path(dataset: str) -> Path:
    return SCORES_DIR / f"{dataset}.parquet"


def report_dir(dataset: str) -> Path:
    d = REPORTS_DIR / dataset
    d.mkdir(parents=True, exist_ok=True)
    return d


def model_path(dataset: str, learner: str) -> Path:
    d = MODELS_DIR / dataset
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{learner}.pkl"
