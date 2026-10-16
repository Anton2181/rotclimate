"""Fast manufactured pressure-path and closed mixing experiments; no climate years."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_cloud_lab as lab
from experiments import v10_cloud_column_lab as column
from scripts import check_v10_cloud_mixing as frozen
from rotclimate_v10.earth import atomic_json, atomic_npz

INTERVALS = (1, 4, 16, 64, 256)
EXCHANGES = (0., .25, .5, .75, 1.)
GRID_LAYERS = (4, 8, 16, 32, 64, 128, 256)
CONTACT_CELLS = (16, 32, 64, 128, 256)


@dataclass(frozen=True)
class Lift:
    key: str
    temperature_c: float
    relative_humidity: float
    start_pa: float
    end_pa: float

    def air(self):
        return lab.Air(self.temperature_c, self.relative_humidity*lab.saturation(self.temperature_c, self.start_pa))


LIFTS = (
    Lift('dry_no_lift', 20., .4, 100000., 100000.),
    Lift('dry_shallow', 20., .2, 93500., 83600.),
    Lift('moist_shallow', 10., .9, 93500., 83600.),
    Lift('late_onset_wide', -5., .45, 68400., 45400.),
    Lift('moist_wide', -5., .9, 68400., 45400.),
    Lift('warm_lift', 20., .7, 100000., 80000.),
    Lift('warm_deep', 25., .8, 100000., 60000.),
    Lift('zero_vapor', 20., 0., 100000., 60000.))


def pair_cases():
    """Declared manufactured populations, without fitting to the regional maps."""
    def lifted(key, t, rh, p0, p1, receiver_t, receiver_rh):
        environment_start = (receiver_t+273.15)*(p0/p1)**lab.KAPPA-273.15
        return {'key': key, 'parcel': lab.Air(t, rh*lab.saturation(t, p0)),
            'environment': lab.Air(environment_start, receiver_rh*lab.saturation(receiver_t, p1)),
            'fraction': .2, 'start_pa': p0, 'end_pa': p1,
            'environment_unadjusted_arrival_temperature_c': receiver_t,
            'environment_unadjusted_arrival_RH': receiver_rh}
    return [
        lifted('lift_dry_environment', 20., .7, 100000., 80000., 10., .2),
        lifted('lift_humid_environment', 20., .7, 100000., 80000., 10., .8),
        lifted('wide_dry_environment', -5., .45, 68400., 45400., -12., .2),
        lifted('wide_humid_environment', -5., .85, 68400., 45400., -24., .8),
        {'key': 'isobaric_mixing_fog', 'parcel': lab.Air(20., lab.saturation(20., 90000.)),
         'environment': lab.Air(0., lab.saturation(0., 90000.)), 'fraction': .5, 'start_pa': 90000., 'end_pa': 90000.}]


def source_id():
    h = hashlib.sha256(frozen.source_id().encode())
    for path in (Path(__file__), Path(lab.__file__), Path(column.__file__)):
        h.update(path.read_bytes())
    return h.hexdigest()


def scalar_result(result):
    return {'rain_g_per_kg_initial_dry_air': float(result['cumulative_rain_kg_per_kg_initial_dry_air'][-1]*1000.),
        'final_temperature_c': result['temperature_c'][-1].tolist(),
        'final_vapor_ratio': result['vapor_ratio'][-1].tolist(),
        'pressure_work_j_per_kg_dry_air': result['pressure_work_j_per_kg_initial_dry_air'],
        'water_error_kg_per_kg_dry_air': result['water_error_kg_per_kg_dry_air'],
        'enthalpy_error_j_per_kg_dry_air': result['enthalpy_error_j_per_kg_dry_air']}


def analyse():
    started = time.monotonic(); code_id = source_id()
    paths = {}; pairs = {}; arrays = {}; maximum_water = maximum_energy = 0.
    for case in LIFTS:
        reference = lab.continuous_reference(case.air(), case.start_pa, case.end_pa)
        reference_rain = reference['rain_kg_per_kg_dry_air']*1000.
        rows = {}
        for n in INTERVALS:
            result = lab.ascend(case.air(), case.start_pa, case.end_pa, n); row = scalar_result(result)
            row.update(rain_error_vs_ODE_g_kg=row['rain_g_per_kg_initial_dry_air']-reference_rain,
                final_temperature_error_vs_ODE_c=row['final_temperature_c'][0]-reference['temperature_c'])
            rows[str(n)] = row
            arrays.update({f'{case.key}_n{n}_{name}': result[name] for name in ('pressure_pa', 'temperature_c', 'vapor_ratio', 'cumulative_rain_kg_per_kg_initial_dry_air')})
            maximum_water = max(maximum_water, abs(result['water_error_kg_per_kg_dry_air']))
            maximum_energy = max(maximum_energy, abs(result['enthalpy_error_j_per_kg_dry_air']))
        paths[case.key] = {'input': asdict(case), 'reference': reference, 'intervals': rows,
            'endpoint_relative_rain_error': rows['1']['rain_error_vs_ODE_g_kg']/reference_rain if reference_rain>0 else None}
    for case in pair_cases():
        rows = {}
        for amount in EXCHANGES:
            row = {}
            for n in INTERVALS:
                result = lab.ascend_pair(case['parcel'], case['environment'], case['fraction'], case['start_pa'], case['end_pa'], n, amount)
                row[str(n)] = dict(scalar_result(result), per_step_exchange_fraction=result['per_step_exchange_fraction'])
                maximum_water = max(maximum_water, abs(result['water_error_kg_per_kg_dry_air']))
                maximum_energy = max(maximum_energy, abs(result['enthalpy_error_j_per_kg_dry_air']))
            rows[str(amount)] = row
        pairs[case['key']] = {'input': {k:asdict(v) if isinstance(v, lab.Air) else v for k,v in case.items()}, 'exchange': rows}
    # Fixed excursion illustrates the declared instant-removal convention, not
    # a regional terrain-flow or hydrometeor-drift simulation.
    air = lab.Air(25., .8*lab.saturation(25., 100000.)); crest = lab.ascend(air, 100000., 80000., 256)
    descended = lab.dry_descent(lab.Air(float(crest['temperature_c'][-1, 0]), float(crest['vapor_ratio'][-1, 0])), 80000., 100000.)
    excursion = {'initial': asdict(air), 'crest': scalar_result(crest), 'return': asdict(descended),
        'return_RH': descended.vapor_ratio/lab.saturation(descended.temperature_c, 100000.),
        'note': 'Prescribed up/down pressure excursion after liquid has left; no horizontal airflow, new terrain forcing or precipitation evaporation.'}
    descent_work = lab.base.CP*(descended.temperature_c-float(crest['temperature_c'][-1, 0]))
    excursion.update(total_pressure_work_j_kg=crest['pressure_work_j_per_kg_initial_dry_air']+descent_work,
        water_error_kg_kg=descended.vapor_ratio+float(crest['cumulative_rain_kg_per_kg_initial_dry_air'][-1])-air.vapor_ratio,
        enthalpy_error_j_kg=float(lab.enthalpy(descended.temperature_c, descended.vapor_ratio)-lab.enthalpy(air.temperature_c, air.vapor_ratio)-crest['pressure_work_j_per_kg_initial_dry_air']-descent_work))
    if abs(excursion['water_error_kg_kg']) > 1e-11 or abs(excursion['enthalpy_error_j_kg']) > 1e-6:
        raise FloatingPointError('Up/down manufactured excursion accounting failed.')
    maximum_water = max(maximum_water, abs(excursion['water_error_kg_kg']))
    maximum_energy = max(maximum_energy, abs(excursion['enthalpy_error_j_kg']))
    grids = {}; numerical = {}; grid_errors = []
    _, coarse_g, coarse_state, coarse_flow = column.fixture(GRID_LAYERS[0])
    for n in GRID_LAYERS:
        _, g, initial, flow = column.fixture(n); ratio = n//GRID_LAYERS[0]
        # Coarse horizontal face flux equals the sum over its refined bands;
        # vertical face flux agrees at every shared pressure interface.
        for fine, old, tolerance in ((g.mass, coarse_g.mass, 1e-10), (initial.water, coarse_state.water, 1e-10),
            (initial.energy, coarse_state.energy, 1e-5), (flow.x, coarse_flow.x, 1e-10)):
            np.testing.assert_allclose(fine.reshape((GRID_LAYERS[0], ratio)+fine.shape[1:]).sum(1), old, atol=tolerance, rtol=0)
        np.testing.assert_allclose(flow.vertical[ratio-1::ratio], coarse_flow.vertical, atol=1e-14, rtol=0)
        for mode in ('bulk', 'unmixed'):
            result = column.run(n, mode); key = f'n{n}_{mode}'
            grids[key] = {k:v for k,v in result.items() if not isinstance(v, np.ndarray) and k not in ('state', 'geometry', 'flow')}
            for field in ('times_seconds', 'rain_history_mm', 'parcel_rain_history_mm'):
                arrays[key+'_'+field] = result[field]
            grid_errors.append((abs(result['water_error_mm']), abs(result['energy_error_j_m2'])))
    for n in (32, 128):
        numerical[str(n)] = {}
        for mode in ('bulk', 'unmixed'):
            fine = column.run(n, mode, .5)
            grid_errors.append((abs(fine['water_error_mm']), abs(fine['energy_error_j_m2'])))
            numerical[str(n)][mode] = {'half_step_rain_mm': fine['rain_mm'], 'half_step_change_mm': fine['rain_mm']-grids[f'n{n}_{mode}']['rain_mm'],
                'half_step_steps': fine['steps'], 'half_step_water_error_mm': fine['water_error_mm'], 'half_step_energy_error_j_m2': fine['energy_error_j_m2']}
        numerical[str(n)]['treatment_gain_change_mm'] = ((numerical[str(n)]['unmixed']['half_step_rain_mm']-numerical[str(n)]['bulk']['half_step_rain_mm'])
            -(grids[f'n{n}_unmixed']['rain_mm']-grids[f'n{n}_bulk']['rain_mm']))
    contacts = {}
    for n in CONTACT_CELLS:
        for courant in (.5, 1.):
            result = column.advect_contact(n, courant); key = f'n{n}_cfl{courant}'
            contacts[key] = {k:v for k,v in result.items() if not isinstance(v, np.ndarray)}
            for field, value in result.items():
                if isinstance(value, np.ndarray):
                    arrays[key+'_'+field] = value
    fine_rain = max(abs(r['intervals']['256']['rain_error_vs_ODE_g_kg']) for r in paths.values())
    fine_t = max(abs(r['intervals']['256']['final_temperature_error_vs_ODE_c']) for r in paths.values())
    if fine_rain > .005 or fine_t > .02:
        raise FloatingPointError('Fine manufactured path misses its independent reference tolerance.')
    if source_id() != code_id:
        raise ValueError('Sources changed during manufactured cloud audit.')
    data = {'schema': 1, 'code_sha256': code_id, 'frozen_cloud_code_sha256': frozen.source_id(),
        'intervals': list(INTERVALS), 'total_exchange_fractions': list(EXCHANGES),
        'single_parcel_cases': paths, 'closed_pair_cases': pairs, 'pressure_excursion': excursion,
        'manufactured_trajectories': len(LIFTS)*len(INTERVALS)+len(pairs)*len(EXCHANGES)*len(INTERVALS)+1,
        'manufactured_column_runs': len(grids)+2*len(numerical), 'grid_layers': list(GRID_LAYERS),
        'periodic_contact_runs': len(contacts), 'periodic_contact_cases': contacts,
        'column_cases': grids, 'column_time_step_checks': numerical,
        'column_input_integrals_and_shared_fluxes_match': True,
        'column_maximum_water_error_mm': max(v[0] for v in grid_errors),
        'column_maximum_energy_error_j_m2': max(v[1] for v in grid_errors),
        'maximum_water_error_kg_per_kg_dry_air': maximum_water, 'maximum_enthalpy_error_j_per_kg_dry_air': maximum_energy,
        'fine_path_reference_maximum_rain_error_g_kg': fine_rain, 'fine_path_reference_maximum_temperature_error_c': fine_t,
        'elapsed_seconds': time.monotonic()-started,
        'interpretation': 'Manufactured paths, closed symmetric mixing and a separate closed two-column finite-volume grid comparison. Liquid-only constant dry Cp/Lv and frozen instant-removal energy convention, not full moist-air thermodynamics or an entraining-convection/cloud-store scheme. Parcel paths retain endpoints and total mixing; the column uses common analytic pressure-face flow and matching mass/water/energy integrals. ODE reference uses the same saturation law, not observations. Neither experiment establishes regional climate convergence.',
        'new_regional_integrations': 0, 'new_downloads': 0, 'atlas_updated': False}
    return data, arrays


def markdown(data):
    lines = ['# Manufactured cloud-process laboratory', '',
        f"{data['manufactured_trajectories']} small parcel trajectories, {data['manufactured_column_runs']} closed column runs and {data['periodic_contact_runs']} periodic contact runs in {data['elapsed_seconds']:.2f} seconds. No regional climate integration or download; atlas unchanged.", '',
        '## Refining the same pressure path', '',
        '| Manufactured parcel | One jump | 256 intervals | Independent ODE | One-jump error |',
        '|---|---:|---:|---:|---:|']
    for key, row in data['single_parcel_cases'].items():
        reference = row['reference']['rain_kg_per_kg_dry_air']*1000.
        relative = row['endpoint_relative_rain_error']
        error = f'{relative:+.2%}' if relative is not None else 'zero reference rain'
        lines.append(f"| {key} | {row['intervals']['1']['rain_g_per_kg_initial_dry_air']:.5f} | {row['intervals']['256']['rain_g_per_kg_initial_dry_air']:.5f} | {reference:.5f} | {error} |")
    lines += ['', 'Rain units: grams per kilogram of initial dry air. These are not mm/year or seasonal regional rainfall. All versions traverse the same complete pressure drop; cutting the path at a layer face would be a different experiment.', '',
        f"The 256-interval path differs from the independently integrated reference by at most {data['fine_path_reference_maximum_rain_error_g_kg']:.5f} g/kg and {data['fine_path_reference_maximum_temperature_error_c']:.5f}°C on this fixed set. The reference solves the same liquid-only constant-Cp/Lv equations; it is not an observed cloud or independent saturation dataset.", '',
        '![Pressure paths](pressure_paths.png)', '',
        '## Mixing with a finite environment', '',
        '| Manufactured pair | No exchange | 50% total exchange | Complete homogenization |',
        '|---|---:|---:|---:|']
    for key, row in data['closed_pair_cases'].items():
        values = [row['exchange'][str(a)]['256']['rain_g_per_kg_initial_dry_air'] for a in (0., .5, 1.)]
        lines.append(f'| {key} | {values[0]:.5f} | {values[1]:.5f} | {values[2]:.5f} |')
    lines += ['', 'Units now refer to a kilogram of the **whole two-population dry-air mixture**, not a kilogram of donor air alone. Both populations have finite dry mass, vapor and enthalpy. Exchange preserves each dry mass and their total vapor/enthalpy; it is not dilution against an unlimited reservoir. The same total exchange fraction is distributed over the path at every refinement. No coefficient here is calibrated for the regional model.', '',
        'The saturated warm/cold isobaric pair is a mixing-fog counterexample: homogenization can create condensate. Consequently neither perfectly unmixed parcels nor grid-average saturation is a universal upper/lower bound across thermodynamic states. Dry-environment suppression in another constructed case cannot justify suppressing all summer rain.', '',
        '![Closed mixing](closed_mixing.png)', '',
        '## A separate finite-volume grid comparison', '',
        '| Layers over 1000–500hPa | Bulk rain | Unmixed rain | Added rain from the unmixed rule |',
        '|---|---:|---:|---:|']
    for n in GRID_LAYERS:
        a = data['column_cases'][f'n{n}_bulk']['rain_mm']; b = data['column_cases'][f'n{n}_unmixed']['rain_mm']
        lines.append(f'| {n} | {a:.6f} mm | {b:.6f} mm | {b-a:+.6f} mm |')
    lines += ['', 'This is a manufactured two-column circulation, with one rising and one descending branch and a smooth fixed pressure-face flux profile. There are no external water sources, surface evaporation, relaxation or terrain. The initial vapor pool is 6.628mm per unit domain area, and the duration is one fixed column-mass/peak-flux timescale, about 7.08 toy hours. These are not regional rainfall rates or seasonal results.', '',
        'Column mass and initial vapor/enthalpy integrals match on every grid. Fine horizontal fluxes sum to the coarse band fluxes; vertical fluxes match at shared pressure interfaces. Analytically integrated neutral dry profiles define the representative pressure/height, so this comparison does not mix a different initial heat or water supply into refinement.', '',
        'The rain amounts can still move substantially with refinement even while the difference between cloud rules shrinks. Do not call the highest-resolution run an observed answer or assert spatial convergence from a small treatment gap. This illustrates sensitivity to finite-volume transport/mixing and phase changes; it does not attribute the Earth-region errors uniquely.', '',
        '![Grid comparison](column_refinement.png)', '',
        '| Layer count | Half-step bulk rain change | Half-step unmixed rain change | Change in the cloud-rule gain |',
        '|---|---:|---:|---:|']
    for n, values in data['column_time_step_checks'].items():
        lines.append(f"| {n} | {values['bulk']['half_step_change_mm']:+.6f} mm | {values['unmixed']['half_step_change_mm']:+.6f} mm | {values['treatment_gain_change_mm']:+.6f} mm |")
    lines += ['', '## Exact-answer transport control', '',
        '| Periodic cells | Upwind CFL 0.5 rain | Exact-shift CFL 1 rain | Exact inviscid answer |',
        '|---|---:|---:|---:|']
    for n in CONTACT_CELLS:
        a = data['periodic_contact_cases'][f'n{n}_cfl0.5']['rain_g_per_kg_initial_dry_air']
        b = data['periodic_contact_cases'][f'n{n}_cfl1.0']['rain_g_per_kg_initial_dry_air']
        lines.append(f'| {n} | {a:.6f} g/kg | {b:.6f} g/kg | 0 g/kg |')
    lines += ['', 'Saturated 20°C and 0°C air at 900hPa undergo one periodic translation without ascent or physical diffusion. An inviscid parcel keeps its original temperature and vapor, so the exact solution produces no condensate. Conservative first-order upwind mixing of vapor and enthalpy produces artificial rain near the contact even while closing the water/heat ledgers. This uses the same upwind stencil as the frozen transport, on a distinct periodic fixture rather than its open-boundary regional implementation. CFL 1 is a special exact cell shift on this uniform grid, not a proposed regional time step.', '',
        '![Periodic contact](periodic_contact.png)', '',
        'The mixing-fog pair above deliberately allows physical exchange. This contact deliberately excludes it. Their different exact answers require distinguishing physical mixing from numerical diffusion rather than removing all mixing-induced clouds.']
    lines += ['',
        '## Accounting and implementation consequences', '',
        f"Maximum water residual {data['maximum_water_error_kg_per_kg_dry_air']:.2e} kg/kg; enthalpy/work residual {data['maximum_enthalpy_error_j_per_kg_dry_air']:.2e} J/kg. Pressure expansion/compression work is explicitly accumulated, while each liquid adjustment and symmetric exchange conserve the prototype's enthalpy convention.", '',
        f"The separate column comparison closes total water to {data['column_maximum_water_error_mm']:.2e} mm and diagnosed energy/work to {data['column_maximum_energy_error_j_m2']:.2e} J/m².", '',
        'The single-parcel path split and two-column grid comparison are different experiments. Neither refines the real regional grid, reconstructs real subgrid trajectories, adds ice or transports cloud/rain stores. They omit thermal relaxation, external moisture sources and momentum feedback. A path-corrected regional operator would also need the changed latent-heating/pressure-work distribution; substituting condensate alone would fail that physical comparison even if a bookkeeping residual were hidden.', '',
        'The laboratory implements the controlled comparison method motivated by [KiD](https://rmets.onlinelibrary.wiley.com/doi/abs/10.1002/qj.1913). [MetPy documents a moist-path ODE](https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.moist_lapse.html); the reference here uses exact derivatives of this project\'s saturation law and constants to isolate discretization rather than compare different thermodynamic conventions.', '',
        'Reproduce this small saved audit:', '', '```sh', '.venv/bin/python scripts/audit_v10_cloud_lab.py --write', '```']
    return '\n'.join(lines)+'\n'


def plot(data, arrays, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for ax, key in zip(axes.flat, ('moist_shallow', 'warm_lift', 'late_onset_wide', 'warm_deep')):
        row = data['single_parcel_cases'][key]
        for n, color in ((1, '#cb8c5a'), (4, '#77afbc'), (256, '#254d68')):
            t = arrays[f'{key}_n{n}_temperature_c'][:, 0]; p = arrays[f'{key}_n{n}_pressure_pa']/100.
            ax.plot(t, p, '.-' if n<5 else '-', color=color, label=f'{n} interval'+('s' if n>1 else ''), lw=1.7)
        ax.plot(row['reference']['temperature_c'], row['input']['end_pa']/100., 'kx', ms=8, label='ODE endpoint')
        ax.set(title=key.replace('_', ' '), xlabel='Parcel temperature (°C)', ylabel='Pressure (hPa)'); ax.invert_yaxis(); ax.grid(alpha=.2); ax.legend(frameon=False, fontsize=8)
    fig.suptitle('Same complete ascent · coarse and refined thermodynamic paths', fontsize=14)
    for ext in ('png', 'svg'):
        fig.savefig(out/('pressure_paths.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    x = np.array(CONTACT_CELLS)
    rain = [data['periodic_contact_cases'][f'n{n}_cfl0.5']['rain_g_per_kg_initial_dry_air'] for n in x]
    axes[0].plot(x, rain, 'o-', color='#b75865', label='Upwind CFL 0.5')
    axes[0].axhline(0., color='#254d68', ls='--', label='Exact inviscid solution / exact-shift control')
    axes[0].set_xscale('log', base=2); axes[0].set_xticks(x, [str(n) for n in x]); axes[0].set(xlabel='Cells over the same periodic circuit', ylabel='Artificial rain (g / kg initial dry air)'); axes[0].legend(frameon=False, fontsize=8)
    n = CONTACT_CELLS[1]; centers = (np.arange(n)+.5)/n; key = f'n{n}_cfl0.5'
    initial = arrays[key+'_initial_vapor_ratio']; final = arrays[key+'_final_vapor_ratio']
    axes[1].step(centers, initial*1000., where='mid', color='#254d68', label='Initial = exact after one circuit')
    axes[1].plot(centers, final*1000., 'o-', color='#b75865', ms=3, label=f'Upwind after one circuit ({n} cells)')
    axes[1].set(xlabel='Position around periodic circuit', ylabel='Vapor mixing ratio (g / kg dry air)'); axes[1].legend(frameon=False, fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle('No ascent, no physical mixing · numerical diffusion can still make rain', fontsize=13)
    for ext in ('png', 'svg'):
        fig.savefig(out/('periodic_contact.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    x = np.array(data['grid_layers'])
    for mode, color in (('bulk', '#888888'), ('unmixed', '#254d68')):
        axes[0].plot(x, [data['column_cases'][f'n{n}_{mode}']['rain_mm'] for n in x], 'o-', color=color, label=mode)
    gain = [data['column_cases'][f'n{n}_unmixed']['rain_mm']-data['column_cases'][f'n{n}_bulk']['rain_mm'] for n in x]
    axes[1].plot(x, gain, 'o-', color='#3a929c')
    for ax in axes:
        ax.set_xscale('log', base=2); ax.set_xticks(x, [str(n) for n in x]); ax.set_xlabel('Layers over the same 1000–500hPa column'); ax.grid(alpha=.2)
    axes[0].set(title='Total rain continues changing', ylabel='Rain (mm in the toy closed circulation)'); axes[0].legend(frameon=False)
    axes[1].set(title='Difference between rules becomes smaller', ylabel='Unmixed minus bulk rain (mm)')
    fig.suptitle('Vertical transport matters · same initial integrals and analytic circulation', fontsize=13)
    for ext in ('png', 'svg'):
        fig.savefig(out/('column_refinement.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    colors = ('#346b8b', '#459c9a', '#b0854f', '#b75865', '#7064a3')
    for (key, row), color in zip(data['closed_pair_cases'].items(), colors):
        for n, style in ((1, '--'), (256, '-')):
            rain = [row['exchange'][str(a)][str(n)]['rain_g_per_kg_initial_dry_air'] for a in EXCHANGES]
            ax.plot(EXCHANGES, rain, style, color=color, label=key.replace('_', ' ') if n==256 else None, marker='o' if n==256 else None)
    ax.set(xlabel='Total symmetric exchange fraction (fixed across refinements)', ylabel='Condensate (g / kg of whole initial dry-air mixture)', ylim=(0, None), xticks=EXCHANGES)
    ax.grid(alpha=.2); ax.legend(frameon=False, fontsize=9)
    fig.suptitle('Mixing can suppress cloud—or create it\nSolid: 256 pressure intervals · dashed: one interval · manufactured cases', fontsize=13)
    for ext in ('png', 'svg'):
        fig.savefig(out/('closed_mixing.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_cloud_lab')
    args = parser.parse_args(argv)
    if args.write:
        from scripts import replay_v10_cloud_geometry as geometry
        for protected in (ROOT/'output/v10_cloud_geometry', *geometry.protected_paths()):
            a, b = args.out.resolve(), protected.resolve()
            if a == b or a in b.parents or b in a.parents:
                raise ValueError('Preserve completed climates and prepared evidence.')
    data, arrays = analyse()
    if args.write:
        atomic_json(args.out/'audit.json', data); atomic_npz(args.out/'paths.npz', **arrays)
        (args.out/'audit.md').write_text(markdown(data)); plot(data, arrays, args.out)
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
