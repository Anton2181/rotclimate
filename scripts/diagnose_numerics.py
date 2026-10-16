"""Separate round-19 render drift from fit quality; run explicitly, never on import.

Use --plan to inspect the experiment without simulating anything. Each case is
saved separately so a failed later case does not erase completed diagnostics.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(name, '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rotclimate.config import Params

# All changes are relative to the calibration configuration in the input file.
CASES = {
    'baseline': {},
    'coarse_damped': {'t_iters': 192, 't_relaxation': 0.25},
    'picard3': {'picard_iters': 3},
    'picard6': {'picard_iters': 6},
    'picard12': {'picard_iters': 12},
    'steps73': {'steps_per_year': 73},
    'grid4': {'downsample': 4},
    'grid4_t48': {'downsample': 4, 't_iters': 48},
    'grid4_t96': {'downsample': 4, 't_iters': 96},
    'coarse_fitted': {'transport_scheme': 'exponential', 't_iters': 48},
    'fine_fitted': {'downsample': 4, 'transport_scheme': 'exponential', 't_iters': 48},
    'coarse_tight': {'transport_scheme': 'upwind', 't_iters': 48, 'solver_rtol': 1e-6},
    'fine_tight': {'downsample': 4, 'transport_scheme': 'upwind', 't_iters': 48,
                   'solver_rtol': 1e-6},
    'fine_verified': {'downsample': 4, 'transport_scheme': 'upwind', 't_iters': 48,
                      'solver_rtol': 1e-6, 'solver_max_iter': 2000,
                      'solver_require_convergence': True},
    'render': {'downsample': 4, 'steps_per_year': 73, 'picard_iters': 3},
}


def case_params(base, names, seed):
    return [(name, base.replace(beyond_seed=seed, **CASES[name])) for name in names]


def diagnose(p, snapshot=None, progress=None, transport_snapshot=None, spinup=None, result_snapshot=None):
    import numpy as np
    from rotclimate.geography import TARGET_CLASSES
    from rotclimate.koppen import CODES, classify
    from rotclimate.model import ClimateModel
    from rotclimate.score import evaluate, objective

    started = time.monotonic()
    model = ClimateModel(p)
    def temperature_retry(info):
        print(f"  temperature retry: seasonal step {info['seasonal_step']}, stage {info['stage']}, "
              f"damping {info['relaxation']:g}, cap {info['cap']}, "
              f"previous full update {info['previous_update_c']:.4f} C",flush=True)
    run_options = {} if spinup is None else {'spinup': spinup}
    result = model.run(progress=progress, diagnose_moisture=transport_snapshot is not None,
                       temperature_retry=temperature_retry if progress is not None else None,
                       **run_options)
    if not (np.isfinite(result.T).all() and np.isfinite(result.P).all()):
        raise FloatingPointError('Nonfinite temperature or precipitation; refusing to score this run')
    if result_snapshot is not None:
        # Keep an exact completed simulation for atlas export without rerunning
        # it. Geography is reconstructed from the fingerprinted inputs/Params.
        np.savez_compressed(result_snapshot, params_json=np.array(json.dumps(asdict(p))),
            **{key: getattr(result, key) for key in
               ('days', 'T', 'Tsl', 'P', 'W', 'u', 'v', 'snow', 'E')})
    ev = evaluate(result)
    transport_report = None
    if transport_snapshot is not None:
        from rotclimate.transport import save_transport
        transport_report = save_transport(result, ev, transport_snapshot)
    if snapshot is not None:
        from rotclimate.diagnostics import analyse_rules
        analyse_rules(result, ev, snapshot=snapshot)
    st, ix, g = ev['monthly'], ev['indices'], result.grid
    kop = classify(st['Tm'], st['Pm'], st['summer'])
    valid = g.inmap & g.land
    zones = {}
    for cid, key, _, _ in TARGET_CLASSES:
        mask = valid & (g.target == cid)
        counts = ev['confusion'][cid - 1]
        codes, nums = np.unique(kop[mask], return_counts=True)
        zones[key] = dict(
            cells=int(mask.sum()), coverage=ev['per_class'][key], f1=ev['f1'][key],
            correct=float(counts[cid] / max(counts.sum(), 1)),
            # Order: unmatched, then TARGET_CLASSES (IDs 1..7).
            confusion_counts=counts.tolist(),
            koppen_share={CODES[int(c)]: float(n / mask.sum()) for c, n in zip(codes, nums)},
            quantiles={k: np.percentile(ix[k][mask], [10, 50, 90]).tolist() if mask.any() else []
                       for k in ('MAT', 'Tcold', 'Thot', 'MAP', 'aridity', 'Psdry', 'Pwwet')},
        )
    iterations = model.solver.iterations
    return dict(params=asdict(p), seconds=time.monotonic() - started,
                run_settings=dict(spinup_steps_requested=spinup,
                                  spinup_steps_observed=len(model.t_converged) - len(result.days),
                                  steps_per_year=len(result.days)),
                moisture_transport=transport_report,
                moisture_convergence=dict(enabled=p.moisture_residual_tol > 0,
                    tolerance=p.moisture_residual_tol, iterations=model.moisture_iterations,
                    converged=model.moisture_converged,
                    scaled_residual=model.moisture_scaled_residual,
                    unconverged_steps=sum(c is False for c in model.moisture_converged),
                    note='Maximum local discrete-equation residual / max(rain+abs(evaporation),0.1 mm/day), full interior including spin-up.'),
                score=objective(ev, 'f1r'), coverage=ev['total'], accuracy=ev['accuracy'],
                realism=ev['realism'], zones=zones,
                label_policy_audit=ev['label_policy_audit'],
                confusion_columns=['unmatched'] + [c[1] for c in TARGET_CLASSES],
                quantile_percentiles=[10, 50, 90],
                solver=dict(recorded_solves=len(iterations),
                            max_sweeps=max(iterations, default=None),
                            sweep_limit=p.solver_max_iter,
                            at_configured_cap=sum(n >= p.solver_max_iter for n in iterations),
                            unconverged_solves=sum(not c for c in model.solver.converged),
                            max_final_update=max(model.solver.final_updates, default=None),
                            note='Sweep counts alone do not establish residual convergence; empty with direct solver.'),
                temperature_iteration_cap_hits=sum(any(s['iterations'] >= s['cap'] for s in stages)
                                                  for stages in model.t_stages),
                temperature_convergence=dict(
                    tolerance_c=0.05,
                    note='Final fixed-point update, not a PDE residual. Includes spin-up.',
                    iterations=model.t_iterations,
                    retry_steps=sum(len(stages)>1 for stages in model.t_stages),
                    stages=model.t_stages,
                    converged=model.t_converged,
                    unconverged_steps=sum(not c for c in model.t_converged),
                    final_update_max_c=model.t_update_max,
                    final_update_inmap_max_c=model.t_update_inmap_max))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--params', default='calibration/r19p_earthlike/best_params.json')
    ap.add_argument('--out', default='output/r19_diagnostics')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--cases', default='baseline,picard3,steps73,grid4,render')
    ap.add_argument('--plan', action='store_true', help='print settings only; no simulation')
    ap.add_argument('--save-fields', action='store_true', help='save exact rule fields for offline analysis')
    a = ap.parse_args()
    names = a.cases.split(',')
    if any(n not in CASES for n in names) or len(set(names)) != len(names):
        ap.error('Choose unique cases from: ' + ','.join(CASES))
    base = Params.from_json(a.params)
    cases = case_params(base, names, a.seed)
    for name, p in cases:
        print(f'{name}: downsample={p.downsample}, steps={p.steps_per_year}, '
              f'picard={p.picard_iters}, temperature_iters={p.t_iters}, t_relaxation={p.t_relaxation:g}, '
              f'transport={p.transport_scheme}, solver_rtol={p.solver_rtol:g}, '
              f'solver_max_iter={p.solver_max_iter}, strict={p.solver_require_convergence}, '
              f'seed={p.beyond_seed}', flush=True)
    if a.plan:
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, p in cases:
        print(f'Running {name}...', flush=True)
        started = time.monotonic()
        def progress(done, total):
            if done == 1 or done % 5 == 0 or done == total:
                print(f'  {name}: {done}/{total} seasonal steps including spin-up, '
                      f'{(time.monotonic() - started) / 60:.1f} min elapsed', flush=True)
        snapshot = out / f'{name}_seed{a.seed}_fields.npz' if a.save_fields else None
        row = diagnose(p, snapshot=snapshot, progress=progress)
        row.update(case=name, source_params=str(Path(a.params).resolve()))
        path = out / f'{name}_seed{a.seed}.json'
        path.write_text(json.dumps(row, indent=2) + '\n')
        print(f'{name}: objective={row["score"]:.4f}, correct={row["accuracy"]:.1%}; {path}', flush=True)


if __name__ == '__main__':
    main()
