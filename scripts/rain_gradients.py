"""Within-region rain gradients, observed and modelled, from benchmark cells.

    python3 -I scripts/rain_gradients.py RUN [RUN ...] [--regions ...]

For every land cell of each region in a benchmark_local.py run (cells/*.npz),
regress log annual rain (obs and model) on distance to the coast
(log(1 + km)), mean elevation (km) and sub-grid relief (highest minus mean
ground, km), with the region mean removed. Prints the pooled coefficients
and each region's relief coefficient: how much wetter rugged ground is.
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np


def region_rows(run, regions=None):
    out = {}
    for f in sorted(glob.glob(os.path.join(run, "cells", "*.npz"))):
        g = os.path.basename(f)[:-4]
        if regions and g not in regions:
            continue
        z = np.load(f)
        ok = np.isfinite(z["Po"]).all(0) & np.isfinite(z["Ps"]).all(0)
        X = np.column_stack([np.log1p(z["coast_km"][ok]), z["elev"][ok] / 1000, (z["elev_max"][ok] - z["elev"][ok]) / 1000])
        out[g] = (np.log(z["Po"][:, ok].sum(0) + 50), np.log(z["Ps"][:, ok].sum(0) + 50), X)
    return out


def fit(X, y):
    A = np.column_stack([X - X.mean(0), np.ones(len(y))])
    return np.linalg.lstsq(A, y - y.mean(), rcond=None)[0][:-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--regions", nargs="*")
    a = ap.parse_args()
    for run in a.runs:
        rows = region_rows(run, a.regions)
        O = np.concatenate([v[0] - v[0].mean() for v in rows.values()])
        S = np.concatenate([v[1] - v[1].mean() for v in rows.values()])
        X = np.concatenate([v[2] - v[2].mean(0) for v in rows.values()])
        bo, bs = fit(X, O), fit(X, S)
        print(f"{run}: pooled coast/elev/relief  obs {bo.round(3)}  model {bs.round(3)}  | within sd obs {O.std():.3f} model {S.std():.3f}"
              f"  corr {np.corrcoef(O, S)[0, 1]:.3f}")
        print("   relief coefficient by region (obs / model): " + "  ".join(
            f"{g[:9]} {fit(v[2], v[0])[2]:+.2f}/{fit(v[2], v[1])[2]:+.2f}" for g, v in rows.items()))


if __name__ == "__main__":
    main()
