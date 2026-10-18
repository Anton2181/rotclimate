"""Build a separate atlas for one parameter set, beside the live one.

Simulates the map, writes the atlas data, the year animations and a copy of
the atlas page (with its own heading, and without the live atlas's experiment
gallery, which belongs to other fits) into atlases/<name>/. The live atlas in
atlas/ is not touched.

    python -I scripts/build_atlas_variant.py --params calibration/earth/joint_e1_retro.json \
        --name earth_joint --title "Rotclimate Atlas: Earth-tested physics" \
        --eyebrow "Physics fitted on real climates" --downsample 8
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rotclimate.config import Params  # noqa: E402


def load(path):
    d = json.loads(Path(path).read_text())
    d = d.get("params", d)
    return Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__})


def page(src: str, title: str, eyebrow: str, lede: str, note: str) -> str:
    html = src.replace("<title>Rotclimate Atlas</title>", f"<title>{title}</title>", 1)
    html = html.replace("<h1>Rotclimate Atlas</h1>", f"<h1>{title}</h1>", 1)
    html = re.sub(r'<span class="eyebrow">[^<]*</span>', f'<span class="eyebrow">{eyebrow}</span>', html, count=1)
    html = re.sub(r'<p class="lede">[^<]*</p>', f'<p class="lede">{lede}</p><p class="lede">{note}</p>', html,
                  count=1)
    # the experiments gallery shows other fits' animations: leave it to the live atlas
    html = re.sub(r'\s*<section>\s*<div class="section-head">\s*<h2>Experiments</h2>.*?</section>', "", html,
                  count=1, flags=re.S)
    return html


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--eyebrow", required=True)
    ap.add_argument("--lede", default="Click anywhere on land to see its climate through the local year, "
                                      "and which real places feel most alike.")
    ap.add_argument("--note", default="")
    ap.add_argument("--downsample", type=int, default=8)
    ap.add_argument("--set", default='{"solver_rtol": 1e-6, "solver_require_convergence": false}')
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--seeds", default="", help="comma list of surroundings layouts to average (ensemble climate)")
    ap.add_argument("--workers", type=int, default=1, help="parallel runs for --seeds")
    a = ap.parse_args()
    from rotclimate import render as R
    from rotclimate.__main__ import simulate
    from rotclimate.atlas import build
    from rotclimate.score import evaluate, objective

    p = load(a.params).replace(downsample=a.downsample, **json.loads(a.set))
    out = ROOT / "atlases" / a.name
    data = out / "data"
    data.mkdir(parents=True, exist_ok=True)
    t = time.time()
    seeds = [int(x) for x in a.seeds.split(",") if x.strip()]
    if seeds:
        from rotclimate.model import run_ensemble
        r = run_ensemble(p, seeds, workers=a.workers)
    else:
        r = simulate(p)
    ev = evaluate(r)
    fr = R.FullRes(r)
    build(r, fr, ev, outdir=data)
    if not a.no_gif:
        R.season_gif(fr, data / "year_temperature.gif", "T")
        R.season_gif(fr, data / "year_precipitation.gif", "P")
        R.season_gif(fr, data / "year_vapour.gif", "W")
        R.season_gif(fr, data / "year_growing.gif", "G")
    # around the map: the invented land and sea the model adds on every side (one
    # layout: an average over layouts mixes different coastlines out there)
    if p.beyond_style == "procedural":
        rr = simulate(p.replace(beyond_seed=seeds[0], downsample=max(16, a.downsample))) if seeds else r
        R.around_koppen(rr, data / "around_koppen.webp")
        if not a.no_gif:
            R.around_gif(rr, data / "around_year.gif")
        meta = json.loads((data / "atlas.json").read_text())
        note = (f"Nobody drew the world beyond the map, so the model invents {p.pad_km:,.0f} km of land and sea on "
                "every side. How much of each side is land was fitted along with the climate; the coastlines "
                "themselves are random, so this is one plausible neighbourhood, not a fact about the world.")
        if seeds:
            note += (f" The map above averages {len(seeds)} random layouts of it; these pictures show layout "
                     f"{seeds[0]}.")
        meta["around"] = dict(note=note, layout=seeds[0] if seeds else p.beyond_seed, averaged=len(seeds))
        (data / "atlas.json").write_text(json.dumps(meta, ensure_ascii=False))
    src = (ROOT / "atlas" / "index.html").read_text()
    (out / "index.html").write_text(page(src, a.title, a.eyebrow, a.lede, a.note))
    shutil.copy(ROOT / "atlas" / "climate-comparison.js", out / "climate-comparison.js")
    p.to_json(out / "params.json")
    codes = __import__("rotclimate.koppen", fromlist=["CODES"]).CODES
    import numpy as np
    from rotclimate.koppen import classify
    st = ev["monthly"]
    g = r.grid
    kop = np.array(codes)[classify(st["Tm"], st["Pm"], st["summer"])]
    med = g.inmap & g.land & (g.target == 4)
    summary = dict(params=a.params, downsample=a.downsample, seeds=seeds or None, seconds=round(time.time() - t),
                   strict_accuracy=ev["accuracy"], zonefit=objective(ev, "zonefit"),
                   recall={k: float(v) for k, v in ev["recall"].items()},
                   mediterranean=dict(dry_share=float(np.char.startswith(kop[med], "B").mean()),
                                      cs_share=float(np.char.startswith(kop[med], "Cs").mean())))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    print("atlas written to", out)


if __name__ == "__main__":
    main()
