"""User-run transport diagnosis of the current fit and Mediterranean probes.

Default prints a plan. --run enables two simulations, with no parameter search
or atlas overwrite. Completed exact matching diagnostic runs can be resumed.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.config import Params
from scripts.mediterranean_pilot import convergence_summary, matching_params


def case_summary(detail):
    med = detail['zones']['med']['koppen_share']
    return dict(params=detail['params'], accuracy=detail['accuracy'],
                zone_recall={key: value['correct'] for key, value in detail['zones'].items()},
                mediterranean=dict(dry_share=sum(v for k,v in med.items() if k.startswith('B')),
                                   cs_share=sum(v for k,v in med.items() if k.startswith('Cs'))),
                convergence=convergence_summary(detail),
                moisture_transport=detail['moisture_transport'])


def completed_comparisons(out, options):
    """Keep matching completed cases when the other case is run separately."""
    rows = {}
    for name, p in options.items():
        path = out / f'{name}.json'
        if not all(f.exists() for f in (path, out / f'{name}_fields.npz', out / f'{name}_transport.npz')):
            continue
        detail = json.loads(path.read_text())
        if matching_params(detail['params'], p) and detail.get('moisture_transport') is not None:
            rows[name] = case_summary(detail)
    return rows


def case_options(converged):
    options = dict(current=Params.from_json(ROOT / 'calibration/round20_retrograde_mediterranean.json'),
                   focused=Params.from_json(ROOT / 'calibration/round20_retrograde_focused.json'))
    if converged:
        options = {name: p.replace(picard_iters=256, moisture_relaxation=0.25,
                    moisture_residual_tol=0.01, moisture_require_convergence=True,
                    solver_rtol=1e-7) for name, p in options.items()}
    options['seasonal'] = options['current'].replace(eddy_seasonality=0.4)
    # A one-factor circulation test relative to the successful seasonal case.
    options['poleward'] = options['seasonal'].replace(hadley_edge=options['seasonal'].hadley_edge + 4.)
    options['strong_seasonal'] = options['seasonal'].replace(eddy_seasonality=0.7)
    # Complete the interaction check between the measured winter-rain benefit
    # of focused storms and the measured cold-dry summer reduction at contrast .7.
    options['focused_seasonal'] = options['focused'].replace(eddy_seasonality=0.7)
    return options


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--converged', action='store_true',
                    help='test moisture-equation stopping with a larger cap; stop immediately on failure')
    ap.add_argument('--cases', default='current,focused')
    a = ap.parse_args()
    options = case_options(a.converged)
    if a.out is None:
        a.out = ROOT / ('output/moisture_converged' if a.converged else 'output/moisture_transport')
    names = a.cases.split(',')
    if len(set(names)) != len(names) or any(n not in options for n in names):
        ap.error('Choose unique cases from: ' + ','.join(options))
    if (set(options)-{'current','focused'}).intersection(names) and not a.converged:
        ap.error('New physical tests require --converged numerics')
    for name in names:
        p = options[name]
        print(f'{name}: storm width {p.storm_width:.3f}, exchange {p.eddy_rate:.3f}/day, '
              f'world {p.beyond_seed}, temperature relaxation {p.t_relaxation}, '
              f'eddy seasonality {p.eddy_seasonality}, '
              f'Hadley edge {p.hadley_edge:.3f}, '
              f'moisture iterations <= {p.picard_iters}, residual tolerance {p.moisture_residual_tol:g}', flush=True)
    if not a.run:
        print(f'Plan only: {len(names)} simulations with transport recording. Add --run to execute.')
        return
    from scripts.diagnose_numerics import diagnose
    a.out.mkdir(parents=True, exist_ok=True)
    rows = completed_comparisons(a.out, options)
    for name in names:
        p = options[name]
        path = a.out / f'{name}.json'
        fields = a.out / f'{name}_fields.npz'
        transport = a.out / f'{name}_transport.npz'
        d = json.loads(path.read_text()) if path.exists() else None
        reusable = (d is not None and fields.exists() and transport.exists()
                    and matching_params(d['params'], p) and d.get('moisture_transport') is not None)
        if not reusable:
            start = time.monotonic()
            def progress(done, total):
                if done == 1 or done % 5 == 0 or done == total:
                    print(f'{name}: {done}/{total} seasonal steps including spin-up; '
                          f'{(time.monotonic()-start)/60:.1f} minutes', flush=True)
            try:
                d = diagnose(p, snapshot=fields, transport_snapshot=transport, progress=progress)
            except RuntimeError as error:
                (a.out / f'{name}_failure.json').write_text(json.dumps(dict(
                    params=asdict(p), error=str(error), seconds=time.monotonic()-start), indent=2)+'\n')
                raise
            path.write_text(json.dumps(d, indent=2) + '\n')
        c = convergence_summary(d)
        rows[name] = case_summary(d)
        (a.out / 'comparison.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(f'{name}: agreement {d["accuracy"]:.1%}, all enabled convergence checks '
              f'{c["usable_for_comparison"]}', flush=True)
        if not c['usable_for_comparison']:
            raise SystemExit('A convergence check failed; results saved for diagnosis.')
        for zone in ('cold_dry', 'med'):
            for season in ('winter', 'summer'):
                r = d['moisture_transport']['zones'][zone][season]
                print(f'  {zone} {season}: mean rain '
                      f'{r["mean_total_mm_per_cell"]["rain"]:.1f} mm; '
                      f'mean absolute moisture-equation residual / rain '
                      f'{r["absolute_residual_over_rain"]:.1%}', flush=True)


if __name__ == '__main__':
    main()
