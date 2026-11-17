"""Independent scalar constraint replay and area identities for every origin."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
# This is the packet reader under test; no production-model function is called.
from cereal_activity_packet import activity

OUT = ROOT / 'output/cereal_activity_packet_20261117'
KCAL = 912500.


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p): return json.loads(p.read_text())


def rows(p):
    with p.open() as f: return list(csv.DictReader(f))


def close(a, b, atol=1e-7):
    np.testing.assert_allclose(a, b, rtol=2e-12, atol=atol, equal_nan=True)


def decode(folder, field):
    spec = read(folder / 'harvest.json')['arrays'][field]
    assert spec['dtype'] == 'uint16'
    with (folder / 'harvest.bin').open('rb') as f:
        f.seek(spec['offset_bytes']); buffer = f.read(2 * math.prod(spec['shape']))
    raw = np.frombuffer(buffer, dtype='<u2').reshape(spec['shape'])
    return np.array([0. if x == spec['nodata'] else int(x) * spec['scale'] + spec['offset'] for x in raw.flat]).reshape(raw.shape)


def main():
    assert not (OUT / 'review.json').exists()
    result = read(OUT / 'results.json')
    for n, h in result['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in result['files_sha256'].items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *result['files_sha256']]:
        assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    supply = read(ROOT / 'output/urban_candidate_supply_20261116/results.json')
    summaries = {r['physical_case']: r for r in rows(OUT / 'cases.csv')}
    aliases = rows(OUT / 'scenario_aliases.csv'); controls = rows(OUT / 'controls.csv')
    support = {r['climate']: r for r in rows(OUT / 'support.csv')}
    assert len(aliases) == len(controls) == 32 and len(summaries) == 16
    assert {(r['model'], r['climate'], r['scenario']) for r in aliases} == {
        (m, c, n) for m in ['candidate', 'control'] for c in ['raw', 'corrected']
        for n in supply['variants'][m]['climates'][c]['scenarios']}
    origin_cases = 0; value_checks = 0; summary_values = 0; prior_ids = None
    field_maxima = {}; residuals = {}
    for mode in ['raw', 'corrected']:
        with np.load(OUT / f'activities_{mode}.npz') as z: packet = dict(z)
        get = lambda field: packet[mode + '__' + field]
        folder = ROOT / 'atlases/earth_fit/data' / ('corrected' if mode == 'corrected' else '')
        with np.load(folder / 'farm_work_grid.npz') as z: farm = dict(z)
        with np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z: inp = dict(z)
        ids = np.array([i for i, land in enumerate(inp['land'].flat) if land], dtype='<i4')
        np.testing.assert_array_equal(ids, get('origin'))
        assert len(set(ids.tolist())) == len(ids) == 241889
        if prior_ids is not None: np.testing.assert_array_equal(ids, prior_ids)
        prior_ids = ids
        energies = {c: decode(folder, 'kcal_' + c).ravel()[ids] for c in ['wheat', 'barley']}
        arable = decode(folder, 'arable').ravel()[ids]
        crop = farm['cereal'].ravel()[ids]; np.testing.assert_array_equal(crop, get('crop'))
        close(get('land_area_km2'), inp['area'].ravel()[ids]); close(get('arable_share'), arable)
        close(get('cell_km'), inp['cell_km']); np.testing.assert_array_equal(get('shape'), inp['shape'])
        expected_crop = []
        for w, b in zip(energies['wheat'], energies['barley']):
            wc = 336. / w if w > 0 else math.inf; bc = 208. / b if b > 0 else math.inf
            expected_crop.append(0 if not math.isfinite(min(wc, bc)) else (1 if wc <= bc else 2))
        np.testing.assert_array_equal(expected_crop, crop)
        selected = np.where(crop == 1, energies['wheat'], np.where(crop == 2, energies['barley'], np.nan))
        valid = crop > 0
        ha = np.where(valid, inp['area'].ravel()[ids].astype(float) * arable * 36., np.nan)
        close(get('net_kcal_ha'), selected); close(get('potential_area_ha'), ha)
        close(get('potential_kcal'), inp['potential_kcal'][ids])
        close(np.where(valid, selected * ha, 0.), get('potential_kcal'), atol=.01)
        for stored, field in [('listed_rate', 'listed_hours_per_million_kcal'),
                              ('reaping_rate', 'reaping_hours_per_million_kcal'),
                              ('land_rate', 'cropped_ha_per_million_kcal')]:
            np.testing.assert_array_equal(get(stored), np.nan_to_num(farm[field].astype(float)).ravel()[ids])
        np.testing.assert_array_equal(get('harvest_boundaries'), inp['boundaries'][ids])
        norm = np.where(crop == 1, 336., np.where(crop == 2, 208., np.nan))
        expected_support = dict(origins=len(ids), no_cereal=int((crop == 0).sum()),
            wheat_origins=int((crop == 1).sum()), barley_origins=int((crop == 2).sum()),
            farm_cells_excluded_from_transport=int((farm['land'] & ~inp['land']).sum()),
            potential_cropped_ha=math.fsum(ha[valid]), potential_ration_years=math.fsum(get('potential_kcal')) / KCAL)
        for name, value in expected_support.items(): close(float(support[mode][name]), value, atol=1e-5)
        for model in ['candidate', 'control']:
            with np.load(ROOT / f'output/urban_candidate_supply_20261116/packets/{model}/placed_{mode}_fields.npz') as z: fields = dict(z)
            for density in ['central', 'low']:
                rural = fields['rural_' + density].ravel()[ids]
                np.testing.assert_array_equal(packet[f'{model}__{mode}__{density}__rural_people'], rural)
                for hours in [600., 300.]:
                    case = f'{model}__{mode}__{density}__h{int(hours)}'
                    a = activity(packet, model, mode, density, hours)
                    kept = []; classifications = []
                    # Scalar arithmetic does not use field_support or the producer's min/divide arrays.
                    for p, rate, reap, people in zip(get('potential_kcal'), get('listed_rate'), get('reaping_rate'), rural):
                        p, rate, reap, people = map(float, [p, rate, reap, people])
                        workers = people * KCAL / KCAL * .4
                        annual = workers * hours; peak = min(annual, workers * 240.)
                        req = p * rate / 1e6; preq = p * reap / 1e6
                        f = 0. if p == 0 else min(1., annual / req if req > 0 else 1., peak / preq if preq > 0 else 1.)
                        kept.append(f)
                        aa = annual > 0 and abs(req * f - annual) <= 1e-10 * annual
                        pa = peak > 0 and abs(preq * f - peak) <= 1e-10 * peak
                        if p == 0: code = 0
                        elif workers == 0: code = 1
                        elif f >= 1 - 1e-10: code = 2
                        else:
                            assert aa or pa
                            code = 5 if aa and pa else (3 if aa else 4)
                        classifications.append(code)
                    kept = np.asarray(kept); need = rural * KCAL; workers = need / KCAL * .4
                    potential = get('potential_kcal'); produced = potential * kept
                    required = potential * get('listed_rate') / 1e6; peakreq = potential * get('reaping_rate') / 1e6
                    area = get('potential_area_ha') * kept; used = required * kept; reaped = peakreq * kept
                    expected = dict(origin=ids, crop=crop, potential_area_ha=get('potential_area_ha'), retained_area_ha=area,
                        net_kcal_ha=selected, retained_fraction=kept, rural_people=rural, rural_need_kcal=need,
                        workers=workers, annual_hours_available=workers * hours,
                        reaping_hours_available=workers * min(hours, 240.), listed_hours_required=required,
                        reaping_hours_required=peakreq, annual_hours_used=used, reaping_hours_used=reaped,
                        potential_kcal=potential, produced_kcal=produced, rural_retained_kcal=np.minimum(need, produced),
                        rural_shortfall_kcal=np.maximum(need - produced, 0.), surplus_kcal=np.maximum(produced - need, 0.),
                        rate_implied_potential_area_ha=potential * get('land_rate') / 1e6,
                        rate_implied_retained_area_ha=potential * get('land_rate') / 1e6 * kept,
                        work_implied_retained_area_ha=used / norm,
                        listed_hour_residual=used - area * norm,
                        limitation_code=np.asarray(classifications),
                        annual_active=(workers > 0) & (np.abs(used - workers * hours) <= 1e-10 * workers * hours),
                        reaping_active=(workers > 0) & (np.abs(reaped - workers * min(hours, 240.)) <= 1e-10 * workers * min(hours, 240.)))
                    assert set(a) == set(expected)
                    for name, value in expected.items():
                        if name in ['origin', 'crop', 'limitation_code', 'annual_active', 'reaping_active']:
                            np.testing.assert_array_equal(a[name], value)
                        else:
                            close(a[name], value, atol=.01 if name.endswith('kcal') else 1e-7)
                            diff = abs(a[name] - value); finite = np.isfinite(diff)
                            field_maxima[name] = max(field_maxima.get(name, 0.), float(diff[finite].max(initial=0.)))
                        value_checks += len(ids)
                    # Per-origin land, calorie, and resource identities retain float packet residuals.
                    close(np.where(valid, area * selected, 0.), produced, atol=.01)
                    assert np.nanmax(abs(used - area * norm) / np.where(used > 0, used, 1.)) <= 1e-7
                    assert np.all(used <= workers * hours + 1e-5) and np.all(reaped <= workers * min(hours, 240.) + 1e-5)
                    close(produced, np.minimum(produced, need) + np.maximum(produced - need, 0.), atol=.01)
                    row = summaries[case]
                    scalar = dict(origins=len(ids), potential_cropped_ha=math.fsum(get('potential_area_ha')[valid]),
                        retained_cropped_ha=math.fsum(area[valid]), produced_ration_years=math.fsum(produced) / KCAL,
                        cropped_area_retained_fraction=math.fsum(area[valid]) / math.fsum(get('potential_area_ha')[valid]),
                        max_relative_listed_hour_residual=float(np.nanmax(abs(used - area * norm) / np.where(used > 0, used, 1.))),
                        signed_listed_hour_residual=float(np.nansum(used - area * norm)),
                        max_relative_rate_implied_area_residual=float(np.nanmax(abs(expected['rate_implied_retained_area_ha'] - area) / np.where(area > 0, area, 1.))))
                    for i in range(6): scalar['category_' + str(i) + '_origins'] = classifications.count(i)
                    for name, value in scalar.items(): close(float(row[name]), value, atol=1e-5); summary_values += 1
                    for alias in [r for r in aliases if r['physical_case'] == case]:
                        s = supply['variants'][model]['climates'][mode]['scenarios'][alias['scenario']]
                        d = supply['diagnostics'][model][mode][alias['scenario']]
                        assert (s['density'], s['hours_worker_year'], s['extraction']) == (density, hours, float(alias['marketed_fraction']))
                        control = next(r for r in controls if (r['model'], r['climate'], r['scenario']) == (model, mode, alias['scenario']))
                        assert control['physical_case'] == case and int(control['exact_scalars']) == 13
                        assert float(control['original_production_ration_years']) == s['produced_person_years']
                        close(math.fsum(produced) / KCAL, s['produced_person_years'], atol=1e-5)
                        close(math.fsum(expected['surplus_kcal']) / KCAL, d['source_surplus_person_years'], atol=1e-5)
                        close(math.fsum(used), d['annual_hours_used'], atol=1e-4)
                        close(math.fsum(reaped), d['reaping_hours_used'], atol=1e-4)
                    residuals[case] = float(np.nansum(used - area * norm))
                    origin_cases += len(ids)
            print(f'Reviewed {model}/{mode}: four activity cases', flush=True)
    assert origin_cases == 3870224 and result['exact_original_scalar_controls'] == 416
    write = lambda p, d: p.write_text(json.dumps(d, indent=2, allow_nan=False) + '\n')
    write(OUT / 'review.json', dict(status='passed_all_origin_scalar_retention_area_work_food_and_identity_checks',
        results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(Path(__file__)),
        physical_cases=16, origin_case_rows=origin_cases, materialized_values_checked=value_checks,
        summary_values_checked=summary_values, exact_original_scalar_controls=416,
        max_reader_vs_independent_differences=field_maxima, signed_listed_hour_residuals=residuals,
        fresh_exports_byte_exact=True, archived_binary_layout_reused=True,
        scope='Independent scalar min/division replay, crop choice, decoded area/energy and all reader columns. Packet materializer is under test; field_support is not called by reviewer. No independent biological/historical validation.',
        new_scenarios=0, adopt=False))
    print(f'Passed {origin_cases} origin/case rows, {value_checks} materialized values', flush=True)


if __name__ == '__main__': main()
