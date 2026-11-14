import numpy as np
import pytest

from harvest.reference_eto import daily_reference,extraterrestrial_radiation,penman_monteith,pressure_at_elevation,saturation_vapour_pressure,wind_at_2m


def uccle():
    lo,hi=12.3,21.5
    vap=(saturation_vapour_pressure(lo)*.84+saturation_vapour_pressure(hi)*.63)/2
    solar=extraterrestrial_radiation(50.8,187)
    rs=(.25+.5*9.25/solar['daylight_hours'])*solar['ra_mj_m2_day']
    return daily_reference(16.9,lo,hi,vap,wind_at_2m(10/3.6,10),pressure_at_elevation(100),rs,50.8,187,100)


def test_published_fao18_daily_reference_and_intermediates():
    r=uccle()
    assert r['pm_mm_day']==pytest.approx(3.9,abs=.05)
    assert r['ra_mj_m2_day']==pytest.approx(41.09,abs=.02)
    assert r['es_kpa']==pytest.approx(1.997,abs=.001)
    assert r['ea_kpa']==pytest.approx(1.409,abs=.001)
    assert r['delta_kpa_c']==pytest.approx(.122,abs=.001)
    assert r['gamma_kpa_c']==pytest.approx(.0666,abs=.0001)
    assert r['rns_mj_m2_day']==pytest.approx(17.,abs=.03)
    assert r['rnl_mj_m2_day']==pytest.approx(3.71,abs=.03)
    assert r['rn_mj_m2_day']==pytest.approx(13.28,abs=.03)
    assert r['pm_radiation_mm_day']==pytest.approx(2.81,abs=.02)
    assert r['pm_aerodynamic_mm_day']==pytest.approx(1.07,abs=.02)


def test_published_fao8_southern_hemisphere_radiation():
    assert extraterrestrial_radiation(-20,246)['ra_mj_m2_day']==pytest.approx(32.2,abs=.05)


def test_wind_pressure_and_radiation_units():
    assert wind_at_2m(10/3.6,10)==pytest.approx(2.078,abs=.001)
    assert pressure_at_elevation(100)==pytest.approx(100.1,abs=.05)
    assert .408*extraterrestrial_radiation(-20,246)['ra_mj_m2_day']==pytest.approx(13.1,abs=.05)


def test_zero_demand_and_signed_negative_reference_are_explicit():
    es=saturation_vapour_pressure(20)
    assert penman_monteith(20,es,es,0,100,0)['pm_mm_day']==0
    r=penman_monteith(20,es,es,0,100,-2)
    assert r['pm_raw_mm_day']<0 and r['pm_mm_day']==0


def test_radiation_cloud_clamps_and_hargreaves_identity():
    rs=np.array([0.,100.]);before=rs.copy()
    r=daily_reference(20,10,30,1.,2.,100.,rs,30,180,100)
    np.testing.assert_array_equal(rs,before)
    np.testing.assert_allclose(r['rs_ratio_used'],[.3,1.])
    np.testing.assert_allclose(r['hargreaves_mm_day'],.0023*37.8*np.sqrt(20)*.408*r['ra_mj_m2_day'])
    assert r['rs_ratio_raw'][0]==0 and r['rs_ratio_raw'][1]>1


def test_broadcast_scalar_and_vector_are_identical():
    args=[np.array([15.,20.]),[10.,12.],[20.,28.],[1.,1.1],2.,100.,[12.,18.],30.,[30.,180.],100.]
    many=daily_reference(*args)
    for i in range(2):
        one=daily_reference(*[np.asarray(v)[i] if np.ndim(v) else v for v in args])
        for key,value in many.items():assert value[i]==pytest.approx(one[key],rel=1e-13)


@pytest.mark.parametrize('latitude,day',[(91,180),(-91,180),(30,0),(30,367),(30,1.5),(np.nan,180)])
def test_invalid_solar_inputs_refused(latitude,day):
    with pytest.raises(ValueError):extraterrestrial_radiation(latitude,day)


@pytest.mark.parametrize('change',[
    {'tmean_c':np.nan},{'tmin_c':31},{'tmax_c':19},{'ea_kpa':-1},{'ea_kpa':20},
    {'wind2m_ms':-1},{'pressure_kpa':0},{'solar_mj_m2_day':-1},{'elevation_m':11000},
])
def test_invalid_daily_weather_refused(change):
    args=dict(tmean_c=20,tmin_c=10,tmax_c=30,ea_kpa=1,wind2m_ms=2,pressure_kpa=100,solar_mj_m2_day=20,latitude_deg=30,day_of_year=180,elevation_m=100)
    args.update(change)
    with pytest.raises(ValueError):daily_reference(**args)


def test_unsupported_polar_night_and_invalid_conversion_inputs_refused():
    with pytest.raises(ValueError):daily_reference(-20,-25,-15,.05,2,100,0,90,355,0)
    with pytest.raises(ValueError):wind_at_2m(-1,10)
    with pytest.raises(ValueError):wind_at_2m(2,0)
    with pytest.raises(ValueError):pressure_at_elevation(-1000)
    with pytest.raises(ValueError):saturation_vapour_pressure(-240)
