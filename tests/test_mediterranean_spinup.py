from dataclasses import asdict
import json
import sys

import numpy as np
import pytest

from scripts import check_mediterranean_spinup as spinup
from scripts.validate_mediterranean import finalists


def fixture_fields():
    p = finalists()['strong_seasonal'].replace(beyond_seed=1)
    f = dict(target=np.array([2, 4, 7]), valid=np.ones(3, bool), elev=np.zeros(3),
             koppen=np.zeros(3, int), params_json=np.array(json.dumps(asdict(p))))
    f.update({f'index_{k}':np.ones(3) * value for k, value in
              dict(MAT=19., Tcold=5., Thot=30., MAP=400., Pwin=270., Psum=130., Psdry=15., Pwwet=65.).items()})
    return p, f


def detail(p):
    return dict(params=asdict(p), accuracy=.49, zones={
        'med':dict(correct=.35, koppen_share={'BSh':.11, 'Csa':.38}),
        'cold_dry':dict(correct=.68), 'hot_dry':dict(correct=.61)}, moisture_transport=None,
        solver=dict(unconverged_solves=0),
        temperature_convergence=dict(unconverged_steps=0, final_update_max_c=[.04], converged=[True]*33),
        moisture_convergence=dict(enabled=True, unconverged_steps=0))


def test_annual_and_label_changes_expose_a_seasonality_threshold_crossing():
    p, a = fixture_fields()
    b = {k:v.copy() for k,v in a.items()}
    b['index_MAP'][1] += 1.
    b['index_Pwin'][1] = 290.
    b['index_Psum'][1] = 111.
    b['koppen'][1] = 7
    change = spinup.changes(a, b)['zones']['med']
    assert change['winter_70_percent_crossing_share'] == 1.
    assert change['koppen_changed_share'] == 1.
    assert change['fields']['MAP']['signed_median'] == 1.


@pytest.mark.parametrize('changed', ['geography', 'parameters'])
def test_spinup_analysis_rejects_unpaired_physical_changes(changed):
    p, a = fixture_fields()
    b = {k:v.copy() for k,v in a.items()}
    if changed == 'geography':
        b['elev'][1] = 100.
    else:
        b['params_json'] = np.array(json.dumps(asdict(p.replace(beyond_seed=302))))
    with pytest.raises(ValueError, match='identical'):
        spinup.changes(a, b)


def test_monthly_comparison_catches_changes_hidden_by_equal_annual_rain():
    p, a = fixture_fields()
    a.update(summer=np.arange(12) < 6, monthly_temperature_c=np.full((12,3),20.),
             monthly_rain_mm_day=np.full((12,3),1.))
    b = {k:v.copy() for k,v in a.items()}
    b['monthly_rain_mm_day'][0,1] += .1
    b['monthly_rain_mm_day'][1,1] -= .1
    assert np.allclose(a['monthly_rain_mm_day'].sum(0), b['monthly_rain_mm_day'].sum(0))
    change = spinup.monthly_changes(a, b, 365)['zones']['med']
    assert change['precipitation_mm_month']['absolute_maximum'] == pytest.approx(365/120)


def test_new_diagnosis_passes_spinup_only_when_explicitly_requested(monkeypatch):
    from scripts.diagnose_numerics import diagnose
    import rotclimate.model
    calls = []
    class Stopped(Exception):
        pass
    class FakeModel:
        def __init__(self, p):
            pass
        def run(self, **kwargs):
            calls.append(kwargs)
            raise Stopped()
    monkeypatch.setattr(rotclimate.model, 'ClimateModel', FakeModel)
    p, _ = fixture_fields()
    with pytest.raises(Stopped):
        diagnose(p)
    with pytest.raises(Stopped):
        diagnose(p, spinup=50)
    assert 'spinup' not in calls[0]
    assert calls[1]['spinup'] == 50


def test_a_cached_different_warmup_cannot_skip_the_requested_check(monkeypatch, tmp_path):
    from scripts import diagnose_numerics
    p, _ = fixture_fields()
    d = detail(p)
    d.update(spinup_diagnostic_code_id='current', run_settings=dict(
        spinup_steps_requested=25, spinup_steps_observed=25))
    monkeypatch.setattr(spinup, 'load_cached', lambda *args:d)
    calls = []
    def fake_diagnose(params, **kwargs):
        calls.append(kwargs['spinup'])
        return detail(params)
    monkeypatch.setattr(diagnose_numerics, 'diagnose', fake_diagnose)
    spinup.run_case(p, 2, tmp_path, 'model', 'current')
    assert calls == [50]


def test_default_plan_never_launches_or_writes(monkeypatch, tmp_path):
    out = tmp_path/'must-not-exist'
    p = spinup.Params.from_json(spinup.PROFILE)
    monkeypatch.setattr(sys, 'argv', ['check_mediterranean_spinup.py', '--out', str(out)])
    monkeypatch.setattr(spinup, 'load_cached', lambda *args:detail(p))
    def forbidden(*args):
        pytest.fail('Read-only plan must not launch simulations')
    monkeypatch.setattr(spinup, 'run_case', forbidden)
    spinup.main()
    assert not out.exists()


@pytest.mark.parametrize('warmup_years', [1, 2])
def test_existing_model_schedule_repeats_full_years_and_scores_only_last_year(monkeypatch, warmup_years):
    # Exercise calendar/state storage with constant fake solves on nine cells;
    # no real grid, EBM, numerical solver or seasonal climate simulation runs.
    from types import SimpleNamespace
    import rotclimate.model as model_module
    import rotclimate.moisture
    p = spinup.Params(steps_per_year=25, eddy_rate=0, land_amplitude=1, wet_cooling=0, instability=0)
    shape = (3, 3)
    zeros = np.zeros(shape)
    grid = SimpleNamespace(ny=3, nx=3, land=np.ones(shape, bool), lat=zeros+35.,
                           elev=zeros, dx_m=10000., cell_km=10., inmap=np.ones(shape, bool))
    days_seen, progress = [], []
    def land(lat, day):
        days_seen.append(day)
        return zeros + 20. + day / 100.
    model = model_module.ClimateModel.__new__(model_module.ClimateModel)
    model.p, model.g, model.lat = p, grid, grid.lat
    model.z = SimpleNamespace(land=land, ocean=lambda lat,d:zeros+15., zonal=lambda lat,d:zeros+15.)
    model.zonal_wind = lambda season:(zeros, zeros, 10., 25.)
    model.thermal_wind = lambda anomaly:(zeros, zeros)
    model.sst = lambda day,To,Tl:To
    model.col_sigma = model.conv_sigma = 1.
    model.marine_geom = None
    model.trace_cells = None
    model.dhdx = model.dhdy = model.basin_side = zeros
    model.drag = np.ones(shape)
    model.solver = SimpleNamespace(solve=lambda *args,**kwargs:args[5].copy(),converged=[])
    def fake_temperature(solve, initial, *args, **kwargs):
        return SimpleNamespace(temperature=solve(initial, True), update=zeros, iterations=1,
                               converged=True, stages=[])
    monkeypatch.setattr(model_module, 'iterate_temperature', fake_temperature)
    monkeypatch.setattr(rotclimate.moisture, 'solve_moisture', lambda *args,**kwargs:
        SimpleNamespace(water=zeros, rain=zeros+1., iterations=1, converged=True, scaled_residual=0.))
    result = model.run(spinup=warmup_years*25, progress=lambda done,total:progress.append((done,total)))
    expected_days = (np.arange(25)+.5)*365/25
    assert np.allclose(days_seen, np.tile(expected_days, warmup_years+1))
    assert np.allclose(result.T[:,1,1], 20. + expected_days/100.)
    assert result.nt == 25
    assert progress[-1] == ((warmup_years+1)*25, (warmup_years+1)*25)
