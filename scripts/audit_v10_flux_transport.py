"""Fast fixed manufactured transport comparisons; no regional integration."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_flux_transport as transport, v10_transport_lab as lab
from scripts import audit_v10_cloud_lab as parent
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256

CELLS = (16, 32, 64, 128, 256)
LAYERS = (4, 8, 16, 32, 64, 128, 256)


def source_id():
    h = hashlib.sha256(parent.source_id().encode())
    for path in (Path(__file__), Path(transport.__file__), Path(lab.__file__)):
        h.update(path.read_bytes())
    return h.hexdigest()


def compact(result, arrays, key):
    row = {}
    for name, value in result.items():
        if isinstance(value, np.ndarray):
            arrays[key+'_'+name] = value
        elif name not in ('state', 'geometry', 'flow'):
            row[name] = value
    return row


def parent_identity():
    folder=ROOT/'output/v10_cloud_lab'
    saved=json.loads((folder/'audit.json').read_text())
    if saved['code_sha256']!=parent.source_id():
        raise ValueError('Parent laboratory sources changed since its saved audit.')
    return {name:sha256(folder/name) for name in ('audit.json','paths.npz')}


def analyse():
    started = time.monotonic(); code_id = source_id(); parent_files = parent_identity()
    arrays = {}; periodic = {}; columns = {}; half_steps = {}; symmetry = {}; dry = {}
    for case in ('smooth', 'contact'):
        for n in CELLS:
            for scheme in lab.SCHEMES:
                key = f'{case}_n{n}_{scheme}'; tick = time.monotonic()
                result = lab.periodic(n, scheme, case)
                periodic[key] = dict(compact(result, arrays, key), elapsed_seconds=time.monotonic()-tick)
    for case in ('smooth', 'contact'):
        for n in (32, 128):
            for scheme in lab.SCHEMES:
                key = f'{case}_n{n}_{scheme}'; result = lab.periodic(n, scheme, case, .25)
                periodic[key+'_half'] = compact(result, arrays, key+'_half')
    for case in ('smooth', 'contact'):
        for scheme in lab.SCHEMES:
            key = f'{case}_n32_{scheme}'
            row = compact(lab.periodic(32, scheme, case, direction=-1), arrays, key+'_reverse')
            forward = periodic[key]
            symmetry[key] = {'rain_difference_g_kg': row['rain_g_per_kg']-forward['rain_g_per_kg'],
                'theta_error_difference_k': row['theta_mean_absolute_error_k']-forward['theta_mean_absolute_error_k'],
                'vapor_error_difference_g_kg': row['vapor_mean_absolute_error_g_kg']-forward['vapor_mean_absolute_error_g_kg']}
    for n in LAYERS:
        for mode in ('bulk', 'unmixed'):
            for scheme in lab.SCHEMES:
                key = f'n{n}_{mode}_{scheme}'; tick = time.monotonic()
                result = lab.column(n, mode, scheme)
                columns[key] = dict(compact(result, arrays, key), elapsed_seconds=time.monotonic()-tick)
    for n in (32, 128):
        for mode in ('bulk', 'unmixed'):
            for scheme in lab.SCHEMES:
                key = f'n{n}_{mode}_{scheme}'
                result = lab.column(n, mode, scheme, .5)
                half_steps[key] = compact(result, arrays, key+'_half')
                half_steps[key]['rain_change_mm'] = result['rain_mm']-columns[key]['rain_mm']
    for scheme in lab.SCHEMES:
        result = lab.column(32, 'bulk', scheme, vapor=False, physics=False)
        g = result['geometry']; state = result['state']
        theta = (lab.base.temperature(state.energy, g.mass, state.water, g.height_m)+273.15)/transport.thermal.exner(g.pressure)
        dry[scheme] = {'rain_mm': result['rain_mm'], 'vapor_mm': result['remaining_vapor_mm'],
            'maximum_theta_error_k': float(abs(theta-lab.original.THETA).max()),
            'water_error_mm': result['water_error_mm'], 'energy_error_j_m2': result['energy_error_j_m2']}
    parent_data=json.loads((ROOT/'output/v10_cloud_lab/audit.json').read_text())
    exact_controls=all(all(columns[key+'_upwind'][field]==value for field,value in row.items())
        for key,row in parent_data['column_cases'].items())
    orders = {}
    for scheme in lab.SCHEMES:
        errors = [periodic[f'smooth_n{n}_{scheme}']['theta_mean_absolute_error_k'] for n in CELLS]
        orders[scheme] = [float(np.log2(a/b)) for a,b in zip(errors[:-1], errors[1:])]
    gates = {
        'smooth_error_reduced_every_grid': all(periodic[f'smooth_n{n}_coupled_fct']['theta_mean_absolute_error_k'] < periodic[f'smooth_n{n}_upwind']['theta_mean_absolute_error_k'] for n in CELLS),
        'smooth_error_decreases_with_refinement': all(order>0 for order in orders['coupled_fct']),
        'contact_artificial_rain_reduced_every_grid': all(periodic[f'contact_n{n}_coupled_fct']['rain_g_per_kg'] < periodic[f'contact_n{n}_upwind']['rain_g_per_kg'] for n in CELLS),
        'contact_artificial_rain_decreases_with_refinement': all(periodic[f'contact_n{b}_coupled_fct']['rain_g_per_kg'] < periodic[f'contact_n{a}_coupled_fct']['rain_g_per_kg'] for a,b in zip(CELLS[:-1],CELLS[1:])),
        'reversal_scalar_metrics_agree': all(abs(v)<1e-8 for row in symmetry.values() for v in row.values()),
        'dry_uniform_theta_preserved': all(row['maximum_theta_error_k']<1e-8 and row['rain_mm']==row['vapor_mm']==0 for row in dry.values()),
        'both_frozen_cloud_rules_complete_without_clipping': len(columns)==len(LAYERS)*4,
        'fourteen_controls_match_saved_parent_exactly': exact_controls,
    }
    if source_id() != code_id or parent_identity()!=parent_files:
        raise ValueError('Sources or parent evidence changed during manufactured transport comparison.')
    data = {'schema': 1, 'code_sha256': code_id, 'parent_cloud_lab_code_sha256': parent.source_id(),
        'periodic_cases': periodic, 'periodic_reversal_checks': symmetry, 'column_cases': columns,
        'parent_evidence_sha256': parent_files,
        'column_half_step_checks': half_steps, 'dry_uniform_checks': dry, 'smooth_observed_orders': orders,
        'development_gates': gates, 'all_development_gates_pass': all(gates.values()),
        'manufactured_runs': len(periodic)+len(symmetry)+len(columns)+len(half_steps)+len(dry),
        'elapsed_seconds': time.monotonic()-started, 'new_regional_integrations': 0, 'new_downloads': 0, 'atlas_updated': False,
        'method': 'Explicit upwind/centered-midpoint flux correction on a balanced fixed-mass closed face graph. Zalesak-style local budgets and one minimum face coefficient for theta and vapor; diagnostic MSE/T use the same coefficient. Bounds have a 64-epsilon per-field arithmetic allowance with an exact zero lower floor. No scalar clipping, cloud retuning or open boundaries.',
        'interpretation': 'Manufactured numerical validation only. Reduced artificial contact rain and better passive transport do not imply improved regional winter/summer rainfall. Contact error remains nonzero. Closed columns retain the old instantaneous cloud rules and diagnosed prescribed-flow energy convention.'}
    return data, arrays


def markdown(data):
    p = data['periodic_cases']; c = data['column_cases']
    lines = ['# Coupled flux-corrected transport laboratory', '',
        f"{data['manufactured_runs']} fixed manufactured runs in {data['elapsed_seconds']:.2f}s; no regional climate year, download or atlas change.", '',
        '## Passive transport and false cloud formation', '',
        '| Cells | Smooth theta MAE: upwind / candidate | Artificial contact rain: upwind / candidate | Rain reduction |',
        '|---|---:|---:|---:|']
    for n in CELLS:
        a,b = (p[f'smooth_n{n}_{s}']['theta_mean_absolute_error_k'] for s in lab.SCHEMES)
        rain_a,rain_b = (p[f'contact_n{n}_{s}']['rain_g_per_kg'] for s in lab.SCHEMES)
        lines.append(f'| {n} | {a:.5f} / {b:.5f} K | {rain_a:.6f} / {rain_b:.6f} g/kg | {1-rain_b/rain_a:.1%} |')
    lines += ['', 'Both problems complete one periodic translation at common CFL 0.5. Smooth inputs are analytic cell averages; their exact answer is the initial profile. The saturated warm/cold inviscid contact has exact zero rain. Candidate contact error is reduced, not eliminated. Neither number is seasonal regional rain.', '',
        '![Periodic comparison](periodic_comparison.png)', '',
        'Observed smooth theta L1 refinement orders: upwind '+', '.join(f'{x:.2f}' for x in data['smooth_observed_orders']['upwind'])+
        '; candidate '+', '.join(f'{x:.2f}' for x in data['smooth_observed_orders']['coupled_fct'])+'. These empirical rates on this smooth case are not a global order guarantee near fronts or during condensation.', '',
        '## Same closed circulation, unchanged cloud rules', '',
        '| Layers | Upwind bulk / unmixed rain | Candidate bulk / unmixed rain |',
        '|---|---:|---:|']
    for n in LAYERS:
        values = [c[f'n{n}_{mode}_{scheme}']['rain_mm'] for scheme in lab.SCHEMES for mode in ('bulk','unmixed')]
        lines.append(f'| {n} | {values[0]:.6f} / {values[1]:.6f} mm | {values[2]:.6f} / {values[3]:.6f} mm |')
    lines += ['', 'Column mass, initial vapor/enthalpy, circulation, duration, cloud operators and permitted steps match the parent laboratory. This is a finite closed vapor pool, not a regional rainfall rate. The candidate makes this rising-column example wetter while reducing false rain at the isobaric contact. Numerical accuracy cannot be selected by a universal preference for less rain. A small bulk/unmixed gap still does not establish convergence; the parent mixing-fog counterexample also rules out universal bounds across thermodynamic states.', '',
        '![Column comparison](column_comparison.png)', '',
        '## Time-step checks', '', '| Comparison | Half-step rain change |', '|---|---:|']
    for key,row in data['column_half_step_checks'].items():
        lines.append(f"| {key} | {row['rain_change_mm']:+.6f} mm |")
    lines += ['', 'Periodic half-step inputs at 32/128 cells and direction reversal at 32 cells are also saved in the JSON. Exact convergence requires more than a small difference between two cloud rules.', '',
        '## Development gates', '']
    for key,value in data['development_gates'].items():
        lines.append(f"- {'PASS' if value else 'FAIL'}: {key.replace('_',' ')}")
    periodic_water = max(abs(row['water_error_kg_kg']) for row in p.values())
    periodic_heat = max(abs(row['enthalpy_error_j_kg']) for row in p.values())
    rows = list(c.values())+list(data['column_half_step_checks'].values())
    lines += ['', f'Periodic maximum water/heat residuals: {periodic_water:.2e} kg/kg / {periodic_heat:.2e} J/kg. Column maximum water/work-ledger residuals: '+
        f"{max(abs(r['water_error_mm']) for r in rows):.2e} mm / {max(abs(r['energy_error_j_m2']) for r in rows):.2e} J/m².", '',
        '## Scope before regional use', '',
        'This candidate supports balanced fixed-mass closed/periodic meshes only. It has no tested open-boundary inflow/outflow contract, monthly forcing/checkpoint integration or regional runtime estimate. No annual comparison is ready yet. Next add boundary tests with independently prescribed tracer/heat fluxes, and extend manufactured multidimensional circulation checks beyond the tested diagonal periodic translation; retain the same face limiter and physical ledgers. All old climate sources and evidence remain unchanged.', '',
        'Each bounded field gets a 64-machine-epsilon arithmetic allowance scaled to its own magnitude, with an exact zero lower floor. This prevents roundoff in nearly uniform theta from vetoing a real moisture correction. No prognosed scalar is clipped; zero face correction in a field consumes none of its limiting budget. A regression checks this against scalar vapor transport on four nested grids.', '',
        'Method references: [Zalesak (1979)](https://www.sciencedirect.com/science/article/pii/0021999179900512) for multidimensional flux correction; [Möller, Kuzmin and Turek, §§7.1–7.2](https://diamhomes.ewi.tudelft.nl/~mmoller/files/publications/TecRep221.pdf) for limiting budgets and synchronized coefficients. Our explicit finite-volume implementation is not their implicit finite-element solver.', '',
        'Already completed; reproduce only if desired:', '', '```sh', '.venv/bin/python scripts/audit_v10_flux_transport.py --write', '```']
    return '\n'.join(lines)+'\n'


def plot(data, arrays, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    p = data['periodic_cases']; c = data['column_cases']
    fig, axes = plt.subplots(1,2,figsize=(11,4.6),constrained_layout=True)
    for scheme,color,label in (('upwind','#888888','Existing upwind'),('coupled_fct','#254d68','Coupled correction')):
        axes[0].loglog(CELLS,[p[f'smooth_n{n}_{scheme}']['theta_mean_absolute_error_k'] for n in CELLS],'o-',color=color,label=label)
        axes[1].plot(CELLS,[p[f'contact_n{n}_{scheme}']['rain_g_per_kg'] for n in CELLS],'o-',color=color,label=label)
    axes[0].set(title='Smooth transport error',ylabel='Mean absolute potential-temperature error (K)')
    axes[1].set_xscale('log',base=2); axes[1].axhline(0,color='#459c9a',ls='--',label='Exact inviscid answer')
    axes[1].set(title='False rain at a saturated contact',ylabel='Condensate (g / kg initial dry air)')
    for ax in axes:
        ax.set_xticks(CELLS,[str(n) for n in CELLS]); ax.set_xlabel('Cells over the same periodic circuit'); ax.grid(alpha=.2); ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Less numerical mixing · common time step and unchanged cloud adjustment',fontsize=13)
    for ext in ('png','svg'): fig.savefig(out/('periodic_comparison.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.6),constrained_layout=True)
    for ax,mode in zip(axes,('bulk','unmixed')):
        for scheme,color,label in (('upwind','#888888','Existing upwind'),('coupled_fct','#254d68','Coupled correction')):
            ax.plot(LAYERS,[c[f'n{n}_{mode}_{scheme}']['rain_mm'] for n in LAYERS],'o-',color=color,label=label)
        ax.set_xscale('log',base=2);ax.set_xticks(LAYERS,[str(n) for n in LAYERS]); ax.set(title=mode+' cloud rule',xlabel='Layers (1000–500 hPa)',ylabel='Rain from the finite toy vapor pool (mm)');ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Reduced diffusion makes this rising-column example wetter',fontsize=13)
    for ext in ('png','svg'):fig.savefig(out/('column_comparison.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--out',type=Path,default=ROOT/'output/v10_flux_transport_lab')
    args = parser.parse_args(argv)
    if args.write:
        from scripts import replay_v10_cloud_geometry as geometry
        for protected in (ROOT/'output/v10_cloud_geometry',ROOT/'output/v10_cloud_lab',*geometry.protected_paths()):
            a,b = args.out.resolve(),protected.resolve()
            if a==b or a in b.parents or b in a.parents:
                raise ValueError('Preserve completed climates and parent laboratory evidence.')
    data,arrays=analyse()
    if args.write:
        atomic_json(args.out/'audit.json',data);atomic_npz(args.out/'paths.npz',**arrays)
        (args.out/'audit.md').write_text(markdown(data));plot(data,arrays,args.out)
    print(markdown(data))
    return 0 if data['all_development_gates_pass'] else 2


if __name__=='__main__':
    raise SystemExit(main())
