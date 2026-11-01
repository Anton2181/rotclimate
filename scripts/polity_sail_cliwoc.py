"""Sailing-speed shape constants from CLIWOC logbooks (calibration/polity_20261025/addendum_sailing_cliwoc_20261101.json).

    python -I scripts/polity_sail_cliwoc.py --out output/polity_sail_20261101

Daily runs of sailing ships (consecutive noon positions of one ship) against
the wind logged on the first day give the light-wind factor (full speed from
FULL_WIND, at least LIGHT_AIRS of it) and the close-hauled share; the fair
speed stays Casson's. The constants are then tested on Casson (T6) and ORBIS
(T7) as scripts/polity_sail_check.py defines them.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025/addendum_sailing_cliwoc_20261101.json"
DB = ROOT / "data/cache/cliwoc/cliwoc21.gpkg"


def runs():
    c = sqlite3.connect(str(DB))
    rows = c.execute("select ID, YR, MO, DY, latitude, longitude, D, W from CLIWOC21 "
                     "where latitude is not null and longitude is not null and YR is not null and MO is not null and DY is not null").fetchall()
    by = {}
    for sid, yr, mo, dy, la, lo, d, w in rows:
        try:
            k = date(int(yr), int(mo), int(dy)).toordinal()
        except (ValueError, TypeError):
            continue
        by.setdefault(sid, {})[k] = (float(la), float(lo), d, w)
    out = []
    for sid, days in by.items():
        for k, (la, lo, d, w) in days.items():
            nxt = days.get(k + 1)
            if nxt is None or d is None or w is None or not (1 <= int(d) <= 360) or float(w) <= 0:
                continue
            la2, lo2 = nxt[0], nxt[1]
            p1, p2 = np.radians([la, lo]), np.radians([la2, lo2])
            dist = 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((p2[0] - p1[0]) / 2) ** 2 + np.cos(p1[0]) * np.cos(p2[0]) * np.sin((p2[1] - p1[1]) / 2) ** 2))
            if not 5.0 <= dist <= 450.0:
                continue
            y = np.sin(p2[1] - p1[1]) * np.cos(p2[0]); x = np.cos(p1[0]) * np.sin(p2[0]) - np.sin(p1[0]) * np.cos(p2[0]) * np.cos(p2[1] - p1[1])
            course = (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0
            down = (float(d) + 180.0) % 360.0
            theta = abs((course - down + 180.0) % 360.0 - 180.0)
            out.append((dist, theta, float(w)))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_sail_20261101")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    R = runs()
    dist, theta, w = R[:, 0], R[:, 1], R[:, 2]
    fair = np.median(dist[(theta <= 60) & (w >= 10)])
    r = dist / fair
    print(f"{len(R)} daily runs; fair run (theta <= 60, W >= 10 m/s) median {fair:.0f} km/day", flush=True)
    bins = np.arange(1, 21)
    med = np.array([np.median(r[(theta <= 90) & (w >= b - 0.5) & (w < b + 0.5)]) if ((theta <= 90) & (w >= b - 0.5) & (w < b + 0.5)).sum() >= 30 else np.nan for b in bins])
    n = np.array([((theta <= 90) & (w >= b - 0.5) & (w < b + 0.5)).sum() for b in bins])
    ok = np.isfinite(med)
    best = None
    for fw in np.arange(3.0, 15.01, 0.25):
        for la in np.arange(0.1, 0.8, 0.01):
            g = np.clip(bins[ok] / fw, la, 1.0)
            e = float(np.sum((g - med[ok]) ** 2))
            if best is None or e < best[0]:
                best = (e, float(fw), float(la))
    _, FW, LA = best
    ch = (theta >= 95) & (theta <= 115) & (w >= FW)
    share = float(np.median(r[ch]))
    polar = {f"{lo}-{lo + 15}": float(np.median(r[(theta >= lo) & (theta < lo + 15) & (w >= FW)])) for lo in range(0, 180, 15)}
    res = dict(addendum=str(PLAN.relative_to(ROOT)), daily_runs=int(len(R)), fair_km_day=float(fair),
               wind_bins=dict(w=bins.tolist(), median_r=[None if not np.isfinite(x) else float(x) for x in med], n=n.tolist()),
               FULL_WIND=FW, LIGHT_AIRS=LA, CLOSE_HAULED_SHARE=share, close_hauled_n=int(ch.sum()), polar_by_theta=polar)
    print(json.dumps({k: v for k, v in res.items() if k != "wind_bins"}, indent=1), flush=True)
    print("r by wind (m/s):", {int(b): round(float(m), 2) for b, m in zip(bins, med) if np.isfinite(m)}, flush=True)
    # tests: T6 / T7 with the CLIWOC constants against today's
    import polity_sail_check as SC
    from polity import transport as X
    SC.VARIANTS = {"V0": (0.85, 5.0), "CLIWOC": (share, 5.0)}
    old = (X.FULL_WIND, X.LIGHT_AIRS)

    def set_variant(sh, kn, name=None):
        X.CLOSE_HAULED_SHARE, X.SAIL_FAIR_KNOTS = sh, kn
        X.FULL_WIND, X.LIGHT_AIRS = (FW, LA) if abs(sh - share) < 1e-12 and sh != 0.85 else old
        X.POLAR_MEAN = float(X.polar(np.linspace(0.0, 180.0, 1801)).mean())
    SC.set_variant = set_variant
    sys.argv = ["polity_sail_check.py", "--out", str(a.out / "cliwoc_tests")]
    SC.PLAN = PLAN
    try:
        SC.main()
    except KeyError:
        pass
    t = json.loads((a.out / "cliwoc_tests" / "sail.json").read_text())
    v0, vc = t["variants"]["V0"], t["variants"]["CLIWOC"]
    adopted = (vc["T7"]["spearman"] >= v0["T7"]["spearman"] - 0.01 and vc["T7"]["median_abs_log"] < v0["T7"]["median_abs_log"]
               and vc["T6"]["median_abs_log"] <= v0["T6"]["median_abs_log"])
    res.update(T6=dict(V0={k: v0["T6"][k] for k in ("spearman", "median_ratio", "median_abs_log", "west_median_ratio", "long_median_ratio")},
                       CLIWOC={k: vc["T6"][k] for k in ("spearman", "median_ratio", "median_abs_log", "west_median_ratio", "long_median_ratio")}),
               T7=dict(V0={k: v0["T7"][k] for k in ("spearman", "median_ratio", "median_abs_log")},
                       CLIWOC={k: vc["T7"][k] for k in ("spearman", "median_ratio", "median_abs_log")}),
               adopted=bool(adopted), rule=json.loads(PLAN.read_text())["adopt_if"])
    (a.out / "cliwoc.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(T6=res["T6"], T7=res["T7"], adopted=adopted), indent=1))


if __name__ == "__main__":
    main()
