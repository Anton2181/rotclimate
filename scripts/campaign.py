"""Restart campaign against local optima: several independent CMA-ES runs
with large steps from deliberately different starting points, run one after
another (each resumable, so the whole campaign resumes after an interruption).

    python -I scripts/campaign.py --plan calibration/campaign/plan.json

The plan is a JSON list of runs: {"name", "start", "args": [extra
calibrate_cli arguments]}; common arguments go in {"common": [...]} (plan as
an object {"common": [...], "runs": [...]}). A run that finished leaves
<out>/done and is skipped. Random worlds can be generated into start files
with --make-random N --from <params> (world genes drawn uniformly from the
search bounds; physics kept).
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLD_RANGES = {"lat_center": (26.0, 44.0), "tilt": (14.0, 34.0), "north_bearing": (-45.0, 45.0),
                "beyond_north_land": (0.0, 1.0), "beyond_south_land": (0.0, 1.0), "beyond_west_land": (0.0, 1.0),
                "beyond_east_land": (0.0, 1.0), "beyond_southeast_land": (0.0, 1.0),
                "beyond_northeast_land": (0.0, 1.0), "beyond_continuity_km": (100.0, 900.0),
                "beyond_relief_m": (0.0, 1500.0)}


def make_random(src: Path, n: int, outdir: Path, seed: int):
    d = json.loads(src.read_text())
    d = d.get("params", d)
    rng = random.Random(seed)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(n):
        p = dict(d)
        for k, (lo, hi) in WORLD_RANGES.items():
            p[k] = rng.uniform(lo, hi)
        p["retrograde"] = rng.random() < 0.5
        path = outdir / f"random_world_{seed}_{i}.json"
        path.write_text(json.dumps(p, indent=1))
        paths.append(path)
        print(path, {k: round(p[k], 2) for k in ("lat_center", "tilt", "north_bearing")}, "retro" if p["retrograde"] else "pro")
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan")
    ap.add_argument("--make-random", type=int, default=0)
    ap.add_argument("--from", dest="src")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--starts-dir", default="calibration/campaign/starts")
    a = ap.parse_args()
    if a.make_random:
        make_random(Path(a.src), a.make_random, Path(a.starts_dir), a.seed)
        return
    plan = json.loads(Path(a.plan).read_text())
    common, runs = plan.get("common", []), plan["runs"]
    for run in runs:
        out = Path(run["out"])
        if (out / "done").exists():
            print(f"[campaign] {run['name']}: done, skipped", flush=True)
            continue
        cmd = [sys.executable, "-I", str(ROOT / "scripts" / "calibrate_cli.py"), "--resume", "--start", run["start"],
               "--out", str(out)] + common + run.get("args", [])
        print(f"[campaign] {run['name']}: {' '.join(cmd[2:])}", flush=True)
        out.mkdir(parents=True, exist_ok=True)
        with (out / "run.log").open("a") as log:
            code = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
        if code != 0:
            print(f"[campaign] {run['name']}: exit {code}, stopping", flush=True)
            sys.exit(code)
        (out / "done").write_text("ok\n")
        best = json.loads((out / "best_params.json").read_text())
        lines = [l for l in (out / "run.log").read_text().splitlines() if l.startswith("[")]
        print(f"[campaign] {run['name']}: finished | {lines[-1][:160] if lines else ''}", flush=True)


if __name__ == "__main__":
    main()
