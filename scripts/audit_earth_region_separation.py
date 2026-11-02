"""Audit held-out box separation from metadata only; never read observations."""
from pathlib import Path
import argparse
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json


def bounds(region, margin_km=56.):
    lat, lon = region['lat0'], region['lon0']
    if not all(math.isfinite(x) for x in [lat, lon, margin_km, region['width_km'], region['height_km']]):
        raise ValueError('Nonfinite geographic definition')
    if not -89 < lat < 89 or margin_km < 0 or min(region['width_km'], region['height_km']) <= 0:
        raise ValueError('Invalid geographic box')
    dy = (region['height_km'] / 2 + margin_km) / 111.195
    dx = (region['width_km'] / 2 + margin_km) / (111.195 * math.cos(math.radians(lat)))
    return [lon - dx, lon + dx, lat - dy, lat + dy]


def overlap(a, b):
    if min(a[3], b[3]) <= max(a[2], b[2]): return False
    return any(min(a[1], b[1] + shift) > max(a[0], b[0] + shift) for shift in [-360., 0., 360.])


def audit(proposed, known, margin_km=56.):
    rectangles = {name: bounds(spec, margin_km) for name, spec in known.items()}
    own = {name: bounds(spec, margin_km) for name, spec in proposed.items()}
    collisions = {name: [n for n, b in rectangles.items() if overlap(a, b)] for name, a in own.items()}
    for name, a in own.items():
        collisions[name] += [n for n, b in own.items() if n != name and overlap(a, b)]
        if name in known: collisions[name].append('duplicate region name')
    return dict(passes=not any(collisions.values()), known_regions=len(known), proposed_regions=len(proposed),
                conservative_margin_km_each_box=margin_km, bounds=own, collisions=collisions,
                scope='Metadata rectangles with an extra model-cell margin, including longitude wrapping. Not observations, model scores or independent forcing halos.')


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--regions', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    from rotclimate import earth
    from benchmark_local import DEV12_SPECS
    files = [DEV12_SPECS] + [p for p in (ROOT / 'calibration').glob('sealed_*/regions.json')
                             if p.resolve() != a.regions.resolve()]
    known = dict(earth.REGIONS)
    for p in files: known.update(json.loads(p.read_text()))
    result = audit(json.loads(a.regions.read_text()), known)
    result.update(proposed_sha256=file_hash(a.regions), auditor_sha256=file_hash(Path(__file__)),
                  known_definitions=known, sources_sha256={str(p.relative_to(ROOT)): file_hash(p) for p in files})
    write_json(a.out, result)
    if not result['passes']: raise SystemExit('Scored-box overlap: ' + str(result['collisions']))
    print('Separated', result['proposed_regions'], 'new boxes from', result['known_regions'], 'known definitions; observations unopened')


if __name__ == '__main__': main()
