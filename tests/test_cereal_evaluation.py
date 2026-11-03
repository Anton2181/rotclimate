import numpy as np

from scripts.evaluate_cereal_phenology import daily_temperature,daylight_hours,evaluation_country,heat_requirements,metrics


def test_evaluation_targets_cannot_change_training_selection(tmp_path,monkeypatch):
    import scripts.evaluate_cereal_phenology as driver
    monkeypatch.setattr(driver,'OUT',tmp_path)
    (tmp_path/'inputs.json').write_text('{}')
    rows=[dict(id='train',country='a',evaluation=False,growing_days=11),
          dict(id='eval',country='b',evaluation=True,growing_days=100)]
    forcing=dict(temperature=np.zeros((365,2)),annual_temperature=np.zeros(2))
    def prediction(rows,forcing,*,scale,chilling):
        assert all(not r['evaluation'] for r in rows)
        return np.full(len(rows),int(scale*10))
    monkeypatch.setattr(driver,'predict',prediction)
    plan={'tuning':{'heat_scales':[.8,1.2],'winter_chilling_days':[15.]}}
    import json
    driver.select(plan,rows,forcing)
    first=json.loads((tmp_path/'selection.json').read_text())['selected']
    rows[1]['growing_days']=8
    driver.select(plan,rows,forcing)
    assert json.loads((tmp_path/'selection.json').read_text())['selected']==first
    assert first['scale']==1.2


def test_periodic_monthly_interpolation_and_southern_daylight_have_consistent_phase():
    np.testing.assert_allclose(daily_temperature(np.full((12,2),15)),15)
    light=daylight_hours([45,-45,0])
    assert light[171,0]>light[354,0] and light[171,1]<light[354,1]
    np.testing.assert_allclose(light[:,2],12)
    np.testing.assert_allclose(light[:,0]+light[:,1],24)


def test_nonmaturity_is_penalized_and_country_weighting_does_not_reward_replication():
    rows=[dict(country='a',growing_days=100),dict(country='a',growing_days=100),dict(country='b',growing_days=100)]
    result=metrics(rows,np.array([100,100,-1]))
    assert result['country_mean_penalized_error_days']==182.5
    assert result['nonmature_records']==1 and result['mature_only_mae_days']==0


def test_shared_cultivar_adaptation_stays_inside_published_heat_ranges():
    rows=[dict(winter=True,planting_median=300,lat=40),dict(winter=False,planting_median=90,lat=40)]
    for scale in [.8,1,1.2]:
        h=heat_requirements(rows,np.array([-5,35]),scale)
        assert 1700<=h[0]<=2876.9 and 1000<=h[1]<=2648.4
