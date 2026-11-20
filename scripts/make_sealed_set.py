"""Draw a sealed region set: 1-degree grid search in a latitude band for 300 km boxes that are >= 80 % land (WorldClim 5')
and clear (56 km margin) of every known region definition; then 6 boxes drawn with a fixed seed, at least 1,000 km apart.

    python3 -I scripts/make_sealed_set.py OUTDIR PREFIX SEED [LAT_LO LAT_HI]
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import audit_sealed_separation as A
from rotclimate import earth


def known():
    k = {f'earth.{n}': r for n, r in earth.REGIONS.items()}
    for f in sorted((ROOT / 'calibration').rglob('regions*.json')):
        try: d = json.loads(f.read_text())
        except Exception: continue
        d = d.get('regions', d) if isinstance(d, dict) else {}
        for n, r in (d.items() if isinstance(d, dict) else []):
            if isinstance(r, dict) and 'lat0' in r: k[f'{f}:{n}'] = r
    return k


def main():
    out, prefix, seed = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]); lo, hi = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (25.0, 55.0)
    elev = earth._wc('elev'); land = np.isfinite(elev); KB = [A.bounds(r) for r in known().values()]
    cand = []
    for hemi in (1, -1):
        for lat in np.arange(lo + 0.5, hi, 1.0):
            for lon in np.arange(-179.5, 180, 1.0):
                r = dict(lat0=float(hemi * lat), lon0=float(lon), width_km=300, height_km=300)
                dlat = 150 / 111.2; dlon = 150 / (111.2 * math.cos(math.radians(lat)))
                i0, i1 = int((90 - (r['lat0'] + dlat)) * 12), int((90 - (r['lat0'] - dlat)) * 12)
                j0, j1 = int((lon - dlon + 180) * 12), int((lon + dlon + 180) * 12)
                if j0 < 0 or j1 > 4320: continue
                if land[i0:i1, j0:j1].mean() < 0.8: continue
                b = A.bounds(r)
                if any(A.overlap(b, kb) for kb in KB): continue
                cand.append(r)
    rng = np.random.default_rng(seed); order = rng.permutation(len(cand)); pick = []
    dist = lambda a, b: 6371 * math.acos(min(1, max(-1, math.sin(math.radians(a['lat0'])) * math.sin(math.radians(b['lat0'])) + math.cos(math.radians(a['lat0'])) * math.cos(math.radians(b['lat0'])) * math.cos(math.radians(a['lon0'] - b['lon0'])))))
    for i in order:
        c = cand[i]
        if all(dist(c, p) >= 1000 for p in pick): pick.append(c)
        if len(pick) == 6: break
    regs = {f"{prefix}_{abs(int(p['lat0']))}{'n' if p['lat0'] > 0 else 's'}_{abs(int(p['lon0']))}{'e' if p['lon0'] >= 0 else 'w'}": dict(p, note=f'SEALED set {prefix}: grid search seed {seed}') for p in pick}
    out.mkdir(parents=True, exist_ok=True); (out / 'regions.json').write_text(json.dumps(regs, indent=1) + '\n')
    print(len(cand), 'free boxes;', list(regs))


if __name__ == '__main__':
    main()
