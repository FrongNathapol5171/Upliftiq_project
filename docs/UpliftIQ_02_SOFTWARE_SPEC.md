# 02 — Software Specification

**Project:** UpliftIQ — Incremental Targeting Decision Engine
**Document Type:** Software / Technical Specification (Architecture & Design)
**Version:** 1.0
**Status:** Draft for Implementation Hand-off
**Companion:** `UpliftIQ_01_REQUIREMENT_SPEC.md`
**Audience:** AI Coding Agent
**Author:** Nathapol Powpadetkarn (Frong)

---

## 0. How to Use This Document (note to the coding agent)

Build in the **MVP order** of §13. The **modeling + evaluation pipeline (§10) is the thesis core** — get the benchmark and the Qini/AUUC report correct first; the API, simulator, and dashboard wrap it. Never report accuracy/AUC as the primary uplift metric (FR-D1). Every requirement ID maps back to `UpliftIQ_01_REQUIREMENT_SPEC.md`.

---

## 1. Architecture Overview

Three planes: **train** (offline benchmark), **serve** (scoring + decision API), **experience** (simulator PWA + Power BI).

```
┌────────────────────────────────────────────────────────────┐
│  EXPERIENCE PLANE                                           │
│  Next.js PWA — Campaign Simulator (budget slider, charts)   │
│  Power BI — uplift segments, Qini, profit-vs-baseline       │
└───────────────┬────────────────────────────────────────────┘
                │  HTTPS / JSON
┌───────────────▼────────────────────────────────────────────┐
│  SERVE PLANE  (FastAPI)                                     │
│   /score   → uplift score + segment per customer            │
│   /simulate→ budget,cost,value → selection + incremental    │
│              profit + baseline comparison                   │
│   /batch   → ranked target list (CSV UTF-8 BOM)             │
│   loads ◄── trained model artifact + precomputed scores     │
└───────────────┬────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────┐
│  TRAIN PLANE  (Python batch — THESIS CORE)                 │
│  ingest ▸ balance-check ▸ meta-learners (S/T/X + CForest)  │
│  ▸ Qini/AUUC/decile/calibration ▸ pick best ▸ persist      │
│  data via DuckDB/Parquet · models via causalml/EconML/sklift│
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Modeling | **causalml** (Uber), **EconML** (Microsoft), **scikit-uplift** | meta-learners, causal forest, Qini/AUUC, dataset loaders |
| Base learners | scikit-learn / LightGBM / XGBoost | inside the meta-learners |
| Data engine | **DuckDB** over **Parquet** | owner-familiar, scales to Criteo (~14M rows) on one machine |
| Experiment tracking | **MLflow** (optional) | log metrics/artifacts per model×dataset |
| Interpretability | **SHAP** | explain uplift drivers (FR-C5) |
| Serving | **FastAPI** | scoring + decision endpoints |
| Frontend | **Next.js + React + TypeScript + MUI (Material UI) v6+** | PWA, owner stack; Material aligns with the Gemini/Material aesthetic |
| UI components | **MUI core** (`Slider`, `Card`, `AppBar`, `Switch`, `TextField`) + **MUI X** (`DataGrid` for target lists) | beautiful, accessible, low-effort components |
| Charts | **MUI X Charts** (`LineChart`, `BarChart`) — Recharts as fallback | Qini & uplift curves, profit lines, visually consistent with MUI |
| Dashboard | **Power BI** | executive reporting (owner skill) |
| Packaging | **Docker + docker-compose** | reproducible demo |
| Hosting (demo) | Render / Railway / Fly.io / VPS | reachable for reviewers |

---

## 3. Component Design

### 3.1 Data Ingestion & Schema (FR-A1)
Normalise every dataset to a common frame:

| column | meaning |
|--------|---------|
| `f_*` | feature columns |
| `treatment` | binary (1 = treated/contacted, 0 = control) |
| `outcome` | binary primary label (e.g., `visit`/`conversion`) |
| `outcome_value` | optional numeric (e.g., `spend`) for profit |

- **Hillstrom:** map the 3-arm `segment` to binary (e.g., treated = received any email, or run per-arm); outcome = `visit`/`conversion`; value = `spend`.
- **Criteo:** features `f0–f11`; `treatment`; outcome = `visit`/`conversion`.
- Store as Parquet; query/feature-prep via DuckDB.

### 3.2 Experiment Validation (FR-A2)
Before modeling, verify randomization quality: standardized mean differences of features between treatment and control; report a balance table. (For randomized data these should be near zero; flag any drift.)

### 3.3 Uplift Models (FR-A3, A4)
Implement and benchmark, all behind a common interface `fit(X, T, Y)` / `predict_uplift(X)`:

- **S-learner** — single model with `T` as a feature; uplift = f(X, 1) − f(X, 0).
- **T-learner** — separate treated/control models; uplift = μ₁(X) − μ₀(X).
- **X-learner** — impute individual effects, model them, combine via propensity weighting (handles treatment imbalance — important for Criteo's 0.85 treatment ratio).
- **Causal Forest** (EconML `CausalForestDML`) and/or **R-learner** — advanced comparison.

Use `causalml` / `EconML` implementations; do not hand-roll unless for a baseline.

### 3.4 Evaluation (FR-A5) — get this right
Uplift cannot be scored by accuracy (no individual ground truth). Compute on a **randomized holdout**:

- **Qini curve + Qini coefficient**
- **Uplift curve + AUUC** (Area Under Uplift Curve)
- **Uplift-by-decile** table (rank by predicted uplift; show actual incremental response per decile)
- **Calibration** of predicted vs observed uplift by bin

`scikit-uplift` provides `qini_auc_score`, `uplift_auc_score`, `uplift_by_percentile`, and plotting helpers. Emit a versioned, seeded **evaluation report** (markdown + figures) per model×dataset.

### 3.5 Decision Layer (FR-B1–B4)
Pure functions over the scored holdout:

```
select(budget_N, cost_per_contact, value_per_conversion):
    rank customers by predicted uplift (desc)
    take top-N within budget
    expected_incremental_conversions = Σ uplift_i over selected
    expected_incremental_profit =
        expected_incremental_conversions * value_per_conversion
        − N * cost_per_contact
    compare vs baselines:
        random_targeting, propensity_targeting (model P(Y=1))
    return selection, segments, profit, baseline_profits, qini
```

Segment assignment: Persuadable (uplift > +ε), Sleeping Dog (uplift < −ε), and Sure Thing / Lost Cause split by predicted base rate.

### 3.6 Serving API (FR-C1–C3)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/score` | features → `{uplift, segment, base_rate}` |
| `POST` | `/api/simulate` | `{budget, cost, value, dataset}` → selection + incremental profit + baselines + qini points |
| `POST` | `/api/batch` | file/ref → ranked target list, CSV UTF-8 BOM |
| `GET`  | `/api/metrics` | benchmark metrics per model×dataset (for dashboard) |
| `GET`  | `/api/health` | liveness |

The API loads a **precomputed score table** for the demo dataset so `/simulate` is instant (NFR-2); `/score` uses the live model artifact for ad-hoc inputs.

---

## 4. Model & Artifact Storage

- Trained models serialised under `models/{dataset}/{learner}.pkl` (+ MLflow run if enabled).
- A `scores/{dataset}.parquet` table: `{id, uplift, base_rate, segment, T, Y, value}` used by the simulator.
- A `reports/{dataset}/` folder: metrics JSON + Qini/uplift PNGs + the markdown evaluation report.

---

## 5. Frontend Design (Next.js PWA + MUI)

All components are composed from **MUI** (see §8 for the theme + component mapping). Wrap the app in `ThemeProvider` + `CssBaseline`.

### 5.1 Screens / components
- **SimulatorScreen** (hero, UX-1): `BudgetSlider` (MUI `Slider`), `CostInput`/`ValueInput` (MUI `TextField`), `DatasetPicker` (`ToggleButtonGroup`) at top; results below.
- **ProfitPanel** (UX-2): big number — expected incremental profit — plus an uplift-vs-baseline line chart that animates as the slider moves.
- **SegmentBreakdown** (UX-3): four-segment bar/donut with counts.
- **QiniChart** (UX-4): Qini/uplift curve, hover for cumulative gain.
- **BaselineToggle** (UX-5): uplift vs propensity vs random, always comparable.
- **ExportButton** (UX-6): ranked CSV.
- **ThemeToggle** (UX-7).

### 5.2 PWA (NFR-1)
- `manifest.webmanifest`: `display: standalone`, theme_color `#e86020`, maskable icons.
- Service worker caches the app shell; network-first for `/api/*`.
- Respect iOS safe-area insets; test Add-to-Home-Screen on Safari.

---

## 6. (reserved)

## 7. (reserved)

---

## 8. Design System — MUI (Material UI) (binding — UX, NFR-7, `01` §7/§8)

The UI is built with **MUI**. All styling flows from a **single MUI theme** via `ThemeProvider`; use the `sx` prop and `styled()` for layout — **do not add Tailwind** (avoid a second, conflicting styling system). MUI's Material foundation matches the Gemini/Material aesthetic the project targets.

### 8.1 The theme (single source of truth)
Define one theme with light/dark color schemes. Recommended: MUI v6+ CSS-variables theming (`cssVariables: true`, `colorSchemes`) so dark mode is a class toggle with no flicker.

```ts
// theme.ts
import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: "data" },
  colorSchemes: {
    light: {
      palette: {
        primary: {
          main: "#e86020",        // KMITL warm orange — slider fill, primary btn, uplift line
          dark: "#b8431a",        // hover/press
          light: "#fce9df",       // tint / selected background
          contrastText: "#ffffff",
        },
        text: { primary: "#1b1b1f", secondary: "#5f6368" },
        background: { default: "#ffffff", paper: "#f7f7f8" },
        divider: "#e3e3e6",
        success: { main: "#1e8e3e" },
        warning: { main: "#f29900" },
        error:   { main: "#d93025" },
      },
    },
    dark: {
      palette: {
        primary: { main: "#ff7a45", dark: "#e86020", light: "#3a2417", contrastText: "#1b1b1f" },
        text: { primary: "#e6e6e9", secondary: "#a3a3ab" },
        background: { default: "#131316", paper: "#1c1c20" },
        divider: "#34343a",
      },
    },
  },
  shape: { borderRadius: 16 },            // soft, Gemini-like; cards use 16–24
  typography: {
    fontFamily: [
      '"Google Sans"','"Google Sans Text"','"Roboto"','"Inter"',
      "system-ui",'"Noto Sans Thai"',"sans-serif",
    ].join(","),
    h1: { fontWeight: 600 }, h2: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 }, // no ALL-CAPS buttons
  },
  components: {
    MuiButton:  { defaultProps: { disableElevation: true },
                  styleOverrides: { root: { borderRadius: 999 } } }, // pill buttons
    MuiCard:    { styleOverrides: { root: { borderRadius: 20 } } },
    MuiPaper:   { styleOverrides: { rounded: { borderRadius: 20 } } },
    MuiSlider:  { styleOverrides: { thumb: { width: 22, height: 22 } } }, // big touch target
    MuiChip:    { styleOverrides: { root: { borderRadius: 999 } } },
    MuiTextField:{ defaultProps: { variant: "outlined", size: "medium" } },
  },
});
```

### 8.2 Chart series colours (for MUI X Charts)
```ts
export const series = {
  uplift:   "#e86020",  // brand = the hero line (always on top of baseline)
  baseline: "#5f6368",  // propensity targeting (neutral grey)
  random:   "#b0b3b8",  // random targeting
};
```

### 8.3 Contrast rule (NFR-7) — still binding under MUI
`#e86020` on white ≈ **3.2:1** → fails AA for small body text. Therefore:
- Use `primary.main` for **buttons (white text on orange fill — passes), slider/track fills, icons, chart lines, large headings**.
- For **small orange TEXT on a white/paper background**, do **not** use `primary.main`; use a darkened `#9c3614` (define as `primary.dark`-adjacent or a custom `palette.brandText`).
- On dark surfaces the lifted `#ff7a45` is used automatically by the dark scheme.
- Enforce with an automated contrast check in CI.

### 8.4 Component mapping (build the simulator from MUI)
| UI element | MUI component |
|------------|---------------|
| Budget control (hero) | `Slider` (with `valueLabelDisplay`) |
| Cost / value inputs | `TextField` (number, with adornments) |
| Dataset picker | `ToggleButtonGroup` or `Select` |
| Result panels | `Card` / `Paper` with `Stack` + `Grid` |
| Incremental-profit headline | `Typography variant="h2"` in `primary.main` |
| Segment counts | `Chip` set + `MuiX BarChart` |
| Uplift-vs-baseline & Qini | `MuiX LineChart` (series coloured per §8.2) |
| Ranked target list | `MuiX DataGrid` (sortable, exportable) |
| Light/dark toggle | `Switch` + `useColorScheme()` |
| Top bar | `AppBar` + `Toolbar` |

### 8.5 Gemini-style feel
Generous spacing (`theme.spacing` 1.5–3), rounded `Card`s, soft elevation, no ALL-CAPS buttons, the **uplift line in brand orange sitting visibly above the grey baseline**. Animate the profit number/chart on slider change with a short ease-out; respect `prefers-reduced-motion`.

> Setup: wrap the app in `<ThemeProvider theme={theme}><CssBaseline />…`. Use `InitColorSchemeScript` (Next.js App Router) to prevent dark-mode flash. The coding agent should also read `/mnt/skills/public/frontend-design/SKILL.md` before building UI.

---

## 9. (reserved)

---

## 10. Train Plane — THESIS CORE (§3.3–3.5 detailed pipeline)

A scripted, seeded pipeline. One command runs: ingest → balance check → train all learners → evaluate → select best → persist scores/report, per dataset.

### 10.1 Pipeline stages
1. **Load** via `sklift.datasets.fetch_*` (Hillstrom, then Criteo). Cache to Parquet.
2. **Split** train/holdout with fixed seed, stratified by treatment.
3. **Balance report** (FR-A2).
4. **Train** S-, T-, X-learner (causalml/sklift) + Causal Forest (EconML) on identical features.
5. **Evaluate** on holdout: Qini coefficient, AUUC, uplift-by-decile, calibration (FR-A5).
6. **Select** best by Qini (with AUUC as tie-breaker); persist artifact + score table.
7. **Decision benchmark** (FR-B): sweep budget; compute incremental profit for uplift vs propensity vs random; store the profit-vs-baseline curve (the headline, AC-3).
8. **Report**: write `reports/{dataset}/report.md` + figures + metrics JSON.

### 10.2 Headline result (AC-3)
The thesis's central exhibit: at a fixed budget, **incremental profit from uplift targeting minus incremental profit from propensity targeting** — quantified, on ≥ 2 datasets. Plus the uplift-by-decile table showing correct ranking, and Qini/AUUC across learners.

### 10.3 Generalisation (AC-4)
Re-run the entire pipeline on Criteo (use DuckDB chunking / a stratified subsample for development, full run for final numbers). Optionally add Lenta/X5 for a third point.

### 10.4 Interpretability (FR-C5, stretch)
SHAP on the uplift model to rank which features drive persuadability; feed a short LLM-generated plain-language segment explainer if implemented.

---

## 11. Reproducibility & Honesty (FR-D1–D3, NFR-4/8)
- Single `--seed`; pinned library versions; one-command `make all` / `python -m pipeline.run`.
- Report **always** includes the baselines and a note on why accuracy/AUC are not used for uplift.
- All profit figures regenerate from the seeded pipeline.

---

## 12. Deployment & DevOps (NFR-5)
- `docker-compose.yml`: `web` (Next.js), `api` (FastAPI + model artifacts), optional `train` (one-shot pipeline job).
- One command: `docker compose up` → loads precomputed scores → simulator reachable.
- `/api/health` for demo stability; backend deployable to Render/Railway/Fly.io.

---

## 13. Implementation Phases (build order)

**Phase 0 — Foundation:** repo scaffold, docker-compose, `sklift` data loaders, Parquet/DuckDB layer, design tokens.
**Phase 1 — Modeling core (THESIS):** S/T/X-learner + evaluation (Qini/AUUC/decile/calibration) on **Hillstrom**; seeded report. → AC-1/2/5.
**Phase 2 — Decision layer:** budget-constrained selection, incremental profit, baseline comparison, segments. → AC-3.
**Phase 3 — Serving + Simulator:** FastAPI `/score`/`/simulate`/`/batch`; Next.js simulator with live profit-vs-baseline; PWA. → AC-6/7/8.
**Phase 4 — Scale + dashboard:** re-run on **Criteo**; Power BI dashboard. → AC-4.
**Phase 5 — Stretch:** Causal Forest/R-learner deep-dive, Lenta/X5, SHAP + LLM explainer.

---

## 14. Testing Strategy
- **Pipeline:** seeded run reproduces identical metrics (AC-5); asserts top deciles > bottom deciles in actual incremental response (AC-2).
- **Decision layer:** unit tests that uplift selection ≥ random/propensity profit on the holdout (AC-3) for the demo dataset.
- **Metric correctness:** cross-check Qini/AUUC against `scikit-uplift` reference values on Hillstrom.
- **API:** `/simulate` returns consistent numbers vs the offline pipeline for the same inputs.
- **Scale:** Criteo pipeline completes within memory via DuckDB chunking (NFR-3).
- **PWA/UI:** Lighthouse PWA pass; mobile Add-to-Home-Screen; contrast check enforcing the `#e86020` rule (NFR-7).

---

## 15. Repository Structure
```
upliftiq/
├─ docker-compose.yml
├─ .env.example
├─ pipeline/                    # TRAIN PLANE (thesis core)
│  ├─ data.py (sklift loaders → parquet, duckdb)
│  ├─ balance.py (FR-A2)
│  ├─ models.py (S/T/X-learner, causal forest)
│  ├─ evaluate.py (qini, auuc, decile, calibration)
│  ├─ decision.py (budget selection, incremental profit, baselines)
│  └─ run.py (one-command orchestrator, --seed)
├─ api/                         # SERVE PLANE
│  ├─ main.py (/score /simulate /batch /metrics /health)
│  └─ loaders.py (model artifact + score table)
├─ web/                         # EXPERIENCE PLANE (Next.js PWA)
│  ├─ app/ (SimulatorScreen)
│  ├─ components/ (BudgetSlider, ProfitPanel, SegmentBreakdown, QiniChart, ExportButton)
│  ├─ theme.ts                  # §8 MUI theme (single source of truth)
│  ├─ providers.tsx             # ThemeProvider + CssBaseline + color scheme
│  └─ public/ (manifest, icons, sw)
├─ models/  scores/  reports/   # artifacts, score tables, eval reports
├─ powerbi/                     # dashboard + exports (UTF-8 BOM)
└─ docs/
   ├─ UpliftIQ_01_REQUIREMENT_SPEC.md
   └─ UpliftIQ_02_SOFTWARE_SPEC.md
```

---

## 16. Environment Variables (`.env.example`)
```
SEED=42
DATA_HOME=./.uplift_data          # sklift cache
DEFAULT_DATASET=hillstrom
LLM_API_KEY=                      # optional, explainer only
APP_ORIGIN=
```

---

## 17. Traceability (requirement → component)
| Requirement | Built in |
|-------------|----------|
| FR-A1–A2 (ingest, balance) | §3.1, §3.2, pipeline/data,balance |
| FR-A3–A4 (meta-learners) | §3.3, pipeline/models |
| FR-A5–A7 (evaluation, artifact) | §3.4, §10, pipeline/evaluate |
| FR-B1–B4 (decision) | §3.5, pipeline/decision |
| FR-C1–C3 (API) | §3.6, api/ |
| FR-C2 (simulator) | §5, web/ |
| FR-C4 (dashboard) | §10, powerbi/ |
| FR-C5 (explainer) | §10.4 |
| FR-D1–D3 (honesty) | §11 |
| UX/design | §5, §8 |
| NFR-1 (PWA) | §5.2, §12 |
| NFR-3 (scale) | §10.3 |
| NFR-7 (contrast) | §8.1 |

---

*End of `02_SOFTWARE_SPEC.md`*
