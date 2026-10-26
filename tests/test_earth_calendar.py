import numpy as np
import pytest
from scripts.earth_calendar import MONTH_DAYS,observation_weights,monthly_stats
from rotclimate.koppen import monthly_stats as legacy_stats


@pytest.mark.parametrize('steps',[13,25,73,365])
@pytest.mark.parametrize('mirrored',[False,True])
def test_constant_daily_rain_integrates_to_actual_observation_month_lengths(steps,mirrored):
    days=(np.arange(steps)+.5)*365/steps
    values=np.ones((steps,2,3))
    result=monthly_stats(values*15,values,days,mirrored=mirrored)
    order=(np.arange(12)+(6 if mirrored else 0))%12
    np.testing.assert_allclose(result['Pm'],np.broadcast_to(MONTH_DAYS[order,None,None],(12,2,3)),atol=1e-12)
    np.testing.assert_allclose(result['Tm'],15,atol=1e-12)
    np.testing.assert_allclose(result['Pm'].sum(0),365,atol=1e-12)


@pytest.mark.parametrize('mirrored',[False,True])
def test_calendar_change_preserves_annual_rain_integral_and_day_weighted_temperature(mirrored):
    rng=np.random.default_rng(382)
    days=(np.arange(73)+.5)*5
    T=rng.normal(12,10,(73,4,5));P=rng.uniform(0,10,T.shape)
    result=monthly_stats(T,P,days,mirrored=mirrored)
    old=legacy_stats(T,P,days)
    np.testing.assert_allclose(result['Pm'].sum(0),old['Pm'].sum(0),atol=1e-10)
    weighted=(result['Tm']*result['month_days'][:,None,None]).sum(0)/365
    np.testing.assert_allclose(weighted,T.mean(0),atol=1e-12)


def test_mirrored_july_boundary_wraps_across_model_year_instead_of_dropping_rain():
    days=np.arange(365)+.5
    rain=np.zeros((365,1));rain[-1]=1
    result=monthly_stats(rain,rain,days,mirrored=True)
    assert result['original_month'][0]==6
    assert result['Pm'][0,0]==pytest.approx(1)
    assert result['Pm'].sum()==pytest.approx(1)


@pytest.mark.parametrize('days',[[np.nan],[],[0,5,10],[2.5,8,12.5],[[2.5]]])
def test_irregular_or_incomplete_model_calendar_is_rejected(days):
    with pytest.raises(ValueError):observation_weights(days)
