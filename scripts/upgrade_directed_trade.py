"""Stage directed trade without recalculating climate or political control.

The existing outward access indicators are retained under their original
definition; only inbound catchments and ordered shipments are regenerated.
The staged atlas and cache require verification and promotion afterwards.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from local_benchmark_protocol import file_hash, freeze, write_json
from polity.economic_world import prepare
from polity.directed_trade import map_fields
from polity import export as E, mapdata
from rotclimate.geography import source_layers


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlas',choices=['earth_fit','free_fit','whittaker_fit'])
    a=ap.parse_args();name=a.atlas
    folder=ROOT/'output/directed_trade_20261025/publication'/name
    stage=ROOT/'output/directed_trade_20261025/staging'/name
    folder.mkdir(parents=True,exist_ok=True)
    if not stage.exists():shutil.copytree(ROOT/'atlases'/name,stage)
    if not (folder/'input_atlas.json').exists():shutil.copy2(stage/'data/atlas.json',folder/'input_atlas.json')
    if not (folder/'input_cache.npz').exists():shutil.copy2(ROOT/'output/polity_map'/f'{name}.npz',folder/'input_cache.npz')
    paths=list((ROOT/'polity').glob('*.py'))+[Path(__file__),folder/'input_atlas.json',folder/'input_cache.npz']
    paths += [stage/'data'/n for n in ['atlas.bin','harvest.json','harvest.bin','winds12.npz']]
    fingerprint=freeze(folder/'protocol.json',dict(atlas=name,source_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in paths},
        method='Inbound countryside-to-town catchments; ordered directed gravity shipments; unchanged outward access indicators'))
    print(name+': preparing unchanged geography and population',flush=True)
    r=prepare(stage);meta=json.loads((folder/'input_atlas.json').read_text())
    with np.load(folder/'input_cache.npz') as z:cached={k:z[k].copy() for k in z.files}
    for key in ['land','elev','density','claim']:
        if not np.array_equal(r[key],cached[key],equal_nan=True):raise ValueError('Changed political input: '+key)
    coords=np.array([[t['row'],t['col']] for t in r['towns']])
    if not np.array_equal(coords,cached['towns']):raise ValueError('Changed settlement nodes')
    r.update(meta=meta,water=r['statics']['water'],polity_names=[str(n) for n in cached['names']])
    r['polity_rgb']={n:rgb for n,rgb in zip(r['polity_names'],cached['rgb'])}
    checkpoint=folder/'trade.npz'
    if checkpoint.exists():
        with np.load(checkpoint) as z:
            tr={k:z[k].copy() for k in ['towns','mass','catchment','ma_local','ma','through']}
            tr.update(edges=(z['origin'].copy(),z['destination'].copy(),z['volume'].copy()),
                area_ha=None,scale=float(z['scale']),model='inbound-directed',market_access_direction='outbound',
                eligible_people=float(z['eligible_people']),unassigned_people=float(z['unassigned_people']))
        print(name+': reusing directed trade checkpoint',flush=True)
    else:
        tr=map_fields(r,outward_access=np.stack([cached['t_local'],cached['t_ma']]),
                      progress=lambda message:print(name+': '+message,flush=True))
        with checkpoint.with_suffix('.tmp').open('wb') as stream:
            np.savez_compressed(stream,**{k:tr[k] for k in ['towns','mass','catchment','ma_local','ma','through','scale','eligible_people','unassigned_people']},
                                origin=tr['edges'][0],destination=tr['edges'][1],volume=tr['edges'][2])
        checkpoint.with_suffix('.tmp').replace(checkpoint)
    if not np.isclose(tr['mass'].sum()+tr['unassigned_people'],tr['eligible_people'],rtol=1e-12,atol=1e-6):
        raise ValueError('Directed catchment population does not balance')
    layer=E.trade_layer(r,tr,meta,stage/'data',r['elev'],source_layers()['land'])
    meta['layers']=[layer if l['id']=='reach_trade' else l for l in meta['layers']]
    meta['reach']['trade']=dict(model=tr['model'],cost_scale=tr['scale'],market_access_direction='outbound',
        eligible_people=tr['eligible_people'],unassigned_market_people=tr['unassigned_people'],input_identity=fingerprint,
        population_scope='Existing central-occupation population on recognised claimed land; unchanged')
    dfs={c:dict(held_by=cached[f'held_by_{int(c*10):02d}'],contested=cached[f'contested_{int(c*10):02d}']) for c in [0.,.5,1.,2.]}
    mapdata.write(r,dfs,tr,stage/'data/vectors',0.)
    write_json(stage/'data/atlas.json',meta)
    with (stage/'data/trade_towns.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['row','col','kind','inbound_catchment_people','outbound_local_access','outbound_market_access'])
        for i,t in enumerate(r['towns']):writer.writerow([t['row'],t['col'],t['kind'],tr['mass'][i],tr['ma_local'][i],tr['ma'][i]])
    cached.update(t_mass=tr['mass'],t_ma=tr['ma'],t_local=tr['ma_local'],e_child=tr['edges'][0],e_parent=tr['edges'][1],
                  e_flow=tr['edges'][2],through=tr['through'],market_owner=tr['catchment'])
    np.savez_compressed(folder/'cache.npz',**cached)
    original=json.loads((folder/'input_atlas.json').read_text())
    for key in ['harvest','population','observed_numerics']:
        if original[key]!=meta[key]:raise ValueError('Unrelated atlas metadata changed: '+key)
    if original['reach']['defacto']!=meta['reach']['defacto']:raise ValueError('Political population tables changed')
    write_json(folder/'verification.json',dict(status='staged',identity=fingerprint,political_tables_unchanged=True,
        population_scenarios_unchanged=True,assigned_people=float(tr['mass'].sum()),unassigned_people=tr['unassigned_people'],
        metadata_sha256=file_hash(stage/'data/atlas.json'),trade_image_sha256=file_hash(stage/'data/reach_trade.webp'),
        cache_sha256=file_hash(folder/'cache.npz')))
    print(name+': directed trade staged and population partitions verified',flush=True)


if __name__=='__main__':main()
