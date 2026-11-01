"""Forager lifeways (F14) on an atlas, from its stored FORGE fields: a map of hunters / gatherers / fishers and camp moves.

    python -I scripts/figure_lifeways.py atlases/earth_fit output/forager_binford_20261031/lifeways_earth_fit.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap, LogNorm  # noqa: E402
from PIL import Image  # noqa: E402

from foraging.export import LIFEWAY_COLORS, LIFEWAY_LABELS, lifeway_fields  # noqa: E402


def load(data, sub=""):
    meta = json.loads((data / sub / "foraging.json").read_text())
    blob = (data / sub / "foraging.bin").read_bytes()
    out = {}
    for k, s in meta["arrays"].items():
        n = int(np.prod(s["shape"]))
        a = np.frombuffer(blob, dtype=s["dtype"], count=n, offset=s["offset_bytes"]).reshape(s["shape"]).astype(float)
        out[k] = a * s.get("scale", 1.0) + s.get("offset", 0.0)
    return out


def main():
    atlas, out = Path(sys.argv[1]), Path(sys.argv[2])
    sub = sys.argv[3] if len(sys.argv) > 3 else ""
    f = load(atlas / "data", sub)
    land = f["land_fraction"] > 0
    lw = lifeway_fields(f)
    k = lw["prob"].argmax(-1); conf = lw["prob"].max(-1)
    bg = np.array([0.93, 0.93, 0.90]); sea = np.array([0.84, 0.89, 0.94])
    rgb = np.ones(land.shape + (3,)) * sea
    for i, name in enumerate(lw["classes"]):
        m = land & (k == i)
        w = np.clip((conf - 1 / 3) / (2 / 3), 0.25, 1.0)[m][:, None]
        rgb[m] = w * np.array(LIFEWAY_COLORS[name]) + (1 - w) * bg
    shares = {n: (land & (k == i)).sum() / land.sum() for i, n in enumerate(lw["classes"])}
    labels = Image.open(atlas / "data" / "labels.png").convert("RGBA").resize((land.shape[1] * 4, land.shape[0] * 4)) if (atlas / "data" / "labels.png").exists() else None
    fig, axes = plt.subplots(2, 1, figsize=(12, 11.5), constrained_layout=True)
    ax = axes[0]
    ax.imshow(rgb, interpolation="nearest", extent=(0, land.shape[1], land.shape[0], 0))
    if labels is not None:
        ax.imshow(labels, extent=(0, land.shape[1], land.shape[0], 0), alpha=0.6)
    for n in lw["classes"]:
        ax.scatter([], [], s=80, marker="s", color=LIFEWAY_COLORS[n], label=f"{LIFEWAY_LABELS[n]} · {100 * shares[n]:.0f}% of land")
    ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
    ax.set_title("Forager lifeways (F14): what a band would mostly live on, from the FORGE scenario (paler = less certain)", fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
    ax = axes[1]
    moves = np.where(land, lw["moves"], np.nan)
    im = ax.imshow(moves, cmap="YlOrBr", norm=LogNorm(0.8, 20), interpolation="nearest", extent=(0, land.shape[1], land.shape[0], 0))
    ax.set_facecolor(sea)
    if labels is not None:
        ax.imshow(labels, extent=(0, land.shape[1], land.shape[0], 0), alpha=0.6)
    cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.01); cb.set_label("expected residential moves per year")
    ax.set_title("Camp moves: sparser foragers move more often (from scenario density, as among 211 recorded groups)", fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
    fig.savefig(out, dpi=110)
    print(json.dumps({n: round(float(v), 3) for n, v in shares.items()}), "moves median", round(float(np.nanmedian(moves)), 1))


if __name__ == "__main__":
    main()
