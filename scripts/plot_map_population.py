"""Where people would live on the map around 200 AD: the atlas's settlement
field, the same people redistributed around old cores, and the campaign
sheet's own settlement levels.

    python3 -I scripts/plot_map_population.py atlases/earth_fit --out output/population_cores/map_cores.png

Reads the atlas's exported Harvest arrays (data/harvest.json + harvest.bin).
The central occupation scenario fills a fixed share of the settlement
capacity everywhere. The cored panel multiplies capacity by exp(-D / L),
D the straight-line distance to the nearest core, L 800 km (the scale that
fitted Han China, HYDE and Rome; reports/POPULATION_20261023.md), and
rescales to the same total. The cores are the campaign lore's old
heartlands (data/lore_cores.json); where the atlas exports the cored field
(settlement_cored, travel cost through forest and relief) it is used, else the
straight-line distance. Spearman correlations are over hexes with a sheet
settlement level.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

SURFACE, INK, INK2, SEA = "#fcfcfb", "#0b0b0b", "#52514e", "#dfe6ea"
DENSITY = LinearSegmentedColormap.from_list("density", ["#f6f1df", "#f2cf8a", "#e59a4f", "#c8603a", "#8f3426", "#4d1a17"])
ROOT = Path(__file__).resolve().parents[1]
LORE = json.loads((ROOT / "data/lore_cores.json").read_text())["cores"]
MAP_KM = (1058.2 * 1.609344, 2286.8 * 1.609344)


def arrays(atlas: Path):
    h = json.loads((atlas / "data/harvest.json").read_text())
    blob = (atlas / "data/harvest.bin").read_bytes()

    def get(key, raw_values=False):
        d = h["arrays"][key]
        raw = np.frombuffer(blob, np.dtype(d["dtype"]).newbyteorder("<"), count=int(np.prod(d["shape"])),
                            offset=d["offset_bytes"]).reshape(d["shape"])
        if raw_values or "scale" not in d:
            return raw
        out = raw.astype(float) * d["scale"] + d.get("offset", 0.0)
        return np.where(raw == d.get("nodata", -1), np.nan, out)
    return h, get


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("atlas", type=Path)
    ap.add_argument("--scale-km", type=float, default=800.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    h, get = arrays(a.atlas)
    base = get("settlement_base")
    hexid = get("hex_id", raw_values=True).astype(int)
    land = np.isfinite(base)
    ny, nx = base.shape
    km = MAP_KM[0] / ny, MAP_KM[1] / nx
    cores = {c["name"]: (c["y"] * ny / h["height"], c["x"] * nx / h["width"]) for c in LORE}
    share = h["occupation"]["scenarios"]["central"]
    central = share * np.nan_to_num(base)
    if "settlement_cored" in h["arrays"]:
        cored = share * np.nan_to_num(get("settlement_cored"))
    else:
        ii, jj = np.mgrid[0:ny, 0:nx]
        D = np.min([np.hypot((ii - r) * km[0], (jj - c) * km[1]) for r, c in cores.values()], axis=0)
        cored = np.nan_to_num(base) * np.exp(-D / a.scale_km)
        cored *= central.sum() / cored.sum()
    sheet = np.full(base.shape, np.nan)
    levels = {int(k): v["sheet_settlement"] for k, v in h["hexes"].items() if v.get("sheet_settlement") is not None}
    ids = np.array(sorted(levels))
    lookup = np.full(hexid.max() + 1, np.nan)
    lookup[ids] = [levels[i] for i in ids]
    sheet = np.where((hexid > 0) & land, lookup[np.clip(hexid, 0, hexid.max())], np.nan)

    def per_hex(field):
        s = np.bincount(hexid[land].ravel(), weights=field[land].ravel(), minlength=hexid.max() + 1)
        n = np.bincount(hexid[land].ravel(), minlength=hexid.max() + 1)
        return s[ids] / np.maximum(n[ids], 1)
    sh = lookup[ids]
    rho_base = spearmanr(per_hex(central), sh).statistic
    rho_core = spearmanr(per_hex(cored), sh).statistic

    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SEA})
    fig, axs = plt.subplots(3, 1, figsize=(11, 15.5), constrained_layout=True)
    norm = LogNorm(1, 300)
    for ax, field, title in (
            (axs[0], central, f"Settlement field, central occupation: {central.sum() * km[0] * km[1] / 1e6:.0f} M people  "
                              f"(rank match to the sheet {rho_base:.2f})"),
            (axs[1], cored, f"Same people around the lore's old heartlands, exp(−D / {a.scale_km:.0f} km)  "
                            f"(rank match to the sheet {rho_core:.2f})")):
        im = ax.imshow(np.where(land, np.maximum(field, 0.5), np.nan), cmap=DENSITY, norm=norm, interpolation="nearest")
        ax.set_title(title, loc="left", fontsize=11)
        cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01)
        cb.set_label("people per km²", color=INK2)
    for name, (r, c) in cores.items():
        axs[1].plot(c, r, marker="*", ms=14, mfc="#2a78d6", mec=SURFACE, mew=1.2)
        axs[1].annotate(name, (c, r), xytext=(8, -14), textcoords="offset points", fontsize=9, color="#184f95")
    lv = axs[2].imshow(sheet, cmap=DENSITY, vmin=0, vmax=100, interpolation="nearest")
    axs[2].set_title("The campaign sheet's settlement level per hex", loc="left", fontsize=11)
    cb = fig.colorbar(lv, ax=axs[2], shrink=0.8, pad=0.01)
    cb.set_label("sheet level", color=INK2)
    for ax in axs:
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    fig.suptitle(f"Where people would live around 200 AD: {a.atlas.name.replace('_', ' ')} climate", x=0.01, ha="left",
                 fontsize=13)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=100, facecolor=SURFACE)
    print(f"wrote {a.out}: spearman base {rho_base:.3f}, cored {rho_core:.3f}, hexes {len(ids)}")


if __name__ == "__main__":
    main()
