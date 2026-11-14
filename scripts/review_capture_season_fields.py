"""Independent review of the capture-season sensitivity: scalar reference with a separate capture mask."""
import json, math, sys
from pathlib import Path
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.field_clock import field_clock
from land_people import CROPS, DAYS
from review_tigris_fields import pooled_from_raw, STOCKS, FLUXES
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/capture_season_20261114'; MESO = 'mesopotamia_euphrates_only'


def capture_reference():
    text = (ROOT / 'scripts/review_daily_river_fields.py').read_text(); body = text[text.index('def reference('):text.index('def main()')]
    for old, new in (('def reference(P,PET', 'def reference(R,PET'), ('surf=s[i,3]-release+.8*P[m,i]*days/DAYS', 'surf=s[i,3]-release+.8*R[t,i]'),
                     ('rain=P[m,i]*days/DAYS', 'rain=R[t,i]'), ('capture,kcb):', 'capture,kcb,cap):'), ('if capture and flood[t] else 0.', 'if capture and cap[t] else 0.')):
        if body.count(old) != 1: raise ValueError('Reviewed reference layout changed: ' + old)
        body = body.replace(old, new)
    space = dict(np=np, DAYS=DAYS); exec(body, space); return njit(space['reference'])


def main():
    r = json.loads((OUT / 'results.json').read_text()); assert len(r['rows']) == 24 and not r['adopt']
    for name, digest in {**r['producers'], **r['unchanged_sha256']}.items(): assert sha(ROOT / name) == digest, name
    assert sha(OUT / 'fields.npz') == r['files_sha256']['fields.npz']
    reference = capture_reference(); bins = np.linspace(0, 365, 13); c = CROPS['barley']
    with np.load(OUT / 'fields.npz') as a: z = {k: a[k] for k in a.files}
    with np.load(ROOT / 'output/flood_basin_storage_20261114/fields.npz') as a: areas = {k: a[k + '__area_km2'] * 1e6 for k in ('nile', MESO)}
    with np.load(ROOT / 'output/matched_regional_weather_20261114/forcing.npz') as a: F = {k: a[k] for k in a.files}
    phase = json.loads((ROOT / 'output/flood_basin_seasonality_20261113/results.json').read_text())
    q = next(v for v in phase['rows'] if v['id'] == 'aswan')['mean_monthly_flow_m3s']; mean = math.fsum(q) / 12
    sources = {'nile': np.array([max(v - mean, 0) * DAYS * 86400 for v in q]), MESO: pooled_from_raw()}
    maxstate = 0.; steps = 0; table = {}
    for row in r['rows']:
        case = row['case']; region = row['region']; area = areas[region]; T = F[region + '__matched_temperature_c']; P = F[region + '__matched_rain_mm']
        PET = F[region + '__power_' + row['method'] + '_mm']
        begin = 365 * (10 if row['calendar'] == 'old' else 10.5) / 12; end = 365 * (3 if row['calendar'] == 'old' else 2.5) / 12; flood = 365 * 7 / 12
        clock = field_clock(bins, event_edges_days=[begin, end, flood]); cw = clock.cyclic_window(begin, end); fw = clock.cyclic_window(flood, begin)
        cap = {'pre_sowing': fw, 'in_crop': cw, 'both': fw | cw}[row['window']]
        eligible = []
        for i in range(len(area)):
            ts = T[clock.bin_index[cw], i]; heat = math.fsum(max(float(v) - c['base'], 0) * float(d) for v, d in zip(ts, clock.step_days[cw]))
            eligible.append(bool(np.all((ts >= c['window'][0]) & (ts <= c['window'][1])) and ts.max() >= c['need_warm'] and heat >= c['heat']))
        eligible = np.array(eligible); np.testing.assert_array_equal(eligible, z[case + '__eligible'])
        rain = P[clock.bin_index] * (clock.step_days / DAYS)[:, None]; src = sources[region][clock.bin_index] * clock.fraction_of_bin
        annual, monthly, daily, yrs, residual, mass = reference(rain, PET, area, clock.step_days, clock.bin_index, cw, fw, eligible, src, 1.5, .15, 200., 1., True, c['kc'], cap)
        assert yrs == row['spinup_years'] and residual <= 1e-6 and mass < 1e-8, case
        for j, name in enumerate(['initial_' + k for k in STOCKS] + ['final_' + k for k in STOCKS] + ['annual_' + k for k in FLUXES]):
            maxstate = max(maxstate, float(np.max(np.abs(z[case + '__' + name] - annual[j]))))
            np.testing.assert_allclose(z[case + '__' + name], annual[j], rtol=2e-10, atol=2e-8, err_msg=case + ' ' + name)
        for j, name in enumerate(FLUXES + ['river_requested_m3', 'river_delivered_m3', 'river_loss_m3', 'river_outlet_m3']):
            np.testing.assert_allclose(z[case + '__monthly_' + name], monthly[j], rtol=2e-10, atol=.01, err_msg=case + ' ' + name)
        for j, name in enumerate(STOCKS): np.testing.assert_allclose(z[case + '__daily_' + name], daily[j], rtol=2e-10, atol=.01)
        cov = np.divide(annual[12], annual[13], out=np.zeros(len(area)), where=annual[13] > 0)
        value = float(np.average(cov[eligible], weights=area[eligible])); assert math.isclose(row['root_coverage'], value, abs_tol=2e-10)
        if row['window'] == 'pre_sowing': assert row['archived_arrays_exact'] is True
        table[case] = value; steps += len(area) * len(clock.step_days)
    fresh = OUT / 'fresh'; exact = {}
    for name in ['results.json', 'fields.npz']:
        assert (fresh / name).read_bytes() == (OUT / name).read_bytes(), name; exact[name] = sha(OUT / name)
    write(OUT / 'review.json', dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), cases=24, field_steps=steps,
        max_annual_field_difference_mm=maxstate, fresh_byte_exact=exact, coverage=table,
        method='Reviewed scalar reference with the capture mask separated from the pond mask by declared substitutions; sources rebuilt from gauge results and raw pages; producer not imported'))
    print('passed 24 cases;', steps, 'field-steps; max field diff', maxstate)


if __name__ == '__main__':
    main()
