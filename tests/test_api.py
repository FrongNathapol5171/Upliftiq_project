"""API tests (spec §14) — endpoints work and agree with the offline pipeline."""
import pytest
from fastapi.testclient import TestClient

from pipeline import decision
from pipeline.run import run


@pytest.fixture(scope="module")
def client():
    # Ensure the synthetic dataset is scored on disk, then build the app client.
    run(dataset="synthetic", seed=42)
    from api import loaders
    from api.main import app
    loaders.clear_caches()
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "synthetic" in r.json()["datasets"]


def test_metrics(client):
    r = client.get("/api/metrics?dataset=synthetic")
    assert r.status_code == 200
    assert "best_learner" in r.json()


def test_simulate_matches_offline(client):
    from api import loaders
    body = {"budget": 600, "cost": 0.1, "value": 10, "dataset": "synthetic"}
    r = client.post("/api/simulate", json=body)
    assert r.status_code == 200
    api_profit = r.json()["uplift"]["incremental_profit"]

    scores = loaders.load_scores("synthetic")
    offline = decision.simulate(scores, 600, 0.1, 10.0)
    assert abs(api_profit - offline["uplift"]["incremental_profit"]) < 1e-6


def test_score_returns_segment(client):
    from api import loaders
    feats = loaders.load_meta("synthetic")["feature_names"]
    payload = {"dataset": "synthetic", "features": {f: 0.5 for f in feats}}
    r = client.post("/api/score", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "uplift" in body and body["segment"] in decision.SEGMENTS


def test_export_has_bom(client):
    r = client.get("/api/export?dataset=synthetic&top=50")
    assert r.status_code == 200
    assert r.content[:3] == b"\xef\xbb\xbf"  # UTF-8 BOM (NFR-6 / AC-7)
    assert b"rank" in r.content.splitlines()[0]


def test_explain_fallback(client):
    r = client.post("/api/explain", json={"segment": "Persuadable", "dataset": "synthetic"})
    assert r.status_code == 200
    assert len(r.json()["text"]) > 10
