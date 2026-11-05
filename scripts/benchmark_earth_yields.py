"""Fetch, prepare, select and evaluate the preregistered historical crop test."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONFIG = ROOT / 'calibration/low_input_yields_20261105'
PRODUCERS = ['harvest/earth_yields.py', 'harvest/crop_sequences.py', 'scripts/land_people.py', 'scripts/benchmark_earth_yields.py']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def committed(path):
    result = subprocess.run(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT, capture_output=True)
    if result.returncode or result.stdout != path.read_bytes(): raise ValueError('Commit exact protocol/producer/selection first: ' + str(path))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    from harvest.earth_yields import prepare, select, metrics, primary, assert_temporal_integrity
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', required=True, choices=['fetch', 'prepare', 'select', 'evaluate'])
    ap.add_argument('--cache', type=Path, default=ROOT / 'data/cache/era_low_input_20261105')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/low_input_yields_20261105')
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    for name in ['plan.json', 'sources.json', 'amendment.json']: committed(CONFIG / name)
    plan = json.loads((CONFIG / 'plan.json').read_text()); source = json.loads((CONFIG / 'sources.json').read_text())
    if args.stage == 'fetch':
        args.cache.mkdir(parents=True, exist_ok=True)
        for item in source['files']:
            path = args.cache / item['cache_file']
            if not path.exists():
                data = urlopen(item['url'], timeout=90).read()
                if hashlib.sha256(data).hexdigest() != item['sha256']: raise ValueError('Changed provider file: ' + item['id'])
                path.write_bytes(data)
            if sha(path) != item['sha256']: raise ValueError('Cached file changed: ' + item['id'])
            print(item['id'], 'checksum verified')
        return
    identity = dict(plan_sha256=sha(CONFIG / 'plan.json'), amendment_sha256=sha(CONFIG / 'amendment.json'), sources_manifest_sha256=sha(CONFIG / 'sources.json'),
        producers_sha256={p: sha(ROOT / p) for p in PRODUCERS},
        inputs_sha256={s['cache_file']: sha(args.cache / s['cache_file']) for s in source['files']})
    if any(identity['inputs_sha256'][s['cache_file']] != s['sha256'] for s in source['files']): raise ValueError('Source checksum changed')
    cached = args.cache / 'prepared_wheat.json'; selection = args.out / 'selection.json'
    if args.stage == 'prepare':
        cases, excluded = prepare(args.cache, plan)
        write(cached, dict(identity=identity, cases=cases))
        counts = {split: dict(primary_years=len(primary(cases, split)), strata=dict(Counter(c['stratum'] for c in cases if c['split'] == split))) for split in ['training', 'evaluation']}
        write(args.out / 'preparation.json', dict(identity=identity, counts=counts, excluded=excluded, prepared_sha256=sha(cached), evaluation_targets_scored=False, woburn_targets_opened=False))
        print(json.dumps(counts, indent=2)); return
    data = json.loads(cached.read_text())
    if data['identity'] != identity: raise ValueError('Producer/data identity changed; rerun preparation')
    cases = data['cases']; assert_temporal_integrity(cases, plan)
    if args.stage == 'select':
        chosen = select(cases, plan)
        write(selection, dict(identity=identity, prepared_sha256=sha(cached), **chosen))
        print(json.dumps(chosen, indent=2)); return
    committed(selection)
    for p in PRODUCERS: committed(ROOT / p)
    chosen = json.loads(selection.read_text())
    if chosen['identity'] != identity or chosen['prepared_sha256'] != sha(cached): raise ValueError('Frozen selection differs')
    evaluation = primary(cases, 'evaluation')
    base = metrics(evaluation, 1., chosen['training_mean_t_ha']); candidate = metrics(evaluation, chosen['scale'], chosen['training_mean_t_ha'])
    conditions = dict(enough_years=len(evaluation) >= plan['eligibility']['minimum_evaluation_years'],
        log_error_gain=candidate.get('MAE_log10', 1e10) <= .95 * base.get('MAE_log10', 0),
        positive_rmse_skill=(candidate.get('RMSE_skill_vs_training_mean') or 0) > 0,
        positive_correlation=(candidate.get('Pearson_r') or 0) > 0)
    strata = {s: dict(baseline=metrics([c for c in cases if c['split'] == 'evaluation' and c['stratum'] == s], 1., chosen['training_mean_t_ha']), candidate=metrics([c for c in cases if c['split'] == 'evaluation' and c['stratum'] == s], chosen['scale'], chosen['training_mean_t_ha'])) for s in plan['diagnostics']['strata']}
    calendars = [r['calendar'] for c in evaluation for r in c['source_records']]
    result = dict(status='evaluated_single_site_temporal_test', identity=identity, selection_sha256=sha(selection),
        baseline=base, candidate=candidate, qualification_conditions=conditions, temporal_comparator_qualified=all(conditions.values()),
        evaluation_strata=strata, calendar=dict(records=len(calendars), available=sum(r['available'] for r in calendars),
            representable=sum(r.get('representable', False) for r in calendars), failures=dict(Counter(f for r in calendars for f in r.get('failures', []))),
            outside_fixed_crop_year=sum(r.get('outside_fixed_crop_year', False) for r in calendars)),
        evaluation_targets_scored=True, evaluation_pool_now_spent=True, woburn_targets_opened=False,
        ancient_default_adoption=False, production_atlas_changed=False,
        scope='Temporal transfer at one continuously cropped English wheat trial, not independent sites, barley or global AD200 farming. Scale changes mean level only; calendar/water/nutrients are not fitted.')
    complete = [c for c in evaluation if c['temperature_missing_days'] == 0]
    result['complete_temperature_subset'] = dict(baseline=metrics(complete, 1., chosen['training_mean_t_ha']), candidate=metrics(complete, chosen['scale'], chosen['training_mean_t_ha']), refitted=False)
    write(args.out / 'evaluation.json', result)
    # Small public packet supports independent score replay without a raw cache.
    with gzip.GzipFile(filename=str(args.out / 'cases.json.gz'), mode='wb', mtime=0) as f:
        f.write((json.dumps(dict(identity=identity, cases=cases), ensure_ascii=False, allow_nan=False) + '\n').encode())
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
