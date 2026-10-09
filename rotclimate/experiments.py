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
        items.append((FullRes(r), f"axial tilt {t:g}°   score {ev['total']:.2f}{star}"))
        print(f"tilt {t}: {ev['total']:.3f}")
    koppen_frames_gif(items, out, ms=900)


def spin_flip(p: Params, out, res=REF):
    items = []
    for retro in (p.retrograde, not p.retrograde):
        r, ev = _run(p.replace(retrograde=retro, **res))
        items.append((FullRes(r), f"{'retrograde' if retro else 'prograde (Earth-like)'} spin   "
                                  f"score {ev['total']:.2f}"))
        print(retro, ev["total"])
    koppen_frames_gif(items, out, ms=1500)


def lat_sweep(p: Params, out, res=REF):
    items = []
    for lat in np.arange(p.lat_center - 8, p.lat_center + 8.1, 2.0):
        r, ev = _run(p.replace(lat_center=float(lat), **res))
        items.append((FullRes(r), f"map centre at {lat:.1f}°   score {ev['total']:.2f}"))
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
    koppen_frames_gif([(FullRes(r), f"{tag}: {title}   score {ev['total']:.2f}")], tmp, ms=1000)
    from PIL import Image

    Image.open(tmp).convert("RGB").save(it_dir / f"{tag}.png")
    tmp.unlink()
    meta = dict(tag=tag, title=title, note=note, score=ev["total"], accuracy=ev["accuracy"],
                per_class=ev["per_class"], params=json.loads(json.dumps(p.__dict__)))
    (it_dir / f"{tag}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(f"{tag}: {ev['total']:.3f}  acc {ev['accuracy']:.3f}  " +
          " ".join(f"{k}={v:.2f}" for k, v in ev["per_class"].items()))
    return ev


def history(out, it_dir=REPO / "calibration" / "iterations", ms=1300):
    from PIL import Image

    from .render import save_gif

    frames = [Image.open(f).convert("RGB") for f in sorted(Path(it_dir).glob("it*.png"))]
    frames += [frames[-1]] * 2          # linger on the final state
    save_gif(frames, out, ms=ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["tilt", "spin", "lat", "history", "snapshot"])
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
    else:
        history(a.out)


if __name__ == "__main__":
    main()
