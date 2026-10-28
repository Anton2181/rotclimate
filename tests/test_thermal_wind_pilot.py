"""Rainfall-first acceptance must allow regional tradeoffs, not hide failures."""
from scripts.thermal_wind_pilot import score


def fixture():
    regions=['a','b','c'];rows=[];checks={}
    for name in ['legacy_control','legacy_thermal']:
        for region,ratio in zip(regions,[.6,1.05,1.05]):
            rows.append(dict(name=name,region=region,rain=dict(loss=1 if name.endswith('control') else ratio),
                temperature=dict(monthly_mae_C=2 if name.endswith('control') else 2.1)))
            checks[name+'/'+region]=dict(physical_pass=True)
    return rows,checks,dict(base_archives={'legacy':'unused'},regions=regions,
        success=dict(maximum_mean_rain_loss_ratio=.95,maximum_mean_temperature_mae_increase_C=.25))


def test_material_mean_rainfall_gain_can_include_regional_regressions():
    rows,checks,plan=fixture();s=score(rows,checks,plan)['legacy']
    assert s['process_gain'];assert s['regional']['b']['rain_loss_ratio']>1
    assert s['adoption'] is False


def test_temperature_guard_and_missing_or_failed_physics_prevent_claim():
    rows,checks,plan=fixture()
    for row in rows:
        if row['name'].endswith('thermal'):row['temperature']['monthly_mae_C']=2.4
    assert not score(rows,checks,plan)['legacy']['process_gain']
    checks.pop('legacy_thermal/c')
    assert not score(rows,checks,plan)['legacy']['physical_pass']
