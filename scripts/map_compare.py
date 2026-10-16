"""Side-by-side map comparison of parameter sets on the fantasy map (model grid).

One row per parameter file: the painted zones, the zone each cell's simulated
climate is labelled with (the strict label policy, Koppen-gated), the Koppen
classes and the annual rain, plus the promotion-guard measures in the title.

    python -I scripts/map_compare.py --params A.json B.json --names anchor "Earth physics" \
        --downsample 16 --out output/earth_on_map/compare.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

from rotclimate.config import Params  # noqa: E402
from rotclimate.geography import TARGET_CLASSES, TARGET_DRAW_COLORS  # noqa: E402
from rotclimate.koppen import CODES, classify  # noqa: E402


def load(path):
    d = json.loads(Path(path).read_text())
    d = d.get("params", d)
    return Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__})


def zone_rgb(z, land):
    img = np.ones(z.shape + (3,)) * np.array([0.84, 0.89, 0.94])
    img[land] = 0.93
    for cid, col in TARGET_DRAW_COLORS.items():
        img[z == cid] = [int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return img


def run(p):
    from rotclimate.model import ClimateModel
    from rotclimate.score import evaluate

    res = ClimateModel(p).run()
    ev = evaluate(res)
    g = res.grid
    st = ev["monthly"]
    kop = classify(st["Tm"], st["Pm"], st["summer"])
    valid = g.inmap & g.land
    codes = np.array(CODES)[kop]
    med = valid & (g.target == 4)
    m = dict(strict=ev["accuracy"],
             med_dry=float(np.char.startswith(codes[med], "B").mean()),
             med_cs=float(np.char.startswith(codes[med], "Cs").mean()),
             recall={k: float(v) for k, v in ev["recall"].items() if np.isfinite(v)})
    return g, ev["predicted"], kop, st["Pm"].sum(0), m


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", nargs="+", required=True)
    ap.add_argument("--names", nargs="+")
    ap.add_argument("--downsample", type=int, default=16)
    ap.add_argument("--set", default='{"solver_rtol": 1e-5, "solver_require_convergence": false}')
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from rotclimate.render import rgb_image

    names = a.names or [Path(x).stem for x in a.params]
    rows = []
    for path, name in zip(a.params, names):
        p = load(path).replace(downsample=a.downsample, **json.loads(a.set))
        rows.append((name, p) + run(p))
        m = rows[-1][-1]
        print(f"{name}: strict {m['strict']:.1%}, Mediterranean dry {m['med_dry']:.1%}, Cs {m['med_cs']:.1%}, "
              + ", ".join(f"{k} {v:.0%}" for k, v in m["recall"].items()), flush=True)
    sl = rows[0][2].map_slice()
    fig, axs = plt.subplots(len(rows), 4, figsize=(22, 3.3 * len(rows) + 0.8), squeeze=False)
    for ax_row, (name, p, g, pred, kop, rain, m) in zip(axs, rows):
        land = g.land[sl]
        valid = (g.inmap & g.land)[sl]
        ax_row[0].imshow(zone_rgb(np.where(valid, g.target[sl], 0), land), interpolation="nearest")
        ax_row[0].set_title("painted zones", fontsize=10)
        ax_row[1].imshow(zone_rgb(np.where(valid, pred[sl], 0), land), interpolation="nearest")
        ax_row[1].set_title(f"{name}: simulated zones - strict {m['strict']:.1%}", fontsize=10)
        k = rgb_image(kop[sl]).astype(float) / 255
        k[~land] = [0.84, 0.89, 0.94]
        ax_row[2].imshow(k, interpolation="nearest")
        ax_row[2].set_title(f"Koppen - painted Med: {m['med_cs']:.0%} Cs, {m['med_dry']:.0%} dry", fontsize=10)
        im = ax_row[3].imshow(np.where(land, rain[sl], np.nan), cmap="YlGnBu", vmin=0, vmax=2000,
                              interpolation="nearest")
        spin = "reversed spin" if p.retrograde else "Earth spin"
        ax_row[3].set_title(f"annual rain (mm) - {p.lat_center:.1f} N, tilt {p.tilt:.1f}, {spin}", fontsize=10)
        fig.colorbar(im, ax=ax_row[3], shrink=0.8)
        for ax in ax_row:
            ax.set_axis_off()
    handles = [Patch(color=TARGET_DRAW_COLORS[c], label=lab) for c, _, lab, _ in TARGET_CLASSES]
    fig.legend(handles=handles, loc="lower center", ncol=7, fontsize=9, frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(a.out, dpi=80)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
