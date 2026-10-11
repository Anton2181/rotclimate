"""Score ExoPlaSim runs against the painted zones, side by side with rotclimate.

For each run: average the last --years of monthly output, sample it onto the
map's 14 km cells (bilinear; near-surface air temperature corrected from the
GCM's smooth terrain to the map's height with 6.5 C/km; for a mirrored run
the cells' mirrored longitudes undo the mirror), then apply exactly the zone
rules and scores rotclimate is calibrated on. The same parameter set is also
simulated with rotclimate for comparison.

Robust coarse-grid checks are printed too: for the north, middle and south
thirds of the map, the annual rain and the summer share of rain on the
western and eastern coasts (westmost and eastmost quarter of the land in
each row).

    python scripts/exoplasim_compare.py \
        A=calibration/round17_earthlike.json:exo/earthlike_T21:earthlike \
        B=calibration/round17_retrograde.json:exo/retro_T21:retro --res T21 --years 10 \
        --out output/exoplasim_check.png
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rotclimate.config import Params  # noqa: E402
from rotclimate.geography import TARGET_CLASSES, TARGET_DRAW_COLORS, build_grid  # noqa: E402
from rotclimate.koppen import climate_indices, monthly_stats  # noqa: E402
from rotclimate.score import (best_zone, memberships, objective, precision_f1,  # noqa: E402
                              terrain_slope)

LAPSE = 0.0065
G0 = 9.80665


def gcm_climate(folder, res, years):
    files = sorted(glob.glob(str(Path(folder) / f"out_{res}" / "MOST.*.npz")))
    files = [f for f in files if not f.endswith("_metadata.npz")][-years:]
    if not files:
        raise SystemExit(f"no output in {folder}/out_{res}")
    T = P = H = Z = None
    for f in files:
        d = np.load(f)
        t, p = d["tas"] - 273.15, d["pr"] * 86400e3          # C, mm/day
        T = t if T is None else T + t
        P = p if P is None else P + p
        H = d["sg"].mean(0) / G0
        Z = d["zdec"]
    n = len(files)
    return dict(lat=d["lat"], lon=d["lon"], T=T / n, P=P / n * 365.25 / 12, H=H, summer=Z > 0, years=n,
                first=Path(files[0]).name, last=Path(files[-1]).name)


def sample(field, glat, glon, lat, lon):
    """Bilinear on a (lat descending, lon periodic) grid; field [..., nlat, nlon]."""
    la = glat[::-1]
    f = field[..., ::-1, :]
    i = np.clip(np.searchsorted(la, lat) - 1, 0, la.size - 2)
    wy = np.clip((lat - la[i]) / (la[i + 1] - la[i]), 0, 1)
    dl = glon[1] - glon[0]
    x = (lon % 360.0) / dl
    j = np.floor(x).astype(int) % glon.size
    j2 = (j + 1) % glon.size
    wx = x - np.floor(x)
    return ((1 - wy) * ((1 - wx) * f[..., i, j] + wx * f[..., i, j2])
            + wy * ((1 - wx) * f[..., i + 1, j] + wx * f[..., i + 1, j2]))


def score(Tm, Pm, summer, g):
    ix = climate_indices(Tm, Pm, summer)
    mem = memberships(ix, slope=terrain_slope(g))
    valid = g.inmap & g.land
    cov = {}
    for cid, key, _, _ in TARGET_CLASSES:
        m = valid & (g.target == cid)
        cov[key] = float(mem[key][m].mean())
    prec, f1 = precision_f1(mem, g.target, valid, cov, elev=g.elev)
    pred = best_zone(mem)
    painted = valid & (g.target > 0)
    correct = {key: float((pred[valid & (g.target == cid)] == cid).mean()) for cid, key, _, _ in TARGET_CLASSES}
    MAP = ix["MAP"][valid]
    realism = dict(map_median=float(np.median(MAP)), map_p95=float(np.percentile(MAP, 95)))
    obj = objective(dict(f1=f1, per_class=cov, realism=realism), "f1")
    return dict(objective=obj, accuracy=float((pred[painted] == g.target[painted]).mean()), f1=f1,
                coverage=cov, correct=correct, pred=pred, ix=ix)


def coasts(ix, g):
    """Annual rain and summer share on the west / east coasts of each third."""
    valid = g.inmap & g.land
    rows = np.flatnonzero(valid.any(1))
    thirds = np.array_split(rows, 3)
    out = {}
    for name, rr in zip(("north", "middle", "south"), thirds):
        west, east = np.zeros_like(valid), np.zeros_like(valid)
        for r in rr:
            cols = np.flatnonzero(valid[r])
            if cols.size < 8:
                continue
            q = max(cols.size // 4, 1)
            west[r, cols[:q]] = True
            east[r, cols[-q:]] = True
        out[name] = {side: dict(rain=float(np.median(ix["MAP"][m])),
                                summer_share=float(np.median(ix["Psum"][m] / np.maximum(ix["MAP"][m], 1))))
                     for side, m in (("west", west), ("east", east))}
    return out


def rotclimate_climate(p):
    from rotclimate.model import ClimateModel

    r = ClimateModel(p.replace(downsample=8, steps_per_year=25, picard_iters=2)).run()
    st = monthly_stats(r.T, r.P, r.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    return st["Tm"], st["Pm"], st["summer"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="LABEL=params.json:folder:name")
    ap.add_argument("--res", default="T21")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    results, panels = {}, []
    for spec in a.runs:
        label, rest = spec.split("=", 1)
        ppath, folder, name = rest.split(":")
        p = Params.from_json(ppath).replace(downsample=8)
        g = build_grid(p)
        mp = np.load(Path(folder) / f"{name}_map.npz")
        c = gcm_climate(folder, a.res, a.years)
        Tm = sample(c["T"], c["lat"], c["lon"], mp["lat"], mp["lon"])
        hg = sample(c["H"], c["lat"], c["lon"], mp["lat"], mp["lon"])
        Tm = Tm - LAPSE * (np.maximum(g.elev, 0) - hg)[None]
        Pm = np.maximum(sample(c["P"], c["lat"], c["lon"], mp["lat"], mp["lon"]), 0)
        sg = score(Tm, Pm, c["summer"], g)
        sr = score(*rotclimate_climate(p), g)
        spin = "reversed" if p.retrograde else "Earth-like"
        results[label] = dict(spin=spin, params=ppath, gcm_years=f"{c['first']}..{c['last']} ({c['years']})",
                              exoplasim={k: v for k, v in sg.items() if k not in ("pred", "ix")},
                              rotclimate={k: v for k, v in sr.items() if k not in ("pred", "ix")},
                              coasts=dict(exoplasim=coasts(sg["ix"], g), rotclimate=coasts(sr["ix"], g)))
        panels.append((f"{label}: ExoPlaSim {a.res}, {spin} spin", sg["pred"], g))
        panels.append((f"{label}: rotclimate, {spin} spin", sr["pred"], g))
        print(f"== {label} ({spin} spin, {ppath}); ExoPlaSim years {c['first']}..{c['last']}")
        for who, s in (("ExoPlaSim", sg), ("rotclimate", sr)):
            print(f"  {who:10s} objective {s['objective']:.3f}  correct {s['accuracy']:.0%}  "
                  + "  ".join(f"{k} {v:.0%}" for k, v in s["correct"].items()))
        for band in ("north", "middle", "south"):
            ce, cr = results[label]["coasts"]["exoplasim"][band], results[label]["coasts"]["rotclimate"][band]
            print(f"  {band:6s} coast rain W/E: ExoPlaSim {ce['west']['rain']:5.0f}/{ce['east']['rain']:5.0f} mm "
                  f"(summer share {ce['west']['summer_share']:.0%}/{ce['east']['summer_share']:.0%}); "
                  f"rotclimate {cr['west']['rain']:5.0f}/{cr['east']['rain']:5.0f} mm "
                  f"({cr['west']['summer_share']:.0%}/{cr['east']['summer_share']:.0%})")
    if a.out:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap

        g0 = panels[0][2]
        sl = g0.map_slice()
        cols = ["#d9d9d9"] + [TARGET_DRAW_COLORS[c] for c in range(1, 8)]
        cmap = ListedColormap(cols)
        n = len(panels) + 1
        ncol = 3 if n > 4 else n
        nrow = int(np.ceil(n / ncol))
        fig, axs = plt.subplots(nrow, ncol, figsize=(6.2 * ncol, 3.3 * nrow), squeeze=False)
        sea = np.ma.masked_where(g0.land[sl], np.ones(g0.land[sl].shape))
        items = [("Your painted zones", np.where(g0.inmap & g0.land, g0.target, 0), g0)] + panels
        for ax, (title, z, g) in zip(axs.flat, items):
            zz = np.ma.masked_where(~g.land[sl], z[sl])
            ax.imshow(sea, cmap=ListedColormap(["#d6e4ef"]), interpolation="nearest")
            ax.imshow(zz, cmap=cmap, vmin=-0.5, vmax=7.5, interpolation="nearest")
            ax.set_title(title, fontsize=10)
            ax.axis("off")
        for ax in axs.flat[len(items):]:
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(a.out, dpi=110)
        Path(a.out).with_suffix(".json").write_text(json.dumps(results, indent=1))
        print("wrote", a.out)


if __name__ == "__main__":
    main()
