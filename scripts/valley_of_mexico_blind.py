"""Valley of Mexico blind test (calibration/valley_of_mexico_blind_20261116/plan.json, amendment A1): release-3 positions,
the published size model and the people field on the Parsons/Blanton survey's Classic sites. Raw rows stay in the ignored cache."""
import argparse, json, subprocess, sys
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

PLAN = ROOT / 'calibration/valley_of_mexico_blind_20261116/plan.json'; OUT = ROOT / 'output/valley_of_mexico_blind_20261116'
XLSX = ROOT / 'data/cache/valley_of_mexico/site-survey-data.xlsx'; NW = ROOT / 'output/maize_20261116/mexico_newworld/earth.npz'
LAT0, LON0, WKM, HKM = 19.6, -98.95, 160., 180.; SEEDS = [1, 7, 19, 43, 97]
CORES = {'San Lorenzo': (17.75, -94.76), 'San Jose Mogote': (17.20, -96.75), 'El Mirador': (17.75, -89.92)}
SIZES = ROOT / 'output/sizes_greek_walls_20261114/results.json'


def xyz(lat, lon):
    a, b = np.radians(lat), np.radians(lon); return np.column_stack([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)])


def num(v):
    try: return float(str(v).replace(',', ''))
    except (TypeError, ValueError): return np.nan


def rows():
    import openpyxl
    from pyproj import Transformer
    ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]; it = ws.iter_rows(values_only=True); h = next(it); ix = {k: i for i, k in enumerate(h)}
    R = [r for r in it]
    north = np.array([num(r[ix['North']]) for r in R]) * 1000.0; east = np.array([num(r[ix['East']]) for r in R]) * 1000.0   # A1: kilometres
    lon, lat = Transformer.from_crs('EPSG:32614', 'EPSG:4326', always_xy=True).transform(east, north)
    return dict(site=np.array([str(r[ix['SiteCode']]) for r in R]), period=np.array([str(r[ix['Period']]) for r in R]),
                lat=np.asarray(lat), lon=np.asarray(lon), area=np.array([num(r[ix['Area']]) for r in R]),
                pop=np.array([num(r[ix['Population']]) for r in R]), popmin=np.array([num(r[ix['PopMin']]) for r in R]),
                popmax=np.array([num(r[ix['PopMax']]) for r in R]))


def inputs(cell, gf, distance, elevation):
    from settlement_model_earth import sample_earth
    finite = np.isfinite(elevation); filled = np.nan_to_num(elevation)
    g = E.grid(LAT0, LON0, WKM, HKM, cell); lat, lon = g['lat'], g['lon']
    land = E.sample_global(finite.astype(np.uint8), lat, lon).astype(bool); elev = E.sample_global(filled, lat, lon, order=1)
    density, herders, covered = E.earth_people(lat, lon)
    river = E.rivers(g) & land; water = ndi.distance_transform_edt(~river) * cell
    aridity = sample_earth(gf['aridity'], lat, lon); d = sample_earth(distance, lat, lon)
    return dict(g, land=land, elev=np.where(land, elev, 0.), density=density * land, covered=covered, river=river, water_km=water,
                road=np.zeros(land.shape, bool), aridity=aridity, allowed=land.copy(), history800=np.exp(-d / 800.))


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True)
    E.EARTH_NPZ = NW
    from rotclimate.earth import _wc
    from population_cores import travel_distance
    with np.load(NW) as a: gf = dict(a)
    distance = travel_distance(gf, CORES, forest_cost=2., sea_cost=1., relief_cost=1.); elevation = _wc('elev')
    R = rows(); ok = np.isfinite(R['lat']) & np.isfinite(R['lon'])
    classic = ok & np.isin(R['period'], ['Classic', 'Early Classic'])          # A1
    best = {}
    for i in np.flatnonzero(classic):
        a = R['area'][i]; k = R['site'][i]
        if k not in best or (np.nan_to_num(a) > np.nan_to_num(R['area'][best[k]])): best[k] = i
    cl = np.array(sorted(best.values())); allsites = np.flatnonzero(ok)
    result = dict(status='valley_of_mexico_blind_test', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), source_sha256=sha(XLSX),
                  newworld_run_sha256=sha(NW), rows=int(len(R['site'])), classic_sites=int(len(cl)), classic_towns_10ha=int((np.nan_to_num(R['area'][cl]) >= 10).sum()), grids={})
    size_fit = json.loads(SIZES.read_text())['sizes']['primary']; arrays = {}
    for cell in (3, 9):
        x = inputs(cell, gf, distance, elevation); np.savez_compressed(out / f'inputs_{cell}km.npz', **x)
        land = x['land']; ny, nx = land.shape; tree = cKDTree(xyz(x['lat'].ravel(), x['lon'].ravel()))
        cell_of = lambda idx: tree.query(xyz(R['lat'][idx], R['lon'][idx]))[1]
        inwin = lambda idx: (np.abs(R['lat'][idx] - LAT0) < HKM / 2 / 111.32) & (np.abs(R['lon'][idx] - LON0) < WKM / 2 / (111.32 * np.cos(np.radians(LAT0))))
        surveyed = np.zeros(land.size, bool); surveyed[cell_of(allsites[inwin(allsites)])] = True
        surveyed = (ndi.distance_transform_edt(~surveyed.reshape(land.shape)) * cell <= 3.0) & land
        sel = cl[inwin(cl)]; site_cells = cell_of(sel); on = surveyed.ravel()[site_cells]; sel, site_cells = sel[on], site_cells[on]
        args = {k: x[k] for k in ['density', 'land', 'water_km', 'road', 'elev', 'aridity', 'allowed']}; args['cell_km'] = float(cell)
        score, eligible = site_fields(**args)
        production, _, _ = settle.place_towns(**args, marked=[], seed=1); count = len(production)
        tile = dict(allowed=x['allowed'], aridity=x['aridity'])
        seat, release3 = match_count(lambda sp: prior_tiling_sites(x['density'], land, x['water_km'], x['road'], x['elev'], float(cell), prior=x['history800'], seat_people=sp, **tile), count)
        prod = np.asarray(production, int).reshape(-1, 2); rel = np.asarray(release3, int).reshape(-1, 2)
        fields = {'environment': np.where(eligible, score, 0.), 'release3': np.where(eligible, score * x['history800'], 0.)}
        g = dict(shape=[ny, nx], land_cells=int(land.sum()), surveyed_cells=int(surveyed.sum()), production_count=count, release3_seat_people=seat,
                 release3_count=len(rel), cohorts={})
        for name, m in (('classic', np.ones(len(sel), bool)), ('towns', np.nan_to_num(R['area'][sel]) >= 10)):
            cells = np.unique(site_cells[m]); c = dict(sites=int(m.sum()), distinct_cells=int(len(cells)))
            if len(cells):
                c['percentile'] = {k: float(np.mean(relative_ranks(f.ravel()[cells], f[surveyed]))) for k, f in fields.items()}
                c['capture_10km'] = {'production': capture_fraction(cells, prod, nx, float(cell), 10), 'release3': capture_fraction(cells, rel, nx, float(cell), 10)}
            g['cohorts'][name] = c
        if cell == 3:
            people_model = float((x['density'] * surveyed).sum() * cell ** 2)
            obs = {k: float(np.nansum(R[k][sel])) for k in ('pop', 'popmin', 'popmax')}
            g['people'] = dict(model=people_model, observed=obs, ratio=people_model / max(obs['pop'], 1.0),
                               surveyed_km2=float(surveyed.sum() * cell ** 2), passed=bool(0.5 <= people_model / max(obs['pop'], 1.0) <= 2.0))
        if cell == 9:
            people = np.where(land, x['density'], 0.) * cell ** 2
            (_, _, _), H = Z.hinterlands(rel, land, people, float(cell))
            keep = surveyed[rel[:, 0], rel[:, 1]] & (H > 0); n = int(keep.sum())
            areas = np.sort(np.nan_to_num(R['area'][sel]))[::-1]; areas = areas[areas > 0]; n = min(n, len(areas)); obs_a = areas[:n]
            coef = size_fit['models']['M1']['full_coefficients']; sigma = size_fit['models']['M1']['heldout_sigma']; lo_ha, hi_ha = size_fit['area_range_ha']
            mean = coef[0] + coef[1] * np.log(H[keep][:n] if n else H[keep]); runs = []
            for s_ in SEEDS:
                gen = np.sort(Z.generate_area(mean[:n], sigma, Z.draws(n, s_), lo_ha, hi_ha))[::-1]
                runs.append(dict(seed=s_, ks=float(ks_2samp(gen, obs_a).statistic) if n else None, total_ratio=float(gen.sum() / max(obs_a.sum(), 1e-9)),
                                 median_model=float(np.median(gen)) if n else None))
            ks = float(np.mean([r['ks'] for r in runs])) if n else None; tr = float(np.mean([r['total_ratio'] for r in runs]))
            g['sizes'] = dict(n=n, observed_total_ha=float(obs_a.sum()), observed_median_ha=float(np.median(obs_a)) if n else None,
                              observed_largest_ha=[float(v) for v in obs_a[:10]], runs=runs, mean_ks=ks, mean_total_ratio=tr,
                              passed=bool(n and ks <= 0.20 and 0.67 <= tr <= 1.5))
        result['grids'][str(cell)] = g
        arrays.update({f'{cell}km__production': prod, f'{cell}km__release3': rel, f'{cell}km__surveyed': surveyed, f'{cell}km__release3_field': fields['release3']})
        print(cell, json.dumps({k: v for k, v in g.items() if k not in ('sizes',)}), flush=True)
    t = result['grids']['3']['cohorts']['towns']
    p_pass = bool(t.get('percentile') and t['percentile']['release3'] >= 0.55 and t['capture_10km']['release3'] >= t['capture_10km']['production'] - 0.05)
    result.update(test_P_pass=p_pass, test_S_pass=result['grids']['9']['sizes']['passed'], test_N_pass=result['grids']['3']['people']['passed'], raw_rows_redistributed=False)
    np.savez_compressed(out / 'model.npz', **arrays); result['model_sha256'] = sha(out / 'model.npz')
    write(out / 'results.json', result); print('P', p_pass, 'S', result['test_S_pass'], 'N', result['test_N_pass'])
    print(json.dumps(result['grids']['9']['sizes'], indent=0)[:1200]); print(json.dumps(result['grids']['3']['people']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); main(ap.parse_args().out)
