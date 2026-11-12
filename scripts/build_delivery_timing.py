"""Matched destination inventory audit: old bins, continuous starts, job returns."""
import argparse
from dataclasses import asdict, fields as dataclass_fields
import gzip
import io
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.event_food_stocks import EventFoodYear, periodic_event_food_year
from harvest.food_stocks import periodic_food_year
from polity.delivery_events import trip_delivery_events
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_delivery_timing_20261112'
PLAN = ROOT / 'calibration/network_visit_delivery_timing_20261112/plan.json'
YEAR = ROOT / 'output/network_visit_year_complete_20261112'
BASE = ROOT / 'output/network_visit_calendar_20261112'
JOINT = ROOT / 'output/network_visit_joint_order_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'
NAMES = [f.name for f in dataclass_fields(EventFoodYear)]
LABELS = dict(A='Original twelve-bin meals before capacity', B='Continuous meals; arrival-bin-start pulses', C='Continuous meals; selected collector return phases')


def aggregate(site, time, cargo):
    order = np.lexsort((time, site)); site, time, cargo = site[order], time[order], cargo[order]
    starts = np.r_[0, 1 + np.flatnonzero((np.diff(site) != 0) | (np.diff(time) != 0))]
    if not len(site): return dict(site=np.array([], 'i4'), time=np.array([]), cargo=np.array([]), trips=np.array([], 'i8'))
    return dict(site=site[starts].astype('i4'), time=time[starts], cargo=np.add.reduceat(cargo, starts), trips=np.diff(np.r_[starts, len(site)]))


def main(out=OUT):
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes(), 'Commit declaration first'
    controls = subprocess.run([str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', 'tests/test_event_food_stocks.py'], cwd=ROOT, capture_output=True, text=True)
    assert controls.returncode == 0, controls.stdout + controls.stderr
    parent = json.loads((YEAR / 'results.json').read_text()); reviewed = json.loads((YEAR / 'review.json').read_text())
    assert reviewed['status'] == 'passed' and reviewed['results_sha256'] == sha(YEAR / 'results.json')
    assert reviewed['reviewer_sha256'] == sha(ROOT / 'scripts/review_provider_year_visits.py')
    sources = {**parent['sources'], **parent['producers'], **parent['unchanged_schedule_sha256']}
    for p in [YEAR / 'results.json', YEAR / 'review.json', YEAR / 'fields.npz']: sources[str(p.relative_to(ROOT))] = sha(p)
    maps = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'atlases/earth_fit').rglob('*') if p.is_file()}
    for path, digest in sources.items(): assert sha(ROOT / path) == digest, path
    y = np.load(YEAR / 'fields.npz'); arrays = {}; rows = []; event_hashes = {}; provider_rows = []
    out.mkdir(parents=True, exist_ok=True)
    for case in parent['rows']:
        key, mode, pk = (case[k] for k in ('key', 'climate', 'parent_key'))
        x = dict(np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz')); f = dict(np.load(SEEDED / pk / 'fields.npz'))
        scored = y[key + '__mandatory_complete']; policy = y[key + '__policy']; n = len(scored); ids = np.flatnonzero(scored)
        pieces = []
        for month in range(12):
            selected = []
            for pol, p in [(0, BASE / pk / f'collection_{month:02d}.npz'), (1, JOINT / key / f'calendar_{month:02d}.npz')]:
                c = np.load(p); site = c['collection_site']; mask = scored[site] & (policy[site] == pol)
                selected.append({name: c['collection_' + name][mask] for name in ['origin', 'serial', 'site', 'end']})
            c = {name: np.concatenate([p[name] for p in selected]) for name in selected[0]}
            time, cargo = trip_delivery_events(f['origin_departures'][month], f['origin_trips'][month].astype('i8'), x['owner'], scored,
                c['origin'], c['serial'], c['site'], c['end'], month)
            arrival_bin = np.floor(time * 12 / 365).astype(int)
            assert (arrival_bin == (month+1) % 12).all(), 'Return clock crossed original lagged bin'
            np.testing.assert_allclose(np.bincount(c['site'], weights=cargo, minlength=n), np.where(scored, f['arrivals'][(month+1)%12], 0), rtol=1e-12, atol=1e-6)
            pieces.append((c['site'], time, cargo))
        events = aggregate(*(np.concatenate([p[i] for p in pieces]) for i in range(3)))
        event_file = out / f'{key}_events.npz'; np.savez_compressed(event_file, **events); event_hashes[event_file.name] = sha(event_file)
        offsets = np.searchsorted(events['site'], np.arange(n+1))
        rate = f['total'] * 2500; cap = rate * 90
        old = periodic_food_year(f['arrivals'], np.broadcast_to(rate*365/12, (12,n)), cap, loss_fraction_year=.05, step_days=365/12)
        for name in NAMES:
            field = 'town_' + name
            if field in f: np.testing.assert_allclose(getattr(old, name)[scored], f[field][scored], rtol=1e-12, atol=1e-6)
        arrays[key + '__scored'] = scored; arrays[key + '__policy'] = policy; arrays[key + '__actor'] = x['actor']
        arrays[key + '__residents'] = f['total']; arrays[key + '__capacity'] = cap
        arrays[key + '__arrivals'] = f['arrivals']
        results = {account: {name: np.zeros(n) for name in NAMES} for account in LABELS}
        for name in NAMES: results['A'][name][scored] = getattr(old, name)[scored]
        for site in ids:
            b = periodic_event_food_year(np.arange(12)*365/12, f['arrivals'][:, site], demand_rate=rate[site], capacity=cap[site])
            sl = slice(offsets[site], offsets[site+1]); c = periodic_event_food_year(events['time'][sl], events['cargo'][sl], demand_rate=rate[site], capacity=cap[site])
            for account, result in [('B', b), ('C', c)]:
                for name, value in asdict(result).items(): results[account][name][site] = value
        for account, values in results.items():
            no_shortage = scored & (values['unmet'] <= 1e-8 * np.maximum(1., values['needed']))
            for name, values_by_site in values.items(): arrays[f'{key}__{account}__{name}'] = values_by_site
            arrays[f'{key}__{account}__no_shortage'] = no_shortage
            summary = dict(key=key, climate=mode, hours_worker_year=case['hours_worker_year'], crew=case['crew'], accounting=account, label=LABELS[account], scored_providers=len(ids), unscored_providers=n-len(ids), no_shortage_providers=int(no_shortage.sum()),
                **{name: float(values[name][scored].sum()) for name in NAMES if name not in ['periodic_residual','ledger_residual','shortfall_days']},
                provider_shortfall_days=float(values['shortfall_days'][scored].sum()), max_shortfall_days=float(values['shortfall_days'][scored].max(initial=0)),
                max_abs_ledger_residual=float(np.abs(values['ledger_residual'][scored]).max(initial=0)), max_abs_periodic_residual=float(np.abs(values['periodic_residual'][scored]).max(initial=0)), actors=[])
            for actor in range(18):
                mask = scored & (x['actor'] == actor)
                summary['actors'].append(dict(actor_index=actor, scored_providers=int(mask.sum()), no_shortage_providers=int((mask & no_shortage).sum()),
                    **{name: float(values[name][mask].sum()) for name in NAMES}))
            rows.append(summary)
            for site in ids:
                provider_rows.append(dict(case=key, accounting=account, provider=int(site), actor=int(x['actor'][site]), residents=float(f['total'][site]), year_policy=int(policy[site]), no_shortage=bool(no_shortage[site]), **{name:float(values[name][site]) for name in NAMES}))
            print(key, account, 'no-shortage', summary['no_shortage_providers'], '/', len(ids), 'unmet', summary['unmet'], flush=True)
    np.savez_compressed(out / 'fields.npz', **arrays)
    buffer = io.StringIO(newline=''); writer = csv.DictWriter(buffer, fieldnames=list(provider_rows[0])); writer.writeheader(); writer.writerows(provider_rows)
    (out / 'providers.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))
    producers = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'harvest/event_food_stocks.py', ROOT / 'polity/delivery_events.py', ROOT / 'tests/test_event_food_stocks.py', PLAN]}
    for path, digest in {**sources, **maps}.items(): assert sha(ROOT / path) == digest, path
    write(out / 'controls.json', dict(status='passed_before_production', command='pytest -q tests/test_event_food_stocks.py', output=controls.stdout, producers=producers))
    write(out / 'results.json', dict(status='destination_only_delivery_timing_audit', adopt=False, rows=rows, sources=sources, producers=producers,
        files_sha256={**event_hashes, 'fields.npz':sha(out / 'fields.npz'), 'providers.csv.gz':sha(out / 'providers.csv.gz')}, unchanged_atlas_sha256=maps,
        scope='Destination cereal inventory only. A-to-B changes inventory convention; B-to-C isolates return phases. Same original one-bin lag and retention once. Source-bin food assumptions and crew ration/location limits remain open. No map or default change.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT); main(parser.parse_args().out)
