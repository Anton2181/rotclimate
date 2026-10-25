"""Add hinterlands and served-population variants to the existing Trade layer.

Uses an already verified directed-trade publication checkpoint. No new
population, catchment or routing calculation is performed here.
"""
from __future__ import annotations
import colorsys
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from local_benchmark_protocol import file_hash, write_json
from polity.render import PAPER, SEA
from rotclimate.geography import source_layers


def main():
    name=sys.argv[1]
    if name not in ['earth_fit','free_fit','whittaker_fit']:raise ValueError('Unknown atlas')
    folder=ROOT/'output/directed_trade_20261025/publication'/name
    stage=ROOT/'output/directed_trade_20261025/staging'/name;data=stage/'data'
    check=json.loads((folder/'verification.json').read_text())
    if check['status']!='staged' or file_hash(folder/'cache.npz')!=check['cache_sha256']:
        raise ValueError('Verified directed trade checkpoint is required')
    meta=json.loads((data/'atlas.json').read_text())
    if meta['reach']['trade']['model']!='inbound-directed':raise ValueError('Unexpected trade model')
    with np.load(folder/'cache.npz') as z:
        owner=z['market_owner'];mass=z['t_mass'];towns=z['towns'];land=z['land'];claim=z['claim']
    valid=land&(claim>=0)&(owner>=0)
    if owner[valid].max()>=len(mass):raise ValueError('Invalid owner indices')
    width,height=meta['width'],meta['height']
    coast=np.asarray(Image.fromarray(source_layers()['land'].astype(np.uint8)*255).resize((width,height),Image.BILINEAR))>127
    top=np.argsort(-mass,kind='stable')[:8]
    nodes=towns[:,0]*land.shape[1]+towns[:,1]
    colors=np.array([colorsys.hls_to_rgb((int(n)*.61803398875)%1,.77,.46) for n in nodes])
    safe=np.maximum(owner,0)
    territories=np.broadcast_to(PAPER,land.shape+(3,)).copy();territories[valid]=colors[safe[valid]]
    boundary=np.zeros_like(valid)
    boundary[:,1:]|=valid[:,1:]&valid[:,:-1]&(owner[:,1:]!=owner[:,:-1])
    boundary[1:,:]|=valid[1:,:]&valid[:-1,:]&(owner[1:,:]!=owner[:-1,:])
    territories[boundary]*=.82
    thresholds=np.array([5000,10000,25000,50000,100000,250000])
    palette=np.array([[239,243,255],[198,219,239],[158,202,225],[107,174,214],[66,146,198],[33,113,181],[8,69,148]])/255.
    classes=np.searchsorted(thresholds,mass,side='right')
    people=np.broadcast_to(PAPER,land.shape+(3,)).copy();people[valid]=palette[classes[safe[valid]]]
    labels=['under 5,000','5,000–10,000','10,000–25,000','25,000–50,000','50,000–100,000','100,000–250,000','250,000 or more']
    def color(c):return '#%02x%02x%02x'%tuple(np.rint(c*255).astype(int))
    # Reuse the output map scale; numbered centres match the downloaded CSV.
    font=ImageFont.load_default(size=max(11,round(width/170)))
    for pixels,filename in [(territories,'reach_market_hinterlands.webp'),(people,'reach_market_people.webp')]:
        image=Image.fromarray(np.rint(np.clip(pixels,0,1)*255).astype(np.uint8)).resize((width,height),Image.Resampling.NEAREST)
        rgb=np.array(image);rgb[~coast]=np.rint(SEA*255).astype(np.uint8);image=Image.fromarray(rgb)
        draw=ImageDraw.Draw(image)
        for i in top:
            x=(towns[i,1]+.5)*width/land.shape[1];y=(towns[i,0]+.5)*height/land.shape[0]
            draw.ellipse((x-4,y-4,x+4,y+4),fill='white',outline='#222222',width=1)
            draw.text((x+6,y-8),str(int(i)+1),font=font,fill='#222222',stroke_width=2,stroke_fill='white')
        image.save(data/filename,'WEBP',quality=90,method=4)
    row_fields=['market_id','row','col','inbound_catchment_people']
    with (data/'market_hinterlands.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(row_fields)
        for i,(y,x) in enumerate(towns):writer.writerow([i+1,int(y),int(x),float(mass[i])])
    layer=next(l for l in meta['layers'] if l['id']=='reach_trade')
    base_note=layer['note'];base_items=layer['items']
    note=('Cheapest reachable market for goods coming into town over the midyear freight network, '
          'on recognised claimed land. Colours identify market territories, not states. Numbered centres '
          'are the eight largest hinterlands; every market is listed in data/market_hinterlands.csv. '
          'People served are the existing countryside population assigned to that market, not the town’s '
          'inhabitants. Settlement occupancy, population totals and political control do not change.')
    layer['variants']=dict(label='Trade view',default='routes',options=[
        dict(value='routes',label='Routes and towns',file=layer['file'],items=base_items,note=base_note,
             caption='Relative freight routes and the people each market serves'),
        dict(value='markets',label='Market hinterlands',file='reach_market_hinterlands.webp',
             items=[dict(color=color(colors[i]),label=f'Market {i+1} · {mass[i]:,.0f} people served') for i in top]
                   +[dict(color='#dddddd',label='Other market territories use individual colours')],
             note=note,caption='Cheapest inward market; colours are market areas, not polities'),
        dict(value='market_people',label='People served',file='reach_market_people.webp',
             items=[dict(color=color(c),label=l+' people served') for c,l in zip(palette,labels)],
             note=note,caption='Countryside population assigned to each market; not town population')])
    write_json(data/'atlas.json',meta)
    write_json(folder/'market_views.json',dict(status='staged',variants=3,source_cache_sha256=check['cache_sha256'],
        renderer_sha256=file_hash(Path(__file__)),metadata_sha256=file_hash(data/'atlas.json'),
        images_sha256={n:file_hash(data/n) for n in ['reach_market_hinterlands.webp','reach_market_people.webp']},
        csv_sha256=file_hash(data/'market_hinterlands.csv')))
    print(name+': staged three trade views, with unchanged population and route inputs',flush=True)


if __name__=='__main__':main()
