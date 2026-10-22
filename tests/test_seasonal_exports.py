from types import SimpleNamespace
import numpy as np
from rotclimate.climate_fields import lapse_at_days
from rotclimate.config import Params
from rotclimate.koppen import monthly_weights
from rotclimate.render import FullRes
from rotclimate.analogs import model_bins


def fixture():
    p=Params(lapse_rate=6., lapse_seasonal=.25, steps_per_year=25)
    days=(np.arange(25)+.5)*p.year_days/25
    r=SimpleNamespace(params=p, days=days, Tsl=np.full((25,1,2),20.), P=np.ones((25,1,2)))
    fr=FullRes.__new__(FullRes); fr.r=r; fr._lapse=p.lapse_rate
    fr.land=np.array([[True,False]]); fr.elev=np.array([[2000.,0.]])
    fr.up=lambda a,land_fill=True: np.asarray(a)
    return p,r,fr


def test_seasonal_mountain_temperature_and_unchanged_sea():
    p,r,fr=fixture()
    winter=p.winter_solstice_day+p.circulation_lag_days
    summer=winter+p.year_days/2
    assert np.allclose(fr.temperature(r.Tsl[0],days=winter), [[11,20]])
    assert np.allclose(fr.temperature(r.Tsl[0],days=summer), [[5,20]])
    assert np.allclose(lapse_at_days(p.replace(lapse_seasonal=0),r.days),6)


def test_monthly_export_equals_aggregated_surface_temperatures():
    p,r,fr=fixture()
    direct=np.stack([fr.temperature(t,days=d) for t,d in zip(r.Tsl,r.days)])
    expected=(monthly_weights(r.days,p.year_days) @ direct.reshape(25,-1)).reshape(12,1,2)
    assert np.allclose(fr.monthly()[0], expected)


def test_solstice_bins_apply_the_same_seasonal_correction_as_surface_fields():
    p,r,fr=fixture()
    rates=lapse_at_days(p,r.days)[:,None,None]
    sl,_=model_bins(r.Tsl,r.P,r.days,p.winter_solstice_day,p.year_days)
    lr,_=model_bins(rates,np.zeros_like(rates),r.days,p.winter_solstice_day,p.year_days)
    surface=r.Tsl-rates*fr.elev/1000
    expected,_=model_bins(surface,r.P,r.days,p.winter_solstice_day,p.year_days)
    assert np.allclose(sl-lr*fr.elev/1000,expected)
