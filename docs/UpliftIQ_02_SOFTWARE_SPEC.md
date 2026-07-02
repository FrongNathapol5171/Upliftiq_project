# 02 — Software Specification

**Project:** UpliftIQ — Incremental Targeting Decision Engine
**Document Type:** Software / Technical Specification (Architecture & Design)
**Version:** 1.0
**Status:** Final — Ready for Implementation
**Companion:** `UpliftIQ_01_REQUIREMENT_SPEC.md`
**Audience:** AI Coding Agent
**Author:** Nathapol Powpadetkarn (Frong)

---

## 0. How to Use This Document (note to the coding agent)

Build in the **MVP order given in §13**. The **modeling + evaluation pipeline (§5–§6) is the thesis core** — get the benchmark and the Qini/AUUC reporting correct and reproducible *before* polishing the API, simulator, or dashboard. Never surface accuracy/AUC as a primary metric anywhere in the stack (requirement `FR-D1`). Every requirement ID referenced below maps back to `UpliftIQ_01_REQUIREMENT_SPEC.md`.

---

## 1. Architecture Overview

Three planes, cleanly separated so the statistical core can be validated independently of the UI:

```
┌─────────────────────────┐      ┌──────────────────────────┐      ┌───────────────────────┐
│   TRAIN PLANE (offline)  │      │   SERVE PLANE (API)       │      │  EXPERIENCE PLANE      │
│                          │      │                            │      │                       │
│  sklift dataset loaders  │─────▶│  FastAPI: /benchmark       │◀────▶│  Next.js + MUI PWA    │
│  → preprocessing         │      │           /score            │      │  - Benchmark view     │
│  → meta-learner fitting  │      │           /decision         │      │  - Qini charts        │
│  → Qini/AUUC evaluation  │      │           /export           │      │  - Budget simulator   │
│  → persisted model       │      │                            │      │  - Target list grid   │
│    artifacts (joblib)    │      │  (Python, same process     │      │  (calls the API only) │
│                          │      │   or container as train)   │      │                       │
└─────────────────────────┘      └──────────────────────────┘      └───────────────────────┘
```

**Why two services, not one:** the uplift models are Python-native artifacts (scikit-learn/causalml/econml objects). Next.js cannot load or run them directly. FastAPI is the *only* place model training/scoring happens; the frontend only ever talks to it over HTTP.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Modeling language | Python 3.11+ | |
| Uplift library | `scikit-uplift` (`sklift`) | dataset loaders + Qini/AUUC metrics |
| Meta-learner library | `causalml` or `econml` | pick one; `causalml` has simpler S/T/X-learner APIs |
| Backend framework | FastAPI | async, auto-generates OpenAPI schema |
| Model persistence | `joblib` | |
| Frontend framework | Next.js 14+ (App Router), TypeScript | |
| UI library | MUI v6+ (`@mui/material`, `@mui/x-charts`, `@mui/x-data-grid`) | **Tailwind excluded** — do not add it |
| Containerization | Docker + Docker Compose | 2 services: `model-service`, `web` |
| Package managers | `pip` (backend), `npm` (frontend) | |

---

## 3. Repository Structure

```
upliftiq/
├── docker-compose.yml
├── model-service/
│   ├── app/
│   │   ├── main.py                # FastAPI app entrypoint
│   │   ├── routers/
│   │   │   ├── benchmark.py       # POST /benchmark
│   │   │   ├── score.py           # POST /score
│   │   │   ├── decision.py        # POST /decision
│   │   │   └── export.py          # GET /export/{run_id}
│   │   ├── core/
│   │   │   ├── datasets.py        # sklift loader wrappers + fallback cache
│   │   │   ├── learners.py        # S/T/X-learner + causal forest fitting
│   │   │   ├── evaluation.py      # Qini, AUUC, segment breakdown
│   │   │   └── decision_engine.py # budget-constrained ranking
│   │   └── models/                # persisted joblib artifacts (gitignored)
│   ├── data_fallback/             # cached small dataset snapshot (FR-A1 fallback)
│   ├── requirements.txt
│   └── Dockerfile
├── web/
│   ├── app/
│   │   ├── page.tsx                       # dataset selection / home
│   │   ├── benchmark/page.tsx             # model comparison + Qini charts
│   │   ├── simulator/page.tsx             # budget slider + target list
│   │   └── layout.tsx
│   ├── components/
│   │   ├── QiniChart.tsx
│   │   ├── SegmentBreakdown.tsx
│   │   ├── BudgetSlider.tsx
│   │   └── TargetListGrid.tsx
│   ├── theme/
│   │   └── theme.ts                       # MUI theme (see §10)
│   ├── package.json
│   └── Dockerfile
└── UpliftIQ_00/01/02_*.md          # this spec package
```

---

## 4. Data Pipeline & Benchmark Design (Train Plane)

### 4.1 Loading
Wrap each `sklift.datasets.fetch_*` call in `core/datasets.py`:

```python
from sklift.datasets import fetch_hillstrom, fetch_criteo, fetch_lenta, fetch_x5

LOADERS = {
    "hillstrom": lambda: fetch_hillstrom(target_col="visit", return_X_y_t=True),
    "criteo":    lambda: fetch_criteo(target_col="conversion", treatment_col="treatment",
                                       percent10=True, return_X_y_t=True),
    "lenta":     lambda: fetch_lenta(return_X_y_t=True),
    "x5":        lambda: fetch_x5(),  # multi-table; needs custom feature assembly
}
```

### 4.2 Offline fallback (NFR-5, Risk mitigation in `01_REQUIREMENT_SPEC.md` §11)
On first successful fetch, cache the raw dataframe to `data_fallback/<name>.parquet`. On subsequent app startup, check the cache before calling the network loader — this satisfies "single `docker compose up`, no manual steps" even if the sandbox has no internet after the initial build.

### 4.3 Splitting
Stratified train/holdout split (default 70/30) preserving the treatment/control ratio, `random_state` fixed and logged (`FR-A2`, `NFR-1`).

### 4.4 Diagnostics
Before modeling, compute and return: n_train, n_holdout, treatment/control ratio, base conversion rate per arm (`FR-A3`).

---

## 5. Modeling Module (`core/learners.py`)

Fit, at minimum, these four estimators per dataset (`FR-B1`):

| Learner | Approach |
|---|---|
| **S-learner** | Single model with treatment as a feature; uplift = f(x,1) − f(x,0) |
| **T-learner** | Two separate models (treated-only, control-only); uplift = model difference |
| **X-learner** | T-learner + cross-imputed pseudo-effects, propensity-weighted |
| **Causal Forest** | Tree-ensemble estimator of heterogeneous treatment effects |

Log hyperparameters and the random seed for every fit to a `run_manifest.json` alongside the persisted model (`FR-B2`). Persist each fitted model via `joblib.dump` so `/score` can load without retraining (`FR-B3`).

---

## 6. Evaluation Module (`core/evaluation.py`)

- Compute **Qini curve** and **Qini coefficient** and **AUUC** using `sklift.metrics` (`qini_auc_score`, `uplift_at_k`, etc.) — do not hand-roll these; use the library's validated implementations so results are directly comparable to published uplift-modeling literature (`FR-D2`, `AC-6`).
- Compute the **four-segment breakdown** (Persuadable / Sure Thing / Lost Cause / Sleeping Dog) at a configurable decile threshold, using estimated uplift score combined with observed outcome on the holdout set (`FR-D3`).
- Rank all fitted meta-learners by AUUC; expose the winner explicitly in the API response (`FR-D4`).
- **Guardrail:** the evaluation response schema must not include an `accuracy` or `auc` field as a top-level/primary result. If included at all, it must be nested under a clearly labeled `secondary_diagnostics` object (`FR-D1`, `AC-5`).

---

## 7. Decision Layer (`core/decision_engine.py`)

Given `budget`, `cost_per_contact`, and the winning model's uplift scores on the holdout set:

1. Rank customers descending by predicted uplift.
2. Greedily select customers until the budget is exhausted (`floor(budget / cost_per_contact)` customers) — this is a hard cap, never exceeded (`FR-C1`, `AC-3`).
3. Compute expected incremental profit for this uplift-ranked selection.
4. Repeat the same budget-constrained selection using a naive propensity/response ranking (plain classifier, no causal adjustment) as the baseline comparator.
5. Return both target lists plus the profit gap between them — this *is* the thesis headline number (`FR-C2`, `AC-4`).

---

## 8. Backend API (FastAPI)

| Endpoint | Method | Purpose |
|---|---|---|
| `/datasets` | GET | List available datasets + cached status |
| `/benchmark` | POST | `{dataset, seed?}` → fits all meta-learners, returns Qini/AUUC table + winner |
| `/score` | POST | `{dataset, model}` → per-record uplift scores on holdout |
| `/decision` | POST | `{dataset, model, budget, cost_per_contact}` → target list + profit-gap result |
| `/export/{run_id}` | GET | Returns UTF-8-BOM CSV of the target list (`FR-C3`) or a summary PDF/report bundle (`FR-F1`) |

All responses validated against Pydantic schemas; OpenAPI docs auto-served at `/docs`.

---

## 9. Frontend App (Next.js + MUI)

Three screens map directly to the FR-E requirements:

1. **Home / dataset select** (`app/page.tsx`) — dataset cards with diagnostics from `/datasets`.
2. **Benchmark view** (`app/benchmark/page.tsx`) — Qini curves per model (MUI X Charts `LineChart`), AUUC comparison table, segment breakdown (MUI X Charts `BarChart`), winning model highlighted.
3. **Simulator** (`app/simulator/page.tsx`) — budget slider (`FR-E2`) driving a live re-call to `/decision`; target list rendered in MUI X `DataGrid` (`FR-E3`) with a CSV export button wired to `/export/{run_id}`.

---

## 10. Design System

### 10.1 Brand & Accessibility
- Primary: `#e86020` — large surfaces, icons, accents, chart highlight color only.
- Primary-text-safe: `#9c3614` — required for any small body text on a white/light background (raw `#e86020` fails WCAG AA at ~3.2:1 contrast for small text) (`NFR-3`, `AC-10`).
- Typography: declared stack `"Roboto", "Inter", "Noto Sans Thai", sans-serif` — Google Sans is proprietary/undistributable, do not attempt to load it.

### 10.2 MUI Theme (`theme/theme.ts`)

```ts
import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'class' },
  colorSchemes: {
    light: { palette: { primary: { main: '#e86020' }, text: { primary: '#1a1a1a' } } },
    dark:  { palette: { primary: { main: '#e86020' }, background: { default: '#121212' } } },
  },
  typography: {
    fontFamily: '"Roboto", "Inter", "Noto Sans Thai", sans-serif',
  },
  shape: { borderRadius: 16 },
  components: {
    MuiButton: { styleOverrides: { root: { borderRadius: 999 } } },       // pill buttons
    MuiCard:   { styleOverrides: { root: { borderRadius: 20 } } },        // rounded cards
    MuiSlider: { styleOverrides: { thumb: { width: 24, height: 24 } } }, // large slider thumb
  },
});
```

### 10.3 Component Mapping

| UI need | MUI component |
|---|---|
| Qini curve, uplift-by-decile bars | `@mui/x-charts` `LineChart`, `BarChart` |
| Target list table | `@mui/x-data-grid` `DataGrid` |
| Budget input | `@mui/material` `Slider` (custom thumb per §10.2) |
| Dataset/model cards | `@mui/material` `Card` |

Do **not** introduce Tailwind — it was explicitly excluded to avoid two competing styling systems.

---

## 11. Deployment

`docker-compose.yml` — two services:

```yaml
services:
  model-service:
    build: ./model-service
    ports: ["8000:8000"]
    volumes: ["./model-service/data_fallback:/app/data_fallback"]
  web:
    build: ./web
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [model-service]
```

`docker compose up --build` must bring up the full stack from a clean clone with zero manual steps (`NFR-5`, `AC-9`).

---

## 12. Testing & Validation

- **Unit:** each meta-learner's uplift output shape/range; Qini/AUUC computation matches `sklift`'s reference implementation on a toy synthetic dataset with a known ground-truth uplift.
- **Reproducibility test:** run the full benchmark twice with the same seed; assert identical model ranking and near-identical AUUC values (`AC-2`).
- **Contract test:** assert the evaluation API response schema contains no top-level `accuracy`/`auc` field (`AC-5`).
- **E2E:** budget slider → `/decision` → target list length never exceeds `floor(budget / cost_per_contact)` (`AC-3`).

---

## 13. MVP Build Order

1. `core/datasets.py` — Hillstrom loader + fallback cache
2. `core/learners.py` — S/T/X-learner + causal forest fitting on Hillstrom
3. `core/evaluation.py` — Qini/AUUC + segment breakdown, validated against `sklift` reference values
4. `/benchmark` endpoint wired to the above
5. `core/decision_engine.py` + `/decision` endpoint
6. Frontend: dataset select → benchmark view → simulator, in that order
7. CSV export (`/export`)
8. Second dataset (Criteo or Lenta) added to prove generalization
9. Docker Compose one-command demo
10. PWA installability pass + WCAG contrast audit

---

## 14. Appendix — Key JSON Contracts

**`POST /benchmark` response (abridged):**
```json
{
  "dataset": "hillstrom",
  "seed": 42,
  "diagnostics": { "n_train": 44800, "n_holdout": 19200, "base_conversion_rate": 0.0906 },
  "models": [
    { "name": "x_learner", "qini_coefficient": 0.081, "auuc": 0.074,
      "secondary_diagnostics": { "auc_note": "not used for model selection" } },
    { "name": "t_learner", "qini_coefficient": 0.063, "auuc": 0.058 }
  ],
  "winner": "x_learner"
}
```

**`POST /decision` response (abridged):**
```json
{
  "budget": 5000, "cost_per_contact": 2.5, "n_targeted": 2000,
  "uplift_ranked_profit": 18320.5,
  "propensity_ranked_profit": 12110.0,
  "profit_gap": 6210.5,
  "target_list_export_url": "/export/run_20260702_1"
}
```

---

*End of `02_SOFTWARE_SPEC.md`*
