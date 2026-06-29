"""One-command, seeded train-plane orchestrator (NFR-4, FR-D3).

    python -m pipeline.run --dataset hillstrom --seed 42

Stages (§10.1): load ▸ balance ▸ split ▸ train S/T/X/R ▸ evaluate
(Qini/AUUC/decile/calibration) ▸ select best ▸ build score table + segments ▸
decision benchmark ▸ persist (Parquet + optional Supabase) ▸ write report.
"""
from __future__ import annotations

import argparse
import json
import pickle
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config, decision, evaluate, supabase_store
from .balance import balance_report, balance_summary
from .data import load_dataset
from .models import LEARNERS, BaseRateModel, build_learner
from .report import write_report

DEFAULT_LEARNERS = ["s_learner", "t_learner", "x_learner", "r_learner"]


def _split(b, seed: int):
    idx = np.arange(b.n)
    tr, ho = train_test_split(
        idx, test_size=0.3, random_state=seed, stratify=b.treatment.to_numpy()
    )
    return tr, ho


def run(dataset: str = None, seed: int = None, learners: list[str] = None) -> dict:
    dataset = dataset or config.DEFAULT_DATASET
    seed = seed if seed is not None else config.SEED
    learners = learners or DEFAULT_LEARNERS
    np.random.seed(seed)
    t0 = time.time()

    print(f"━━ UpliftIQ pipeline · dataset={dataset} · seed={seed} ━━")

    # 1. Load + normalise.
    b = load_dataset(dataset, seed=seed)
    print(f"[load] {b.name}: {b.n:,} rows · {len(b.feature_names)} features")

    # 2. Balance check (FR-A2).
    bal = balance_summary(b)
    print(f"[balance] max|SMD|={bal['max_abs_smd']:.3f} flagged={bal['n_flagged']} "
          f"passed={bal['passed']}")

    # 3. Split (stratified by treatment).
    tr, ho = _split(b, seed)
    Xtr, Xho = b.X.iloc[tr], b.X.iloc[ho]
    Ttr, Tho = b.treatment.iloc[tr].to_numpy(), b.treatment.iloc[ho].to_numpy()
    Ytr, Yho = b.outcome.iloc[tr].to_numpy(), b.outcome.iloc[ho].to_numpy()
    print(f"[split] train={len(tr):,} holdout={len(ho):,}")

    # 4–5. Train + evaluate each learner on the holdout.
    results, fitted = {}, {}
    for name in learners:
        m = build_learner(name, seed=seed).fit(Xtr, Ttr, Ytr)
        up_ho = m.predict_uplift(Xho)
        ev = evaluate.evaluate_model(Yho, up_ho, Tho)
        results[name] = ev
        fitted[name] = (m, up_ho)
        mt = ev["metrics"]
        print(f"[eval] {name:11s} qini={mt['qini']:.4f} auuc={mt['auuc']:.4f} "
              f"ranks_ok={mt['ranks_correctly']}")

    # 6. Select best by Qini (AUUC tie-break).
    best = max(results, key=lambda k: (results[k]["metrics"]["qini"],
                                       results[k]["metrics"]["auuc"]))
    print(f"[select] best={best}")
    best_model, best_uplift = fitted[best]

    # Base-rate model (propensity to convert) for baseline + segments.
    base_model = BaseRateModel(seed=seed).fit(Xtr, Ytr)
    base_rate_ho = base_model.predict(Xho)

    # Persist best uplift model + base-rate model + serving metadata.
    with open(config.model_path(dataset, best), "wb") as f:
        pickle.dump(best_model, f)
    with open(config.model_path(dataset, "base_rate"), "wb") as f:
        pickle.dump(base_model, f)
    meta = {"dataset": dataset, "best_learner": best, "feature_names": b.feature_names,
            "segment_thresholds": decision.segment_thresholds(best_uplift, base_rate_ho)}
    with open(config.model_path(dataset, "meta").with_suffix(".json"), "w") as f:
        json.dump(meta, f, indent=2)

    # 7. Build score table on the randomized holdout (id, uplift, segment, ...).
    seg_th = decision.segment_thresholds(best_uplift, base_rate_ho)
    segments = decision.assign_segments(best_uplift, base_rate_ho, **seg_th)
    scores = pd.DataFrame(
        {
            "id": np.arange(len(ho)),
            "uplift": best_uplift,
            "base_rate": base_rate_ho,
            "segment": segments,
            "T": Tho,
            "Y": Yho,
            "value": b.outcome_value.iloc[ho].to_numpy(),
        }
    )
    scores.to_parquet(config.scores_path(dataset), index=False)
    print(f"[scores] wrote {config.scores_path(dataset)} ({len(scores):,} rows)")
    pushed = supabase_store.push_scores(scores, dataset)
    print(f"[supabase] {'pushed' if pushed else 'skipped (local Parquet only)'}")

    # 8. Decision benchmark (FR-B / AC-3) — default cost/value assumptions.
    cost, value = 0.10, 10.0
    policies = decision.build_policies(scores)
    sweep = decision.profit_sweep(scores, cost, value, policies=policies)
    demo_budget = int(0.3 * policies["n"])
    headline = decision.simulate(scores, demo_budget, cost, value, policies)
    print(f"[decision] @budget={demo_budget:,}: uplift_profit={headline['uplift']['incremental_profit']:.1f} "
          f"vs propensity={headline['propensity']['incremental_profit']:.1f} "
          f"→ lift={headline['profit_lift_vs_propensity']:.1f}")

    # 9. Assemble metrics + qini points for the best model.
    qini_pts = evaluate.qini_points(Yho, best_uplift, Tho)

    metrics_json = {
        "dataset": dataset,
        "seed": seed,
        "n_rows": int(b.n),
        "n_holdout": int(len(ho)),
        "balance": bal,
        "best_learner": best,
        "learners": {k: results[k]["metrics"] for k in results},
        "decision_demo": {
            "budget": demo_budget,
            "cost_per_contact": cost,
            "value_per_conversion": value,
            **{k: headline[k] for k in
               ("uplift", "propensity", "random",
                "profit_lift_vs_propensity", "profit_lift_vs_random")},
        },
        "why_not_accuracy": evaluate.WHY_NOT_ACCURACY,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    rep_dir = config.report_dir(dataset)
    with open(rep_dir / "metrics.json", "w") as f:
        json.dump(metrics_json, f, indent=2)

    # 10. Report (markdown + figures).
    write_report(
        dataset=dataset,
        metrics=metrics_json,
        balance_df=balance_report(b),
        deciles=results[best]["deciles"],
        calibration=results[best]["calibration"],
        qini_points=qini_pts,
        sweep=sweep,
    )
    print(f"[report] wrote {rep_dir/'report.md'}  (elapsed {metrics_json['elapsed_sec']}s)")
    return metrics_json


def main():
    ap = argparse.ArgumentParser(description="UpliftIQ seeded train pipeline")
    ap.add_argument("--dataset", default=config.DEFAULT_DATASET,
                    help="hillstrom | criteo | synthetic")
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--learners", nargs="*", default=DEFAULT_LEARNERS,
                    choices=list(LEARNERS))
    args = ap.parse_args()
    run(dataset=args.dataset, seed=args.seed, learners=args.learners)


if __name__ == "__main__":
    main()
