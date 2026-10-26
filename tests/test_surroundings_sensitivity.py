import numpy as np
import pytest
from types import SimpleNamespace
from rotclimate.config import Params
from scripts.add_surroundings_sensitivity import sample_spread,physical_key,projected_temperature


def test_streaming_spread_matches_sample_variance():
    fields=np.array([[[1.,2.],[3.,4.]],[[2.,4.],[6.,8.]],[[4.,5.],[8.,9.]]])
    mean,std,count=sample_spread(iter(fields))
    assert count==3
    np.testing.assert_allclose(mean,fields.mean(0))
    np.testing.assert_allclose(std,fields.std(0,ddof=1))


def test_projection_covariance_must_be_preserved_before_computing_spread():
    # Two opposite anomalies cancel when the displayed point interpolates
    # both cells. Interpolating the two nonzero cell deviations would be wrong.
    fields=np.array([[0.,2.],[2.,0.]])
    _,displayed_std,_=sample_spread([np.array([row.mean()]) for row in fields])
    assert displayed_std[0]==0
    assert fields.std(0,ddof=1).mean()>0


def test_physical_fingerprint_allows_only_resolution_and_layout_changes():
    p=Params()
    assert physical_key(p)==physical_key(p.replace(downsample=16,beyond_seed=490101))
    assert physical_key(p)!=physical_key(p.replace(solar_flux=1.01))
    assert physical_key(p)!=physical_key(p.replace(north_bearing=p.north_bearing+1))


def test_fixed_source_lapse_correction_cannot_add_outside_elevation_spread():
    p=Params();days=np.arange(25)*p.year_days/25
    common=dict(params=p,days=days,Tsl=np.full((25,2,2),15.),P=np.ones((25,2,2)))
    a=SimpleNamespace(**common,T=np.full((25,2,2),-10.))
    b=SimpleNamespace(**common,T=np.full((25,2,2),5.))
    fr=SimpleNamespace(up=lambda values:values)
    np.testing.assert_allclose(projected_temperature(a,fr),15.)
    _,spread,_=sample_spread([projected_temperature(a,fr),projected_temperature(b,fr)])
    np.testing.assert_allclose(spread,0.)


def test_sample_size_and_finite_fields_are_required():
    with pytest.raises(ValueError):sample_spread([np.array([1.])])
    with pytest.raises(ValueError):sample_spread([np.array([1.]),np.array([float('nan')])])
