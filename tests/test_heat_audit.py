import numpy as np
import pytest

from rotclimate import earth
from rotclimate.config import Params
from rotclimate.model import ClimateModel
from scripts.audit_air_sea_exchange import slab_flux_wm2, equivalent_depth_m, reference_at
from test_earth import _toy_case


@pytest.mark.parametrize('changes', [{}, dict(ocean_tau_stable=.5, ocean_tau_unstable=.5, ocean_unstable_cap=2.)])
def test_recording_last_heat_solve_leaves_every_model_field_identical(changes):
    case = _toy_case()
    p = earth.earth_params(Params.from_json('calibration/local_accuracy_20261023/r44_params.json'),case).replace(steps_per_year=13,**changes)
    plain = ClimateModel(p,case.grid).run()
    model = ClimateModel(p,case.grid); model.heat_record = {}; model.sst_record = {}
    recorded = model.run()
    assert plain.numerics == recorded.numerics
    assert recorded.numerics['all_checks_passed']
    for key in ['T','Tsl','P','W','u','v','E','snow']:
        np.testing.assert_array_equal(getattr(plain,key),getattr(recorded,key))
    assert len(model.heat_record) == len(recorded.days) == 13
    for i,day in enumerate(recorded.days):
        r = model.heat_record[round(float(day),6)]
        np.testing.assert_array_equal(r['surface_c'],model.sst_record[round(float(day),6)])
        np.testing.assert_allclose(r['air_c'],recorded.Tsl[i],atol=3e-6,rtol=0)
        assert all(a.shape == case.grid.land.shape and np.isfinite(a).all() for a in r.values())
        assert np.max(np.abs(r['rate_state_c']-r['air_c'])) < .05
        if not changes:
            np.testing.assert_array_equal(r['lambda_s'][~case.grid.land],np.full((~case.grid.land).sum(),1/(p.ocean_tau_days*86400.)))
    # Records own their arrays, including the solver's float64 result.
    model.heat_record[round(float(recorded.days[0]),6)]['air_c'][:] = 999
    np.testing.assert_array_equal(plain.Tsl,recorded.Tsl)


def test_heat_flux_and_depth_have_the_declared_physical_units():
    rate = 1/86400.
    assert slab_flux_wm2(rate,2.,1000.) == pytest.approx(1.225*1004*1000*2/86400)
    assert slab_flux_wm2(rate,-2.,250.) == pytest.approx(-.25*slab_flux_wm2(rate,2.,1000.))
    assert equivalent_depth_m(rate,10.) == pytest.approx(864.)
    with pytest.raises(ValueError): equivalent_depth_m(0.,10.)


def test_southern_reference_rotates_months_and_reverses_only_northward_wind():
    from types import SimpleNamespace
    # Spatially uniform references make this an exact calendar/frame test,
    # independent of interpolation details or external files.
    a = np.broadcast_to(np.arange(12.)[:,None,None],(12,73,144)).copy()
    g = SimpleNamespace(lat=np.array([[30.]]))
    south = reference_at(SimpleNamespace(name='chile',grid=g,lon=np.array([[-70.]])),dict(air=a,u=a+10,v=a+20))
    expected = np.roll(np.arange(12.),6)
    np.testing.assert_array_equal(south['air'][:,0,0],expected)
    np.testing.assert_array_equal(south['u'][:,0,0],expected+10)
    np.testing.assert_array_equal(south['v'][:,0,0],-(expected+20))


def test_static_reference_decodes_length_one_attributes_and_checks_cached_bytes(tmp_path, monkeypatch):
    import h5py
    from scripts import audit_air_sea_exchange as audit
    monkeypatch.setattr(audit,'REFERENCE',tmp_path)
    for prefix in ['air','uwnd','vwnd']:
        with h5py.File(tmp_path/(prefix+'.sig995.mon.ltm.nc'),'w') as f:
            time=f.create_dataset('time',data=np.arange(12));time.attrs['climo_period']=b'1991/01/01 - 2020/12/31'
            f.create_dataset('lat',data=90-2.5*np.arange(73));f.create_dataset('lon',data=2.5*np.arange(144))
            var=f.create_dataset(prefix,data=np.full((12,73,144),2.,dtype=np.float32))
            var.attrs['level_desc']=b'0.995 sigma';var.attrs['units']=b'degC' if prefix=='air' else b'm/s'
            var.attrs['scale_factor']=np.array([2.]);var.attrs['add_offset']=np.array([-1.])
    archive,receipt=audit.prepare_reference()
    with np.load(archive) as f:
        for key in ['air','u','v']: np.testing.assert_array_equal(f[key],np.full((12,73,144),3.))
    assert receipt['period']=='1991-2020'
    archive.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Changed reference'):audit.prepare_reference()
