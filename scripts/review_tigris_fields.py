"""Independent review of the Tigris-pool fields: scalar reference, raw-gauge source, exact controls."""
import json, math, sys
from decimal import Decimal
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.field_clock import field_clock
from land_people import CROPS, DAYS
from review_tigris_gauge import parse, years
from review_rain_timing_fields import step_rain_reference
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/tigris_fields_20261114'; R = 'mesopotamia_euphrates_only'
STOCKS = ['top_mm', 'deep_mm', 'bound_mm', 'pond_mm']
FLUXES = ['infiltration_mm', 'delivered_mm', 'surface_evap_mm', 'bare_diffusion_mm', 'root_uptake_mm', 'root_potential_mm', 'pond_evap_mm',
          'pond_release_mm', 'surface_overflow_mm', 'soil_drainage_mm', 'rain_excluded_mm']


def pooled_from_raw():
    hit = years(parse(ROOT / 'data/cache/flood_basin_seasonality_20261113/hit.html'), 1932, 1972)
    mosul = years(parse(ROOT / 'data/cache/tigris_gauge_20261114/mosul.html'), 1932, 1972)
    common = sorted(set(hit) & set(mosul)); assert len(common) >= 5
    q = [sum(hit[y][m] + mosul[y][m] for y in common) / len(common) for m in range(12)]; mean = sum(q) / 12
    return np.array([float(max(v - mean, Decimal(0)) * Decimal(365) / 12 * 86400) for v in q])


def main():
    r = json.loads((OUT / 'results.json').read_text()); assert len(r['rows']) == 8 and not r['adopt']
    for name, digest in {**r['producers'], **r['unchanged_sha256']}.items(): assert sha(ROOT / name) == digest, name
    assert sha(OUT / 'fields.npz') == r['files_sha256']['fields.npz']
    reference = step_rain_reference(); bins = np.linspace(0, 365, 13)
    with np.load(OUT / 'fields.npz') as a: z = {k: a[k] for k in a.files}
    with np.load(ROOT / 'output/flood_basin_storage_20261114/fields.npz') as a: area = a[R + '__area_km2'] * 1e6
    with np.load(ROOT / 'output/matched_regional_weather_20261114/forcing.npz') as a: F = {k: a[k] for k in a.files if k.startswith(R)}
    source = pooled_from_raw(); np.testing.assert_allclose(z['source_m3_pooled'], source, rtol=1e-12)
    T, P = F[R + '__matched_temperature_c'], F[R + '__matched_rain_mm']; c = CROPS['barley']
    maxstate = 0.; steps = 0
    for row in r['rows']:
        case = row['case']; PET = F[R + '__power_' + row['method'] + '_mm']
        begin = 365 * (10 if row['calendar'] == 'old' else 10.5) / 12; end = 365 * (3 if row['calendar'] == 'old' else 2.5) / 12; flood = 365 * 7 / 12
        clock = field_clock(bins, event_edges_days=[begin, end, flood]); cw = clock.cyclic_window(begin, end); fw = clock.cyclic_window(flood, begin)
        eligible = []
        for i in range(len(area)):
            ts = T[clock.bin_index[cw], i]; heat = math.fsum(max(float(v) - c['base'], 0) * float(d) for v, d in zip(ts, clock.step_days[cw]))
            eligible.append(bool(np.all((ts >= c['window'][0]) & (ts <= c['window'][1])) and ts.max() >= c['need_warm'] and heat >= c['heat']))
        eligible = np.array(eligible); np.testing.assert_array_equal(eligible, z[case + '__eligible'])
        rain = P[clock.bin_index] * (clock.step_days / DAYS)[:, None]
        step_source = source[clock.bin_index] * clock.fraction_of_bin
        annual, monthly, daily, yrs, residual, mass = reference(rain, PET, area, clock.step_days, clock.bin_index, cw, fw, eligible, step_source,
                                                               1.5, .15, 200., 1., row['capture'], c['kc'])
        assert yrs == row['spinup_years'] and residual <= 1e-6 and mass < 1e-8, case
        for j, name in enumerate(['initial_' + k for k in STOCKS] + ['final_' + k for k in STOCKS] + ['annual_' + k for k in FLUXES]):
            maxstate = max(maxstate, float(np.max(np.abs(z[case + '__' + name] - annual[j]))))
            np.testing.assert_allclose(z[case + '__' + name], annual[j], rtol=2e-10, atol=2e-8, err_msg=case + ' ' + name)
        for j, name in enumerate(FLUXES + ['river_requested_m3', 'river_delivered_m3', 'river_loss_m3', 'river_outlet_m3']):
            np.testing.assert_allclose(z[case + '__monthly_' + name], monthly[j], rtol=2e-10, atol=.01, err_msg=case + ' ' + name)
        for j, name in enumerate(STOCKS): np.testing.assert_allclose(z[case + '__daily_' + name], daily[j], rtol=2e-10, atol=.01)
        cov = np.divide(annual[12], annual[13], out=np.zeros(len(area)), where=annual[13] > 0)
        assert math.isclose(row['root_coverage'], float(np.average(cov[eligible], weights=area[eligible])), abs_tol=2e-10)
        assert math.isclose(row['delivered_m3'], float(monthly[12].sum()), rel_tol=1e-9)
        if not row['capture']: assert row['rain_only_arrays_exact'] is True
        steps += len(area) * len(clock.step_days)
    fresh = OUT / 'fresh'; exact = {}
    for name in ['results.json', 'fields.npz']:
        assert (fresh / name).read_bytes() == (OUT / name).read_bytes(), name; exact[name] = sha(OUT / name)
    write(OUT / 'review.json', dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), cases=8, field_steps=steps,
        max_annual_field_difference_mm=maxstate, fresh_byte_exact=exact,
        method='Pooled source rebuilt from raw gauge pages with Decimal; reviewed scalar river/soil/pond reference with matched forcing; eligibility, annual field stocks/fluxes, monthly basin ledgers and daily stocks compared; producer not imported'))
    print('passed 8 cases;', steps, 'field-steps; max field diff', maxstate)


if __name__ == '__main__':
    main()
