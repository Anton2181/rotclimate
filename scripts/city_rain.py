"""Rainfall at real cities: how close is the model to each city's own normals?

    python3 -I scripts/city_rain.py RUN [RUN ...] --out output/city_rain/r35.json

RUN is a benchmark_local.py output folder (its cells/*.npz). Every GeoNames
city of 50,000+ in data/real_cities_worldclim.csv (WorldClim 2.1 at 5 arc-min,
1970-2000) that lies within 40 km of a scored cell centre is compared with
that cell's simulated monthly rain. The same comparison for the observed
56 km cell mean (WorldClim aggregated to the cell) is the floor a perfect
56 km model would still miss by: rain that varies inside one cell.

With several runs, the first is the reference and later runs report how many
cities got closer.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CITIES = ROOT / "data" / "real_cities_worldclim.csv"
MAX_KM = 40.0


def cities():
    with open(CITIES, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    return [dict(name=r["name"], country=r["country"], lat=float(r["lat"]), lon=float(r["lon"]),
                 population=int(float(r["population"] or 0)), P=np.array([float(r[f"P{m}"]) for m in range(1, 13)]))
            for r in rows]


def km(lat1, lon1, lat2, lon2):
    r = np.pi / 180
    c = np.sin(lat1 * r) * np.sin(lat2 * r) + np.cos(lat1 * r) * np.cos(lat2 * r) * np.cos((lon1 - lon2) * r)
    return 6371 * np.arccos(np.clip(c, -1, 1))


def match(run: Path, towns):
    """City rows with the containing cell's simulated and observed monthly rain."""
    out, seen = [], set()
    for path in sorted((run / "cells").glob("*.npz")):
        z = np.load(path)
        for t in towns:
            d = km(t["lat"], t["lon"], z["lat"], z["lon"])
            k = int(np.argmin(d))
            if d[k] > MAX_KM or (t["name"], t["lat"]) in seen:
                continue
            seen.add((t["name"], t["lat"]))
            out.append(dict(region=path.stem, name=t["name"], country=t["country"], population=t["population"],
                            lat=t["lat"], lon=t["lon"], obs=t["P"], sim=z["Ps"][:, k].astype(float),
                            cell=z["Po"][:, k].astype(float)))
    return out


def stats(obs, sim):
    oa, sa = obs.sum(1), sim.sum(1)
    rel = np.abs(sa - oa) / np.maximum(oa, 1)
    of = obs / np.maximum(oa, 1e-9)[:, None]
    sf = sim / np.maximum(sa, 1e-9)[:, None]
    return dict(cities=int(len(oa)),
                annual_log_rmse=float(np.sqrt(np.mean(np.log((sa + 50) / (oa + 50)) ** 2))),
                annual_median_abs_error_pct=float(100 * np.median(rel)),
                within_25pct=float(np.mean(rel <= 0.25)), within_50pct=float(np.mean(rel <= 0.5)),
                annual_bias_pct=float(100 * np.median((sa - oa) / np.maximum(oa, 1))),
                monthly_mae_mm=float(np.abs(sim - obs).mean()),
                seasonality_tv=float(np.mean(0.5 * np.abs(sf - of).sum(1))))


def summarise(rows):
    obs = np.array([r["obs"] for r in rows]); sim = np.array([r["sim"] for r in rows]); cell = np.array([r["cell"] for r in rows])
    regions = sorted({r["region"] for r in rows})
    by_region = {}
    for g in regions:
        m = np.array([r["region"] == g for r in rows])
        by_region[g] = dict(model=stats(obs[m], sim[m]), floor=stats(obs[m], cell[m]))
    return dict(model=stats(obs, sim), floor_56km=stats(obs, cell), regions=by_region)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--worst", type=int, default=15)
    a = ap.parse_args()
    towns = cities()
    results, ref_rows = {}, None
    for run in a.runs:
        rows = match(run, towns)
        s = summarise(rows)
        m, f = s["model"], s["floor_56km"]
        print(f"{run}: {m['cities']} cities · annual median error {m['annual_median_abs_error_pct']:.0f}% "
              f"(56 km floor {f['annual_median_abs_error_pct']:.0f}%) · within 25% {m['within_25pct']:.1%} "
              f"(floor {f['within_25pct']:.1%}) · log RMSE {m['annual_log_rmse']:.3f} (floor {f['annual_log_rmse']:.3f}) · "
              f"monthly MAE {m['monthly_mae_mm']:.1f} mm (floor {f['monthly_mae_mm']:.1f}) · median bias {m['annual_bias_pct']:+.0f}%")
        if ref_rows is None:
            ref_rows = rows
            err = [abs(np.log((r["sim"].sum() + 50) / (r["obs"].sum() + 50))) for r in rows]
            worst = [rows[i] for i in np.argsort(err)[::-1][:a.worst]]
            s["worst"] = [dict(name=r["name"], country=r["country"], region=r["region"], obs_mm=round(float(r["obs"].sum())),
                               sim_mm=round(float(r["sim"].sum())), cell_obs_mm=round(float(r["cell"].sum()))) for r in worst]
            for w in s["worst"]:
                print(f"   {w['name']:22s} {w['country']:16s} {w['region']:16s} observed {w['obs_mm']:5d} · model {w['sim_mm']:5d} · cell {w['cell_obs_mm']:5d} mm")
        else:
            ref = {(r["name"], r["lat"]): r for r in ref_rows}
            closer = worse = 0
            for r in rows:
                q = ref.get((r["name"], r["lat"]))
                if q is None:
                    continue
                e0 = abs(np.log((q["sim"].sum() + 50) / (q["obs"].sum() + 50)))
                e1 = abs(np.log((r["sim"].sum() + 50) / (r["obs"].sum() + 50)))
                closer += e1 < e0 - 0.01; worse += e1 > e0 + 0.01
            s["vs_reference"] = dict(closer=int(closer), further=int(worse))
            print(f"   annual total closer at {closer} cities, further at {worse}")
        results[str(run)] = s
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
