"""Steppe against farmland: the recorded border and the two travel models (E3).

    python3 -I scripts/plot_steppe_border.py --out output/polity_earth/steppe_border.png

Reads output/polity_earth/steppe_{2AD,742AD}.npz and calibration/polity_20261025/eras_e3.json
(scripts/polity_eras_check.py --stage e3).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SURFACE, INK, INK_SOFT = "#fcfcfb", "#0b0b0b", "#52514e"
FARM, HERD, OTHER, SEA = np.array([42, 120, 214]) / 255, np.array([235, 104, 52]) / 255, np.array([.90, .89, .86]), \
    np.array([.84, .89, .94])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = json.loads((ROOT / "calibration/polity_20261025/eras_e3.json").read_text())
    with np.load(ROOT / "output/polity_earth/steppe.npz") as z:
        land = z["land"].astype(bool)
    cases = [("2AD", "Han AD 2 against the Xiongnu", "Han", "Xiongnu"),
             ("742AD", "Tang AD 742 against the Türgesh", "Tang", "Türgesh")]
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.4), facecolor=SURFACE, constrained_layout=True)
    for row, (year, label, farm_name, herd_name) in enumerate(cases):
        with np.load(ROOT / f"output/polity_earth/steppe_{year}.npz") as z:
            farm, herd, df, dw, dr = z["farm"], z["herd"], z["d_farm"], z["d_walk"], z["d_ride"]
        union = farm | herd
        r = res[label]
        panels = [("recorded", farm, herd), (f"steppe on foot · {r['walking']['balanced_accuracy']:.3f}",
                                             union & (df <= dw), union & (dw < df)),
                  (f"steppe riding · {r['riding']['balanced_accuracy']:.3f}", union & (df <= dr), union & (dr < df))]
        for col, (title, f_, h_) in enumerate(panels):
            img = np.where(land[..., None], OTHER, SEA)
            img[f_] = FARM; img[h_] = HERD
            A = ax[row, col]
            A.imshow(img, interpolation="nearest")
            if col:
                A.contour(farm.astype(float), levels=[0.5], colors=[INK], linewidths=0.8)
            A.set_xticks([]); A.set_yticks([])
            for s in A.spines.values():
                s.set_visible(False)
            A.set_title((label + " · " if col == 0 else "") + title, loc="left", fontsize=10, color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=FARM), plt.Rectangle((0, 0), 1, 1, color=HERD)]
    fig.legend(handles, ["farming state (reached from its county seats, on foot)",
                         "steppe polity (reached from its pastures)"], loc="outside lower center", ncol=2,
               frameon=False, fontsize=9.5,
               title="Black line: the farming state's recorded border · figure in each title: balanced accuracy "
                     "of who gets each place", title_fontsize=9)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=100, facecolor=SURFACE, bbox_inches="tight")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
