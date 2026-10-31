"""Season checks at stations for the seasons addendum (calibration/polity_20261025/addendum_seasons_20261031.json).

    python -I scripts/polity_season_stations.py --out output/polity_seasons_20261031

Mud months with and without the 25 mm topsoil layer at Kyiv, Moscow, Rome,
Patna, Cairo and Beijing from WorldClim 2.1 5' station-point climate, and the
monsoon-coast diagnostic (onshore component of the NCEP vector-mean wind at
Konkan, Coromandel, the Alexandria approaches and the Gulf of Lion).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from polity import seasons as S  # noqa: E402

STATIONS = {"Kyiv": (50.45, 30.52), "Moscow": (55.75, 37.62), "Rome": (41.90, 12.50), "Patna": (25.60, 85.10),
            "Cairo": (30.04, 31.24), "Beijing": (39.90, 116.40)}
COASTS = {"Konkan (16 N, 71 E)": (16.0, 71.0, 73.0), "Coromandel (13 N, 81 E)": (13.0, 81.0, 80.2),
          "Alexandria approaches (31.5 N, 29.9 E)": (31.5, 29.9, None), "Gulf of Lion (42.5 N, 4.5 E)": (42.5, 4.5, None)}


def station_climate(lat, lon):
    from rotclimate.earth import _wc
    ny, nx = 2160, 4320; res = 180.0 / ny
    i, j = int((90.0 - lat) / res), int((lon + 180.0) / res)
    out = {}
    for var in ("tavg", "tmax", "tmin", "prec"):
        vals = []
        for m in range(1, 13):
            a = _wc(var, m)[i - 1:i + 2, j - 1:j + 2]
            vals.append(float(np.nanmean(a)))
        out[var] = np.array(vals)[:, None]
    return out


def ncep(var):
    z = np.load(ROOT / "data/cache/ncep_ltm/ncep_surface_ltm.npz")
    return z[var], z["lat"], z["lon"]


def at(a, lat, lon, la, lo):
    from scipy import ndimage as ndi
    step = float(lat[0] - lat[1]); r = (lat[0] - la) / step; c = ((lo - lon[0]) / step) % len(lon)
    return np.array([float(ndi.map_coordinates(a[m], [[r], [c]], order=1, mode="wrap")[0]) for m in range(12)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_seasons_20261031")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = json.loads((ROOT / "calibration/polity_20261025/addendum_seasons_20261031.json").read_text())
    res = dict(addendum="calibration/polity_20261025/addendum_seasons_20261031.json", stations={})
    for name, (la, lo) in STATIONS.items():
        c = station_climate(la, lo)
        row = {}
        for label, top in (("before", 0.0), ("topsoil", 25.0)):
            f = S.fields(c["tavg"], c["tmax"], c["tmin"], c["prec"], np.array([la]), topsoil_mm=top)
            row[label] = dict(mud=[round(float(x), 2) for x in f["mud"][:, 0]], snow=[int(x) for x in f["snow"][:, 0]],
                              runoff=[round(float(x), 1) for x in f["runoff"][:, 0]])
        row["climate"] = {k: [round(float(x), 1) for x in v[:, 0]] for k, v in c.items()}
        res["stations"][name] = row
    M = S.MONTHS
    mud = lambda name, when="topsoil": dict(zip(M, res["stations"][name][when]["mud"]))
    kyiv = sum(mud("Kyiv")[m] >= 0.5 for m in ("Mar", "Apr", "Oct", "Nov"))
    moscow = mud("Moscow")["Apr"] >= 0.5 and (mud("Moscow")["Oct"] >= 0.5 or mud("Moscow")["Nov"] >= 0.5)
    new = lambda name, months: [m for m in months if mud(name)[m] >= 0.5 > mud(name, "before")[m]]
    no_new = dict(Rome=new("Rome", ["Jun", "Jul", "Aug", "Sep"]), Patna=new("Patna", ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"]),
                  Cairo=new("Cairo", M), Beijing=new("Beijing", ["Oct", "Nov", "Dec", "Jan", "Feb"]))
    res["autumn_mud"] = dict(kyiv_months=int(kyiv), kyiv_before=int(sum(mud("Kyiv", "before")[m] >= 0.5 for m in ("Mar", "Apr", "Oct", "Nov"))),
                             moscow_passes=bool(moscow), no_new_mud_failures=no_new,
                             runoff_unchanged=all(res["stations"][n]["before"]["runoff"] == res["stations"][n]["topsoil"]["runoff"] for n in STATIONS),
                             adopted=bool(kyiv >= 3 and moscow and not any(no_new.values())), rule=plan["autumn_mud"]["adopt_if"])
    u, lat, lon = ncep("u"); v, _, _ = ncep("v")
    coasts = {}
    for name, (la, lo, _) in COASTS.items():
        uu, vv = at(u, lat, lon, la, lo), at(v, lat, lon, la, lo)
        coasts[name] = dict(u=[round(float(x), 2) for x in uu], v=[round(float(x), 2) for x in vv])
    # onshore direction: toward the nearest land, from the WorldClim land mask
    from rotclimate.earth import _wc
    land = np.isfinite(_wc("tavg", 1)); res5 = 180.0 / land.shape[0]
    for name, (la, lo, _) in COASTS.items():
        i0, j0 = int((90 - la) / res5), int((lo + 180) / res5)
        r = 120
        sub = land[max(0, i0 - r):i0 + r + 1, j0 - r:j0 + r + 1]
        ii, jj = np.nonzero(sub)
        dy = -(ii + max(0, i0 - r) - i0) * res5 * 111.2; dx = (jj + j0 - r - j0) * res5 * 111.2 * np.cos(np.radians(la))
        k = np.argmin(np.hypot(dx, dy)); d = np.hypot(dx[k], dy[k]); ex, ey = dx[k] / d, dy[k] / d
        on = np.array(coasts[name]["u"]) * ex + np.array(coasts[name]["v"]) * ey
        cls = ["closed" if o >= 8.0 else "uncertain" if o >= 5.5 else "open" for o in on]
        coasts[name].update(onshore=[round(float(x), 2) for x in on], classes=dict(zip(M, cls)), coast_km=round(float(d), 1))
    k, c, al, gl = (coasts[n]["classes"] for n in COASTS)
    expectations = {"Konkan": all(k[m] != "open" for m in ("Jun", "Jul", "Aug")) and all(k[m] == "open" for m in ("Dec", "Jan", "Feb")),
                    "Coromandel": c["Nov"] != "open" and c["Mar"] == "open" and c["Apr"] == "open",
                    "Alexandria": all(al[m] == "open" for m in ("Jun", "Jul", "Aug")),
                    "Gulf of Lion": all(gl[m] == "open" for m in ("Jun", "Jul", "Aug"))}
    res["monsoon_coasts"] = dict(coasts=coasts, expectations=expectations)
    (a.out / "stations.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(autumn_mud=res["autumn_mud"], expectations=expectations,
                          mud={n: dict(before=res["stations"][n]["before"]["mud"], after=res["stations"][n]["topsoil"]["mud"]) for n in STATIONS},
                          coasts={n: dict(onshore=coasts[n]["onshore"], classes=list(coasts[n]["classes"].values())) for n in COASTS}), indent=1))


if __name__ == "__main__":
    main()
