from dataclasses import asdict
from rotclimate.config import Params
from scripts.check_surface_momentum import reservoir_failures
from scripts.check_vapor_flux import screening
from test_vapor_flux_gate import cases


def test_environmental_certificate_must_match_global_lapse_at_every_step():
    p=asdict(Params(moisture_reservoirs=True,moisture_residual_tol=.01,
        moisture_reservoir_temperature_profile='environmental',moisture_reservoir_lapse_k_km=6.5))
    cert=dict(all_layer_checks_passed=True,max_scaled_layer_residual=.001,max_scaled_column_residual=.001,
        partition_temperature_profile='environmental',partition_lapse_k_km=6.5,
        steps=[dict(partition_temperature_profile='environmental',partition_lapse_k_km=6.)])
    assert reservoir_failures({'moisture_reservoirs':cert},p)
    cert['steps'][0]['partition_lapse_k_km']=6.5
    assert reservoir_failures({'moisture_reservoirs':cert},p)==[]
    del cert['partition_temperature_profile']
    assert reservoir_failures({'moisture_reservoirs':cert},p)


def test_better_rain_cannot_bypass_independent_thermal_reference_guard(monkeypatch):
    import scripts.check_vapor_flux as module
    plan,rows=cases();plan['require_environmental_partition']=True
    for row in rows:row['params'].update(moisture_reservoir_temperature_profile='environmental',moisture_reservoir_lapse_k_km=6.5)
    monkeypatch.setattr(module,'environmental_reference',lambda p:{'reviews':{'environmental_6.5':{'qualifies':True}}})
    assert screening(rows,plan)['flux_conservative_storm']['qualifies']
    monkeypatch.setattr(module,'environmental_reference',lambda p:{'reviews':{'environmental_6.5':{'qualifies':False}}})
    result=screening(rows,plan)['flux_conservative_storm']
    assert not result['qualifies'] and any('thermal' in f for f in result['failures'])
