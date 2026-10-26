"""Cached native-grid thermal/humidity audit; no climate integration or fitting."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments import v10_forcing_audit as old
from rotclimate.column_thermodynamics import integrate_saturation_profile,specific_saturation,saturation_column,G
from rotclimate.model import w_sat
from local_benchmark_protocol import file_hash,freeze,write_json


def partial_humidity(q,pressure_hpa):
    q=np.asarray(q,float);p=np.asarray(pressure_hpa,float)
    if (q.ndim!=3 or p.ndim!=1 or q.shape[1]!=len(p) or not np.isfinite(q).all() or (q<0).any()
            or p[0]!=925 or p[-1]!=300 or not (np.diff(p)<0).all() or 700 not in p):
        raise ValueError('Need finite nonnegative monthly native q and descending925–300hPa levels including700')
    k=list(p).index(700)
    integrate=lambda a,levels:np.trapezoid(a[:,::-1],x=levels[::-1]*100,axis=1)
    water=integrate(q,p)/G
    lower=integrate(q[:,:k+1],p[:k+1])/((p[0]-p[k])*100)
    upper=integrate(q[:,k:],p[k:])/((p[k]-p[-1])*100)
    if (lower<=0).any():raise ValueError('Nonpositive lower partial-column humidity')
    return water,upper/lower


def main():
    path=ROOT/'calibration/vertical_reference_20261026/plan.json';plan=json.loads(path.read_text())
    out=ROOT/'output/vertical_reference_20261026';out.mkdir(exist_ok=True)
    if (out/'review.json').exists():raise ValueError('Preserve prior reference audit')
    cache=ROOT/'data/v10_atmosphere';manifest=json.loads((cache/'downloads.json').read_text());sources=[path,Path(__file__),cache/'downloads.json',
        ROOT/'experiments/v10_forcing_audit.py',ROOT/'rotclimate/column_thermodynamics.py',ROOT/'rotclimate/model.py']
    def payload(name,url):
        p=cache/name;row=manifest[name]
        if row['url']!=url or row['sha256']!=file_hash(p):raise ValueError('Changed reference provenance: '+name)
        sources.append(p);return p.read_text()
    def field(var,region):
        units=old.metadata(payload(var+'.das',old.BASE+f'{var}.mon.1981-2010.ltm.nc.das'),var)
        pieces=[]
        for i,box in enumerate(old.BOXES[region]):
            y0,y1,x0,x1=box;query=f'{var}[0:1:11][0:1:{old.VARIABLES[var]-1}][{y0}:1:{y1}][{x0}:1:{x1}]'
            raw=old.parse_ascii(payload(f'{var}_{region}_{i}.ascii',old.BASE+f'{var}.mon.1981-2010.ltm.nc.ascii?'+query),var)
            old.validate_subset(raw,box,old.VARIABLES[var]);pieces.append(old.normalize(raw,var,units))
        first=pieces[0]
        for other in pieces[1:]:
            if any(not np.array_equal(getattr(first,a),getattr(other,a)) for a in ['pressure_hpa','latitude','time']):raise ValueError('Split reference axes changed')
        longitude=np.concatenate([f.longitude for f in pieces]);order=np.argsort(longitude)
        return old.Field(np.concatenate([f.values for f in pieces],axis=-1)[...,order],first.pressure_hpa,first.latitude,longitude[order],first.time)
    fields={region:{var:field(var,region) for var in ['air','shum']} for region in plan['regions']}
    sources += [ROOT/'output/circulation_audit_20261026'/f'{r}.npz' for r in plan['regions']]
    identity=freeze(out/'protocol.json',dict(plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in dict.fromkeys(sources)}))
    rows={};plot_data={}
    for region,group in fields.items():
        air,hum=group['air'],group['shum'];levels=np.array(plan['pressure_hpa'])
        if any(not np.array_equal(getattr(air,a),getattr(hum,a)) for a in ['latitude','longitude','time']):raise ValueError('Thermal/humidity reference axes changed')
        ti=[list(air.pressure_hpa).index(p) for p in levels];qi=[list(hum.pressure_hpa).index(p) for p in levels]
        q=hum.values[:,qi]/(1+hum.values[:,qi]);t=air.values[:,ti]+273.15
        observed,ratio=partial_humidity(q.reshape(12,len(levels),-1),levels)
        with np.load(ROOT/'output/circulation_audit_20261026'/f'{region}.npz') as saved:
            if (not np.array_equal(saved['reference_latitude'],hum.latitude) or not np.array_equal(saved['reference_longitude'],hum.longitude)
                    or not np.array_equal(saved['partial_water_kgm2'].reshape(12,-1),observed)):
                raise ValueError('Reference footprints/water changed')
            mask=saved['mask_ocean'];area=saved['native_area_km2'][mask];days=saved['month_days']
        if not mask.any():raise ValueError('No native ocean footprint')
        q=q.reshape(12,len(levels),-1)[:,:,mask];t=t.reshape(12,len(levels),-1)[:,:,mask]
        observed=observed[:,mask];ratio=ratio[:,mask]
        weights=days[:,None]*area[None,:];mean=lambda v:float(np.sum(v*weights)/weights.sum())
        monthly=lambda v:(v*area).sum(-1)/area.sum()
        annual_profile=lambda v:(v*weights[:,None,:]).sum((0,2))/weights.sum()
        obs_sat=specific_saturation(t,levels[None,:,None]*100);obs_capacity,_=partial_humidity(obs_sat,levels)
        row=dict(native_ocean_cells=int(mask.sum()),area_km2=float(area.sum()),observed_partial_water_mm=mean(observed),
            observed_mean_upper_lower_q_ratio=mean(ratio),observed_effective_liquid_saturation_fraction=mean(observed)/mean(obs_capacity),
            profiles={},native_observed_partial_water_mm=observed.tolist(),native_observed_partial_q_ratio=ratio.tolist())
        plot_data[region]=dict(observed_temperature=annual_profile(t)-273.15,observed_water=monthly(observed))
        for profile in plan['profiles']:
            ps=np.full((12,int(mask.sum())),92500.)
            edges=np.broadcast_to(levels[:,None,None]*100,(len(levels),)+ps.shape)
            _,temperatures=integrate_saturation_profile(t[:,0]-273.15,ps,edges,profile=profile,lapse_k_km=plan['lapse_k_km'])
            predicted_t=np.moveaxis(temperatures,0,1)
            qs=specific_saturation(predicted_t,levels[None,:,None]*100)
            cap,shape=partial_humidity(qs,levels)
            plot_data[region][profile]=dict(temperature=annual_profile(predicted_t)-273.15,water=monthly(cap)*plan['map_rh'])
            thermal_mae=float((np.abs(predicted_t[:,1:]-t[:,1:])*weights[:,None,:]).sum()/(weights.sum()*(len(levels)-1)))
            for rh in plan['ocean_column_rh']:
                own=rh*cap;key=f'{profile}_rh{rh:.6g}'
                row['profiles'][key]=dict(profile=profile,column_rh=rh,partial_water_mm=mean(own),
                    partial_water_mae_mm=mean(np.abs(own-observed)),partial_water_bias_mm=mean(own-observed),
                    mean_upper_lower_q_ratio=mean(shape),thermal_shape_mae_C=thermal_mae,
                    native_predicted_partial_water_mm=own.tolist(),native_partial_q_ratio=shape.tolist())
        rows[region]=row
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for (region,data),pair in zip(plot_data.items(),axes):
        ax,water_ax=pair
        for key,color,label in [('observed','#222','NCEP temperature'),('lapse','#ad7951','Environmental lapse'),('moist','#327f94','Saturated moist profile')]:
            value=data['observed_temperature'] if key=='observed' else data[key]['temperature']
            ax.plot(value,levels,color=color,label=label,lw=2)
        ax.set(yscale='log',ylim=(925,300),xlabel='Temperature (°C)',ylabel='Pressure (hPa)',title=f'{region.title()} · observed925hPa anchor')
        ax.set_yticks(levels);ax.set_yticklabels(levels);ax.legend(frameon=False,fontsize=8);ax.grid(alpha=.15)
        for key,color,label in [('observed','#222','Observed specific humidity'),('lapse','#ad7951','Lapse, column RH0.60'),('moist','#327f94','Moist, column RH0.60')]:
            value=data['observed_water'] if key=='observed' else data[key]['water']
            water_ax.plot(range(12),value,color=color,label=label,lw=2)
        water_ax.set(xticks=range(12),xticklabels=list('JFMAMJJASOND'),ylabel='Matched925–300hPa water (mm)',title=f'{rows[region]["native_ocean_cells"]} native ocean cells · same area/month weights')
        water_ax.legend(frameon=False,fontsize=8);water_ax.grid(alpha=.15)
    fig.suptitle('Earth vertical structure · cached native reference diagnostic',fontsize=16)
    fig.supxlabel('NCEP/NCAR1981–2010 monthly means; both profiles anchored at observed925hPa temperature, higher temperatures/humidity withheld.\n'
        'Shown RH0.60 is the fixed middle design value, not selected by accuracy. Partial-column ocean samples; no climate integration or rainfall score.',fontsize=8)
    picture=out/'native_profiles.png';fig.savefig(picture,dpi=145);plt.close(fig)
    temperature=np.linspace(-65,40,107);fig,axes=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    axes[0].plot(temperature,w_sat(temperature),label='Legacy2.2km vapor scale',color='#888',ls='--')
    capacities={}
    for profile,color in [('lapse','#ad7951'),('moist','#327f94')]:
        column=saturation_column(temperature,101325.,profile=profile,lapse_k_km=plan['lapse_k_km'])
        axes[0].plot(temperature,column.total_mm,label=profile.title()+' pressure profile',color=color)
        axes[1].plot(temperature,column.upper_lower_q_ratio,label=profile.title()+' pressure profile',color=color)
        capacities[profile]=dict(temperature_C=temperature.tolist(),capacity_mm=column.total_mm.tolist(),upper_lower_saturation_q_ratio=column.upper_lower_q_ratio.tolist())
    axes[0].set(yscale='log',ylabel='Saturated whole-column water (mm)',xlabel='Prescribed surface temperature (°C)',title='Pressure integration changes warm and cold capacity')
    axes[1].set(ylabel='Upper/lower saturated specific-humidity ratio',xlabel='Prescribed surface temperature (°C)',title='Capacity profile is not a fixed humidity ratio')
    for ax in axes:ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Physical capacity sensitivity · no observed rainfall fitting',fontsize=15)
    fig.supxlabel('Sea-level pressure, same4.414K/km lapse parameter; moist profile diagnosed from thermodynamics.200K prescribed stratosphere, water top100hPa.\n'
        'Saturation capacity is not actual precipitable water. Effective humidity and all unchanged Earth safeguards still require coupled testing.',fontsize=8)
    second=out/'capacity_profiles.png';fig.savefig(second,dpi=145);plt.close(fig)
    report=dict(complete=True,identity=identity,scope=plan['publication'],regions=rows,capacity_profiles=capacities,
        climate_integrations=0,physics_or_atlas_adoption=False,images_sha256={p.name:file_hash(p) for p in [picture,second]})
    write_json(out/'review.json',report)
    print(json.dumps({r:{k:v for k,v in row.items() if not k.startswith('native_') and k!='profiles'} for r,row in rows.items()},indent=2))
    for r,row in rows.items():print(r,{n:{k:v for k,v in s.items() if not k.startswith('native_')} for n,s in row['profiles'].items()})


if __name__=='__main__':main()
