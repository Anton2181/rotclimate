"""Does a setting restore the rain contrast between a region's cities?

    python3 -I scripts/probe_city_contrast.py --fit calibration/local_accuracy_20261023/r36_params.json \
        --variants '{"base": {}, "lee0.5": {"lee_drying": 0.5}}' --regions levant iberia japan \
        --out output/contrast_probe

Runs scripts/benchmark_local.py on the regions for each variant, then for
every region with 20+ cities reports the slope of the cities' modelled
against observed annual rain (log, as scripts/city_rain.py: 1 = the model
spreads wet and dry places as far apart as they are), the cities' log RMSE
and the region's rainfall loss. A probe, not a gate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from city_rain import cities, match  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", required=True)
    ap.add_argument("--variants", required=True, help="json {name: overrides}")
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    towns = cities()
    table = {}
    for name, over in json.loads(a.variants).items():
        out = a.out / name
        if not (out / "summary.json").exists():
            subprocess.run([sys.executable, "-I", str(ROOT / "scripts/benchmark_local.py"), "--fit", a.fit, "--set", json.dumps(over),
                            "--regions", *a.regions, "--out", str(out)], check=True, stdout=subprocess.DEVNULL)
        regions = json.loads((out / "summary.json").read_text())["regions"]
        rows = match(out, towns)
        res = {}
        for g in a.regions:
            rr = [r for r in rows if r["region"] == g]
            o = np.log(np.array([r["obs"].sum() for r in rr]) + 50); s = np.log(np.array([r["sim"].sum() for r in rr]) + 50)
            slope = float(np.polyfit(o, s, 1)[0]) if len(rr) >= 20 else float("nan")
            res[g] = dict(cities=len(rr), slope=slope, city_log_rmse=float(np.sqrt(np.mean((s - o) ** 2))) if rr else float("nan"),
                          loss=regions[g]["rain"]["loss"], T=regions[g]["temperature"]["monthly_mae_C"])
        table[name] = res
        print(f"{name:14s} " + " | ".join(f"{g[:10]} {v['slope']:+.2f} {v['city_log_rmse']:.2f} L{v['loss']:.3f}" for g, v in res.items()), flush=True)
    (a.out / "probe.json").write_text(json.dumps(table, indent=1))


if __name__ == "__main__":
    main()
