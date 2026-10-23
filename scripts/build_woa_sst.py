"""Monthly sea-surface temperature climatology from the World Ocean Atlas 2018
(objectively analysed mean, all decades, 1 degree), for Earth-mode checks of
the model's sea surface.

    python3 -I scripts/build_woa_sst.py data/cache/woa18 data/cache/earth/woa18_sst_1deg.npz

Input: woa18_decav_tMMan01.csv.gz from
https://www.ncei.noaa.gov/data/oceans/woa/WOA18/DATA/temperature/csv/decav/1.00/
(Locarnini et al. 2018, NOAA Atlas NESDIS 81). Only the 0 m column is read.
Output: sst [12, 180, 360] deg C (NaN over land), lat/lon cell centres,
and the SHA-256 of every source file.
"""
import csv
import gzip
import hashlib
import sys
from pathlib import Path

import numpy as np


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    sst = np.full((12, 180, 360), np.nan, np.float32)
    hashes = {}
    for m in range(12):
        f = src / f"woa18_decav_t{m + 1:02d}an01.csv.gz"
        hashes[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        with gzip.open(f, "rt") as fh:
            for row in csv.reader(fh):
                if not row or row[0].startswith("#") or len(row) < 3 or row[2].strip() == "":
                    continue
                lat, lon, v = float(row[0]), float(row[1]), float(row[2])
                i, j = int(np.floor(lat + 90.0)), int(np.floor(lon + 180.0))
                if 0 <= i < 180 and 0 <= j < 360 and -3.0 < v < 40.0:
                    sst[m, i, j] = v
    lat = np.arange(180) - 89.5
    lon = np.arange(360) - 179.5
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, sst=sst, lat=lat, lon=lon, sources=np.array(sorted(hashes.items())))
    print(f"{out}: {np.isfinite(sst[0]).sum()} ocean cells; Jan mean {np.nanmean(sst[0]):.2f} C, Jul {np.nanmean(sst[6]):.2f} C")


if __name__ == "__main__":
    main()
