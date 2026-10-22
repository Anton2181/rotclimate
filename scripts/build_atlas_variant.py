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
from dataclasses import asdict
import hashlib
import json
import pickle
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


def write_provenance(data: Path, identity: dict, image_scale: int):
    """Keep simulation inputs and export sources beside a portable atlas."""
    sources = [ROOT / 'rotclimate' / name for name in
               ('atlas.py', 'render.py', 'biomes.py', 'biome_targets.py', 'climate_fields.py')]
    sources += [ROOT / 'data' / name for name in
                ('whittaker_biomes.csv', 'whittaker_sources.json', 'WHITTAKER_LICENSE.txt',
                 'biome_target_crosswalk.json', 'whittaker_coverage.json')]
    provenance = dict(simulation=identity, image_scale=image_scale,
                      export_sources={str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                                      for f in sources},
                      convergence_note='Requested tolerances are in simulation.params. Observed convergence '
                                       'checks are recorded separately in atlas.json and summary.json; '
                                       'numerical convergence does not establish physical accuracy.')
    (data / 'build_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


def page(src: str, title: str, eyebrow: str, lede: str, note: str) -> str:
    html = src.replace("<title>Rotclimate Atlas</title>", f"<title>{title}</title>", 1)
    html = html.replace("<h1>Rotclimate Atlas</h1>", f"<h1>{title}</h1>", 1)
    html = re.sub(r'<span class="eyebrow">[^<]*</span>', f'<span class="eyebrow">{eyebrow}</span>', html, count=1)
    html = re.sub(r'<p class="lede">[^<]*</p>', f'<p class="lede">{lede}</p><p class="lede">{note}</p>', html,
                  count=1)
    links=['<a href="../">Compare fits</a>']
    for name,label,heading in [('free_fit','Free fit','Rotclimate Free-Fit Atlas'),
                               ('earth_fit','Earth fit','Rotclimate Earth-Fit Atlas'),
                               ('whittaker_fit','Whittaker fit','Rotclimate Whittaker-Fit Atlas')]:
        active=' aria-current="page"' if title==heading else ''
        links.append(f'<a href="../{name}/"{active}>{label}</a>')
    html=html.replace('</header>','<nav class="atlas-nav" aria-label="Atlas fits">'+' '.join(links)+'</nav></header>',1)
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
    ap.add_argument("--set", default='{}', help='explicit overrides; saved numerical requirements are preserved')
    ap.add_argument('--fit-objective', choices=['zonefit','whittaker','whittaker-broad','whittaker-covered'], default='zonefit')
    ap.add_argument('--require-verified', action='store_true', help='refuse exports without successful observed convergence checks')
    ap.add_argument('--max-outside',type=float,help='reject a build whose source land exceeds this outside-diagram fraction')
    ap.add_argument('--minimum-biome-score',type=float,help='minimum strict target-biome objective for publication')
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--seeds", default="", help="comma list of surroundings layouts to average (ensemble climate)")
    ap.add_argument("--workers", type=int, default=1, help="parallel runs for --seeds")
    ap.add_argument("--image-scale", type=int, choices=[1, 2, 3], default=3,
                    help="image resolution multiplier; does not change the simulation grid")
    ap.add_argument("--checkpoint", help="local result cache, verified against parameters, seeds and model sources")
    a = ap.parse_args()
    for label,value in [('max-outside',a.max_outside),('minimum-biome-score',a.minimum_biome_score)]:
        if value is not None and not 0 <= value <= 1:
            ap.error('--'+label+' must be between zero and one')
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
    # Cache only self-generated local results. A stopped export can then be
    # restarted without repeating the full simulation; incompatible caches
    # fail explicitly rather than serving fields from another parameter set.
    identity = dict(params=json.loads(json.dumps(asdict(p))), seeds=seeds, sources={
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in (ROOT / "rotclimate").glob("*.py")
        if f.name not in {"atlas.py", "render.py", "biomes.py", "climate_fields.py"}})
    identity["map_inputs"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in (ROOT / "data/source").iterdir() if f.is_file()}
    checkpoint = Path(a.checkpoint) if a.checkpoint else None
    if checkpoint and checkpoint.exists():
        with checkpoint.open("rb") as f:
            cached = pickle.load(f)
        if cached["identity"] != identity:
            raise ValueError("Result checkpoint inputs or model sources differ; use a new checkpoint")
        r = cached["result"]
        print("Loaded verified simulation checkpoint", flush=True)
    else:
        print("Simulating climate...", flush=True)
        if seeds:
            from rotclimate.model import run_ensemble
            r = run_ensemble(p, seeds, workers=a.workers)
        else:
            r = simulate(p)
        if checkpoint:
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            tmp = checkpoint.with_suffix(".tmp")
            with tmp.open("wb") as f:
                pickle.dump(dict(identity=identity, result=r), f)
            tmp.replace(checkpoint)
            print("Saved simulation checkpoint", flush=True)
    numerics = getattr(r, 'numerics', None)
    if a.require_verified and not (numerics and numerics.get('all_checks_passed')):
        raise RuntimeError('Atlas export requires observed successful linear, temperature and moisture checks')
    ev = evaluate(r)
    from rotclimate import biome_targets
    valid = r.grid.inmap & r.grid.land
    biome_scores = {profile:biome_targets.evaluate(ev['indices'],r.grid.target,valid,profile)
                    for profile in ['strict','broad']}
    profile = 'broad' if a.fit_objective=='whittaker-broad' else 'strict'
    fit_score = objective(ev,'zonefit') if a.fit_objective=='zonefit' else biome_scores[profile]['score']
    coverage = None
    if a.fit_objective == 'whittaker-covered' or a.max_outside is not None:
        coverage = biome_targets.rendered_coverage(r)
        if a.fit_objective == 'whittaker-covered':
            fit_score = biome_targets.covered_score(fit_score,coverage)
    if a.max_outside is not None and coverage['outside_share'] > a.max_outside:
        raise RuntimeError(f"Outside-diagram land {coverage['outside_share']:.4%} exceeds publication limit {a.max_outside:.4%}")
    if a.minimum_biome_score is not None and biome_scores['strict']['score'] < a.minimum_biome_score:
        raise RuntimeError('Strict biome fit is below the publication floor')
    # High-resolution monthly fields are large. Concurrent branches may
    # simulate independently, but only one export should allocate them at once.
    import fcntl
    export_lock = (ROOT / "atlases" / ".build.lock").open("a")
    print("Waiting for atlas export memory slot...", flush=True)
    fcntl.flock(export_lock, fcntl.LOCK_EX)
    fr = R.FullRes(r)
    print("Rendering atlas layers and station data...", flush=True)
    build(r, fr, ev, outdir=data, image_scale=a.image_scale)
    if a.fit_objective.startswith('whittaker'):
        from rotclimate.atlas import add_biome_target_layers
        add_biome_target_layers(fr, data, profile)
    meta_path=data/'atlas.json';meta=json.loads(meta_path.read_text())
    meta['calibration']=dict(objective=a.fit_objective,score=fit_score,whittaker_profile=profile if a.fit_objective.startswith('whittaker') else None)
    meta['observed_numerics']=numerics
    meta_path.write_text(json.dumps(meta,ensure_ascii=False))
    if not a.no_gif:
        print("Rendering seasonal animations...", flush=True)
        R.season_gif(fr, data / "year_temperature.gif", "T")
        R.season_gif(fr, data / "year_precipitation.gif", "P")
        R.season_gif(fr, data / "year_vapour.gif", "W")
        R.season_gif(fr, data / "year_growing.gif", "G")
    # around the map: the invented land and sea the model adds on every side (one
    # layout: an average over layouts mixes different coastlines out there)
    if p.beyond_style == "procedural":
        rr = simulate(p.replace(beyond_seed=seeds[0], downsample=max(16, a.downsample))) if seeds else r
        around_numerics = getattr(rr, 'numerics', None)
        if a.require_verified and not (around_numerics and around_numerics.get('all_checks_passed')):
            raise RuntimeError('Neighbourhood export requires successful observed convergence checks')
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
        meta["around"] = dict(note=note, layout=seeds[0] if seeds else p.beyond_seed, averaged=len(seeds),
                              observed_numerics=around_numerics)
        (data / "atlas.json").write_text(json.dumps(meta, ensure_ascii=False))
    src = (ROOT / "atlas" / "index.html").read_text()
    (out / "index.html").write_text(page(src, a.title, a.eyebrow, a.lede, a.note))
    shutil.copy(ROOT / "atlas" / "climate-comparison.js", out / "climate-comparison.js")
    shutil.copy(ROOT / "atlas" / "harvest.js", out / "harvest.js")
    p.to_json(out / "params.json")
    codes = __import__("rotclimate.koppen", fromlist=["CODES"]).CODES
    import numpy as np
    from rotclimate.koppen import classify
    st = ev["monthly"]
    g = r.grid
    kop = np.array(codes)[classify(st["Tm"], st["Pm"], st["summer"])]
    med = g.inmap & g.land & (g.target == 4)
    summary = dict(params=a.params, downsample=a.downsample, image_scale=a.image_scale,
                   seeds=seeds or None, seconds=round(time.time() - t),
                   strict_accuracy=ev["accuracy"], zonefit=objective(ev, "zonefit"),
                   recall={k: float(v) for k, v in ev["recall"].items()},
                   mediterranean=dict(dry_share=float(np.char.startswith(kop[med], "B").mean()),
                                      cs_share=float(np.char.startswith(kop[med], "Cs").mean())))
    from rotclimate.__main__ import numerical_settings
    summary['numerics'] = numerical_settings(p)
    summary['observed_numerics'] = numerics
    summary['fit_objective'] = a.fit_objective
    summary['fit_score'] = fit_score
    summary['whittaker'] = biome_scores
    if coverage is not None:
        summary['whittaker_coverage'] = coverage
        summary['coverage_policy'] = biome_targets.coverage_policy()
        shutil.copy(ROOT/'data/whittaker_coverage.json',data/'whittaker_coverage.json')
    write_provenance(data, identity, a.image_scale)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    # These products use the exported climate packet, with no new simulation.
    # The existing export lock also bounds the farming analysis's memory use.
    from harvest.export import export as export_harvest
    export_harvest(out)
    print(json.dumps(summary, indent=1))
    print("atlas written to", out)
    export_lock.close()


if __name__ == "__main__":
    main()
