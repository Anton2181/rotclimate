"""Independent Decimal review of source-qualified crop-stage component outputs."""
import csv
from decimal import Decimal, ROUND_HALF_UP, localcontext
from html import unescape
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.crop_stage import StageCurve
from settlement_locations_earth import sha,write

OUT=ROOT/'output/crop_stage_20261114'


def area(lengths,levels,a,b):
    """Separate Decimal trapezoids clipped to four segments."""
    origin=Decimal(0);result=Decimal(0)
    endpoints=[(levels[0],levels[0]),(levels[0],levels[1]),(levels[1],levels[1]),(levels[1],levels[2])]
    for length,(start,end) in zip(lengths,endpoints):
        left,right=max(a,origin),min(b,origin+length)
        if right>left:
            at_left=start+(end-start)*(left-origin)/length
            at_right=start+(end-start)*(right-origin)/length
            result+=(right-left)*(at_left+at_right)/2
        origin+=length
    return result


def main():
    r=json.loads((OUT/'reference.json').read_text())
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    # Extract numeric source rows independently, retaining geographic context.
    sources={}
    for name,spec in r['sources'].items():
        path=ROOT/'data/cache/crop_stage_20261114'/name
        assert sha(path)==spec['sha256'],name
        raw=path.read_text(encoding='latin1');rows=[]
        for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw,re.I|re.S):
            cells=[]
            for td in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.I|re.S):
                td=re.sub(r'<sup\b[^>]*>.*?</sup>','',td,flags=re.I|re.S)
                cells.append(' '.join(unescape(re.sub(r'<[^>]*>','',td)).split()))
            rows.append(cells)
        sources[name]=rows
    stage_source=sources['fao56_ch6.html']
    start=next(i for i,row in enumerate(stage_source) if row and row[0]=='Barley/Oats/Wheat')
    assert [v['source_cells'] for v in r['table11']]==stage_source[start:start+11]
    for v in r['table11']:
        assert sum(map(Decimal,map(str,v['stage_days'])))==Decimal(v['total_days'])
    for v in r['table17']:
        assert v['source_cells'] in sources['fao56_ch7.html']
        assert v['kcb_initial_text']==(v['source_cells'][1] or '0.15')
    source_plain=' '.join(unescape(re.sub(r'<[^>]*>',' ',(ROOT/'data/cache/crop_stage_20261114/fao56_ch7.html').read_text(encoding='latin1'))).split())
    for text in r['source_claims'].values():assert text in source_plain
    assert r['table11'][7]['stage_days']==[30,140,40,30] and r['table11'][7]['region']=='Mediterranean'
    assert r['table17'][2]['kcb_initial_text']=='0.15-0.5' and r['table17'][2]['kcb_end_text']=='0.15-0.3'
    lengths=list(map(Decimal,['25','25','30','20']))
    levels=list(map(Decimal,['.15','1.14','.25']))
    assert r['example30']['stage_days']==list(map(float,lengths))
    assert r['example30']['coefficients']==list(map(float,levels))
    expected_points=[Decimal('.15'),Decimal('.15')+Decimal(12)/25*Decimal('.99'),Decimal('1.14'),(Decimal('1.14')+Decimal('.25'))/2]
    for row,day,expected in zip(r['example30']['points'],[12,37,65,90],expected_points):
        assert row['day']==day and abs(Decimal(str(row['value']))-expected)<Decimal('1e-14')
        assert str(expected.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))==row['published']
    count=0;total=Decimal(0);last=Decimal(0);maxerror=0.
    with localcontext() as context:
        context.prec=40
        with (OUT/'intervals.csv').open() as file:
            for v in csv.DictReader(file):
                a,b=Decimal(v['start_day']),Decimal(v['end_day'])
                assert a==last and b>a
                exact=area(lengths,levels,a,b)
                error=abs(Decimal(v['integral_kcb_days'])-exact)
                assert error<Decimal('1e-12')
                assert abs(Decimal(v['mean_kcb'])-exact/(b-a))<Decimal('1e-12')
                total+=exact;last=b;count+=1;maxerror=max(maxerror,float(error))
        assert last==100 and count==r['interval_rows']
        assert total==Decimal('67.975')
        assert abs(Decimal(str(r['example30']['integral_kcb_days']))-total)<Decimal('1e-12')
        assert abs(Decimal(str(r['example30']['mean_kcb']))-total/100)<Decimal('1e-14')
        # Additional independently integrated curves exercise the operator,
        # rather than only the printed example with its known parameters.
        rng=np.random.default_rng(141114);synthetic=0;max_synthetic=0.
        for case in range(100):
            ls=[Decimal(int(v))/10 for v in rng.integers(1,1000,4)]
            cs=[Decimal(int(v))/100 for v in rng.integers(0,150,3)]
            curve=StageCurve(tuple(map(float,ls)),*map(float,cs));end=sum(ls)
            for j in range(40):
                a,b=sorted(end*Decimal(int(v))/10000 for v in rng.integers(0,10001,2))
                exact=area(ls,cs,a,b)
                error=abs(Decimal(str(float(curve.integral(float(a),float(b)))))-exact)
                assert error<Decimal('3e-12')
                synthetic+=1;max_synthetic=max(max_synthetic,float(error))
    fresh={}
    for name in ['reference.json','intervals.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name
        fresh[name]=sha(OUT/name)
    assert not r['earth_fields_scored'] and not r['adopt']
    tests=['crop_stage','rain_timing','river_fields','field_clock','soil_drying','flood_storage','flood_water','flood_timing','flood_gauge_quality']
    controls=subprocess.run([sys.executable,'-m','pytest','-q',*[f'tests/test_{name}.py' for name in tests]],cwd=ROOT,capture_output=True,text=True,check=True)
    write(OUT/'review.json',dict(status='passed',reviewer_sha256=sha(Path(__file__)),reference_sha256=sha(OUT/'reference.json'),method='Independent Decimal point, rounding and clipped-trapezoid integration; raw source cells and context checked; producer not imported',controls_stdout=controls.stdout,source_stage_rows=11,source_coefficient_rows=3,published_points=4,interval_rows=count,max_interval_error_kcb_days=maxerror,synthetic_curves=100,synthetic_intervals=synthetic,max_synthetic_error_kcb_days=max_synthetic,fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),earth_fields_scored=False,adopt=False))
    print(controls.stdout.strip());print('Passed Decimal component/source review:',count,'intervals;',synthetic,'synthetic intervals;two fresh files byte-exact')


if __name__=='__main__':main()
