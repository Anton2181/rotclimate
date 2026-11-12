"""Predeclared64-point robustness and explicit existing staff-threshold probes."""
import argparse
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from build_settlement_feedback import inventory_fields, audit_positive
from polity.settlement_feedback import FeedbackInputs
from polity.settlement_dispatch import DispatchFeedback

OUT = ROOT / 'output/settlement_dispatch_search_20261112'
PLAN = ROOT / 'calibration/settlement_dispatch_search_20261112/plan.json'
PARENT = ROOT / 'output/settlement_feedback_20261112'
JOINT = ROOT / 'output/settlement_dispatch_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'


def capture(trial):
    fields = {name: trial[name] for name in ('total', 'rural', 'moved', 'staff', 'civil', 'active',
        'source_supported', 'source_deficit_origins', 'feasible', 'dispatch_scale', 'maximum_dispatch_scale',
        'collection_hours', 'staff_gross_hours', 'origin_trips')}
    fields.update(origin_departures=trial['flow']['origin_departures'], arrivals=trial['flow']['arrivals'],
        produced_kcal=trial['work'].produced_kcal, annual_hours_used=trial['work'].annual_hours_used,
        reaping_hours_used=trial['work'].reaping_hours_used,
        **inventory_fields('rural_', trial['rural_food'].year), **inventory_fields('export_', trial['flow']['export_year']),
        **inventory_fields('town_', trial['town_food']))
    return fields


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit exact search-check declaration first')
    publication = json.loads((JOINT / 'atlas_publication.json').read_text())
    preserved = dict(publication['original_packets_sha256'])
    preserved['atlases/earth_fit/data/settlement_dispatch.json'] = publication['manifest_sha256']
    for path in (ROOT / 'atlases/earth_fit/data/dispatch').rglob('*'):
        if path.is_file(): preserved[str(path.relative_to(ROOT))] = sha(path)
    sources = {str(p.relative_to(ROOT)): sha(p) for p in (PLAN, Path(__file__), ROOT / 'polity/settlement_dispatch.py',
        ROOT / 'polity/settlement_feedback.py', ROOT / 'harvest/field_support.py', ROOT / 'harvest/food_stocks.py',
        ROOT / 'scripts/build_settlement_feedback.py', ROOT / 'polity/settlement_residents.py')}
    fields = {}; rows = []
    for mode, hours in itertools.product(('raw', 'corrected'), (600, 300)):
        key = f'{mode}_h{hours}_load120000_all_open'; folder = JOINT / key
        old = dict(np.load(folder / 'fields.npz')); result = json.loads((folder / 'results.json').read_text())
        review = json.loads((folder / 'review.json').read_text())
        assert review['status'] == 'passed' and review['results_sha256'] == sha(folder / 'results.json')
        for path, digest in {**result['sources'], **result['producers']}.items():
            if sha(ROOT / path) != digest: raise ValueError('Changed joint source: ' + path)
        for path in (PARENT / f'{mode}_inputs.npz', WORK / f'{mode}_paths.npz', folder / 'results.json', folder / 'fields.npz', folder / 'review.json'):
            sources[str(path.relative_to(ROOT))] = sha(path)
        x = dict(np.load(PARENT / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz'))
        local = x['local_index']; n = len(x['nodes'])
        inputs = FeedbackInputs(x['people'][local], x['owner'], x['potential_kcal'][local], x['boundaries'][local],
            x['listed_hours'][local], x['reaping_hours'][local], x['access'], x['civilian_request'], x['affiliated'],
            np.bincount(x['owner'], weights=x['potential_kcal'][local], minlength=n))
        m = DispatchFeedback(inputs, outward_days=paths['outward_days'], inward_days=paths['inward_days'],
            load_kcal=120000., monthly_open=np.ones(12, bool), transfer_fraction=.075, hours_worker_year=hours)
        print(key, 'checking64intervals and existing150-person staff transition', flush=True)
        fine = m.solve(scan_intervals=64)
        gate = audit_positive(m, fine)
        overlap_fields = dict(scan_feasible=np.stack([s['feasible'] for s in fine['scan']]),
            scan_source_supported=np.stack([s['source_supported'] for s in fine['scan']]),
            scan_destination_unmet=np.stack([s['destination_unmet'] for s in fine['scan']]))
        for name, value in overlap_fields.items():
            if not np.array_equal(value[::2], old[name]): raise ValueError('Changed original overlap points: ' + key + name)
            fields[key + '__fine_' + name] = value
        for name, value in capture(fine).items(): fields[key + '__fine_' + name] = value
        fields[key + '__upper'] = m.upper; fields[key + '__budget'] = m.budget
        fields[key + '__fine_selected_fraction'] = fine['selected_fraction']
        fields[key + '__fine_refined_upper_fraction'] = fine['refined_upper_fraction']
        probe_rows = []
        for offset in (-1e-6, 0., 1e-6):
            threshold = 150. + offset; eligible = m.upper >= threshold
            trial = m.evaluate(np.where(eligible, threshold, 0.))
            m._set_dispatch(trial, trial['maximum_dispatch_scale'], final=True)
            tag = { -1e-6: 'below', 0.: 'at', 1e-6: 'above'}[offset]
            for name, value in capture(trial).items(): fields[key + '__probe_' + tag + '_' + name] = value
            fields[key + '__probe_' + tag + '_eligible'] = eligible
            good = eligible & trial['feasible']
            coarse_miss = good & (old['total'] == 0); fine_miss = good & (fine['total'] == 0)
            probe_rows.append(dict(offset=offset, tag=tag, eligible_sites=int(eligible.sum()), feasible_sites=int(good.sum()),
                coarse_zero_but_probe_feasible=int(coarse_miss.sum()), fine_zero_but_probe_feasible=int(fine_miss.sum()),
                coarse_missed_indices=np.flatnonzero(coarse_miss).tolist(), fine_missed_indices=np.flatnonzero(fine_miss).tolist()))
        delta = fine['total'] - old['total']
        rows.append(dict(key=key, climate=mode, hours_worker_year=hours, old_town_people=float(old['total'].sum()),
            fine_town_people=float(fine['total'].sum()), town_people_difference=float(delta.sum()),
            maximum_absolute_site_change=float(np.abs(delta).max()), sites_changed_over_one_person=int((np.abs(delta) > 1.).sum()),
            old_sources=int(old['active'].sum()), fine_sources=int(fine['active'].sum()),
            source_switches=int((old['active'] != fine['active']).sum()), source_gate=gate, overlap_arrays_exact=3 * 33,
            probes=probe_rows, no_global_optimality_or_adoption=True))
        print(key, 'fine delta', round(float(delta.sum()), 6), 'people;source switches', rows[-1]['source_switches'],
            'threshold missed sources', probe_rows[1]['fine_zero_but_probe_feasible'], flush=True)
    for path, digest in {**sources, **preserved}.items():
        if sha(ROOT / path) != digest: raise ValueError('Changed original input/map during search check: ' + path)
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', **fields)
    write(out / 'results.json', dict(status='finer_search_and_staff_transition_development_check', adopt=False,
        sources=sources, unchanged_maps_sha256=preserved, fields_sha256=sha(out / 'fields.npz'), rows=rows,
        original_sixteen_cases_and_maps_changed=False,
        limits='Finite-grid and known threshold diagnostics;not a global optimum,Earthskill,calibrated population or geographic patrol qualification.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
