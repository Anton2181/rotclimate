"""Build data/real_cities_wmo.csv from the WMO World Weather Information Service.

The WMO publishes official climate normals (monthly mean max/min temperature
and precipitation) for ~2000 cities as JSON.  This script downloads them and
writes the same CSV format as data/real_cities_approx.csv; once the file
exists, the analogue matching (rotclimate/analogs.py) uses it automatically.

    python scripts/fetch_wmo_normals.py            # needs worldweather.wmo.int

Monthly mean temperature = (mean max + mean min) / 2.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://worldweather.wmo.int/en/json"
OUT = Path(__file__).resolve().parent.parent / "data" / "real_cities_wmo.csv"


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 ** i)
            last = e  # noqa: F841


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main(limit=None):
    lst = get(f"{BASE}/full_city_list.txt").splitlines()
    rows = []
    for line in lst[1:limit]:
        parts = [p.strip().strip('"') for p in line.split(";")]
        if len(parts) < 3 or not parts[2].isdigit():
            continue
        country, city, cid = parts[0], parts[1], parts[2]
        try:
            d = json.loads(get(f"{BASE}/{cid}_en.json"))["city"]
            months = d["climate"]["climateMonth"]
            T, P = [], []
            for m in sorted(months, key=lambda m: int(m["month"]))[:12]:
                hi, lo, pr = num(m.get("maxTemp")), num(m.get("minTemp")), num(m.get("rainfall"))
                if hi is None or lo is None or pr is None:
                    raise ValueError("incomplete")
                T.append(round((hi + lo) / 2, 1))
                P.append(round(pr))
            if len(T) != 12:
                continue
            rows.append([city, country, num(d.get("cityLatitude")), num(d.get("cityLongitude")), ""]
                        + T + P)
            print(f"{len(rows):5d} {city}, {country}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  skip {city}: {e}", file=sys.stderr)
        time.sleep(0.2)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "country", "lat", "lon", "elev"] + [f"T{i}" for i in range(1, 13)]
                   + [f"P{i}" for i in range(1, 13)])
        w.writerows(rows)
    print("wrote", OUT, len(rows), "cities")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
