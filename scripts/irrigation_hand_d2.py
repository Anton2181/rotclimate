"""Plan D2 (calibration/geography_control_20261107/plan_D1.json, "D2"): river irrigation gated by height above the
river, tested against the 1900 Historical Irrigation Dataset (Siebert et al. 2015; CC0; doi:10.13019/M20599).

    .venv/bin/python -I scripts/irrigation_hand_d2.py prep     # 1' fields -> 5' baseline and gated scores, HID 1900
    .venv/bin/python -I scripts/irrigation_hand_d2.py dev      # choose H0 on the development half (12 W - 45 E)
    .venv/bin/python -I scripts/irrigation_hand_d2.py blind    # the single blind evaluation (60 E - 125 E)
"""
from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_D1.json"
OUT = ROOT / "output/irrigation_hand_d2"
HID = ROOT / "data/cache/hid_20261108/hid_archive.zip"
H0S = (10.0, 20.0, 40.0, 80.0, 160.0)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def hid_1900(name="AEI_HYDE_FINAL_IR_1900.asc"):
    z = zipfile.ZipFile(HID); inner = zipfile.ZipFile(io.BytesIO(z.read("10_13019_M20599/HID_v10.zip")))
    s7 = zipfile.ZipFile(io.BytesIO(inner.read("Supplement_S7_AEI_in_gridded_products_of_the_HID_ascii.zip")))
    txt = s7.read(name).decode().splitlines()
    head = {}
    k = 0
    while txt[k].split()[0].lower() in ("ncols", "nrows", "xllcorner", "yllcorner", "cellsize", "nodata_value"):
        key, val = txt[k].split()[:2]; head[key.lower()] = float(val); k += 1
    a = np.loadtxt(txt[k:], dtype=np.float32)
    a[a == head.get("nodata_value", -9999)] = np.nan
    return a, head                                        # hectares per cell, rows from the north


def prep():
    import land_people_earth as E
    from arable_slope_earth import etopo_window
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    earth = np.load(ROOT / "output/land_people/earth/earth.npz")
    land5 = earth["land"]; shape5 = land5.shape
    nav, stream = E.river_masks(shape5)                   # 1' rasters of the harness window, rows from the north
    z = etopo_window().astype(float)
    assert z.shape == nav.shape, (z.shape, nav.shape)
    H, W = z.shape
    lat1 = E.WINDOW["lat"][1] - (np.arange(H) + 0.5) / 60.0
    river = nav | stream
    irr1 = np.zeros(z.shape, np.float32); hand1 = np.full(z.shape, np.nan, np.float32); dmin1 = np.zeros(z.shape, np.float32)
    band, pad = 4 * 60, 60
    for b0 in range(0, H, band):
        lo, hi = max(b0 - pad, 0), min(b0 + band + pad, H)
        lat = E.WINDOW["lat"][1] - (b0 + band / 2) / 60.0
        samp = (E.KM_DEG / 60.0, E.KM_DEG * np.cos(np.radians(lat)) / 60.0)
        d_nav = ndi.distance_transform_edt(~nav[lo:hi], sampling=samp)
        d_st = ndi.distance_transform_edt(~stream[lo:hi], sampling=samp)
        d_r, (iy, ix) = ndi.distance_transform_edt(~river[lo:hi], sampling=samp, return_indices=True)
        zz = z[lo:hi]
        part_irr = np.maximum(np.exp(-d_nav / 6.0), 0.6 * np.exp(-d_st / 2.5))
        part_hand = zz - zz[iy, ix]                          # height above the nearest mapped river cell
        s = slice(b0 - lo, b0 - lo + min(band, H - b0))
        irr1[b0:b0 + min(band, H - b0)] = part_irr[s]; hand1[b0:b0 + min(band, H - b0)] = part_hand[s]
        dmin1[b0:b0 + min(band, H - b0)] = d_r[s]
    blk = lambda a: a.reshape(shape5[0], 5, shape5[1], 5).mean((1, 3))
    fields = dict(baseline=blk(irr1), dmin=blk(dmin1).astype(np.float32), hand_mean=blk(np.where(np.isfinite(hand1), hand1, 0.0)))
    for h0 in H0S:
        fields[f"hand_{int(h0)}"] = blk(irr1 * np.exp(-np.maximum(np.nan_to_num(hand1), 0.0) / h0))
    # HID 1900 on the harness window (5 arc-min, rows from the north)
    for name in ("AEI_HYDE_FINAL_IR_1900.asc", "AEI_HYDE_FINAL_CP_1900.asc"):
        a, head = hid_1900(name)
        r0 = int(round((90 - E.WINDOW["lat"][1]) * 12)); c0 = int(round((E.WINDOW["lon"][0] + 180) * 12))
        sub = a[r0:r0 + shape5[0], c0:c0 + shape5[1]]
        lat5 = earth["lat"]; cell_ha = (E.KM_DEG / 12) ** 2 * np.cos(np.radians(lat5))[:, None] * 100.0
        fields["hid_" + name.split("_")[3].lower()] = np.nan_to_num(sub / cell_ha).astype(np.float32)
    ai = np.nan_to_num(earth["P_ann"]) / np.maximum(np.nan_to_num(earth["PET_ann"]), 1.0)
    fields["ai"] = ai.astype(np.float32); fields["land"] = land5
    np.savez_compressed(OUT / "fields.npz", **fields, lat=earth["lat"], lon=earth["lon"])
    log("prep done", {k: v.shape for k, v in fields.items()}, f"({time.time() - t0:.0f}s)")


def auc(score, positive):
    from scipy.stats import rankdata
    r = rankdata(score); n1 = positive.sum(); n0 = (~positive).sum()
    return float((r[positive].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def evaluate(half, which="hid_ir"):
    f = dict(np.load(OUT / "fields.npz"))
    lon = f["lon"][None, :] * np.ones_like(f["ai"])
    span = {"development": (-12.0, 45.0), "blind": (60.0, 125.0)}[half]
    cells = f["land"] & (f["ai"] < 0.65) & (f["dmin"] <= 30.0) & (lon >= span[0]) & (lon < span[1])
    pos = f[which][cells] >= 0.10
    res = dict(cells=int(cells.sum()), positive=int(pos.sum()), baseline=auc(f["baseline"][cells], pos))
    for h0 in H0S:
        res[f"hand_{int(h0)}"] = auc(f[f"hand_{int(h0)}"][cells], pos)
    return res


def dev():
    res = evaluate("development"); res_cp = evaluate("development", "hid_cp")
    best = max(H0S, key=lambda h: res[f"hand_{int(h)}"])
    out = dict(plan=str(PLAN.relative_to(ROOT)), development=res, development_cp_sensitivity=res_cp, chosen_H0=best)
    (OUT / "dev.json").write_text(json.dumps(out, indent=1)); log(json.dumps(out, indent=1))


def blind():
    d = json.loads((OUT / "dev.json").read_text()); h0 = d["chosen_H0"]
    res = evaluate("blind"); res_cp = evaluate("blind", "hid_cp")
    gain = res[f"hand_{int(h0)}"] - res["baseline"]
    out = dict(plan=str(PLAN.relative_to(ROOT)), chosen_H0=h0, blind=res, blind_cp_sensitivity=res_cp, gain=gain, adopt=bool(gain >= 0.01))
    (OUT / "blind.json").write_text(json.dumps(out, indent=1)); log(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"prep": prep, "dev": dev, "blind": blind}[sys.argv[1]]()
