# 01 — Requirement Specification

**Project:** UpliftIQ — Incremental Targeting Decision Engine
**Working Thesis Title:** *UpliftIQ: A Productionized Uplift-Modeling Decision Engine for Incremental Campaign Targeting — A Meta-Learner Benchmark on Incremental ROI*
**Document Type:** Requirement Specification (Business / Product Requirements)
**Version:** 1.0
**Status:** Draft for Implementation Hand-off
**Audience:** AI Coding Agent, Thesis Advisor, Reviewers
**Author:** Nathapol Powpadetkarn (Frong)
**Program:** M.Sc. Business Analytics & Statistics, KMITL

---

## 1. Purpose of This Document

This document defines **what** the system must do and **why**, independent of implementation. The companion `02_SOFTWARE_SPEC.md` defines **how**.

The thesis answers one question other student projects do not:

> **"Who buys *because of* the campaign — not merely who buys?"**

This is the difference between **correlation** (response/churn prediction, done to death) and **causation** (individual treatment effect / uplift). The project (a) builds and benchmarks uplift models, then (b) wraps the best one in a deployed decision engine that selects whom to target under a budget and reports the **incremental profit** gained versus conventional targeting.

> ⚠️ **Reviewer-facing framing.** The statistical core is causal inference: estimating the **Conditional Average Treatment Effect (CATE)** under the *fundamental problem of causal inference* (we never observe both potential outcomes for one person). The engineering — API, simulator, dashboard — exists to make the statistics *decision-grade*. This is what makes the work both rigorous and rare.

---

## 2. Background & Problem Statement

A marketing team can afford to contact only a fraction of its customers (e.g., 10,000 of 100,000). The industry default is to target **those most likely to convert**. This is a costly mistake:

- Many high-propensity customers are **Sure Things** — they convert anyway; the incentive is wasted margin.
- Some customers are **Sleeping Dogs (Do-Not-Disturb)** — contacting them *reduces* conversion (annoyance, opt-out). The campaign actively destroys value.
- The only segment worth paying for is **Persuadables** — customers who convert *only if* contacted.

Propensity targeting cannot see these segments because it models P(convert), not the **treatment effect** P(convert | treated) − P(convert | not treated). UpliftIQ models the latter, ranks customers by causal uplift, and spends the budget where it actually creates incremental conversions.

### The four uplift segments
| Segment | Behaviour | Action |
|---|---|---|
| **Persuadable** | Converts only if treated (uplift > 0) | **Target** (the gold) |
| **Sure Thing** | Converts regardless | Don't target (wasted incentive) |
| **Lost Cause** | Never converts | Don't target (wasted contact) |
| **Sleeping Dog** | Treatment *lowers* conversion (uplift < 0) | **Never target** |

---

## 3. Objectives

### 3.1 Research Objectives (Thesis)
- **RO-1** Estimate **CATE / uplift** per customer from randomized experimental data.
- **RO-2** Implement and **benchmark multiple meta-learners** (S-, T-, X-learner) plus an advanced estimator (Causal Forest / R-learner) on standard uplift datasets.
- **RO-3** Evaluate models with **uplift-appropriate metrics** — Qini coefficient, AUUC (Area Under Uplift Curve), uplift-by-decile, and calibration — *not* accuracy/AUC, and justify why.
- **RO-4** Quantify the **incremental business value**: profit/ROI of uplift-based targeting versus (a) random targeting and (b) propensity/response targeting, under a fixed budget.
- **RO-5** Demonstrate generalisation by repeating the benchmark on ≥ 2 datasets of different scale.

### 3.2 Product Objectives
- **PO-1** Serve per-customer uplift scores via an API.
- **PO-2** Provide an interactive **campaign simulator**: set a budget → see selected customers, segment mix, expected incremental conversions and profit, updated live.
- **PO-3** Provide an executive **uplift dashboard** (Power BI) for segment and Qini reporting.
- **PO-4** Run as a mobile-friendly **web application**, containerised for one-command demo.

### 3.3 Out of Scope (this PoC)
- Real-time bidding / live campaign execution (the engine *recommends*, it does not send).
- Continuous online learning; models are trained in batch.
- Causal discovery on purely observational data without a treatment indicator (datasets used are randomized/experimental).
- Native mobile apps (web/PWA only).

---

## 4. Stakeholders & Personas

| ID | Persona | Goal | Needs |
|----|---------|------|-------|
| P1 | **Marketing analyst** | Spend budget for max incremental return | Whom to target, expected lift, simple controls |
| P2 | **Marketing manager / CMO** | Justify spend | Incremental profit vs baseline, segment view |
| P3 | **Data scientist (owner)** | Validate models | Clean benchmark, reproducible pipeline, metrics |
| P4 | **Thesis reviewer** | Assess rigour | Correct causal framing, honest evaluation |

---

## 5. Functional Requirements

### Tier A — Modeling & Benchmark (THESIS CORE)
- **FR-A1** Ingest a randomized uplift dataset with features `X`, treatment flag `T`, and outcome `Y` (see §9 for datasets).
- **FR-A2** Validate experimental integrity: check treatment/control **covariate balance** before modeling.
- **FR-A3** Train uplift models: **S-learner, T-learner, X-learner** (mandatory) and **Causal Forest / R-learner** (advanced comparison).
- **FR-A4** Estimate a **per-customer uplift score** (CATE) on a held-out set.
- **FR-A5** Evaluate with **Qini coefficient, AUUC, uplift-by-decile, and calibration**; produce a versioned, seeded evaluation report.
- **FR-A6** Run the full benchmark on **≥ 2 datasets** and compare results.
- **FR-A7** Persist the selected best model as a servable artifact.

### Tier B — Decision Layer (business value)
- **FR-B1** Given a **budget** (max N contacts), per-contact **cost**, and per-conversion **value**, rank customers by uplift and select the top-N within budget.
- **FR-B2** Compute **expected incremental conversions and incremental profit** for the selection.
- **FR-B3** Compare against **baselines**: random targeting and propensity/response targeting — report the profit gap (the headline number).
- **FR-B4** Classify each customer into one of the four uplift segments (§2).

### Tier C — Serving & Experience
- **FR-C1** Scoring API: accept customer features → return uplift score + segment.
- **FR-C2** **Campaign Simulator** UI: budget/cost/value controls; live output of selected count, segment mix, incremental conversions, incremental profit, and the Qini curve.
- **FR-C3** Batch scoring: upload/point to a customer file → return a ranked target list (CSV export, UTF-8 BOM).
- **FR-C4** Power BI dashboard: segment distribution, Qini/uplift curves, profit-vs-baseline, decile lift.
- **FR-C5** (Stretch) RAG/LLM "explainer": plain-language description of why a segment is persuadable, grounded in the model's feature attributions.

### Tier D — Guardrails
- **FR-D1** Evaluation must **never** report accuracy/AUC as the primary uplift metric; the report must state why these are inappropriate for uplift.
- **FR-D2** The decision layer must always show the **counterfactual baseline** alongside the uplift result (no cherry-picking).
- **FR-D3** Any claimed profit figure must be reproducible from the seeded pipeline.

---

## 6. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-1 | **Platform** | Web application, mobile-friendly, installable as a PWA. |
| NFR-2 | **Performance** | Simulator recomputes selection + metrics for ≤ 100k scored rows in ≤ 1 s (precomputed scores). |
| NFR-3 | **Scalability** | Pipeline must handle the Criteo dataset (~14M rows) on a single machine via chunking / DuckDB. |
| NFR-4 | **Reproducibility** | Single-seed, single-command end-to-end run (data → model → metrics → report). |
| NFR-5 | **Portability** | Fully containerised (Docker + compose). |
| NFR-6 | **I18n** | English UI; Thai-friendly exports (UTF-8 BOM CSV). |
| NFR-7 | **Accessibility** | WCAG AA contrast; primary `#e86020` usage rule per §8. |
| NFR-8 | **Honesty** | Metrics, baselines, and assumptions reported transparently (FR-D1–D3). |

---

## 7. UX / UI Requirements

A clean, modern analytics surface in the spirit of Google Gemini / Material, mobile-friendly, with KMITL warm orange as the accent.

- **UX-1 Simulator-first.** The hero screen is the **Campaign Simulator**: a budget slider and cost/value inputs at top; results update live below.
- **UX-2 Money on screen.** The signature interaction: drag the budget slider → **expected incremental profit updates in real time**, with the uplift-targeting line visibly above the baseline line. This is the demo that reviewers remember.
- **UX-3 Segment view.** A clear visual of the four segments and how many fall in each.
- **UX-4 Qini/uplift curve.** Rendered interactively; hover for cumulative incremental gain.
- **UX-5 Baseline contrast.** Uplift vs propensity vs random always shown together.
- **UX-6 Export.** One-click ranked target list (CSV, UTF-8 BOM).
- **UX-7 Light & dark mode.**
- **UX-8 Mobile ergonomics.** Works one-handed; large tap targets; responsive charts.

### Design Tokens (binding)
- **Primary:** `#e86020` (KMITL warm orange) — slider fill, primary buttons, the uplift line on charts, key accents.
- **Typography:** **Google Sans**.
  > Implementation note: Google Sans is proprietary and **not** on Google Fonts. Use the stack `"Google Sans", "Google Sans Text", "Roboto", "Inter", system-ui, sans-serif` with graceful fallback; do not ship a broken font load.
- **Shape:** generous radii, soft surfaces, airy spacing.
- Full token table in `02_SOFTWARE_SPEC.md` §8.

---

## 8. Accessibility Constraint on the Primary Colour

`#e86020` on white is ≈ **3.2:1** contrast — **fails** WCAG AA for normal body text (needs ≥ 4.5:1).

- Use `#e86020` for **large text, icons, fills, borders, chart lines, accents** only.
- For **small brand-coloured text on white**, use a darkened `#9c3614`.
- On dark surfaces, use a lightened `#ff7a45`.
- Mandatory (NFR-7). Full palette in the software spec.

---

## 9. Datasets (verified, public, ready to use)

> 🟢 **Zero data risk.** Unlike a university-data project, all datasets here are **public, free, and free of privacy constraints** — the project can start immediately. All are real randomized experiments.

### 9.1 Primary — Hillstrom / MineThatData (recommended starting point)
Clean, classic, 3-arm **randomized** email experiment. 64,000 customers; arms = *Men's email*, *Women's email*, *No email (control)*; outcomes = `visit`, `conversion`, `spend`; features include recency, history value, channel, etc. Small enough to iterate fast, well-documented in the uplift literature.

- Original announcement: `https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html`
- Original CSV: `http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`
- Clean mirror (used by scikit-uplift): `https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz`
- Kaggle copy: `https://www.kaggle.com/datasets/bofulee/kevin-hillstrom-minethatdata-e-mailanalytics`
- Loader: `from sklift.datasets import fetch_hillstrom`

### 9.2 Scale — Criteo Uplift Prediction v2.1
Large real ad-incrementality benchmark. ~**13.98M rows**, 12 anonymized features `f0–f11`, `treatment`, `exposure`, and labels `visit`, `conversion`. Use to prove the pipeline scales (NFR-3).

- Homepage / description: `https://ailab.criteo.com/criteo-uplift-prediction-dataset/`
- Direct download (CSV gz, ~297 MB): `http://go.criteo.net/criteo-research-uplift-v2.1.csv.gz`
- Hugging Face: `https://huggingface.co/datasets/criteo/criteo-uplift`
- Loader: `from sklift.datasets import fetch_criteo`
- **License: CC BY-NC-SA 4.0** (non-commercial — fine for academic use; cite the Diemert et al. 2018 paper).

### 9.3 Additional — Lenta & X5 RetailHero (retail, optional 3rd dataset)
Russian retail uplift datasets for extra generalisation evidence (RO-5).

- Lenta loader: `from sklift.datasets import fetch_lenta`
- X5 RetailHero loader: `from sklift.datasets import fetch_x5` (competition page: `https://ods.ai/competitions/x5-retailhero-uplift-modeling/data`)

### 9.4 Easiest path
`pip install scikit-uplift` provides `fetch_hillstrom`, `fetch_criteo`, `fetch_lenta`, `fetch_x5` with auto-download and caching — no manual file handling required. Docs: `https://www.uplift-modeling.com/`.

---

## 10. Constraints & Assumptions
- **C-1** Single developer + AI coding agent; PoC scope.
- **C-2** Web/PWA only; no native builds.
- **C-3** Containerised for reproducible demo.
- **A-1** Datasets are randomized → treatment is unconfounded (no need for observational adjustment in the core; balance is still verified, FR-A2).
- **A-2** Cost/value parameters for the decision layer are user-supplied assumptions, clearly labelled.

---

## 11. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Misusing accuracy/AUC for uplift | High (invalidates thesis) | Med | Mandate Qini/AUUC; FR-D1; explain why |
| Cherry-picked profit claim | High | Med | Always show baselines (FR-D2); seeded repro (FR-D3) |
| Criteo size overwhelms machine | Med | Med | DuckDB chunking; subsample for dev; full run for final (NFR-3) |
| Project read as "just ML" | Med | Low | Causal framing + deployed decision engine + simulator demo |
| Google Sans licensing | Low | High | Documented fallback (§7) |

---

## 12. MVP Scope (MoSCoW)

**Must:** FR-A1–A7 on **Hillstrom**, FR-B1–B4 decision layer, FR-C1–C2 scoring API + simulator, FR-C4 Power BI, PWA + design tokens, seeded reproducible pipeline.
**Should:** Second dataset (Criteo) for scale/generalisation, FR-C3 batch scoring export.
**Could:** Lenta/X5 third dataset, FR-C5 LLM explainer.
**Won't (this cycle):** live campaign execution, online learning, native apps.

---

## 13. Acceptance Criteria & Success Metrics

### Research (thesis)
- **AC-1** S-, T-, X-learner + one advanced model trained and **benchmarked** on Hillstrom with **Qini coefficient and AUUC** reported under a seeded split.
- **AC-2** Uplift-by-decile shows the top deciles have materially higher actual incremental response than the bottom (the model *ranks* uplift correctly).
- **AC-3** Decision layer shows uplift targeting yields **higher incremental profit** than random and propensity targeting at a fixed budget — the **headline result**, with the gap quantified.
- **AC-4** Benchmark reproduced on a **second dataset** (Criteo) demonstrating the pipeline scales.
- **AC-5** Full pipeline re-runs end-to-end from one command with a fixed seed (NFR-4).

### Product
- **AC-6** Simulator: changing the budget updates selection, segment mix, and incremental profit live, with the baseline visible (UX-2/5).
- **AC-7** Ranked target list exports as UTF-8 BOM CSV (FR-C3).
- **AC-8** App installs and is usable on mobile (PWA).

---

## 14. Glossary
- **Uplift / CATE** — Conditional Average Treatment Effect: τ(x) = E[Y | X=x, T=1] − E[Y | X=x, T=0].
- **Meta-learner** — uplift estimator built from base ML models (S/T/X/R-learner).
- **Qini coefficient / AUUC** — uplift-specific ranking-quality metrics.
- **Persuadable / Sure Thing / Lost Cause / Sleeping Dog** — the four uplift segments.
- **Fundamental problem of causal inference** — only one potential outcome per unit is observed; individual uplift is never directly measured, so evaluation is done at group level on a randomized holdout.

---

*End of `01_REQUIREMENT_SPEC.md`*
