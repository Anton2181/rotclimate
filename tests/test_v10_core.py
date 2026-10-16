"""Small manufactured physical tests; no regional climate integrations."""
from dataclasses import replace
import numpy as np
import pytest

from rotclimate_v10.core import (Config,Domain,State,DAY,MONTH_DAYS,CENTERS,advance,air_masses,
    balanced_flow,divergence,initial_state,interpolate_months,stable_step,tracer_flux)
from rotclimate_v10.weather import catalogue,flow_at
from rotclimate_v10.integrate import integrate_year,settling,rain_metrics
from rotclimate_v10.earth import EarthCase


def domain(n=5,land=True):
    shape = (n,n)
    return Domain('manufactured',np.full(shape,land,dtype=bool),np.zeros(shape),
                  np.broadcast_to(np.linspace(42,36,n)[:,None],shape).copy(),np.full((12,)+shape,15.),60000.,60000.)


def zero_flow(d):
    ny,nx = d.land.shape
    x = np.zeros((ny,nx+1));y = np.zeros((ny+1,nx))
    return balanced_flow(x,y,x,y,d.dx,d.dy)


def test_return_flow_preserves_uniform_mixing_ratio_in_closed_box():
    d = domain();c = Config();ml,mu,_ = air_masses(d,c)
    rng = np.random.default_rng(2)
    x = np.zeros((5,6));y = np.zeros((6,5))
    x[:,1:-1] = rng.normal(0,8000,(5,4));y[1:-1,:] = rng.normal(0,8000,(4,5))
    f = balanced_flow(x,y,np.zeros_like(x),np.zeros_like(y),d.dx,d.dy)
    q = .004
    s = State(ml*q,mu*q,np.zeros_like(ml))
    updated,_,budget = advance(s,d,c,f,stable_step(f,ml,mu,d.dx,d.dy,c),0,physics=False)
    np.testing.assert_allclose(updated.lower,s.lower,atol=1e-13)
    np.testing.assert_allclose(updated.upper,s.upper,atol=1e-13)
    assert abs(budget['boundary_export_mm'])<1e-14
    assert abs(budget['water_error_mm'])<1e-13


@pytest.mark.parametrize('sign',[-1,1])
def test_vertical_donor_and_positivity(sign):
    d = domain();c = Config();ml,mu,_ = air_masses(d,c)
    x = np.tile(np.linspace(-5000,5000,6),(5,1))*sign;y = np.zeros((6,5))
    f = balanced_flow(x,y,np.zeros_like(x),np.zeros_like(y),d.dx,d.dy)
    s = State(np.full((5,5),.1),np.full((5,5),10.),np.zeros((5,5)))
    dt = stable_step(f,ml,mu,d.dx,d.dy,c)
    updated,_,budget = advance(s,d,c,f,dt,0,physics=False)
    assert updated.lower.min()>=0 and updated.upper.min()>=0
    assert abs(budget['water_error_mm'])<1e-12
    with pytest.raises(ValueError,match='CFL'):
        advance(s,d,c,f,dt*1.01,0,physics=False)


def test_open_boundary_ledger_and_inflow_donor():
    d = domain();c = Config();ml,mu,_ = air_masses(d,c)
    x = np.full((5,6),20000.);y = np.zeros((6,5))
    f = balanced_flow(x,y,x,y,d.dx,d.dy)
    s = State(np.zeros((5,5)),np.zeros((5,5)),np.zeros((5,5)))
    updated,_,b = advance(s,d,c,f,100.,0,physics=False)
    assert updated.lower[:,0].min()>0
    assert b['boundary_export_mm']<0
    assert abs(b['inventory_change_mm']+b['boundary_export_mm'])<1e-13


def test_reject_noncontinuous_column():
    d = domain();x = np.zeros((5,6));y = np.zeros((6,5))
    bad = x.copy();bad[:,2] = 100.
    with pytest.raises(ValueError,match='continuity'):
        balanced_flow(x,y,bad,y,d.dx,d.dy)


@pytest.mark.parametrize('land',[True,False])
def test_rain_storage_and_runoff_ledger(land):
    d = domain(land=land);c = Config()
    s = State(np.full((5,5),200.),np.full((5,5),100.),np.full((5,5),149. if land else 0.))
    updated,rain,b = advance(s,d,c,zero_flow(d),3600,0)
    assert rain.min()>0
    assert abs(b['water_error_mm'])<1e-11
    if land:
        assert b['runoff_mm']>0 and b['ocean_rain_mm']==0
        np.testing.assert_allclose(updated.soil,c.soil_capacity_mm)
    else:
        assert b['ocean_rain_mm']>0 and b['runoff_mm']==0
        assert updated.soil.max()==0


def test_land_evaporation_is_internal_and_ocean_evaporation_external():
    c = Config()
    for land in (True,False):
        d = domain(land=land);s = initial_state(d,c)
        s.lower *= .1;s.upper *= .1
        _,rain,b = advance(s,d,c,zero_flow(d),3600,0)
        assert rain.max()==0
        if land:
            assert b['land_evaporation_mm']>0
            assert abs(b['inventory_change_mm'])<1e-12
        else:
            assert b['ocean_evaporation_mm']>0
            assert abs(b['inventory_change_mm']-b['ocean_evaporation_mm'])<1e-12


def test_weather_determinism_mass_continuity_and_topography():
    d = domain();d.elevation_m[2,2] = 2500.;c = Config()
    events = catalogue(d,c)
    assert events==catalogue(d,c)
    f = flow_at(d,c,events,20*DAY)
    np.testing.assert_allclose(divergence(f.lower_x+f.upper_x,f.lower_y+f.upper_y,d.dx,d.dy),0,atol=1e-14)
    np.testing.assert_allclose(divergence(f.lower_x,f.lower_y,d.dx,d.dy)+f.vertical,0,atol=1e-14)
    np.testing.assert_allclose(divergence(f.upper_x,f.upper_y,d.dx,d.dy)-f.vertical,0,atol=1e-14)
    repeat = flow_at(d,c,events,385*DAY)
    np.testing.assert_array_equal(f.lower_x,repeat.lower_x)
    assert abs(f.vertical).max()>0


def test_months_wrap_and_interpolate_at_centres():
    a = np.arange(12.)
    for i,t in enumerate(CENTERS):assert interpolate_months(a,t)==i
    assert interpolate_months(a,0)==interpolate_months(a,365*DAY)


def test_manufactured_transport_refines_towards_analytic_translation():
    def error(n):
        dx = 1/n;dt = .4*dx;steps = round(.2/dt)
        x = (np.arange(n)+.5)*dx
        q = np.broadcast_to(2+np.sin(2*np.pi*x),(2,n)).copy()
        fx = np.ones((2,n+1));fy = np.zeros((3,n));mass = np.ones((2,n))
        for k in range(steps):
            boundary = np.broadcast_to(2+np.sin(2*np.pi*(x-k*dt)),(2,n))
            a,b = tracer_flux(q,mass,fx,fy,boundary)
            q -= dt*divergence(a,b,dx,1.)
        exact = 2+np.sin(2*np.pi*(x-steps*dt))
        return abs(q[0,n//3:-1]-exact[n//3:-1]).mean()
    errors = [error(n) for n in (50,100,200)]
    assert errors[1]<errors[0]*.6 and errors[2]<errors[1]*.6


def test_tiny_zero_flow_year_counts_real_months_and_closes_budget():
    d = domain(2,land=False)
    c = replace(Config(),max_step_s=DAY,forcing_interval_s=DAY,background_wind_ms=0,
                storm_rate_month=0,bulk_exchange_coefficient=0,land_pet_mm_day=0)
    s = initial_state(d,c)
    months = []
    r = integrate_year(d,c,s,storms=False,progress=lambda m,steps:months.append((m,steps)))
    assert r.budget['steps']==365 and len(months)==12
    assert months[0][1]==31 and months[1][1]==59
    assert abs(r.budget['annual_water_error_mm'])<1e-12 and r.rain_mm.max()==0
    assert settling(r,r,np.ones((2,2),dtype=bool))['passed']


def test_observed_rain_does_not_enter_engine_and_temperature_is_not_scored():
    d = domain();mask = d.land
    case = EarthCase(d,np.zeros((5,5)),np.ones((12,5,5))*10,mask,np.ones((5,5))*60,np.zeros((5,5),bool))
    rain = np.ones((12,5,5))*11
    m = rain_metrics(case,rain)
    assert m['monthly_mae_mm']==1 and m['annual_bias_mm']==12
    assert 'temperature' not in str(m)
    assert 'rain' not in Domain.__dataclass_fields__
