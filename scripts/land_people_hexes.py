"""Land and people per hex, and a check against the campaign sheet.

Averages the land-and-people grid (scripts/land_people.py) over the game's
hexes (pointy-top, 90 per row, data/hexgrid.json), then compares each hex
with the sheet's own Settlement Level and Wealth Base (ravages/data.json,
economy.max) by rank correlation, overall and within each terrain.

    python -I scripts/land_people_hexes.py output/land_people
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
NCOL = 90
MAP_W = 2000.0                    # map coordinates of the hex grid
DRAW_W = 4401                     # the drawing the land grid divides


def hex_index(shape, div, grid):
    """Hex number (1-based) of every cell of the land grid, by nearest centre."""
    h, w = shape
    s = DRAW_W / MAP_W
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    x = (xx + 0.5) * div / s
    y = (yy + 0.5) * div / s
    best = np.full(shape, -1)
    bd = np.full(shape, np.inf)
    r0 = np.clip(np.round((y - grid["y0"]) / grid["dy"]).astype(int), 0, None)
    for dr in (-1, 0, 1):
        r = r0 + dr
        c0 = np.round((x - grid["x0"]) / grid["dx"] - 0.5 * (r % 2)).astype(int)
        for dc in (-1, 0, 1):
            c = c0 + dc
            cx = grid["x0"] + grid["dx"] * (c + 0.5 * (r % 2))
            cy = grid["y0"] + grid["dy"] * r
            d = (x - cx) ** 2 + (y - cy) ** 2
            ok = (r >= 0) & (c >= 0) & (c < NCOL) & (d < bd)
            bd = np.where(ok, d, bd)
            best = np.where(ok, r * NCOL + c + 1, best)
    return best


def per_hex(z, idx, keys):
    land = z["land"]
    out = {}
    hx = idx[land]
    n = np.bincount(hx, minlength=idx.max() + 1)
    for k in keys:
        v = np.nan_to_num(z[k][land].astype(float))
        out[k] = np.bincount(hx, v, minlength=idx.max() + 1) / np.maximum(n, 1)
    out["n"] = n
    return out


def main(folder):
    folder = Path(folder)
    z = dict(np.load(folder / "land_people.npz"))
    div = int(z["div"])
    grid = json.loads((ROOT / "data" / "hexgrid.json").read_text())
    idx = hex_index(z["land"].shape, div, grid)
    keys = ["capacity", "kcal_ha", "lgp_days", "npp", "irr", "arable", "malaria", "P_ann", "T_ann"]
    H = per_hex(z, idx, keys)
    data = json.loads((ROOT / "ravages" / "data.json").read_text())
    emax = data["economy"]["max"]
    rows = []
    for h, (lvl, base) in emax.items():
        h = int(h)
        if h < len(H["n"]) and H["n"][h] >= 4:
            rows.append((h, lvl, base, data["hexes"][str(h)][3], *(H[k][h] for k in keys)))
    hexn = np.array([r[0] for r in rows])
    lvl = np.array([r[1] for r in rows], float)
    base = np.array([r[2] for r in rows], float)
    terr = np.array([r[3].rstrip("s") for r in rows])
    cols = {k: np.array([r[4 + i] for r in rows]) for i, k in enumerate(keys)}
    rep = dict(hexes=len(rows))
    for k in keys:
        rep[k] = dict(settlement=float(stats.spearmanr(cols[k], lvl)[0]),
                      wealth=float(stats.spearmanr(cols[k], base)[0]))
    # within terrain: does the climate explain what the drawn terrain does not?
    within = {}
    for t in sorted(set(terr)):
        m = terr == t
        if m.sum() >= 30:
            within[t] = dict(n=int(m.sum()),
                             wealth=float(stats.spearmanr(cols["capacity"][m], base[m])[0]),
                             settlement=float(stats.spearmanr(cols["capacity"][m], lvl[m])[0]),
                             wealth_vs_kcal=float(stats.spearmanr(cols["kcal_ha"][m], base[m])[0]))
    rep["within_terrain"] = within
    rep["terrain_wealth_median"] = {t: float(np.median(base[terr == t])) for t in sorted(set(terr))}
    rep["terrain_capacity_median"] = {t: float(np.median(cols["capacity"][terr == t])) for t in sorted(set(terr))}
    # settlement level classes: median capacity
    rep["capacity_by_settlement"] = {int(v): float(np.median(cols["capacity"][lvl == v])) for v in sorted(set(lvl))}
    rep["capacity_by_wealth"] = {int(v): float(np.median(cols["capacity"][base == v]))
                                 for v in sorted(set(base)) if (base == v).sum() >= 10}
    print(json.dumps(rep, indent=1))
    out = {int(h): [round(float(H[k][h]), 3) for k in keys] for h in range(1, len(H["n"])) if H["n"][h] > 0}
    (folder / "hexes.json").write_text(json.dumps(dict(keys=keys, hexes=out)))
    (folder / "sheet_check.json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
