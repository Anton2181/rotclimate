"""Independent review of the rain-timing sensitivity.

Pulse rain is rebuilt here from the declared bin/event intersections with plain
loops (harvest.rain_timing is not imported). The scalar river/soil/pond ledger
is the previously reviewed reference from scripts/review_daily_river_fields.py,
taken from its source with two declared substitutions so that it reads rain
per clock step instead of spreading monthly rain uniformly.
"""
import json, math, sys
from pathlib import Path
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.field_clock import field_clock
from land_people import CROPS, DAYS
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/rain_timing_20261114'; BASE = ROOT / 'output/daily_river_fields_20261114'
STOCKS = ['top_mm', 'deep_mm', 'bound_mm', 'pond_mm']
FLUXES = ['infiltration_mm', 'delivered_mm', 'surface_evap_mm', 'bare_diffusion_mm', 'root_uptake_mm', 'root_potential_mm', 'pond_evap_mm',
          'pond_release_mm', 'surface_overflow_mm', 'soil_drainage_mm', 'rain_excluded_mm']


def step_rain_reference():
    text = (ROOT / 'scripts/review_daily_river_fields.py').read_text()
    body = text[text.index('def reference('):text.index('def main()')]
    for old, new in (('def reference(P,PET', 'def reference(R,PET'), ('surf=s[i,3]-release+.8*P[m,i]*days/DAYS', 'surf=s[i,3]-release+.8*R[t,i]'),
                     ('rain=P[m,i]*days/DAYS', 'rain=R[t,i]')):
        if body.count(old) != 1: raise ValueError('Reviewed reference layout changed: ' + old)
        body = body.replace(old, new)
    if 'P[' in body: raise ValueError('Monthly rain still referenced')
    space = dict(np=np, DAYS=DAYS); exec(body, space); return njit(space['reference'])


def pulse_rain(bins, edges, P, count):
    """Rain per step and field from first principles; count 0 is uniform."""
    nt = len(edges) - 1; rain = np.zeros((nt, P.shape[1]))
    for t in range(nt):
        a, z = float(edges[t]), float(edges[t + 1])
        for b in range(12):
            lo, hi = float(bins[b]), float(bins[b + 1])
            if count == 0:
                over = max(min(z, hi) - max(a, lo), 0.0)
                if over > 0: rain[t] += P[b] * (over / (hi - lo))
                continue
            for j in range(count):
                centre = lo + (j + 0.5) / count * (hi - lo)
                over = max(min(z, centre + 0.5) - max(a, centre - 0.5), 0.0)
                if over > 0: rain[t] += P[b] * (over / count)
    return rain


def main():
    r = json.loads((OUT / 'results.json').read_text()); assert len(r['rows']) == 32 and not r['adopt']
    for name, digest in {**r['producers'], **r['pinned_daily_producers'], **r['unchanged_sha256']}.items(): assert sha(ROOT / name) == digest, name
    assert sha(OUT / 'fields.npz') == r['files_sha256']['fields.npz'] and sha(BASE / 'results.json') == r['baseline_results_sha256']
    reference = step_rain_reference(); bins = np.linspace(0, 365, 13)
    with np.load(OUT / 'fields.npz') as archive: z = {k: archive[k] for k in archive.files}
    with np.load(ROOT / 'output/flood_basin_storage_20261114/fields.npz') as archive: raw = {k: archive[k] for k in archive.files}
    with np.load(BASE / 'fields.npz') as archive: old = {k: archive[k] for k in archive.files if '__z1.5_' in k and '_b0.15_p200_e1_' in k and '__barley__' in k}
    phase = json.loads((ROOT / 'output/flood_basin_seasonality_20261113/results.json').read_text())
    events = sorted({edge for count in (1, 2, 4) for b in range(12) for j in range(count)
                     for edge in (bins[b] + (j + .5) / count * (bins[b + 1] - bins[b]) - .5, bins[b] + (j + .5) / count * (bins[b + 1] - bins[b]) + .5)})
    columns = ['initial_' + k for k in STOCKS] + ['final_' + k for k in STOCKS] + ['annual_' + k for k in FLUXES]
    maxstate = 0.; maxmass = 0.; maxrain = 0.; steps = 0; spread = {}
    for row in r['rows']:
        case = row['case']; b = row['region']; area = raw[b + '__area_km2'] * 1e6; T = raw[b + '__T']; P = raw[b + '__P']; PET = raw[b + '__PET']; c = CROPS[row['crop']]
        assert (row['crop'], row['root_depth_m'], row['bare_background'], row['pond_capacity_mm'], row['efficiency']) == ('barley', 1.5, .15, 200., 1.)
        begin = 365 * (10 if row['calendar'] == 'old' else 10.5) / 12; end = 365 * (3 if row['calendar'] == 'old' else 2.5) / 12; flood = 365 * 7 / 12
        clock = field_clock(bins, event_edges_days=[begin, end, flood] + events); cw = clock.cyclic_window(begin, end); fw = clock.cyclic_window(flood, begin)
        assert len(clock.step_days) == len(z[case + '__daily_top_mm'])
        eligible = []
        for i in range(len(area)):
            ts = T[clock.bin_index[cw], i]; heat = math.fsum(max(float(v) - c['base'], 0) * float(d) for v, d in zip(ts, clock.step_days[cw]))
            eligible.append(bool(np.all((ts >= c['window'][0]) & (ts <= c['window'][1])) and ts.max() >= c['need_warm'] and heat >= c['heat']))
        eligible = np.array(eligible); np.testing.assert_array_equal(eligible, z[case + '__eligible'])
        np.testing.assert_array_equal(eligible, old[row['parent_case'] + '__eligible'])                    # eligibility fixed at baseline
        rain = pulse_rain(bins, clock.edges_days, P, row['events_per_bin'])
        totals = np.array([rain[clock.bin_index == k].sum(0) for k in range(12)]); maxrain = max(maxrain, float(np.max(np.abs(totals - P))))
        assert rain.min() >= 0 and np.allclose(totals, P, rtol=1e-11, atol=1e-9), case
        if row['events_per_bin']: assert math.isclose(float(clock.step_days[rain.max(1) > 0].sum()), 12. * row['events_per_bin'], abs_tol=1e-9) or P.max(1).min() == 0
        assert math.isclose(row['rain_m3'], float(np.sum(rain * area[None, :] / 1000.)), rel_tol=1e-11)
        gauge = 'aswan' if b == 'nile' else 'hit'; q = next(v for v in phase['rows'] if v['id'] == gauge)['mean_monthly_flow_m3s']; mean = math.fsum(q) / 12
        source = np.array([max(v - mean, 0) * DAYS * 86400 for v in q])[clock.bin_index] * clock.fraction_of_bin
        annual, monthly, daily, years, residual, mass = reference(rain, PET, area, clock.step_days, clock.bin_index, cw, fw, eligible, source,
            row['root_depth_m'], row['bare_background'], row['pond_capacity_mm'], row['efficiency'], row['capture'], c['kc'])
        assert years == row['spinup_years'] and residual <= 1e-6 and row['periodic'], case
        maxmass = max(maxmass, float(mass)); assert mass < 1e-8
        for j, name in enumerate(columns):
            actual = z[case + '__' + name]; maxstate = max(maxstate, float(np.max(np.abs(actual - annual[j]))))
            np.testing.assert_allclose(actual, annual[j], rtol=2e-10, atol=2e-8, err_msg=case + ' ' + name)
        for j, name in enumerate(FLUXES + ['river_requested_m3', 'river_delivered_m3', 'river_loss_m3', 'river_outlet_m3']):
            np.testing.assert_allclose(z[case + '__monthly_' + name], monthly[j], rtol=2e-10, atol=.01, err_msg=case + ' ' + name)
        for j, name in enumerate(STOCKS): np.testing.assert_allclose(z[case + '__daily_' + name], daily[j], rtol=2e-10, atol=.01)
        cov = np.divide(annual[12], annual[13], out=np.zeros(len(area)), where=annual[13] > 0)
        np.testing.assert_allclose(z[case + '__root_coverage'], cov, atol=2e-10)
        value = float(np.average(cov[eligible], weights=area[eligible])); assert math.isclose(row['root_coverage'], value, abs_tol=2e-10)
        assert abs(row['joint_mass_residual_m3']) < .01
        spread.setdefault(row['parent_case'], {})[row['rain_pattern']] = value; steps += len(area) * len(clock.step_days)
    for c in r['clock_control']:                                                                         # uniform common clock against the archived original clock
        parent = c['parent_case']; assert math.isclose(c['common_clock_uniform_coverage'], spread[parent]['uniform'], abs_tol=2e-10)
        assert math.isclose(c['coverage_difference'], spread[parent]['uniform'] - float(np.average(old[parent + '__root_coverage'][old[parent + '__eligible']],
            weights=(raw[('nile' if parent.startswith('nile') else 'mesopotamia_euphrates_only') + '__area_km2'])[old[parent + '__eligible']])), abs_tol=1e-9)
    fresh = OUT / 'fresh'; exact = {}
    for name in ['results.json', 'fields.npz']:
        assert (fresh / name).exists(), 'Run the producer into output/rain_timing_20261114/fresh first'
        assert (fresh / name).read_bytes() == (OUT / name).read_bytes(), name; exact[name] = sha(OUT / name)
    summary = {p: dict(v, range=max(v.values()) - min(v.values())) for p, v in spread.items()}
    write(OUT / 'review.json', dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), scenario_rows=len(r['rows']),
        field_steps=steps, max_annual_field_difference_mm=maxstate, max_step_mass_residual_mm=maxmass, max_bin_rain_total_error_mm=maxrain,
        fresh_byte_exact=exact, coverage_by_pattern=summary,
        max_clock_control_coverage_difference=max(abs(c['coverage_difference']) for c in r['clock_control']),
        method='Pulse rain rebuilt from bin/event intersections with plain loops; previously reviewed scalar river/soil/pond reference with two declared '
               'substitutions to read per-step rain; eligibility, annual per-field stocks and fluxes, monthly basin ledgers, daily basin stocks compared; producer and rain module not imported'))
    print('Passed 32 cases;', steps, 'field-steps; max field diff', maxstate, '; max clock-control coverage diff', max(abs(c['coverage_difference']) for c in r['clock_control']))


if __name__ == '__main__':
    main()
