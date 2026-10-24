"""Where does a region's rain come from? One Earth region's monthly fields.

    python3 -I scripts/diagnose_region_rain.py --fit calibration/local_accuracy_20261023/r35_params.json \
        --region north_india --months 4 7 --out output/diag_rain/north_india

Runs the region once (with --set overrides) and saves the full simulated
domain (map plus padding): precipitation, precipitable water, evaporation,
surface wind and temperature by month, next to WorldClim's rain on the map.
The figure shows, for each chosen month, observed and simulated rain on a
common scale and the simulated winds over precipitable water.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402

from benchmark_local import DEV12_SPECS  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402

INK, SURFACE = "#1b262c", "#fcfcfb"


def monthly(field, res):
    """[12, ny, nx] monthly means of a [nt, ny, nx] field, via monthly_stats's month windows."""
    p = res.params
    st = monthly_stats(field, np.maximum(field, 0), res.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    return st["Tm"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", required=True)
    ap.add_argument("--set", default="{}")
    ap.add_argument("--region", required=True)
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--months", type=int, nargs="+", default=[1, 7])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    p = load_params(a.fit).replace(**json.loads(a.set))
    case = earth.region_case(a.region, a.cell_km)
    res = earth.run_case(p, case, steps=p.steps_per_year)
    g = case.grid
    fields = {k: monthly(getattr(res, k), res) for k in ("P", "W", "E", "u", "v", "T")}
    for k in ("P", "E"):
        fields[k] = fields[k] * 30.4                       # mm / day -> mm / month
    a.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out / "fields.npz", **fields, obs_P=np.asarray(case.obs_P), land=g.land, inmap=g.inmap,
                        lat=g.lat, lon=case.lon, elev=g.elev)
    m = g.inmap & g.land & np.isfinite(case.obs_P).all(0)
    print("map land, mm/month    obs  sim   W mm  E mm  v m/s  u m/s")
    for k in range(12):
        print(f"  month {k + 1:2d}       {np.nanmean(case.obs_P[k][m]):5.0f} {fields['P'][k][m].mean():5.0f} {fields['W'][k][m].mean():6.1f}"
              f" {fields['E'][k][m].mean():5.0f} {fields['v'][k][m].mean():+6.2f} {fields['u'][k][m].mean():+6.2f}")
    land = g.land.astype(float)
    fig, axs = plt.subplots(len(a.months), 3, figsize=(16, 4.6 * len(a.months)), squeeze=False, constrained_layout=True)
    norm = LogNorm(5, 600)
    for row, mo in zip(axs, a.months):
        k = mo - 1
        obs = np.where(g.inmap & g.land, np.asarray(case.obs_P)[k], np.nan)
        for ax, f, title in ((row[0], obs, f"Observed rain, month {mo}"), (row[1], fields["P"][k], f"Simulated rain, month {mo}")):
            im = ax.imshow(np.maximum(f, 5), norm=norm, cmap="YlGnBu", origin="upper")
            ax.set_title(title, loc="left")
        fig.colorbar(im, ax=row[:2], shrink=0.8).set_label("mm per month")
        im = row[2].imshow(fields["W"][k], cmap="BuPu", origin="upper", vmin=0, vmax=60)
        s = max(1, g.land.shape[1] // 25)
        yy, xx = np.mgrid[0:g.land.shape[0]:s, 0:g.land.shape[1]:s]
        row[2].quiver(xx, yy, fields["u"][k][::s, ::s], -fields["v"][k][::s, ::s], color=INK, scale=150, width=0.003)
        row[2].set_title(f"Precipitable water (mm) and surface wind, month {mo}", loc="left")
        fig.colorbar(im, ax=row[2], shrink=0.8)
        for ax in row:
            ax.contour(land, levels=[0.5], colors=[INK], linewidths=0.7)
            ax.contour(g.inmap.astype(float), levels=[0.5], colors=["#c8452f"], linewidths=0.9, linestyles="dashed")
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"{a.region}: rain and its supply (dashed: scored map)", x=0.01, ha="left")
    fig.savefig(a.out / "rain.png", dpi=90, facecolor=SURFACE)
    print("wrote", a.out / "rain.png")


if __name__ == "__main__":
    main()
