"""Plan D2b (calibration/geography_control_20261107/plan_D1.json, "D2b"): irrigation reach on wide floodplains -
distance scale x height-above-river gate, scored on ranking (AUC) and amount against the 1900 Historical Irrigation
Dataset (Siebert et al. 2015), development west of 45 E, blind on the Americas.

    .venv/bin/python -I scripts/irrigation_reach_d2b.py prep REGION     # development | check | blind
    .venv/bin/python -I scripts/irrigation_reach_d2b.py dev
    .venv/bin/python -I scripts/irrigation_reach_d2b.py blind
"""
from __future__ import annotations

import itertools
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_D1.json"
OUT = ROOT / "output/irrigation_reach_d2b"
CACHE = ROOT / "data/cache/irrigation_reach_d2b"
REGIONS = {"development": dict(lat=(0.0, 56.0), lon=(-12.0, 45.0)), "check": dict(lat=(0.0, 56.0), lon=(60.0, 125.0)),
           "blind": dict(lat=(-10.0, 50.0), lon=(-125.0, -35.0))}
L_NAV = (6.0, 12.0, 24.0, 48.0)
H0S = (5.0, 10.0, 20.0)
CUTOFF_KM = 60.0
KM_DEG = 111.32
URL = ("https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/"
       "ETOPO_2022_v1_60s_N90W180_surface.nc.dods")
log = lambda *a: print(*a, flush=True)  # noqa: E731


def etopo(region):
    w = REGIONS[region]; path = CACHE / f"etopo60_{region}.npy"
    if path.exists():
        return np.load(path)
    CACHE.mkdir(parents=True, exist_ok=True)
    i0, i1 = int(round((w["lat"][0] + 90) * 60)), int(round((w["lat"][1] + 90) * 60))
    j0, j1 = int(round((w["lon"][0] + 180) * 60)), int(round((w["lon"][1] + 180) * 60))
    rows = []
    for a in range(i0, i1, 120):
        b = min(a + 120, i1)
        for attempt in range(4):
            try:
                raw = urllib.request.urlopen(URL + f"?z[{a}:1:{b - 1}][{j0}:1:{j1 - 1}]", timeout=300).read(); break
            except Exception as e:                                        # noqa: BLE001
                log("retry", a, e); time.sleep(2 ** attempt * 2)
        k = raw.index(b"Data:\n") + 6; n = int(np.frombuffer(raw[k:k + 4], ">u4")[0])
        rows.append(np.frombuffer(raw[k + 8:k + 8 + 4 * n], ">f4").reshape(b - a, j1 - j0))
    z = np.concatenate(rows)[::-1].astype(np.float32)                     # rows from the north
    np.save(path, z); return z


def rivers(region, shape1):
    """Navigable / stream masks at 1' (Natural Earth 10 m, as scripts/land_people_earth.river_masks)."""
    from PIL import Image, ImageDraw
    import land_people_earth as E
    w = REGIONS[region]; H, W = shape1
    nav = Image.new("L", (W, H)); stream = Image.new("L", (W, H))
    dn, ds = ImageDraw.Draw(nav), ImageDraw.Draw(stream)
    gj = json.loads(E.RIVERS.read_text(encoding="utf-8"))
    for f in gj["features"]:
        g, pr = f.get("geometry") or {}, f.get("properties") or {}
        if pr.get("featurecla") not in ("River", "Lake Centerline"):
            continue
        lines = [g["coordinates"]] if g.get("type") == "LineString" else g.get("coordinates", [])
        draw = dn if float(pr.get("scalerank", 99)) <= E.NAVIGABLE_RANK else ds
        for line in lines:
            pts = [((x - w["lon"][0]) * 60, (w["lat"][1] - y) * 60) for x, y, *_ in line]
            if len(pts) > 1:
                draw.line(pts, fill=255, width=1)
    return np.array(nav) > 0, np.array(stream) > 0


def grids5(region):
    """5' land, aridity (P / Hargreaves PET, as the harness), HID 1900 fraction, cell area (km2)."""
    import land_people_earth as E
    from land_people import hargreaves, sunlight_top
    from irrigation_hand_d2 import hid_1900
    w = REGIONS[region]
    r0, r1 = int(round((90 - w["lat"][1]) * 12)), int(round((90 - w["lat"][0]) * 12))
    c0, c1 = int(round((w["lon"][0] + 180) * 12)), int(round((w["lon"][1] + 180) * 12))
    T = np.stack([E.wc("tavg", m)[r0:r1, c0:c1] for m in range(1, 13)])
    P = np.stack([E.wc("prec", m)[r0:r1, c0:c1] for m in range(1, 13)])
    D = np.stack([E.wc("tmax", m)[r0:r1, c0:c1] - E.wc("tmin", m)[r0:r1, c0:c1] for m in range(1, 13)])
    land = np.isfinite(T).all(0) & np.isfinite(P).all(0) & np.isfinite(D).all(0)
    lat = w["lat"][1] - (np.arange(r1 - r0) + 0.5) / 12; LAT = np.broadcast_to(lat[:, None], land.shape)
    PET = hargreaves(np.nan_to_num(T), np.nan_to_num(D), sunlight_top(LAT, 23.44, 355.0))
    ai = np.where(land, np.nan_to_num(P).sum(0) / np.maximum(PET.sum(0), 1.0), np.nan)
    area = (KM_DEG / 12) ** 2 * np.cos(np.radians(LAT))
    a, _ = hid_1900("AEI_HYDE_FINAL_IR_1900.asc")
    hid = np.nan_to_num(a[r0:r1, c0:c1]) / (area * 100.0)
    return land, ai, hid.astype(np.float32), area


def prep(region):
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    z = etopo(region).astype(float); nav, stream = rivers(region, z.shape); river = nav | stream
    w = REGIONS[region]; H, W = z.shape
    land5, ai, hid, area = grids5(region)
    assert land5.shape == (H // 5, W // 5), (land5.shape, z.shape)
    dn = np.zeros(z.shape, np.float32); dst = np.zeros(z.shape, np.float32); hand = np.zeros(z.shape, np.float32)
    dmin = np.zeros(z.shape, np.float32)
    band, pad = 240, 60
    for b0 in range(0, H, band):
        lo, hi = max(b0 - pad, 0), min(b0 + band + pad, H)
        lat = w["lat"][1] - (b0 + band / 2) / 60.0
        samp = (KM_DEG / 60.0, KM_DEG * np.cos(np.radians(lat)) / 60.0)
        s = slice(b0 - lo, b0 - lo + min(band, H - b0)); o = slice(b0, b0 + min(band, H - b0))
        dn[o] = ndi.distance_transform_edt(~nav[lo:hi], sampling=samp)[s]
        dst[o] = ndi.distance_transform_edt(~stream[lo:hi], sampling=samp)[s]
        d_r, (iy, ix) = ndi.distance_transform_edt(~river[lo:hi], sampling=samp, return_indices=True)
        zz = z[lo:hi]; hand[o] = (zz - zz[iy, ix])[s]; dmin[o] = d_r[s]
    blk = lambda a: a.reshape(H // 5, 5, W // 5, 5).mean((1, 3))
    gate_cut = dmin <= CUTOFF_KM; hpos = np.maximum(hand, 0.0)
    fields = dict(land=land5, ai=np.nan_to_num(ai, nan=9.0).astype(np.float32), hid=hid, area=area.astype(np.float32),
                  dmin=blk(dmin).astype(np.float32))
    for L, h0 in itertools.product(L_NAV, H0S):
        irr = np.maximum(np.exp(-dn / L), 0.6 * np.exp(-dst / (L * 2.5 / 6.0))) * np.exp(-hpos / h0) * gate_cut
        fields[f"L{int(L)}_H{int(h0)}"] = blk(irr).astype(np.float32)
    np.savez_compressed(OUT / f"fields_{region}.npz", **fields)
    log(region, "prep done", z.shape, f"({time.time() - t0:.0f}s)")


def auc(score, positive):
    from scipy.stats import rankdata
    r = rankdata(score); n1 = positive.sum(); n0 = (~positive).sum()
    return float((r[positive].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def evaluate(region):
    f = dict(np.load(OUT / f"fields_{region}.npz")); land = f["land"]
    near = land & (f["dmin"] <= 30.0)
    rank_cells = near & (f["ai"] < 0.65); arid = near & (f["ai"] < 0.2)
    pos = f["hid"][rank_cells] >= 0.10
    hid_area = float((f["hid"] * f["area"])[arid].sum())
    res = dict(rank_cells=int(rank_cells.sum()), positive=int(pos.sum()), arid_cells=int(arid.sum()), hid_arid_km2=hid_area)
    for L, h0 in itertools.product(L_NAV, H0S):
        k = f"L{int(L)}_H{int(h0)}"
        model_area = float((f[k] * f["area"])[arid].sum())
        res[k] = dict(auc=auc(f[k][rank_cells], pos), model_arid_km2=model_area,
                      amount_error=abs(float(np.log(max(model_area, 1e-9) / max(hid_area, 1e-9)))))
    return res


def dev():
    res = evaluate("development"); chk = evaluate("check")
    today = "L6_H10"; keys = [f"L{int(L)}_H{int(h)}" for L, h in itertools.product(L_NAV, H0S)]
    ok = [k for k in keys if res[k]["auc"] >= res[today]["auc"] - 0.01]
    chosen = min(ok, key=lambda k: res[k]["amount_error"])
    out = dict(plan=str(PLAN.relative_to(ROOT)), development=res, check_reported=chk, today=today, admissible=ok, chosen=chosen)
    (OUT / "dev.json").write_text(json.dumps(out, indent=1))
    for k in keys:
        log(f"{k:9s} dev AUC {res[k]['auc']:.3f} amount {res[k]['model_arid_km2'] / max(res['hid_arid_km2'], 1):.2f}x  | check AUC {chk[k]['auc']:.3f} amount {chk[k]['model_arid_km2'] / max(chk['hid_arid_km2'], 1):.2f}x")
    log("HID arid km2 dev", round(res["hid_arid_km2"]), "check", round(chk["hid_arid_km2"]), "| chosen", chosen)


def blind():
    d = json.loads((OUT / "dev.json").read_text()); k, today = d["chosen"], d["today"]
    res = evaluate("blind")
    gate = dict(amount_better=res[k]["amount_error"] < res[today]["amount_error"], auc_ok=res[k]["auc"] >= res[today]["auc"] - 0.01)
    out = dict(plan=str(PLAN.relative_to(ROOT)), chosen=k, blind=res, gate=gate, adopt=bool(all(gate.values())))
    (OUT / "blind.json").write_text(json.dumps(out, indent=1))
    log(f"blind (Americas): today {today} AUC {res[today]['auc']:.3f} amount {res[today]['model_arid_km2'] / max(res['hid_arid_km2'], 1):.2f}x; "
        f"chosen {k} AUC {res[k]['auc']:.3f} amount {res[k]['model_arid_km2'] / max(res['hid_arid_km2'], 1):.2f}x; gate {gate} adopt {out['adopt']}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep(sys.argv[2])
    else:
        {"dev": dev, "blind": blind}[cmd]()
