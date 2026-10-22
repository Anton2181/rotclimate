"""Check the portable land packet, food budget, area totals and input hashes."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image


def verify(data, climate):
    data=Path(data);m=json.loads((data/'harvest.json').read_text());blob=(data/'harvest.bin').read_bytes()
    arrays={};end=0
    for key,s in m['arrays'].items():
        dtype=np.dtype(s['dtype']);n=int(np.prod(s['shape']));start=s['offset_bytes'];stop=start+n*dtype.itemsize
        assert start>=end and start%4==0 and stop<=len(blob),key
        raw=np.frombuffer(blob,dtype=dtype,count=n,offset=start).reshape(s['shape'])
        value=raw.astype(float)*s['scale']+s['offset']
        if s['nodata'] is not None:value[raw==s['nodata']]=np.nan
        arrays[key]=value;end=stop
    assert end==len(blob)
    assert list(arrays['crop'].shape)==m['shape']
    assert all(a.shape==arrays['crop'].shape for a in arrays.values())
    land=np.isfinite(arrays['crop']);assert land.any()
    assert all(np.isfinite(a[land]).all() for a in arrays.values())
    assert set(arrays['crop'][land])<=set(range(1,6))
    assert set(arrays['double_crop'][land])<={0.,1.}
    assert all(np.isnan(a[~land]).all() for a in arrays.values())
    q=lambda key:m['arrays'][key]['scale']
    v=lambda key:arrays[key][land]
    np.testing.assert_allclose(v('food_capacity'),v('crop_capacity')+v('pastoral_capacity'),rtol=0,
        atol=q('food_capacity')+q('crop_capacity')+q('pastoral_capacity'))
    penalty=m['parameters']['maximum_malaria_penalty']
    np.testing.assert_allclose(v('health'),1-penalty*v('malaria'),rtol=0,
                              atol=q('health')+penalty*q('malaria'))
    usable=v('crop_capacity')*v('clearance')+v('pastoral_capacity')
    budget_error=(q('crop_capacity')+q('pastoral_capacity')+v('crop_capacity').max()*q('clearance')
                  +usable.max()*(q('access')+q('health')))
    for key,health in [('settlement_no_malaria',1),('settlement_base',v('health'))]:
        np.testing.assert_allclose(v(key),usable*v('access')*health,rtol=0,atol=budget_error+q(key))
    for key,health in [('livability_no_malaria',1),('livability',v('health'))]:
        expected=100*usable/(usable+m['parameters']['livability_food_reference_per_km2'])*v('access')*health
        np.testing.assert_allclose(v(key),expected,rtol=0,atol=budget_error+q(key))
    assert np.all(v('settlement_base')<=v('settlement_no_malaria')+q('settlement_base')+q('settlement_no_malaria'))
    assert np.all(v('settlement_no_malaria')<=v('food_capacity')+q('settlement_no_malaria')+q('food_capacity'))
    for key,lo,hi in [('malaria',0,1),('malaria_months',0,12),('livability',0,100),
                      ('livability_no_malaria',0,100),('irr',0,1),
                      ('access',m['parameters']['river_access_floor'],1),('health',1-penalty,1)]:
        assert v(key).min()>=lo-q(key) and v(key).max()<=hi+q(key),key
    s=m['summary'];fs=m['occupation']['scenarios']
    assert 0<fs['frontier']<fs['central']<fs['core']<=1
    for disease,base in [('endemic','settlement_base'),('absent','settlement_no_malaria')]:
        for name,f in fs.items():
            np.testing.assert_allclose(s['population'][disease][name],s[base]*f,rtol=1e-12)
    for key,total in [('area_km2','land_km2'),('food_capacity_people','food_capacity'),
                      ('crop_capacity_people','crop_capacity'),('settlement_base','settlement_base'),
                      ('settlement_no_malaria','settlement_no_malaria')]:
        np.testing.assert_allclose(sum(p[key] for p in m['provinces']),s[total],rtol=2e-6)
    assert abs(sum(s['crops'])-1)<2e-6
    assert all(abs(sum(p['crops'])-1)<2e-6 for p in m['provinces'])
    for layer in climate['layers']:
        if not layer['id'].startswith('land_'):continue
        for file in {layer['file'],*layer.get('scenario_files',{}).values()}:
            with Image.open(data/file) as im:
                assert im.size==(m['width'],m['height']);im.verify()
    province_rows=list(csv.DictReader((data/'provinces_people.csv').open()))
    assert len(province_rows)==len(m['provinces'])
    assert abs(sum(int(r['central_endemic_people']) for r in province_rows)-s['population']['endemic']['central'])<=len(province_rows)/2+1
    assert list(csv.DictReader((data/'places_harvest.csv').open()))
    provenance=json.loads((data/'harvest_provenance.json').read_text())
    assert hashlib.sha256((data/'atlas.bin').read_bytes()).hexdigest()==provenance['inputs']['climate_sha256']
    assert provenance['fingerprint']==climate['harvest']['fingerprint']
    assert hashlib.sha256(json.dumps(provenance['inputs'],sort_keys=True).encode()).hexdigest()==provenance['fingerprint']
    # Small source copies in the portable bundle must match those used to build it.
    for name in ['harvest_model.json','harvest_sources.json','settlement_reference_regions.json']:
        assert hashlib.sha256((data/name).read_bytes()).hexdigest()==provenance['inputs']['sources']['data/'+name]
    assert hashlib.sha256((data/'earth_crop_reference.webp').read_bytes()).hexdigest()==provenance['inputs']['sources']['land/earth.webp']
    crop_model=json.loads((data/'crop_model.json').read_text())
    assert set(crop_model['crops'])=={'wheat','barley','millet','rice'}
    assert crop_model['single_crop_sown_share']==.68 and crop_model['kcal_per_person_year']==1.1e6
    return dict(status='passed',binary_bytes=len(blob),fields=len(arrays),land_cells=int(land.sum()),
                provinces=len(m['provinces']),sheet_hexes=m['sheet_check']['hexes'],
                scenario_population=s['population'],food_capacity=s['food_capacity'])
