"""Command line entry point.

    python -m rotclimate render  --params calibration/best_params.json
    python -m rotclimate calibrate --out calibration/run --evals 600
    python -m rotclimate score   --params calibration/best_params.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from .config import OUTPUT, Params

CLIMOGRAPH_CITIES = [
    "Sam'al", "Harran", "Urrann", "Paraman", "Kadā", "Zakuruiði", "Iasos", "Nasios",
    "Gaietai", "Ilun", "Ordin", "Yasna", "Cašman", "Argos", "Tegea", "Kullanos",
    "Sabate", "Lakui", "Arsakos", "Gulussa", "Bahir Dar", "Gambela", "Bulut", "Yashil",
]


def simulate(params: Params, quiet=False):
    from .model import ClimateModel

    t = time.time()
    m = ClimateModel(params)

    def prog(i, n):
        if not quiet and (i % 10 == 0 or i == n):
            print(f"\r  week {i}/{n}", end="", flush=True)

    r = m.run(progress=prog)
    if not quiet:
        print(f"\r  simulated {r.nt} steps on {m.g.ny}x{m.g.nx} cells in {time.time() - t:.0f}s")
    return r


def cmd_score(a):
    from .score import evaluate, format_report

    p = Params.from_json(a.params) if a.params else Params()
    if a.downsample:
        p = p.replace(downsample=a.downsample)
    if a.steps:
        p = p.replace(steps_per_year=a.steps)
    r = simulate(p)
    ev = evaluate(r)
    print(format_report(ev))


def cmd_render(a):
    from . import render as R
    from .score import evaluate

    p = Params.from_json(a.params) if a.params else Params()
    p = p.replace(downsample=a.downsample, steps_per_year=a.steps, picard_iters=3)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    r = simulate(p)
    ev = evaluate(r)
    fr = R.FullRes(r)
    t = time.time()
    k = fr.koppen()
    mem = R.fullres_memberships(fr)
    print(f"  full-resolution Köppen in {time.time() - t:.0f}s")
    spin = "retrograde" if p.retrograde else "prograde"
    sub = f"(map centre {p.lat_center:.1f}°N, axial tilt {p.tilt:.1f}°, {spin} spin)"
    R.koppen_map(fr, out / "koppen.png", f"Köppen-Geiger climates  {sub}")
    R.comparison_map(fr, mem, out / "comparison.png",
                     f"Target vs simulation — score {ev['total']:.2f}, zone accuracy {ev['accuracy']:.0%}")
    ix = fr._ix
    R.field_map(fr, ix["MAT"], out / "temperature_annual.png", "Mean annual temperature",
                "turbo", -10, 30, "°C", levels=np.arange(-12, 32, 2))
    R.field_map(fr, ix["Tcold"], out / "temperature_coldest.png", "Coldest month mean temperature",
                "turbo", -25, 25, "°C", levels=np.arange(-26, 28, 2))
    R.field_map(fr, ix["Thot"], out / "temperature_warmest.png", "Warmest month mean temperature",
                "turbo", 0, 40, "°C", levels=np.arange(0, 42, 2))
    R.field_map(fr, ix["MAP"], out / "precipitation_annual.png", "Annual precipitation",
                "YlGnBu", 0, 2500, "mm / year",
                levels=[0, 100, 200, 300, 400, 500, 650, 800, 1000, 1250, 1500, 2000, 2500, 3000],
                extend="max")
    R.monthly_atlas(fr, out / "atlas_temperature.png", "T")
    R.monthly_atlas(fr, out / "atlas_precipitation.png", "P")
    R.climographs(fr, CLIMOGRAPH_CITIES, out / "climographs.png")
    R.insolation_chart(p, out / "insolation.png")
    R.context_map(r, out / "world_context.png")
    if not a.no_gif:
        t = time.time()
        R.season_gif(fr, out / "year_temperature.gif", "T", stride=a.gif_stride)
        R.season_gif(fr, out / "year_precipitation.gif", "P", stride=a.gif_stride)
        print(f"  gifs in {time.time() - t:.0f}s")
    summary = dict(score=ev["total"], accuracy=ev["accuracy"], per_class=ev["per_class"],
                   koppen_share={})
    from .koppen import CODES

    vals, counts = np.unique(k[fr.land], return_counts=True)
    for v, c in zip(vals, counts):
        if v >= 0:
            summary["koppen_share"][CODES[v]] = round(float(c / fr.land.sum()), 4)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    if a.atlas:
        from .atlas import build

        build(r, fr, ev)
    p.to_json(out / "params.json")
    print(json.dumps(summary["per_class"], indent=1), summary["score"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rotclimate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("render", help="simulate and draw every map / gif / chart")
    s.add_argument("--params", default=None)
    s.add_argument("--out", default=str(OUTPUT))
    s.add_argument("--downsample", type=int, default=4)
    s.add_argument("--steps", type=int, default=73)
    s.add_argument("--gif-stride", type=int, default=1)
    s.add_argument("--no-gif", action="store_true")
    s.add_argument("--atlas", action="store_true", help="also export the atlas data")
    s.set_defaults(func=cmd_render)
    s = sub.add_parser("score", help="simulate and print the target score")
    s.add_argument("--params", default=None)
    s.add_argument("--downsample", type=int, default=None)
    s.add_argument("--steps", type=int, default=None)
    s.set_defaults(func=cmd_score)
    s = sub.add_parser("calibrate", help="search parameters (see calibrate.py)")
    s.set_defaults(func=None)
    a, rest = ap.parse_known_args(argv)
    if a.cmd == "calibrate":
        from .calibrate import main as cmain

        sys.argv = [sys.argv[0]] + rest
        return cmain()
    a.func(a)


if __name__ == "__main__":
    main()
