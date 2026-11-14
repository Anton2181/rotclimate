"""Published FAO drying components and declared synthetic shared-pool columns."""
import argparse,csv,io,json,re,subprocess,sys
from html import unescape
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.soil_drying import soil_profile,soil_state,soil_step,surface_coefficients,root_stress
from harvest.field_clock import field_clock
from qualify_flood_storage_sources import SOURCES,CACHE
from settlement_locations_earth import sha,write
PLAN=ROOT/'calibration/soil_drying_20261114/plan.json'
OUT=ROOT/'output/soil_drying_20261114'


def source_rows(name,example):
    path=CACHE/name;assert sha(path)==SOURCES[name]['sha256'],name
    text=path.read_text(encoding='latin1');start=text.index('EXAMPLE '+str(example));stop=text.find('EXAMPLE',start+20)
    fragment=text[start:stop if stop>=0 else len(text)];rows=[]
    for raw in re.findall(r'<tr\b[^>]*>(.*?)</tr>',fragment,re.I|re.S):
        cells=[' '.join(unescape(re.sub('<[^>]*>','',v)).split()) for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',raw,re.S|re.I)]
        if len(cells)==8 and cells[0] in {str(i) for i in range(1,11)}:rows.append(cells)
    assert len(rows)==10 and [int(v[0]) for v in rows]==list(range(1,11))
    return rows


def column_run(profile,forcing,*,fraction=1.):
    state=soil_state(profile,fraction);initial={name:np.array(getattr(state,name)) for name in ('top_mm','deep_mm','bound_mm')}
    names=('evaporation_mm','root_uptake_mm','drainage_mm','kr','ke','ks','root_potential_mm')
    result={name:[] for name in (*names,'top_mm','deep_mm','bound_mm')}
    for water,eto,kcb,p in zip(forcing['water_mm'],forcing['eto_mm_day'],forcing['kcb'],forcing['p']):
        step=soil_step(profile,state,water,eto,kcb,1.2,p);state=step.state
        for name in names:result[name].append(np.asarray(getattr(step,name)))
        for name in ('top_mm','deep_mm','bound_mm'):result[name].append(np.asarray(getattr(state,name)))
    return {**{name:np.array(v) for name,v in result.items()},**{'initial_'+name:value for name,value in initial.items()}}


def main(out=OUT):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    out.mkdir(parents=True,exist_ok=True)
    controls=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_soil_drying.py','tests/test_field_clock.py','tests/test_flood_storage.py','tests/test_flood_water.py','tests/test_flood_timing.py','tests/test_flood_gauge_quality.py'],cwd=ROOT,capture_output=True,text=True,check=True)
    write(out/'controls.json',dict(status='passed_before_evidence_outputs',stdout=controls.stdout))
    original=json.loads((ROOT/'output/flood_basin_storage_20261114/results.json').read_text())
    protected={**original['unchanged_atlas_sha256'],**{'output/flood_basin_storage_20261114/'+name:digest for name,digest in json.loads((ROOT/'output/flood_basin_storage_20261114/review.json').read_text())['fresh_byte_exact'].items()}}
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    rows=[];benchmark_rows=[];fields={};depletion=0.
    for raw in source_rows('fao56_ch7.html',31):
        kr,ke=surface_coefficients(depletion,9.,20.,.15,1.2);evap=float(ke)*4.5
        values=[depletion,1 if depletion<=9 else 2,float(kr),float(ke),evap,depletion+evap,evap+.15*4.5]
        for index,(text,value) in enumerate(zip(raw[1:],values)):
            # Only the explicitly printed RHS of the Kr equation is numeric evidence.
            numeric=text.rsplit('=',1)[-1].strip();decimals=len(numeric.split('.')[1]) if '.' in numeric else None
            expected=float(numeric);tolerance=.5*10**(-decimals)+1e-9 if decimals is not None else 1e-9
            error=abs(value-expected);assert error<=tolerance,('FAO31',raw[0],index,text,value,tolerance)
            benchmark_rows.append(dict(example=31,day=int(raw[0]),column=index+1,source_text=text,published_value=expected,model_value=value,tolerance=tolerance))
        rows.append(dict(example=31,day=int(raw[0]),start_depletion_mm=depletion,kr=float(kr),ke=float(ke),soil_evaporation_mm=evap,total_et_mm=evap+.675,end_depletion_mm=depletion+evap));depletion+=evap
    depletion=55.
    for raw in source_rows('fao56_ch8.html',37):
        ks=float(root_stress(160-depletion,160.,.4));et=ks*6.
        values=[5.,1.2,6.,depletion,ks,et,depletion+et]
        for index,(text,value) in enumerate(zip(raw[1:],values)):
            decimals=len(text.split('.')[1]);expected=float(text);tolerance=.5*10**(-decimals)+1e-9
            assert abs(value-expected)<=tolerance,('FAO37',raw[0],index,text,value)
            benchmark_rows.append(dict(example=37,day=int(raw[0]),column=index+1,source_text=text,published_value=expected,model_value=value,tolerance=tolerance))
        rows.append(dict(example=37,day=int(raw[0]),start_depletion_mm=depletion,ks=ks,actual_et_mm=et,end_depletion_mm=depletion+et));depletion+=et
    rng=np.random.default_rng(20261114);n=200;days=180
    wp=rng.uniform(.04,.20,n);fc=wp+rng.uniform(.08,.18,n);ze=rng.uniform(.10,.15,n);zr=rng.uniform(.6,1.8,n)
    tew=1000*(fc-.5*wp)*ze;profile=soil_profile(fc,wp,zr,ze,.3*tew)
    forcing=dict(water_mm=rng.uniform(0,50,(days,n))*(rng.random((days,n))<.12),eto_mm_day=rng.uniform(1,7,(days,n)),kcb=rng.uniform(0,1.1,(days,n)),p=rng.uniform(.4,.7,(days,n)))
    for name,value in dict(theta_wp=wp,theta_fc=fc,ze_m=ze,zr_m=zr,rew_mm=.3*tew,**forcing,**column_run(profile,forcing)).items():fields['random__'+name]=value
    for label,kcb in [('bare',0.),('crop',1.)]:
        forcing=dict(water_mm=np.zeros(60),eto_mm_day=np.full(60,4.5),kcb=np.full(60,kcb),p=np.full(60,.55))
        for name,value in column_run(soil_profile(.25,.1,1.,.1,9.),forcing).items():fields[label+'__'+name]=value
    amendment=PLAN.parent/'clock_amendment.json'
    assert subprocess.check_output(['git','show','HEAD:'+str(amendment.relative_to(ROOT))],cwd=ROOT)==amendment.read_bytes()
    bins=np.linspace(0,365,13);capture_start=365*7/12;crop_start=365*10.5/12;crop_end=365*2.5/12
    clock=field_clock(bins,event_edges_days=[capture_start,crop_start,crop_end])
    totals=np.arange(1,25,dtype=float).reshape(12,2)
    for name,value in dict(bin_edges_days=bins,edges_days=clock.edges_days,step_days=clock.step_days,bin_index=clock.bin_index,fraction_of_bin=clock.fraction_of_bin,monthly_totals=totals,distributed_totals=clock.spread_bin_totals(totals),capture_mask=clock.cyclic_window(capture_start,crop_start),crop_mask=clock.cyclic_window(crop_start,crop_end)).items():fields['clock__'+name]=value
    np.savez_compressed(out/'fields.npz',**fields)
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(benchmark_rows[0]));writer.writeheader();writer.writerows(benchmark_rows)
    (out/'benchmarks.csv').write_text(buffer.getvalue())
    sources={str((CACHE/name).relative_to(ROOT)):spec['sha256'] for name,spec in SOURCES.items() if name.endswith('.html')}
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,amendment,ROOT/'harvest/soil_drying.py',ROOT/'tests/test_soil_drying.py',ROOT/'harvest/field_clock.py',ROOT/'tests/test_field_clock.py']}
    write(out/'results.json',dict(status='component_and_synthetic_only',benchmarks=rows,benchmark_numeric_cells=len(benchmark_rows),source_tables='FAO56 Examples31/37; known published component checks, not blind validation',sources=sources,producers=producers,files_sha256={name:sha(out/name) for name in ('fields.npz','benchmarks.csv')},unchanged_sha256=protected,synthetic_profiles=n,synthetic_days=days,synthetic_profile_days=n*days,clock=dict(steps=len(clock.step_days),year_days=365,capture_days=float(clock.step_days[fields['clock__capture_mask']].sum()),crop_days=float(clock.step_days[fields['clock__crop_mask']].sum()),example_dates_qualified=False),adopt=False,earth_or_harvest_scores_computed=False,limits='Component gates do not qualify combined uptake allocation, local soil/flood access, root development or groundwater. Supplied clock dates and uniform within-bin disaggregation are not local observations. No new Earth field runs.'))
    print('Published components match all',len(benchmark_rows),'printed numeric cells;',n*days,'synthetic profile-days written')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT);main(parser.parse_args().out)
