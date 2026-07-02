# 00 — Handoff Guide (Read This First)

**Project:** UpliftIQ — Incremental Targeting Decision Engine
**Purpose of this file:** a manual for whoever opens this folder next — an AI coding agent, a human developer, or the thesis advisor — so they know what exists, in what order to read it, and how to get the system running without asking the author anything.

---

## 1. What is UpliftIQ, in one paragraph

UpliftIQ answers a different question than a normal predictive model. Instead of "who is likely to buy," it answers **"who will buy *because* we targeted them, and who would have bought anyway (or gets annoyed if we do)."** This is causal uplift modeling. The system benchmarks four meta-learner approaches on real randomized-experiment marketing datasets, ranks customers by estimated incremental effect (not raw probability), and — under a fixed campaign budget — decides who to target to maximize incremental profit. The thesis's headline result is a quantified profit gap between uplift-based targeting and traditional propensity-based targeting, evaluated with uplift-specific metrics (Qini, AUUC) rather than accuracy/AUC.

---

## 2. What's in this package

| File | What it defines | Read it if you are... |
|---|---|---|
| `UpliftIQ_00_HANDOFF_GUIDE.md` | This file — orientation and quick start | Everyone, first |
| `UpliftIQ_01_REQUIREMENT_SPEC.md` | **What** to build and **why** (business/product requirements, acceptance criteria) | Advisor, reviewer, or anyone validating scope |
| `UpliftIQ_02_SOFTWARE_SPEC.md` | **How** to build it (architecture, APIs, data pipeline, design system, deployment) | An AI coding agent or developer, before writing any code |

Build order: read `01` fully once for context → keep `02` open as the working reference while implementing → come back to `01` §10 (Acceptance Criteria) to self-check before calling a milestone done.

---

## 3. Quick facts

| | |
|---|---|
| **Thesis core** | Causal inference / uplift modeling (meta-learners + Qini/AUUC evaluation) |
| **Data** | 100% public datasets, no access request needed |
| **Primary datasets** | Hillstrom MineThatData, Criteo Uplift v2.1, Lenta, X5 RetailHero (all via `scikit-uplift`) |
| **Backend** | Python 3.11+, FastAPI, `scikit-uplift`, `causalml` or `econml` |
| **Frontend** | Next.js 14+ (App Router), TypeScript, MUI v6+, MUI X Charts, MUI X DataGrid |
| **Deployment** | Docker Compose, 2 services (model-service + web) |
| **Design language** | Gemini-inspired, mobile-first PWA, primary color `#e86020` |
| **Never do** | Report accuracy or AUC as the headline metric — uplift can't be validated that way (see Glossary) |

---

## 4. Getting started (for an AI coding agent picking this up cold)

```bash
# 1. Scaffold the repo per 02_SOFTWARE_SPEC.md §3 (Repository Structure)
# 2. Model service
cd model-service
python -m venv .venv && source .venv/bin/activate
pip install scikit-uplift causalml fastapi uvicorn pandas scikit-learn
python -c "from sklift.datasets import fetch_hillstrom; print(fetch_hillstrom().data.shape)"  # sanity check: downloads dataset

# 3. Frontend
cd ../web
npm install
npm run dev

# 4. Full stack
docker compose up --build
```

If `fetch_hillstrom()` fails to download (no internet in the build sandbox), fall back to a bundled CSV snapshot — see `02_SOFTWARE_SPEC.md` §4.2.

---

## 5. Non-negotiable decisions (don't relitigate these)

1. **Metric discipline.** Every evaluation surface (API response, chart, exported report) must lead with Qini coefficient / AUUC. Accuracy or AUC may appear only as a labeled secondary diagnostic, never as *the* result.
2. **Reproducibility.** All train/holdout splits and model fits must be seeded and logged. The benchmark must be re-runnable and produce the same ranking of meta-learners.
3. **Design system.** MUI only — do not introduce Tailwind (avoids styling-system conflicts established during spec review). Primary `#e86020` is for large surfaces/accents only; small body text on white must use the darkened `#9c3614` (the base color fails WCAG AA at ~3.2:1 contrast for small text).
4. **Typography.** "Google Sans" is proprietary and not distributable via Google Fonts. Use the declared fallback stack (`Roboto, Inter, "Noto Sans Thai", sans-serif`) — do not attempt to embed Google Sans itself.
5. **Two services, not one.** The Next.js app must not try to run the uplift models itself (they're Python-native artifacts). FastAPI is the only model-serving layer.

---

## 6. Glossary (quick reference — full version in `01_REQUIREMENT_SPEC.md` §14)

- **Uplift / CATE** — Conditional Average Treatment Effect: the causal effect of treatment for a given customer profile.
- **Meta-learner** — an uplift estimator built on top of standard ML models (S-, T-, X-learner, causal forest).
- **Qini coefficient / AUUC** — uplift-specific ranking-quality metrics; the correct replacement for accuracy/AUC in this problem class.
- **Persuadable / Sure Thing / Lost Cause / Sleeping Dog** — the four customer uplift segments; only Persuadables are worth targeting.

---

## 7. Pre-flight checklist before declaring "done"

- [ ] Benchmark reproduces the same meta-learner ranking on a re-run with the same seed
- [ ] Qini curve and AUUC are the primary reported numbers everywhere (UI, exports, docs)
- [ ] Budget-constrained decision layer respects the budget as a hard constraint, not a soft suggestion
- [ ] CSV export is UTF-8 with BOM (Thai/Excel compatibility)
- [ ] App installs as a PWA on mobile
- [ ] `docker compose up` is a genuine one-command demo from a clean clone
- [ ] Small text never renders in raw `#e86020` on a white background
