"""Add two conditional surroundings-spread maps from verified nine-layout fields.

No climate, population or political calculation is changed. Only an exact
parameter match (apart from resolution and random surroundings seed) is allowed.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import csv
import json
import pickle
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from matplotlib import colormaps
from PIL import Image
from earth_benchmark import load_params
from local_benchmark_protocol import identity,file_hash,write_json
from rotclimate.render import FullRes,OCEAN_RGB
from rotclimate.score import evaluate
from rotclimate.koppen import monthly_stats


def sample_spread(fields):
    """Welford moments of the displayed fields, including spatial covariance."""
    count=0;mean=None;m2=None
    for field in fields:
        value=np.asarray(field,float)
        if not np.isfinite(value).all():raise ValueError('Nonfinite ensemble field')
        if mean is None:mean=np.zeros_like(value);m2=np.zeros_like(value)
        if value.shape!=mean.shape:raise ValueError('Inconsistent ensemble grid')
        count+=1;delta=value-mean;mean+=delta/count;m2+=delta*(value-mean)
    if count<2:raise ValueError('Need multiple independently generated surroundings')
    return mean,np.sqrt(np.maximum(m2/(count-1),0)),count


def physical_key(p):
    return identity({k:v for k,v in asdict(p).items() if k not in {'downsample','beyond_seed'}})


def projected_temperature(result,fr):
    # Atlas temperatures interpolate sea-level fields before applying the
    # fixed source-pixel lapse offset. That offset cancels in the spread.
    # Interpolating temperatures already cooled at coarse elevations could
    # instead introduce varying outside-terrain heights into coastal fills.
    p=result.params
    monthly=monthly_stats(result.Tsl,result.P,result.days,p.year_days,
                          summer_solstice=p.winter_solstice_day+p.year_days/2)
    return fr.up(monthly['Tm'].mean(0))


def add(atlas,audit=ROOT/'output/r39_world_audit'):
    atlas=Path(atlas).resolve();audit=Path(audit).resolve();data=atlas/'data'
    review=json.loads((audit/'review.json').read_text());protocol=json.loads((audit/'protocol.json').read_text())
    if not review.get('complete'):raise ValueError('The fixed audit must be complete')
    p=load_params(atlas/'params.json');key=physical_key(p)
    for name,expected in protocol['source_hashes'].items():
        if name.startswith(('rotclimate/','data/source/')) and file_hash(ROOT/name)!=expected:
            raise ValueError('Changed diagnostic scientific input: '+name)
    seeds=protocol['plan']['layouts']
    if len(seeds)!=9 or len(set(seeds))!=9:raise ValueError('Need the complete fixed nine-layout sample')
    prefix=None
    for label in ['reference','candidate']:
        path=audit/'members'/f'audit_{label}_seed{seeds[0]}.pkl'
        with path.open('rb') as stream:result=pickle.load(stream)['result']
        if physical_key(result.params)==key:prefix=label;break
    if prefix is None:raise ValueError('No audited climate matches this atlas physics and geography')
    sources=[];coarse=[];first=None
    def fields():
        nonlocal first
        for seed in seeds:
            path=audit/'members'/f'audit_{prefix}_seed{seed}.pkl'
            with path.open('rb') as stream:cached=pickle.load(stream)
            result=cached['result']
            if physical_key(result.params)!=key or result.params.beyond_seed!=seed or result.params.downsample!=16:
                raise ValueError('Wrong sensitivity member parameters')
            if not result.numerics.get('all_checks_passed'):raise ValueError('Unverified sensitivity member')
            indices=evaluate(result)['indices'];fr=FullRes(result)
            if first is None:first=result
            sources.append(dict(seed=seed,file=str(path.relative_to(ROOT)),sha256=file_hash(path)))
            coarse.append(np.stack([indices['MAT'],indices['MAP']]))
            # Interpolate every member BEFORE taking spread. Interpolating a
            # coarse standard deviation would ignore covariance between cells.
            yield np.stack([projected_temperature(result,fr),fr.up(indices['MAP'])])
    means,spread,count=sample_spread(fields())
    coarse_mean,coarse_std,_=sample_spread(coarse)
    relative=np.divide(100*spread[1],means[1],out=np.zeros_like(means[1]),where=means[1]>0)
    meta=json.loads((data/'atlas.json').read_text());fr=FullRes(first);land=fr.land
    palette=colormaps['YlOrRd'];stops=['#%02x%02x%02x'%tuple(np.rint(np.array(palette(v)[:3])*255).astype(int)) for v in np.linspace(0,1,9)]
    note=('Sample spread across nine new hypothetical surroundings layouts at ds16; the main climate maps '
          'still average layouts 1–3 at ds8. Only the invented surroundings seed varies. This is conditional '
          'boundary sensitivity, not year-to-year weather, total model uncertainty or measured climate error. '
          'Standard deviations use n−1; colours saturate at the scale maximum.')
    layers=[];summaries={}
    for name,label,field,maximum,unit in [
        ('rain','Rain sensitivity',relative,50.,'Annual rain sample spread (% of its nine-layout mean)'),
        ('temperature','Temperature sensitivity',spread[0],2.,'Annual temperature sample spread (°C)')]:
        filename=f'surroundings_{name}_spread.webp'
        rgb=palette(np.clip(field/maximum,0,1))[...,:3];rgb[~land]=OCEAN_RGB
        image=Image.fromarray(np.rint(rgb*255).astype(np.uint8))
        image.resize((meta['width'],meta['height']),Image.Resampling.LANCZOS).save(data/filename,'WEBP',quality=90,method=4)
        layers.append(dict(id='surroundings_'+name,file=filename,label=label,kind='ramp',group='Fit checks',
                           unit=unit,vmin=0,vmax=maximum,stops=stops,note=note,
                           download='surroundings_sensitivity.csv'))
        summaries[name]=dict(median=float(np.median(field[land])),p90=float(np.quantile(field[land],.9)),maximum=float(field[land].max()))
    g=first.grid;mask=g.inmap&g.land
    with (data/'surroundings_sensitivity.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['grid_row','grid_col','source_x','source_y','mean_annual_c','sd_annual_c','mean_rain_mm_year','sd_rain_mm_year','rain_sd_percent'])
        for y,x in zip(*np.nonzero(mask)):
            rain=coarse_mean[1,y,x];ratio=100*coarse_std[1,y,x]/rain if rain>0 else 0
            writer.writerow([int(y),int(x),(x-g.pad+.5)*g.f,(y-g.pad+.5)*g.f,
                             float(coarse_mean[0,y,x]),float(coarse_std[0,y,x]),float(rain),float(coarse_std[1,y,x]),float(ratio)])
    record=dict(method='conditional-surroundings-sample-spread-v1',layouts=seeds,count=count,downsample=16,
        ddof=1,physical_parameter_key=key,member_group=prefix,sources=sources,summaries=summaries,
        projection='Interpolate each member to source land pixels before computing moments. Temperature uses sea-level fields before the shared source-terrain lapse correction, which cancels in spread.',
        note=note,exporter_sha256=file_hash(Path(__file__)),audit_review_sha256=file_hash(audit/'review.json'))
    write_json(data/'surroundings_sensitivity.json',record)
    ids={layer['id'] for layer in layers};meta['layers']=[layer for layer in meta['layers'] if layer['id'] not in ids]+layers
    meta['surroundings_sensitivity']=dict(metadata='surroundings_sensitivity.json',download='surroundings_sensitivity.csv',
        count=count,member_group=prefix,summaries=summaries,physical_parameter_key=key)
    (data/'atlas.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    return dict(status='passed',atlas=str(atlas.relative_to(ROOT)),added_layers=sorted(ids),
                metadata_sha256=file_hash(data/'atlas.json'),summaries=summaries,member_group=prefix)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlas',type=Path)
    ap.add_argument('--audit',type=Path,default=ROOT/'output/r39_world_audit');args=ap.parse_args()
    print(json.dumps(add(args.atlas,args.audit),indent=2))
