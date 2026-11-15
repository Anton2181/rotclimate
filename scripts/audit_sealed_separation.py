"""Separation audit of a proposed sealed set against every known region definition.

    python3 -I scripts/audit_sealed_separation.py calibration/sealed_X/regions.json
Bounds are the metadata rectangles widened by 56 km (one model cell) on every side, with longitude wrapping.
"""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from rotclimate import earth
M = 56.0


def bounds(r):
    dlat = (r['height_km'] / 2 + M) / 111.2; dlon = (r['width_km'] / 2 + M) / (111.2 * max(math.cos(math.radians(abs(r['lat0']) + dlat)), 0.05))
    return [r['lon0'] - dlon, r['lon0'] + dlon, r['lat0'] - dlat, r['lat0'] + dlat]


def overlap(a, b):
    if a[3] < b[2] or b[3] < a[2]: return False
    for s in (-360, 0, 360):
        if a[0] < b[1] + s and b[0] + s < a[1]: return True
    return False


def main():
    path = Path(sys.argv[1]); prop = json.loads(path.read_text()); known = {}
    for k, r in earth.REGIONS.items(): known[f'earth.{k}'] = r
    for f in sorted((ROOT / 'calibration').rglob('regions*.json')):
        if f.resolve() == path.resolve(): continue
        try: d = json.loads(f.read_text())
        except Exception: continue
        d = d.get('regions', d) if isinstance(d, dict) else {}
        for k, r in (d.items() if isinstance(d, dict) else []):
            if isinstance(r, dict) and 'lat0' in r: known[f'{f.relative_to(ROOT)}:{k}'] = r
    B = {k: bounds(r) for k, r in prop.items()}; KB = {k: bounds(r) for k, r in known.items()}
    col = {k: [n for n, kb in KB.items() if overlap(b, kb)] for k, b in B.items()}
    inner = [(a, b) for a in B for b in B if a < b and overlap(B[a], B[b])]
    out = dict(passes=not any(col.values()) and not inner, known_regions=len(known), proposed_regions=len(B), conservative_margin_km_each_box=M,
               bounds=B, collisions=col, internal_overlaps=inner)
    (path.parent / 'separation_audit.json').write_text(json.dumps(out, indent=1) + '\n'); print(out['passes'], len(known), {k: v for k, v in col.items() if v}, inner)


if __name__ == '__main__':
    main()
