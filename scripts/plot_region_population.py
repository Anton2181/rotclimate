"""One campaign region's settlement field before and after a change to the
Harvest model, beside its rain-to-evaporation ratio.

    python3 -I scripts/plot_region_population.py --before atlases/free_fit \
        --after output/atlas_r35/preview/free_fit --region "Old Arǧos" \
        --out output/population_reliability/old_argos.png

Reads each atlas's exported Harvest arrays (data/harvest.json + harvest.bin).
The window is the region's hexes plus ~150 km around them; the region's own
hexes are outlined.
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

SURFACE, INK, INK2, SEA = "#fcfcfb", "#0b0b0b", "#52514e", "#dfe6ea"
DENSITY = LinearSegmentedColormap.from_list("density", ["#f6f1df", "#f2cf8a", "#e59a4f", "#c8603a", "#8f3426", "#4d1a17"])
WATER = LinearSegmentedColormap.from_list("water", ["#8f3426", "#e59a4f", "#f6f1df", "#86b6ef", "#184f95"])


def load(atlas: Path):
    h = json.loads((atlas / "data/harvest.json").read_text())
    blob = (atlas / "data/harvest.bin").read_bytes()

    def get(key, raw_values=False):
        d = h["arrays"][key]
        raw = np.frombuffer(blob, np.dtype(d["dtype"]).newbyteorder("<"), count=int(np.prod(d["shape"])),
                            offset=d["offset_bytes"]).reshape(d["shape"])
        if raw_values or "scale" not in d:
            return raw
        return np.where(raw == d.get("nodata", -1), np.nan, raw.astype(float) * d["scale"] + d.get("offset", 0.0))
    return h, get


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--before-label", default="before")
    ap.add_argument("--after-label", default="after")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    hb, gb = load(a.before)
    ha, ga = load(a.after)
    hexid = gb("hex_id", raw_values=True).astype(int)
    ids = [int(k) for k, v in hb["hexes"].items() if v.get("region") == a.region]
    inside = np.isin(hexid, ids)
    rows, cols = np.nonzero(inside)
    pad = 40                                        # analysis cells of ~3.7 km
    r0, r1 = max(rows.min() - pad, 0), min(rows.max() + pad, hexid.shape[0])
    c0, c1 = max(cols.min() - pad, 0), min(cols.max() + pad, hexid.shape[1])
    win = (slice(r0, r1), slice(c0, c1))
    before, after = gb("settlement_base")[win], ga("settlement_base")[win]
    ratio = ga("aridity")[win]
    reg = inside[win]

    def mean(field, mask):
        return float(np.nanmean(field[mask]))
    arid = reg & (ratio < 0.2)
    wet = reg & (ratio >= 0.65)
    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SEA})
    fig, grid = plt.subplots(2, 2, figsize=(12.5, 10), constrained_layout=True)
    axs = grid.ravel()
    im = axs[0].imshow(ratio, cmap=WATER, vmin=0, vmax=1.5, interpolation="nearest")
    axs[0].set_title("Rain over potential evaporation", loc="left", fontsize=11)
    fig.colorbar(im, ax=axs[0], shrink=0.8, pad=0.01).set_label("P / PET (below 0.2 arid)", color=INK2)
    change = after / np.where(before > 0, before, np.nan)
    im = axs[1].imshow(change, cmap=WATER, vmin=0, vmax=1.2, interpolation="nearest")
    axs[1].set_title("Share of the capacity kept", loc="left", fontsize=11)
    fig.colorbar(im, ax=axs[1], shrink=0.8, pad=0.01).set_label(f"{a.after_label} / {a.before_label}", color=INK2)
    norm = LogNorm(2, 300)
    for ax, field, label in ((axs[2], before, a.before_label), (axs[3], after, a.after_label)):
        im = ax.imshow(np.where(np.isfinite(field), np.maximum(field, 1), np.nan), cmap=DENSITY, norm=norm,
                       interpolation="nearest")
        ax.set_title(f"{label}\narid plains {mean(field, arid):.0f}, wetter land {mean(field, wet):.0f} people/km² "
                     f"(×{mean(field, wet) / max(mean(field, arid), 1e-9):.1f})", loc="left", fontsize=10.5)
    fig.colorbar(im, ax=axs[2:], shrink=0.8, pad=0.01).set_label("settlement capacity, people per km²", color=INK2)
    for ax in axs:
        ax.contour(reg.astype(float), levels=[0.5], colors=[INK], linewidths=0.9)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    fig.suptitle(f"{a.region}: where the low-input harvest can feed people (outline: the region's hexes)", x=0.01,
                 ha="left", fontsize=12.5)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=105, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
