"""Compare captured projected winds in true geographic coordinates; no runs."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from circulation_components import bilinear_monthly
from circulation_reference import geographic_wind, projection_jacobian
from local_benchmark_protocol import file_hash, write_json
from review_circulation_components import monthly

OUT = ROOT / 'output/circulation_components_20261127'
PLAN = ROOT / 'calibration/circulation_components_20261127/plan.json'


def main():
    assert not (OUT / 'geographic_review.json').exists(), 'Preserve completed comparison'
    plan = json.loads(PLAN.read_text())
    original = json.loads((OUT / 'review.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    specs = json.loads((ROOT / plan['region_specs']).read_text())
    with np.load(ROOT / plan['surface_reference']) as z:
        reference = dict(z)
    records, plots = [], {}
    for row in result['rows']:
        path = OUT / row['name'] / 'capture.npz'
        assert file_hash(path) == row['capture_sha256']
        with np.load(path) as z:
            s = dict(z)
        spec = specs[row['region']]
        assert spec['lat0'] > 0 and row['earth_frame'] == dict(retrograde=False, north_bearing=0)
        geometry = projection_jacobian(s['lat'], s['lon'], spec['lat0'], spec['lon0'])
        east, north = geographic_wind(s['step_u'], s['step_v'], geometry)
        drag = s['grid_drag'][s['rows'], s['cols']]
        belt = geographic_wind(s['diag__zonal_u']*drag, s['diag__zonal_v']*drag, geometry)
        pressure = geographic_wind(s['diag__pressure_u']*drag, s['diag__pressure_v']*drag, geometry)
        np.testing.assert_allclose(east, belt[0]+pressure[0], atol=2e-12, rtol=1e-13)
        np.testing.assert_allclose(north, belt[1]+pressure[1], atol=2e-12, rtol=1e-13)
        model = [monthly(a) for a in [east, north]]
        obs = [bilinear_monthly(reference[k], s['lat'], s['lon']) for k in ['u', 'v']]
        prior = next(r for r in original['statistics'] if r['name']==row['name'])
        curves = {k:np.asarray(v) for k,v in prior['monthly'].items()}
        for key, arrays in [('model',model),('obs',obs),('belt',[monthly(a) for a in belt]),('pressure',[monthly(a) for a in pressure])]:
            for axis, value in zip(['u','v'], arrays, strict=True):
                curves[key+'_'+axis] = value.mean(1)
        plots[row['name']] = curves
        records.append(dict(name=row['name'], region=row['region'], pad_km=row['pad_km'],
            frame='Physical east/north using inverse azimuthal-equidistant projection Jacobian, including metric factors.',
            geographic_vector_rmse_m_s=float(np.sqrt(np.mean((model[0]-obs[0])**2+(model[1]-obs[1])**2))),
            july={k:float(v[6]) for k,v in curves.items()}, monthly={k:v.tolist() for k,v in curves.items()},
            maximum_jacobian_metric_departure=float(max(np.max(np.abs(geometry[0]-1)),np.max(np.abs(geometry[3]-1)))),
            initial_fixed_frame_july_model_u=prior['july']['model_u']))
    # Reuse layout with corrected geographic model components and preserve the
    # original grid-frame figure/input as a separate, historical artifact.
    import review_circulation_components as plotting
    destination = OUT / 'geographic_plot'
    destination.mkdir(exist_ok=False)
    plotting.OUT = destination
    plotting.figure(plan, plots)
    (destination / 'wind_components.png').rename(OUT / 'geographic_wind_components.png')
    destination.rmdir()
    dependencies = [Path(__file__), ROOT/'scripts/circulation_reference.py', ROOT/'scripts/circulation_components.py',
                    ROOT/'scripts/review_circulation_components.py']
    write_json(OUT / 'geographic_review.json', dict(status='reviewed_geographic_wind_diagnostics_not_climate_qualification',
        original_grid_review_sha256=file_hash(OUT/'review.json'), plan_sha256=file_hash(PLAN),
        reference_sha256=file_hash(ROOT/plan['surface_reference']),
        correction='Initial review compares grid-right/up components with geographic reference. This supplement converts captured model vectors and both components using the existing tested projection Jacobian; it preserves original data/review/figure and requires no physical rerun.',
        dependencies_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in dependencies}, statistics=records,
        figure_sha256=file_hash(OUT/'geographic_wind_components.png'),
        scope='Descriptive regridded climatology; model cells are not independent observed wind samples. The pressure-gate slopes remain the exact production-grid diagnostic, not a full-pressure or geographic-gradient equivalence.',
        extra_regional_integrations=0, parameter_changes={}, observed_forcing=False, climate_adopted=False, atlas_changed=False))
    print('Applied existing tested projection/metric transform to wind comparison; no climate reruns.')


if __name__ == '__main__':
    main()
