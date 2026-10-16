"""User-run warm-up sensitivity check of the frozen local shortlist.

No parameter search. Default prints the plan without writing files. --run checks
world 1 with one and two full warm-up years, reusing its saved default-warm-up
result for context. Only the final year is scored; all seasonal solves must
converge. These checks assess sensitivity to initialization, not grid accuracy.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.config import Params
from scripts.mediterranean_pilot import matching_params
from scripts.tune_mediterranean import checked_summary, load_cached
from scripts.validate_mediterranean import model_code_id

PROFILE = ROOT / 'calibration/round20_retrograde_local_shortlist.json'


def diagnostic_code_id():
    h = hashlib.sha256(model_code_id().encode())
    for path in (Path(__file__), ROOT / 'scripts/diagnose_numerics.py'):
        h.update(path.read_bytes())
    return h.hexdigest()


def changes(before, after):
    """Continuous fields alongside labels, to expose threshold amplification."""
    for key in ('target', 'valid', 'elev'):
        if not np.array_equal(before[key], after[key]):
            raise ValueError('Warm-up comparisons require identical geography')
    a, b = json.loads(str(before['params_json'])), json.loads(str(after['params_json']))
    if not matching_params(a, Params(**b)):
        raise ValueError('Warm-up comparisons require identical physical and numerical parameters')
    valid = before['valid'] & (before['target'] > 0)
    def stats(values):
        return dict(median=float(np.median(values)), p95=float(np.percentile(values, 95)),
                    maximum=float(np.max(values)))
    def region(mask):
        fields = {}
        for key in ('MAT', 'Tcold', 'Thot', 'MAP', 'Pwin', 'Psum', 'Psdry', 'Pwwet'):
            delta = after['index_' + key][mask] - before['index_' + key][mask]
            fields[key] = dict(signed_median=float(np.median(delta)), absolute_change=stats(np.abs(delta)))
        aw = before['index_Pwin'][mask] / np.maximum(before['index_MAP'][mask], 1e-9)
        bw = after['index_Pwin'][mask] / np.maximum(after['index_MAP'][mask], 1e-9)
        return dict(cells=int(mask.sum()), fields=fields,
                    winter_70_percent_crossing_share=float(((aw >= .7) != (bw >= .7)).mean()),
                    koppen_changed_share=float((before['koppen'][mask] != after['koppen'][mask]).mean()))
    return dict(painted=region(valid), zones={key:region(valid & (before['target'] == cid))
                for cid, key in ((2, 'cold_dry'), (4, 'med'), (7, 'hot_dry'))})


def monthly_changes(before, after, year_days):
    for key in ('target', 'valid', 'summer'):
        if not np.array_equal(before[key], after[key]):
            raise ValueError('Monthly warm-up comparisons require identical geography and calendar')
    a, b = json.loads(str(before['params_json'])), json.loads(str(after['params_json']))
    if not matching_params(a, Params(**b)):
        raise ValueError('Monthly warm-up comparisons require identical parameters')
    valid = before['valid'] & (before['target'] > 0)
    def region(mask):
        def describe(key, scale):
            delta = scale * (after[key][:, mask] - before[key][:, mask])
            return dict(absolute_p95=float(np.percentile(np.abs(delta), 95)),
                        absolute_maximum=float(np.abs(delta).max()))
        return dict(temperature_c=describe('monthly_temperature_c', 1.),
                    precipitation_mm_month=describe('monthly_rain_mm_day', year_days / 12.))
    return dict(painted=region(valid), zones={key:region(valid & (before['target'] == cid))
                for cid, key in ((2, 'cold_dry'), (4, 'med'), (7, 'hot_dry'))})


def run_case(p, years, out, model_id, diagnostic_id):
    name = f'warmup{years}y_seed{p.beyond_seed}'
    path, fields = out / f'{name}.json', out / f'{name}_fields.npz'
    transport = out / f'{name}_transport.npz'
    spinup = years * p.steps_per_year
    d = load_cached(path, fields, p, model_id)
    reusable = (d is not None and transport.exists() and
                d.get('spinup_diagnostic_code_id') == diagnostic_id and
                d.get('run_settings', {}).get('spinup_steps_requested') == spinup and
                d['run_settings'].get('spinup_steps_observed') == spinup)
    if reusable:
        with np.load(transport, allow_pickle=False) as saved:
            reusable = matching_params(json.loads(str(saved['params_json'])), p)
    if not reusable:
        from scripts.diagnose_numerics import diagnose
        started = time.monotonic()
        def progress(done, total):
            if done == 1 or done % 5 == 0 or done == total:
                print(f'{name}: {done}/{total} seasonal steps; '
                      f'{(time.monotonic()-started)/60:.1f} min', flush=True)
        try:
            d = diagnose(p, snapshot=fields, transport_snapshot=transport, progress=progress, spinup=spinup)
        except RuntimeError as error:
            (out / f'{name}_failure.json').write_text(json.dumps(dict(params=asdict(p),
                spinup_steps_requested=spinup, error=str(error), details=getattr(error, 'details', None),
                validation_code_id=model_id, spinup_diagnostic_code_id=diagnostic_id), indent=2) + '\n')
            raise
        d.update(validation_code_id=model_id, spinup_diagnostic_code_id=diagnostic_id)
        path.write_text(json.dumps(d, indent=2) + '\n')
    row = checked_summary(d)
    print(f"{name}: Mediterranean dry {row['mediterranean']['dry_share']:.2%}, "
          f"cold-dry {row['zone_recall']['cold_dry']:.2%}, "
          f"hot-dry {row['zone_recall']['hot_dry']:.2%}", flush=True)
    return row, fields, transport


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/mediterranean_spinup')
    a = ap.parse_args()
    p = Params.from_json(PROFILE)
    if p.beyond_seed != 1 or p.steps_per_year != 25:
        ap.error('This bounded check is prepared for the frozen world 1 profile at 25 steps/year.')
    if not all((p.t_require_convergence, p.moisture_require_convergence, p.solver_require_convergence)):
        ap.error('Shortlist must retain all strict convergence requirements.')
    model_id, diagnostic_id = model_code_id(), diagnostic_code_id()
    baseline = ROOT / 'output/mediterranean_tuning/slightly_narrower_seed1.json'
    baseline_fields = baseline.with_name(baseline.stem + '_fields.npz')
    detail = load_cached(baseline, baseline_fields, p, model_id)
    if detail is None:
        ap.error('The saved shortlist baseline is missing or stale; do not silently rerun or substitute it.')
    row = checked_summary(detail)
    observed = len(detail['temperature_convergence']['converged']) - p.steps_per_year
    if observed != 8:
        ap.error('Expected the verified eight-step warm-up baseline.')
    print('World 1, unchanged local shortlist: saved 8-step warm-up; '
          'new 25-step and 50-step warm-ups. Only the final 25-step year is scored.\n'
          'Two sequential simulations (50 and 75 steps total), about 30–40 minutes '
          'at recent speeds; difficult steps may add time. No search or atlas update.', flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.')
        return
    a.out.mkdir(parents=True, exist_ok=True)
    rows = {'default': row}
    snapshots = {'default': baseline_fields}
    archives = {}
    for years in (1, 2):
        key = f'warmup{years}y'
        rows[key], snapshots[key], archives[key] = run_case(p, years, a.out, model_id, diagnostic_id)
        comparisons = {}
        for before, after in (('default', 'warmup1y'), ('default', 'warmup2y'), ('warmup1y', 'warmup2y')):
            if after not in snapshots:
                continue
            with np.load(snapshots[before], allow_pickle=False) as b, np.load(snapshots[after], allow_pickle=False) as c:
                comparisons[f'{before}_to_{after}'] = changes(b, c)
        if years == 2:
            with np.load(archives['warmup1y'], allow_pickle=False) as b, np.load(archives['warmup2y'], allow_pickle=False) as c:
                comparisons['monthly_1y_to_2y'] = monthly_changes(b, c, p.year_days)
        report = dict(validation_code_id=model_id, spinup_diagnostic_code_id=diagnostic_id,
                      completed=len(archives), expected=2, cases=rows, changes=comparisons,
                      note='Warm-up sensitivity on one development world, not an independent accuracy verdict. '
                           'Compare continuous monthly/seasonal rain and temperature as well as threshold-sensitive labels. '
                           'No automatic acceptance, extra simulation, search or atlas update.')
        (a.out / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
