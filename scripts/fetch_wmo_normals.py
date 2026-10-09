"""Build data/real_cities_wmo.csv from the WMO World Weather Information Service.

The WMO publishes official climate normals (monthly mean max/min temperature
and precipitation) for ~3,600 cities as JSON. This script downloads them and
writes the CSV the analogue matching (rotclimate/analogs.py) reads: stations far
from any city in data/real_cities_worldclim.csv become reference places, and
scripts/build_reference.py uses the rest to cross-check the city normals.

    python scripts/fetch_wmo_normals.py            # needs worldweather.wmo.int

Monthly mean temperature is the published mean where given, else
(mean max + mean min) / 2. Raw responses are cached in data/wmo_cache/.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://worldweather.wmo.int/en/json"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "real_cities_wmo.csv"
CACHE = ROOT / "data" / "wmo_cache"


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(1.5 * 2 ** i)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch_city(cid):
    path = CACHE / f"{cid}.json"
    if path.exists():
        return json.loads(path.read_text())
    txt = get(f"{BASE}/{cid}_en.json")
    path.write_text(txt)
    return json.loads(txt)


def parse(country, city, cid):
    d = fetch_city(cid)["city"]
    clim = d.get("climate") or {}
    months = clim.get("climateMonth") or []
    if len(months) < 12:
        raise ValueError("no monthly climate")
    T, P, D = [], [], []
    for m in sorted(months, key=lambda m: int(m["month"]))[:12]:
        mean, hi, lo, pr = (num(m.get(k)) for k in ("meanTemp", "maxTemp", "minTemp", "rainfall"))
        if mean is None and hi is not None and lo is not None:
            mean = (hi + lo) / 2
        if mean is None or pr is None:
            raise ValueError("incomplete months")
        T.append(round(mean, 1))
        P.append(round(pr))
        D.append(round(hi - lo, 1) if hi is not None and lo is not None and hi >= lo else None)
    if any(v is None for v in D):              # day/night range only when every month has it
        D = [""] * 12
    lat, lon = num(d.get("cityLatitude")), num(d.get("cityLongitude"))
    if lat is None or lon is None:
        raise ValueError("no coordinates")
    period = ""
    if clim.get("tempb") and clim.get("tempe"):
        period = f"{clim['tempb']}-{clim['tempe']}"
    return [d.get("cityName") or city, country, round(lat, 3), round(lon, 3), "", period] + T + P + D


def main(limit=None, workers=8):
    CACHE.mkdir(parents=True, exist_ok=True)
    lst = get(f"{BASE}/full_city_list.txt").splitlines()
    jobs = []
    for line in lst[1:limit]:
        parts = [p.strip().strip('"') for p in line.split(";")]
        if len(parts) >= 3 and parts[2].isdigit():
            jobs.append((parts[0], parts[1], parts[2]))
    rows, skipped = [], 0

    def work(job):
        try:
            return parse(*job)
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(work, jobs), 1):
            if r is None:
                skipped += 1
            else:
                rows.append(r)
            if i % 250 == 0:
                print(f"{i}/{len(jobs)} fetched, {len(rows)} usable", flush=True)
    rows.sort(key=lambda r: (r[1], r[0]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        f.write("# Official WMO World Weather Information Service climate normals "
                "(worldweather.wmo.int), fetched by scripts/fetch_wmo_normals.py\n")
        w = csv.writer(f)
        w.writerow(["name", "country", "lat", "lon", "elev", "period"]
                   + [f"T{i}" for i in range(1, 13)] + [f"P{i}" for i in range(1, 13)]
                   + [f"D{i}" for i in range(1, 13)])
        w.writerows(rows)
    print(f"wrote {OUT}: {len(rows)} cities ({skipped} without usable normals)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
