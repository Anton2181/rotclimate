"""Verify population provenance, census conservation, local caps and map assets."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from .export import DEFINITIONS,views


def verify(data,climate):
    data=Path(data);m=json.loads((data/'population.json').read_text());blob=(data/'population.bin').read_bytes()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(data/'population.bin')==m['binary_sha256']
    assert sha(data/'atlas.bin')==m['inputs']['climate_sha256']
    assert sha(data/'harvest.bin')==m['inputs']['harvest_sha256']
    assert sha(data/'harvest.json')==m['inputs']['harvest_metadata_sha256']
    assert m['fingerprint']==climate['population']['fingerprint']
    assert hashlib.sha256(json.dumps(m['inputs'],sort_keys=True).encode()).hexdigest()==m['fingerprint']
    assert sha(data/'population_model.json')==m['inputs']['sources']['data/population_model.json']
    fields={};end=0
    for key,s in m['arrays'].items():
        dtype=np.dtype(s['dtype']);n=int(np.prod(s['shape']));start=s['offset'];stop=start+n*dtype.itemsize
        assert start>=end and start%4==0 and stop<=len(blob)
        fields[key]=np.frombuffer(blob,dtype=dtype,count=n,offset=start).reshape(s['shape']);end=stop
        assert list(fields[key].shape)==m['shape'] and np.isfinite(fields[key]).all()
    assert end==len(blob)
    land=fields['area']>0;assert land.any()
    assert all((fields[key]>=0).all() for key in ['area','capacity','capacity_absent','rural','attraction'])
    assert (fields['attraction'][land]>0).all() and (fields['attraction'][land]<=1).all()
    assert (fields['rural'][land]>=fields['attraction'][land]).all()
    assert (fields['market']<=len(m['markets'])).all() and (fields['province']<=len(m['provinces'])).all()
    assert np.array_equal(fields['market'][land]==0,fields['travel'][land]<0)
    for p in m['markets']:assert 0<=p['row']<m['shape'][0] and 0<=p['column']<m['shape'][1]
    trials=[]
    for disease in ['endemic','absent']:
        c=fields['capacity_absent' if disease=='absent' else 'capacity'].astype(float)
        total=float((c*fields['area']).sum())
        for pattern in ['dispersed','rural','markets']:
            for requested in [0,m['default_population'],total*1.2]:
                maps,people,unmet=views(fields,requested,pattern,disease)
                np.testing.assert_allclose(people.sum()+unmet,requested,rtol=1e-9,atol=1e-5)
                assert (people<=c*fields['area']+1e-8).all()
                assert np.isfinite(maps['density']).all() and maps['pressure'].max()<=100+1e-8
                trials.append(dict(disease=disease,pattern=pattern,requested=requested,allocated=float(people.sum()),unallocated=unmet))
    rows=list(csv.DictReader((data/'population_provinces.csv').open()))
    np.testing.assert_allclose(sum(float(r['allocated_people']) for r in rows),m['summary']['allocated'],rtol=1e-10)
    assert sum(float(r['area_km2']) for r in rows)>0
    for key,*_ in DEFINITIONS:
        with Image.open(data/('pop_'+key+'.webp')) as im:assert im.size==(m['width'],m['height']);im.verify()
    return dict(status='passed',binary_bytes=len(blob),fields=len(fields),land_cells=int(land.sum()),markets=len(m['markets']),
                provinces=len(rows),census_trials=len(trials),default_population=m['default_population'],
                default_allocated=m['summary']['allocated'],unreachable_land_km2=m['summary']['unreachable_land_km2'])
