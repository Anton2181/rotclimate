"""Season conventions, additive placement errors and paired numerical effects."""
from types import SimpleNamespace
import numpy as np
import pytest
from scripts import review_v10_cloud_mixing as r


def test_response_seasons_match_frozen_october_march_convention():
    assert set(r.WINTER)=={0,1,2,9,10,11}
    assert set(r.SUMMER)=={3,4,5,6,7,8}
    assert set(r.WINTER).isdisjoint(r.SUMMER) and set(r.WINTER)|set(r.SUMMER)==set(range(12))


def test_regime_error_contributions_sum_to_overall_and_expose_wrong_season():
    mask=np.ones((1,2),bool);arid=np.array([[True,False]]);med=~arid
    observed=np.ones((12,1,2))*10.;old=observed.copy();new=old.copy()
    new[r.SUMMER,0,0]+=20.;new[r.WINTER,0,0]-=5.
    old[:,0,1]=0.;new[:,0,1]=5.
    rows=r.placement(old,new,observed,mask,{'reference_arid':arid,'reference_mediterranean':med})
    total=sum(v['overall_mae_gain_contribution_mm'] for v in rows.values())
    assert total==pytest.approx((abs(old-observed)-abs(new-observed)).mean())
    for v in rows.values():assert v['overall_mae_gain_contribution_mm']==pytest.approx(v['winter_overall_mae_gain_contribution_mm']+v['summer_overall_mae_gain_contribution_mm'])
    assert rows['reference_arid']['new_summer_mm']>rows['reference_arid']['reference_summer_mm']
    assert rows['reference_arid']['new_winter_mm']<rows['reference_arid']['reference_winter_mm']
    assert rows['reference_arid']['overall_mae_gain_contribution_mm']<0


def test_numerical_treatment_gain_cancels_common_bulk_shift():
    mask=np.ones((2,2),bool)
    def record(rain,steps):return (None,np.full((12,2,2),rain),np.ones((12,5,2,2)),None,{'steps':steps})
    result=r.numerical_difference(record(10.,100),record(10.1,200),mask,record(5.,100),record(5.1,200))
    assert result['monthly_rain_difference_p95_mm']==pytest.approx(.1)
    assert result['annual_rain_difference_p95_mm']==pytest.approx(1.2)
    assert result['treatment_gain_change_monthly_p95_mm']==pytest.approx(0.)
    assert result['fine_over_coarse_step_ratio']==2.


def test_reference_regime_masks_partition_scored_land():
    codes=r.run.run.koppen_maps.koppen.CODES
    target=np.array([[codes.index('Csa'),codes.index('BWh'),codes.index('Cfb')]])
    case=SimpleNamespace(score_mask=np.ones((1,3),bool),coast_distance_km=np.array([[50.,200.,400.]]))
    groups=r.groups_for(case,target)
    assert np.all(sum(groups[k].astype(int) for k in ('reference_mediterranean','reference_arid','other_reference_land'))==1)
    assert groups['coast'].sum()==groups['interior'].sum()==1


def test_default_review_does_not_write_output(tmp_path,monkeypatch):
    monkeypatch.setattr(r,'analyse',lambda *a:({}, {}, {}));monkeypatch.setattr(r,'markdown',lambda *a:'review')
    monkeypatch.setattr(r,'plot',lambda *a:pytest.fail('Unexpected output'))
    out=tmp_path/'absent'
    assert r.main(['--out',str(out)])==0 and not out.exists()


def test_review_cannot_overwrite_experiment(tmp_path,monkeypatch):
    monkeypatch.setattr(r,'analyse',lambda *a:({}, {}, {}))
    source=tmp_path/'source'
    with pytest.raises(ValueError,match='Preserve'):r.main(['--source',str(source),'--out',str(source),'--write'])
