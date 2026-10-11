"""Export the map and its calibrated surroundings as ExoPlaSim boundary files.

ExoPlaSim (Paradise et al. 2022) is a fast 3-D climate model. It has no
reversed-spin option, but reversed spin with the sun crossing the sky the
other way is the same physics as Earth's spin on the east-west mirror image
of the map (Mikolajewicz et al. 2018 found the remaining difference
negligible), so --mirror writes the mirrored map for a reversed-spin run.

The rotclimate grid (the map plus its procedural surroundings, ~1,100 km on
each side) is placed on the globe with the map centre at 180 deg E; beyond
it is open ocean. Each GCM cell gets the land fraction and mean land height
of the rotclimate cells inside it; it is land where that fraction is >= 0.5.

Writes <out>/<name>_surf_0172.sra (land mask), <name>_surf_0129.sra
(surface geopotential, m2/s2) and <name>_map.npz (lat/lon of every map cell,
for sampling the GCM output back onto the map).

    python scripts/exoplasim_export.py calibration/round17_earthlike.json --res T21 --out exo/earthlike
    python scripts/exoplasim_export.py calibration/round17_retrograde.json --res T21 --mirror --out exo/retro
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rotclimate.config import Params  # noqa: E402
from rotclimate.geography import build_grid  # noqa: E402

G0 = 9.80665
KM_PER_DEG = 111.195
NLAT = {"T21": 32, "T42": 64, "T63": 96}


def gcm_grid(res):
    nlat = NLAT[res]
    x, _ = np.polynomial.legendre.leggauss(nlat)
    lat = np.degrees(np.arcsin(x))[::-1]                      # north to south
    lon = np.arange(2 * nlat) * 360.0 / (2 * nlat)
    edges = np.concatenate([[90.0], 0.5 * (lat[1:] + lat[:-1]), [-90.0]])
    return lat, lon, edges


def write_sra(path, kcode, field):
    nlat, nlon = field.shape
    header = "".join(f" {h:11d}" for h in (kcode, 0, 20170927, 0, nlon, nlat, 0, 0))
    rows = field.reshape(-1, 8)
    Path(path).write_text(header + "\n" + "\n".join("".join(f" {v:9.3f}" for v in r) for r in rows) + "\n")


def export(params_path, res, mirror, out, name):
    p = Params.from_json(params_path)
    g = build_grid(p)
    lat2 = g.lat
    ny, nx = lat2.shape
    xkm = (np.arange(nx) - (nx - 1) / 2) * g.cell_km
    if mirror:
        xkm = -xkm
    lon2 = 180.0 + xkm[None, :] / (KM_PER_DEG * np.cos(np.radians(lat2)))
    lat, lon, edges = gcm_grid(res)
    dlon = 360.0 / lon.size
    iy = np.clip(np.searchsorted(-edges, -lat2, side="right") - 1, 0, lat.size - 1)
    ix = np.round(lon2 / dlon).astype(int) % lon.size
    land_sum = np.zeros((lat.size, lon.size))
    elev_sum = np.zeros_like(land_sum)
    np.add.at(land_sum, (iy, ix), g.land_frac)
    np.add.at(elev_sum, (iy, ix), g.land_frac * np.maximum(g.elev, 0.0))
    # area of each GCM cell in rotclimate cells: uncovered parts are ocean
    band = np.radians(edges[:-1]) - np.radians(edges[1:])
    cell_area = (KM_PER_DEG * np.degrees(1.0)) ** 2 * np.radians(dlon) * (
        np.sin(np.radians(edges[:-1])) - np.sin(np.radians(edges[1:])))
    n_fit = cell_area[:, None] / g.cell_km ** 2
    frac = np.clip(land_sum / n_fit, 0, 1)
    mask = (frac >= 0.5).astype(float)
    height = np.where(mask > 0, elev_sum / np.maximum(land_sum, 1e-9), 0.0)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_sra(out / f"{name}_surf_0172.sra", 172, mask)
    write_sra(out / f"{name}_surf_0129.sra", 129, height * G0)
    np.savez_compressed(out / f"{name}_map.npz", lat=lat2, lon=lon2, inmap=g.inmap, land=g.land,
                        target=g.target, mirror=mirror, gcm_lat=lat, gcm_lon=lon, frac=frac)
    # a quick look at the continent on the GCM grid
    rows = np.flatnonzero(frac.max(1) > 0.05)
    cols = np.flatnonzero(frac.max(0) > 0.05)
    print(f"{name}: {res}, {int(mask.sum())} land cells; continent spans lat {lat[rows].max():.1f} to "
          f"{lat[rows].min():.1f}, lon {lon[cols].min():.1f} to {lon[cols].max():.1f}; tilt {p.tilt:.1f}, "
          f"{'mirrored (reversed spin)' if mirror else 'as drawn (Earth spin)'}")
    for r in range(rows.min(), rows.max() + 1):
        print(f"  {lat[r]:6.1f} " + "".join("#" if mask[r, c] else ("+" if frac[r, c] > 0.2 else ".")
                                          for c in range(cols.min(), cols.max() + 1)))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("params")
    ap.add_argument("--res", default="T21", choices=list(NLAT))
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="rotclimate")
    a = ap.parse_args()
    export(a.params, a.res, a.mirror, a.out, a.name)


if __name__ == "__main__":
    main()
