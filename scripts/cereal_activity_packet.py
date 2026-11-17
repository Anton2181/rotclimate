"""Recover fixed annual cereal activities; replay existing field work only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harvest.field_support import field_support

OUT = ROOT / 'output/cereal_activity_packet_20261117'
SUPPLY = ROOT / 'output/urban_candidate_supply_20261116'
PARENT = ROOT / 'output/annual_agricultural_budget_20261117'
PLANS = ['calibration/roman_benchmark_20261117/cereal_activity_packet.json',
         'calibration/roman_benchmark_20261117/cereal_activity_precision.json']
KCAL = 2500. * 365.
CATEGORIES = ['No cereal output', 'No effective workers', 'Potential ceiling',
              'Annual work limits area', 'Reaping limits area', 'Both work limits']


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def write(p, d):
    p.write_text(json.dumps(d, indent=2, allow_nan=False) + '\n')


def table(p, rows):
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def decode(folder, name):
    meta = read(folder / 'harvest.json')['arrays'][name]
    blob = (folder / 'harvest.bin').read_bytes()
    raw = np.frombuffer(blob, dtype=np.dtype(meta['dtype']), count=int(np.prod(meta['shape'])),
                        offset=meta['offset_bytes']).reshape(meta['shape'])
    value = raw.astype(float) * meta['scale'] + meta['offset']
    return np.where(raw == meta['nodata'], 0., value)


def key(model, mode, density, hours):
    return f'{model}__{mode}__{density}__h{int(hours)}'


def load_packet(folder, mode):
    with np.load(folder / f'activities_{mode}.npz') as z:
        return dict(z)


def activity(packet, model, mode, density, hours):
    """Materialize aligned columns from deduplicated arrays; no constraint solve."""
    get = lambda n: packet[f'{mode}__{n}']
    rural = packet[f'{model}__{mode}__{density}__rural_people']
    retained = packet[key(model, mode, density, hours) + '__retained']
    potential = get('potential_kcal'); need = rural * KCAL
    workers = need / KCAL * .4
    annual = workers * hours; peak = np.minimum(annual, workers * 240.)
    listed_required = potential * get('listed_rate') / 1e6
    reaping_required = potential * get('reaping_rate') / 1e6
    used = listed_required * retained; reaped = reaping_required * retained
    produced = potential * retained
    annual_ratio = np.divide(used, annual, out=np.zeros_like(annual), where=annual > 0)
    peak_ratio = np.divide(reaped, peak, out=np.zeros_like(peak), where=peak > 0)
    annual_active = (annual > 0) & (abs(annual_ratio - 1) <= 1e-10)
    peak_active = (peak > 0) & (abs(peak_ratio - 1) <= 1e-10)
    positive = potential > 0; no_workers = positive & (workers == 0)
    limited = positive & ~no_workers & (retained < 1 - 1e-10)
    code = np.where(positive, 2, 0).astype('u1')
    code[no_workers] = 1
    code[limited & annual_active & ~peak_active] = 3
    code[limited & ~annual_active & peak_active] = 4
    code[limited & annual_active & peak_active] = 5
    assert np.all((~limited) | annual_active | peak_active)
    hectares = get('potential_area_ha'); area = hectares * retained
    norm = np.where(get('crop') == 1, 336., np.where(get('crop') == 2, 208., np.nan))
    land_rate_area = potential * get('land_rate') / 1e6
    return dict(origin=get('origin'), crop=get('crop'), potential_area_ha=hectares,
        retained_area_ha=area, net_kcal_ha=get('net_kcal_ha'), retained_fraction=retained,
        rural_people=rural, rural_need_kcal=need, workers=workers,
        annual_hours_available=annual, reaping_hours_available=peak,
        listed_hours_required=listed_required, reaping_hours_required=reaping_required,
        annual_hours_used=used, reaping_hours_used=reaped,
        potential_kcal=potential, produced_kcal=produced,
        rural_retained_kcal=np.minimum(need, produced),
        rural_shortfall_kcal=np.maximum(need - produced, 0), surplus_kcal=np.maximum(produced - need, 0),
        rate_implied_potential_area_ha=land_rate_area,
        rate_implied_retained_area_ha=land_rate_area * retained,
        work_implied_retained_area_ha=used / norm,
        listed_hour_residual=used - area * norm,
        limitation_code=code, annual_active=annual_active, reaping_active=peak_active)


def verify_parent():
    q = read(PARENT / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(PARENT / n) == h, n
    # Latest full protected inventory is reached through this pinned parent.
    p = ROOT / 'output/annual_assumption_impact_20261117'; old = read(p / 'qualification.json')
    for n, h in {**old['sources_sha256'], **old['protected_sha256']}.items(): assert sha(ROOT / n) == h, n
    for n, h in old['files_sha256'].items(): assert sha(p / n) == h, n
    return q


def main(out):
    assert not (out / 'results.json').exists(), 'Use an isolated --out'
    for n in PLANS:
        assert subprocess.check_output(['git', 'show', 'HEAD:' + n], cwd=ROOT) == (ROOT / n).read_bytes()
    verify_parent(); source = read(SUPPLY / 'results.json')
    paths = [ROOT / n for n in PLANS] + [Path(__file__), ROOT / 'harvest/field_support.py',
        PARENT / 'qualification.json', SUPPLY / 'results.json', SUPPLY / 'review.json',
        ROOT / 'research_notes/farm_labour_20261103.json']
    assert sha(ROOT / 'harvest/field_support.py') == source['sources_sha256']['harvest/field_support.py']
    packet = {}; supports = []; controls = []; summaries = []; aliases = []; checks = 0
    for mode in ['raw', 'corrected']:
        folder = ROOT / 'atlases/earth_fit/data' / ('corrected' if mode == 'corrected' else '')
        inp = ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz'
        prep = inp.with_name(f'{mode}_preparation.json')
        assert sha(inp) == read(prep)['inputs_sha256']
        for n in ['farm_work_grid.npz', 'harvest.json', 'harvest.bin']:
            p = folder / n; paths.append(p)
            assert sha(p) == read(prep)['sources'][str(p.relative_to(ROOT))]
        paths.extend([inp, prep])
        with np.load(inp) as z: x = dict(z)
        with np.load(folder / 'farm_work_grid.npz') as z: farm = dict(z)
        land = x['land']; ids = np.flatnonzero(land.ravel()).astype('<i4')
        shape = tuple(land.shape); assert shape == (463, 1000)
        energy = {c: decode(folder, 'kcal_' + c) for c in ['wheat', 'barley']}
        arable = decode(folder, 'arable'); crop = farm['cereal']
        wh = np.divide(336., energy['wheat'], out=np.full(shape, np.inf), where=energy['wheat'] > 0)
        bh = np.divide(208., energy['barley'], out=np.full(shape, np.inf), where=energy['barley'] > 0)
        choice = np.where(np.isfinite(np.minimum(wh, bh)), np.where(wh <= bh, 1, 2), 0)
        np.testing.assert_array_equal(np.where(farm['land'], choice, 0), crop)
        np.testing.assert_array_equal(x['listed_hours'], np.nan_to_num(farm['listed_hours_per_million_kcal']).ravel().astype(float))
        np.testing.assert_array_equal(x['reaping_hours'], np.nan_to_num(farm['reaping_hours_per_million_kcal']).ravel().astype(float))
        np.testing.assert_array_equal(x['boundaries'], farm['harvest_boundaries'].ravel())
        selected = np.where(crop == 1, energy['wheat'], np.where(crop == 2, energy['barley'], 0.))
        # Archived cell area is float32. Promote BEFORE the hectare conversion;
        # multiplying the native array by 100 would introduce a new rounding.
        recovered_land_area = x['area'].astype(float)
        planned_area = 100 * recovered_land_area * arable * .6 * .6
        reconstructed = np.where(land, selected * 100 * x['area'] * arable * .6 * .6, 0.).ravel()
        np.testing.assert_array_equal(reconstructed, x['potential_kcal'])
        valid = (crop > 0) & (selected > 0)
        common = dict(origin=ids, shape=np.array(shape), cell_km=x['cell_km'],
            crop=crop.ravel()[ids], land_area_km2=recovered_land_area.ravel()[ids], arable_share=arable.ravel()[ids],
            potential_area_ha=np.where(valid, planned_area, np.nan).ravel()[ids],
            net_kcal_ha=np.where(valid, selected, np.nan).ravel()[ids],
            potential_kcal=x['potential_kcal'][ids], listed_rate=x['listed_hours'][ids],
            reaping_rate=x['reaping_hours'][ids],
            land_rate=np.nan_to_num(farm['cropped_ha_per_million_kcal']).astype(float).ravel()[ids],
            harvest_boundaries=x['boundaries'][ids])
        packet.update({mode + '__' + k: v for k, v in common.items()})
        if mode == 'corrected': np.testing.assert_array_equal(packet['raw__origin'], ids)
        supports.append(dict(climate=mode, origins=len(ids), no_cereal=int((common['crop'] == 0).sum()),
            wheat_origins=int((common['crop'] == 1).sum()), barley_origins=int((common['crop'] == 2).sum()),
            farm_cells_excluded_from_transport=int((farm['land'] & ~land).sum()),
            potential_cropped_ha=float(np.nansum(common['potential_area_ha'])),
            potential_ration_years=float(common['potential_kcal'].sum() / KCAL)))
        for model in ['candidate', 'control']:
            fp = SUPPLY / f'packets/{model}/placed_{mode}_fields.npz'; paths.append(fp)
            with np.load(fp) as z: fields = dict(z)
            np.testing.assert_array_equal(fields['land'], land)
            scenarios = source['variants'][model]['climates'][mode]['scenarios']
            for density in ['central', 'low']:
                rural = fields['rural_' + density].ravel(); need = rural * KCAL
                assert not np.any(rural[~land.ravel()])
                packet[f'{model}__{mode}__{density}__rural_people'] = rural[ids]
                for hours in [600., 300.]:
                    case = key(model, mode, density, hours)
                    work = field_support(reconstructed, x['listed_hours'], x['reaping_hours'],
                                         rural_need_kcal=need, hours_worker_year=hours)
                    packet[case + '__retained'] = work.retained[ids]
                    deficit = np.maximum(need - work.produced_kcal, 0.)
                    surplus = np.where(land.ravel(), np.maximum(work.produced_kcal - need, 0.), 0.)
                    for name, s in scenarios.items():
                        if s['density'] != density or s['hours_worker_year'] != hours: continue
                        d = source['diagnostics'][model][mode][name]
                        exact = dict(rural_people=float(rural.sum()), rural_workers=float(work.workers.sum()),
                            rural_food_shortfall_person_years=float(deficit[ids].sum() / KCAL),
                            cells_below_rural_need=int((land.ravel() & (deficit > 1e-6)).sum()),
                            production_forgone_person_years=float((reconstructed - work.produced_kcal)[ids].sum() / KCAL),
                            annual_hours_available=float(work.annual_hours_available[ids].sum()),
                            annual_hours_used=float(work.annual_hours_used[ids].sum()),
                            reaping_hours_available=float(work.reaping_hours_available[ids].sum()),
                            reaping_hours_used=float(work.reaping_hours_used[ids].sum()),
                            rural_need_person_years=float(need[ids].sum() / KCAL),
                            source_surplus_person_years=float(surplus.sum() / KCAL),
                            marketed_person_years=float(surplus.sum() * s['extraction'] / KCAL))
                        assert all(d[k] == v for k, v in exact.items()), (case, name, [(k, d[k], v) for k, v in exact.items() if d[k] != v])
                        assert float(work.produced_kcal[ids].sum() / KCAL) == s['produced_person_years']
                        checks += len(exact) + 1
                        controls.append(dict(model=model, climate=mode, scenario=name, physical_case=case,
                            exact_scalars=len(exact) + 1, original_production_ration_years=s['produced_person_years']))
                        aliases.append(dict(model=model, climate=mode, scenario=name, physical_case=case, marketed_fraction=s['extraction']))
                    a = activity(packet, model, mode, density, hours)
                    norm = np.where(a['crop'] == 1, 336., np.where(a['crop'] == 2, 208., np.nan))
                    ratio = np.abs(a['listed_hour_residual']) / np.where(a['annual_hours_used'] > 0, a['annual_hours_used'], 1.)
                    assert float(np.nanmax(ratio)) <= 1e-7
                    area_ratio = np.abs(a['rate_implied_retained_area_ha'] - a['retained_area_ha']) / np.where(a['retained_area_ha'] > 0, a['retained_area_ha'], 1.)
                    assert float(np.nanmax(area_ratio)) <= 1e-7
                    summary = dict(physical_case=case, model=model, climate=mode, density=density, hours_worker_year=hours,
                        origins=len(ids), potential_cropped_ha=float(np.nansum(a['potential_area_ha'])),
                        retained_cropped_ha=float(np.nansum(a['retained_area_ha'])),
                        cropped_area_retained_fraction=float(np.nansum(a['retained_area_ha']) / np.nansum(a['potential_area_ha'])),
                        produced_ration_years=float(a['produced_kcal'].sum() / KCAL),
                        max_relative_listed_hour_residual=float(np.nanmax(ratio)),
                        signed_listed_hour_residual=float(np.nansum(a['listed_hour_residual'])),
                        max_relative_rate_implied_area_residual=float(np.nanmax(area_ratio)))
                    for i in range(len(CATEGORIES)): summary['category_' + str(i) + '_origins'] = int((a['limitation_code'] == i).sum())
                    summaries.append(summary)
    assert len(summaries) == 16 and len(aliases) == 32
    out.mkdir(parents=True, exist_ok=True)
    for mode in ['raw', 'corrected']:
        selected = {k: v for k, v in packet.items() if k.startswith(mode + '__') or '__' + mode + '__' in k}
        np.savez_compressed(out / f'activities_{mode}.npz', **selected)
    for n, rows in [('support.csv', supports), ('cases.csv', summaries), ('controls.csv', controls), ('scenario_aliases.csv', aliases)]: table(out / n, rows)
    write(out / 'schema.json', dict(grid_shape=[463, 1000], origin_identity='row*1000+column',
        common='climate__field: shared physical/crop/precision inputs; float64, NaN for undefined cereal area/yield',
        cohort='model__climate__density__rural_people: one actual fixed rural workforce basis',
        case='model__climate__density__hHOURS__retained: canonical retained fraction; use activity() to materialize aligned area/work/food columns',
        scenario_aliases='Extraction shares reference physical cases and must never duplicate land/workforce.',
        categories={str(i): n for i, n in enumerate(CATEGORIES)},
        bytes={mode: (out / f'activities_{mode}.npz').stat().st_size for mode in ['raw', 'corrected']},
        historical_scope='Annual listed cereal operations only; no independent population, crop diversity, complete occupation or seasonal validation.'))
    paths = sorted(set(paths))
    files = ['activities_raw.npz', 'activities_corrected.npz', 'support.csv', 'cases.csv', 'controls.csv', 'scenario_aliases.csv', 'schema.json']
    write(out / 'results.json', dict(status='recovered_fixed_annual_cereal_activity_packet_pending_review',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths},
        files_sha256={n: sha(out / n) for n in files}, physical_cases=16, supply_scenarios=32,
        literal_field_support_replays=16, exact_original_scalar_controls=checks,
        crop_choice_mismatches=0, potential_reconstruction_byte_exact=True,
        climate_crop_route_placement_calls=0, new_scenarios=0, new_fit=False, main_atlas_changed=False, adopt=False))
    print(f'16 activity cases; 32 scenario aliases; {checks} exact archived scalars; two climate packets', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
