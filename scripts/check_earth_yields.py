"""Replay historical yield scores directly from the public observation packet.

Metric calculation and finite-grid selection deliberately do not import the
benchmark's metric/selection functions. --raw additionally matches provider rows.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_SNAPSHOT = '67b7aa1ca31e30c3e2488d0f81249863ff5b22ad'


def replay(rows, scale, mean):
    actual = np.array([r['observed_t_ha'] for r in rows]); predicted = np.array([r['baseline_t_ha'] * scale for r in rows])
    errors = abs(np.log10(np.clip(actual, .05, None)) - np.log10(np.clip(predicted, .05, None)))
    rmse = float(np.linalg.norm(actual - predicted) / np.sqrt(len(rows)))
    reference = float(np.linalg.norm(actual - mean) / np.sqrt(len(rows)))
    return dict(n=len(rows), MAE_log10=float(errors.mean()), MAE_t_ha=float(abs(actual-predicted).mean()),
        RMSE_t_ha=rmse, Pearson_r=float(np.corrcoef(actual, predicted)[0, 1]) if np.ptp(predicted) > 1e-12 and np.ptp(actual) > 1e-12 else None,
        RMSE_skill_vs_training_mean=1-rmse/reference if reference else None,
        observed_mean=float(actual.mean()), predicted_mean=float(predicted.mean()),
        fraction_within_factor2=float(np.mean(errors <= math.log10(2))))


def compare(actual, expected):
    assert actual.keys() == expected.keys()
    for k, value in actual.items():
        if value is None: assert expected[k] is None, k
        else: assert math.isclose(value, expected[k], rel_tol=1e-10, abs_tol=1e-12), (k, value, expected[k])


def check(origin, raw=None):
    packet = json.loads(gzip.decompress((origin / 'cases.json.gz').read_bytes()))
    result = json.loads((origin / 'evaluation.json').read_text()); selected = json.loads((origin / 'selection.json').read_text())
    plan_path = ROOT / 'calibration/low_input_yields_20261105/plan.json'; plan = json.loads(plan_path.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert packet['identity'] == result['identity'] == selected['identity']
    assert result['selection_sha256'] == sha(origin / 'selection.json')
    assert result['identity']['plan_sha256'] == sha(plan_path)
    for k, fn in [('amendment_sha256', 'amendment.json'), ('sources_manifest_sha256', 'sources.json')]:
        assert result['identity'][k] == sha(plan_path.parent / fn)
    for name, digest in result['identity']['producers_sha256'].items():
        if sha(ROOT / name) != digest:
            archived = subprocess.check_output(['git', 'show', PRODUCER_SNAPSHOT + ':' + name], cwd=ROOT)
            assert hashlib.sha256(archived).hexdigest() == digest, name
    cases = packet['cases']; primary = [c for c in cases if c['stratum'] == 'unmanured_plot3']
    assert len({(c['year'], c['stratum']) for c in cases}) == len(cases)
    for c in cases:
        a, b = plan['split'][c['split']]; assert a <= c['year'] <= b
        rows = c['source_records']; total = sum(r['area'] for r in rows)
        assert math.isclose(c['observed_t_ha'], sum(r['grain'] * r['area'] for r in rows) / total)
        assert c['crop_year_start'] == [c['year'] - 1, 9] and c['crop_year_end'] == [c['year'], 8]
        assert .0 <= c['baseline_t_ha'] <= 1. + 1e-12
    train = [c for c in primary if c['split'] == 'training']; test = [c for c in primary if c['split'] == 'evaluation']
    mean = np.mean([r['observed_t_ha'] for r in train]); assert math.isclose(mean, selected['training_mean_t_ha'])
    assert [c['case_id'] for c in train] == selected['training_case_ids']
    g = plan['model']['scale_grid']; scales = np.geomspace(g['minimum'], g['maximum'], g['count'])
    optimum = min(scales, key=lambda s: (replay(train, s, mean)['MAE_log10'], abs(math.log(s)), s))
    assert math.isclose(optimum, selected['scale'], abs_tol=1e-12)
    compare(replay(train, 1, mean), selected['baseline']); compare(replay(train, optimum, mean), selected['candidate'])
    compare(replay(test, 1, mean), result['baseline']); compare(replay(test, optimum, mean), result['candidate'])
    b, c = result['baseline'], result['candidate']
    conditions = dict(enough_years=len(test) >= plan['eligibility']['minimum_evaluation_years'],
        log_error_gain=c['MAE_log10'] <= .95 * b['MAE_log10'],
        positive_rmse_skill=(c['RMSE_skill_vs_training_mean'] or 0) > 0,
        positive_correlation=(c['Pearson_r'] or 0) > 0)
    assert result['qualification_conditions'] == conditions
    assert result['temporal_comparator_qualified'] == all(conditions.values())
    for name, scores in result['evaluation_strata'].items():
        rows = [c for c in cases if c['split'] == 'evaluation' and c['stratum'] == name]
        compare(replay(rows, 1, mean), scores['baseline']); compare(replay(rows, optimum, mean), scores['candidate'])
    complete = [c for c in test if c['temperature_missing_days'] == 0]
    compare(replay(complete, 1, mean), result['complete_temperature_subset']['baseline'])
    compare(replay(complete, optimum, mean), result['complete_temperature_subset']['candidate'])
    assert not result['ancient_default_adoption'] and not result['production_atlas_changed'] and not result['woburn_targets_opened']
    if raw:
        with zipfile.ZipFile(raw / 'broadbalk_0.zip') as z:
            source = {(int(r['harvest_year']), r['plot'], '' if r['sub_plot'] == '*' else r['sub_plot']): r for r in csv.DictReader(io.StringIO(z.read('crop_data.csv').decode('utf-8-sig')))}
        for c in cases:
            for r in c['source_records']:
                original = source[c['year'], r['plot'], r['subplot']]
                assert float(original['grain']) == r['grain'] and float(original['area_ha']) == r['area']
                assert original['sow_date'] == r['sow_date'] and original['harvest_date'] == r['harvest_date']
        for name, digest in result['identity']['inputs_sha256'].items(): assert sha(raw / name) == digest
    return dict(status='passed', primary_training_years=len(train), primary_evaluation_years=len(test),
        complete_temperature_evaluation_years=len(complete), all_management_aggregates=len(cases), independent_metric_and_grid_replay=True,
        provider_rows_matched=bool(raw), raw_woburn_yields_opened=False,
        producer_snapshot_commit=PRODUCER_SNAPSHOT,
        scope='Score/selection, unit aggregation, chronology and source-row replay; not independent verification of every importer or physical equation.')


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--origin', type=Path, default=ROOT / 'output/low_input_yields_20261105'); ap.add_argument('--raw', type=Path); a = ap.parse_args()
    result = check(a.origin, a.raw)
    (a.origin / 'replay.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
