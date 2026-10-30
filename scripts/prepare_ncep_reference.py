"""Prepare the NCEP/NCAR Reanalysis 1 monthly surface climatology (1991-2020).

    python -I scripts/prepare_ncep_reference.py --download

Fetches the global 2.5-degree long-term monthly means of the sigma-0.995 winds
and relative humidity, sea-level pressure and precipitable water through the
NOAA PSL THREDDS OPeNDAP text service, then writes
data/cache/ncep_ltm/ncep_surface_ltm.npz (u, v m/s; rh %; slp hPa; pw mm;
[12, 73, 144], latitude 90..-90, longitude 0..357.5). Without --download it
only checks the cache. Reference data for diagnostics (scripts/attribute_observed_forcing.py);
nothing here enters a model run unless wind_source="observed" is asked for.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/ncep_ltm"
OUT = CACHE / "ncep_surface_ltm.npz"
BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/surface/"
FIELDS = dict(u=("uwnd.sig995", "uwnd"), v=("vwnd.sig995", "vwnd"), rh=("rhum.sig995", "rhum"),
              slp=("slp", "slp"), pw=("pr_wtr.eatm", "pr_wtr"))


def fetch(file, var):
    url = f"{BASE}{file}.mon.ltm.nc.ascii?{var}[0:1:11][0:1:72][0:1:143]"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "rotclimate-reference/1.0"}),
                                        timeout=180) as response:
                return url, response.read().decode()
        except Exception as error:                      # the service rate-limits bursts (HTTP 429)
            if attempt == 5:
                raise
            print(f"{file}: {error}; retrying", flush=True)
            time.sleep(10 * (attempt + 1))


def parse(text, var):
    body = text.split("---------------------------", 1)[1]
    a = np.full((12, 73, 144), np.nan, np.float32)
    for line in body.splitlines():
        m = re.match(r"\[(\d+)\]\[(\d+)\], (.*)", line)
        if m:
            a[int(m[1]), int(m[2])] = np.array(m[3].split(","), float)
    lat = np.array(re.search(rf"{var}\.lat\[73\]\s*\n(.*)", body)[1].split(","), float)
    lon = np.array(re.search(rf"{var}\.lon\[144\]\s*\n(.*)", body)[1].split(","), float)
    if not np.isfinite(a).all() or not np.allclose(lat, 90 - 2.5 * np.arange(73)) or not np.allclose(lon, 2.5 * np.arange(144)):
        raise ValueError(f"Unexpected NCEP {var} grid or missing values")
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()
    if args.download and not OUT.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        arrays, sources = {}, {}
        for key, (file, var) in FIELDS.items():
            url, text = fetch(file, var)
            arrays[key] = parse(text, var)
            sources[key] = dict(url=url, sha256=hashlib.sha256(text.encode()).hexdigest())
            print(f"{key}: {file} ok", flush=True)
        np.savez_compressed(OUT, lat=90 - 2.5 * np.arange(73), lon=2.5 * np.arange(144), **arrays)
        (CACHE / "sources.json").write_text(json.dumps(sources, indent=1))
    if not OUT.exists():
        sys.exit(f"Missing {OUT}; run with --download")
    with np.load(OUT) as z:
        print(json.dumps({k: [list(z[k].shape), float(z[k].min()), float(z[k].max())] for k in z.files}))


if __name__ == "__main__":
    main()
