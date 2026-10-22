import numpy as np

from harvest.models import (malaria_fields, malaria_thermal, occupation_reference,
                            settlement_fields, thermal_reference)
from scripts.land_people import best_crop_mix


def test_published_malaria_curve_has_cooler_peak_and_fails_outside_thermal_limits():
    assert 25 < thermal_reference()[1] < 26
    t = np.array([0., 15., 20., 25.57, 30., 35., 50.])
    r = malaria_thermal(t)
    assert r[0] == r[1] == r[5] == r[6] == 0
    assert r[3] > .999 and r[2] < r[3] and r[4] < r[3]
    # A cold map must not rescale itself to look as suitable as a tropical map.
    np.testing.assert_allclose(malaria_thermal([20.]), r[2:3])


def test_rain_and_irrigation_change_habitat_without_creating_risk_in_freezing_weather():
    warm = np.full((12, 1), 25.57)
    dry = np.zeros((12, 1)); wet = np.full((12, 1), 80.)
    a = malaria_fields(warm, dry, [0.])
    b = malaria_fields(warm, dry, [1.])
    c = malaria_fields(warm, wet, [0.])
    assert a['malaria'][0] == 0 < b['malaria'][0] < c['malaria'][0] <= 1
    assert c['malaria_months'][0] == 12
    assert malaria_fields(warm-40, wet, [1.])['malaria'][0] == 0


def test_settlement_scenarios_respect_food_budget_and_disease_removal():
    a = settlement_fields(np.array([0., 100., 200.]), np.array([0., 800., 1500.]),
                          np.array([8, 8, 4]), np.array([.5, .5, .85]),
                          np.array([np.inf, 20., 0.]), np.array([0., .5, 1.]))
    np.testing.assert_allclose(a['food_capacity'], a['crop_capacity']+a['pastoral_capacity'])
    assert np.all(a['settlement_base'] <= a['settlement_no_malaria'])
    assert np.all(a['settlement_no_malaria'] <= a['food_capacity'])
    assert np.all((a['livability'] >= 0) & (a['livability'] <= 100))
    assert a['settlement_base'][0] == a['livability'][0] == 0
    assert a['pastoral_capacity'][1] > 0
    fractions = list(occupation_reference()['scenarios'].values())
    assert 0 < fractions[0] < fractions[1] < fractions[2] <= 1
    coast = settlement_fields(np.array([100.,100.]),np.array([1000.,1000.]),
                              np.array([0,255]),np.array([.5,.5]),np.array([0.,0.]),np.array([0.,0.]))
    for value in coast.values():
        assert value[0] == value[1]  # coastal missing biomes use the neutral outside-diagram scenario


def test_secondary_crop_updates_the_primary_label_and_requires_a_disjoint_season():
    kcal = {'wheat':np.array([10.]), 'millet':np.array([9.]), 'rice':np.array([12.])}
    masks = {name:np.zeros((12, 1), bool) for name in kcal}
    masks['wheat'][:6] = True; masks['millet'][6:] = True; masks['rice'][:] = True
    total, primary, secondary = best_crop_mix(kcal, masks, np.array([True]))
    np.testing.assert_allclose(total, [14.5])
    assert primary[0] == 0 and secondary[0] == 1
    total, primary, secondary = best_crop_mix(kcal, masks, np.array([False]))
    assert total[0] == 12 and primary[0] == 2 and secondary[0] == -1


def test_portable_quantizer_keeps_real_zero_distinct_from_ocean(tmp_path):
    from harvest.export import pack_fields
    # Interoperability: decode the descriptor exactly as the browser does.
    names=['crop_capacity','pastoral_capacity','food_capacity','kcal_ha','lgp_days','npp','irr',
           'aridity','malaria','malaria_months','clearance','access','health','settlement_base',
           'settlement_no_malaria','livability','livability_no_malaria','arable',
           'kcal_wheat','kcal_barley','kcal_millet','kcal_rice','kcal_dates','crop','double_crop']
    field=np.array([[np.nan,0.],[.37,100.]])
    fields={key:field.copy() for key in names};fields['crop']=np.array([[0,1],[2,5]])
    fields['double_crop']=np.array([[np.nan,0],[1,0]])
    path=tmp_path/'harvest.bin';land=np.isfinite(field)
    specs=pack_fields(fields,land,np.array([[0,1],[2,3]]),path);blob=path.read_bytes()
    for key,s in specs.items():
        raw=np.frombuffer(blob,dtype=s['dtype'],count=4,offset=s['offset_bytes']).reshape(2,2)
        if key not in ['crop','hex_id','double_crop','aridity']:
            assert raw[0,0]==0 and raw[0,1]==1
            decoded=raw*s['scale']+s['offset']
            np.testing.assert_allclose(decoded[land],field[land],atol=s['scale']/2+1e-9)


def test_surface_interpolation_uses_solstice_phase_and_monthly_lapse():
    from harvest.export import surface_months
    arrays={'elev':np.full((2,2),1000.),'T12':np.arange(12)[:,None,None]*np.ones((12,2,2))*10,
            'P12':np.ones((12,2,2))*42,'D12':np.ones((12,2,2))*100}
    lapse=np.linspace(4.,7.,12)
    meta=dict(width=4,height=4,cell_px=2,lapse12=lapse,lat_center=30,north_bearing=0,mi_per_px=1,km_per_deg=111)
    t,p,d,lat=surface_months(meta,arrays)
    np.testing.assert_allclose(t[:,0,0],np.arange(12)-lapse)
    np.testing.assert_allclose(p,42);np.testing.assert_allclose(d,10)
    assert lat[0,0]>lat[1,0]


def test_coastal_area_and_province_totals_serialize_and_conserve_food():
    import json
    from harvest.export import aggregates
    fraction=np.array([[0.,.25,.75,1.],[1.,.5,0.,1.]],dtype=np.float32)
    land=fraction>0
    fields={k:np.where(land,value,np.nan) for k,value in {
        'crop_capacity':100.,'pastoral_capacity':10.,'food_capacity':110.,
        'settlement_base':60.,'settlement_no_malaria':80.,'malaria':.3,
        'lgp_days':220.,'irr':.1,'aridity':.8,'double_crop':0.}.items()}
    fields['crop']=np.where(land,1,0)
    info,index,area=aggregates(fields,{'land_fraction':fraction},dict(width=2000,mi_per_px=1.))
    json.dumps(info)  # Portable metadata must not contain numpy-only scalar types.
    expected_area=float(fraction.astype(float).sum())*(500*1.609344)**2
    np.testing.assert_allclose(info['summary']['land_km2'],expected_area,rtol=1e-6)
    np.testing.assert_allclose(sum(p['food_capacity_people'] for p in info['provinces']),expected_area*110,rtol=1e-6)
    assert info['summary']['population']['endemic']['central']<info['summary']['food_capacity']
