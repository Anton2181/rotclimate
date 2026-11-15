"""FloodPlains blind test (calibration/floodplains_blind_20261115/plan.json): release-3 positions and the published
size model on southern Mesopotamian survey sites occupied at AD 200. Raw rows stay in the ignored cache."""
import argparse, csv, io, json, subprocess, sys, zipfile
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import earth as E, settle, settlement_sizes as Z
from polity.settlement_locations import site_fields, prior_tiling_sites, match_count
from polity.survey_transfer import relative_ranks, capture_fraction
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/floodplains_blind_20261115/plan.json'; OUT = ROOT / 'output/floodplains_blind_20261115'
ZIP = ROOT / 'data/cache/floodplains_archiraq/archiraq-master.zip'; MEMBER = 'archiraq-master/docs/papers/1/data_stacked.csv'
LAT0, LON0, WKM, HKM = 31.8, 45.6, 600., 500.; SEEDS = [1, 7, 19, 43, 97]
SIZES = ROOT / 'output/sizes_greek_walls_20261114/results.json'; OLD_SIZES = ROOT / 'output/settlement_release2_20261113/results.json'


def xyz(lat, lon):
    a, b = np.radians(lat), np.radians(lon); return np.column_stack([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)])


def rows():
    text = zipfile.ZipFile(ZIP).read(MEMBER).decode('utf-8', 'replace'); r = list(csv.DictReader(io.StringIO(text)))
    num = lambda v: float(v) if v not in ('', 'NA', None) else np.nan
    start = np.array([num(x['StartDate']) for x in r]); end = np.array([num(x['EndDate']) for x in r])
    lo, hi = np.nanmin(np.r_[start, end]), np.nanmax(np.r_[start, end])
    if not (-10000 <= lo and hi <= 2100):
        raise ValueError(f'Date convention not calendar years ({lo}, {hi}): amend the plan before scoring')
    lat = np.array([num(x['Longitude']) for x in r]); lon = np.array([num(x['Latitude']) for x in r]); size = np.array([num(x['SizeHa']) for x in r])
    ids = np.array([x['Id'] for x in r])   # amendment A1: latitude/longitude columns are swapped in the source
    return dict(ids=ids, start=start, end=end, lat=lat, lon=lon, size=size, date_range=[float(lo), float(hi)])


def inputs(cell, global_fields, distance, elevation):
    from settlement_model_earth import sample_earth
    finite = np.isfinite(elevation); filled = np.nan_to_num(elevation)
    g = E.grid(LAT0, LON0, WKM, HKM, cell); lat, lon = g['lat'], g['lon']
    land = E.sample_global(finite.astype(np.uint8), lat, lon).astype(bool); elev = E.sample_global(filled, lat, lon, order=1)
    density, herders, covered = E.earth_people(lat, lon)
    river = E.rivers(g) & land; water = ndi.distance_transform_edt(~river) * cell
    aridity = sample_earth(global_fields['aridity'], lat, lon); d = sample_earth(distance, lat, lon)
    return dict(g, land=land, elev=np.where(land, elev, 0.), density=density * land, covered=covered, river=river, water_km=water,
                road=np.zeros(land.shape, bool), aridity=aridity, allowed=land.copy(), history800=np.exp(-d / 800.))


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True)
    from rotclimate.earth import _wc
    from population_cores import travel_distance, CORE_SETS
    with np.load(ROOT / 'output/land_people/earth/earth.npz') as a: gf = dict(a)
    distance = travel_distance(gf, CORE_SETS['cradles + Rome'], forest_cost=2., sea_cost=1., relief_cost=1.); elevation = _wc('elev')
    R = rows(); covers = (R['start'] <= 200) & (R['end'] >= 200) & (R['size'] > 0) & np.isfinite(R['lat'])
    best = {}
    for i in np.flatnonzero(covers):
        if R['ids'][i] not in best or R['size'][i] > R['size'][best[R['ids'][i]]]: best[R['ids'][i]] = i
    ad = np.array(sorted(best.values())); allsites = np.flatnonzero(np.isfinite(R['lat']) & np.isfinite(R['lon']))
    result = dict(status='floodplains_blind_test', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), source_zip_sha256=sha(ZIP),
                  date_range=R['date_range'], rows=int(len(R['ids'])), ad200_sites=int(len(ad)), ad200_towns_ge_10ha=int((R['size'][ad] >= 10).sum()), grids={})
    size_fit = json.loads(SIZES.read_text())['sizes']['primary']; old_fit = json.loads(OLD_SIZES.read_text())['sizes']['primary']
    arrays = {}
    for cell in (3, 9):
        x = inputs(cell, gf, distance, elevation); np.savez_compressed(out / f'inputs_{cell}km.npz', **x)
        land = x['land']; ny, nx = land.shape; tree = cKDTree(xyz(x['lat'].ravel(), x['lon'].ravel()))
        cell_of = lambda idx: tree.query(xyz(R['lat'][idx], R['lon'][idx]))[1]
        inwin = lambda idx: (np.abs(R['lat'][idx] - LAT0) < HKM / 2 / 111.32) & (np.abs(R['lon'][idx] - LON0) < WKM / 2 / (111.32 * np.cos(np.radians(LAT0))))
        surveyed = np.zeros(land.size, bool); surveyed[cell_of(allsites[inwin(allsites)])] = True
        surveyed = (ndi.distance_transform_edt(~surveyed.reshape(land.shape)) * cell <= 3.0) & land
        sel = ad[inwin(ad)]; site_cells = cell_of(sel); on = surveyed.ravel()[site_cells]; sel, site_cells = sel[on], site_cells[on]
        args = {k: x[k] for k in ['density', 'land', 'water_km', 'road', 'elev', 'aridity', 'allowed']}; args['cell_km'] = float(cell)
        score, eligible = site_fields(**args)
        production, _, _ = settle.place_towns(**args, marked=[], seed=1); count = len(production)
        tile = dict(allowed=x['allowed'], aridity=x['aridity'])
        seat, release3 = match_count(lambda sp: prior_tiling_sites(x['density'], land, x['water_km'], x['road'], x['elev'], float(cell), prior=x['history800'], seat_people=sp, **tile), count)
        prod = np.asarray(production, int).reshape(-1, 2); rel = np.asarray(release3, int).reshape(-1, 2)
        fields = {'environment': np.where(eligible, score, 0.), 'release3': np.where(eligible, score * x['history800'], 0.)}
        bg = surveyed
        g = dict(shape=[ny, nx], land_cells=int(land.sum()), surveyed_cells=int(surveyed.sum()), production_count=count, release3_seat_people=seat,
                 release3_count=len(rel), cohorts={})
        for name, m in (('ad200', np.ones(len(sel), bool)), ('towns', R['size'][sel] >= 10)):
            cells = np.unique(site_cells[m]); c = dict(sites=int(m.sum()), distinct_cells=int(len(cells)))
            if len(cells):
                c['percentile'] = {k: float(np.mean(relative_ranks(f.ravel()[cells], f[bg]))) for k, f in fields.items()}
                c['capture_10km'] = {'production': capture_fraction(cells, prod, nx, float(cell), 10), 'release3': capture_fraction(cells, rel, nx, float(cell), 10)}
            g['cohorts'][name] = c
        if cell == 9:
            people = np.where(land, x['density'], 0.) * cell ** 2
            (_, _, _), H = Z.hinterlands(rel, land, people, float(cell))
            keep = surveyed[rel[:, 0], rel[:, 1]] & (H > 0); n = int(keep.sum())
            observed = np.sort(R['size'][sel])[::-1][:n]
            sizes = {}
            for label, fit in (('published_refit', size_fit), ('release2_previous', old_fit)):
                coef = fit['models']['M1']['full_coefficients']; sigma = fit['models']['M1']['heldout_sigma']; lo_ha, hi_ha = fit['area_range_ha']
                mean = coef[0] + coef[1] * np.log(H[keep]); runs = []
                for s in SEEDS:
                    gen = Z.generate_area(mean, sigma, Z.draws(n, s), lo_ha, hi_ha)
                    runs.append(dict(seed=s, ks=float(ks_2samp(gen, observed).statistic), total_ratio=float(gen.sum() / observed.sum()), median_model=float(np.median(gen))))
                sizes[label] = dict(runs=runs, mean_ks=float(np.mean([r['ks'] for r in runs])), mean_total_ratio=float(np.mean([r['total_ratio'] for r in runs])),
                                    passed=bool(np.mean([r['ks'] for r in runs]) <= 0.20 and 0.67 <= np.mean([r['total_ratio'] for r in runs]) <= 1.50))
            g['sizes'] = dict(model_towns_in_surveyed_area=n, observed_largest_n=dict(median=float(np.median(observed)), total=float(observed.sum()),
                              quantiles={str(q): float(np.quantile(observed, q)) for q in (.1, .25, .5, .75, .9)}), models=sizes)
        result['grids'][str(cell)] = g
        arrays.update({f'{cell}km__production': prod, f'{cell}km__release3': rel, f'{cell}km__surveyed': surveyed, f'{cell}km__release3_field': fields['release3']})
        print(cell, json.dumps({k: v for k, v in g.items() if k != 'sizes'}), flush=True)
    t = result['grids']['3']['cohorts']['towns']
    p_pass = bool(t.get('percentile') and t['percentile']['release3'] >= 0.55 and t['capture_10km']['release3'] >= t['capture_10km']['production'] - 0.05)
    s_pass = result['grids']['9']['sizes']['models']['published_refit']['passed']
    result.update(test_P_pass=p_pass, test_S_pass=s_pass, raw_rows_redistributed=False)
    np.savez_compressed(out / 'model.npz', **arrays); result['model_sha256'] = sha(out / 'model.npz')
    write(out / 'results.json', result); print('P', p_pass, 'S', s_pass, json.dumps(result['grids']['9']['sizes'], indent=0)[:1500])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); main(ap.parse_args().out)
