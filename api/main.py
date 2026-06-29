"""FR-C1–C3 — UpliftIQ serving API.

    GET  /api/health    liveness
    GET  /api/datasets  datasets that have been scored
    GET  /api/metrics   benchmark metrics per model × dataset (dashboard)
    POST /api/score     features -> {uplift, segment, base_rate}
    POST /api/simulate  {budget,cost,value,dataset} -> selection + profit + baselines + qini
    POST /api/batch     CSV upload -> ranked target list (CSV, UTF-8 BOM)
    POST /api/explain   LLM/templated segment explainer (Gemini, FR-C5)
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pipeline import config, decision, evaluate

from . import gemini, loaders

app = FastAPI(title="UpliftIQ API", version="1.0.0",
              description="Incremental targeting decision engine — scoring + simulation.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.APP_ORIGIN, "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── schemas ────────────────────────────────────────────────────────────────
class ScoreRequest(BaseModel):
    features: dict[str, float] = Field(..., description="feature_name -> value")
    dataset: str = config.DEFAULT_DATASET


class SimulateRequest(BaseModel):
    budget: int = Field(..., ge=0, description="number of customers to contact")
    cost: float = Field(0.10, ge=0, description="cost per contact")
    value: float = Field(10.0, ge=0, description="value per incremental conversion")
    dataset: str = config.DEFAULT_DATASET


class ExplainRequest(BaseModel):
    segment: str
    dataset: str = config.DEFAULT_DATASET


# ── helpers ────────────────────────────────────────────────────────────────
def _ready(dataset: str):
    try:
        return loaders.load_scores(dataset)
    except loaders.DatasetNotReady as e:
        raise HTTPException(status_code=409, detail=str(e))


def _base_threshold(scores: pd.DataFrame) -> float:
    return float(np.median(scores["base_rate"]))


# ── endpoints ──────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "datasets": loaders.available_datasets(),
        "supabase": config.supabase_enabled(),
        "gemini": config.gemini_enabled(),
    }


@app.get("/api/datasets")
def datasets():
    return {"datasets": loaders.available_datasets(), "default": config.DEFAULT_DATASET}


@app.get("/api/metrics")
def metrics(dataset: str = config.DEFAULT_DATASET):
    try:
        return loaders.load_metrics(dataset)
    except loaders.DatasetNotReady as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/score")
def score(req: ScoreRequest):
    scores = _ready(req.dataset)
    uplift_model, base_model, feature_names = loaders.load_models(req.dataset)
    row = {f: float(req.features.get(f, 0.0)) for f in feature_names}
    X = pd.DataFrame([row], columns=feature_names)
    uplift = float(uplift_model.predict_uplift(X)[0])
    base_rate = float(base_model.predict(X)[0])
    th = loaders.load_meta(req.dataset).get("segment_thresholds", {})
    segment = decision.assign_segments(
        np.array([uplift]), np.array([base_rate]),
        pos_thresh=th.get("pos_thresh"), neg_thresh=th.get("neg_thresh", 0.0),
        base_thresh=th.get("base_thresh", _base_threshold(scores)),
    )[0]
    return {"uplift": uplift, "base_rate": base_rate, "segment": segment}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    scores = _ready(req.dataset)
    policies = loaders.load_policies(req.dataset)
    result = decision.simulate(scores, req.budget, req.cost, req.value, policies)

    # Qini/uplift curve points + total segment mix (for charts).
    qini = evaluate.qini_points(scores["Y"], scores["uplift"], scores["T"])
    result["qini_points"] = qini["qini"]
    result["uplift_points"] = qini["uplift"]
    result["total_segments"] = decision.segment_counts(scores["segment"].to_numpy())
    result["profit_sweep"] = decision.profit_sweep(
        scores, req.cost, req.value, policies=policies
    )
    return result


@app.post("/api/batch")
async def batch(dataset: str = config.DEFAULT_DATASET, file: UploadFile = File(...)):
    """Score an uploaded customer CSV -> ranked target list (CSV, UTF-8 BOM)."""
    _ready(dataset)
    uplift_model, base_model, feature_names = loaders.load_models(dataset)
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    X = df.reindex(columns=feature_names, fill_value=0.0).astype(float)
    uplift = uplift_model.predict_uplift(X)
    base_rate = base_model.predict(X)
    th = loaders.load_meta(dataset).get("segment_thresholds", {})
    seg = decision.assign_segments(
        uplift, base_rate, pos_thresh=th.get("pos_thresh"),
        neg_thresh=th.get("neg_thresh", 0.0), base_thresh=th.get("base_thresh"),
    )

    out = df.copy()
    out["uplift"] = uplift
    out["base_rate"] = base_rate
    out["segment"] = seg
    out = out.sort_values("uplift", ascending=False).reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))

    buf = io.StringIO()
    out.to_csv(buf, index=False)
    data = "﻿" + buf.getvalue()  # UTF-8 BOM for Excel/Thai (NFR-6)
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="targets_{dataset}.csv"'},
    )


@app.get("/api/export")
def export(dataset: str = config.DEFAULT_DATASET, top: int | None = None):
    """One-click ranked target list of the scored dataset (CSV, UTF-8 BOM)."""
    scores = _ready(dataset)
    out = scores.sort_values("uplift", ascending=False).reset_index(drop=True)
    if top:
        out = out.head(int(top))
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    data = "﻿" + buf.getvalue()
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="targets_{dataset}.csv"'},
    )


@app.post("/api/explain")
def explain(req: ExplainRequest):
    scores = _ready(req.dataset)
    counts = decision.segment_counts(scores["segment"].to_numpy())
    if req.segment not in counts:
        raise HTTPException(status_code=400, detail=f"Unknown segment '{req.segment}'.")
    total = int(sum(counts.values()))
    try:
        metrics = loaders.load_metrics(req.dataset).get("learners", {})
    except loaders.DatasetNotReady:
        metrics = {}
    result = gemini.explain_segment(
        segment=req.segment, count=counts[req.segment], total=total, metrics=metrics
    )
    result.update({"segment": req.segment, "count": counts[req.segment], "total": total})
    return result
