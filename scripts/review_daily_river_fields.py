"""Independent compiled scalar joint ledger for every daily development case."""
import csv,gzip,json,math,sys
from pathlib import Path
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.field_clock import field_clock
from land_people import CROPS,DAYS
from settlement_locations_earth import sha,write
OUT=ROOT/'output/daily_river_fields_20261114'
STOCKS=['top_mm','deep_mm','bound_mm','pond_mm']
FLUXES=['infiltration_mm','delivered_mm','surface_evap_mm','bare_diffusion_mm','root_uptake_mm','root_potential_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm']


@njit(cache=True)
def reference(P,PET,area,dt,binid,cropwin,flood,eligible,source,zr,bg,pondcap,eff,capture,kcb):
    nf=len(area);nt=len(dt);s=np.zeros((nf,4));scratch=np.zeros((nf,4));cd=150*(zr-.1)
    for year in range(1,51):
        initial=s.copy();annual=np.zeros((19,nf));monthly=np.zeros((15,12));daily=np.zeros((4,nt));maxres=0.
        for t in range(nt):
            m=binid[t];days=dt[t];demand=0.
            for i in range(nf):
                release=0. if flood[t] else s[i,3]
                surf=s[i,3]-release+.8*P[m,i]*days/DAYS
                limit=min(max(20+cd-s[i,0]-s[i,1]-s[i,2],0.),20*days)
                request=max(limit+(pondcap if flood[t] else 0.)-surf,0.) if capture and flood[t] else 0.
                scratch[i,0]=release;scratch[i,1]=surf;scratch[i,2]=limit;scratch[i,3]=request
                demand+=request*area[i]/1000.
            gross=min(source[t],demand/eff);delivered=gross*eff;ratio=delivered/demand if demand>0 else 0.
            monthly[11,m]+=demand;monthly[12,m]+=delivered;monthly[13,m]+=gross-delivered;monthly[14,m]+=source[t]-gross
            for i in range(nf):
                before=s[i].sum();rain=P[m,i]*days/DAYS;eto=PET[m,i]/DAYS
                supply=scratch[i,3]*ratio;surf=scratch[i,1]+supply;inf=min(surf,scratch[i,2]);surf-=inf
                pond=min(surf,pondcap if flood[t] else 0.);overflow=surf-pond;covered=pond>0
                pe=min(pond,eto*days);pond-=pe
                top=s[i,0];deep=s[i,1];bound=s[i,2];water=inf
                new=min(5.,bound+water);water=max(water-(new-bound),0.);bound=new
                new=min(15.,top+water);water=max(water-(new-top),0.);top=new
                new=min(cd,deep+water);water=max(water-(new-deep),0.);deep=new
                grow=cropwin[t] and eligible[i];b=kcb if grow else bg
                de=20-top-bound;kr=1. if de<=9 else (20-de)/11
                ke=min(kr*(1.2-b),.3 if grow else 1.2)
                wetroot=top+deep;ks=min(1.,wetroot/(.45*(15+cd)))
                effective=0. if covered else eto
                evap=min(ke*effective*days,top+bound)
                ta=max(top-evap,0.);ba=max(bound-max(evap-top,0.),0.)
                evap=(top-ta)+(bound-ba);top=ta;bound=ba
                root=0.;diff=0.;potential=kcb*eto*days if grow else 0.
                if grow:
                    target=min(ks*kcb*effective*days,top+deep);fraction=target/(top+deep) if top+deep>0 else 0.
                    ta=top*(1-fraction);da=deep*(1-fraction);root=(top-ta)+(deep-da);top=ta;deep=da
                else:diff=min(bg*effective*days,deep);deep-=diff
                s[i,0]=top;s[i,1]=deep;s[i,2]=bound;s[i,3]=pond
                values=(inf,supply,evap,diff,root,potential,pe,scratch[i,0],overflow,water,.2*rain)
                for j in range(11):annual[8+j,i]+=values[j];monthly[j,m]+=values[j]*area[i]/1000.
                for j in range(4):daily[j,t]+=s[i,j]*area[i]/1000.
                residue=before+rain+supply-s[i].sum()-evap-diff-root-pe-scratch[i,0]-overflow-water-.2*rain
                maxres=max(maxres,abs(residue))
        residual=np.max(np.abs(s-initial))
        if residual<=1e-6:break
    annual[:4]=initial.T;annual[4:8]=s.T
    return annual,monthly,daily,year,residual,maxres


def main():
    r=json.loads((OUT/'results.json').read_text());assert len(r['rows'])==256
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    core=json.loads((OUT/'core/review.json').read_text());assert core['status']=='passed_before_earth_outputs'
    with np.load(OUT/'fields.npz') as archive:z={name:archive[name] for name in archive.files}
    with np.load(ROOT/'output/flood_basin_storage_20261114/fields.npz') as archive:
        for region in ['nile','mesopotamia_euphrates_only']:
            for name in ['lat','lon','area_km2','T','P','PET','qualified']:np.testing.assert_array_equal(z[region+'__'+name],archive[region+'__'+name])
    phase=json.loads((ROOT/'output/flood_basin_seasonality_20261113/results.json').read_text())
    checks=0;field_days=0;maxstate=0.;maxledger=0.;columns=['initial_'+k for k in STOCKS]+['final_'+k for k in STOCKS]+['annual_'+k for k in FLUXES]
    for row in r['rows']:
        case=row['case'];b=row['region'];area=z[b+'__area_km2']*1e6;T=z[b+'__T'];P=z[b+'__P'];PET=z[b+'__PET'];c=CROPS[row['crop']]
        begin=365*(10 if row['calendar']=='old' else 10.5)/12;end=365*(3 if row['calendar']=='old' else 2.5)/12;flood=365*7/12
        clock=field_clock(np.linspace(0,365,13),event_edges_days=[begin,end,flood]);cw=clock.cyclic_window(begin,end);fw=clock.cyclic_window(flood,begin)
        eligibility=[]
        for i in range(len(area)):
            ts=T[clock.bin_index[cw],i];heat=math.fsum(max(float(v)-c['base'],0)*float(d) for v,d in zip(ts,clock.step_days[cw]))
            eligibility.append(bool(np.all((ts>=c['window'][0])&(ts<=c['window'][1])) and ts.max()>=c['need_warm'] and heat>=c['heat']))
        eligible=np.array(eligibility);np.testing.assert_array_equal(eligible,z[case+'__eligible'])
        gauge='aswan' if b=='nile' else 'hit';q=next(v for v in phase['rows'] if v['id']==gauge)['mean_monthly_flow_m3s'];mean=math.fsum(q)/12
        monthlysource=np.array([max(v-mean,0)*DAYS*86400 for v in q]);np.testing.assert_allclose(z[b+'__source_m3'],monthlysource,rtol=1e-14)
        source=monthlysource[clock.bin_index]*clock.fraction_of_bin
        annual,monthly,daily,years,residual,mass=reference(P,PET,area,clock.step_days,clock.bin_index,cw,fw,eligible,source,row['root_depth_m'],row['bare_background'],row['pond_capacity_mm'],row['efficiency'],row['capture'],c['kc'])
        assert years==row['spinup_years'] and (residual<=1e-6)==row['periodic'],case
        maxledger=max(maxledger,float(mass));assert mass<1e-8
        for j,name in enumerate(columns):
            actual=z[case+'__'+name];error=float(np.max(np.abs(actual-annual[j])));maxstate=max(maxstate,error)
            np.testing.assert_allclose(actual,annual[j],rtol=2e-10,atol=2e-8,err_msg=case+' '+name)
        month_names=FLUXES+['river_requested_m3','river_delivered_m3','river_loss_m3','river_outlet_m3']
        for j,name in enumerate(month_names):np.testing.assert_allclose(z[case+'__monthly_'+name],monthly[j],rtol=2e-10,atol=.01,err_msg=case+' '+name)
        for j,name in enumerate(STOCKS):np.testing.assert_allclose(z[case+'__daily_'+name],daily[j],rtol=2e-10,atol=.01)
        expected_cov=np.divide(annual[12],annual[13],out=np.zeros(len(area)),where=annual[13]>0)
        np.testing.assert_allclose(z[case+'__root_coverage'],expected_cov,atol=2e-10)
        assert math.isclose(row['eligible_area_km2'],area[eligible].sum()/1e6,abs_tol=1e-6)
        assert math.isclose(row['root_coverage'],float(np.average(expected_cov[eligible],weights=area[eligible])),abs_tol=2e-10)
        assert math.isclose(row['adequate_root_area_km2'],area[eligible&(expected_cov>=.95)].sum()/1e6,abs_tol=1e-6)
        assert abs(row['joint_mass_residual_m3'])<.01
        checks+=1;field_days+=len(area)*len(clock.step_days)
        if checks%32==0:print('Reviewed',checks,'/256',flush=True)
    bycase={row['case']:row for row in r['rows']};csv_rows=0
    with gzip.open(OUT/'fields.csv.gz','rt',newline='') as stream:
        for v in csv.DictReader(stream):
            case=v['case'];i=int(v['field']);region=bycase[case]['region'];assert float(v['latitude'])==z[region+'__lat'][i] and float(v['longitude'])==z[region+'__lon'][i]
            assert float(v['area_km2'])==z[region+'__area_km2'][i];ok=bool(z[case+'__eligible'][i]);assert int(v['eligible'])==ok
            if ok:assert float(v['root_coverage'])==z[case+'__root_coverage'][i]
            else:assert v['root_coverage']==''
            for name in columns:assert float(v[name])==z[case+'__'+name][i]
            csv_rows+=1
    assert not r['adopt'] and not r['heldout_qualified'] and not r['harvest_or_population_scored']
    fresh=OUT/'fresh';exact={}
    for name in ['results.json','fields.npz','fields.csv.gz']:
        assert (fresh/name).exists(),'Wait for the independent fresh producer run'
        assert (fresh/name).read_bytes()==(OUT/name).read_bytes(),name;exact[name]=sha(OUT/name)
    write(OUT/'review.json',dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),method='Independent compiled scalar soil/pond/node ledger for every field and spinup; raw retained inputs, thermal eligibility and all CSV cells checked; producer/coupler not imported',scenario_rows=checks,field_days=field_days,csv_rows=csv_rows,max_scalar_daily_mass_residual_mm=maxledger,max_annual_field_difference_mm=maxstate,fresh_byte_exact=exact,protected_files=len(r['unchanged_sha256']),adopt=False))
    print('Passed all256cases;',field_days,'fielddays;',csv_rows,'CSVrows;maxfielddiff',maxstate)


if __name__=='__main__':main()
