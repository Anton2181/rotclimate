"""Release-2 Earth calibration: placement confirmation test and city-size fit.

Declared in calibration/settlement_release2_20261113/plan.json before any fit.
Raw catalogue rows stay in the ignored cache; outputs are aggregates plus the
fitted coefficients needed to rebuild the fantasy settlements.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import ks_2samp, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import settlement_sizes as Z
from rotclimate.earth import forward
from settlement_locations_earth import metrics, sha, write
from settlement_intensity_earth import quality

PLAN = ROOT / 'calibration/settlement_release2_20261113/plan.json'
OUT = ROOT / 'output/settlement_release2_20261113'
CACHE = ROOT / 'data/cache/roman_city_source_recovery_20261113'
POOLS = ROOT / 'output/settlement_locations_20261110'
CORE = ROOT / 'output/core_population_inputs_20261111'
POSITIONS = ROOT / 'output/settlement_joint_locations_20261112/positions.npz'
WINDOWS = json.loads((ROOT / 'calibration/polity_20261025/plan.json').read_text())['earth_windows']
SEEDS = (1, 7, 19, 43, 97)


def committed_plan():
    blob = subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT)
    if blob != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration before running')
    return json.loads(blob)


def quadrant_test():
    """Finalist versus production inside four allowed-land quadrants per pool."""
    positions = np.load(POSITIONS)
    rows = []
    for pool in ('han', 'rome'):
        x = dict(np.load(POOLS / f'{pool}_inputs.npz'))
        ar, ac = np.nonzero(x['allowed'])
        mr, mc = np.median(ar), np.median(ac)
        yy, xx = np.indices(x['allowed'].shape)
        whole = {}
        for variant in ('production', 'fixed18_L800'):
            towns = positions[f'{pool}__{variant}__1']
            m = metrics(x, towns); whole[variant] = quality(m)
        rows.append(dict(pool=pool, quadrant='whole', production_Q=whole['production'], finalist_Q=whole['fixed18_L800']))
        for name, mask in (('north_west', (yy <= mr) & (xx <= mc)), ('north_east', (yy <= mr) & (xx > mc)),
                           ('south_west', (yy > mr) & (xx <= mc)), ('south_east', (yy > mr) & (xx > mc))):
            sub = dict(x); sub['allowed'] = x['allowed'] & mask
            row = dict(pool=pool, quadrant=name)
            for variant, label in (('production', 'production'), ('fixed18_L800', 'finalist')):
                towns = positions[f'{pool}__{variant}__1']
                inside = towns[sub['allowed'][towns[:, 0], towns[:, 1]]]
                m = metrics(sub, inside)
                row.update({f'{label}_Q': quality(m), f'{label}_unique_F1': m['unique_F1'], f'{label}_M1': m['M1'],
                            f'{label}_M3': m['M3'], f'{label}_centres': len(inside), 'observed_cells': m['n_real']})
            rows.append(row)
    quads = [r for r in rows if r['quadrant'] != 'whole']
    wins = sum(r['finalist_Q'] > r['production_Q'] for r in quads)
    pools = all(r['finalist_Q'] > r['production_Q'] for r in rows if r['quadrant'] == 'whole')
    return dict(rows=rows, quadrant_wins=wins, quadrants=len(quads), both_pools_better=pools,
                passed=bool(wins >= 6 and pools))


def cohort():
    cities = list(csv.DictReader(io.StringIO((CACHE / 'cities.csv').read_bytes().decode('cp1252'))))
    areas = {r['Primary Key']: float(r['Area']) for r in
             csv.DictReader(io.StringIO((CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    x = dict(np.load(POOLS / 'rome_inputs.npz')); h = dict(np.load(CORE / 'rome_history.npz'))
    cell = float(x['cell_km']); land = x['land']; ny, nx = land.shape
    keep = [r for r in cities if float(r['Start Date']) <= 150 and (r['End Date'].strip().upper() == 'NULL' or float(r['End Date']) >= 150)]
    lat = np.array([float(r['Latitude (Y)']) for r in keep]); lon = np.array([float(r['Longitude (X)']) for r in keep])
    w = WINDOWS['rome']; px, py = forward(lat, lon, w['lat0'], w['lon0'])
    col = np.round(px / cell + (nx - 1) / 2).astype(int); row = np.round((ny - 1) / 2 - py / cell).astype(int)
    inside = (row >= 0) & (row < ny) & (col >= 0) & (col < nx)
    _, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True)
    rc, cc = np.clip(row, 0, ny - 1), np.clip(col, 0, nx - 1)
    sr, sc = iy[rc, cc], ix[rc, cc]
    flat = np.unique((sr * nx + sc)[inside])
    legacy_exact = bool(np.array_equal(flat, x['real']))
    # one hinterland per distinct occupied cell; cities sharing a cell share it
    centres = np.column_stack(np.unravel_index(flat, land.shape))
    people = np.where(land, x['density'], 0.0) * cell ** 2
    _, H = Z.hinterlands(centres, land, people, cell)  # equal split of exactly tied cells
    index = {int(f): i for i, f in enumerate(flat)}
    pred = Z.site_predictors(centres, land, x['water_km'], x['road'], cell, h['distance_km'])
    rows = []
    counts = dict(catalogue_AD150=len(keep), inside_window=int(inside.sum()), distinct_cells=len(flat),
                  legacy_cells_reproduced=legacy_exact, no_area_record=0, off_allowed=0, zero_hinterland=0,
                  shared_cell_records=0, nonfinite_core=0)
    cell_use = {}
    for r, ok, a, b in zip(keep, inside, sr, sc):
        if not ok:
            continue
        key = r['Primary Key']
        if key not in areas:
            counts['no_area_record'] += 1; continue
        if not x['allowed'][a, b]:
            counts['off_allowed'] += 1; continue
        i = index[int(a * nx + b)]
        if H[i] <= 0:
            counts['zero_hinterland'] += 1; continue
        if not np.isfinite(pred['core'][i]):
            counts['nonfinite_core'] += 1; continue
        cell_use[i] = cell_use.get(i, 0) + 1
        rows.append(dict(key=key, province=r['Province'], area=areas[key], lnH=float(np.log(H[i])), cell=i,
                         **{k: float(pred[k][i]) for k in ('coast', 'river', 'road', 'core')}))
    counts['shared_cell_records'] = sum(v for v in cell_use.values() if v > 1)
    counts['with_area_on_allowed_land'] = len(rows)
    return rows, counts, areas


def evaluate(rows, label):
    y = np.log([r['area'] for r in rows]); fold = np.array([Z.province_fold(r['province']) for r in rows])
    cols = {k: np.array([r[k] for r in rows]) for k in ('lnH', 'coast', 'river', 'road', 'core')}
    take = lambda m: {k: v[m] for k, v in cols.items()}
    out = dict(cohort=label, n=len(rows), provinces=len({r['province'] for r in rows}),
               fold_sizes=[int((fold == f).sum()) for f in range(4)],
               fold_provinces=[len({r['province'] for r, f2 in zip(rows, fold) if f2 == f}) for f in range(4)], models={})
    held = {}
    for name, names in Z.MODELS.items():
        pred = np.empty(len(y)); fold_mae = []
        for f in range(4):
            coef = Z.fit(take(fold != f), names, y[fold != f])
            pred[fold == f] = Z.predict(take(fold == f), names, coef)
            fold_mae.append(float(np.mean(np.abs(y[fold == f] - pred[fold == f]))))
        res = y - pred; held[name] = pred
        full = Z.fit(cols, names, y)
        out['models'][name] = dict(terms=['intercept', *names], heldout_mae=float(np.mean(np.abs(res))),
            heldout_rmse=float(np.sqrt(np.mean(res ** 2))), heldout_sigma=float(np.std(res)),
            heldout_r2=float(1 - np.sum(res ** 2) / np.sum((y - y.mean()) ** 2)), fold_mae=fold_mae,
            heldout_spearman=float(spearmanr(pred, y).statistic) if names else 0.0,
            full_coefficients=[float(v) for v in full])
    order = ['M0', 'M1', 'M2', 'M3']; chosen = 'M0'
    for name in order[1:]:
        if out['models'][name]['heldout_mae'] <= out['models'][chosen]['heldout_mae'] * 0.98:
            chosen = name
    out['selected'] = chosen
    sigma = out['models'][chosen]['heldout_sigma']; area = np.exp(y)
    ks, ratio = [], []
    for seed in SEEDS:
        gen = Z.generate_area(held[chosen], sigma, Z.draws(len(y), seed), area.min(), area.max())
        ks.append(float(ks_2samp(gen, area).statistic)); ratio.append(float(gen.sum() / area.sum()))
    out['gate'] = dict(ks_by_seed=ks, total_area_ratio_by_seed=ratio, mean_ks=float(np.mean(ks)),
        mean_total_area_ratio=float(np.mean(ratio)),
        passed=bool(np.mean(ks) <= 0.10 and 0.80 <= np.mean(ratio) <= 1.25))
    out['area_range_ha'] = [float(area.min()), float(area.max())]
    out['observed_quantiles_ha'] = {str(q): float(np.quantile(area, q)) for q in (.05, .25, .5, .75, .95)}
    gen = Z.generate_area(held[chosen], sigma, Z.draws(len(y), 1), area.min(), area.max())
    out['generated_seed1_quantiles_ha'] = {str(q): float(np.quantile(gen, q)) for q in (.05, .25, .5, .75, .95)}
    return out


def run(out):
    plan = committed_plan(); out.mkdir(parents=True, exist_ok=True)
    placement = quadrant_test()
    rows, counts, areas = cohort()
    primary = [r for r in rows if r['area'] not in (20.0, 30.0)]
    results = dict(primary=evaluate(primary, 'primary_without_20_30_ha'), all_values=evaluate(rows, 'all_values'))
    walls = [r for r in primary]
    official = np.array(list(areas.values()))
    x = dict(np.load(POOLS / 'rome_inputs.npz')); cell = float(x['cell_km'])
    model_people = float((np.where(x['land'] & x['allowed'], x['density'], 0.0) * cell ** 2).sum())
    cohort_area = np.array([r['area'] for r in rows])
    result = dict(
        status='release2_earth_calibration_exposed_pools_internal_blocked_tests',
        plan_sha256=sha(PLAN), producer_sha256=sha(__file__), model_sha256=sha(ROOT / 'polity/settlement_sizes.py'),
        sources=dict(cities=sha(CACHE / 'cities.csv'), areas=sha(CACHE / 'areas.csv'),
                     rome_inputs=sha(POOLS / 'rome_inputs.npz'), han_inputs=sha(POOLS / 'han_inputs.npz'),
                     rome_history=sha(CORE / 'rome_history.npz'), positions=sha(POSITIONS)),
        counts_decision=plan['counts']['decision'],
        placement=placement, size_cohort=counts, sizes=results,
        residents=dict(
            central_total_all_885_official_areas=float(Z.residents(official, 'central').sum()),
            low_total_all_885_official_areas=float(Z.residents(official, 'low').sum()),
            published_reference_range=[10.6e6, 12.2e6],
            cohort_central_residents=float(Z.residents(cohort_area, 'central').sum()),
            cohort_low_residents=float(Z.residents(cohort_area, 'low').sum()),
            model_people_on_allowed_land=model_people,
            cohort_central_share_of_model_people=float(Z.residents(cohort_area, 'central').sum() / model_people),
            cohort_low_share_of_model_people=float(Z.residents(cohort_area, 'low').sum() / model_people)),
        raw_rows_redistributed=False,
        limits='All pools are exposed development data. Province- and quadrant-blocked tests are internal hold-outs declared before fitting, '
               'not blind external validation. Areas are catalogue extents with mixed estimate bases; residents are a density scenario.')
    write(out / 'results.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT)
    r = run(p.parse_args().out)
    print(json.dumps({k: r[k] for k in ('placement', 'size_cohort', 'residents')}, indent=1)[:6000])
    for k, v in r['sizes'].items():
        print(k, v['n'], v['fold_sizes'], 'selected', v['selected'], json.dumps(v['gate']))
        for m, d in v['models'].items():
            print('  ', m, {a: round(b, 4) for a, b in d.items() if isinstance(b, float)}, [round(c, 3) for c in d['full_coefficients']])
