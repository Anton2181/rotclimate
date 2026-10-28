from scripts.divergent_thermal_pilot import score
from test_thermal_wind_pilot import fixture


def test_profiles_are_separately_compared_to_original_winds():
    rows,checks,plan=fixture()
    for row in list(rows):
        if row['name']=='legacy_thermal':
            clone=dict(row,name='legacy_single',rain=dict(loss=2.))
            rows.append(clone);checks['legacy_single/'+row['region']]=dict(physical_pass=True)
    result=score(rows,checks,plan)
    assert result['legacy_thermal']['process_gain']
    assert not result['legacy_single']['process_gain']
    assert result['legacy_thermal']['regional']['b']['rain_loss_ratio']>1
    assert result['legacy_thermal']['adoption'] is False


def test_missing_physical_result_cannot_support_a_candidate():
    rows,checks,plan=fixture();checks.pop('legacy_thermal/a')
    assert not score(rows,checks,plan)['legacy_thermal']['physical_pass']
