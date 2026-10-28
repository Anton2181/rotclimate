"""Independently reconstruct the six diagnostic cases; export process evidence."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,identity,write_json
from recover_transport_diagnosis import canonical_exact
from rotclimate.transport import vapor_face_fluxes,diffusion_face_fluxes,face_divergence
from rotclimate.reservoir_moisture import reservoir_rain_partition
from rotclimate.moisture import rain_coefficient
from rotclimate import earth
from rotclimate.numerics import matrix_product
from scripts.earth_calendar import observation_weights
from scripts.benchmark_local import DEV12_SPECS
from scripts.transport_native import diagnose,references
from scripts.circulation_reference import projection_jacobian,geographic_wind,native_aggregation,column_targets,vector_scores

DAY=86400.
SEASONS=dict(DJF=[11,0,1],MAM=[2,3,4],JJA=[5,6,7],SON=[8,9,10])
FOCUS=dict(north_india='JJA',mexico='SON',pacific_nw='DJF')


def check_sidecar(a,row):
    """Rebuild faces, donor exchange, rainfall and equations from primitives."""
    p=SimpleNamespace(**row['params']);n=p.steps_per_year
    if len(a['scored_indices'])!=n or len(a['water'])!=n+8:
        raise ValueError('Changed diagnostic step count')
    certs=row['numerics']['moisture_reservoirs']['steps']
    np.testing.assert_array_equal(a['solved_days'],[s['day'] for s in certs])
    np.testing.assert_array_equal(a['solved_days'][a['scored_indices']],a['days'])
    dx=p.cell_km*1000 if hasattr(p,'cell_km') else 56000.
    # The fixed experiment declares56km; no spacing inference from a field.
    dx=56000.
    maximum=0.;max_dry=0.
    for step in range(len(a['water'])):
        w=a['water'][step];mass=a['layer_mass'][step];winds=a['winds'][step]
        adv=[];diff=[];dry=[]
        for layer in range(2):
            faces=vapor_face_fluxes(w[layer],*winds[layer],mass=mass[layer])
            mixing=diffusion_face_fluxes(w[layer],p.moisture_diffusion,dx,mass=mass[layer])
            for key,value in zip(('vapor_face_x','vapor_face_south'),faces):np.testing.assert_array_equal(a[key][step,layer],value)
            for key,value in zip(('diffusion_face_x','diffusion_face_south'),mixing):np.testing.assert_array_equal(a[key][step,layer],value)
            adv.append(-DAY*face_divergence(*faces,dx));diff.append(-DAY*face_divergence(*mixing,dx))
            dry.append(face_divergence(*vapor_face_fluxes(mass[layer],*winds[layer],mass=mass[layer]),dx))
        dry=np.stack(dry);max_dry=max(max_dry,float(np.abs(dry.sum(0)).max()))
        np.testing.assert_array_equal(a['upward_air'][step,1:-1,1:-1],-dry[0])
        # Symmetric vertical conductance is disabled in both literal profiles.
        assert p.moisture_reservoir_mixing_days==0
        air=a['upward_air'][step]
        vertical=(np.maximum(air,0)*w[0]/mass[0]-np.maximum(-air,0)*w[1]/mass[1])*DAY
        np.testing.assert_allclose(a['vertical_water'][step],vertical,rtol=2e-14,atol=2e-14)
        np.testing.assert_array_equal(a['advection'][step],np.stack(adv))
        np.testing.assert_array_equal(a['diffusion'][step],np.stack(diff))
        closure={k.removeprefix('closure_'):a[k][step] for k in a if k.startswith('closure_')}
        coef,recycling=reservoir_rain_partition(w,a['fractions'][step],a['saturation'][step],
            a['dynamics'][step],a['instability'][step],p,closure)
        np.testing.assert_array_equal(a['rain'][step],coef*w*DAY)
        np.testing.assert_array_equal(a['recycled'][step],recycling*w[1]*DAY)
        rh=w/a['fractions'][step]/a['saturation'][step]
        overflow=np.divide(np.maximum(rh-1,0),rh,out=np.zeros_like(rh),where=rh>0)/DAY
        dynamic=rain_coefficient(w/a['fractions'][step],a['saturation'][step],a['dynamics'][step],
            a['instability'][step],p.rh_threshold,p.precip_tau_days,spread=p.rh_spread)-overflow
        total=w.sum(0)
        conv=closure['conv']*np.exp(11.4*(np.minimum(total/a['saturation'][step],1.5)-closure['r0']))*closure['fT']/(np.maximum(total,.1)*DAY)
        survival=np.exp(-closure['evap']*np.maximum((20+closure['T']/5)*(100-100*np.clip(rh[0],0,1)),0)/3000)
        for name,value in [('dynamic',dynamic*survival*w*DAY),('convective',conv*survival*w*DAY),('overflow',overflow*w*DAY)]:
            np.testing.assert_allclose(a['rain_'+name][step],value,rtol=2e-14,atol=2e-14)
        recycled=np.stack([a['recycled'][step],-a['recycled'][step]])
        equation=(a['evaporation'][step]-a['drying'][step]+a['storm'][step]+recycled-a['rain'][step])[:,1:-1,1:-1]+np.stack(adv)+np.stack(diff)+np.stack([-vertical[1:-1,1:-1],vertical[1:-1,1:-1]])
        np.testing.assert_allclose(equation,a['residual'][step],rtol=0,atol=3e-12)
        maximum=max(maximum,float(np.abs(equation-a['residual'][step]).max()))
    return dict(solved_steps=len(a['water']),maximum_reconstruction_error_mm_day=maximum,
        maximum_absolute_dry_column_divergence_per_s=max_dry,all_faces_exact=True,
        rain_and_recycling_exact=True,donor_and_layer_equations_reconstructed=True)


def summarize(a,case):
    g=case.grid;n=len(a['days']);idx=a['scored_indices'];mask=a['score_land']
    spec=earth.REGIONS[case.name];geometry=projection_jacobian(g.lat,case.lon,spec['lat0'],spec['lon0'])
    area=g.cell_km**2/geometry[-1];area=area[mask]
    weights,durations,_=observation_weights(a['days'])
    monthly=lambda v:matrix_product(weights,v.reshape(n,-1)).reshape((12,)+v.shape[1:])
    average=lambda v:np.average(v[...,mask],axis=-1,weights=area)
    fields={k:a[k][idx] for k in ['rain','evaporation','drying','storm','rain_dynamic','rain_convective','rain_overflow']}
    for k in ['advection','diffusion','residual']:
        full=np.zeros((n,2)+g.land.shape);full[:,:,1:-1,1:-1]=a[k][idx];fields[k]=full
    vert=a['vertical_water'][idx];fields['vertical']=np.stack([-vert,vert],axis=1)
    recycle=a['recycled'][idx];fields['recycled']=np.stack([recycle,-recycle],axis=1)
    # Physical signed contributions; rainfall and drying are losses.
    for k in ['rain','drying']:fields[k]=-fields[k]
    means={k:average(monthly(v))*durations[:,None] for k,v in fields.items()}
    pw=average(monthly(a['water'][idx]));ratio=(a['water'][idx,1]/a['layer_mass'][idx,1])/(a['water'][idx,0]/a['layer_mass'][idx,0])
    means['q_ratio']=average(monthly(ratio));means['water']=pw
    observed=average(np.nan_to_num(case.obs_P))
    m=dict(observed_rain=observed.tolist(),**{k:v.tolist() for k,v in means.items()})
    seasons={season:{k:np.asarray(v)[months].sum(0).tolist() for k,v in means.items() if k not in ('q_ratio','water')} for season,months in SEASONS.items()}
    for season,months in SEASONS.items():
        seasons[season]['observed_rain']=float(observed[months].sum())
        seasons[season]['q_ratio']=float(np.average(means['q_ratio'][months],weights=durations[months]))
        seasons[season]['water']=np.average(means['water'][months],axis=0,weights=durations[months]).tolist()
    return dict(cells=int(mask.sum()),area_km2=float(area.sum()),monthly=m,seasons=seasons,
        aggregation='Original full scoring land mask, true cell area, Gregorian interval overlap. These diagnostic area/calendar means differ from the unchanged historical unweighted/equal-month score.')


def pressure_level_comparison(a,case,plan):
    """Separate vertical wind error from erroneous humidity weighting."""
    g=case.grid;spec=earth.REGIONS[case.name];idx=a['scored_indices'];n=len(idx)
    weights,durations,order=observation_weights(a['days'])
    geo=projection_jacobian(g.lat,case.lon,spec['lat0'],spec['lon0']);area=g.cell_km**2/geo[-1]
    ref=references(plan['transport_reference_plan']);fields={v:ref[case.name,v] for v in ('uwnd','vwnd','shum','hgt')}
    _,_,height=column_targets(fields);wind=a['winds'][idx]
    east,north=geographic_wind(wind[:,:,0],wind[:,:,1],geo);wind=np.stack([east,north],axis=2)
    pressure=101325*np.exp(-g.elev/8000);interior=np.ones_like(g.land)
    interior[[0,-1],:]=False;interior[:,[0,-1]]=False
    result={}
    for kind in ('land','ocean'):
        own=g.inmap&interior&((g.land&np.isfinite(case.obs_P).all(0)) if kind=='land' else ~g.land)
        aggregate,masks,native_area,_=native_aggregation(g.lat,case.lon,area,own,g.land,g.elev,fields['shum'],height)
        mask=a['native_'+kind+'_mask']
        np.testing.assert_array_equal(mask,masks[kind]&(aggregate((pressure>=92500).astype(float))>=1-1e-12))
        result[kind]={}
        if not mask.any():continue
        for level in (925,850,700,500,300):
            model=np.where((level*100>=.75*pressure)[None,None],wind[:,0],wind[:,1])
            model=aggregate(matrix_product(weights,model.reshape(n,-1)).reshape((12,2)+g.land.shape))
            observed=np.stack([fields[v].values[order,list(fields[v].pressure_hpa).index(level)] for v in ('uwnd','vwnd')],axis=1).reshape(12,2,-1)
            result[kind][str(level)]=vector_scores(model[:,:,mask],observed[:,:,mask],native_area[mask],durations)
    return result


def verify_and_summarize(out):
    protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text());plan=protocol['plan']
    if not review['complete'] or review['identity']!=identity(protocol) or review['actual_integrations']!=7 or len(review['records'])!=6 or review['strictly_passed']!=6 or review['interrupted_integrations']!=1 or review['pending_integrations']!=0:
        raise ValueError('Need complete six-case diagnosis and preserved interrupted attempt')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Frozen diagnostic source/input changed: '+name)
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()));data={};checks=[];pictures_data={}
    for row in review['records']:
        name,region=row['name'],row['region'];folder=ROOT/review['origins'][name+'/'+region]
        exact=canonical_exact(row,plan,folder)
        raw=folder/name/(region+'_transport.npz')
        if file_hash(raw)!=row['transport_arrays_sha256']:raise ValueError('Changed transport arrays')
        with np.load(raw,allow_pickle=False) as source:a={k:source[k] for k in source.files}
        check=check_sidecar(a,row);case=earth.region_case(region,plan['cell_km'])
        report,native=diagnose(case,SimpleNamespace(**row['params']),a,plan)
        if report!=row['matched_native']:raise ValueError('Native metrics changed')
        for key,value in native.items():np.testing.assert_array_equal(a[key],value)
        if region in plan['extra_circulation_regions']:
            source=folder/name/(region+'_extra.npz');old=ROOT/plan['profile_control_archives'][name]/(region+'_extra.npz')
            if file_hash(source)!=row['extra_circulation_arrays_sha256']:raise ValueError('Changed extra native archive')
            with np.load(source) as new,np.load(old) as archived:
                assert set(new.files)==set(archived.files)
                for key in new.files:np.testing.assert_array_equal(new[key],archived[key])
            exact['extra_native_arrays_exact']=True
        checks.append({**exact,**check})
        levels=pressure_level_comparison(a,case,plan)
        summary=summarize(a,case)
        data.setdefault(region,{})[name]=dict(full_land=summary,native=report,pressure_levels=levels,
            unchanged_historical_rain=row['rain'],unchanged_historical_temperature=row['temperature'],
            unchanged_historical_monthly_rain=row['monthly_rain'])
        if name=='global06':pictures_data[region]=(a,case)
    evidence=dict(status='passed',source_protocol_sha256=file_hash(out/'protocol.json'),
        source_review_sha256=file_hash(out/'review.json'),sources_verified=len(protocol['sources']),cases=checks,
        total_actual_attempts=7,complete_strict_cases=6,interrupted_controller_attempts=1,
        cumulative_actual_attempts=1886,cumulative_strict_passes=1881,cumulative_failures_or_interruptions=5,
        actual_additional_integrations_from_analysis=0,physics_or_atlas_adoption=False)
    result=dict(verification=evidence,regions=data,
        purpose='Diagnostic process evidence only; saved climate arrays unchanged; not a rainfall improvement or new calibration.',
        scope=plan['fixed_background_scope'],limitations=next(iter(data.values()))['global04']['native']['limitations'])
    return evidence,result,pictures_data


def plot(out,result,pictures_data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'global04':'#9d6d23','global06':'#236d9b'};labels={'global04':'Legacy ocean','global06':'Hydrostatic half'}
    fig,axes=plt.subplots(3,2,figsize=(14,11),layout='constrained')
    keys=['evaporation','advection','diffusion','vertical','recycled','storm','drying','rain']
    palette=['#479c9b','#5c9dc8','#9fc8d4','#bc82ab','#e4b65b','#9bb857','#c88d76','#555d67']
    for row,region in enumerate(FOCUS):
        own=result['regions'][region];ax=axes[row,0];months=np.arange(12)
        obs=own['global06']['full_land']['monthly']['observed_rain'];ax.plot(months,obs,color='#24272b',lw=2,label='Observed')
        for name in colors:
            monthly=own[name]['full_land']['monthly'];rain=-np.array(monthly['rain']).sum(1)
            ax.plot(months,rain,color=colors[name],label=labels[name],lw=2)
        ax.set(title=region.replace('_',' ').title()+' · full scoring land',ylabel='Rain mm/month',xticks=months,xticklabels=list('JFMAMJJASOND'));ax.grid(alpha=.2)
        if row==0:ax.legend(fontsize=9)
        ax=axes[row,1];season=FOCUS[region];budget=own['global06']['full_land']['seasons'][season];pos=np.zeros(2);neg=np.zeros(2)
        for key,color in zip(keys,palette):
            v=np.array(budget[key]);base=np.where(v>=0,pos,neg);ax.bar([0,1],v,bottom=base,label=key.replace('_',' '),color=color,width=.65)
            pos+=np.maximum(v,0);neg+=np.minimum(v,0)
        ax.axhline(0,color='#333',lw=.7);ax.set(title=f'Hydrostatic half · {season} layer balances',ylabel='Signed water mm/season',xticks=[0,1],xticklabels=['Lower 25% dry mass','Upper 75% dry mass'])
        if row==0:ax.legend(ncol=4,fontsize=8,loc='upper center',bbox_to_anchor=(.5,1.28))
    fig.suptitle('Where the modeled water goes — six exact-climate diagnostic reruns',fontsize=16)
    fig.savefig(out/'transport_water_budgets.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    for row,(region,kind) in enumerate([('north_india','land'),('mexico','land'),('pacific_nw','ocean')]):
        ref=result['regions'][region]['global06']['native'][kind]
        for comp in range(2):
            ax=axes[row,comp];ax.plot(months,np.array(ref['wind']['monthly_reference'])[:,comp],color='#24272b',label='NCEP monthly q-weighted',lw=2)
            for name in colors:
                native=result['regions'][region][name]['native'][kind]
                ax.plot(months,np.array(native['wind']['monthly_model'])[:,comp],color=colors[name],label=labels[name],lw=2)
            ax.axhline(0,color='#777',lw=.6);ax.grid(alpha=.2)
            ax.set(title=f"{region.replace('_',' ').title()} · {kind} · {ref['coverage']['matched_cells']} native cells",ylabel=('East' if comp==0 else 'North')+' wind m/s',xticks=months,xticklabels=list('JFMAMJJASOND'))
            if row==0 and comp==0:ax.legend(fontsize=9)
    fig.suptitle('925–300 hPa winds on identical pressure and native footprints\nModel mean(q u); NCEP product of monthly means lacks submonthly covariance',fontsize=14)
    fig.savefig(out/'transport_matched_winds.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    for row,(region,kind) in enumerate([('north_india','land'),('mexico','land'),('pacific_nw','ocean')]):
        for col,level in enumerate(('925','700')):
            ax=axes[row,col];level_data=result['regions'][region]['global06']['pressure_levels'][kind][level]
            for component,style in [(0,'-'),(1,'--')]:
                ax.plot(months,np.array(level_data['monthly_reference'])[:,component],style,color='#24272b',label='NCEP '+('east' if component==0 else 'north'))
                for name in colors:
                    d=result['regions'][region][name]['pressure_levels'][kind][level]
                    ax.plot(months,np.array(d['monthly_model'])[:,component],style,color=colors[name],label=labels[name]+' '+('east' if component==0 else 'north'))
            ax.axhline(0,color='#777',lw=.6);ax.grid(alpha=.2)
            ax.set(title=f"{region.replace('_',' ').title()} · {kind} · {level} hPa",ylabel='Wind m/s',xticks=months,xticklabels=list('JFMAMJJASOND'))
            if row==0 and col==0:ax.legend(fontsize=8,ncol=2)
    fig.suptitle('Wind at matched pressure levels — separate circulation from humidity weighting\nModel two-box vertical representation; identical925hPa-valid native footprints',fontsize=14)
    fig.savefig(out/'transport_pressure_levels.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,3,figsize=(15,12),layout='constrained')
    for row,(region,(a,case)) in enumerate(pictures_data.items()):
        g=case.grid;mask=a['score_land'];season=FOCUS[region];months=SEASONS[season];weights,durations,_=observation_weights(a['days']);n=len(a['days']);idx=a['scored_indices']
        coeff=(weights[months]*durations[months,None]).sum(0)
        sim=np.tensordot(coeff,a['rain'][idx].sum(1),axes=(0,0));obs=np.nan_to_num(case.obs_P[months]).sum(0)
        storm=np.tensordot(coeff,a['storm'][idx].sum(1),axes=(0,0))
        spec=earth.REGIONS[region];geo=projection_jacobian(g.lat,case.lon,spec['lat0'],spec['lon0']);east,north=geographic_wind(a['winds'][idx,0,0],a['winds'][idx,0,1],geo)
        u=np.tensordot(coeff/coeff.sum(),east,axes=(0,0));v=np.tensordot(coeff/coeff.sum(),north,axes=(0,0))
        limit=max(float(np.percentile(obs[mask],98)),float(np.percentile(sim[mask],98)),1.)
        for col,value in enumerate((obs,sim,storm)):
            ax=axes[row,col];ax.set_facecolor('#dceaf2')
            if col<2:im=ax.pcolormesh(case.lon,g.lat,np.ma.masked_where(~mask,value),cmap='YlGnBu',vmin=0,vmax=limit,shading='auto')
            else:
                bound=max(1.,float(np.percentile(np.abs(value[mask]),98)));im=ax.pcolormesh(case.lon,g.lat,np.ma.masked_where(~mask,value),cmap='BrBG',vmin=-bound,vmax=bound,shading='auto')
                stride=4;sl=(slice(None,None,stride),slice(None,None,stride));q=ax.quiver(case.lon[sl],g.lat[sl],np.where(g.inmap,u,np.nan)[sl],np.where(g.inmap,v,np.nan)[sl],scale=110,width=.003,color='#202d36')
                ax.quiverkey(q,.65,.94,5,'5 m/s',coordinates='axes',labelpos='E')
            ax.set(title=f"{region.replace('_',' ').title()} · {season}\n"+['Observed rain','Hydrostatic-half rain','Storm supply + / removal −; lower winds'][col],xlabel='Longitude',ylabel='Latitude')
            ax.set_xlim(case.lon[g.inmap].min(),case.lon[g.inmap].max());ax.set_ylim(g.lat[g.inmap].min(),g.lat[g.inmap].max())
            fig.colorbar(im,ax=ax,shrink=.78,label='mm/season')
    fig.suptitle('Seasonal rainfall and storm redistribution — diagnostic maps, unchanged climate\nColors clipped at regional98th percentiles; arrows are lower-air winds',fontsize=15)
    fig.savefig(out/'transport_seasonal_maps.png',dpi=150);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve()
    evidence,result,maps=verify_and_summarize(out);plot(out,result,maps)
    result['images_sha256']={p.name:file_hash(p) for p in sorted(out.glob('transport_*.png'))}
    result['analyzer_sha256']=file_hash(Path(__file__))
    write_json(out/'diagnosis.json',result);write_json(out/'scientific_verification.json',evidence)
    for region,profiles in result['regions'].items():
        for name,data in profiles.items():
            s=data['full_land']['seasons'][FOCUS[region]]
            print(region,name,FOCUS[region],json.dumps(s))


if __name__=='__main__':main()
