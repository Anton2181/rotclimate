"""Meta M2: draw the sealed bank ONCE, and the fixed global sentinel set from it.

    .venv/bin/python -I scripts/make_sealed_bank.py OUTDIR SEED

Grid search (1 deg) for 120 km boxes >= 70 % land, clear (56 km margin) of every known region definition, at
0-70 deg in both hemispheres; boxes >= 400 km apart, drawn in a seeded random order. Stratified by latitude band
(B1 0-12, B2 12-25, B3 25-40, B4 40-55, B5 55-70): the bank keeps the seeded order inside each band.
The first 3 boxes of each band form the SENTINEL set (15 boxes): run for every candidate as a harm check, never
sealed. The rest is the BANK; scripts/bank_draw.py hands out boxes in bank order, by declared band, once each,
and records every draw in OUTDIR/ledger.json. Writes OUTDIR/bank.json, sentinel.json (regions specs) and
commitment.txt (SHA-256 of bank.json) for the declaration.
"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import audit_sealed_separation as A
from rotclimate import earth
from make_sealed_set import known

# Sealed sets spent ONCE and never tuned on may be overlapped (low/mid-latitude land is otherwise exhausted, 28 Nov
# 2026); the development pool's parts, JJ (whose per-box results redesigned e152) and all non-sealed region files stay
# excluded.
DEV_PARTS = ("sealed_20261031", "sealed_20261031b", "sealed_20261101c", "tropical_check_20261122t", "sealed_20261122r",
             "sealed_20261123S18", "sealed_20261124U18", "sealed_20261128JJ")


def known_core():
    return {k: r for k, r in known().items()
            if not ("calibration/sealed_2026" in k and not any(f"calibration/{d}/" in k for d in DEV_PARTS))}

BANDS = dict(B1=(0, 12), B2=(12, 25), B3=(25, 40), B4=(40, 55), B5=(55, 70))
SIZE, LAND_MIN, SEP_KM, N_SENT = 120.0, 0.7, 400.0, 3


def dist(a, b):
    return 6371 * math.acos(min(1, max(-1, math.sin(math.radians(a["lat0"])) * math.sin(math.radians(b["lat0"]))
                                        + math.cos(math.radians(a["lat0"])) * math.cos(math.radians(b["lat0"]))
                                        * math.cos(math.radians(a["lon0"] - b["lon0"])))))


def main():
    out, seed = ROOT / sys.argv[1], int(sys.argv[2]); half = SIZE / 2
    elev = earth._wc("elev"); land = np.isfinite(elev); KB = [A.bounds(r) for r in known_core().values()]
    cand = []
    for hemi in (1, -1):
        for lat in np.arange(0.5, 70, 1.0):
            for lon in np.arange(-179.5, 180, 1.0):
                r = dict(lat0=float(hemi * lat), lon0=float(lon), width_km=SIZE, height_km=SIZE)
                dlat = half / 111.2; dlon = half / (111.2 * math.cos(math.radians(lat)))
                i0, i1 = int((90 - (r["lat0"] + dlat)) * 12), int((90 - (r["lat0"] - dlat)) * 12)
                j0, j1 = int((lon - dlon + 180) * 12), int((lon + dlon + 180) * 12)
                if j0 < 0 or j1 > 4320 or i0 < 0: continue
                if land[i0:i1, j0:j1].mean() < LAND_MIN: continue
                if any(A.overlap(A.bounds(r), kb) for kb in KB): continue
                cand.append(r)
    rng = np.random.default_rng(seed); pick = []
    for i in rng.permutation(len(cand)):
        c = cand[i]
        if all(dist(c, p) >= SEP_KM for p in pick): pick.append(c)
    band = lambda r: next(b for b, (lo, hi) in BANDS.items() if lo <= abs(r["lat0"]) < hi)
    name = lambda r: f"bk_{abs(int(r['lat0']))}{'n' if r['lat0'] > 0 else 's'}_{abs(int(r['lon0']))}{'e' if r['lon0'] >= 0 else 'w'}"
    bank, sent = {b: [] for b in BANDS}, {}
    for r in pick:                                   # seeded order kept within each band
        b = band(r); spec = dict(r, band=b, note=f"sealed bank seed {seed}")
        if sum(1 for v in sent.values() if v["band"] == b) < N_SENT:
            sent[name(r).replace("bk_", "sn_")] = dict(spec, note=f"SENTINEL (harm check, not sealed) seed {seed}")
        else:
            bank[b].append([name(r), spec])
    out.mkdir(parents=True, exist_ok=True)
    (out / "bank.json").write_text(json.dumps(bank, indent=1) + "\n")
    (out / "sentinel.json").write_text(json.dumps(sent, indent=1) + "\n")
    (out / "ledger.json").write_text(json.dumps(dict(draws=[]), indent=1) + "\n")
    h = hashlib.sha256((out / "bank.json").read_bytes()).hexdigest()
    (out / "commitment.txt").write_text(h + "  bank.json\n")
    print(len(cand), "free boxes;", len(pick), "picked;", {b: len(v) for b, v in bank.items()}, "bank;", len(sent), "sentinel;", h[:16])


if __name__ == "__main__":
    main()
