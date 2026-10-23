"""The great cities of AD 100-200 against the settlement model (and HYDE).

    python3 -I scripts/great_cities_check.py --csv data/cache/reba2016/modelskiAncientV2.csv \
        --earth output/land_people/earth/earth.npz --hyde data/cache/hyde33/popc_ce_200.tif

Cities: Modelski (2003) ancient city sizes, geocoded by Reba, Reitsma & Seto
(2016), Sci. Data 3:160034 (figshare, CC BY 4.0): every city with a size at
AD 100 or 200 inside the Earth window. Each field is averaged within 100 km
of each city (land cells), and the city's value is placed among the same
100 km means of all land cells: its percentile. A model that puts people
where the great cities were gives high percentiles. Seventeen-odd cities make
this a coarse check, reported city by city. Cities within 500 km of a
declared core score high by construction (Rome is one), so the summary is
repeated without them.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from harvest_earth_hyde import earth_stages  # noqa: E402
from hyde_compare import hyde_at  # noqa: E402
from population_cores import CORE_SETS, core_distance, core_term, travel_distance  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True); ap.add_argument("--earth", required=True); ap.add_argument("--hyde")
    ap.add_argument("--reliability", help="START,FULL,POWER of harvest.models.harvest_reliability (default none)")
    ap.add_argument("--margins", help="T0,T1,A0,A1 of harvest.models.margin_reliability (default none)")
    a = ap.parse_args()
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    mg = [float(x) for x in a.margins.split(",")] if a.margins else None
    km2, stages = earth_stages(z, reliability=tuple(map(float, a.reliability.split(","))) if a.reliability else None,
                               margins=((mg[0], mg[1]), (mg[2], mg[3])) if mg else None)
    base = np.nan_to_num(stages["+ malaria (settlement base)"])
    fields = {"settlement base": base,
              "× old cores (travel, L 800)": base * core_term(travel_distance(z, CORE_SETS["cradles + Rome"], 2.0, 1.0, 1.0), 800)}
    if a.hyde:
        fields["HYDE 3.3, 200 CE"] = hyde_at(a.hyde, lat, lon) / km2
    rows = list(csv.DictReader(open(a.csv, encoding="latin-1")))
    cities = []
    for r in rows:
        size = max([float(r[k]) for k in ("AD_100", "AD_200") if r.get(k)] or [0])
        if size <= 0:
            continue
        la, lo = float(r["Latitude"]), float(r["Longitude"])
        if lat.min() <= la <= lat.max() and lon.min() <= lo <= lon.max():
            cities.append((r["City"], la, lo, size))
    cities.sort(key=lambda c: -c[3])
    win = 23                                            # 5' cells: ~100 km half-width at mid-latitudes
    print(f"{len(cities)} cities with a size at AD 100 or 200 in the window")
    header = f"{'city':14s} {'size':>8s} " + " ".join(f"{k[:24]:>26s}" for k in fields)
    print(header)
    pct = {}
    for k, f in fields.items():
        m = uniform_filter(np.where(land, f, 0.0), win) / np.maximum(uniform_filter(land.astype(float), win), 1e-9)
        ref = np.sort(m[land])
        vals = []
        for name, la, lo, size in cities:
            i, j = int(np.argmin(np.abs(lat - la))), int(np.argmin(np.abs(lon - lo)))
            vals.append(100.0 * np.searchsorted(ref, m[i, j]) / len(ref))
        pct[k] = vals
    for n, (name, la, lo, size) in enumerate(cities):
        print(f"{name[:14]:14s} {size:8.0f} " + " ".join(f"{pct[k][n]:25.0f}%" for k in fields))
    far = np.array([core_distance(np.array([la]), np.array([lo]), CORE_SETS["cradles + Rome"])[0, 0] > 500.0
                    for _, la, lo, _ in cities])
    for label, sel in (("all", np.ones(len(cities), bool)), (f"{int(far.sum())} beyond 500 km of a core", far)):
        print(f"{'median, ' + label:23s} " + " ".join(f"{np.median(np.array(pct[k])[sel]):25.0f}%" for k in fields))
        print(f"{'top decile, ' + label:23s} " + " ".join(f"{np.mean(np.array(pct[k])[sel] >= 90):26.0%}" for k in fields))


if __name__ == "__main__":
    main()
