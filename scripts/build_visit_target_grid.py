"""Apply the unchanged assign-once visit rule to all five declared target grids."""
import argparse
from dataclasses import fields as dataclass_fields
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from prepare_visit_target_grid import OUT, PLAN, PARENT, INPUTS
from polity.network_visits import VisitAllocation, allocate_reserved_visits

SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def main(out=OUT, prepared=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes(): raise ValueError('Commit target-grid declaration first')
    designs = json.loads(PLAN.read_text())['designs']; parent = json.loads((PARENT / 'results.json').read_text())
    checked = json.loads((PARENT / 'review.json').read_text())
    assert checked['status'] == 'passed' and checked['results_sha256'] == sha(PARENT / 'results.json')
    assert checked['reviewer_sha256'] == sha(ROOT / 'scripts/review_network_duty_visits.py')
    for path, digest in {**parent['sources'], **parent['producers'], **parent['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    sources = {}; producers = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'polity/network_visits.py', PLAN)}
    # Canonical relative identities stay the same during fresh replay; prepared
    # packets must match them byte for byte before being consumed.
    for mode in ('raw', 'corrected'):
        receipt = json.loads((prepared / f'{mode}_paths.json').read_text())
        for path, digest in receipt['sources'].items(): assert sha(ROOT / path) == digest, path
        assert (prepared / f'{mode}_paths.json').read_bytes() == (OUT / f'{mode}_paths.json').read_bytes()
        sources[str((OUT / f'{mode}_paths.json').relative_to(ROOT))] = sha(OUT / f'{mode}_paths.json')
        for name, digest in receipt['files_sha256'].items():
            assert sha(prepared / name) == sha(OUT / name) == digest
            sources[str((OUT / name).relative_to(ROOT))] = digest
    for p in (PARENT / 'results.json', PARENT / 'review.json', PARENT / 'fields.npz'):
        sources[str(p.relative_to(ROOT))] = sha(p)
    protected = dict(parent['unchanged_map_sha256'])
    protected['atlases/earth_fit/data/network_duty_visits.json'] = sha(ROOT / 'atlases/earth_fit/data/network_duty_visits.json')
    for p in (ROOT / 'atlases/earth_fit/data/network_visits').rglob('*'):
        if p.is_file(): protected[str(p.relative_to(ROOT))] = sha(p)
    old = dict(np.load(PARENT / 'fields.npz')); rows = []; field_hashes = {}; target_ids = {}
    out.mkdir(parents=True, exist_ok=True)
    for design in designs:
        ident = design['id']; arrays = {}
        for mode in ('raw', 'corrected'):
            x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); t = dict(np.load(prepared / mode / ident / 'targets.npz'))
            target_ids[(mode, ident)] = t['target_nodes']; demand = t['target_reference_masks'] > 0; arrays[mode + '__demand'] = demand
            sources[str((INPUTS / f'{mode}_inputs.npz').relative_to(ROOT))] = sha(INPUTS / f'{mode}_inputs.npz')
            pairs = []
            for month in range(12):
                p = dict(np.load(prepared / mode / ident / f'paths_{month:02d}.npz'))
                provider = np.repeat(p['keys'][:, 1], np.diff(p['offsets'])).astype('i8')
                pairs.append((provider, p['target_index'].astype('i8'), 7 * (p['outward_days'] + p['inward_days']) + 1))
            for previous in (r for r in parent['rows'] if r['climate'] == mode):
                key = previous['key']; folder = SEEDED / previous['parent_key']; physical_result = json.loads((folder / 'results.json').read_text())
                for path, digest in {**physical_result['sources'], **physical_result['producers']}.items(): assert sha(ROOT / path) == digest, path
                f = dict(np.load(folder / 'fields.npz')); assert sha(folder / 'fields.npz') == physical_result['fields_sha256']
                sources[str((folder / 'fields.npz').relative_to(ROOT))] = sha(folder / 'fields.npz')
                bins = []; zero_controls = []
                for month, (provider, target, cost) in enumerate(pairs):
                    kwargs = dict(provider_actor=x['actor'], supported_staff=f['staff'], active=f['active'], demand=demand, crew=previous['crew'])
                    visit = allocate_reserved_visits(provider, target, cost, reserved_hours=f['work_secondary_hours'][0, month], **kwargs)
                    zero = allocate_reserved_visits(provider, target, cost, reserved_hours=np.zeros(len(x['nodes'])), **kwargs)
                    assert not zero.served.any() and not zero.used_hours.any() and np.array_equal(zero.route_unreachable, visit.route_unreachable)
                    bins.append(visit); zero_controls.append(zero.provider_work_unavailable)
                for field in dataclass_fields(VisitAllocation): arrays[key + '__' + field.name] = np.stack([getattr(v, field.name) for v in bins])
                arrays[key + '__reserved_hours'] = f['work_secondary_hours'][0].copy()
                arrays[key + '__zero_budget_work_unavailable'] = np.stack(zero_controls)
                used = arrays[key + '__used_hours']; nonpatrol = f['work_fundable_collection_hours'] + f['work_secondary_hours'][1:].sum(axis=0)
                total_used = nonpatrol + used; full_unused = f['work_gross_hours'] - total_used
                assert np.all(full_unused >= -1e-8)
                np.testing.assert_allclose(full_unused, f['work_unused_hours'] + arrays[key + '__unused_hours'], rtol=1e-11, atol=1e-7)
                arrays[key + '__whole_provider_unused_hours'] = full_unused
                served = arrays[key + '__served']; requested = int(demand.sum() * 12); actors = []
                for actor in range(len(demand)):
                    actor_row = dict(actor_index=actor, inventory_present=bool((x['actor'] == actor).any()), requested_visits=int(demand[actor].sum() * 12), completed_visits=int(served[:, actor].sum()))
                    for name in ('route_unreachable', 'provider_work_unavailable', 'capacity_unmet'): actor_row[name] = int(arrays[key + '__' + name][:, actor].sum())
                    actors.append(actor_row)
                row = dict(design=ident, **design, key=key, climate=mode, hours_worker_year=previous['hours_worker_year'], crew=previous['crew'],
                    target_points=len(t['target_nodes']), actual_spacing_km=float(x['cell_km'] * design['block_cells']),
                    represented_land_km2=float(t['target_area_km2'].sum()), requested_visits=requested, completed_visits=int(served.sum()),
                    completed_fraction=float(served.sum() / requested) if requested else None,
                    requested_tasks_per_1000_land_km2=float(requested / t['target_area_km2'].sum() * 1000),
                    completed_by_bin=served.sum(axis=(1, 2)).astype(int).tolist(), reserved_patrol_hours=float(arrays[key + '__reserved_hours'].sum()),
                    visit_hours_used=float(used.sum()), unused_patrol_hours=float(arrays[key + '__unused_hours'].sum()), actors=actors, zero_budget_visits=0)
                for name in ('route_unreachable', 'provider_work_unavailable', 'capacity_unmet'): row[name] = int(arrays[key + '__' + name].sum())
                rows.append(row); print(ident, key, row['completed_visits'], '/', requested, 'whole point tasks', flush=True)
        np.testing.assert_array_equal(target_ids['raw', ident], target_ids['corrected', ident])
        if ident == 'b3_p0':
            assert set(arrays) == set(old)
            for name in arrays: np.testing.assert_array_equal(arrays[name], old[name])
        target = out / (ident + '_fields.npz'); np.savez_compressed(target, **arrays); field_hashes[target.name] = sha(target)
    assert len(rows) == 40
    for path, digest in {**sources, **producers, **protected}.items(): assert sha(ROOT / path) == digest, path
    write(out / 'results.json', dict(status='forty_declared_target_grid_scenarios', adopt=False, rows=rows, fields_sha256=field_hashes,
        sources=sources, producers=producers, unchanged_map_sha256=protected, all_original_baseline_fields_exact=True,
        limits='Spacing changes supplied task density;phase changes point geography. Neither is empirical demand or a numerical-convergence/global-optimum/territorial-authority qualification.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT); parser.add_argument('--prepared', type=Path, default=OUT)
    args = parser.parse_args(); main(args.out, args.prepared)
