"""Qualify FAO cereal stage context and reproduce its published curve example."""
import argparse
import csv
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.crop_stage import StageCurve
from qualify_flood_storage_sources import Rows
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/crop_stage_20261114/plan.json'
CACHE=ROOT/'data/cache/crop_stage_20261114'
OUT=ROOT/'output/crop_stage_20261114'


def source_rows(raw):
    # Keep superscripts separate: 20 followed by footnote2 is not 202 days.
    clean=re.sub(r'<sup\b[^>]*>.*?</sup>','',raw,flags=re.S|re.I)
    parser=Rows();parser.feed(clean)
    independent=[]
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw,re.S|re.I):
        cells=[]
        for cell in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row,re.S|re.I):
            cell=re.sub(r'<sup\b[^>]*>.*?</sup>','',cell,flags=re.S|re.I)
            cells.append(' '.join(unescape(re.sub(r'<[^>]+>','',cell)).split()))
        independent.append(cells)
    return parser.rows,independent


def selected_stages(rows):
    start=next(i for i,r in enumerate(rows) if r and r[0]=='Barley/Oats/Wheat')
    finish=next(i for i in range(start+1,len(rows)) if rows[i] and rows[i][0]=='Maize (grain)')
    crop=None;result=[]
    for row in rows[start:finish]:
        if len(row)==8:crop=row[0];values=row[1:]
        else:assert len(row)==7;values=row
        stage=[int(v) for v in values[:4]]
        total=int(values[4]);assert sum(stage)==total
        result.append(dict(crop=crop,stage_days=stage,total_days=total,planting=values[5],region=values[6],source_cells=row))
    assert len(result)==11
    return result


def selected_coefficients(rows):
    result=[];cereal=None
    for row in rows:
        if row and row[0]=='i. Cereals' and len(row)==4:
            cereal=row
        if row and row[0] in ('Barley','Spring Wheat','Winter Wheat') and len(row)==4:
            assert cereal is not None
            result.append(dict(crop=row[0],kcb_initial_text=row[1] or cereal[1],initial_inherited_from_cereals=not bool(row[1]),kcb_mid_text=row[2],kcb_end_text=row[3],source_cells=row))
    assert len(result)==3
    return result


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());CACHE.mkdir(parents=True,exist_ok=True)
    facts={};raws={}
    for name,spec in plan['sources'].items():
        path=CACHE/name
        old=ROOT/'data/cache/flood_storage_sources_20261114'/name
        if not path.exists() and old.exists():shutil.copyfile(old,path)
        if not path.exists():
            request=urllib.request.Request(spec['url'],headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=30) as response:data=response.read()
            assert __import__('hashlib').sha256(data).hexdigest()==spec['sha256'],'Source changed; audit before use'
            path.write_bytes(data)
        assert sha(path)==spec['sha256'],name
        raws[name]=path.read_text(encoding='latin1')
        first,second=source_rows(raws[name])
        select=selected_stages if name=='fao56_ch6.html' else selected_coefficients
        facts[name]=select(first);assert facts[name]==select(second),'Independent table parses differ'
    plain=' '.join(unescape(re.sub(r'<[^>]+>',' ',raws['fao56_ch7.html'])).split())
    claims={
        'winter_wheat_end_footnote10':'The higher value is for hand-harvested crops.',
        'winter_wheat_initial_footnote11':'The two K cb ini values for winter wheat are for less than 10% ground cover and for during the dormant, winter period, if the vegetation fully covers the ground, but conditions are nonfrozen.',
        'basal_diffusion':'The K cb ET o does include a residual diffusive evaporation component supplied by soil water below the dry surface and by soil water from beneath dense vegetation.',
        'reference_climate':'For specific adjustment in climates where RH min differs from 45% or where the wind speed is larger or smaller than 2 m/s, the K cb mid and K cb end values larger than 0.45 must be adjusted using the following equation:',
    }
    for text in claims.values():assert text in plain,text
    for snippet in ['25, 25, 30 and 20 days','0.15, 0.63, 1.14 and 0.70 respectively']:
        assert snippet in plain,snippet
    curve=StageCurve((25,25,30,20),.15,1.14,.25)
    benchmark=[dict(day=day,published=published,value=float(curve.value(day))) for day,published in [(12,'0.15'),(37,'0.63'),(65,'1.14'),(90,'0.70')]]
    edges=np.unique(np.r_[np.arange(0,100,.37),curve.edges_days,[12,37,65,90]])
    out.mkdir(parents=True,exist_ok=True)
    with (out/'intervals.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['start_day','end_day','mean_kcb','integral_kcb_days'])
        for a,b in zip(edges[:-1],edges[1:]):writer.writerow([a,b,float(curve.mean(a,b)),float(curve.integral(a,b))])
    base=ROOT/'output/rain_timing_20261114/results.json'
    r=json.loads(base.read_text());protected=dict(r['unchanged_sha256'])
    for folder in ['daily_river_fields_20261114','rain_timing_20261114']:
        for name in ['results.json','fields.npz','review.json']:
            path=ROOT/'output'/folder/name;protected[str(path.relative_to(ROOT))]=sha(path)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    producers=[Path(__file__),ROOT/'harvest/crop_stage.py',ROOT/'tests/test_crop_stage.py',ROOT/'scripts/qualify_flood_storage_sources.py',PLAN]
    write(out/'reference.json',dict(status='generic_sources_and_component_only',sources=plan['sources'],table11=facts['fao56_ch6.html'],table17=facts['fao56_ch7.html'],source_claims=claims,example30=dict(stage_days=list(curve.stage_days),coefficients=[curve.kcb_initial,curve.kcb_mid,curve.kcb_end],points=benchmark,integral_kcb_days=float(curve.integral(0,100)),mean_kcb=float(curve.mean(0,100))),interval_rows=len(edges)-1,files_sha256={'intervals.csv':sha(out/'intervals.csv')},producers={str(p.relative_to(ROOT)):sha(p) for p in producers},unchanged_sha256=protected,earth_fields_scored=False,independent_regional_validation=False,adopt=False))
    print('Two source parses agree;11 stage-context rows;3 cereal coefficient rows;4 published benchmark points;',len(edges)-1,'exact intervals')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
