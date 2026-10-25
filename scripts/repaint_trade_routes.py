"""Repaint staged trade lanes from verified weights, without rerouting goods."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from local_benchmark_protocol import file_hash,write_json
from polity.economic_world import prepare
from polity import export as E,mapdata
from rotclimate.geography import source_layers


def main():
    name=sys.argv[1]
    if name not in ['earth_fit','free_fit','whittaker_fit']:raise ValueError('Unknown atlas')
    folder=ROOT/'output/directed_trade_20261025/publication'/name
    stage=ROOT/'output/directed_trade_20261025/staging'/name;data=stage/'data'
    verified=json.loads((folder/'verification.json').read_text())
    before=file_hash(folder/'cache.npz')
    if before!=verified['cache_sha256']:raise ValueError('Trade weights changed before repaint')
    with np.load(folder/'cache.npz') as z:c={k:z[k].copy() for k in z.files}
    meta=json.loads((data/'atlas.json').read_text());r=prepare(stage)
    for key in ['land','elev','claim','density']:
        if not np.array_equal(r[key],c[key],equal_nan=True):raise ValueError('Physical input changed: '+key)
    r.update(meta=meta,water=r['statics']['water'],polity_names=[str(n) for n in c['names']])
    r['polity_rgb']={n:rgb for n,rgb in zip(r['polity_names'],c['rgb'])}
    tr=dict(mass=c['t_mass'],ma=c['t_ma'],ma_local=c['t_local'],edges=(c['e_child'],c['e_parent'],c['e_flow']),
            scale=meta['reach']['trade']['cost_scale'],model='inbound-directed',market_access_direction='outbound',area_ha=None)
    old=next(l for l in meta['layers'] if l['id']=='reach_trade')
    layer=E.trade_layer(r,tr,meta,data,r['elev'],source_layers()['land'])
    if old.get('variants'):
        layer['variants']=old['variants']
        route=next(o for o in layer['variants']['options'] if o['value']=='routes')
        route.update(items=layer['items'],note=layer['note'],caption='Continuous sea lanes; widths show relative traffic')
    meta['layers']=[layer if l['id']=='reach_trade' else l for l in meta['layers']]
    dfs={f:dict(held_by=c[f'held_by_{int(f*10):02d}'],contested=c[f'contested_{int(f*10):02d}']) for f in [0.,.5,1.,2.]}
    mapdata.write(r,dfs,tr,data/'vectors')
    (data/'atlas.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    assert file_hash(folder/'cache.npz')==before
    files=[Path(__file__),ROOT/'polity/routes.py',ROOT/'polity/export.py',ROOT/'polity/mapdata.py',ROOT/'scripts/render_political_plate.py']
    write_json(folder/'display_repaint.json',dict(status='staged',trade_weights_unchanged=True,cache_sha256=before,
        metadata_sha256=file_hash(data/'atlas.json'),trade_image_sha256=file_hash(data/'reach_trade.webp'),
        display_sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in files}))
    print(name+': continuous sea lanes repainted from unchanged trade weights',flush=True)


if __name__=='__main__':main()
