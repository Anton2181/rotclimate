"""Compare the Earth run of the food-capacity model with HYDE 3.3 population.

    python3 -I scripts/hyde_compare.py --hyde data/cache/hyde33/popc_ce_200.tif \
        --earth output/land_people/earth/earth.npz --out output/population_hyde/ce_200.json

HYDE 3.3 (Klein Goldewijk et al.; portal https://hyde-portal.geo.uu.nl, raster
popc = people per 5 arc-minute cell, first row at 90 N, first column at 180 W)
is itself a model: modern-country totals spread by suitability weights similar
to ours. Agreement inside a country therefore shows that two proxies agree, not
that either is right; this is a consistency check, not validation.

Both fields are aggregated to 1 degree (12 x 12 cells) over land of the Earth
window. Reported, against HYDE and for a uniform-over-land baseline:
  spearman      rank correlation of 1-degree densities
  moved_share   share of people that must move to turn one map into the other
                (0.5 x sum |share_a - share_b|; scale-free, pattern only)
  log_rmse      RMS of log10((density_a + 1) / (density_b + 1)) after scaling
                each map to HYDE's window total
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def hyde_at(path, lat, lon):
    a = np.array(Image.open(path), dtype=np.float64)
    a[~np.isfinite(a) | (a < 0)] = 0.0
    rows = np.clip(np.floor((90.0 - lat) * 12).astype(int), 0, a.shape[0] - 1)
    cols = np.clip(np.floor((lon + 180.0) * 12).astype(int), 0, a.shape[1] - 1)
    return a[np.ix_(rows, cols)]


def blocks(x, n=12):
    h, w = (x.shape[0] // n) * n, (x.shape[1] // n) * n
    return x[:h, :w].reshape(h // n, n, w // n, n).sum((1, 3))


def spearman(a, b):
    """Rank correlation with tied ranks averaged (nan when a field is constant)."""
    from scipy.stats import spearmanr
    return float(spearmanr(a, b).statistic)


def metrics(model_people, hyde_people, area, land_blk):
    m, h, A = model_people[land_blk], hyde_people[land_blk], area[land_blk]
    m = m * h.sum() / max(m.sum(), 1e-9)
    dm, dh = m / A, h / A
    return dict(spearman=spearman(dm, dh),
                moved_share=float(0.5 * np.abs(m / m.sum() - h / h.sum()).sum()),
                log_rmse=float(np.sqrt(np.mean(np.log10((dm + 1) / (dh + 1)) ** 2))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hyde", required=True)
    ap.add_argument("--earth", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    cell_km2 = (111.32 / 12) ** 2 * np.cos(np.radians(lat))[:, None] * np.ones((1, len(lon)))
    hyde = hyde_at(a.hyde, lat, lon) * land
    model = np.nan_to_num(z["capacity"]) * cell_km2 * land
    uniform = cell_km2 * land
    H, M, U, A = blocks(hyde), blocks(model), blocks(uniform), blocks(cell_km2 * land)
    ok = (blocks(land.astype(float)) >= 0.5 * 144) & (H > 0)
    res = dict(source=a.hyde, window=dict(lat=[float(lat.min()), float(lat.max())], lon=[float(lon.min()), float(lon.max())]),
               blocks=int(ok.sum()), hyde_total_m=float(H[ok].sum() / 1e6), capacity_total_m=float(M[ok].sum() / 1e6),
               capacity=metrics(M, H, A, ok), uniform=metrics(U, H, A, ok))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"{Path(a.hyde).name}: {res['blocks']} land blocks (1 deg), HYDE {res['hyde_total_m']:.1f} M people, "
          f"capacity {res['capacity_total_m']:.1f} M")
    for k in ("capacity", "uniform"):
        v = res[k]
        print(f"  {k:9s} rank corr {v['spearman']:.3f}  people to move {v['moved_share']:.1%}  log10 RMSE {v['log_rmse']:.3f}")


if __name__ == "__main__":
    main()
