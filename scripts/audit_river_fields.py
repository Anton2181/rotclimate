"""Independent bare FAO31 and synthetic river/pond/soil accounting before Earth runs."""
import argparse,json,math,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.field_clock import field_clock
from harvest.soil_drying import soil_profile,soil_state
from harvest.river_fields import bare_soil_step,field_year,RiverClock
from settlement_locations_earth import sha,write
OUT=ROOT/'output/daily_river_fields_20261114/core'


def scalar_soil(stock,water,eto,dt,cropped,kcb,bg,p,ct=15.,cd=135.,cb=5.,rew=9.):
    # Physical stock order is bound/top/deep here.
    bound,top,deep=map(float,stock);remaining=float(water)
    new=[]
    for old,cap in [(bound,cb),(top,ct),(deep,cd)]:
        amount=min(remaining,max(cap-old,0));new.append(old+amount);remaining-=amount
    bound,top,deep=new;de=ct+cb-top-bound
    kr=1 if de<=rew else (ct+cb-de)/(ct+cb-rew)
    basal=kcb if cropped else bg;ke=min(kr*(1.2-basal),.25*1.2 if cropped else 1.2)
    e=min(ke*eto*dt,top+bound);et=min(top,e);top-=et;bound-=e-et
    if cropped:
        # Ks is from the wetted state, before surface extraction.
        wetroot=new[1]+new[2];ks=min(1,wetroot/((1-p)*(ct+cd)))
        uptake=min(ks*kcb*eto*dt,top+deep);fraction=uptake/(top+deep) if top+deep else 0
        top*=1-fraction;deep*=1-fraction;diffusion=0.
    else:diffusion=min(bg*eto*dt,deep);deep-=diffusion;uptake=0.
    return [bound,top,deep],dict(surface_evap_mm=e,bare_diffusion_mm=diffusion,root_uptake_mm=uptake,soil_drainage_mm=remaining)


def scalar_year(a,pondcap,infilrate,eff,bg):
    nf=len(a['area_m2']);nt=len(a['clock'].step_days);nn=a['source_m3'].shape[1]
    stock=np.zeros((nf,3));pond=np.zeros(nf);trace={k:[] for k in ['bound_mm','top_mm','deep_mm','pond_mm','delivered_mm','river_delivered_m3','river_loss_m3','river_outlet_m3','surface_evap_mm','bare_diffusion_mm','root_uptake_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm']}
    for t,dt in enumerate(a['clock'].step_days):
        before=stock.sum(1)+pond;release=np.where(a['pond_mask'][t],0,pond);pond-=release
        surface=pond+.8*a['rain_mm'][t];limit=np.minimum(155-stock.sum(1),infilrate*dt)
        caps=np.where(a['pond_mask'][t],pondcap,0)
        req=np.where(a['capture_mask'][t],np.maximum(limit+caps-surface,0),0)
        demand=[math.fsum(float(req[i]*a['area_m2'][i]/1000) for i in range(nf) if a['field_nodes'][i]==node) for node in range(nn)]
        available=list(a['source_m3'][t]);delivered=np.zeros(nn);loss=np.zeros(nn);outlet=np.zeros(nn)
        for node in reversed(a['clock'].river_order):
            useful=min(demand[node],available[node]*eff);withdraw=useful/eff;available[node]-=withdraw
            delivered[node]=useful;loss[node]=withdraw-useful;parent=a['clock'].river_receiver[node]
            if parent<0:outlet[node]=available[node]
            else:available[parent]+=available[node]
        delivery=np.array([req[i]*delivered[node]/demand[node] if demand[node]>0 else 0 for i,node in enumerate(a['field_nodes'])]);surface+=delivery
        infiltration=np.minimum(surface,limit);surface-=infiltration
        pond=np.minimum(surface,caps);overflow=surface-pond;covered=pond>0
        pond_e=np.minimum(pond,a['eto_mm_day'][t]*dt);pond-=pond_e
        flux={k:np.zeros(nf) for k in ['surface_evap_mm','bare_diffusion_mm','root_uptake_mm','soil_drainage_mm']}
        for i in range(nf):
            stock[i],f=scalar_soil(stock[i],infiltration[i],0 if covered[i] else a['eto_mm_day'][t,i],float(dt),bool(a['crop_mask'][t,i]),.75,bg,.55)
            for name,value in f.items():flux[name][i]=value
        final=stock.sum(1)+pond
        residual=before+a['rain_mm'][t]+delivery-final-.2*a['rain_mm'][t]-release-overflow-pond_e-sum(flux.values())
        assert np.max(np.abs(residual))<1e-9
        for name,value in dict(bound_mm=stock[:,0],top_mm=stock[:,1],deep_mm=stock[:,2],pond_mm=pond,delivered_mm=delivery,river_delivered_m3=delivered,river_loss_m3=loss,river_outlet_m3=outlet,pond_evap_mm=pond_e,pond_release_mm=release,surface_overflow_mm=overflow,**flux).items():trace[name].append(value.copy())
    return {k:np.asarray(v) for k,v in trace.items()}


def main(out=OUT):
    tests=['test_river_fields.py','test_field_clock.py','test_soil_drying.py','test_flood_storage.py','test_flood_water.py','test_flood_timing.py','test_flood_gauge_quality.py']
    control=subprocess.run([sys.executable,'-m','pytest','-q',*[str(ROOT/'tests'/v) for v in tests]],cwd=ROOT,capture_output=True,text=True,check=True)
    assert '105 passed' in control.stdout
    profile=soil_profile(.25,.1,1.,.1,9.);state=soil_state(profile,1.);bare=[]
    for day in range(10):
        r=bare_soil_step(profile,state,0,4.5,.15);total=float(r.evaporation_mm+r.diffusion_mm)
        assert abs(float(state.total_mm-r.state.total_mm)-total)<1e-10
        bare.append(dict(day=day+1,surface_et_mm=float(r.evaporation_mm),diffusion_mm=float(r.diffusion_mm),total_et_mm=total,deep_mm=float(r.state.deep_mm)));state=r.state
    source=json.loads((ROOT/'output/soil_drying_20261114/results.json').read_text())['benchmarks']
    for row in bare:
        old=next(v for v in source if v['example']==31 and v['day']==row['day'])
        assert abs(row['surface_et_mm']-old['soil_evaporation_mm'])<1e-12 and abs(row['total_et_mm']-old['total_et_mm'])<1e-12
    rng=np.random.default_rng(20261115);base=field_clock(np.linspace(0,12,13),event_edges_days=[3.5,7.25,8.])
    nt=len(base.step_days);max_error=0.;fields={};field_steps=0
    for case in range(100):
        nf=int(rng.integers(2,10));nn=int(rng.integers(1,6));recv=np.array([-1]+[int(rng.integers(-1,i)) for i in range(1,nn)])
        crop=np.broadcast_to(base.cyclic_window(8.,1.)[:,None],(nt,nf));pond=np.broadcast_to(base.cyclic_window(3.5,7.25)[:,None],(nt,nf))
        a=dict(profile=profile,area_m2=rng.uniform(500,5000,nf),field_nodes=rng.integers(0,nn,nf),source_m3=rng.uniform(0,200,(nt,nn)),clock=RiverClock(base,np.arange(nn),recv),rain_mm=rng.uniform(0,20,(nt,nf))*(rng.random((nt,nf))<.25),eto_mm_day=rng.uniform(0,7,(nt,nf)),crop_mask=crop,capture_mask=pond,pond_mask=pond,crop_kcb=.75)
        cap=float(rng.uniform(0,50));rate=float(rng.uniform(5,30));eff=float(rng.uniform(.5,1));bg=.15 if case%2 else 0.
        actual=field_year(**a,pond_capacity_mm=cap,infiltration_mm_day=rate,efficiency=eff,bare_background=bg)
        expected=scalar_year(a,cap,rate,eff,bg)
        for name,value in expected.items():
            error=float(np.max(np.abs(actual[name]-value)));max_error=max(max_error,error)
            np.testing.assert_allclose(actual[name],value,rtol=2e-12,atol=1e-9,err_msg=str(case)+' '+name)
            fields[f'{case:03}__'+name]=actual[name]
        for name in ('area_m2','field_nodes','source_m3','rain_mm','eto_mm_day','crop_mask','capture_mask','pond_mask'):fields[f'{case:03}__'+name]=a[name]
        fields[f'{case:03}__parameters']=np.array([cap,rate,eff,bg]);fields[f'{case:03}__receiver']=recv
        field_steps+=nt*nf
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'synthetic.npz',**fields)
    paths=[Path(__file__),ROOT/'harvest/river_fields.py',ROOT/'tests/test_river_fields.py']
    write(out/'review.json',dict(status='passed_before_earth_outputs',producers={str(p.relative_to(ROOT)):sha(p) for p in paths},controls_stdout=control.stdout,full_bare_FAO31=bare,synthetic_forests=100,synthetic_field_steps=field_steps,scalar_history_max_error=max_error,synthetic_sha256=sha(out/'synthetic.npz'),earth_or_harvest_scores=False))
    print('Core passed105controls, fullbareFAO31,100forests,',field_steps,'joint field steps;maxerror',max_error)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT);main(parser.parse_args().out)
