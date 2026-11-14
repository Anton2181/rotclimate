"""Independent Decimal FAO checks and scalar physical-pool accounting."""
import csv,json,math,subprocess,sys
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from qualify_flood_storage_sources import Rows,CACHE
from settlement_locations_earth import sha,write
OUT=ROOT/'output/soil_drying_20261114'


def printed_rows(name,example):
    text=(CACHE/name).read_text(encoding='latin1');begin=text.index('EXAMPLE '+str(example));end=text.find('EXAMPLE',begin+20)
    parser=Rows();parser.feed(text[begin:end if end>=0 else len(text)])
    rows=[v for v in parser.rows if len(v)==8 and v[0] in {str(i) for i in range(1,11)}]
    assert len(rows)==10;return rows


def scalar_step(stock,capacity,rew,water,eto,kcb,p):
    # Physical pool order here is bound/top/deep, unlike producer state layout.
    before=list(stock);remaining=water;wet=[]
    for old,limit in zip(stock,capacity):
        fill=min(remaining,limit-old);wet.append(old+fill);remaining-=fill
    bound,top,deep=wet;cb,ct,cd=capacity;tew=cb+ct;taw=ct+cd
    de=tew-(bound+top)
    kr=1. if de<=rew else (tew-de)/(tew-rew)
    ke=min(kr*(1.2-kcb),1.2)
    ks=1. if top+deep>=(1-p)*taw else (top+deep)/((1-p)*taw)
    e=min(ke*eto,bound+top);top_e=min(top,e);bound_e=e-top_e
    top-=top_e;bound-=bound_e
    t=min(ks*kcb*eto,top+deep)
    top_t=t*top/(top+deep) if top+deep>0 else 0.;deep_t=t-top_t
    after=[bound,top-top_t,deep-deep_t]
    assert min(after)>-1e-10
    residual=math.fsum(before)+water-math.fsum(after)-e-t-remaining
    return after,dict(evaporation_mm=e,root_uptake_mm=t,drainage_mm=remaining,kr=kr,ke=ke,ks=ks),residual


def main():
    result=json.loads((OUT/'results.json').read_text())
    for name,digest in {**result['sources'],**result['producers'],**result['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert '90 passed' in json.loads((OUT/'controls.json').read_text())['stdout']
    with (OUT/'benchmarks.csv').open() as f:csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==140;cursor=0;decimal_max=0.
    with localcontext() as context:
        context.prec=40
        D=Decimal
        for example,name in [(31,'fao56_ch7.html'),(37,'fao56_ch8.html')]:
            depletion=D(0) if example==31 else D(55)
            for raw in printed_rows(name,example):
                if example==31:
                    kr=D(1) if depletion<=9 else (20-depletion)/11;ke=kr*D('1.05');e=ke*D('4.5')
                    expected=[depletion,D(1 if depletion<=9 else 2),kr,ke,e,depletion+e,e+D('.675')];depletion+=e
                else:
                    ks=min(D(1),(160-depletion)/96);e=ks*6
                    expected=[D(5),D('1.2'),D(6),depletion,ks,e,depletion+e];depletion+=e
                summary=next(v for v in result['benchmarks'] if v['example']==example and v['day']==int(raw[0]))
                mapping={31:[('start_depletion_mm',0),('kr',2),('ke',3),('soil_evaporation_mm',4),('end_depletion_mm',5),('total_et_mm',6)],37:[('start_depletion_mm',3),('ks',4),('actual_et_mm',5),('end_depletion_mm',6)]}
                for key,index in mapping[example]:assert abs(summary[key]-float(expected[index]))<1e-12
                for column,(text,value) in enumerate(zip(raw[1:],expected),1):
                    v=csv_rows[cursor];cursor+=1
                    assert int(v['example'])==example and int(v['day'])==int(raw[0]) and int(v['column'])==column and v['source_text']==text
                    rhs=text.rsplit('=',1)[-1].strip();observed=D(rhs)
                    tolerance=D('0.5')*D(10)**(-len(rhs.split('.')[1]))+D('1e-9') if '.' in rhs else D('1e-9')
                    assert abs(value-observed)<=tolerance
                    error=abs(float(value)-float(v['model_value']));assert error<1e-12;decimal_max=max(decimal_max,error)
    with np.load(OUT/'fields.npz') as archive:z={k:archive[k] for k in archive.files}
    max_mass=0.;max_state=0.;compartment_checks=0
    for i in range(200):
        fc=float(z['random__theta_fc'][i]);wp=float(z['random__theta_wp'][i]);ze=float(z['random__ze_m'][i]);zr=float(z['random__zr_m'][i])
        capacity=[500*wp*ze,1000*(fc-wp)*ze,1000*(fc-wp)*(zr-ze)]
        stock=capacity.copy()
        for name,value in zip(('bound_mm','top_mm','deep_mm'),stock):assert math.isclose(float(z['random__initial_'+name][i]),value,rel_tol=1e-14)
        for day in range(180):
            water=float(z['random__water_mm'][day,i]);eto=float(z['random__eto_mm_day'][day,i]);kcb=float(z['random__kcb'][day,i]);p=float(z['random__p'][day,i])
            stock,expected,residual=scalar_step(stock,capacity,float(z['random__rew_mm'][i]),water,eto,kcb,p)
            max_mass=max(max_mass,abs(residual));assert abs(residual)<1e-9
            for name,value in expected.items():
                actual=float(z['random__'+name][day,i]);assert abs(actual-value)<2e-10,(day,i,name,actual,value)
            for name,value,limit in zip(('bound_mm','top_mm','deep_mm'),stock,capacity):
                actual=float(z['random__'+name][day,i]);assert -1e-12<=actual<=limit+1e-12
                error=abs(actual-value);max_state=max(max_state,error);assert error<2e-10
                compartment_checks+=1
    for label,kcb in [('bare',0.),('crop',1.)]:
        stock=[5.,15.,135.];capacity=stock.copy()
        for day in range(60):
            stock,expected,residual=scalar_step(stock,capacity,9.,0.,4.5,kcb,.55)
            assert abs(residual)<1e-9
            for name,value in expected.items():assert abs(float(z[label+'__'+name][day])-value)<2e-10
            for name,value in zip(('bound_mm','top_mm','deep_mm'),stock):assert abs(float(z[label+'__'+name][day])-value)<2e-10
        if label=='bare':
            assert np.all(z['bare__root_uptake_mm']==0)
            assert np.all(z['bare__deep_mm']==135.)
            assert z['bare__evaporation_mm'].sum()<=20.+1e-10
    model_total=z['random__top_mm']+z['random__deep_mm']+z['random__bound_mm']
    initial=z['random__initial_top_mm']+z['random__initial_deep_mm']+z['random__initial_bound_mm']
    starts=np.concatenate([initial[None,:],model_total[:-1]],axis=0)
    residuals=starts+z['random__water_mm']-model_total-z['random__evaporation_mm']-z['random__root_uptake_mm']-z['random__drainage_mm']
    model_mass=float(np.abs(residuals).max());assert model_mass<1e-9
    annual=initial+z['random__water_mm'].sum(0)-model_total[-1]-z['random__evaporation_mm'].sum(0)-z['random__root_uptake_mm'].sum(0)-z['random__drainage_mm'].sum(0)
    assert np.max(np.abs(annual))<1e-8
    edges=z['clock__edges_days'];bins=z['clock__bin_edges_days'];dt=np.diff(edges)
    assert np.all((dt>0)&(dt<=1)) and np.isin(bins,edges).all()
    np.testing.assert_array_equal(dt,z['clock__step_days'])
    expected_totals=np.arange(1,25,dtype=float).reshape(12,2)
    np.testing.assert_array_equal(expected_totals,z['clock__monthly_totals'])
    with localcontext() as context:
        context.prec=40
        for step,(a,b) in enumerate(zip(edges[:-1],edges[1:])):
            for column in range(2):
                expected=Decimal(0)
                for month in range(12):
                    lo=max(Decimal.from_float(float(a)),Decimal.from_float(float(bins[month])))
                    hi=min(Decimal.from_float(float(b)),Decimal.from_float(float(bins[month+1])))
                    if hi>lo:expected+=Decimal(int(expected_totals[month,column]))*(hi-lo)/(Decimal.from_float(float(bins[month+1]))-Decimal.from_float(float(bins[month])))
                assert abs(float(expected)-z['clock__distributed_totals'][step,column])<1e-12
            month=int(z['clock__bin_index'][step]);assert bins[month]<=a<b<=bins[month+1]
            np.testing.assert_allclose(z['clock__fraction_of_bin'][step],(b-a)/(bins[month+1]-bins[month]),rtol=1e-14)
    for month in range(12):np.testing.assert_allclose(z['clock__distributed_totals'][z['clock__bin_index']==month].sum(0),expected_totals[month],rtol=1e-14,atol=1e-12)
    flood=z['clock__capture_mask'];crop=z['clock__crop_mask'];assert not (flood&crop).any()
    a=365*7/12;b=365*10.5/12;c=365*2.5/12
    np.testing.assert_array_equal(flood,(edges[:-1]>=a)&(edges[1:]<=b))
    np.testing.assert_array_equal(crop,(edges[:-1]>=b)|(edges[1:]<=c))
    assert math.isclose(dt[flood].sum(),365*3.5/12,abs_tol=1e-12)
    assert math.isclose(dt[crop].sum(),365*4/12,abs_tol=1e-12)
    assert not result['clock']['example_dates_qualified']
    fresh=OUT/'fresh';subprocess.run([sys.executable,str(ROOT/'scripts/soil_drying_benchmarks.py'),'--out',str(fresh)],cwd=ROOT,check=True)
    exact={}
    for name in ('results.json','fields.npz','benchmarks.csv'):
        assert (OUT/name).read_bytes()==(fresh/name).read_bytes(),name;exact[name]=sha(OUT/name)
    assert not result['adopt'] and not result['earth_or_harvest_scores_computed']
    write(OUT/'review.json',dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),method='Independent HTMLParser source rows, 40-digit Decimal component equations and scalar bound/top/deep simulation; Decimal clock overlap integration; producer/model functions not imported',benchmark_numeric_cells=140,synthetic_profile_days=36000,compartment_checks=compartment_checks,clock_segments=len(dt),clock_source_columns=2,max_decimal_vs_model_mm=decimal_max,max_scalar_daily_mass_residual_mm=max_mass,max_model_daily_mass_residual_mm=model_mass,max_model_180day_mass_residual_mm=float(np.max(np.abs(annual))),max_state_error_mm=max_state,fresh_byte_exact=exact,protected_files=len(result['unchanged_sha256']),adopt=False))
    print('Passed140published cells,36000scalar days,',compartment_checks,'compartment checks;3fresh files exact; maxmass',max_mass)


if __name__=='__main__':main()
