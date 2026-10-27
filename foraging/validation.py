"""Verify a portable adapted FORGE packet and its resource/area accounting."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from PIL import Image


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(data, climate=None):
    data=Path(data)
    if climate is None:climate=json.loads((data/'atlas.json').read_text())
    m=json.loads((data/'foraging.json').read_text());blob=(data/'foraging.bin').read_bytes()
    assert sha(data/'foraging.bin')==m['binary_sha256'],'Foraging binary checksum differs'
    assert sha(data/'atlas.bin')==m['original_climate_sha256']==m['inputs']['climate_sha256'],'Foraging climate input differs'
    assert hashlib.sha256(json.dumps(m['inputs'],sort_keys=True).encode()).hexdigest()==m['fingerprint']
    assert climate['foraging']['fingerprint']==m['fingerprint']
    assert sha(data/'foraging_model.json')==m['inputs']['sources']['data/foraging_model.json']
    shape=tuple(m['shape']);arrays={};end=0
    for key,s in m['arrays'].items():
        dtype=np.dtype(s['dtype']);count=int(np.prod(s['shape']));start=s['offset_bytes'];stop=start+count*dtype.itemsize
        assert tuple(s['shape'])==shape and start%4==0 and start>=end and stop<=len(blob),key
        arrays[key]=np.frombuffer(blob,dtype=dtype,count=count,offset=start).reshape(shape)
        end=stop
    assert end==len(blob),'Trailing or incomplete foraging binary'
    fraction=arrays['land_fraction'];land=np.isfinite(fraction)&(fraction>0)
    assert land.any() and np.all((fraction[land]>0)&(fraction[land]<=1+1e-6))
    for key,value in arrays.items():
        assert np.isfinite(value[land]).all(),key
        if key in ['converged','floor_limited','unsupported']:
            assert set(np.unique(value[land]))<={0,1},key
            assert (value[~land]==255).all(),key
        else:assert np.isnan(value[~land]).all(),key
    density=arrays['density_people_km2'];area=arrays['cell_area_km2']
    assert (density[land]>=0).all() and (area[land]>0).all()
    assert (density[land & (arrays['unsupported']==1)]==0).all()
    assert np.all((arrays['foraging_hours_day'][land]>=0)&(arrays['foraging_hours_day'][land]<=24))
    assert np.all((arrays['meat_fraction'][land]>=0)&(arrays['meat_fraction'][land]<=1))
    assert np.all((arrays['scarcity_days_year'][land]>=0)&(arrays['scarcity_days_year'][land]<=365))
    assert np.all((arrays['years_simulated'][land]>=1)&(arrays['years_simulated'][land]<=m['run']['years']))
    for key in ['maximum_relative_resource_residual','maximum_relative_energy_residual']:
        assert key in arrays and np.max(arrays[key][land])<=1e-10,(key,float(np.max(arrays[key][land])))
    summary=m['summary'];population=float((density[land].astype(float)*area[land]).sum())
    np.testing.assert_allclose(population,summary['total_scenario_people'],rtol=3e-6,atol=1e-5)
    np.testing.assert_allclose(float(area[land].sum(dtype=float)),summary['land_km2'],rtol=3e-6)
    np.testing.assert_allclose(sum(p['area_km2'] for p in m['provinces']),summary['land_km2'],rtol=3e-12)
    np.testing.assert_allclose(sum(p['scenario_people'] for p in m['provinces']),summary['total_scenario_people'],rtol=3e-12,atol=1e-8)
    rows=list(csv.DictReader((data/'foraging_provinces.csv').open()))
    assert len(rows)==len(m['provinces'])
    np.testing.assert_allclose(sum(float(r['scenario_people']) for r in rows),summary['total_scenario_people'],rtol=3e-12,atol=1e-8)
    layers=[l for l in climate['layers'] if l['id'].startswith('forage_')]
    assert len(layers)==4 and all(l['group']=='Foraging' and l['controls']==[] for l in layers)
    for layer in layers:
        for name in [layer['file'],layer['tiers']['file']]:
            with Image.open(data/name) as image:
                assert image.size==(m['width'],m['height']);image.verify()
    return dict(status='passed',fields=len(arrays),binary_bytes=len(blob),analysis_shape=list(shape),
        land_cells=int(land.sum()),scenario_people=summary['total_scenario_people'],
        converged_land_share=summary['converged_land_share'],
        maximum_relative_resource_residual=float(arrays['maximum_relative_resource_residual'][land].max()),
        maximum_relative_energy_residual=float(arrays['maximum_relative_energy_residual'][land].max()),
        climate_unchanged=True,map_modes=4,provinces=len(rows))
