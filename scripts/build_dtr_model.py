"""Build data/dtr_knn.npz: the Earth-trained day/night range model
(see rotclimate/diurnal.py).

Samples 100,000 WorldClim 2.1 land cells (5 arc-min) between 8 and 62 deg
latitude, computes the model inputs (distance to the sea from the WorldClim
coastline), reports a cross-validated score holding out one 60-degree
longitude sector at a time, and saves the standardised rows.

Inputs (downloaded separately into data/cache/worldclim/, see README):
  wc2.1_5m_{tavg,tmin,tmax,prec,elev}.zip
Run with:  python -I scripts/build_dtr_model.py <repo root>
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(ROOT))
from rotclimate.diurnal import FEATURES, K, features  # noqa: E402

WC = ROOT / "data" / "cache" / "worldclim"
OUT = ROOT / "data" / "dtr_knn.npz"
N_CELLS = 100_000


def grid(var, month=None):
    member = f"wc2.1_5m_{var}.tif" if month is None else f"wc2.1_5m_{var}_{month:02d}.tif"
    im = Image.open(io.BytesIO(zipfile.ZipFile(WC / f"wc2.1_5m_{var}.zip").read(member)))
    a = np.array(im, dtype=np.float32)
    nd = im.tag_v2.get(42113)
    if nd is not None:
        a[a == np.float32(float(str(nd).strip("\x00 ")))] = np.nan
    a[a < -1e30] = np.nan
    return a


def unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)


def main():
    elev = grid("elev")
    ny, nx = elev.shape
    lat = 90 - (np.arange(ny) + 0.5) / 12
    lon = -180 + (np.arange(nx) + 0.5) / 12
    land = np.isfinite(elev)
    coast = ~land & ndi.binary_dilation(land)
    cy, cx = np.nonzero(coast)
    ly, lx = np.nonzero(land & (np.abs(lat)[:, None] > 8) & (np.abs(lat)[:, None] < 62))
    rng = np.random.default_rng(0)
    pick = rng.choice(ly.size, N_CELLS, replace=False)
    ly, lx = ly[pick], lx[pick]
    dist = cKDTree(unit(lat[cy], lon[cx])).query(unit(lat[ly], lon[lx]))[0] * 6371.0
    T = np.stack([grid("tavg", m)[ly, lx] for m in range(1, 13)])
    P = np.stack([grid("prec", m)[ly, lx] for m in range(1, 13)])
    D = np.stack([grid("tmax", m)[ly, lx] - grid("tmin", m)[ly, lx] for m in range(1, 13)])
    ok = np.isfinite(T).all(0) & np.isfinite(P).all(0) & np.isfinite(D).all(0)
    T, P, D = T[:, ok], P[:, ok], D[:, ok]
    X = features(T, P, elev[ly, lx][ok], dist[ok], lat[ly][ok])
    y = D.reshape(-1)
    mu, sd = X.mean(0), X.std(0)
    Z = (X - mu) / sd
    # cross-validation: hold out one 60-degree longitude sector at a time
    sector = np.broadcast_to(((lon[lx][ok] + 180) // 60).astype(int), T.shape).reshape(-1)
    err = np.empty_like(y)
    for s in np.unique(sector):
        tr, te = sector != s, sector == s
        dd, ii = cKDTree(Z[tr]).query(Z[te], k=K, workers=-1)
        w = 1.0 / (dd + 0.05)
        err[te] = (y[tr][ii] * w).sum(1) / w.sum(1) - y[te]
    r2 = 1 - (err ** 2).mean() / y.var()
    print(f"{ok.sum()} cells x 12 months; day/night range {y.mean():.1f} +- {y.std():.1f} C")
    print(f"held-out continents: R2 {r2:.3f}, mean abs error {np.abs(err).mean():.2f} C")
    keep = rng.choice(y.size, 120_000, replace=False)
    np.savez_compressed(OUT, z=Z[keep].astype(np.float16), y=y[keep].astype(np.float16),
                        mu=mu.astype(np.float32), sd=sd.astype(np.float32),
                        features=np.array(FEATURES), r2=np.float32(r2), mae=np.float32(np.abs(err).mean()))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
