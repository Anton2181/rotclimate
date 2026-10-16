"""Re-score each spin's calibration finalists on worlds the search never saw.

A best-of-hundreds score on the three calibration worlds is inflated (the
winner's curse), so the spin comparison is judged here instead:

* finalists: the top K distinct, fully scored candidates of each run
* worlds: fresh procedural surroundings (seeds 101 ...), the same for both
* objective: computed, as in calibration, from zone metrics averaged over
  the worlds; its uncertainty from a paired bootstrap over worlds
* a gap inside +-TIE (declared before looking) is reported as a tie

    python scripts/spin_rematch.py calibration/r16_retrograde calibration/r16_prograde \
        --k 3 --worlds 60 --out calibration/r16_rematch.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

from rotclimate.calibrate import evaluate_params  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.score import objective  # noqa: E402

TIE = 0.01
FIRST_SEED = 101


def finalists(run: Path, k: int) -> list[dict]:
    rows = [json.loads(line) for line in (run / "evals.jsonl").open()]
    rows = [r for r in rows if not r.get("raced") and r.get("score", -1) > 0]
    rows.sort(key=lambda r: -r["score"])
    out, seen = [], []
    for r in rows:
        v = np.array([x for x in r["params"].values() if isinstance(x, (int, float))], float)
        if any(np.allclose(v, s, rtol=1e-6) for s in seen):
            continue
        seen.append(v)
        out.append(r)
        if len(out) == k:
            break
    return out


MODE = "f1"


def _init_worker(mode):
    global MODE
    MODE = mode


def unique_candidates(cands):
    """Evaluate identical physical/numerical configurations once per world."""
    unique, aliases, seen = {}, {}, {}
    for label, row in cands.items():
        # Every job explicitly overrides this seed before simulation.
        params = {k: v for k, v in row['params'].items() if k != 'beyond_seed'}
        key = json.dumps(params, sort_keys=True)
        if key not in seen:
            seen[key] = label
            unique[label] = row
            aliases[label] = []
        aliases[seen[key]].append(label)
    return unique, aliases


def _job(a):
    started = time.monotonic()
    label, params, seed = a
    p = Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in params.items()})
    r = evaluate_params(p, MODE, [seed])
    return label, seed, dict(f1=r["f1"], per_class=r["per_class"], realism=r["realism"],
                             recall=r["recall"], display_accuracy=r["display_accuracy"],
                             acc=r["accuracy"], score=r["score"], seconds=time.monotonic() - started)


def obj(rows, mode=None):
    ev = {key: {k: float(np.mean([r[key][k] for r in rows])) for k in rows[0][key]}
          for key in (("f1", "per_class", "realism", "recall")
                      if (mode or MODE) == "zonefit" else ("f1", "per_class", "realism"))}
    return objective(ev, mode or MODE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs=2, help="retrograde run dir, Earth-like run dir")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--worlds", type=int, default=60)
    ap.add_argument("--first-seed", type=int, default=FIRST_SEED)
    ap.add_argument("--baseline-params", nargs=2, metavar=("RETROGRADE", "EARTHLIKE"),
                    help="also evaluate the unchanged starting worlds on the same held-out seeds")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="")
    ap.add_argument("--plan", action="store_true", help="inspect candidate/world counts without simulating")
    ap.add_argument("--objective", default="f1", choices=["f1", "f1r", "zonefit"])
    a = ap.parse_args()
    global MODE
    MODE = a.objective
    if a.worlds < 1 or a.k < 1:
        ap.error("worlds and k must be positive")
    seeds = list(range(a.first_seed, a.first_seed + a.worlds))
    cands = {}
    for spin, run in zip(("retrograde", "earthlike"), a.runs):
        for i, r in enumerate(finalists(Path(run), a.k)):
            cands[f"{spin}#{i + 1}"] = r
        if f"{spin}#1" not in cands:
            ap.error(f"No successful fully evaluated candidates in {run}")
    if a.baseline_params:
        from dataclasses import asdict
        for spin, path in zip(("retrograde", "earthlike"), a.baseline_params):
            cands[f"{spin}-baseline"] = dict(params=asdict(Params.from_json(path)), score=None)
    unique, aliases = unique_candidates(cands)
    jobs = [(lab, r["params"], s) for s in seeds for lab, r in unique.items()]
    print(f"{len(cands)} candidate labels; {len(unique)} unique fits × {len(seeds)} worlds "
          f"= {len(jobs)} simulations", flush=True)
    if a.plan:
        return
    per = {lab: {} for lab in cands}
    progress = Path(a.out).with_suffix('.progress.jsonl').open('w') if a.out else None
    started = time.monotonic()
    try:
        with mp.get_context("spawn").Pool(a.workers, initializer=_init_worker, initargs=(MODE,)) as pool:
            for done, (lab, s, r) in enumerate(pool.imap_unordered(_job, jobs, chunksize=1), 1):
                for alias in aliases[lab]:
                    per[alias][s] = r
                if progress:
                    progress.write(json.dumps(dict(candidate=lab, aliases=aliases[lab], seed=s, result=r)) + '\n')
                    progress.flush()
                print(f"[{done}/{len(jobs)} completed, {(time.monotonic() - started) / 60:.1f} min] "
                      f"{lab}, world {s}: correct {r['acc']:.1%}, took {r['seconds'] / 60:.1f} min", flush=True)
    finally:
        if progress:
            progress.close()
    summary = {}
    for lab, r in cands.items():
        rows = [per[lab][s] for s in seeds]
        summary[lab] = dict(calibration_score=r["score"], fresh_objective=obj(rows), fresh_f1_objective=obj(rows, "f1"),
                            fresh_wet_summer_hot=float(np.mean([x["realism"]["wet_summer_hot"] for x in rows])),
                            fresh_correct=float(np.mean([x["acc"] for x in rows])),
                            fresh_display_correct=float(np.mean([x["display_accuracy"] for x in rows])),
                            fresh_recall={k: float(np.mean([x["recall"][k] for x in rows])) for k in rows[0]["recall"]},
                            fresh_macro_recall=float(np.nanmean([v for x in rows for v in x["recall"].values()])),
                            fresh_f1={k: float(np.mean([x["f1"][k] for x in rows])) for k in rows[0]["f1"]})
        training = f"{r['score']:.4f}" if r['score'] is not None else "baseline"
        print(f"{lab:13s} calibration {training}  fresh objective {summary[lab]['fresh_objective']:.4f}  "
              f"(zones only {summary[lab]['fresh_f1_objective']:.4f})  correct {summary[lab]['fresh_correct']:.3f}  "
              f"hot wet summers {summary[lab]['fresh_wet_summer_hot']:.2f}")
    # each spin is represented by its calibration best (#1), declared in advance
    R = [per["retrograde#1"][s] for s in seeds]
    E = [per["earthlike#1"][s] for s in seeds]
    gap = obj(R) - obj(E)
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(2000):
        ii = rng.integers(0, len(seeds), len(seeds))
        boot.append(obj([R[i] for i in ii]) - obj([E[i] for i in ii]))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    dacc = np.array([r["acc"] - e["acc"] for r, e in zip(R, E)])
    wins = int((dacc > 0).sum())
    verdict = ("tie" if lo > -TIE and hi < TIE else
               "retrograde ahead" if lo > 0 else "Earth-like ahead" if hi < 0 else "undecided")
    print(f"objective gap (retrograde - Earth-like) {gap:+.4f}, 95% interval {lo:+.4f} to {hi:+.4f} "
          f"(tie band +-{TIE}): {verdict}")
    print(f"painted land correct: {np.mean([r['acc'] for r in R]):.3f} vs {np.mean([e['acc'] for e in E]):.3f}, "
          f"retrograde ahead on {wins} of {len(seeds)} worlds")
    improvement = {}
    if a.baseline_params:
        for spin in ("retrograde", "earthlike"):
            winner, baseline = summary[f"{spin}#1"], summary[f"{spin}-baseline"]
            improvement[spin] = {key: winner[key] - baseline[key] for key in
                                 ("fresh_objective", "fresh_correct", "fresh_display_correct", "fresh_macro_recall")}
            print(f"{spin} changes versus unchanged start: {improvement[spin]}")
    if a.out:
        Path(a.out).write_text(json.dumps(dict(
            objective=a.objective, seeds=seeds, tie_band=TIE, gap=gap, interval=[float(lo), float(hi)], verdict=verdict,
            baseline_improvement=improvement,
            correct_gap=float(dacc.mean()), correct_wins=wins, finalists=summary,
            per_world={lab: {str(s): per[lab][s] for s in seeds} for lab in cands}), indent=1))


if __name__ == "__main__":
    main()
