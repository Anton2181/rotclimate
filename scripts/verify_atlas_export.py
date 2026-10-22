"""Check a built atlas's binary fields, layers, biome shares and climate exports."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
from rotclimate.biomes import LABELS


def verify_numerics(observed):
    assert observed and observed.get('all_checks_passed'), 'Observed convergence checks required'
    if 'members' in observed:
        assert len(observed['members']) == 3, 'Publication needs the three declared layouts'
        for member in observed['members']:
            verify_numerics(member)
    else:
        assert observed['linear_solves'] > 0 and observed['temperature_steps'] > 0
        assert observed['linear_unconverged'] == observed['temperature_unconverged'] == 0
        assert observed['moisture_checked'] and observed['moisture_unconverged'] == 0
        assert observed['temperature_max_update_c'] <= .05


def verify(root, require_verified=False):
    root=Path(root); data=root/'data';meta=json.loads((data/'atlas.json').read_text());blob=(data/'atlas.bin').read_bytes()
    end=0;arrays={}
    for name,spec in meta['arrays'].items():
        dtype=np.dtype(spec['dtype']);count=int(np.prod(spec['shape']));start=spec['offset'];stop=start+count*dtype.itemsize
        assert start>=end and start%4==0 and stop<=len(blob),f'invalid binary span: {name}'
        arrays[name]=np.frombuffer(blob,dtype=dtype,count=count,offset=start).reshape(spec['shape']);end=stop
    assert end==len(blob)
    assert arrays['biome'].shape==arrays['cls'].shape==arrays['elev'].shape
    assert np.array_equal(arrays['biome']==255,arrays['cls']==255)
    assert set(np.unique(arrays['biome']))<=set(range(len(LABELS)))|{255}
    assert abs(sum(b['share'] for b in meta['biomes'])-1)<1e-10
    assert len(meta['lapse_local'])==len(meta['months'])==11 and len(meta['lapse12'])==12
    assert np.isfinite(meta['lapse12']).all() and min(meta['lapse12'])>0
    assert any(l['id']=='whittaker' for l in meta['layers'])
    images=set()
    for layer in meta['layers']:
        for file in [layer['file'],*layer.get('frames',[]),*layer.get('scenario_files',{}).values()]:
            with Image.open(data/file) as im:im.verify()
            images.add(file)
    with Image.open(data/'whittaker_diagram.png') as im:im.verify()
    rows=list(csv.DictReader((data/'places_climate.csv').open()))
    assert rows and all(r['whittaker_biome'] in LABELS+['sea'] for r in rows)
    assert (data/'WHITTAKER_LICENSE.txt').exists()
    observed=meta.get('observed_numerics')
    if require_verified:
        verify_numerics(observed)
        if 'around' in meta:
            verify_numerics(meta['around']['observed_numerics'])
    animations={}
    for file in data.glob('*.gif'):
        with Image.open(file) as im:
            frames=im.n_frames
            for frame in range(frames):
                im.seek(frame);im.load()
            assert frames > 1, f'Animation has only one frame: {file}'
            animations[file.name]=frames
    if any(l['id']=='biome_targets' for l in meta['layers']):
        assert (data/'biome_target_crosswalk.json').exists()
        assert len(meta['biome_target_audit'])==7
        assert any(l['id']=='biome_match' for l in meta['layers'])
    harvest=None
    if meta.get('harvest'):
        from harvest.validation import verify as verify_harvest
        harvest=verify_harvest(data,meta)
    return dict(atlas=str(root),binary_bytes=len(blob),fields=len(arrays),layer_images=len(images),places=len(rows),harvest=harvest,
                unclassified_land_share=meta['biomes'][0]['share'],status='passed',
                numerical_checks_passed=bool(observed and observed.get('all_checks_passed')),
                animation_frames=animations)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlas',nargs='+');ap.add_argument('--out')
    ap.add_argument('--require-verified',action='store_true')
    a=ap.parse_args();results=[verify(root,a.require_verified) for root in a.atlas]
    text=json.dumps(results,indent=2);print(text)
    if a.out:Path(a.out).write_text(text+'\n')
