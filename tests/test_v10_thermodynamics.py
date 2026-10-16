"""Manufactured energy/phase-change and orchestration tests. No Earth runs."""
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pytest

from rotclimate_v10.core import Config,Domain,State,DAY,balanced_flow,air_masses,stable_step
from rotclimate_v10.earth import EarthCase
from rotclimate_v10.integrate import YearResult
from experiments import v10_thermodynamics as h
from scripts import check_v10_thermodynamics as runner
from scripts import diagnose_v10_pilot as diagnosis


def case():
    land = np.ones((3,3),bool)
    d = Domain('fake',land,np.zeros((3,3)),np.broadcast_to(np.array([42.,41.,40.])[:,None],(3,3)).copy(),
               np.full((12,3,3),15.),60000.,60000.)
    return EarthCase(d,np.broadcast_to(np.array([-7.,-6.,-5.]),(3,3)).copy(),np.full((12,3,3),10.),
                     land,np.full((3,3),100.),np.zeros((3,3),bool))


def zero_flow(d):
    y,x = d.land.shape;fx = np.zeros((y,x+1));fy = np.zeros((y+1,x))
    return balanced_flow(fx,fy,fx,fy,d.dx,d.dy)


def fake_result(d,c,state):
    shape = (12,)+d.land.shape;reference = np.full(shape,15.)
    budget = {'annual_water_error_mm':0.,'max_step_water_error_mm':0.,'annual_energy_error_j_m2':0.,
              'max_step_energy_error_j_m2':0.,'max_air_continuity_kg_m2_s':0.,'min_store_mm':0.}
    return h.ThermalYear(state,np.full(shape,10.),reference+c.lower_temperature_offset_c,
                         reference+c.upper_temperature_offset_c,reference,budget)


@pytest.mark.parametrize('raw,ratio,pressure',[(10.,.025,85000.),(-20.,.01,38000.),(25.,.03,90000.)])
def test_saturation_retains_latent_heating_and_condenses_less_than_isothermal(raw,ratio,pressure):
    mass = np.ones((2,2))*2500;water = mass*ratio;z = np.ones((2,2))*1000
    energy = mass*(h.CP*(raw+273.15)+h.G*z)+h.LV*water
    remaining,rain,t = h.adjust(water,energy,mass,z,pressure)
    assert rain.min()>0 and t.min()>raw
    np.testing.assert_allclose(remaining/mass,h.saturation(t,pressure),atol=1e-12)
    np.testing.assert_allclose(h.CP*mass*(t-raw),h.LV*rain,atol=1e-7)
    np.testing.assert_allclose(mass*(h.CP*(t+273.15)+h.G*z)+h.LV*remaining,energy,atol=1e-6)
    assert (rain<mass*(ratio-h.saturation(raw,pressure))).all()


def test_unsaturated_parcel_unchanged():
    mass = np.array([[2000.]]);water = np.array([[2.]]);z = np.array([[1000.]])
    energy = mass*(h.CP*280+h.G*z)+h.LV*water
    after,rain,t = h.adjust(water,energy,mass,z,85000.)
    np.testing.assert_array_equal(after,water);assert rain.max()==0
    np.testing.assert_allclose(t,6.85,atol=1e-12)


def test_dry_static_energy_accounts_for_adiabatic_height_change():
    mass = np.ones((1,1))*2500;water = np.ones((1,1))
    energy = mass*h.CP*290+h.LV*water
    lower = h.temperature(energy,mass,water,np.zeros((1,1)))
    lifted = h.temperature(energy,mass,water,np.full((1,1),1000.))
    np.testing.assert_allclose(lower-lifted,h.G*1000/h.CP)


def test_closed_return_flow_preserves_uniform_mse_and_water_mixing_ratio():
    c = Config();d = case().domain;ml,mu,_ = air_masses(d,c)
    fx = np.zeros((3,4));fy = np.zeros((4,3));fx[:,1:-1] = [[2000,-3000],[1500,2500],[-1000,3000]]
    f = balanced_flow(fx,fy,np.zeros_like(fx),fy,d.dx,d.dy)
    state = h.initial_state(d,c)
    state.water = State(ml*.002,mu*.002,np.zeros((3,3)))
    state.lower_energy = ml*320000;state.upper_energy = mu*320000
    dt = stable_step(f,ml,mu,d.dx,d.dy,c)
    new,rain,_,_,b = h.advance(state,d,c,h.Closure(),f,dt,0,physics=False)
    np.testing.assert_allclose(new.lower_energy,state.lower_energy,atol=1e-6)
    np.testing.assert_allclose(new.upper_energy,state.upper_energy,atol=1e-6)
    np.testing.assert_allclose(new.water.lower,state.water.lower,atol=1e-13)
    assert abs(b['energy_error_j_m2'])<1e-6 and abs(b['water_error_mm'])<1e-12 and rain.max()==0


def test_open_energy_boundary_is_counted_with_water():
    c = Config();d = case().domain;ml,mu,_ = air_masses(d,c)
    fx = np.full((3,4),10000.);fy = np.zeros((4,3));f = balanced_flow(fx,fy,fx,fy,d.dx,d.dy)
    state = h.initial_state(d,c);state.lower_energy *= 1.001
    new,_,_,_,b = h.advance(state,d,c,h.Closure(),f,100.,0.,physics=False)
    assert abs(b['energy_boundary_export_j_m2'])>0
    assert abs(b['energy_inventory_change_j_m2']+b['energy_boundary_export_j_m2'])<1e-6
    assert abs(b['water_error_mm'])<1e-12


@pytest.mark.parametrize('land',[True,False])
def test_evaporation_and_saturation_close_both_ledgers(land):
    c = replace(Config(),bulk_exchange_coefficient=.0012);d = case().domain;d.land[:] = land
    s = h.initial_state(d,c)
    ml,mu,ps = air_masses(d,c);zl,zu = h.levels(d,c)
    # Supersaturation while holding initial sensible temperature at reference.
    s.lower_energy += h.LV*ml*.02;s.water.lower += ml*.02
    _,rain,_,_,b = h.advance(s,d,c,h.Closure(),zero_flow(d),3600,0)
    assert rain.min()>0
    assert abs(b['water_error_mm'])<1e-11 and abs(b['energy_error_j_m2'])<1e-5
    assert b['surface_latent_input_j_m2']==pytest.approx(h.LV*(b['ocean_evaporation_mm']+b['land_evaporation_mm']))


def test_finite_relaxation_reservoir_logged():
    c = replace(Config(),bulk_exchange_coefficient=0.,land_pet_mm_day=0.);d = case().domain
    s = h.initial_state(d,c);ml,mu,_ = air_masses(d,c)
    s.lower_energy += 10*h.CP*ml
    _,_,tl,_,b = h.advance(s,d,c,h.Closure(),zero_flow(d),3600,0.)
    expected = (15+c.lower_temperature_offset_c)+10*np.exp(-3600/(5*DAY))
    np.testing.assert_allclose(tl,expected,atol=1e-12)
    assert b['temperature_relaxation_j_m2']<0 and abs(b['energy_error_j_m2'])<1e-5


def test_tiny_manufactured_year_budget_and_monthly_means():
    c = replace(Config(),max_step_s=DAY,forcing_interval_s=DAY,background_wind_ms=0.,storm_rate_month=0.,
                bulk_exchange_coefficient=0.,land_pet_mm_day=0.)
    d = case().domain;s = h.initial_state(d,c)
    r = h.integrate_year(d,c,h.Closure(),s,storms=False)
    assert r.budget['steps']==365 and r.rain_mm.max()==0
    assert abs(r.budget['annual_energy_error_j_m2'])<1e-3 and abs(r.budget['annual_water_error_mm'])<1e-12
    np.testing.assert_allclose(r.lower_temperature_c,12.,atol=1e-11)
    np.testing.assert_allclose(r.reference_temperature_c,15.,atol=1e-11)


def test_unsupported_temperature_fails_without_clipping():
    with pytest.raises(FloatingPointError,match='supported'):
        h.saturation(np.array([100.]),90000.)


def test_checkpoint_resume_and_bad_budget_rejection(tmp_path):
    c = Config();earth = case();calls = []
    def fake(d,c,closure,state,storms,progress):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('interrupted')
        return fake_result(d,c,state)
    with pytest.raises(RuntimeError,match='interrupted'):
        runner.run_case(earth,c,h.Closure(),tmp_path,True,integrator=fake)
    assert (tmp_path/'year1.json').exists() and not (tmp_path/'year2.json').exists()
    calls = []
    def complete(d,c,closure,state,storms,progress):
        calls.append(1);return fake_result(d,c,state)
    summary,_ = runner.run_case(earth,c,h.Closure(),tmp_path,True,integrator=complete)
    assert len(calls)==2 and summary['eligible_for_mechanism_comparison']
    r = fake_result(earth.domain,c,h.initial_state(earth.domain,c));r.budget['annual_energy_error_j_m2'] = 2.
    with pytest.raises(ValueError,match='budget'):runner.save_year(tmp_path,4,r,0.)
    assert not (tmp_path/'year4.json').exists()


def test_temperature_drift_blocks_eligibility_even_with_stable_rain():
    c = Config();earth = case();r = fake_result(earth.domain,c,h.initial_state(earth.domain,c))
    r.lower_temperature_c += 6.
    t = runner.temperature_diagnostics(r,earth,c)
    assert not t['provisional_guard_passed']
    assert t['lower']['monthly_abs_departure_p95_c']==pytest.approx(6.)


def test_default_never_prepares_or_integrates(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'load_verified',lambda *a:pytest.fail('unexpected simulation setup'))
    assert runner.main(['--out',str(tmp_path/'out')])==0 and list(tmp_path.iterdir())==[]


def test_extension_reuses_unchanged_state_and_stops_when_settled(tmp_path):
    earth = case();c = Config();state = h.initial_state(earth.domain,c).water
    previous = YearResult(state,np.full((12,3,3),10.),{})
    calls = []
    def fake(d,c,s,storms,progress):
        assert s is state;calls.append(1)
        b = dict(annual_water_error_mm=0.,max_step_water_error_mm=0.,max_air_continuity_kg_m2_s=0.,min_store_mm=0.)
        return YearResult(state,previous.rain_mm.copy(),b)
    _,check,y = runner.extend_baseline('fake','mean_only',earth,[previous]*3,c,tmp_path,integrator=fake)
    assert len(calls)==1 and y==4 and check['passed']


def test_full_runner_with_fake_integrations_and_original_provenance(tmp_path,monkeypatch):
    c = Config();earth = case();source = tmp_path/'original';source.mkdir();(source/'manifest.json').write_text('{}')
    originals = {}
    for region in ('california','iberia'):
        for mode in ('storms','mean_only'):
            originals[region,mode] = [YearResult(h.initial_state(earth.domain,c).water,np.full((12,3,3),10.),{})]*3
    cases = {region:replace(earth,domain=replace(earth.domain,name=region)) for region in ('california','iberia')}
    monkeypatch.setattr(runner,'load_verified',lambda *a:({'code_sha256':'fixture'},c,cases,originals))
    calls = [];real_run = runner.run_case
    def fake(d,c,closure,state,storms,progress):
        calls.append(1);return fake_result(d,c,state)
    monkeypatch.setattr(runner,'run_case',lambda *a,**kw:real_run(*a,**kw,integrator=fake))
    out = tmp_path/'check'
    assert runner.main(['--run','--source',str(source),'--out',str(out)])==0
    assert len(calls)==24
    result = json.loads((out/'summary.json').read_text())
    assert len(result['cases'])==8 and result['failures']=={} and result['atlas_updated'] is False
    assert len(list(out.glob('*_heat_check.png')))==2
    assert runner.main(['--run','--source',str(source),'--out',str(out)])==0
    assert len(calls)==24
    (out/'manifest.json').write_text('{}')
    assert runner.main(['--run','--source',str(source),'--out',str(out)])==2
    assert len(calls)==24
