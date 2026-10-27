"""Manufactured conservative geography and resource-adapter tests."""
import numpy as np
import pytest
from foraging.export import area_average, land_average, pack_fields, aggregates
from foraging.forcing import daily_resources, miami_npp


def adapter():
    return dict(grass_npp_fraction=.5,annual_meat_fraction_of_npp=.0005,
                phenology_temperature_floor_c=0.,phenology_temperature_span_c=15.,
                phenology_rain_half_saturation_mm=50.)


def test_noninteger_grid_overlap_conserves_area_and_constant_fields():
    values=np.arange(35,dtype=float).reshape(5,7)
    coarse=area_average(values,(3,4))
    np.testing.assert_allclose(coarse.mean(),values.mean(),rtol=1e-14)
    np.testing.assert_allclose(area_average(np.ones((12,5,7)),(3,4)),1.)
    land=np.ones((5,7));land[:2,:3]=.25;land[2:4,3:5]=0.
    result=land_average(values,land,(3,4));fraction=area_average(land,(3,4))
    np.testing.assert_allclose((result*fraction).mean(),(values*land).mean(),rtol=1e-14)


def test_daily_forcing_preserves_published_annual_plant_allocation_and_proxy_prey():
    t=np.full((12,2),20.);p=np.full_like(t,50.);npp=np.array([1000.,500.])
    f=daily_resources(t,p,npp,adapter())
    below=max(.2,(88.3-.0534*600)/100)
    expected=npp*1000*.015*(.065+below*.5)
    np.testing.assert_allclose(f['plant_supply'].sum(0),expected,rtol=2e-14)
    np.testing.assert_allclose(f['meat_supply'][0],npp*.5)
    assert (f['meat_supply'][1:]==0).all()
    assert not f['phenology_uniform_fallback'].any()


def test_frozen_climate_fallback_does_not_create_or_discard_annual_resources():
    t=np.full((12,1),-10.);p=np.full_like(t,10.)
    npp=miami_npp(t,p);f=daily_resources(t,p,npp,adapter())
    assert f['phenology_uniform_fallback'][0]
    np.testing.assert_allclose(f['plant_supply'],np.broadcast_to(f['annual_plant_kgdm_km2']/365,(365,1)))
    with pytest.raises(ValueError):daily_resources(t,-p,npp,adapter())


def test_float_packet_distinguishes_real_zero_from_ocean(tmp_path):
    land=np.array([[False,True],[True,True]])
    value=np.array([[0.,0.],[.1234,10.]])
    specs=pack_fields({'density_people_km2':value,'converged':land},land,tmp_path/'foraging.bin')
    blob=(tmp_path/'foraging.bin').read_bytes()
    floats=np.frombuffer(blob,dtype='<f4',count=4).reshape(2,2)
    assert np.isnan(floats[0,0]) and floats[0,1]==0.
    s=specs['converged'];flags=np.frombuffer(blob,dtype='u1',count=4,offset=s['offset_bytes']).reshape(2,2)
    assert flags[0,0]==255 and (flags[land]==1).all()


def test_fractional_provinces_conserve_population_without_discarding_unconverged_cells():
    fraction=np.array([[1.,.5],[.2,0.]])
    fields={name:np.zeros((2,2)) for name in ['unsupported','foraging_hours_day','scarcity_days_year','meat_fraction']}
    fields.update(density_people_km2=np.array([[2.,4.],[3.,0.]]),converged=np.array([[True,False],[True,False]]))
    provinces=np.stack([fraction*.3,fraction*.7])
    summary,rows=aggregates(fields,fraction,10.,['A','B'],provinces)
    assert summary['total_scenario_people']==46.
    assert summary['converged_scenario_people']==26.
    np.testing.assert_allclose(sum(p['scenario_people'] for p in rows),46.)
    np.testing.assert_allclose(sum(p['area_km2'] for p in rows),17.)
