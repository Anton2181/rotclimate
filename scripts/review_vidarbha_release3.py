"""Independent review of the release-3 Vidarbha check: raw survey join, pyproj projection,
dense dot-product matching, scalar percentiles and captures, spacing of the release-3 tiling."""
import collections, csv, io, json, re, sys, zipfile
from pathlib import Path
import numpy as np
from pyproj import Proj
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity import settle

OUT = ROOT / 'output/vidarbha_release3_20261114'; CACHE = ROOT / 'data/cache/vidarbha_survey_2016'
METHODS = ROOT / 'calibration/vidarbha_survey_20261111/methods.json'


def distance(lat, lon, a, b):
    lat, lon, a, b = map(np.radians, (lat, lon, a, b))
    h = np.sin((lat - a) / 2) ** 2 + np.cos(lat) * np.cos(a) * np.sin((lon - b) / 2) ** 2
    return 6371 * 2 * np.arctan2(np.sqrt(np.clip(h, 0, 1)), np.sqrt(np.clip(1 - h, 0, 1)))


def main():
    r = json.loads((OUT / 'results.json').read_text()); methods = json.loads(METHODS.read_text())
    assert r['plan_sha256'] == sha(ROOT / 'calibration/vidarbha_release3_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/vidarbha_release3.py')
    for n, d in r['survey_files'].items(): assert sha(CACHE / n) == d
    assert sha(OUT / 'model.npz') == r['model_sha256']
    prep = json.loads((ROOT / 'output/vidarbha_survey_20261111/preparation.json').read_text()); norm = lambda s: re.sub('[^a-z0-9]', '', s.lower()); tables = {}
    with zipfile.ZipFile(CACHE / 'Vidarbha_2016Survey_SiteRecords.zip') as z:
        for kind in ('AllSites', 'Settlements'):
            body = z.read(prep['archive_members'][kind]['path']); spec = prep['tables'][kind]
            tables[kind] = [{norm(k): v.strip() for k, v in row.items() if k and k.strip()} for row in csv.DictReader(io.StringIO(body.decode(spec['format']['encoding']), newline='')) if any(row.values())]
    byid = collections.defaultdict(list)
    for row in tables['AllSites']: byid[row['sitecode']].append(row)
    rows = [byid[row['sitecode']][0] for row in tables['Settlements']]; assert len(rows) == 134
    lat = np.array([float(x['north']) for x in rows]); lon = np.array([float(x['east']) for x in rows])
    zones = np.array([x['surveyzone'] for x in rows]); phase = np.array([x['ehs'].lower() for x in rows])
    inside = np.zeros(len(rows), bool)
    for zone, f in methods['frames'].items(): inside |= (zones == zone) & (distance(lat, lon, f['latitude'], f['longitude']) <= 13)
    proj = Proj(proj='aeqd', lat_0=20.8, lon_0=78.5, R=6371000, units='km'); X, Y = proj(lon, lat)
    offsets = {'central': (0, 0)}
    for axis in 'xy':
        for o in (-3., -1., 1., 3.): offsets[f'{axis}{o:+g}km'] = (o if axis == 'x' else 0, o if axis == 'y' else 0)
    model = dict(np.load(OUT / 'model.npz')); checks = 0; spacing_checked = 0
    for grid, g in r['grids'].items():
        cell = int(grid); inp = dict(np.load(OUT / f'inputs_{cell}km.npz')); ny, nx = inp['land'].shape
        la, lo = np.radians(inp['lat'].ravel()), np.radians(inp['lon'].ravel()); vectors = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]).T
        recovered = {}
        for name, (dx, dy) in offsets.items():
            olon, olat = proj(X + dx, Y + dy, inverse=True); a, b = np.radians(olat), np.radians(olon)
            pts = np.array([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)]).T
            ids = np.concatenate([np.argmax(pts[i:i + 8] @ vectors.T, axis=1) for i in range(0, len(rows), 8)])
            window = (np.abs(X + dx) <= nx * cell / 2) & (np.abs(Y + dy) <= ny * cell / 2); recovered[name] = (ids, window & inp['land'].ravel()[ids])
        towns = model[f'{cell}km__towns__release3_L800']; ids = towns[:, 0] * nx + towns[:, 1]
        c = g['constraints']['release3_L800']; assert c['placed'] == len(ids) == c['requested'] == g['natural_production_count'] and len(set(ids)) == len(ids)
        # release-3 tiling exclusion rebuilt from the shared library constants (not the producer): towns are stored in
        # placement order, and no later town may sit inside an earlier town's prior-scaled catchment circle
        _, d = settle.site_score(inp['density'], inp['land'], inp['water_km'], ndi.distance_transform_edt(inp['land']) * cell, inp['road'], inp['elev'], cell)
        d_eff = d * inp['history800']
        catch = g['release3_seat_people'] / settle.SEAT_REF_DENSITY * (settle.SEAT_REF_DENSITY / np.maximum(d_eff.ravel()[ids], 1e-9)) ** settle.SEAT_BETA
        radius = np.minimum(np.sqrt(catch / np.pi), settle.MAX_RADIUS_KM) / cell * settle.SPACING
        gaps = np.sqrt(((towns[:, None, :] - towns[None, :, :]) ** 2).sum(2))
        for k in range(len(ids)):
            assert np.all(gaps[k, k + 1:] ** 2 > radius[k] ** 2), 'spacing'
        spacing_checked += len(ids)
        for m in g['metrics']:
            member = inside.copy()
            if m['cohort'] == 'EH-S_yes': member &= phase == 'yes'
            elif m['cohort'] == 'possible_phase': member &= np.isin(phase, ['yes', '?', ''])
            rid, valid = recovered[m['offset']]; cells = np.unique(rid[member & valid & (zones == m['zone'])]); assert m['distinct_cells'] == len(cells)
            f = methods['frames'][m['zone']]; background = inp['land'] & (distance(inp['lat'], inp['lon'], f['latitude'], f['longitude']) <= 13)
            for name, value in m['opportunity'].items():
                field = model[f'{cell}km__field__{name}']; v = field.ravel()[cells]; b = field[background]
                ref = float(np.mean([(np.sum(b < s) + .5 * np.sum(b == s)) / len(b) for s in v])) if len(v) else None
                assert (value is None and ref is None) or abs(value - ref) < 1e-12; checks += 1
            pts = np.column_stack(np.divmod(cells, nx))
            for name, caps in m['captures'].items():
                t = model[f'{cell}km__towns__{name}']; near = np.sqrt(((pts[:, None, :] - t[None, :, :]) ** 2).sum(2)).min(1) * cell if len(cells) else np.array([])
                for rad, value in caps.items():
                    ref = float(np.mean(near <= int(rad))) if len(cells) else None
                    assert (value is None and ref is None) or abs(value - ref) < 1e-12; checks += 1
    prim = [m for m in r['grids']['3']['metrics'] if m['cohort'] == 'EH-S_yes' and m['offset'] == 'central']
    rd = np.mean([m['opportunity']['release3_L800'] for m in prim]) - np.mean([m['opportunity']['environment'] for m in prim])
    cd = np.mean([m['captures']['release3_L800']['10'] for m in prim]) - np.mean([m['captures']['production_seed1']['10'] for m in prim])
    gd = r['guard']; assert abs(gd['rank_delta_release3_vs_production'] - rd) < 1e-12 and abs(gd['capture_delta_release3_vs_production'] - cd) < 1e-12
    assert gd['guard_pass'] == bool(gd['support_qualified'] and rd >= -.05 and cd >= -.10 and gd['constraints_pass'])
    fresh = OUT / 'fresh'; exact = {}
    for n in ('results.json', 'model.npz'):
        assert (fresh / n).read_bytes() == (OUT / n).read_bytes(), n; exact[n] = sha(OUT / n)
    write(OUT / 'review.json', dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), scalar_metric_checks=checks,
        independent_source_joins=134, fresh_byte_exact=exact, guard_reconstructed=True, towns_spacing_checked=spacing_checked))
    print('passed', checks, 'scalar checks')


if __name__ == '__main__':
    main()
