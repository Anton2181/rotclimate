"""Han AD 2 census by commandery against the settlement model on Earth (and HYDE).

    python3 -I scripts/han_census_check.py --shp data/cache/han_ad2/shp/ResearchArea \
        --earth output/land_people/earth/earth.npz --hyde data/cache/hyde33/popc_ce_0.tif \
        --out output/population_han/ad2.json

Census: Zheng & Wu (2026), Sci. Data 13:876, doi:10.1038/s41597-026-07086-6,
figshare doi:10.6084/m9.figshare.30518417 (CC BY 4.0): 103 commandery and
kingdom polygons of AD 2 with the recorded populations of the Hanshu
(57.7 M). The polygons are in an Albers equal-area projection on the
Krasovsky ellipsoid (central meridian 105 E, standard parallels 25 and 47 N);
the 5 arc-minute cell centres of the Earth run are projected forward into it
(Snyder 1987, eq. 3-12, 14-3 to 14-6) and tested for containment.

The census is a real count inside one state (one technology, one tax
system), so it tests where the environment puts people, not history. Only
the pattern is compared: each field is scaled to the census total over the
commanderies it covers. A commandery is used when at least 90 % of its cells
fall in the Earth window. HYDE 3.3 at 0 CE is scored on the same polygons
for comparison (it has no AD 2 slice; its China total is matched to the
same census, so its inner split is HYDE's own model).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

A_KRA, F_KRA = 6378245.0, 1 / 298.3
LON0, PHI1, PHI2 = 105.0, 25.0, 47.0


def _albers_constants():
    e2 = 2 * F_KRA - F_KRA ** 2
    e = np.sqrt(e2)

    def q(phi):
        s = np.sin(phi)
        return (1 - e2) * (s / (1 - e2 * s * s) - np.log((1 - e * s) / (1 + e * s)) / (2 * e))

    def m(phi):
        s = np.sin(phi)
        return np.cos(phi) / np.sqrt(1 - e2 * s * s)

    p1, p2 = np.radians(PHI1), np.radians(PHI2)
    n = (m(p1) ** 2 - m(p2) ** 2) / (q(p2) - q(p1))
    C = m(p1) ** 2 + n * q(p1)
    rho0 = A_KRA * np.sqrt(C - n * q(0.0)) / n
    return q, n, C, rho0


def albers_forward(lat, lon):
    q, n, C, rho0 = _albers_constants()
    rho = A_KRA * np.sqrt(C - n * q(np.radians(lat))) / n
    th = n * np.radians(lon - LON0)
    return rho * np.sin(th), rho0 - rho * np.cos(th)


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    import shapefile
    from harvest_earth_hyde import earth_stages
    from hyde_compare import hyde_at

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shp", required=True)
    ap.add_argument("--earth", required=True)
    ap.add_argument("--hyde")
    ap.add_argument("--leaching", type=float, default=0.0, help="maximum low-input yield penalty of leached soils (0 = off)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2, stages = earth_stages(z, a.leaching)
    fields = {"crops only": stages["crops only (Earth run)"],
              "crops x clearance + herding": stages["crops x clearance + herding"],
              "settlement base (+ rivers, malaria)": stages["+ malaria (settlement base)"],
              "uniform over land": stages["uniform over land"]}
    if a.hyde:
        fields["HYDE 3.3, 0 CE"] = hyde_at(a.hyde, lat, lon) / km2
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    china = (LA > 15) & (LA < 50) & (LO > 95)
    X, Y = albers_forward(LA[china], LO[china])
    pts = np.column_stack([X, Y])
    ci, cj = np.nonzero(china)

    r = shapefile.Reader(a.shp)
    rows = []
    for shp, rec in zip(r.iterShapes(), r.iterRecords()):
        d = rec.as_dict()
        if d["YEAR"] != "2AD":
            continue
        inside = np.zeros(len(pts), bool)
        parts = list(shp.parts) + [len(shp.points)]
        for k in range(len(parts) - 1):
            ring = np.asarray(shp.points[parts[k]:parts[k + 1]])
            bb = (pts[:, 0] >= ring[:, 0].min()) & (pts[:, 0] <= ring[:, 0].max()) & \
                 (pts[:, 1] >= ring[:, 1].min()) & (pts[:, 1] <= ring[:, 1].max())
            if bb.any():
                hit = np.zeros(len(pts), bool)
                hit[bb] = Poly(ring).contains_points(pts[bb])
                inside ^= hit          # rings alternate outer / hole (even-odd)
        sel_i, sel_j = ci[inside], cj[inside]
        area_cells = float(km2[sel_i, sel_j].sum())
        area_poly = float(d["AREA"])               # km2 in the dataset
        rows.append(dict(name=d["PrefNAM"], pop=float(d["POP"]), area_km2=area_poly, cells=int(inside.sum()),
                         coverage=area_cells / max(area_poly, 1e-9),
                         model={k: float((np.nan_to_num(v[sel_i, sel_j]) * km2[sel_i, sel_j] * land[sel_i, sel_j]).sum())
                                for k, v in fields.items()}))
    use = [x for x in rows if x["coverage"] >= 0.9 and x["cells"] >= 4]
    obs = np.array([x["pop"] for x in use]); area = np.array([x["area_km2"] for x in use])
    res = dict(commanderies_total=len(rows), commanderies_used=len(use), census_used_m=float(obs.sum() / 1e6), stages={})
    print(f"AD 2: {len(rows)} commanderies, {len(use)} with >= 90 % of their area in the Earth window "
          f"({obs.sum() / 1e6:.1f} M people)")
    for k in fields:
        m = np.array([x["model"][k] for x in use])
        m = m * obs.sum() / max(m.sum(), 1e-9)
        dm, do = m / area, obs / area
        v = dict(spearman=spearman(dm, do), moved_share=float(0.5 * np.abs(m / m.sum() - obs / obs.sum()).sum()),
                 log_rmse=float(np.sqrt(np.mean(np.log10((dm + 1) / (do + 1)) ** 2))))
        res["stages"][k] = v
        print(f"  {k:36s} rank corr {v['spearman']:.3f}  people to move {v['moved_share']:.1%}  log10 RMSE {v['log_rmse']:.3f}")
    res["commanderies"] = rows
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
