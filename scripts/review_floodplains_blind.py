"""Independent review of output/floodplains_blind_20261115: raw-zip cohort rebuilt with csv + swapped columns + class codes,
position metrics recomputed from model.npz and the stored inputs with separate percentile/capture code, observed bands, fresh replay."""
import csv, io, json, sys, zipfile
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
OUT = ROOT / 'output/floodplains_blind_20261115'; r = json.loads((OUT / 'results.json').read_text())
assert r['plan_sha256'] == sha(ROOT / 'calibration/floodplains_blind_20261115/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/floodplains_blind.py')
rows = list(csv.DictReader(io.StringIO(zipfile.ZipFile(ROOT / 'data/cache/floodplains_archiraq/archiraq-master.zip').read('archiraq-master/docs/papers/1/data_stacked.csv').decode('utf-8', 'replace'))))
f = lambda v: float(v) if v not in ('', 'NA') else float('nan')
best = {}
for x in rows:
    s, e, c = f(x['StartDate']), f(x['EndDate']), f(x['SizeHa'])
    if s <= 200 <= e and c > 0 and x['Longitude'] not in ('', 'NA'):
        if x['Id'] not in best or c > best[x['Id']][0]: best[x['Id']] = (c, f(x['Longitude']), f(x['Latitude']))    # (code, lat, lon)
assert len(best) == r['ad200_sites'] and sum(v[0] >= 3 for v in best.values()) == r['ad200_towns_class3plus']
m = np.load(OUT / 'model.npz'); checks = 0
def pct(v, b):
    b = np.asarray(b, float); return float(np.mean([(np.sum(b < s) + .5 * np.sum(b == s)) / len(b) for s in v]))
for cell in (3, 9):
    x = np.load(OUT / f'inputs_{cell}km.npz'); g = r['grids'][str(cell)]; ny, nx = x['land'].shape
    lat, lon = x['lat'].ravel(), x['lon'].ravel(); surveyed = m[f'{cell}km__surveyed']; field = m[f'{cell}km__release3_field']
    a = np.radians(lat); b = np.radians(lon); grid = np.column_stack([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)])
    for name, keep in (('ad200', lambda c: True), ('towns', lambda c: c >= 3)):
        pts = [(la, lo) for c, la, lo in best.values() if keep(c) and abs(la - 31.8) < 250 / 111.32 and abs(lo - 45.6) < 300 / (111.32 * np.cos(np.radians(31.8)))]
        pa, pb = np.radians([p[0] for p in pts]), np.radians([p[1] for p in pts]); P = np.column_stack([np.cos(pa) * np.cos(pb), np.cos(pa) * np.sin(pb), np.sin(pa)])
        ids = np.concatenate([np.argmax(P[i:i + 64] @ grid.T, axis=1) for i in range(0, len(P), 64)]); ids = ids[surveyed.ravel()[ids]]
        cells = np.unique(ids); assert len(cells) == g['cohorts'][name]['distinct_cells'], (cell, name)
        assert abs(pct(field.ravel()[cells], field[surveyed]) - g['cohorts'][name]['percentile']['release3']) < 1e-12; checks += 1
        for key in ('production', 'release3'):
            t = m[f'{cell}km__{key}']; pt = np.column_stack(np.divmod(cells, nx))
            cap = float(np.mean(np.sqrt(((pt[:, None, :] - t[None]) ** 2).sum(2)).min(1) * cell <= 10)); assert abs(cap - g['cohorts'][name]['capture_10km'][key]) < 1e-12; checks += 1
t = r['grids']['3']['cohorts']['towns']; assert r['test_P_pass'] == (t['percentile']['release3'] >= .55 and t['capture_10km']['release3'] >= t['capture_10km']['production'] - .05)
s = r['grids']['9']['sizes']; lo, hi = s['observed_largest_n']['total_bounds_ha']; v = s['models']['published_refit']
assert r['test_S_pass'] == v['passed'] == (v['mean_same_band_share'] >= .5 and .67 * lo <= v['mean_model_total'] <= 1.5 * hi)
fresh = OUT / 'fresh/results.json'; exact = fresh.exists() and fresh.read_bytes() == (OUT / 'results.json').read_bytes()
write(OUT / 'review.json', dict(status='passed' if exact else 'passed_without_fresh_replay', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), scalar_checks=checks, fresh_byte_exact=bool(exact)))
print('review', exact, checks)
