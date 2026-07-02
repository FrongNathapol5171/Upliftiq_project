# 01 — Requirement Specification

**Project:** UpliftIQ — Incremental Targeting Decision Engine
**Working Thesis Title:** *UpliftIQ: A Budget-Constrained Causal Uplift Framework for Incremental Marketing Targeting*
**Document Type:** Requirement Specification (Business / Product Requirements)
**Version:** 1.0
**Status:** Final — Ready for Implementation Hand-off
**Audience:** AI Coding Agent, Thesis Advisor, Reviewers
**Author:** Nathapol Powpadetkarn (Frong)
**Program:** M.Sc. Business Analytics & Statistics, KMITL

---

## 1. Purpose of This Document

This document defines **what** the system must do and **why**, independent of implementation. It is the contract the finished software is validated against. The companion document `02_SOFTWARE_SPEC.md` defines **how** it is built.

Two intents run in parallel and both must be satisfied:

1. **Product intent** — a working decision-support tool that a marketing/CRM analyst could plausibly use to decide who to target in a campaign under a fixed budget.
2. **Research intent (the thesis core)** — a rigorous, reproducible benchmark comparing causal uplift modeling against traditional response modeling, reported with uplift-appropriate statistics. **The benchmark and evaluation methodology — not the web app — is the academic contribution.**

> ⚠️ **Reviewer-facing framing.** This is not "a targeting app." It is "a causal-inference study in which the web app is the delivery mechanism for the decision layer." Every requirement below is written to keep statistical rigor central.

---

## 2. Background & Problem Statement

Most marketing targeting systems are built on **response models**: predict P(purchase | contacted), then target whoever scores highest. This is a well-known statistical error. A response model cannot separate:

- **Sure Things** — would have bought regardless of contact (wasted spend)
- **Lost Causes** — will not buy no matter what (wasted spend)
- **Sleeping Dogs** — contact actively *reduces* their likelihood to buy (negative ROI)
- **Persuadables** — buy *only if* contacted (the only group targeting should chase)

A response model cannot distinguish these four groups because it never estimates a counterfactual — it only ever sees one outcome per customer, not what would have happened under the other treatment. **Uplift modeling** exists specifically to estimate this individual/segment-level *incremental* effect using data from a randomized (or quasi-randomized) treatment/control experiment.

The business question this project answers: **given a fixed campaign budget, does ranking customers by estimated uplift produce more incremental profit than ranking by predicted response probability?** This is directly measurable, directly defensible statistically, and directly relevant to any company running marketing experiments — which is why all target datasets originate from real randomized campaigns.

---

## 3. Goals & Non-Goals

**Goals**
- Build and validate a benchmark of uplift meta-learners on multiple public experimental datasets
- Produce a budget-constrained targeting decision layer that operationalizes the best-performing model
- Communicate results (Qini curves, AUUC, segment breakdown, profit simulation) through an accessible, mobile-first web app
- Produce a reproducible, seed-controlled pipeline suitable for academic defense

**Non-Goals**
- This is not a production marketing-automation platform; it does not send real emails/SMS or integrate with a live CRM
- This is not a general-purpose AutoML tool; the model family is intentionally scoped to uplift meta-learners
- This does not claim causal identification beyond what the source datasets' randomization already provides (no attempt to de-bias observational/non-randomized data)

---

## 4. Stakeholders & Users

| Role | Interest |
|---|---|
| **Thesis author** (project owner) | Builds and defends the work |
| **Thesis advisor / committee** | Validates statistical rigor and defensibility |
| **Persona: Marketing/CRM Analyst** | Hypothetical end user of the simulator — uploads a budget, gets a target list and expected incremental profit |

---

## 5. Scope

**MVP (must ship for the thesis defense):**
- Data ingestion for at least 2 datasets (Hillstrom + one of Criteo/Lenta/X5)
- Full meta-learner benchmark (S-, T-, X-learner, causal forest) with Qini/AUUC evaluation
- Budget-constrained decision layer
- Web app: upload/select dataset → view benchmark results → run budget simulator → export target list

**Stretch (only after MVP is fully working):**
- All four public datasets benchmarked
- R-learner / doubly-robust learner added to the comparison
- Power BI companion dashboard consuming exported results
- Multi-treatment-arm support (Hillstrom has two treatment arms: Men's, Women's campaign)

---

## 6. Functional Requirements

### FR-A — Data & Benchmark Ingestion
- **FR-A1** System shall load each supported dataset via its official `scikit-uplift` loader (no manual re-hosting of data).
- **FR-A2** System shall perform a stratified train/holdout split preserving treatment/control ratios, with a fixed random seed.
- **FR-A3** System shall report basic dataset diagnostics (sample size, treatment/control balance, base conversion rate) before modeling.

### FR-B — Modeling
- **FR-B1** System shall fit at minimum: S-learner, T-learner, X-learner, and a causal-forest-based estimator, on each dataset's training split.
- **FR-B2** All model hyperparameters and the random seed used shall be logged and exportable (reproducibility requirement).
- **FR-B3** System shall persist fitted models so the API can score new/holdout records without retraining on every request.

### FR-C — Decision Layer
- **FR-C1** Given a campaign budget (currency amount or % of population) and per-contact cost, system shall rank customers by predicted uplift and select the target set that maximizes total expected incremental profit within budget.
- **FR-C2** System shall simulate expected incremental profit for both the uplift-ranked target list and a propensity-ranked target list at the same budget, and report the gap between them.
- **FR-C3** System shall allow exporting the resulting ranked target list as CSV (UTF-8 with BOM, for Excel/Thai-locale compatibility).

### FR-D — Evaluation & Reporting
- **FR-D1** System shall never present accuracy or AUC as the primary/headline evaluation metric for an uplift model. Qini coefficient and AUUC are the required primary metrics; accuracy/AUC may appear only as a clearly labeled secondary diagnostic.
- **FR-D2** System shall generate a Qini curve (cumulative incremental gain vs. % population targeted) for each fitted model.
- **FR-D3** System shall report the four-segment breakdown (Persuadable / Sure Thing / Lost Cause / Sleeping Dog) at a configurable decile threshold.
- **FR-D4** System shall rank the benchmarked meta-learners by AUUC and clearly surface the winning model.

### FR-E — Simulator Web App
- **FR-E1** System shall provide a mobile-first, installable (PWA) web interface.
- **FR-E2** Users shall be able to select a dataset, view benchmark results, and interactively adjust the budget slider to see the target list and expected profit update.
- **FR-E3** Charts (Qini curve, decile uplift bars) shall be rendered with MUI X Charts; the target list shall be rendered with MUI X DataGrid.

### FR-F — Export & Reporting
- **FR-F1** System shall support exporting a summary report (model comparison table + Qini chart image + target list) suitable for inclusion in the thesis document.

---

## 7. Non-Functional Requirements

- **NFR-1 (Reproducibility):** Every benchmark run must be re-runnable with identical results given the same seed and dataset version.
- **NFR-2 (Performance):** Benchmark for a single dataset (all four meta-learners) shall complete in under 5 minutes on a standard laptop CPU; scoring an existing model via the API shall respond in under 2 seconds for up to 50,000 records.
- **NFR-3 (Accessibility):** UI shall meet WCAG AA contrast for all text, including brand-colored text (see Handoff Guide §5.3 on the `#e86020` / `#9c3614` distinction).
- **NFR-4 (Installability):** The web app shall pass Lighthouse PWA installability checks.
- **NFR-5 (Portability):** The entire system shall start via a single `docker compose up` command from a clean clone, with no manual dataset pre-downloading required by the user.
- **NFR-6 (Security):** No customer PII is involved (all datasets are public and pre-anonymized); no auth system is required for MVP.

---

## 8. Data Requirements

All datasets are loaded via the `scikit-uplift` (`sklift`) Python package's built-in fetchers — no manual hosting, no access request, no privacy review needed.

| Dataset | Loader | Size | Treatment structure | Notes |
|---|---|---|---|---|
| **Hillstrom MineThatData** | `sklift.datasets.fetch_hillstrom` | ~64,000 customers | 3-arm: Men's email / Women's email / no email | Classic benchmark; supports `target_col='visit'`, `'conversion'`, or `'spend'` |
| **Criteo Uplift v2.1** | `sklift.datasets.fetch_criteo` | ~14M rows (use `percent10=True` subsample for a laptop-feasible run) | 2-arm: exposure / control | Large-scale ad-incrementality benchmark from Diemert et al. 2018 |
| **Lenta** | `sklift.datasets.fetch_lenta` | Retail grocery promo dataset | 2-arm | From the 2020 Lenta/Microsoft BigTarget Hackathon |
| **X5 RetailHero** | `sklift.datasets.fetch_x5` | Multi-table (clients, train, purchases) | 2-arm | More realistic/messier schema; good stretch-goal dataset |

MVP requires Hillstrom + one additional dataset. All four is a stretch goal (§5).

---

## 9. Success Metrics / Thesis Headline Result

**The headline result is:** *the incremental profit gap, at a fixed budget, between targeting ranked by the best uplift meta-learner versus targeting ranked by a propensity/response model,* measured via AUUC and validated visually via the Qini curve, on at least two independent public experimental datasets.

Secondary results: benchmark comparison table across meta-learners; segment-level (four-quadrant) breakdown showing the practical cost of ignoring Sleeping Dogs and Sure Things.

---

## 10. Acceptance Criteria

- **AC-1** Benchmark runs end-to-end on Hillstrom data and produces Qini/AUUC for all four meta-learners.
- **AC-2** Benchmark is reproducible: re-running with the same seed produces the same model ranking.
- **AC-3** Decision layer respects the budget constraint as a hard cap — never recommends targeting beyond the specified budget.
- **AC-4** Decision layer output includes the profit-gap comparison (uplift-ranked vs. propensity-ranked) required for the headline result.
- **AC-5** UI never displays accuracy/AUC as the primary metric anywhere (spot-checked across all screens and exports).
- **AC-6** Qini curve renders correctly and matches the manually-computed reference value on a held-out sample (sanity check against `sklift`'s own `qini_auc_score`).
- **AC-7** Target list exports as UTF-8-with-BOM CSV (FR-C3).
- **AC-8** App installs and is usable on mobile as a PWA.
- **AC-9** `docker compose up` starts the full stack from a clean clone with zero manual steps.
- **AC-10** Small brand-colored text passes WCAG AA contrast (uses `#9c3614`, not raw `#e86020`).

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Criteo full dataset (~14M rows) too large/slow for laptop iteration | Use `percent10=True` subsample for development; full dataset only for the final reported run if feasible |
| Meta-learners disagree across datasets (no single "winner") | This is a legitimate, reportable finding — the thesis should discuss *why* (dataset size, treatment effect heterogeneity), not force a single answer |
| Committee unfamiliar with uplift-specific metrics | §14 Glossary and a short "why not accuracy/AUC" explainer must be embedded directly in the app's reporting view, not left to the thesis document alone |
| `scikit-uplift` dataset download fails in an offline build environment | Cache a small dataset snapshot in-repo as a fallback (see `02_SOFTWARE_SPEC.md` §4.2) |

---

## 12. Assumptions & Constraints

- Development and demo environment has internet access at least once to download datasets via `sklift`'s fetchers (cached afterward).
- No real customer data is used or required at any point.
- Single-developer build; architecture favors simplicity over horizontal scalability.

---

## 13. Out of Scope

- Live campaign execution (sending actual emails/SMS)
- CRM integration
- Multi-user auth / role-based access
- Non-randomized/observational causal inference (e.g., propensity score matching on non-experimental data) — out of scope for this thesis's identification strategy

---

## 14. Glossary

- **Uplift / CATE** — Conditional Average Treatment Effect: τ(x) = E[Y | X=x, T=1] − E[Y | X=x, T=0].
- **Meta-learner** — an uplift estimator built from standard ML models (S-, T-, X-, R-learner).
- **Qini coefficient / AUUC** — uplift-specific ranking-quality metrics; replace accuracy/AUC for this problem class.
- **Persuadable / Sure Thing / Lost Cause / Sleeping Dog** — the four uplift segments; only Persuadables justify targeting spend.
- **Fundamental problem of causal inference** — only one potential outcome per unit is ever observed; individual-level uplift is never directly measurable, so evaluation must be done at the group level on a randomized holdout.
- **Propensity model / response model** — a standard predictive model of P(outcome | treated), used here only as the deliberately naive baseline the uplift approach is benchmarked against.

---

*End of `01_REQUIREMENT_SPEC.md`*
