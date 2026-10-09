"""Side experiments that make good animations.

    python -m rotclimate.experiments tilt   --params P  --out output/tilt_sweep.gif
    python -m rotclimate.experiments spin   --params P  --out output/spin_flip.gif
    python -m rotclimate.experiments history --out output/improvement.gif
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .config import REPO, Params
from .model import ClimateModel
from .render import FullRes, koppen_frames_gif
from .score import evaluate

REF = dict(downsample=12, steps_per_year=37, picard_iters=2)   # reference evaluation


def _run(p: Params):
    r = ClimateModel(p).run()
    return r, evaluate(r)


def tilt_sweep(p: Params, out, tilts=None, res=REF):
    tilts = tilts if tilts is not None else [0, 5, 10, 15, 20, 23.44, 27, 30, 35, 40, 45, 50, 60]
    items = []
    for t in tilts:
        r, ev = _run(p.replace(tilt=float(t), **res))
        star = "  ← calibrated" if abs(t - p.tilt) < 0.6 else ""
        items.append((FullRes(r).compact(), f"axial tilt {t:g}°   score {ev['total']:.2f}{star}"))
        print(f"tilt {t}: {ev['total']:.3f}")
    koppen_frames_gif(items, out, ms=900)


def spin_flip(p: Params, out, res=REF):
    items = []
    for retro in (p.retrograde, not p.retrograde):
        r, ev = _run(p.replace(retrograde=retro, **res))
        items.append((FullRes(r).compact(), f"{'retrograde' if retro else 'prograde (Earth-like)'} spin   "
                                  f"score {ev['total']:.2f}"))
        print(retro, ev["total"])
    koppen_frames_gif(items, out, ms=1500)


def lat_sweep(p: Params, out, res=REF):
    items = []
    for lat in np.arange(p.lat_center - 8, p.lat_center + 8.1, 2.0):
        r, ev = _run(p.replace(lat_center=float(lat), **res))
        items.append((FullRes(r).compact(), f"map centre at {lat:.1f}°   score {ev['total']:.2f}"))
        print(lat, ev["total"])
    koppen_frames_gif(items, out, ms=900)


def snapshot(p: Params, tag: str, title: str, note: str = "", it_dir=REPO / "calibration" / "iterations",
             res=REF):
    """Record one improvement iteration: params, scores and a rendered frame."""
    from .render import _fig_to_pil, koppen_frames_gif  # noqa: F401

    it_dir = Path(it_dir)
    it_dir.mkdir(parents=True, exist_ok=True)
    r, ev = _run(p.replace(**res))
    tmp = it_dir / f"{tag}.gif"
    koppen_frames_gif([(FullRes(r).compact(), f"{tag}: {title}   score {ev['total']:.2f}")], tmp, ms=1000)
    from PIL import Image

    Image.open(tmp).convert("RGB").save(it_dir / f"{tag}.png")
    tmp.unlink()
    from .score import objective

    meta = dict(tag=tag, title=title, note=note, score=ev["total"], accuracy=ev["accuracy"],
                balanced=objective(ev, "balanced"), rivers=ev["rivers"], realism=ev["realism"],
                per_class=ev["per_class"], params=json.loads(json.dumps(p.__dict__)))
    (it_dir / f"{tag}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(f"{tag}: {ev['total']:.3f}  balanced {meta['balanced']:.3f}  acc {ev['accuracy']:.3f}  "
          f"rivers {ev['rivers']['spearman']:.2f}  " +
          " ".join(f"{k}={v:.2f}" for k, v in ev["per_class"].items()))
    return ev


def history(out, it_dir=REPO / "calibration" / "iterations", ms=1300):
    from PIL import Image

    from .render import save_gif

    # "p" frames (e.g. it07p) are side comparisons, not steps of the improvement
    frames = [Image.open(f).convert("RGB") for f in sorted(Path(it_dir).glob("it*.png"))
              if not f.stem.endswith("p")]
    frames += [frames[-1]] * 2          # linger on the final state
    save_gif(frames, out, ms=ms)


def robustness(p: Params, seeds=(1, 2, 3, 4, 5, 6), resolutions=((16, 25), (12, 37), (8, 73))):
    """Score spread across random surroundings and across grid resolutions."""
    rows = []
    for sd in seeds:
        r, ev = _run(p.replace(beyond_seed=sd, **REF))
        rows.append(("seed", sd, ev["total"], ev["accuracy"], ev["rivers"]["spearman"]))
        print(f"seed {sd}: {ev['total']:.3f}")
    for f, st in resolutions:
        r, ev = _run(p.replace(downsample=f, steps_per_year=st, picard_iters=2 if f > 8 else 3))
        rows.append(("res", f"{r.grid.cell_km:.0f} km / {st} steps", ev["total"], ev["accuracy"],
                     ev["rivers"]["spearman"]))
        print(f"res {f}: {ev['total']:.3f}")
    return rows


def surroundings(p: Params, out, res=REF):
    """Animate how the unknown off-map land changes the climate."""
    cases = [("as calibrated", {}),
             ("open ocean on every side", dict(beyond_north_land=0.0, beyond_south_land=0.0,
                                               beyond_west_land=0.0, beyond_east_land=0.0)),
             ("continent to the west", dict(beyond_west_land=0.95)),
             ("continent to the east", dict(beyond_east_land=0.95)),
             ("continent to the north", dict(beyond_north_land=0.95)),
             ("ocean to the north", dict(beyond_north_land=0.0)),
             ("land everywhere", dict(beyond_north_land=0.95, beyond_south_land=0.95,
                                      beyond_west_land=0.95, beyond_east_land=0.95))]
    items = []
    for name, kw in cases:
        r, ev = _run(p.replace(**kw, **res))
        items.append((FullRes(r).compact(), f"{name}   score {ev['total']:.2f}"))
        print(name, ev["total"])
    koppen_frames_gif(items, out, ms=1500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["tilt", "spin", "lat", "history", "snapshot", "robust",
                                     "surroundings"])
    ap.add_argument("--params", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--title", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    p = Params.from_json(a.params) if a.params else Params()
    if a.what == "tilt":
        tilt_sweep(p, a.out)
    elif a.what == "spin":
        spin_flip(p, a.out)
    elif a.what == "lat":
        lat_sweep(p, a.out)
    elif a.what == "snapshot":
        snapshot(p, a.tag, a.title, a.note)
    elif a.what == "robust":
        rows = robustness(p)
        if a.out:
            Path(a.out).write_text(json.dumps(rows, indent=1))
    elif a.what == "surroundings":
        surroundings(p, a.out)
    else:
        history(a.out)


if __name__ == "__main__":
    main()
