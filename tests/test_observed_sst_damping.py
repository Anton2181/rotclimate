"""Actual prescribed SST must drive moisture as well as the ocean heat target."""
import numpy as np
from rotclimate.model import ClimateModel
from scripts.surface_wind_forcing import at_day
from test_earth import _toy_case
from test_transient_orography import strict_params


def setup_model(source, heat_only):
    grid = _toy_case().grid
    grid.obs_sst = np.broadcast_to((21 + 3*np.sin(2*np.pi*np.arange(12)/12))[:, None, None],
                                  (12, grid.ny, grid.nx)).copy()
    grid.obs_sst.flags.writeable = False
    p = strict_params().replace(sst_source=source, sst_damping=.65,
        sst_damping_heat_only=heat_only, inflow_gain=1., inflow_sst=0., sea_ice=0.)
    m = ClimateModel(p, grid=grid)
    m.sst_record = {}
    m.trace_cells = (np.array([12,12]), np.array([4,16])) # one sea, one land
    return m


def test_observed_surface_is_prescribed_for_heat_and_water_despite_model_damping():
    m = setup_model('observed', True)
    before = m.g.obs_sst.tobytes()
    result = m.run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    assert m.g.obs_sst.tobytes() == before
    for record in m.trace:
        expected = at_day(m.g.obs_sst, record['day'], m.p.year_days)
        np.testing.assert_array_equal(m.sst_record[round(record['day'], 6)], expected)
        np.testing.assert_array_equal(record['SST'], expected[m.trace_cells])
        np.testing.assert_array_equal(record['Teq'][0], expected[12,4])
    # This flag describes a correction of modeled SST. It must have no physical
    # effect when the entire sea surface has been prescribed independently.
    other = setup_model('observed', False).run(diagnose_moisture=True)
    assert other.numerics['all_checks_passed']
    for name in ['T','Tsl','P','W','E','u','v','snow']:
        a,b=getattr(result,name),getattr(other,name)
        assert a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes(),name
    for name in result.moisture_budget:
        a,b=result.moisture_budget[name],other.moisture_budget[name]
        assert a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes(),name


def test_model_surface_keeps_existing_heat_only_undamped_moisture_temperature():
    m = setup_model('model', True)
    result = m.run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    p=m.p
    for record in m.trace:
        day=record['day']
        undamped=m.z.sea(m.lat,day,p.sst_offset,0.,p.sst_damping_lat,p.sst_tropical,p.sst_tropical_lat)
        delta=undamped-m._zonal_sea(m.lat,day)
        expected=m.sst_record[round(day,6)]+delta
        np.testing.assert_array_equal(record['SST'],expected[m.trace_cells])
