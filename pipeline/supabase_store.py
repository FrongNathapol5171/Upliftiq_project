"""Optional Supabase score store.

When SUPABASE_URL + SUPABASE_SERVICE_KEY are set, the seeded pipeline upserts
the per-customer score table to Supabase (Postgres) so the API and any
dashboard can read a shared, queryable source of truth. When the keys are
absent every function is a no-op and the system falls back to local Parquet —
so the project runs end-to-end with zero cloud setup.

Apply supabase/schema.sql once in the Supabase SQL editor to create the table.
"""
from __future__ import annotations

import math

import pandas as pd

from . import config

# Score-table columns persisted to Supabase / Parquet.
SCORE_COLUMNS = ["id", "dataset", "uplift", "base_rate", "segment", "T", "Y", "value"]


def _client():
    """Create a Supabase client, or None if disabled / unavailable."""
    if not config.supabase_enabled():
        return None
    try:
        from supabase import create_client

        return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    except Exception as exc:  # pragma: no cover - network/dep guard
        print(f"[supabase] disabled (client error: {exc})")
        return None


def _records(df: pd.DataFrame, dataset: str) -> list[dict]:
    """Convert a score frame to JSON-safe upsert records."""
    out = df.copy()
    if "id" not in out.columns:
        out = out.reset_index().rename(columns={"index": "id"})
    out["dataset"] = dataset
    out = out[[c for c in SCORE_COLUMNS if c in out.columns]]
    records = out.to_dict(orient="records")
    # JSON cannot hold NaN/inf.
    for r in records:
        for k, v in r.items():
            if isinstance(v, float) and not math.isfinite(v):
                r[k] = None
    return records


def push_scores(df: pd.DataFrame, dataset: str, chunk_size: int = 1000) -> bool:
    """Upsert a score table to Supabase. Returns True if written, else False."""
    client = _client()
    if client is None:
        return False
    records = _records(df, dataset)
    table = config.SUPABASE_SCORES_TABLE
    try:
        # Clear prior rows for this dataset, then chunked insert.
        client.table(table).delete().eq("dataset", dataset).execute()
        for i in range(0, len(records), chunk_size):
            client.table(table).upsert(records[i : i + chunk_size]).execute()
        print(f"[supabase] wrote {len(records)} rows to {table} (dataset={dataset})")
        return True
    except Exception as exc:  # pragma: no cover - network guard
        print(f"[supabase] write failed, falling back to Parquet: {exc}")
        return False


def fetch_scores(dataset: str) -> pd.DataFrame | None:
    """Read a dataset's score table from Supabase, or None if unavailable."""
    client = _client()
    if client is None:
        return None
    table = config.SUPABASE_SCORES_TABLE
    try:
        rows: list[dict] = []
        page, size = 0, 1000
        while True:
            resp = (
                client.table(table)
                .select("*")
                .eq("dataset", dataset)
                .range(page * size, page * size + size - 1)
                .execute()
            )
            batch = resp.data or []
            rows.extend(batch)
            if len(batch) < size:
                break
            page += 1
        if not rows:
            return None
        return pd.DataFrame(rows)
    except Exception as exc:  # pragma: no cover - network guard
        print(f"[supabase] read failed, falling back to Parquet: {exc}")
        return None
