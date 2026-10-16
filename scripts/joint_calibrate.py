"""Fit physics and world together to the painted map while the physics stays
realistic on Earth.

Score (maximised) = the map's objective (zonefit by default)
                    - penalty * max(0, Earth climate distance - earth_max)
where the Earth climate distance is the mean over --regions (rotclimate.earth).
A candidate whose map score is already more than --race below the best so
far skips the Earth runs (it cannot win).

    python -I scripts/joint_calibrate.py --start calibration/world_e1_retro/best_params.json \
        --fix '{"retrograde": true}' --earth-max 2.25 --out calibration/joint_e1_retro
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

from rotclimate import calibrate as C  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from earth_calibrate import NUMERICS, SPACES  # noqa: E402

WORLD = [g for g in C.SPACE_WORLD if g[0] != "retrograde"]
SPACE = SPACES["e1"] + WORLD
_CASES = {}


def decode(x, base: Params) -> Params:
    lo = np.array([g[1] for g in SPACE]); hi = np.array([g[2] for g in SPACE])
    v = dict(zip([g[0] for g in SPACE], lo + np.clip(x, 0, 1) * (hi - lo)))
    t1 = v.pop("tier1"); t2 = t1 + v.pop("tier2_add"); t3 = t2 + v.pop("tier3_add"); t4 = t3 + v.pop("tier4_add")
    return base.replace(tier_tops=(round(t1), round(t2), round(t3), round(t4)), **{k: float(x) for k, x in v.items()})


def encode(p: Params):
    t = p.tier_tops
    v = {g[0]: getattr(p, g[0], None) for g in SPACE}
    v.update(tier1=t[0], tier2_add=t[1] - t[0], tier3_add=t[2] - t[1], tier4_add=t[3] - t[2])
    if "north_bearing" in v:
        v["north_bearing"] = (v["north_bearing"] + 180.0) % 360.0 - 180.0
    lo = np.array([g[1] for g in SPACE]); hi = np.array([g[2] for g in SPACE])
    return np.clip((np.array([v[g[0]] for g in SPACE], float) - lo) / (hi - lo), 0, 1)


def evaluate(args):
    x, base_dict, a, cutoff = args
    p = decode(np.asarray(x), Params(**base_dict))
    out = dict(params=asdict(p))
    t = time.time()
    try:
        m = C.evaluate_params(p, a["objective"])
        out["map"] = {k: m[k] for k in ("score", "mean", "accuracy", "per_class", "recall", "f1")}
        if cutoff is not None and m["score"] < cutoff:
            out.update(score=m["score"] - 1.0, raced=True)
            return out
        q = p.replace(**NUMERICS)
        d = {}
        for r in a["regions"]:
            if (r, a["cell_km"]) not in _CASES:
                _CASES[(r, a["cell_km"])] = earth.region_case(r, a["cell_km"])
            case = _CASES[(r, a["cell_km"])]
            d[r] = earth.climate_distance(earth.run_case(q, case, steps=q.steps_per_year), case)
        out["earth"] = d
        out["earth_mean"] = float(np.mean(list(d.values())))
        out["score"] = m["score"] - a["penalty"] * max(0.0, out["earth_mean"] - a["earth_max"])
    except Exception as e:
        out.update(score=-9.0, error=repr(e)[:300])
    out["seconds"] = round(time.time() - t, 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", required=True)
    ap.add_argument("--set", default='{"downsample": 16, "solver_rtol": 1e-5, "solver_require_convergence": false}')
    ap.add_argument("--fix", default='{"retrograde": true}', help="json of parameter values held fixed")
    ap.add_argument("--regions", nargs="+", default=["california", "iberia", "southeast_us", "levant",
                                                      "central_asia", "east_china"])
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--objective", default="zonefit")
    ap.add_argument("--earth-max", type=float, default=2.25)
    ap.add_argument("--penalty", type=float, default=1.0)
    ap.add_argument("--race", type=float, default=0.08)
    ap.add_argument("--bounds", default='{"hadley_edge":[28,34],"hadley_shift":[3,8],"itcz_mean":[2,8],'
                                        '"itcz_shift":[6,14],"trade_speed":[4,9],"westerly_speed":[4,12],'
                                        '"orographic":[0,10],"sst_offset":[-5,4]}')
    ap.add_argument("--evals", type=int, default=480)
    ap.add_argument("--popsize", type=int, default=16)
    ap.add_argument("--sigma", type=float, default=0.12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import cma

    global SPACE
    bounds = json.loads(a.bounds)
    SPACE = [(n, *bounds.get(n, (lo, hi))) for n, lo, hi in SPACE]
    d = json.loads(Path(a.start).read_text())
    d = d.get("params", d)
    base = Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__})
    base = base.replace(**json.loads(a.set)).replace(**json.loads(a.fix))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "space.json").write_text(json.dumps(dict(args=vars(a), space=SPACE), indent=1))
    log = (out / "evals.jsonl").open("a")
    cfg = dict(objective=a.objective, regions=a.regions, cell_km=a.cell_km, earth_max=a.earth_max, penalty=a.penalty)
    x0 = encode(base)
    es = cma.CMAEvolutionStrategy(x0, a.sigma, dict(bounds=[0, 1], popsize=a.popsize, seed=a.seed, verbose=-9))
    bd = asdict(base)
    t0 = time.time()

    def show(tag, r):
        m = r.get("map", {})
        return (f"{tag} score {r['score']:.4f} | map {a.objective} {m.get('score', float('nan')):.3f} strict "
                f"{m.get('accuracy', float('nan')):.1%} | Earth d {r.get('earth_mean', float('nan')):.3f} "
                + " ".join(f"{k[:5]} {v:.2f}" for k, v in r.get("earth", {}).items())
                + (f" | error {r['error']}" if "error" in r else ""))

    with mp.get_context("fork").Pool(a.workers) as pool:
        best = pool.map(evaluate, [(x0, bd, cfg, None)])[0]
        log.write(json.dumps(best) + "\n"); log.flush()
        print(show("start", best), flush=True)
        n = 1
        while n + a.popsize <= a.evals:
            xs = es.ask()
            cutoff = best["map"]["score"] - a.race if "map" in best else None
            res = pool.map(evaluate, [(x, bd, cfg, cutoff) for x in xs], chunksize=1)
            es.tell(xs, [-r["score"] for r in res])
            for r in res:
                log.write(json.dumps(r) + "\n")
                if r["score"] > best["score"]:
                    best = r
            log.flush(); n += len(xs)
            Path(out / "best_params.json").write_text(json.dumps(best["params"], indent=1))
            raced = sum(bool(r.get("raced")) for r in res)
            print(f"[{n:4d} evals, {raced:2d} raced, {time.time() - t0:5.0f}s] " + show("best", best)
                  + f" | per class {json.dumps({k: round(v, 2) for k, v in best['map']['per_class'].items()})}",
                  flush=True)


if __name__ == "__main__":
    main()
