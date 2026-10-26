import numpy as np
import pytest
from dataclasses import asdict
from rotclimate.config import Params
from scripts.circulation_reference import layer_partial_water,humidity_scores,humidity_protection
from scripts.check_surface_momentum import reservoir_failures


def test_matched_pressure_water_has_independent_piecewise_analytic_solution():
    ps=np.full((2,3),100000.)
    q=np.array([.01,.002])[None,:,None,None]
    water=q*np.stack([.25*ps,.75*ps])[None]/9.80665
    np.testing.assert_allclose(layer_partial_water(water,ps),265/9.80665)
    lower=layer_partial_water(water,ps,92500,70000)
    upper=layer_partial_water(water,ps,70000,30000)
    np.testing.assert_allclose(lower,185/9.80665)
    np.testing.assert_allclose(upper,80/9.80665)
    np.testing.assert_allclose(lower+upper,layer_partial_water(water,ps))
    # A full-column ratio is intentionally different from the matched partial ratio.
    np.testing.assert_allclose((upper/40000)/(lower/22500),.24324324324324323)


def test_pressure_overlap_clips_below_ground_without_creating_water():
    ps=np.full((1,1),80000.)
    water=np.ones((1,2,1,1))
    np.testing.assert_allclose(layer_partial_water(water,ps,100000,10000),1.8333333333333333)
    with pytest.raises(ValueError):layer_partial_water(water,ps,30000,92500)
    with pytest.raises(ValueError):layer_partial_water(-water,ps)


def test_humidity_scores_and_guard_use_area_and_days_and_cannot_trade_shape_for_water():
    water=np.ones((12,2));ratio=water*.25
    days=np.arange(1,13);area=np.array([1.,3.])
    score=humidity_scores(water+np.array([0,2]),water,ratio+.1,ratio,area,days)
    assert score['partial_water_mae_mm']==pytest.approx(1.5)
    assert score['partial_q_ratio_mae']==pytest.approx(.1)
    assert humidity_protection(score,score)['passed']
    worse=dict(score,partial_water_mae_mm=.1,partial_q_ratio_mae=.103)
    assert not humidity_protection(worse,score)['passed']
    with pytest.raises(ValueError):humidity_protection(dict(score,native_cells=1),score)
    assert not humidity_protection(None,score)['passed']
    assert not humidity_protection(dict(score,partial_q_ratio_mae=float('nan')),score)['passed']


def test_later_gates_require_independent_layer_and_column_not_just_total_pass_flag():
    p=asdict(Params(moisture_reservoirs=True,moisture_residual_tol=.02))
    c=dict(all_layer_checks_passed=True,steps=[{}],max_scaled_layer_residual=.01,max_scaled_column_residual=.01)
    assert reservoir_failures({'moisture_reservoirs':c},p)==[]
    c['max_scaled_layer_residual']=.03
    assert reservoir_failures({'moisture_reservoirs':c},p)
    assert reservoir_failures({'all_checks_passed':True},p)


def test_good_rainfall_cannot_bypass_native_humidity_or_layer_certificate():
    from test_vapor_flux_gate import cases
    from scripts.check_vapor_flux import screening
    plan,rows=cases()
    plan.update(require_moisture_reservoirs=True,humidity_regions={'iberia':'ocean'},
                humidity_control='reference',humidity_max_ratio=1.02)
    for row in rows:
        row['params'].update(moisture_reservoirs=True,moisture_residual_tol=.02)
        row['numerics']['moisture_reservoirs']=dict(all_layer_checks_passed=True,steps=[{}],
            max_scaled_layer_residual=.01,max_scaled_column_residual=.01)
        row['circulation']=dict(humidity=dict(scores=dict(ocean=dict(native_cells=20,area_km2=100.,
            partial_water_mae_mm=2.,partial_q_ratio_mae=.1))))
    assert screening(rows,plan)['flux_conservative_storm']['qualifies']
    row=next(r for r in rows if r['name']=='flux_conservative_storm' and r['region']=='iberia')
    row['circulation']['humidity']['scores']['ocean']['partial_q_ratio_mae']=.103
    assert not screening(rows,plan)['flux_conservative_storm']['qualifies']
    row['circulation']['humidity']['scores']['ocean']['partial_q_ratio_mae']=.1
    row['numerics']['moisture_reservoirs']['max_scaled_layer_residual']=float('nan')
    assert not screening(rows,plan)['flux_conservative_storm']['qualifies']
